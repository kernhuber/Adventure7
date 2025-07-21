# Funktionierender Web-Server ohne Syntax-Fehler
import asyncio
import json
import threading
import webbrowser
import time
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Set
from collections import deque
import Utils

Utils.ADV_LOGGER = Utils.dlogger()

from Utils import tw_print, dprint, dpprint, dl

# Prüfe ob websockets installiert ist
try:
    import websockets
except ImportError:
    dprint(dl.WEBGUI,"❌ 'websockets' Package ist nicht installiert!")
    dprint(dl.WEBGUI,"Installiere es mit: pip install websockets")
    exit(1)

# Prüfe ob Game-Module verfügbar sind
try:
    from GameState import GameState
    from PlayerState import PlayerState

    GAME_MODULES_AVAILABLE = True
    dprint(dl.WEBGUI,"✅ Game-Module erfolgreich importiert")
except ImportError as e:
    dprint(dl.WEBGUI,f"⚠️  Game-Module nicht verfügbar: {e}")
    dprint(dl.WEBGUI,"⚠️  Verwende Demo-Modus")
    GAME_MODULES_AVAILABLE = False


class WebAdventureServer:
    def __init__(self, host='localhost', websocket_port=8765, http_port=8000):
        self.host = host
        self.websocket_port = websocket_port
        self.http_port = http_port

        # Game instances per session
        self.game_sessions: Dict[str, dict] = {}
        self.connected_clients: Set = set()

        # Start HTTP server for static files
        self.start_http_server()

    def start_http_server(self):
        """Starte HTTP-Server für HTML/CSS/JS Files"""

        def run_http_server():
            try:
                handler = SimpleHTTPRequestHandler
                httpd = HTTPServer((self.host, self.http_port), handler)
                dprint(dl.WEBGUI,f"📄 HTTP Server bereit auf http://{self.host}:{self.http_port}")
                httpd.serve_forever()
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    dprint(dl.WEBGUI,f"⚠️  Port {self.http_port} ist bereits belegt. Verwende anderen Port.")
                    self.http_port += 1
                    self.start_http_server()
                else:
                    dprint(dl.WEBGUI,f"❌ HTTP Server Fehler: {e}")
            except Exception as e:
                dprint(dl.WEBGUI,f"❌ Unerwarteter HTTP Server Fehler: {e}")

        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        time.sleep(0.5)

    async def register_client(self, websocket):
        """Registriere neuen Client"""
        self.connected_clients.add(websocket)
        session_id = str(id(websocket))

        dprint(dl.WEBGUI,f"🔌 Neuer Client verbunden: {session_id}")

        if GAME_MODULES_AVAILABLE:
            # Versuche echtes GameState zu verwenden
            try:
                dprint(dl.WEBGUI,f"🎮 Versuche echtes GameState zu erstellen...")
                game = GameState()
                dprint(dl.WEBGUI,f"✅ GameState erstellt")

                # Spieler erstellen
                player = PlayerState("WebPlayer", game.places["p_start"])
                game.players.append(player)

                # Umschlag hinzufügen
                if "o_umschlag" in game.objects:
                    player.add_to_inventory(game.objects["o_umschlag"])
                    dprint(dl.WEBGUI,f"✅ Umschlag hinzugefügt")

                dprint(dl.WEBGUI,f"✅ Spieler erstellt: {player.name} in {player.location.name}")

                # Versuche Hund hinzuzufügen
                try:
                    from NPCPlayerState import NPCPlayerState
                    dog = NPCPlayerState(name="Hund", location=game.places["p_geldautomat"])
                    game.players.append(dog)
                    dprint(dl.WEBGUI,f"✅ Hund hinzugefügt: {dog.name} in {dog.location.name}")
                    dprint(dl.WEBGUI,f"🎮 Spieler insgesamt: {len(game.players)}")
                except Exception as e:
                    dprint(dl.WEBGUI,f"⚠️  Hund konnte nicht hinzugefügt werden: {e}")

                # Konvertiere zu serialisierbarem Format
                game_state = self.serialize_real_game_state(game)

                # Session mit Command-Queue und Pending-Input erstellen
                self.game_sessions[session_id] = {
                    "type": "real",
                    "game": game,
                    "state": game_state,
                    "cmd_q": deque(),  # Command queue wie in PlayerState
                    "pending_llm_input": None  # Pending input wie in PlayerState
                }

            except Exception as e:
                dprint(dl.WEBGUI,f"❌ Fehler beim echten GameState: {e}")
                dprint(dl.WEBGUI,f"⚠️  Verwende Demo-Modus als Fallback")
                game_state = self.create_demo_game_state()
                self.game_sessions[session_id] = {
                    "type": "demo",
                    "state": game_state,
                    "cmd_q": deque(),
                    "pending_llm_input": None
                }
        else:
            # Demo-Modus
            dprint(dl.WEBGUI,f"📱 Erstelle Demo-GameState...")
            game_state = self.create_demo_game_state()
            self.game_sessions[session_id] = {
                "type": "demo",
                "state": game_state,
                "cmd_q": deque(),
                "pending_llm_input": None
            }

        # Sende initialen Zustand
        await self.send_game_state(websocket, self.game_sessions[session_id]["state"])
        dprint(dl.WEBGUI,f"✅ Client {session_id} initialisiert ({self.game_sessions[session_id]['type']} Modus)")

    def create_demo_game_state(self):
        """Erstelle Demo-GameState ohne echte Game-Module"""
        return {
            "round": 1,
            "game_over": False,
            "game_won": False,
            "player": {
                "name": "WebPlayer",
                "location": "Wüsten-Start",
                "thirst": 40,
                "inventory": ["Briefumschlag"]
            },
            "environment": {
                "objects": ["Kaputtes Fahrrad"],
                "ways": ["Zum Schuppen", "Zum Warenautomat", "Zum Geldautomat"],
                "blockedWays": []
            },
            "scene_description": """Du befindest dich in einer endlosen Wüste. Die Sonne brennt erbarmungslos herab. 
            Dein Fahrrad liegt kaputt neben dir - die Kette ist gerissen. Du musst einen Weg finden, 
            das Fahrrad zu reparieren und deinen wichtigen Briefumschlag rechtzeitig abzuliefern."""
        }

    def serialize_real_game_state(self, game):
        """Konvertiere echtes GameState zu JSON-Format"""
        try:
            player = game.players[0] if game.players else None
            if not player:
                return self.create_demo_game_state()

            # Sichere Zugriffe
            current_location = getattr(player, 'location', None)
            if not current_location:
                return self.create_demo_game_state()

            # Objekte
            visible_objects = []
            try:
                for obj in getattr(current_location, 'place_objects', []):
                    if not getattr(obj, 'hidden', True):
                        callnames = getattr(obj, 'callnames', ['Unbekanntes Objekt'])
                        if callnames:
                            visible_objects.append(callnames[0])
            except:
                pass

            # Wege
            available_ways = []
            blocked_ways = []
            try:
                for way in getattr(current_location, 'ways', []):
                    if getattr(way, 'visible', True):
                        try:
                            obstruction = way.obstruction_check(game) if hasattr(way, 'obstruction_check') else "Free"
                            destination = getattr(way, 'destination', None)
                            if destination:
                                dest_name = getattr(destination, 'callnames', ['Unbekanntes Ziel'])
                                dest_name = dest_name[0] if dest_name else 'Unbekanntes Ziel'

                                if obstruction == "Free":
                                    available_ways.append(dest_name)
                                else:
                                    blocked_ways.append(f"{dest_name} ({obstruction})")
                        except:
                            pass
            except:
                pass

            # Szenenbeschreibung
            scene_description = "Du befindest dich an einem mysteriösen Ort."
            try:
                if hasattr(game, 'llm') and game.llm and hasattr(game.llm, 'narrate'):
                    scene_description = game.llm.narrate(game, player)
                elif hasattr(current_location, 'description'):
                    scene_description = current_location.description
            except:
                pass

            return {
                "round": getattr(game, 'time', 1),
                "game_over": getattr(game, 'game_over', False),
                "game_won": getattr(game, 'game_won', False),
                "player": {
                    "name": getattr(player, 'name', 'WebPlayer'),
                    "location": getattr(current_location, 'callnames', ['Unbekannt'])[0],
                    "thirst": getattr(player, 'thirst_counter', 40),
                    "inventory": [getattr(item, 'callnames', ['Unbekanntes Item'])[0]
                                  for item in getattr(player, 'inventory', [])]
                },
                "environment": {
                    "objects": visible_objects,
                    "ways": available_ways,
                    "blockedWays": blocked_ways
                },
                "scene_description": scene_description
            }

        except Exception as e:
            dprint(dl.WEBGUI,f"❌ Fehler beim Serialisieren: {e}")
            return self.create_demo_game_state()

    async def unregister_client(self, websocket):
        """Client-Verbindung beenden"""
        self.connected_clients.discard(websocket)
        session_id = str(id(websocket))
        if session_id in self.game_sessions:
            del self.game_sessions[session_id]
        dprint(dl.WEBGUI,f"👋 Client {session_id} getrennt")

    async def send_game_state(self, websocket, game_state):
        """Sende Game-State an Client"""
        try:
            message = {
                "type": "game_state",
                "data": game_state
            }
            await websocket.send(json.dumps(message))
            dprint(dl.WEBGUI,f"📤 Game-State gesendet")
        except Exception as e:
            dprint(dl.WEBGUI,f"❌ Fehler beim Senden: {e}")

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
        raw_command = command_data.get('command', '').strip()

        dprint(dl.WEBGUI,f"📥 Kommando empfangen: '{raw_command}' (Modus: {session['type']})")

        # Bestimme welches Command zu verarbeiten ist - EXAKT wie Player_game_move
        command_to_execute = None

        # Schritt 1: Prüfe ob Commands in Queue vorhanden sind
        if session["cmd_q"]:
            # Es gibt bereits Commands in der Queue - nimm das nächste
            command_to_execute = session["cmd_q"].popleft()
            dprint(dl.WEBGUI,f"🔄 Führe Command aus Queue aus: {command_to_execute['function_call']['name']}")
        else:
            # Schritt 2: Keine Commands in Queue - hole User Input
            user_input = None

            # Prüfe pending input zuerst
            if session["pending_llm_input"]:
                user_input = session["pending_llm_input"]
                session["pending_llm_input"] = None
                dprint(dl.WEBGUI,f"🔄 Verwende pending input: '{user_input}'")
            elif raw_command:
                # Verwende frisches Command vom User
                user_input = raw_command
                dprint(dl.WEBGUI,f"🆕 Verwende frisches Command: '{user_input}'")

            if not user_input:
                dprint(dl.WEBGUI,"⚠️  Kein Input verfügbar")
                return

            # Schritt 3: Verarbeite User Input
            if user_input.lower() in ["quit", "inventory", "dogstate", "nichts", "context", "toggle_layout"]:
                # Direkte Commands ohne LLM-Parsing
                session["cmd_q"].append({'function_call': {'name': user_input.lower(), 'args': {}}})
            else:
                # LLM-Parsing erforderlich
                if session["type"] == "real" and GAME_MODULES_AVAILABLE:
                    try:
                        game = session["game"]
                        player = game.players[0] if game.players else None

                        if hasattr(game, 'llm') and game.llm and player:
                            # LLM-Parsing mit aktuellem Kontext
                            context = game.compile_current_game_context_for_llm_tools(player)
                            parsed_commands = game.llm.parse_user_input_to_commands(user_input, context)

                            print(
                                f"🤖 LLM parsed {len(parsed_commands)} commands: {[cmd['function_call']['name'] for cmd in parsed_commands]}")

                            # Intercepte "rest-command" - GENAU wie in Player_game_move
                            if len(parsed_commands) > 1:
                                if parsed_commands[-1]["function_call"]["name"] == "rest":
                                    session["pending_llm_input"] = parsed_commands[-1]["function_call"]["args"][
                                        "remaining_input"]
                                    del (parsed_commands[-1])
                                    dprint(dl.WEBGUI,f"🔄 Rest-Command intercepted! Pending: '{session['pending_llm_input']}'")

                            # Füge Commands zur Queue hinzu
                            session["cmd_q"].extend(parsed_commands)
                        else:
                            dprint(dl.WEBGUI,"⚠️  LLM nicht verfügbar, verwende fallback")
                            session["cmd_q"].append(
                                {'function_call': {'name': 'zurueckweisen', 'args': {'why': 'LLM nicht verfügbar'}}})
                    except Exception as e:
                        dprint(dl.WEBGUI,f"❌ Fehler beim LLM-Parsing: {e}")
                        session["cmd_q"].append(
                            {'function_call': {'name': 'zurueckweisen', 'args': {'why': f'LLM-Fehler: {str(e)}'}}})
                else:
                    # Demo-Modus
                    session["cmd_q"].append(
                        {'function_call': {'name': 'zurueckweisen', 'args': {'why': f'Demo: {user_input}'}}})

            # Schritt 4: Nimm das erste Command aus der Queue
            if session["cmd_q"]:
                command_to_execute = session["cmd_q"].popleft()
            else:
                dprint(dl.WEBGUI,"⚠️  Keine Commands verfügbar nach Verarbeitung")
                return

        # Schritt 5: Führe das Command aus
        dprint(dl.WEBGUI,f"▶️  Führe aus: {command_to_execute['function_call']['name']}")
        result = await self.execute_single_command(session, command_to_execute)

        # Schritt 6: Sende Antwort
        response = {
            "type": "command_result",
            "command": raw_command,
            "executed_command": command_to_execute['function_call']['name'],
            "results": [
                {"command": command_to_execute['function_call']['name'], "result": result, "is_game_move": True}],
            "game_state": session["state"],
            "pending_commands": len(session["cmd_q"]),  # Debug info
            "has_pending_input": session["pending_llm_input"] is not None,  # Debug info
            "pending_input_preview": session["pending_llm_input"][:50] + "..." if session["pending_llm_input"] and len(
                session["pending_llm_input"]) > 50 else session["pending_llm_input"]
        }

        await websocket.send(json.dumps(response))
        print(
            f"✅ Command '{command_to_execute['function_call']['name']}' ausgeführt. Queue: {len(session['cmd_q'])}, Pending: {session['pending_llm_input'] is not None}")

        # Schritt 7: Wenn noch Commands in Queue oder Pending Input vorhanden, sofort weiter verarbeiten
        if session["cmd_q"] or session["pending_llm_input"]:
            dprint(dl.WEBGUI,f"🔄 Weitere Commands verfügbar - continue processing...")
            # Simuliere weiteres Command ohne User-Input
            await self.handle_command(websocket, {"command": ""})  # Empty command triggers queue processing

    def create_simple_command(self, user_input):
        """Erstelle einfaches Command ohne LLM"""
        return {'function_call': {'name': 'zurueckweisen', 'args': {'why': f'Einfache Verarbeitung: {user_input}'}}}

    async def execute_single_command(self, session, command_dict):
        """Führe ein einzelnes Command aus"""
        try:
            if session["type"] == "real" and GAME_MODULES_AVAILABLE:
                game = session["game"]
                player = game.players[0] if game.players else None

                if player and hasattr(game, 'verb_execute_json'):
                    # Durst-Logik - GENAU wie in Player_game_move
                    player.thirst_counter -= 1
                    thirst_message = ""

                    if player.thirst_counter == 0:
                        game.game_over = True
                        thirst_message = "***Leider bist du verdurstet!***"
                    elif player.thirst_counter == 20:
                        thirst_message = "***Du hast Gottseidank noch keinen wirklichen Durst. Nur ein wenig. Ein wenig Durst hast du schon.***"
                    elif player.thirst_counter == 10:
                        thirst_message = "***Jetzt hast Du schon Durst. Du solltest dringend etwas zu Trinken suchen!***"
                    elif player.thirst_counter <= 5:
                        thirst_message = f"***Du hast jetzt richtig Durst! Es reicht noch für {player.thirst_counter} Spielrunden, dann verdurstest Du!***"

                    # Echte Game-Engine
                    result = game.verb_execute_json(player, command_dict)

                    # Füge Durst-Nachricht hinzu, falls vorhanden
                    if thirst_message:
                        result = f"{result}\n\n{thirst_message}"

                    if hasattr(game, 'time'):
                        game.time += 1

                    # Update game state
                    session["state"] = self.serialize_real_game_state(game)

                    # NPC-Züge ausführen
                    try:
                        await self.process_npc_turns(game, None)  # websocket=None, da wir nur den state updaten
                    except Exception as e:
                        dprint(dl.WEBGUI,f"⚠️  NPC-Fehler: {e}")

                    return result
                else:
                    return self.process_simple_command_execution(command_dict)
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

                result = self.process_demo_command_execution(session["state"], func_name, args)

                # Füge Durst-Nachricht hinzu, falls vorhanden
                if thirst_message:
                    result = f"{result}\n\n{thirst_message}"

                return result

        except Exception as e:
            dprint(dl.WEBGUI,f"❌ Fehler beim Ausführen von Command: {e}")
            return f"Fehler: {str(e)}"

    def process_simple_command_execution(self, command_dict):
        """Einfache Command-Ausführung ohne vollständige Game-Engine"""
        func_name = command_dict.get('function_call', {}).get('name', 'unknown')
        return f"Kommando '{func_name}' erkannt (vereinfachter Modus)"

    def process_demo_command_execution(self, game_state, func_name, args):
        """Demo-Command-Ausführung"""
        if func_name == "hilfe":
            return "**Demo-Modus aktiv** - Verfügbare Kommandos: hilfe, umsehen, gehe, nimm, untersuche"
        elif func_name == "umsehen":
            return "Du blickst umher. Die Wüstensonne brennt erbarmungslos."
        elif func_name == "gehe":
            direction = args.get('direction', 'unbekannt')
            if "schuppen" in direction.lower():
                game_state["player"]["location"] = "Schuppen"
                game_state["environment"]["objects"] = ["Blumentopf", "Stuhl"]
                game_state["environment"]["ways"] = ["Zurück zum Start"]
                game_state["scene_description"] = "Du stehst vor einem alten Holzschuppen."
                return "Du gehst zum Schuppen."
            elif "start" in direction.lower():
                game_state["player"]["location"] = "Wüsten-Start"
                game_state["environment"]["objects"] = ["Kaputtes Fahrrad"]
                game_state["environment"]["ways"] = ["Zum Schuppen", "Zum Warenautomat", "Zum Geldautomat"]
                game_state["scene_description"] = "Du bist zurück am Startpunkt."
                return "Du kehrst zum Start zurück."
            else:
                return f"Du gehst zu: {direction}"
        elif func_name == "zurueckweisen":
            why = args.get('why', 'Unbekannter Grund')
            return f"***{why}***"
        else:
            return f"Demo-Kommando '{func_name}' ausgeführt"

    async def process_npc_turns(self, game, websocket):
        """Führe NPC-Züge aus - inklusive ExplosionState"""
        try:
            from NPCPlayerState import NPCPlayerState
            # Versuche auch ExplosionState zu importieren
            try:
                from ExplosionState import ExplosionState
                EXPLOSION_AVAILABLE = True
            except ImportError:
                EXPLOSION_AVAILABLE = False
                dprint(dl.WEBGUI,"⚠️  ExplosionState nicht verfügbar")

            npc_actions = []
            players_to_remove = []  # Für Spieler die durch Explosion eliminiert werden

            for npc in game.players:
                if isinstance(npc, NPCPlayerState):
                    # Normaler NPC (Hund)
                    npc_input = npc.NPC_game_move(game)
                    if npc_input and npc_input != "nichts":
                        npc_result = game.verb_execute(npc, npc_input)
                        if npc_result and npc_result.strip():
                            npc_actions.append(f"**{npc.name}:** {npc_result}")

                elif EXPLOSION_AVAILABLE and isinstance(npc, ExplosionState):
                    # Explosion-NPC
                    dprint(dl.WEBGUI,f"💥 Verarbeite Explosion: Timer={npc.kaboom_timer}")

                    # ExplosionState verwendet explosion_input() statt NPC_game_move()
                    explosion_input = npc.explosion_input(game)

                    if explosion_input and explosion_input != "nichts":
                        # Explosion hat etwas getan - führe es aus
                        explosion_result = game.verb_execute(npc, explosion_input)
                        if explosion_result and explosion_result.strip():
                            npc_actions.append(f"**💥 EXPLOSION:** {explosion_result}")

                    # Prüfe ob die Explosion abgelaufen ist (kaboom_timer = 0 nach explosion_input)
                    if npc.kaboom_timer <= 0:
                        dprint(dl.WEBGUI,"💥 Explosion ist abgelaufen - entferne ExplosionState")
                        players_to_remove.append(npc)
                    else:
                        # Timer-Nachricht für noch aktive Explosionen
                        timer_msg = f"***Sprengladung explodiert in {npc.kaboom_timer} Spielzügen in {npc.location.name if npc.location else 'unbekanntem Ort'}***"
                        npc_actions.append(f"**💣 Timer:** {timer_msg}")

            # Entferne abgelaufene Explosionen
            for player in players_to_remove:
                if player in game.players:
                    game.players.remove(player)
                    dprint(dl.WEBGUI,f"🗑️  {player.name} aus Spielerliste entfernt")

            # Sende NPC-Aktionen an Client
            if npc_actions and websocket:
                npc_message = {
                    "type": "npc_actions",
                    "actions": npc_actions,
                    "game_state": self.serialize_real_game_state(game)
                }
                await websocket.send(json.dumps(npc_message))

        except Exception as e:
            dprint(dl.WEBGUI,f"⚠️  NPC-Fehler (inklusive Explosion): {e}")
            import traceback
            traceback.print_exc()

    def process_demo_command(self, game_state, command):
        """Demo-Kommando-Verarbeitung (Legacy - wird nicht mehr verwendet)"""
        if "hilfe" in command:
            return "**Demo-Modus aktiv** - Verfügbare Kommandos: hilfe, umsehen, gehe zum [Ort], inventar"
        elif "umsehen" in command:
            return "Du blickst umher. Die Wüstensonne brennt erbarmungslos."
        elif "inventar" in command:
            items = game_state["player"]["inventory"]
            return f"**Du trägst bei dir:** {', '.join(items)}" if items else "Dein Inventar ist leer."
        elif "schuppen" in command and "gehe" in command:
            game_state["player"]["location"] = "Schuppen"
            game_state["environment"]["objects"] = ["Blumentopf", "Stuhl"]
            game_state["environment"]["ways"] = ["Zurück zum Start"]
            game_state["scene_description"] = "Du stehst vor einem alten Holzschuppen."
            return "Du gehst zum Schuppen."
        elif "start" in command and "gehe" in command:
            game_state["player"]["location"] = "Wüsten-Start"
            game_state["environment"]["objects"] = ["Kaputtes Fahrrad"]
            game_state["environment"]["ways"] = ["Zum Schuppen", "Zum Warenautomat", "Zum Geldautomat"]
            game_state["scene_description"] = "Du bist zurück am Startpunkt."
            return "Du kehrst zum Start zurück."
        else:
            return f"Du versuchst: '{command}'. (Demo-Modus - versuche: hilfe, umsehen, gehe zum Schuppen)"

    def process_simple_command(self, command):
        """Einfache Kommando-Verarbeitung für echte Game-Engine ohne LLM (Legacy - wird nicht mehr verwendet)"""
        if "hilfe" in command:
            return "**Verfügbare Kommandos:** gehe zu [Ort], untersuche [Objekt], nimm [Objekt], umsehen, inventar"
        elif "umsehen" in command:
            return "Du blickst umher. Die Wüstensonne brennt erbarmungslos."
        elif "inventar" in command:
            return "Verwende 'inventar' Kommando für Inventar-Anzeige."
        else:
            return f"Du versuchst: '{command}'. (Verwende 'hilfe' für verfügbare Kommandos)"

    async def handle_client(self, websocket):
        """Handle einzelne Client-Verbindung"""
        try:
            await self.register_client(websocket)

            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'command':
                        await self.handle_command(websocket, data)
                    elif message_type == 'ping':
                        await websocket.send(json.dumps({"type": "pong"}))
                    else:
                        dprint(dl.WEBGUI,f"⚠️ Unbekannter Message-Type: {message_type}")

                except json.JSONDecodeError as e:
                    dprint(dl.WEBGUI,f"❌ JSON-Fehler: {e}")
                except Exception as e:
                    dprint(dl.WEBGUI,f"❌ Fehler beim Verarbeiten: {e}")

        except websockets.exceptions.ConnectionClosed:
            dprint(dl.WEBGUI,"🔌 Client-Verbindung normal geschlossen")
        except Exception as e:
            dprint(dl.WEBGUI,f"❌ Unerwarteter Fehler: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start_websocket_server(self):
        """Starte WebSocket-Server"""
        dprint(dl.WEBGUI,f"🔌 WebSocket Server startet auf ws://{self.host}:{self.websocket_port}")

        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.websocket_port
        )

        dprint(dl.WEBGUI,f"✅ WebSocket Server bereit auf ws://{self.host}:{self.websocket_port}")
        await server.wait_closed()

    def start_server(self):
        """Starte Server"""
        dprint(dl.WEBGUI,f"🌐 Browser wird geöffnet auf: http://{self.host}:{self.http_port}/adventure_web.html")
        dprint(dl.WEBGUI,f"💡 Game-Module verfügbar: {'✅ Ja' if GAME_MODULES_AVAILABLE else '❌ Nein (Demo-Modus)'}")
        dprint(dl.WEBGUI,f"{'=' * 60}")

        time.sleep(1)

        try:
            webbrowser.open(f"http://{self.host}:{self.http_port}/adventure_web.html")
        except Exception as e:
            dprint(dl.WEBGUI,f"⚠️ Konnte Browser nicht öffnen: {e}")

        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            dprint(dl.WEBGUI,f"\n👋 Server beendet")


