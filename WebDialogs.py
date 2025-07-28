"""
This file contains class WebDialogs, which calls individual
Dialogs on the Web interface and returns their return values
"""

import json
import re
import random
#from websockets.legacy.server import WebSocketServerProtocol

from Utils import dl, dprint, dpprint


class WebDialogs:
    def __init__(self, ws: "WebSocketServerProtocol", session_id: str):
        self.ws = ws
        self.sid = session_id

    @staticmethod
    def clean_game_over_text(text: str) -> str:
        """Bereinigt Text für optimale Darstellung im Game-Over-Screen"""
        # 1. Normalisiere Zeilenumbrüche
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 2. Entferne Leerzeichen am Zeilenanfang/-ende jeder Zeile
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)

        # 3. Entferne führende/trailing Leerzeilen
        text = text.strip()

        return text

    async def do_game_over(self, won: bool, text: str):
        """Sendet ein Game-Over-Popup an den Web-Client"""
        dprint(dl.WEBGUI, "🎬 Ending game with explicit command")
        try:
            clean_text = self.clean_game_over_text(text)
            await self.ws.send(json.dumps({
                "type": "game_over",
                "text": clean_text,
                "won": won
            }))
            dprint(dl.WEBGUI, "✅ Sent game_over message to client")
        except Exception as e:
            dprint(dl.WEBGUI, "❌ Fehler beim Senden des Game-Over-Dialogs")
            dpprint(dl.WEBGUI, e)

    async def ask_for_pin(self, expected_md5_hash: str) -> str:
        try:
            await self.ws.send(json.dumps({
                "type": "pinpad",
                "hash": expected_md5_hash
            }))
            dprint(dl.WEBGUI, "🔐 PINPAD an Client gesendet")

            async for message in self.ws:
                data = json.loads(message)
                if data.get("type") == "pinpad_result":
                    result = data.get("result", "FAIL")
                    dprint(dl.WEBGUI, f"🔐 PINPAD Ergebnis empfangen: {result}")
                    return result
        except Exception as e:
            dpprint(dl.WEBGUI, e)
            return "FAIL"

    async def ask_for_playername(self) -> str:
        try:
            await self.ws.send(json.dumps({
                "type": "playername",
            }))
            dprint(dl.WEBGUI, "🔐 Frage den Spielername vom Client ab")

            async for message in self.ws:
                data = json.loads(message)
                if data.get("type") == "playername_result":
                    result = data.get("result", "WebPlayer")
                    dprint(dl.WEBGUI, f"🔐 playername - Ergebnis empfangen: {result}")
                    return result
        except Exception as e:
            dpprint(dl.WEBGUI, e)
            return "WebPlayer"

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

    async def trugger_minigame(self, websocket, player, game_type):
        """Starte ein Mini-Game im Web-Interface"""
        session_id = str(id(websocket))
        if session_id not in self.game_sessions:
            return

        session = self.game_sessions[session_id]

        # Markiere Mini-Game als aktiv
        #session["minigame_active"] = True

        # Registriere Mini-Game im GameState falls verfügbar

        self.start_minigame_session(session_id, game_type, player)

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

    async def hundle_minigame_result(self, websocket, data):
        """Verarbeite Ergebnis eines Mini-Games"""

        await self.ws.send(json.dumps({
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

    async def do_minigame(self)->str:
        try:
            game_types = ['circle_fight', 'sum_fight', 'odd_even_fight', 'close_fight']
            game_type = random.choice(game_types)
            game_data = self.create_minigame_data(game_type)
            await self.ws.send(
                json.dumps({
                    "type":"start_minigame",
                    "game_type": game_type,
                    "game_data": game_data
                })
            )
            async for message in self.ws:
                data = json.loads(message)
                if data.get("type") == "minigame_result":
                    result = data.get("result","TIE")
                    dprint(dl.WEBGUI,f"Recieved minigame result: {result}")
                    dpprint(dl.WEBGUI,data)
                    return result
            #
            # No valid answer found
            #
            return "TIE"
        except Exception as e:
            dprint(dl.WEBGUI,"Exeption executing do_minigame. Exception details:")
            dpprint(dl.WEBGUI,e)
            return "TIE"