"""Die Agentenschleife OHNE Netz, OHNE KI und OHNE Spielengine – nur mit Fake-Modell und Fake-Welt.

Aufruf (aus dem Projektordner):
    ./venv/bin/python3 -m agent_player.fake_run            # Demo: freie Aktionen, Fehler, Züge
    ./venv/bin/python3 -m agent_player.fake_run verzettelt # Aufruflimit -> neutraler Ersatzzug
"""
import asyncio
import sys

from agent_player import config
from agent_player.context import AgentKontext
from agent_player.control import AgentSteuerung
from agent_player.fake_llm import FakeAgentLLM, DEMO_ANTWORTEN, VERZETTELT_ANTWORTEN
from agent_player.loop import spiele_runde
from agent_player.trace import Spur


class FakeWelt:
    """Winzige Kulisse mit zwei Orten, die dem Agenten dieselbe Sicht liefert wie der Browser."""

    def __init__(self):
        self.runde = 1
        self.ort = "Start"
        self.schluessel_gefunden = False

    def ansicht(self) -> dict:
        wege = {"Start": ["Schuppen"], "Schuppen": ["Start", "innen"]}.get(self.ort, [])
        objekte = ["Blumentopf"] + (["Schlüssel"] if self.schluessel_gefunden else []) if self.ort == "Schuppen" else []
        return {"round": self.runde, "player": {"location": self.ort, "thirst": 40, "inventory": ["Umschlag"]},
                "environment": {"objects": objekte, "ways": wege, "blockedWays": []},
                "scene_description": f"(Fake-Szene) Du bist am Ort {self.ort}.", "dog": {}, "zombie": {}}

    async def zug(self, function_call: dict) -> list[dict]:
        fc = function_call["function_call"]
        if fc["name"] == "gehe":
            self.ort = fc["args"]["direction"]
        if fc["name"] == "untersuche":
            self.schluessel_gefunden = True
        self.runde += 1
        return [{"type": "command_result", "results": [{"command": fc["name"], "result": f"(Fake) {fc['name']} {fc['args']}", "is_game_move": True}]}]


async def main(szenario: str) -> None:
    antworten = VERZETTELT_ANTWORTEN if szenario == "verzettelt" else DEMO_ANTWORTEN
    welt, spur = FakeWelt(), Spur()

    async def melde(nachricht: dict) -> None:
        spur.schreibe(nachricht)
        if nachricht["type"] == "agent_event":
            print(f"[{nachricht['kind']:5}] Runde {nachricht['round']} · {nachricht['tool']} {nachricht['args']}"
                  f"{' · warum: ' + nachricht['warum'] if nachricht.get('warum') else ''}\n         {nachricht['result']}")

    steuerung = AgentSteuerung(tempo_ms=0)
    steuerung.kommando("start")
    ctx = AgentKontext(FakeAgentLLM(antworten), steuerung, welt.ansicht, welt.zug, melde)
    for _ in range(4):
        ergebnis = await spiele_runde(ctx)
        print(f"--> Zug der Runde: {ergebnis.zug}{' (NEUTRAL, Limit!)' if ergebnis.neutral else ''}\n")
    print("Notizbuch:\n" + ctx.notizbuch.lesen())
    print(f"\nSpur: {spur.pfad} (Aufruflimit pro Runde: {config.MAX_AUFRUFE_PRO_RUNDE})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "demo"))