def create_working_html():
    """Erstelle eine garantiert funktionierende HTML-Datei"""
    html_content = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>🏜️ Wüsten-Adventure</title>
    <style>
        body { font-family: monospace; background: #2c1810; color: #f5deb3; padding: 20px; }
        .panel { background: rgba(0,0,0,0.7); border: 2px solid #cd853f; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 10px; }
        #user-input { width: 80%; padding: 10px; background: #333; color: #f5deb3; border: 1px solid #cd853f; }
        #send-button { padding: 10px 20px; background: #8b4513; color: #f5deb3; border: 1px solid #cd853f; cursor: pointer; }
        .status { color: #ffd700; }
        .debug-info { font-size: 0.8em; color: #888; margin-top: 5px; }
        .explosion { color: #ff4444; font-weight: bold; animation: blink 1s infinite; }
        .explosion-timer { color: #ffaa00; font-weight: bold; }
        @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.5; } }
    </style>
</head>
<body>
    <h1>🏜️ Wüsten-Adventure</h1>
    <div id="connection-status" class="status">Verbinde...</div>

    <div class="grid">
        <div id="scene" class="panel">
            <h2>🌅 Aktuelle Szene</h2>
            <div id="scene-content">Lade Spiel...</div>
        </div>

        <div id="status" class="panel">
            <h2>👤 Status</h2>
            <div id="player-info">
                <div id="player-name">Spieler: Lade...</div>
                <div id="location">Ort: Lade...</div>
                <div id="thirst">Durst: <span id="thirst-value">40/40</span></div>
            </div>
            <h3>🎒 Inventar:</h3>
            <div id="inventory">Lade...</div>
        </div>

        <div id="environment" class="panel">
            <h2>🗺️ Umgebung</h2>
            <h3>📦 Objekte:</h3>
            <ul id="objects-list"><li>Lade...</li></ul>
            <h3>🚶 Wege:</h3>
            <ul id="ways-list"><li>Lade...</li></ul>
        </div>
    </div>

    <div id="last-action" class="panel">
        <h2>⚡ Letzte Aktion</h2>
        <div id="last-command"><strong>Kommando:</strong> <span id="command-text">Noch keine</span></div>
        <div id="last-result"><div id="result-text">Warte auf Verbindung...</div></div>
        <div class="debug-info" id="debug-info">Debug: Warte auf Verbindung...</div>
    </div>

    <div style="margin-top: 20px;">
        <input type="text" id="user-input" placeholder="Was möchtest du tun?" onkeypress="if(event.key==='Enter') sendCommand()" disabled>
        <button id="send-button" onclick="sendCommand()" disabled>Senden</button>
    </div>

    <script>
        console.log('🚀 Adventure startet...');

        let gameState = {
            round: 1,
            player: { name: "WebPlayer", location: "Start", thirst: 40, inventory: [] },
            environment: { objects: [], ways: [], blockedWays: [] },
            lastAction: { command: "Noch keine", result: "Warte auf Verbindung..." }
        };

        let backend = null;

        class AdventureBackend {
            constructor() {
                this.ws = null;
                this.connect();
            }

            connect() {
                const status = document.getElementById('connection-status');
                if (status) status.textContent = 'Verbinde...';

                try {
                    this.ws = new WebSocket('ws://localhost:8765');

                    this.ws.onopen = () => {
                        console.log('✅ Verbunden');
                        if (status) status.textContent = '🟢 Verbunden';
                        document.getElementById('user-input').disabled = false;
                        document.getElementById('send-button').disabled = false;
                    };

                    this.ws.onmessage = (event) => {
                        const data = JSON.parse(event.data);
                        this.handleMessage(data);
                    };

                    this.ws.onclose = () => {
                        console.log('🔌 Verbindung getrennt');
                        if (status) status.textContent = '🔴 Getrennt';
                        document.getElementById('user-input').disabled = true;
                        document.getElementById('send-button').disabled = true;
                    };

                } catch (error) {
                    console.error('❌ Verbindungsfehler:', error);
                    if (status) status.textContent = '❌ Fehler';
                }
            }

            sendCommand(command) {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'command', command: command }));
                }
            }

            handleMessage(data) {
                switch(data.type) {
                    case 'game_state':
                        this.updateGameState(data.data);
                        break;
                    case 'command_result':
                        if (data.results && data.results.length > 0) {
                            gameState.lastAction = {
                                command: data.command,
                                result: data.results[data.results.length - 1].result
                            };
                        }
                        if (data.game_state) this.updateGameState(data.game_state);
                        else updateUI();

                        // Debug-Info anzeigen
                        this.updateDebugInfo(data);
                        break;
                    case 'npc_actions':
                        if (data.actions && data.actions.length > 0) {
                            // Formatiere Explosions-Nachrichten speziell
                            let formattedActions = data.actions.map(action => {
                                if (action.includes('💥 EXPLOSION') || action.includes('KABUMM')) {
                                    return `<span class="explosion">${action}</span>`;
                                } else if (action.includes('💣 Timer') || action.includes('explodiert in')) {
                                    return `<span class="explosion-timer">${action}</span>`;
                                } else {
                                    return action;
                                }
                            });

                            gameState.lastAction = {
                                command: 'NPC-Aktionen',
                                result: formattedActions.join('\\n')
                            };
                        }
                        if (data.game_state) this.updateGameState(data.game_state);
                        else updateUI();
                        break;
                    case 'error':
                        gameState.lastAction = {
                            command: data.command || 'Fehler',
                            result: '❌ ' + data.message
                        };
                        updateUI();
                        break;
                }
            }

            updateGameState(newState) {
                Object.assign(gameState, newState);
                updateUI();

                if (newState.scene_description) {
                    const content = document.getElementById('scene-content');
                    if (content) content.innerHTML = newState.scene_description.replace(/\\n/g, '<br>');
                }
            }

            updateDebugInfo(data) {
                const debugInfo = document.getElementById('debug-info');
                if (debugInfo) {
                    const pendingCommands = data.pending_commands || 0;
                    const hasPendingInput = data.has_pending_input || false;
                    const executedCommand = data.executed_command || 'unknown';
                    const pendingPreview = data.pending_input_preview || '';

                    debugInfo.innerHTML = `Debug: Executed: <strong>${executedCommand}</strong>, Queue: ${pendingCommands}, Pending: ${hasPendingInput}` + 
                                         (pendingPreview ? `<br>Next: "${pendingPreview}"` : '');
                }
            }
        }

        function updateUI() {
            try {
                const playerName = document.getElementById('player-name');
                const location = document.getElementById('location');
                const thirstValue = document.getElementById('thirst-value');

                if (playerName) playerName.textContent = 'Spieler: ' + (gameState.player?.name || 'Unbekannt');
                if (location) location.textContent = 'Ort: ' + (gameState.player?.location || 'Unbekannt');
                if (thirstValue) thirstValue.textContent = (gameState.player?.thirst || 40) + '/40';

                const inventory = document.getElementById('inventory');
                if (inventory) {
                    const items = gameState.player?.inventory || [];
                    if (items.length === 0) {
                        inventory.innerHTML = '<em>Leer</em>';
                    } else {
                        inventory.innerHTML = items.map(item => '<div>• ' + item + '</div>').join('');
                    }
                }

                const objectsList = document.getElementById('objects-list');
                if (objectsList) {
                    const objects = gameState.environment?.objects || [];
                    if (objects.length === 0) {
                        objectsList.innerHTML = '<li><em>Keine Objekte</em></li>';
                    } else {
                        objectsList.innerHTML = objects.map(obj => '<li>' + obj + '</li>').join('');
                    }
                }

                const waysList = document.getElementById('ways-list');
                if (waysList) {
                    const ways = gameState.environment?.ways || [];
                    if (ways.length === 0) {
                        waysList.innerHTML = '<li><em>Keine Wege</em></li>';
                    } else {
                        waysList.innerHTML = ways.map(way => '<li>' + way + '</li>').join('');
                    }
                }

                const commandText = document.getElementById('command-text');
                const resultText = document.getElementById('result-text');

                if (commandText) commandText.textContent = gameState.lastAction?.command || 'Noch keine';
                if (resultText) resultText.innerHTML = (gameState.lastAction?.result || 'Warte...').replace(/\\n/g, '<br>');

            } catch (error) {
                console.error('❌ UI-Fehler:', error);
            }
        }

        function sendCommand() {
            const input = document.getElementById('user-input');
            if (!input) return;

            const command = input.value.trim();
            if (!command) return;

            input.value = '';

            if (backend) {
                backend.sendCommand(command);
            } else {
                console.error('❌ Kein Backend');
            }
        }

        document.addEventListener('DOMContentLoaded', function() {
            backend = new AdventureBackend();
            updateUI();
            setTimeout(() => {
                const input = document.getElementById('user-input');
                if (input) input.focus();
            }, 1000);
        });

        console.log('✅ Script geladen');
    </script>
</body>
</html>'''

    with open("adventure_web.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    dprint(dl.WEBGUI,"✅ Funktionierende HTML-Datei erstellt!")


def run_working_adventure():
    """Starte funktionierenden Web-Server"""
    dprint(dl.WEBGUI,"🏜️ Starte FUNKTIONIERENDEN Wüsten-Adventure Web-Server...")

    try:
        server = WebAdventureServer()
        server.start_server()
    except KeyboardInterrupt:
        dprint(dl.WEBGUI,"\n👋 Server beendet")
    except Exception as e:
        dprint(dl.WEBGUI,f"❌ Fehler: {e}")


if __name__ == "__main__":
    # Erstelle HTML-File
    create_working_html()
    run_working_adventure()