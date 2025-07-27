# Vollständige web_backend_server.py mit Mini-Game Integration
import asyncio
import json
import threading
import webbrowser
import time
from pathlib import Path
import random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Dict, Set
from collections import deque

from tornado import websocket

import Utils

Utils.ADV_LOGGER = Utils.dlogger()

from Utils import tw_print, dprint, dpprint, dl

txt_final_lost_text = """

################################

# An einem weit entfernten Ort #

################################


Eine schwarz gekleidete Gestalt lehnt sich in einem Ledersessel zurück und stößt mit einem leisen Hauchen beißenden Zigarettenrauch aus. Dann drückt sie die Zigarette langsam im Aschenbecher aus und fragt: „Ist der Bote gekommen?“


„Ich fürchte nicht“, erwidert eine zweite Gestalt, die am anderen Ende des Raumes in einem Sessel der bequemen Sitzecke sitzt und gemächlich an einem Glas mit goldenem Whiskey nippt.


„Das war zu befürchten.“ – „Ja … und nun?“


Die erste Gestalt erhebt sich und verschränkt die Hände hinter dem Rücken. Nach kurzem Überlegen sagt sie ruhig: „Wie geplant. Es bleibt leider keine andere Wahl.“


Die zweite Gestalt nickt wortlos. Gemeinsam treten sie zu einem Schaltpult in der Ecke des Raumes.


Jeder steckt einen Schlüssel in eines der beiden Schlüssellöcher und beide betätigen gleichzeitig den Schalter in der Mitte des Pultes.


*********************************

*** Dann geht die Welt unter. ***

*********************************

"""

txt_final_won_text = """

################################
# An einem weit entfernten Ort #
################################

Eine schwarz gekleidete Gestalt lehnt sich in einem Ledersessel zurück.
„Der Bote hat den Umschlag gebracht“, sagt sie und wedelt mit dem Umschlag.

„Das sind großartige Neuigkeiten!“, erwidert eine zweite Gestalt und erhebt sich aus einer bequemen Sitzecke am anderen Ende des Raumes. Einen Moment lang starren beide den Umschlag an. Dann öffnet ihn die erste Gestalt und zieht einen vergilbten Notizzettel hervor. Auf diesem sind in krakeliger Handschrift einige Zeichen gekritzelt.

Lange betrachten sie schweigend den Zettel.
Dann entspannen sich ihre Gesichtszüge.

„Damit ist die Bedrohung endgültig vorbei.“
„Gott sei Dank“, murmelt die erste Gestalt, zerknüllt den Zettel und wirft ihn in einen Papierkorb neben der Sitzecke.

Anschließend verlassen beide den Raum durch eine schwere, mit Leder gepolsterte Tür.

******************************
*** Die Welt ist gerettet! ***
******************************

"""


# Prüfe ob websockets installiert ist
try:
    import websockets
except ImportError:
    dprint(dl.WEBGUI, "❌ 'websockets' Package ist nicht installiert!")
    dprint(dl.WEBGUI, "Installiere es mit: pip install websockets")
    exit(1)

# Prüfe ob Game-Module verfügbar sind
try:
    from GameState import GameState
    from PlayerState import PlayerState

    GAME_MODULES_AVAILABLE = True
    dprint(dl.WEBGUI, "✅ Game-Module erfolgreich importiert")
