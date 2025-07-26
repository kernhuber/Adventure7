"""
This file contains class WebDialogs, which calls individual
Dialogs on the Web interface and returns their return values
"""

import json
import re
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