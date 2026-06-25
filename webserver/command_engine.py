"""Player command handling for the web backend.

CommandEngineMixin contributes the core command loop to WebAdventureServer:
- handle_command: the port of PlayerState.user_input -- pull/parse user input, drive
  the per-session command queue (incl. the LLM "rest" continuation and pending
  input), execute one command per turn, emit the result and any NPC actions.
- execute_single_command: run a single parsed command against the game engine
  (thirst countdown, turn advance, game-over, pinpad), or the demo equivalent.

Kept as a mixin so this large, self-referential code lives in its own file while
behaviour stays identical. Relies on the host class providing ``self.game_sessions``
and the NPC methods (``collect_npc_actions``, ``handle_minigame_result``) from
NPCRunnerMixin.
"""
import json

from Utils import dprint, dl, json_cmd_simple
from webserver.serialization import serialize_real_game_state
from webserver.demo import process_demo_command_execution, process_simple_command_execution
from webserver.texts import txt_final_lost_text, txt_final_won_text
from webserver.game_modules import GAME_MODULES_AVAILABLE, PlayerState


class CommandEngineMixin:

    async def handle_command(self, websocket, command_data):
        """Verarbeite Spieler-Kommando - Exakte Nachbildung von Player_game_move Logik"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Keine aktive Spielsession"
            }))
            return

        session = self.game_sessions[session_id]
        game = session["game"]


        # NEUE: Blockiere Commands während Mini-Game
        if session.get("minigame_active", False):
            await websocket.send(json.dumps({
                "type": "info",
                "message": "Bitte beende zuerst das laufende Mini-Game!"
            }))
            return

        raw_command = command_data.get('command', '').strip()

        dprint(dl.WEBGUI, f"📥 Kommando empfangen: '{raw_command}' (Modus: {session['type']})")

        # Bestimme welches Command zu verarbeiten ist - EXAKT wie Player_game_move

        #
        # Beispiel: (annahme: wir sind im Schuppen, und dort gibt es eine Leiter (o_leiter))
        #
        # user_input: "nimm die Leiter, gehe nach draussen, und lehne die Leiter an den Schuppen"
        #
        # --> Wird zur Verarbeitung an das LLM gesandt. Im aktuellen Kontext gibt es nur
        #     eine Leiter, aber keinen Schuppen. Dss LLM erzeugt folgende function_calls:
        #
        #  cmd_q = [
        #            {...{"nimm", "o_leiter"} ...}
        #            {...{"gehe", "p_schuppen} ...}
        #            {...{"rest", "lehne die Leiter an den Schuppen"}
        #          ]
        #
        # Die Kommandos werden nun pro Spielrunde nach und nach abgearbeitet. Das "rest"-
        # Kommando ist besonders, es wird wieder an das LLM übergeben. Wenn eins der
        # vorigen Kommandos einen neuen Kontext erzeugt hat (z.B. durch Gehen an einen
        # anderen Ort, so wird es eine neue cmd_q erzeugen:
        #
        # cmd_q = [
        #             {... {"anwenden", "o_leiter", "o_schuppen"} ...}
        #         ]
        #
        # ... sonst:
        #
        # cmd_q = [
        #             { ... {"zurueckweisen", "Das geht hier nicht..."} ...}
        #         ]
        #
        # Eine neue Benutzereingabe wird vom GUI erst abgefragt, wenn cmd_q leer ist. Die
        # Kommandos sind alle in dem JSON-Format, welches auch vom LLM zurückgeliefert
        # wird:
        # {
        #   "function_call" : {
        #        "name": "<func_name>":
        #        "args": {
        #            "arg1_name": "arg1_value"
        #                ...
        #            "agnn_name": "argn_value"
        #        }
        #    }
        # }
        #
        # In älteren Versionen des Spiels hatte die Klasse PlayerState eine Funktion
        # user_input() - da wir hier ein web-Interface haben, ist die Logik dieser
        # Funktion hierher gewandert.
        #
        # Todo:
        # Drüber nachdenken die Funktion wieder zurück in PlayerState zu migrieren.

        command_to_execute = None

        # Schritt 1: Prüfe ob Commands in Queue vorhanden sind
        if session["cmd_q"]:
            # Es gibt bereits Commands in der Queue - nimm das nächste
            command_to_execute = session["cmd_q"].popleft()
            dprint(dl.WEBGUI, f"🔄 Führe Command aus Queue aus: {command_to_execute['function_call']['name']}")
        else:
            # Schritt 2: Keine Commands in Queue - hole User Input
            user_input = None

            # Prüfe pending input (aus einem "rest"-Function Call ) zuerst
            if session["pending_llm_input"]:
                user_input = session["pending_llm_input"]
                session["pending_llm_input"] = None
                dprint(dl.WEBGUI, f"🔄 Verwende pending input: '{user_input}'")
            elif raw_command:
                # Verwende frisches Command vom User
                user_input = raw_command
                dprint(dl.WEBGUI, f"🆕 Verwende frisches Command: '{user_input}'")

            if not user_input:
                dprint(dl.WEBGUI, "⚠️  Kein Input verfügbar")
                return

            # Schritt 3: Verarbeite User Input
            if user_input.lower() in ["quit", "inventory", "dogstate", "nichts", "context", "toggle_layout","pinpad","minigame","zombie_chat"]:
                # Direkte Commands ohne LLM-Parsing

                if user_input.lower().startswith("minigame"):
                    minigame_result = await session["web_dialogs"].do_minigame()
                    session["cmd_q"].append({
                        "function_call": {
                            "name": "zurueckweisen",
                            "args": {"why": f"Minigame-Result ergab: {minigame_result}"}
                        }
                    })
                elif user_input.lower().startswith("zombie_chat"):
                    gs = session["game"]
                    pl = next(p for p in gs.players if type(p) is PlayerState)
                    zombie_chat_result = await session["web_dialogs"].do_chat(gs, pl, "Zombie")
                else:
                    session["cmd_q"].append({'function_call': {'name': user_input.lower(), 'args': {}}})
            else:
                # LLM-Parsing erforderlich.
                # user_input hat an dieser Stelle entweder einen Wert aus einer Benutzereingabe
                # oder aus einem "rest"-Kommando
                #
                if session["type"] == "real" and GAME_MODULES_AVAILABLE:
                    try:
                        game = session["game"]
                        player = game.players[0] if game.players else None

                        if hasattr(game, 'llm') and game.llm and player:
                            # LLM-Parsing mit aktuellem Kontext
                            context = game.compile_current_game_context_for_llm_tools(player)
                            parsed_commands = game.llm.parse_user_input_to_commands(user_input, context)

                            dprint(dl.WEBGUI,
                                   f"🤖 LLM parsed {len(parsed_commands)} commands: {[cmd['function_call']['name'] for cmd in parsed_commands]}")

                            # Intercept "rest-command" - GENAU wie in Player_game_move
                            # Das "rest"-Kommando kann, wenn es überhaupt existiert, nur am
                            # Ende des Arrays stehen, welcher vom LLM zurückgeliefert wurde.
                            # Wenn es existiert, werte es aus (Argument in remaining_input schreiben),
                            # und lösche es vom Ende der Queue

                            if len(parsed_commands) > 1:
                                if parsed_commands[-1]["function_call"]["name"] == "rest":
                                    session["pending_llm_input"] = parsed_commands[-1]["function_call"]["args"][
                                        "remaining_input"]
                                    del (parsed_commands[-1])
                                    dprint(dl.WEBGUI,
                                           f"🔄 Rest-Command intercepted! Pending: '{session['pending_llm_input']}'")

                            # Füge Commands zur Queue hinzu
                            session["cmd_q"].extend(parsed_commands)
                        else:
                            dprint(dl.WEBGUI, "⚠️  LLM nicht verfügbar, verwende fallback")
                            session["cmd_q"].append(
                                {'function_call': {'name': 'zurueckweisen', 'args': {'why': 'LLM nicht verfügbar'}}})
                    except Exception as e:
                        dprint(dl.WEBGUI, f"❌ Fehler beim LLM-Parsing: {e}")
                        session["cmd_q"].append(
                            {'function_call': {'name': 'zurueckweisen', 'args': {'why': f'LLM-Fehler: {str(e)}'}}})
                else:
                    # Demo-Modus
                    session["cmd_q"].append(
                        {'function_call': {'name': 'zurueckweisen', 'args': {'why': f'Demo: {user_input}'}}})

            # Schritt 4: Nimm das erste Command aus der Queue
            # An dieser Stelle wird die Queue nach und nach abgearbeitet (pro Spielrunde ein Kommando)
            #
            if session["cmd_q"]:
                command_to_execute = session["cmd_q"].popleft()
            else:
                dprint(dl.WEBGUI, "⚠️  Keine Commands verfügbar nach Verarbeitung")
                return

        # Schritt 5: Führe das Command aus
        dprint(dl.WEBGUI, f"▶️  Führe aus: {command_to_execute['function_call']['name']}")
        result = await self.execute_single_command(session, command_to_execute, session_id)

        res_msg = json_cmd_simple("player_message", result)
        # Schritt 6: Sende Antwort
        response = {
            "type": "command_result",
            "command": raw_command,
            "executed_command": command_to_execute['function_call']['name'],
            "results": [
                {"command": command_to_execute['function_call']['name'], "result": result,
                 "is_game_move": not (command_to_execute['function_call']['name'] == "zurueckweisen"
                                      and command_to_execute['function_call'].get('args', {}).get('is_system_error', False))}],
            "game_state": session["state"],
            "pending_commands": len(session["cmd_q"]),  # Debug info
            "has_pending_input": session["pending_llm_input"] is not None,  # Debug info
            "pending_input_preview": session["pending_llm_input"][:50] + "..." if session["pending_llm_input"] and len(
                session["pending_llm_input"]) > 50 else session["pending_llm_input"]
        }

        await websocket.send(json.dumps(response))
        dprint(dl.WEBGUI,
               f"✅ Command '{command_to_execute['function_call']['name']}' ausgeführt. Queue: {len(session['cmd_q'])}, Pending: {session['pending_llm_input'] is not None}")

        # Schritt 6.5: Sende NPC-Actions falls vorhanden
        #
        # Nun werden die NPCs behandelt. Auch diese können ein Kommando pro Spielrunde absetzen.
        # Da sie aber nur einzelne Kommandos absetzen, wird keine komplexe Parsing-Logik benötigt

        if "pending_npc_actions" in session and session["pending_npc_actions"]:
            npc_actions = session["pending_npc_actions"]
            del session["pending_npc_actions"]  # Cleanup

            # NEUE: Prüfe auf Mini-Game Trigger in NPC-Actions
            filtered_actions = []
            explosion_happened = False
            for action in npc_actions:
                args = action.get("function_call",{}).get("args",{})
                f_call = action.get("function_call",{}).get("name",None)
                if f_call:
                    match f_call:
                        case "minigame":
                            dprint(dl.WEBGUI, f"🎮 Mini-Game Trigger erkannt!")

                            # Starte Mini-Game
                            result = await session["web_dialogs"].do_minigame()
                            #
                            # Find Dog in Players in current session
                            #
                            r = await self.handle_minigame_result(websocket,result)
                            filtered_actions.append(r)

                        # Formatiere normale Nachrichten für bessere Unterscheidung
                        # if '💥 EXPLOSION:' in action:
                        case "do_explosion":
                            # Echte Explosion - markiere sie eindeutig
                            #filtered_actions.append(args["message"])
                            explosion_happened = True
                            filtered_actions.append({
                                "command":f_call,
                                "message":args["message"]
                            })

                        # elif 'explodiert in' in action and 'Spielzügen' in action:
                        case "explosion_message":
                            # Timer-Nachricht - markiere als Timer
                            filtered_actions.append(
                                {
                                    "command":f_call,
                                    "message":f"**💣 Timer:** {args['message']}"
                                }
                            )
                        case "dog_message": # '**Hund:**' in action:
                            # Hund-Aktion bleibt wie sie ist
                            filtered_actions.append(
                                {
                                    "command":f_call,
                                    "message":args["message"]
                                }
                            )
                        case "zombie_message":
                            filtered_actions.append(
                                {
                                    "command": f_call,
                                    "message": args["message"]
                                }
                            )
                        case _:
                            # Andere NPC-Aktionen
                            filtered_actions.append({})

            if filtered_actions:
                npc_message = {
                    "type": "npc_actions",
                    "command": action, #NEU!!
                    "actions": filtered_actions,
                    "game_state": session["state"]
                }
                #
                # An das GUI senden, wo es dann (in JavaScript) weiterverarbeitet wird
                #
                await websocket.send(json.dumps(npc_message))
                dprint(dl.WEBGUI, f"💥 NPC-Actions gesendet: {len(filtered_actions)} Aktionen")
                #
                # Hat die Explosion uns weggeputzt?
                #
                if explosion_happened:
                    if game.check_game_over():
                        game.game_over = True
                        await session["web_dialogs"].do_game_over(False,txt_final_lost_text)

        # Schritt 7: Wenn noch Commands in Queue oder Pending Input vorhanden, sofort weiter verarbeiten
        if session["cmd_q"] or session["pending_llm_input"]:
            dprint(dl.WEBGUI, f"🔄 Weitere Commands verfügbar - continue processing...")
            # Simuliere weiteres Command ohne User-Input
            await self.handle_command(websocket, {"command": ""})  # Empty command triggers queue processing

    async def execute_single_command(self, session, command_dict, session_id):
        """Führe ein einzelnes Command aus"""
        try:
            # Bestimme ob Narration aktualisiert werden soll
            func_name = command_dict.get('function_call', {}).get('name', '')
            args = command_dict.get('function_call', {}).get('args', {})
            queue_empty = len(session["cmd_q"]) == 0
            is_look_around = func_name == "umsehen"

            dprint(dl.WEBGUI, f"🎭 Aktualisiere Narration (Queue leer: {queue_empty}, Umsehen: {is_look_around})")


            if session["type"] == "real" and GAME_MODULES_AVAILABLE:
                game = session["game"]
                player = game.players[0] if game.players else None



                is_system_error = (func_name == "zurueckweisen" and args.get("is_system_error", False))

                if player and hasattr(game, 'verb_execute_json'):
                    # Durst-Logik - Zähler VOR der Aktion runterzählen (nur bei echten Spielzügen)
                    game.consume_thirst(player, is_system_error)
                    thirst_message = ""

                    # ⬇️ Spezialbehandlung check_pinpad VOR dem allgemeinen Aufruf
                    if func_name == "check_pinpad":
                        hash = args.get("hash", "")
                        pin_result = await session["web_dialogs"].ask_for_pin(hash)

                        if pin_result == "OK":
                            game.objects["o_geld_dollar"].hidden = False
                            return "**Die Zahl stimmt!** Der Automat rattert und spuckt frische US-Dollar aus."
                        else:
                            return " --- Die Zahl ist falsch. ---"

                    # Echte Game-Engine - Aktion ZUERST ausführen (z.B. Trinken setzt thirst_counter zurück)
                    if not game.game_over:
                        if func_name in ["interaktion", "interagiere", "interagieren"]:
                            who = player.name
                            whom = command_dict["function_call"]["args"].get("who", "")
                            firstmessage = command_dict["function_call"]["args"].get("firstmessage", "")
                            result = await game.async_verb_interact(player, session_id, whom, firstmessage, dialogs=session["web_dialogs"])
                        else:
                            result = game.verb_execute_json(player, command_dict, session_id)

                    # Durst-Warnung NACH der Aktion prüfen (so sieht man den Post-Aktion-Zustand).
                    # Engine entscheidet game_over (Verdursten) und liefert die Nachricht.
                    thirst_message = game.evaluate_thirst(player)
                    #
                    # game_over kann durch Verdursten oder durch irgendwelche Aktionen bei verb_execute kommen
                    #
                    if game.game_over:
                        txt = f"""
{thirst_message}
                        
