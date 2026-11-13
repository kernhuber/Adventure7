# WebAdventureServer: WebSocket/HTTP backend for the web GUI (Mini-Game Integration).
# Formerly web_backend_server.py; relocated into the webserver/ package (Step 1 refactor).
import asyncio
import json
import webbrowser
import time
import sys
import os
from pathlib import Path
import random
from typing import Set
from collections import deque

from webserver.http_server import start_http_server
from webserver.serialization import serialize_real_game_state
from webserver.demo import create_demo_game_state
from webserver.session import SessionManager
from webserver.npc_runner import NPCRunnerMixin
from webserver.command_engine import CommandEngineMixin

from tornado import websocket

import utils
import traceback

utils.ADV_LOGGER = utils.dlogger()


from utils import dprint, dl

# Adapter für LLM-Client Gemini importieren
from services.adapters import LLMClientGemini


# Prüfe ob websockets installiert ist
try:
    import websockets
except ImportError:
    dprint(dl.WEBGUI, "❌ 'websockets' Package ist nicht installiert!")
    dprint(dl.WEBGUI, "Installiere es mit: pip install websockets")
    exit(1)

# Game-Module (oder Demo-Fallback) zentral aus game_modules beziehen
from webserver.game_modules import GAME_MODULES_AVAILABLE, GameState, PlayerState


