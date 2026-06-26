"""
This file contains class WebDialogs, which calls individual
Dialogs on the Web interface and returns their return values
"""
from __future__ import annotations
import json
import re
import random
import player_state
import npc_zombie_state
import game_state

#from websockets.legacy.server import WebSocketServerProtocol

from utils import dl, dprint, dpprint


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

    # ============== Zombie/Player-Interaction ==============

    async def do_chat(self, gs, pl, whom, firstmessage=""):
        """
        pl: Player Object which started the conversation (actually not needed)
        who: Player Object which is addressed in the conversation

        We assume, that any validity checks (for example pl and who in the same location) have
        already taken place

        """
        if not isinstance(pl, player_state.PlayerState) or hasattr(pl, 'zombie_state') or hasattr(pl, 'dog_state'):
            #
            # pl is not a human player - check if whom is, then swap
            #

            if not isinstance(whom, player_state.PlayerState) or hasattr(whom, 'zombie_state') or hasattr(whom, 'dog_state'):
                # Neither is a human player - can't do web chat
                return
            #
            # Swap so pl is always the human player (who has the WebSocket)
            #

            t = whom
            whom = pl
            pl = t

        n1 = whom.name
        n2 = pl.name

        start_chat_message = {
            "type": "zombie_chat",
            "who": n1,
            "whom": n2,
            "firstmsg": firstmessage,  # NEU!!
        }
        #
        # An das GUI senden, wo es dann (in JavaScript) weiterverarbeitet wird
        #
        chat_running = True
        last_chat=None
        zahler = 1
        await self.ws.send(json.dumps(start_chat_message))
        while chat_running:
            async for m in self.ws:
                data = json.loads(m)
                closeChat = data.get('closeChat',None)
                if closeChat:
                    chat_running = False
                    ls_chat = data.get('zombiechat', None)
                    whom.end_chat(gs.llm,ls_chat if ls_chat else last_chat)
                    # Log zombie state transition if applicable
                    if hasattr(whom, 'zombie_state'):
                        from npc_zombie_state import ZombieState
                        dprint(dl.WEBGUI, f"Zombie state after chat: {whom.zombie_state}")
                        if whom.zombie_state == ZombieState.COOPERATING:
                            dprint(dl.WEBGUI, "Zombie transitioned to COOPERATING after dialog!")
                    break
                else:
                    chat = data.get("zombiechat",None)
                    if chat:
                        r = whom.chat(gs.llm,chat)
                        last_chat = chat
                    await self.ws.send(json.dumps({"zombiemessage":r}))
                    zahler += 1

        #
        # await self.ws.send(...), dann ws auswerten (for m in ws: msg = json.loads(m), m enthält die message
        #



        return "True"