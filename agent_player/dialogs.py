"""AgentDialogs: ersetzt WebDialogs, wenn der Agent statt eines Menschen spielt.

LERNPUNKT: Die Engine fragt den Spieler nur über dieses "Dialog-Port"-Objekt
(Name, PIN, Minispiel, Chat, Game Over). Deshalb genügt es, das Objekt auszutauschen –
Engine und NPCs merken nicht, dass kein Mensch tippt. Wir erben von WebDialogs, damit
alles, was der Agent NICHT ersetzt (z. B. das Game-Over-Popup), wie bisher im Browser erscheint.
"""
import asyncio
import json
import random

from web_dialogs import WebDialogs
from utils import dprint, dl
from agent_player import config


class AgentDialogs(WebDialogs):
    ctx = None   # AgentContext; setzt der Runner, sobald der Agent spielt (ohne ihn: Platzhalter-Verhalten)

    async def ask_for_playername(self) -> str:
        return config.AGENT_PLAYER_NAME

    async def do_minigame(self) -> str:
        """Kein Minispiel im Agentenmodus: das Ergebnis wird einfach gewürfelt.

        'WON' bedeutet (wie in handle_minigame_result): der HUND gewinnt."""
        result = random.choices(["WON", "LOST", "TIE"], weights=config.MINIGAME_WEIGHTS)[0]
        dprint(dl.WEBGUI, f"🎲 Agentenmodus: Minispiel ersetzt durch Zufall -> {result}")
        # Der Browser zeigt den Kampf als Overlay (web/dogfight_overlay.js). Wir warten, bis es vorbei ist -
        # sonst käme z. B. das Game-Over-Popup schon während des Kampfes.
        await self.ws.send(json.dumps({"type": "agent_dogfight", "result": result}))
        await asyncio.sleep(config.DOGFIGHT_DURATION_S)
        return result

    async def ask_for_pin(self, expected_md5_hash: str) -> str:
        """Das PIN-Pad bedient der Agent selbst (pin.py); ohne Agent mit Modell bleibt das Pad unlösbar."""
        if self.ctx is None:
            await self._info("🔐 PIN-Pad: hier spielt kein Agent mit Modell – die PIN kann nicht eingegeben werden.")
            return "FAIL"
        from agent_player.pin import solve_pinpad
        return await solve_pinpad(self.ctx, expected_md5_hash)

    async def do_chat(self, gs, pl, whom, firstmessage=""):
        """Das Gespräch führt der Agent selbst (chat.py). Das Chat-Modal im Browser ist nur Zuschauer.

        Wie in WebDialogs.do_chat kann `pl` ein NPC sein (NPC-initiiertes Gespräch, z. B. beim Erwachen des
        Zombies) – dann ist `firstmessage` dessen Eröffnung, sonst die erste Äußerung des Agenten."""
        from agent_player.chat import run_conversation
        npc_start, agent_start = "", firstmessage
        if hasattr(pl, "zombie_state") or hasattr(pl, "dog_state"):
            pl, whom = whom, pl
            npc_start, agent_start = firstmessage, ""
        if self.ctx is None:
            await self._info(f"💬 {pl.name} möchte reden – hier spielt kein Agent mit Modell, das Gespräch entfällt.")
            return "True"

        await self.ws.send(json.dumps({"type": "zombie_chat", "who": whom.name, "whom": pl.name,
                                       "firstmsg": npc_start, "readonly": True}))

        async def show(speaker: str, text: str) -> None:
            if speaker == "agent":
                await self.ws.send(json.dumps({"type": "agent_chat_line", "text": text}))
            else:
                await self.ws.send(json.dumps({"zombiemessage": text}))    # wie bei einem menschlichen Spieler

        async def npc_reply(chat: list[dict]) -> str:
            # whom.chat ruft das (synchrone) NPC-LLM: im Thread, damit der Server nicht blockiert.
            return await asyncio.to_thread(whom.chat, gs.llm, list(chat))

        chat = await run_conversation(self.ctx, whom.name, npc_reply, show, npc_start, agent_start)
        await self.ws.send(json.dumps({"type": "agent_chat_end"}))
        await asyncio.to_thread(whom.end_chat, gs.llm, chat)               # Vertrauen/Gedächtnis des NPC, unverändert
        if hasattr(whom, "zombie_state"):
            dprint(dl.WEBGUI, f"Zombie state after chat: {whom.zombie_state} (trust={getattr(whom, 'trust', '?')})")
        return "True"

    async def _info(self, text: str) -> None:
        await self.ws.send(json.dumps({"type": "info", "message": text}))
