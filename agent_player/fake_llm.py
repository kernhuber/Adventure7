"""Fake-Modell: liefert vorgegebene Antworten, ohne Netz und ohne KI.

Zwei Zwecke:
  1. Test: die Schleife (loop.py) lässt sich ohne Google-SDK und ohne Kosten prüfen.
  2. Lehrmaterial: "So sieht die Schleife ohne KI aus" – die Schleife ist genau dieselbe,
     nur kommen die Werkzeugaufrufe aus einer Liste statt aus einem Modell.
"""
from agent_player.llm import AgentLLM, ModelReply, ToolCall, Message
from agent_player.tools import ToolSpec


class FakeAgentLLM(AgentLLM):
    model = "fake"

    def __init__(self, responses: list[ModelReply]):
        self.responses = list(responses)

    async def ask(self, system: str, messages: list[Message], tools: list[ToolSpec]) -> ModelReply:
        if self.responses:
            return self.responses.pop(0)
        return ModelReply(text="(Das Fake-Skript ist zu Ende – ich warte nur noch.)",
                       calls=[ToolCall("abwarten", {"warum": "Skript zu Ende"})])


def _move(name: str, why: str, **args) -> ToolCall:
    return ToolCall(name, {**args, "warum": why})


# Spielt am Spielanfang: freie Aktionen, einen Fehler (kostet keine Runde), dann echte Züge.
DEMO_REPLIES: list[ModelReply] = [
    ModelReply(text="Ich verschaffe mir erst einen Überblick und notiere mir den Plan.",
            calls=[ToolCall("inventar_ansehen"),
                     ToolCall("notizbuch_schreiben", {"text": "Plan: Schuppen suchen, dort nach Hilfe für die Fahrradkette schauen."})]),
    ModelReply(text="Dorthin möchte ich gehen.", calls=[_move("gehen", "Ein Ort, den es nicht gibt – ein Fehler kostet keine Runde.", target="Mars")]),
    ModelReply(text="Dann eben zum Schuppen.", calls=[_move("gehen", "Im Schuppen gibt es vielleicht Hilfe.", target="Schuppen")]),
    ModelReply(text="Der Blumentopf sieht verdächtig aus.", calls=[_move("untersuchen", "Unter Blumentöpfen liegt oft etwas.", obj="Blumentopf")]),
    ModelReply(calls=[ToolCall("notizbuch_schreiben", {"text": "Unter dem Blumentopf liegt ein Schlüssel."}),
                     _move("nehmen", "Der Schlüssel könnte eine Tür öffnen.", obj="Schlüssel")]),
]

# Ein Modell, das sich verzettelt: nur freie Aktionen -> Aufruflimit -> neutraler Ersatzzug.
RAMBLING_REPLIES: list[ModelReply] = [ModelReply(calls=[ToolCall("notizbuch_lesen")]) for _ in range(20)]