class WebAdventureServer(CommandEngineMixin, NPCRunnerMixin):
    def __init__(self, host='localhost', websocket_port=8765, http_port=8000):
        self.host = host
        self.websocket_port = websocket_port
        self.http_port = http_port

        # Game instances per session
        self.game_sessions = SessionManager()
        self.connected_clients: Set = set()

        # Start HTTP server for static files; remember the port actually bound.
        self.http_port = start_http_server(self.host, self.http_port)

    async def register_client(self, websocket):
        """Registriere neuen Client"""
        self.connected_clients.add(websocket)
        session_id = str(id(websocket))

        dprint(dl.WEBGUI, f"🔌 Neuer Client verbunden: {session_id}")

        # Agentenmodus: Browser verbindet sich mit ws://host:port/?mode=agent[&player=llm|fake|skript][&save=<slot>]
        # (siehe docs/AGENT-SPIELER-PLAN.md). Sonst spielt wie bisher ein Mensch.
        agent_mode, agent_player_type, agent_save, agent_tip = self._agent_request(websocket)
        agent_state, agent_messages = None, []   # aus einem geladenen Spielstand (Meldungen gehen an den Browser)
        human_load = None if agent_mode else self._load_request(websocket)   # ?load=<slot>: Mensch ab Spielstand

        if GAME_MODULES_AVAILABLE:
            # Versuche echtes GameState zu verwenden
            try:
                dprint(dl.WEBGUI, f"🎮 Versuche echtes GameState zu erstellen...")
                from services.llm_factory import make_llm
                llm = make_llm()   # wählt Gemini/Gemma gemäß utils.LLM_BACKEND
                game = GameState(llm=llm)

                # WebDialogs (PlayerDialogs port) is owned by the web layer now.
                from web_dialogs import WebDialogs
                if agent_mode:
                    # LERNPUNKT: nur das Dialog-Objekt wird ausgetauscht, die Engine bleibt gleich.
                    from agent_player.dialogs import AgentDialogs
                    wd = AgentDialogs(websocket, session_id)
                else:
                    wd = WebDialogs(websocket, session_id)
                dprint(dl.WEBGUI, f"✅ GameState erstellt")

                # Spieler erstellen
                # Beim Laden eines Spielstands entfällt die Namensabfrage (der Spielername kommt aus dem Spielstand).
                pname = "Spieler" if human_load else await wd.ask_for_playername()
                player = PlayerState(pname, game.places["p_start"])
                player.session_id = session_id  # 👈 Spieler bekommt seine Session-ID
                game.players.append(player)

                # Umschlag hinzufügen
                if "o_umschlag" in game.objects:
                    player.add_to_inventory(game.objects["o_umschlag"])
                    dprint(dl.WEBGUI, f"✅ Umschlag hinzugefügt")

                dprint(dl.WEBGUI, f"✅ Spieler erstellt: {player.name} in {player.location.name}")

                # Versuche Hund hinzuzufügen
                from utils import GHOSTMODE, NODOG
                if not GHOSTMODE:
                    if not NODOG:
                        try:
                            from npc_dog_state import NPCDogState
                            dog = NPCDogState(name="Hund", location=game.places["p_geldautomat"])
                            game.players.append(dog)
                            dprint(dl.WEBGUI, f"✅ Hund hinzugefügt: {dog.name} in {dog.location.name}")
                            dprint(dl.WEBGUI, f"🎮 Spieler insgesamt: {len(game.players)}")
                        except Exception as e:
                            dprint(dl.WEBGUI, f"⚠️  Hund konnte nicht hinzugefügt werden: {e}")
                    else:
                        dprint(dl.WEBGUI,"Kein Hund hinzugefügt - NODOG Flag gesetzt")
                else:
                    dprint(dl.WEBGUI,"Kein Hund hinzugefügt - GHOSTMODE")

                # Agentenmodus mit &save=<slot>: Spielstand samt Agentenzustand laden (Format wird geprüft).
                if agent_mode and agent_save:
                    from agent_player import savestate
                    loaded, agent_state, agent_messages = savestate.load_game(agent_save, llm)
                    if loaded is not None:
                        game = loaded
                        player = game.players[0]
                        player.session_id = session_id

                # Mensch mit ?load=<slot>: Spielstand laden und die frisch gebaute Welt ersetzen.
                if human_load:
                    try:
                        from services.save_load import load_from_file
                        from agent_player.savestate import path_for
                        game = load_from_file(path_for(human_load), llm=llm)
                        player = game.players[0]
                        player.session_id = session_id
                        agent_messages.append(f"📂 Spielstand '{human_load}' geladen.")
                    except Exception as e:
                        dprint(dl.WEBGUI, f"Load-Fehler: {e}")
                        agent_messages.append(f"❌ Laden von '{human_load}' fehlgeschlagen ({e}) – es startet ein neues Spiel.")

                # Konvertiere zu serialisierbarem Format - MIT initialer Narration
                game_state = serialize_real_game_state(game, session_id=session_id)

                # Session mit Command-Queue und Pending-Input erstellen.
                # WebDialogs und Scene-Cache gehören zur Session (früher fälschlich
                # serverweit in self.wd / self._session_scene_cache gehalten, was
                # zwischen gleichzeitigen Clients überschrieben wurde).
                session = {
                    "type": "real",
                    "game": game,
                    "state": game_state,
                    "cmd_q": deque(),  # Command queue wie in PlayerState
                    "pending_llm_input": None,  # Pending input wie in PlayerState
                    "minigame_active": False,  # NEUE: Mini-Game Status
                    "web_dialogs": wd,
                    "scene_cache": game_state.get("scene_description", ""),
                }
                if agent_mode:
                    # Der Runner spielt die Züge; session["tap"] (None = aus) schneidet mit, was der Browser bekommt.
                    from agent_player.runner import AgentRunner
                    session["tap"] = None
                    session["agent"] = AgentRunner(self, websocket, session, session_id, agent_player_type, agent_state, agent_tip)
                self.game_sessions[session_id] = session
                game.cmd_q = session["cmd_q"]

            except Exception as e:
                dprint(dl.WEBGUI, f"❌ Fehler beim echten GameState: {e}")
                traceback.print_exc()
                dprint(dl.WEBGUI, f"⚠️  Verwende Demo-Modus als Fallback")
                game_state = create_demo_game_state()
                # Kein game.cmd_q hier: das echte GameState ist evtl. gar nicht
                # zustande gekommen ('game' kann in diesem except undefiniert sein).
                self.game_sessions[session_id] = {
                    "type": "demo",
                    "state": game_state,
                    "cmd_q": deque(),
                    "pending_llm_input": None,
                    "minigame_active": False,
                    "web_dialogs": None,
                    "scene_cache": game_state.get("scene_description", ""),
                }
        else:
            # Demo-Modus
            dprint(dl.WEBGUI, f"📱 Erstelle Demo-GameState...")
            game_state = create_demo_game_state()
            self.game_sessions[session_id] = {
                "type": "demo",
                "state": game_state,
                "cmd_q": deque(),
                "pending_llm_input": None,
                "minigame_active": False,
                "web_dialogs": None,
                "scene_cache": game_state.get("scene_description", ""),
            }


        # Sende initialen Zustand
        await self.send_game_state(websocket, self.game_sessions[session_id]["state"])
        for notice in agent_messages:                # z. B. "Spielstand geladen" oder eine Formatwarnung
            await websocket.send(json.dumps({"type": "info", "message": notice}))
        dprint(dl.WEBGUI, f"✅ Client {session_id} initialisiert ({self.game_sessions[session_id]['type']} Modus)")

    @staticmethod
    def _agent_request(websocket) -> tuple[bool, str, str | None, str]:
        """Liest aus der WebSocket-URL, ob der Agent spielen soll (?mode=agent), wer spielt
        (&player=llm|fake|skript, Standard llm), ob ab einem Spielstand gestartet wird (&save=<slot>) und einen
        optionalen ersten Hinweis an den Agenten (&tipp=<text>).
        Ohne Query oder mit anderem Modus spielt ein Mensch."""
        from urllib.parse import urlparse, parse_qs
        try:
            query = parse_qs(urlparse(websocket.request.path).query)
        except Exception:
            return False, "llm", None, ""
        if query.get("mode", [""])[0] != "agent":
            return False, "llm", None, ""
        spieler = query.get("player", ["llm"])[0]
        save = query.get("save", [""])[0].strip() or None
        tipp = query.get("tipp", [""])[0].strip()[:500]
        return True, (spieler if spieler in ("llm", "fake", "skript") else "llm"), save, tipp

    @staticmethod
    def _load_request(websocket) -> str | None:
        """Menschlicher Spieler ab Spielstand: ws://host:port/?load=<slot> (aus dem Welcome-Screen)."""
        from urllib.parse import urlparse, parse_qs
        try:
            return parse_qs(urlparse(websocket.request.path).query).get("load", [""])[0].strip() or None
        except Exception:
            return None

    async def unregister_client(self, websocket):
        """Client-Verbindung beenden"""
        self.connected_clients.discard(websocket)
        session_id = str(id(websocket))

        if session_id in self.game_sessions:
            runner = self.game_sessions[session_id].get("agent")
            if runner is not None:
                runner.close()
            del self.game_sessions[session_id]

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
                    #elif message_type == 'minigame_result':  # NEUE
                    #    await self.handle_minigame_result(websocket, data)
                    elif message_type == 'agent_control':
                        # Steuerung des Agenten (Start/Pause/Einzelschritt/...) aus dem Zuschauer-Panel.
                        runner = self.game_sessions[str(id(websocket))].get("agent")
                        if runner is not None:
                            await runner.handle_control_command(data)
                    elif message_type == 'list_slots':
                        # GUI "Laden"-Button fragt die vorhandenen Spielstände ab.
                        from webserver.command_engine import _list_slots
                        await websocket.send(json.dumps({"type": "slot_list", "slots": _list_slots()}))
                    elif message_type == 'ping':
                        await websocket.send(json.dumps({"type": "pong"}))
                    else:
                        dprint(dl.WEBGUI, f"⚠️ Unbekannter Message-Type: {message_type}")

                except json.JSONDecodeError as e:
                    dprint(dl.WEBGUI, f"❌ JSON-Fehler: {e}")
                except Exception as e:
                    dprint(dl.WEBGUI, f"❌ Fehler beim Verarbeiten: {e}")
                    traceback.print_exc()

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