except ImportError as e:
    dprint(dl.WEBGUI, f"⚠️  Game-Module nicht verfügbar: {e}")
    dprint(dl.WEBGUI, "⚠️  Verwende Demo-Modus")
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
            from functools import partial
            #
            # No Directory Listing
            #

            class NoListingHandler(SimpleHTTPRequestHandler):
                def list_directory(self, path):
                    self.send_error(403, "Verzeichnisauflistung nicht erlaubt")
                    return None
            try:
                handler = partial(NoListingHandler, directory="web")
                httpd = HTTPServer((self.host, self.http_port), handler)
                dprint(dl.WEBGUI, f"📄 HTTP Server bereit auf http://{self.host}:{self.http_port}")
                httpd.serve_forever()
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    dprint(dl.WEBGUI, f"⚠️  Port {self.http_port} ist bereits belegt. Verwende anderen Port.")
                    self.http_port += 1
                    self.start_http_server()
                else:
                    dprint(dl.WEBGUI, f"❌ HTTP Server Fehler: {e}")
            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Unerwarteter HTTP Server Fehler: {e}")

        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        time.sleep(0.5)

    async def register_client(self, websocket):
        """Registriere neuen Client"""
        self.connected_clients.add(websocket)
        session_id = str(id(websocket))

        dprint(dl.WEBGUI, f"🔌 Neuer Client verbunden: {session_id}")

        if GAME_MODULES_AVAILABLE:
            # Versuche echtes GameState zu verwenden
            try:
                dprint(dl.WEBGUI, f"🎮 Versuche echtes GameState zu erstellen...")
                game = GameState()

                # NEUE: Registriere Web-Session im GameState
                game.register_web_session(session_id, websocket)
                self.wd = game.web_sessions[session_id]["WebDialogs"]
                dprint(dl.WEBGUI, f"✅ GameState erstellt")

                # Spieler erstellen
                pname = await self.wd.ask_for_playername()
                player = PlayerState(pname, game.places["p_start"])
                player.session_id = session_id  # 👈 Spieler bekommt seine Session-ID
                game.players.append(player)

                # Umschlag hinzufügen
                if "o_umschlag" in game.objects:
                    player.add_to_inventory(game.objects["o_umschlag"])
                    dprint(dl.WEBGUI, f"✅ Umschlag hinzugefügt")

                dprint(dl.WEBGUI, f"✅ Spieler erstellt: {player.name} in {player.location.name}")

                # Versuche Hund hinzuzufügen
                try:
                    from NPCPlayerState import NPCPlayerState
                    dog = NPCPlayerState(name="Hund", location=game.places["p_geldautomat"])
                    game.players.append(dog)
                    dprint(dl.WEBGUI, f"✅ Hund hinzugefügt: {dog.name} in {dog.location.name}")
                    dprint(dl.WEBGUI, f"🎮 Spieler insgesamt: {len(game.players)}")
                except Exception as e:
                    dprint(dl.WEBGUI, f"⚠️  Hund konnte nicht hinzugefügt werden: {e}")

                # Konvertiere zu serialisierbarem Format - MIT initialer Narration
                game_state = self.serialize_real_game_state(game, update_narration=True, session_id=session_id)

                # Session mit Command-Queue und Pending-Input erstellen
                self.game_sessions[session_id] = {
                    "type": "real",
                    "game": game,
                    "state": game_state,
                    "cmd_q": deque(),  # Command queue wie in PlayerState
                    "pending_llm_input": None,  # Pending input wie in PlayerState
                    "minigame_active": False  # NEUE: Mini-Game Status
                }
                game.cmd_q = self.game_sessions[session_id]["cmd_q"]

                # Initialisiere Scene-Cache für diese Session
                if not hasattr(self, '_session_scene_cache'):
                    self._session_scene_cache = {}
                self._session_scene_cache[session_id] = game_state.get("scene_description", "")

            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Fehler beim echten GameState: {e}")
                dprint(dl.WEBGUI, f"⚠️  Verwende Demo-Modus als Fallback")
                game_state = self.create_demo_game_state()
                self.game_sessions[session_id] = {
                    "type": "demo",
                    "state": game_state,
                    "cmd_q": deque(),
                    "pending_llm_input": None,
                    "minigame_active": False
                }
                game.cmd_q = self.game_sessions[session_id]["cmd_q"]
        else:
            # Demo-Modus
            dprint(dl.WEBGUI, f"📱 Erstelle Demo-GameState...")
            game_state = self.create_demo_game_state()
            self.game_sessions[session_id] = {
                "type": "demo",
                "state": game_state,
                "cmd_q": deque(),
                "pending_llm_input": None,
                "minigame_active": False
            }


        # Sende initialen Zustand
        await self.send_game_state(websocket, self.game_sessions[session_id]["state"])
        dprint(dl.WEBGUI, f"✅ Client {session_id} initialisiert ({self.game_sessions[session_id]['type']} Modus)")

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
            "dog": {
                "location": "Geldautomat",
                "state": "Der Hund tut nichts... (Demo)"
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

    def serialize_real_game_state(self, game, update_narration=False, session_id=None):
        """Konvertiere echtes GameState zu JSON-Format"""
        from NPCPlayerState import NPCPlayerState
        try:
            player = game.players[0] if game.players else None
            if not player:
                return self.create_demo_game_state()

            # Finde Hund (kann None sein falls Hund eliminiert wurde)
            dog = next((d for d in game.players if type(d) is NPCPlayerState), None)

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

            # Szenenbeschreibung - NUR wenn explizit angefordert
            scene_description = "Du befindest dich an einem mysteriösen Ort."
            if update_narration:
                try:
                    if hasattr(game, 'llm') and game.llm and hasattr(game.llm, 'narrate'):
                        dprint(dl.WEBGUI, f"🎭 Generiere neue Szenenbeschreibung für {current_location.name}")
                        scene_description = game.llm.narrate(game, player)
                    elif hasattr(current_location, 'description'):
                        scene_description = current_location.description
                except Exception as e:
                    dprint(dl.WEBGUI, f"⚠️  Narration-Fehler: {e}")
                    scene_description = "Du befindest dich an einem geheimnisvollen Ort."

                # Cache die neue Beschreibung in der Session
                if session_id and hasattr(self, '_session_scene_cache'):
                    self._session_scene_cache[session_id] = scene_description
            else:
                # Verwende gecachte Beschreibung, falls vorhanden
                if session_id and hasattr(self, '_session_scene_cache') and session_id in self._session_scene_cache:
                    scene_description = self._session_scene_cache[session_id]
                    dprint(dl.WEBGUI, f"♻️  Verwende gecachte Szenenbeschreibung für Session {session_id}")
                else:
                    # Fallback: einfache Beschreibung ohne LLM
                    try:
                        if hasattr(current_location, 'description'):
                            scene_description = current_location.description
                    except:
                        pass

            # Hund-Informationen
            dog_info = {
                "location": "Unbekannt",
                "state": "Kein Hund im Spiel"
            }
            if dog:
                try:
                    dog_location = getattr(dog.location, 'callnames', ['Unbekannt'])
                    dog_info = {
                        "location": dog_location[0] if dog_location else 'Unbekannt',
                        "state": getattr(dog, 'dog_state_message', 'Der Hund tut nichts')
                    }
                except:
                    pass

            return {
                "round": getattr(game, 'time', 1),
                "game_over": getattr(game, 'game_over', False),
                "game_won": getattr(game, 'game_won', False),
                "player": {
                    "name": getattr(player, 'name', player.name),
                    "location": getattr(current_location, 'callnames', ['Unbekannt'])[0],
                    "thirst": getattr(player, 'thirst_counter', 40),
                    "inventory": [getattr(item, 'callnames', ['Unbekanntes Item'])[0]
                                  for item in getattr(player, 'inventory', [])]
                },
                "dog": dog_info,
                "environment": {
                    "objects": visible_objects,
                    "ways": available_ways,
                    "blockedWays": blocked_ways
                },
                "scene_description": scene_description
            }

        except Exception as e:
            dprint(dl.WEBGUI, f"❌ Fehler beim Serialisieren: {e}")
            return self.create_demo_game_state()

    async def unregister_client(self, websocket):
        """Client-Verbindung beenden"""
        self.connected_clients.discard(websocket)
        session_id = str(id(websocket))

        # NEUE: Entferne Web-Session auch aus GameState
        if session_id in self.game_sessions:
            session = self.game_sessions[session_id]
            if session["type"] == "real" and "game" in session:
                session["game"].unregister_web_session(session_id)
            del self.game_sessions[session_id]

        # Bereinige auch Scene-Cache für diese Session
        if hasattr(self, '_session_scene_cache') and session_id in self._session_scene_cache:
            del self._session_scene_cache[session_id]
            dprint(dl.WEBGUI, f"🧹 Scene-Cache für Session {session_id} bereinigt")

        dprint(dl.WEBGUI, f"👋 Client {session_id} getrennt")

    async def send_game_state(self, websocket, game_state):
        """Sende Game-State an Client"""
        try:
            message = {
                "type": "game_state",
                "data": game_state
            }
            await websocket.send(json.dumps(message))
            dprint(dl.WEBGUI, f"📤 Game-State gesendet")
        except Exception as e:
            dprint(dl.WEBGUI, f"❌ Fehler beim Senden: {e}")

    # ============== NEUE MINI-GAME FUNKTIONEN ==============

    def create_minigame_data(self, game_type):
        """Erstelle Spiel-spezifische Daten für Mini-Games"""
        if game_type == "sum_fight":
            # Generiere 10 Zufallszahlen wie in MiniGames.py
            stones = [random.randint(1, 10) for _ in range(10)]
            total_sum = sum(stones)
            max_stone = max(stones)

            # Zielzahl muss mindestens so groß wie der größte Stein sein
            reach = random.randint(max_stone, total_sum)

            # Münzwurf wer anfängt (0 = Hund, 1 = Spieler)
            who_starts = random.choice([0, 1])

            dprint(dl.WEBGUI, f"🎲 Sum Fight: stones={stones}, reach={reach}, starts={who_starts}")

            return {
                "stones": stones,
                "reach": reach,
                "whoStarts": who_starts
            }

        # Andere Spiele brauchen keine speziellen Daten
        return {}

    async def trigger_minigame(self, websocket, game_type):
        """Starte ein Mini-Game im Web-Interface"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            return

        session = self.game_sessions[session_id]

        # Markiere Mini-Game als aktiv
        session["minigame_active"] = True

        # Registriere Mini-Game im GameState falls verfügbar
        if session["type"] == "real" and "game" in session:
            game = session["game"]
            player = game.players[0] if game.players else None
            if player and hasattr(game, 'start_minigame_session'):
                game.start_minigame_session(session_id, game_type, player)

        # Erstelle Spiel-Daten
        game_data = self.create_minigame_data(game_type)

        # Sende Mini-Game-Aufforderung an Client
        message = {
            "type": "start_minigame",
            "game_type": game_type,
            "game_data": game_data
        }

        await websocket.send(json.dumps(message))
        dprint(dl.WEBGUI, f"🎮 Mini-Game gestartet: {game_type}")

    async def handle_minigame_result(self, websocket, data):
        """Verarbeite Ergebnis eines Mini-Games"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Keine aktive Spielsession"
            }))
            return

        session = self.game_sessions[session_id]
        game_type = data.get('game_type')
        result = data.get('result')  # 'WON', 'LOST', 'TIE'

        dprint(dl.WEBGUI, f"🎮 Mini-Game Ergebnis: {game_type} -> {result}")

        # Markiere Mini-Game als nicht mehr aktiv
        session["minigame_active"] = False

        # Konvertiere Web-Result zu MiniGames.py Format
        if session["type"] == "real" and GAME_MODULES_AVAILABLE:
            try:
                from NPCPlayerState import DogFight

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
                    await self.wd.do_game_over(game.game_won, txt)

                dog_fight_result = dog_result_map.get(result, DogFight.TIE)

                # Suche Hund in der Spielerliste und verarbeite Ergebnis
                game = session["game"]
                from NPCPlayerState import NPCPlayerState
                dog = next((p for p in game.players if isinstance(p, NPCPlayerState)), None)

                fight_message = "Mini-Game beendet"

                if dog and hasattr(dog, 'process_fight_result'):
                    # Übergebe Ergebnis direkt an Hund-Logik
                    fight_message = dog.process_fight_result(game, dog_fight_result)
                    dprint(dl.WEBGUI, f"✅ Fight result verarbeitet: {fight_message[:50]}...")

                # Beende Mini-Game Session im GameState
                if hasattr(game, 'complete_minigame_session'):
                    game.complete_minigame_session(session_id, result)

                # Sende Ergebnis an Client
                response = {
                    "type": "minigame_complete",
                    "game_type": game_type,
                    "result": result,
                    "message": fight_message,
                    "game_state": self.serialize_real_game_state(game, update_narration=False, session_id=session_id)
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
                'WON': f"***Hund gewinnt das {game_type}! (Demo)***",
                'LOST': f"***Du gewinnst das {game_type}! (Demo)***",
                'TIE': f"***{game_type} endet unentschieden! (Demo)***"
            }

            response = {
                "type": "minigame_complete",
                "game_type": game_type,
                "result": result,
                "message": demo_messages.get(result, "Mini-Game beendet (Demo)"),
                "game_state": session["state"]
            }

            await websocket.send(json.dumps(response))

    # ============== ERWEITERTE COMMAND HANDLING ==============

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
        command_to_execute = None

        # Schritt 1: Prüfe ob Commands in Queue vorhanden sind
        if session["cmd_q"]:
            # Es gibt bereits Commands in der Queue - nimm das nächste
            command_to_execute = session["cmd_q"].popleft()
            dprint(dl.WEBGUI, f"🔄 Führe Command aus Queue aus: {command_to_execute['function_call']['name']}")
        else:
            # Schritt 2: Keine Commands in Queue - hole User Input
            user_input = None

            # Prüfe pending input zuerst
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
            if user_input.lower() in ["quit", "inventory", "dogstate", "nichts", "context", "toggle_layout","pinpad"]:
                # Direkte Commands ohne LLM-Parsing
                if user_input.lower().startswith("pinpad"):
                    hash = "81dc9bdb52d04dc20036dbd8313ed055"  # MD5 für 1234
                    pin_result = await self.wd.ask_for_pin(hash)
                    session["cmd_q"].append({
                        "function_call": {
                            "name": "zurueckweisen",
                            "args": {"why": f"PIN-Eingabe ergab: {pin_result}"}
                        }
                    })
                else:
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

                            dprint(dl.WEBGUI,
                                   f"🤖 LLM parsed {len(parsed_commands)} commands: {[cmd['function_call']['name'] for cmd in parsed_commands]}")

                            # Intercepte "rest-command" - GENAU wie in Player_game_move
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
            if session["cmd_q"]:
                command_to_execute = session["cmd_q"].popleft()
            else:
                dprint(dl.WEBGUI, "⚠️  Keine Commands verfügbar nach Verarbeitung")
                return

        # Schritt 5: Führe das Command aus
        dprint(dl.WEBGUI, f"▶️  Führe aus: {command_to_execute['function_call']['name']}")
        result = await self.execute_single_command(session, command_to_execute, session_id)

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
        dprint(dl.WEBGUI,
               f"✅ Command '{command_to_execute['function_call']['name']}' ausgeführt. Queue: {len(session['cmd_q'])}, Pending: {session['pending_llm_input'] is not None}")

        # Schritt 6.5: Sende NPC-Actions falls vorhanden
        if "pending_npc_actions" in session and session["pending_npc_actions"]:
            npc_actions = session["pending_npc_actions"]
            del session["pending_npc_actions"]  # Cleanup

            # NEUE: Prüfe auf Mini-Game Trigger in NPC-Actions
            filtered_actions = []
            for action in npc_actions:
                if 'MINIGAME:' in action:
                    # Extrahiere Mini-Game Type
                    game_type = action.split('MINIGAME:')[1].strip()
                    dprint(dl.WEBGUI, f"🎮 Mini-Game Trigger erkannt: {game_type}")

                    # Starte Mini-Game
                    await self.trigger_minigame(websocket, game_type)

                    # Ersetze die Nachricht durch einen Hinweis
                    filtered_actions.append(f"**🎮 Ein Kampf beginnt!** Bereite dich auf das {game_type}-Mini-Game vor!")
                else:
                    # Formatiere normale Nachrichten für bessere Unterscheidung
                    if '💥 EXPLOSION:' in action:
                        # Echte Explosion - markiere sie eindeutig
                        filtered_actions.append(action)
                    elif 'explodiert in' in action and 'Spielzügen' in action:
                        # Timer-Nachricht - markiere als Timer
                        filtered_actions.append(f"**💣 Timer:** {action}")
                    elif '**Hund:**' in action:
                        # Hund-Aktion bleibt wie sie ist
                        filtered_actions.append(action)
                    else:
                        # Andere NPC-Aktionen
                        filtered_actions.append(action)

            if filtered_actions:
                npc_message = {
                    "type": "npc_actions",
                    "actions": filtered_actions,
                    "game_state": session["state"]
                }
                await websocket.send(json.dumps(npc_message))
                dprint(dl.WEBGUI, f"💥 NPC-Actions gesendet: {len(filtered_actions)} Aktionen")

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

            # Narration nur bei vollständig abgearbeiteten Sätzen oder explizitem Umsehen
            update_narration = queue_empty or is_look_around

            if update_narration:
                dprint(dl.WEBGUI, f"🎭 Aktualisiere Narration (Queue leer: {queue_empty}, Umsehen: {is_look_around})")
            else:
                dprint(dl.WEBGUI,
                       f"♻️  Verwende gecachte Narration (Queue: {len(session['cmd_q'])}, Command: {func_name})")

            if session["type"] == "real" and GAME_MODULES_AVAILABLE:
                game = session["game"]
                player = game.players[0] if game.players else None

                if player and hasattr(game, 'verb_execute_json'):
                    # Durst-Logik - GENAU wie in Player_game_move
                    player.thirst_counter -= 1
                    thirst_message = ""
                    # ⬇️ Deine neue Behandlung VOR dem allgemeinen Aufruf
                    if func_name == "check_pinpad":
                        hash = args.get("hash", "")
                        pin_result = await self.wd.ask_for_pin(hash)

                        if pin_result == "OK":
                            game.objects["o_geld_dollar"].hidden = False
                            return "**Die Zahl stimmt!** Der Automat rattert und spuckt frische US-Dollar aus."
                        else:
                            return " --- Die Zahl ist falsch. ---"
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
                    if not game.game_over:
                        result = game.verb_execute_json(player, command_dict)
                    #
                    # game_over kann durch Verdursten oder durch irgendwelche Aktionen bei verb_execute kommen
                    #
                    if game.game_over:
                        txt = f"""
{thirst_message}
                        
{result}
                        
{txt_final_won_text if game.game_won else txt_final_lost_text}
"""

                        await self.do_game_over(session_id,game.game_won,txt)

                    # Füge Durst-Nachricht hinzu, falls vorhanden
                    if thirst_message:
                        result = f"{result}\n\n{thirst_message}"

                    if hasattr(game, 'time'):
                        game.time += 1

                    # Update game state - MIT Narration nur bei Bedarf
                    session["state"] = self.serialize_real_game_state(game, update_narration=update_narration,
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
            dprint(dl.WEBGUI, f"❌ Fehler beim Ausführen von Command: {e}")
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

    async def collect_npc_actions(self, game, session_id=None):
        """Sammle NPC-Aktionen OHNE sie zu senden - für später in handle_command"""
        try:
            from NPCPlayerState import NPCPlayerState
            # Versuche auch ExplosionState zu importieren
            try:
                from ExplosionState import ExplosionState
                EXPLOSION_AVAILABLE = True
            except ImportError:
                EXPLOSION_AVAILABLE = False
                dprint(dl.WEBGUI, "⚠️  ExplosionState nicht verfügbar")

            npc_actions = []
            players_to_remove = []  # Für Spieler die durch Explosion eliminiert werden

            for npc in game.players:
                if isinstance(npc, NPCPlayerState):
                    # Normaler NPC (Hund)
                    npc_input = npc.NPC_game_move(game)
                    if npc_input and npc_input != "nichts":
                        if "MINIGAME" not in npc_input:
                            npc_result = game.verb_execute(npc, npc_input)
                            if npc_result and npc_result.strip():
                                npc_actions.append(f"**{npc.name}:** {npc_result}")
                        else:
                            #
                            # Initiate Minigame in web GUI
                            #
                            npc_actions.append(npc_input)

                elif EXPLOSION_AVAILABLE and isinstance(npc, ExplosionState):
                    # Explosion-NPC - VEREINFACHT
                    dprint(dl.WEBGUI, f"💥 Sammle Explosion: Timer={npc.kaboom_timer}")

                    # ExplosionState.explosion_input() macht ALLES und gibt Nachrichten zurück
                    explosion_messages = npc.explosion_input(game)

                    # Verwende die Nachrichten direkt (keine verb_execute nötig!)
                    if explosion_messages and explosion_messages != "nichts":
                        npc_actions.append(f"**💥 EXPLOSION:** {explosion_messages}")
                        dprint(dl.WEBGUI, f"💥 Explosion-Messages gesammelt: {len(explosion_messages)} Zeichen")

                    # Prüfe ob die Explosion abgelaufen ist (kaboom_timer = 0 nach explosion_input)
                    if npc.kaboom_timer <= 0:
                        dprint(dl.WEBGUI, "💥 Explosion ist abgelaufen - entferne ExplosionState")
                        players_to_remove.append(npc)

            # Entferne abgelaufene Explosionen
            for player in players_to_remove:
                if player in game.players:
                    game.players.remove(player)
                    dprint(dl.WEBGUI, f"🗑️  {player.name} aus Spielerliste entfernt")

            # Update game state nach NPC-Aktionen - OHNE Narration (da schon gemacht)
            if session_id and hasattr(self, 'game_sessions') and session_id in self.game_sessions:
                session = self.game_sessions[session_id]
                session["state"] = self.serialize_real_game_state(game, update_narration=False, session_id=session_id)

            return npc_actions

        except Exception as e:
            dprint(dl.WEBGUI, f"⚠️  NPC-Sammeln-Fehler: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ============== CLIENT HANDLING ==============

    async def handle_client(self, websocket):
        """Handle einzelne Client-Verbindung - ERWEITERT für Mini-Games"""
        try:
            await self.register_client(websocket)

            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get('type')

                    if message_type == 'command':
                        await self.handle_command(websocket, data)
                    elif message_type == 'minigame_result':  # NEUE
                        await self.handle_minigame_result(websocket, data)
                    elif message_type == 'ping':
                        await websocket.send(json.dumps({"type": "pong"}))
                    else:
                        dprint(dl.WEBGUI, f"⚠️ Unbekannter Message-Type: {message_type}")

                except json.JSONDecodeError as e:
                    dprint(dl.WEBGUI, f"❌ JSON-Fehler: {e}")
                except Exception as e:
                    dprint(dl.WEBGUI, f"❌ Fehler beim Verarbeiten: {e}")

        except websockets.exceptions.ConnectionClosed:
            dprint(dl.WEBGUI, "🔌 Client-Verbindung normal geschlossen")
        except Exception as e:
            dprint(dl.WEBGUI, f"❌ Unerwarteter Fehler: {e}")
        finally:
            await self.unregister_client(websocket)

    async def start_websocket_server(self):
        """Starte WebSocket-Server"""
        dprint(dl.WEBGUI, f"🔌 WebSocket Server startet auf ws://{self.host}:{self.websocket_port}")

        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.websocket_port
        )

        dprint(dl.WEBGUI, f"✅ WebSocket Server bereit auf ws://{self.host}:{self.websocket_port}")
        await server.wait_closed()

    def start_server(self):
        """Starte Server"""
        dprint(dl.WEBGUI, f"🌐 Browser wird geöffnet auf: http://{self.host}:{self.http_port}")
        dprint(dl.WEBGUI, f"💡 Game-Module verfügbar: {'✅ Ja' if GAME_MODULES_AVAILABLE else '❌ Nein (Demo-Modus)'}")
        dprint(dl.WEBGUI, f"🎮 Mini-Game Support: ✅ Aktiviert")
        dprint(dl.WEBGUI, f"{'=' * 60}")

        time.sleep(1)

        try:
            webbrowser.open(f"http://{self.host}:{self.http_port}")
        except Exception as e:
            dprint(dl.WEBGUI, f"⚠️ Konnte Browser nicht öffnen: {e}")

        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            dprint(dl.WEBGUI, f"\n👋 Server beendet")

    import re

    def clean_game_over_text(self,text):
        import re
        """Bereinigt Text für optimale Darstellung im Game-Over-Screen"""
        # 1. Normalisiere Zeilenenumbrüche
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 2. Entferne Leerzeichen am Zeilenanfang/-ende jeder Zeile
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # 3. Reduziere mehrfache Leerzeilen auf maximal eine
        #text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # 4. Entferne führende/trailing Leerzeilen
        text = text.strip()

        return text

    async def do_game_over(self, session_id, won:bool, text:str):
        dprint(dl.WEBGUI,"Ending game with explicit command")
        text = self.clean_game_over_text(text)
        try:
            # WebSocket aus der Session holen
            if session_id in self.game_sessions:
                session = self.game_sessions[session_id]
                if session["type"] == "real" and "game" in session:
                    game = session["game"]
                    # WebSocket aus game.web_sessions holen (falls registriert)
                    if hasattr(game, 'web_sessions') and session_id in game.web_sessions:
                        websocket = game.web_sessions[session_id]["websocket"]
                        await websocket.send(json.dumps({"type": "game_over", "text": text, "won": won}))
                        dprint(dl.WEBGUI,"Sent game_over message to client")
                        return

            dprint(dl.WEBGUI, "❌ WebSocket für Game-Over nicht gefunden")
        except Exception as e:
            dpprint(dl.WEBGUI,e)







def run_working_adventure():
    """Starte funktionierenden Web-Server mit Mini-Game Support"""
    dprint(dl.WEBGUI, "🏜️ Starte ERWEITERTEN Wüsten-Adventure Web-Server mit Mini-Games...")

    try:
        server = WebAdventureServer()
        server.start_server()
    except KeyboardInterrupt:
        dprint(dl.WEBGUI, "\n👋 Server beendet")
    except Exception as e:
        dprint(dl.WEBGUI, f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":

    run_working_adventure()