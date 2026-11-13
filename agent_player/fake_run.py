"""Die Agentenschleife OHNE Netz, OHNE KI und OHNE Spielengine – nur mit Fake-Modell und Fake-Welt.

Aufruf (aus dem Projektordner):
    ./venv/bin/python3 -m agent_player.fake_run            # Demo: freie Aktionen, Fehler, Züge
    ./venv/bin/python3 -m agent_player.fake_run verzettelt # Aufruflimit -> neutraler Ersatzzug
"""
import asyncio
import sys

from agent_player import config
from agent_player.context import AgentContext
from agent_player.control import AgentController
from agent_player.fake_llm import FakeAgentLLM, DEMO_REPLIES, RAMBLING_REPLIES
from agent_player.loop import play_round
from agent_player.trace import Trace


class FakeWorld:
    """Winzige Kulisse mit zwei Orten, die dem Agenten dieselbe Sicht liefert wie der Browser."""

    def __init__(self):
        self.round_number = 1
        self.place = "Start"
        self.key_found = False

    def view(self) -> dict:
        way_list = {"Start": ["Schuppen"], "Schuppen": ["Start", "innen"]}.get(self.place, [])
        objects = ["Blumentopf"] + (["Schlüssel"] if self.key_found else []) if self.place == "Schuppen" else []
        return {"round": self.round_number, "player": {"location": self.place, "thirst": 40, "inventory": ["Umschlag"]},
                "environment": {"objects": objects, "ways": way_list, "blockedWays": []},
                "scene_description": f"(Fake-Szene) Du bist am Ort {self.place}.", "dog": {}, "zombie": {}}

    async def move(self, function_call: dict) -> list[dict]:
        fc = function_call["function_call"]
        if fc["name"] == "gehe":
            self.place = fc["args"]["direction"]
        if fc["name"] == "untersuche":
            self.key_found = True
        self.round_number += 1
        return [{"type": "command_result", "results": [{"command": fc["name"], "result": f"(Fake) {fc['name']} {fc['args']}", "is_game_move": True}]}]


async def main(scenario: str) -> None:
    responses = RAMBLING_REPLIES if scenario == "verzettelt" else DEMO_REPLIES
    world, trace = FakeWorld(), Trace()

    async def report(message: dict) -> None:
        trace.write(message)
        if message["type"] == "agent_event":
            print(f"[{message['kind']:5}] Runde {message['round']} · {message['tool']} {message['args']}"
                  f"{' · warum: ' + message['warum'] if message.get('warum') else ''}\n         {message['result']}")

    controller = AgentController(tempo_ms=0)
    controller.command("start")
    ctx = AgentContext(FakeAgentLLM(responses), controller, world.view, world.move, report)
    for _ in range(4):
        result = await play_round(ctx)
        print(f"--> Zug der Runde: {result.move}{' (NEUTRAL, Limit!)' if result.neutral else ''}\n")
    print("Notizbuch:\n" + ctx.notebook.read())
    print(f"\nSpur: {trace.file_path} (Aufruflimit pro Runde: {config.MAX_CALLS_PER_ROUND})")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "demo"))
