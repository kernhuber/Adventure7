"""NPC turn handling for the web backend.

NPCRunnerMixin contributes the NPC-facing methods to WebAdventureServer:
- collect_npc_actions: run one move per NPC (dog / zombie / explosion) plus the
  per-turn switch-timer countdown, returning the actions for handle_command to emit.
- handle_minigame_result: apply a finished mini-game result to the dog and reply.

Kept as a mixin so this large, self-referential code can live in its own file while
behaviour stays identical to the original methods. Relies on the host class
providing ``self.game_sessions``.
"""
import json

from Utils import dprint, dl
from webserver.serialization import serialize_real_game_state
from webserver.texts import txt_final_lost_text
from webserver.game_modules import GAME_MODULES_AVAILABLE


class NPCRunnerMixin:

    async def handle_minigame_result(self, websocket, result):
        """Verarbeite Ergebnis eines Mini-Games"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Keine aktive Spielsession"
            }))
            return

        session = self.game_sessions[session_id]


        dprint(dl.WEBGUI, f"🎮 Mini-Game Ergebnis:  -> {result}")

        # Markiere Mini-Game als nicht mehr aktiv
        session["minigame_active"] = False

        # Konvertiere Web-Result zu MiniGames.py Format
        if session["type"] == "real" and GAME_MODULES_AVAILABLE:
            try:
                from NPCDogState import DogFight

                # Konvertiere String zu DogFight Enum
                dog_result_map = {
                    'WON': DogFight.WON,  # Hund gewinnt
                    'LOST': DogFight.LOST,  # Hund verliert
                    'TIE': DogFight.TIE  # Unentschieden
                }
                #
                # Wenn der Hund gesiegt hat, ist das Spiel zu Ende
                #
                if result == "WON":
                    txt=f"""Der Hund hat Dich besiegt - du verlierst das Spiel!
  
  {txt_final_lost_text}                  
                    """
                    game = session["game"]
                    # await self.do_game_over(session_id, game.game_won, txt)
                    await session["web_dialogs"].do_game_over(game.game_won, txt)

                dog_fight_result = dog_result_map.get(result, DogFight.TIE)

                # Suche Hund in der Spielerliste und verarbeite Ergebnis
                game = session["game"]
                from NPCDogState import NPCDogState
                dog = next((p for p in game.players if isinstance(p, NPCDogState)), None)

                fight_message = "Mini-Game beendet"

                if dog and hasattr(dog, 'process_fight_result'):
                    # Übergebe Ergebnis direkt an Hund-Logik
                    fight_message_json = dog.process_fight_result(game, dog_fight_result)
                    fight_message = fight_message_json["function_call"]["args"]["message"]
                    dprint(dl.WEBGUI, f"✅ Fight result verarbeitet: {fight_message[:50]}...")

                # Beende Mini-Game Session im GameState
                if hasattr(game, 'complete_minigame_session'):
                    game.complete_minigame_session(session_id, result)

                # Sende Ergebnis an Client
                response = {
                    "type": "minigame_complete",
                    "result": result,
                    "message": fight_message,
                    "game_state": serialize_real_game_state(game, session_id=session_id)
                }

                await websocket.send(json.dumps(response))
                dprint(dl.WEBGUI, f"✅ Mini-Game Ergebnis verarbeitet: {result}")

            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Fehler beim Verarbeiten des Mini-Game Ergebnisses: {e}")
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Fehler beim Verarbeiten des Spielergebnisses: {str(e)}"
                }))
        else:
            # Demo-Modus
            demo_messages = {
                'WON': f"***Hund gewinnt den Kampf! (Demo)***",
                'LOST': f"***Du gewinnst den Kampf! (Demo)***",
                'TIE': f"***Der Kampf endet unentschieden! (Demo)***"
            }

            response = {
                "type": "minigame_complete",
                "result": result,
                "message": demo_messages.get(result, "Mini-Game beendet (Demo)"),
                "game_state": session["state"]
            }

            await websocket.send(json.dumps(response))

    async def collect_npc_actions(self, game, session_id=None):
        """Sammle NPC-Aktionen OHNE sie zu senden - für später in handle_command"""
        try:
            from NPCDogState import NPCDogState
            from Utils import json_cmd_simple
            # Versuche auch ExplosionState zu importieren
            try:
                from ExplosionState import ExplosionState
                EXPLOSION_AVAILABLE = True
            except ImportError:
                EXPLOSION_AVAILABLE = False
                dprint(dl.WEBGUI, "⚠️  ExplosionState nicht verfügbar")

            npc_actions = []
            players_to_remove = []  # Für Spieler die durch Explosion eliminiert werden

            from NPCZombieState import NPCZombieState

            for npc in game.players:
                if isinstance(npc, NPCDogState):
                    # Normaler NPC (Hund)
                    #
                    # Der NPCDogState ("Hund") liefert ergebnisse, die erst durch
                    # verb_execute ausgeführt werden müssen (z.B: er geht irgendwo hin)
                    # Die verb_execute-Funktion liefert Strings, die erst in dog_messages
                    # umgewandelt werden müssen. (Dies ist notwendig, weil die gleichen
                    # execute-Methoden für alle NPC aufgerufen werden, egal ob PlayerState
                    # oder NPNCPlayerState)
                    #
                    npc_input = npc.NPC_game_move(game)
                    command = npc_input.get("function_call",{}).get("name",None)
                    args = npc_input.get("function_call",{}).get("args",{})

                    if npc_input and command != "nichts":
                        if command != "minigame":
                            if command  in ["interaktion", "interagiere", "interagieren"]:

                                whom = npc_input["function_call"]["args"]["who"]
                                firstmessage = npc_input["function_call"]["args"]["firstmessage"]
                                npc_result = await game.async_verb_interact(npc, session_id, whom, firstmessage)
                            else:
                                npc_result = game.verb_execute_json(npc, npc_input, session_id)
                            if npc_result and npc_result.strip():
                                npc_actions.append(json_cmd_simple("dog_message",f"**{npc.name}:** {npc_result}"))
                        else:
                            #
                            # Initiate Minigame in web GUI
                            #
                            npc_actions.append(npc_input)

                elif isinstance(npc, NPCZombieState):
                    # Zombie NPC
                    npc_input = npc.NPC_game_move(game)
                    command = npc_input.get("function_call", {}).get("name", None)
                    args = npc_input.get("function_call", {}).get("args", {})

                    if npc_input and command != "nichts":
                        if command in ["interaktion", "interagiere", "interagieren"]:
                            whom = args.get("who", "")
                            firstmessage = args.get("firstmessage", "")
                            npc_result = await game.async_verb_interact(npc, session_id, whom, firstmessage)
                        elif command == "zombie_message":
                            # Direct message, no game engine processing needed
                            npc_result = args.get("message", "")
                        else:
                            npc_result = game.verb_execute_json(npc, npc_input, session_id)

                        npc.game_engine_answer(game, npc_result)

                        if npc_result and npc_result.strip():
                            npc_actions.append(json_cmd_simple("zombie_message", f"**{npc.name}:** {npc_result}"))

                elif EXPLOSION_AVAILABLE and isinstance(npc, ExplosionState):
                    # Explosion-NPC - VEREINFACHT
                    dprint(dl.WEBGUI, f"💥 Sammle Explosion: Timer={npc.kaboom_timer}")

                    # ExplosionState.explosion_input() macht ALLES und gibt Nachrichten zurück
                    #explosion_messages = npc.explosion_input(game)
                    #
                    # ExplosionState liefert immer Ergebnisse vom Typ
                    # explosion_message oder do_explosion, die nicht weiter
                    # von verb_execute interpretiert werden müssen, sondern
                    # direkt zur Ausgabe an das GUI übergeben werden können
                    #
                    npc_input = npc.explosion_input(game)
                    command = npc_input.get("function_call", {}).get("name", None)
                    args = npc_input.get("function_call", {}).get("args", {})

                    # Verwende die Nachrichten direkt (keine verb_execute nötig!)
                    if npc_input and command != "nichts":
                        npc_actions.append(npc_input)
                        dprint(dl.WEBGUI, f"💥 Explosion-Messages gesammelt!")

                    # Prüfe ob die Explosion abgelaufen ist (kaboom_timer = 0 nach explosion_input)
                    if npc.kaboom_timer <= 0:
                        dprint(dl.WEBGUI, "💥 Explosion ist abgelaufen - entferne ExplosionState")
                        players_to_remove.append(npc)

            # Switch timer countdown — runs once per turn, after all NPCs have acted
            f = game.get_flags()
            if f.schalter_kontrollraum_timer > 0:
                f.schalter_kontrollraum_timer -= 1
                if f.schalter_kontrollraum_timer <= 0 and not f.zombie_cooperative:
                    f.schalter_kontrollraum = False
            if f.schalter_generatorraum_timer > 0:
                f.schalter_generatorraum_timer -= 1
                if f.schalter_generatorraum_timer <= 0 and not f.zombie_cooperative:
                    f.schalter_generatorraum = False

            # Entferne abgelaufene Explosionen
            for player in players_to_remove:
                if player in game.players:
                    game.players.remove(player)
                    dprint(dl.WEBGUI, f"🗑️  {player.name} aus Spielerliste entfernt")
            # Update game state nach NPC-Aktionen - OHNE Narration (da schon gemacht)
            if session_id and hasattr(self, 'game_sessions') and session_id in self.game_sessions:
                session = self.game_sessions[session_id]
                session["state"] = serialize_real_game_state(game, session_id=session_id)

            return npc_actions

        except Exception as e:
            dprint(dl.WEBGUI, f"⚠️  NPC-Sammeln-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return []