{result}
                        
{txt_final_won_text if game.game_won else txt_final_lost_text}
"""

                        # await self.do_game_over(session_id,game.game_won,txt)
                        await session["web_dialogs"].do_game_over(game.game_won, txt)

                    # Füge Durst-Nachricht hinzu, falls vorhanden
                    if thirst_message:
                        result = f"{result}\n\n{thirst_message}"

                    game.advance_time(is_system_error)

                    # Update game state - MIT Narration nur bei Bedarf
                    session["state"] = serialize_real_game_state(game,
                                                                      session_id=session_id)

                    # NPC-Züge sammeln (NICHT senden!) - die werden später in handle_command gesendet
                    npc_actions = []
                    try:
                        npc_actions = await self.collect_npc_actions(game, session_id)
                        # Speichere NPC-Actions in der Session für handle_command
                        session["pending_npc_actions"] = npc_actions
                    except Exception as e:
                        dprint(dl.WEBGUI, f"⚠️  NPC-Fehler: {e}")

                    return result
                else:
                    return process_simple_command_execution(command_dict)
            else:
                # Demo-Modus - auch hier Durst simulieren
                if "player" in session["state"] and "thirst" in session["state"]["player"]:
                    session["state"]["player"]["thirst"] -= 1

                    thirst_message = ""
                    thirst_level = session["state"]["player"]["thirst"]

                    if thirst_level == 0:
                        session["state"]["game_over"] = True
                        thirst_message = "***Leider bist du verdurstet!*** (Demo)"
                    elif thirst_level == 20:
                        thirst_message = "***Du hast Gottseidank noch keinen wirklichen Durst. Nur ein wenig. Ein wenig Durst hast du schon.*** (Demo)"
                    elif thirst_level == 10:
                        thirst_message = "***Jetzt hast Du schon Durst. Du solltest dringend etwas zu Trinken suchen!*** (Demo)"
                    elif thirst_level <= 5:
                        thirst_message = f"***Du hast jetzt richtig Durst! Es reicht noch für {thirst_level} Spielrunden, dann verdurstest Du!*** (Demo)"

                func_name = command_dict.get('function_call', {}).get('name', 'unknown')
                args = command_dict.get('function_call', {}).get('args', {})

                result = process_demo_command_execution(session["state"], func_name, args)

                # Füge Durst-Nachricht hinzu, falls vorhanden
                if thirst_message:
                    result = f"{result}\n\n{thirst_message}"

                return result

        except Exception as e:
            dprint(dl.WEBGUI, f"❌ Fehler beim Ausführen von Command: {e}")
            return f"Fehler: {str(e)}"
