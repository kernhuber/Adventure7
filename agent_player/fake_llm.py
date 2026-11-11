"""Fake-Modell: liefert vorgegebene Antworten, ohne Netz und ohne KI.

Zwei Zwecke:
  1. Test: die Schleife (loop.py) lässt sich ohne Google-SDK und ohne Kosten prüfen.
  2. Lehrmaterial: "So sieht die Schleife ohne KI aus" – die Schleife ist genau dieselbe,
     nur kommen die Werkzeugaufrufe aus einer Liste statt aus einem Modell.
"""
from agent_player.llm import AgentLLM, Antwort, Aufruf, Nachricht
from agent_player.tools import Werkzeug


class FakeAgentLLM(AgentLLM):
    modell = "fake"

    def __init__(self, antworten: list[Antwort]):
        self.antworten = list(antworten)

    async def frage(self, system: str, nachrichten: list[Nachricht], werkzeuge: list[Werkzeug]) -> Antwort:
        if self.antworten:
            return self.antworten.pop(0)
        return Antwort(text="(Das Fake-Skript ist zu Ende – ich warte nur noch.)",
                       aufrufe=[Aufruf("abwarten", {"warum": "Skript zu Ende"})])


def _zug(name: str, warum: str, **args) -> Aufruf:
    return Aufruf(name, {**args, "warum": warum})


# Spielt am Spielanfang: freie Aktionen, einen Fehler (kostet keine Runde), dann echte Züge.
DEMO_ANTWORTEN: list[Antwort] = [
    Antwort(text="Ich verschaffe mir erst einen Überblick und notiere mir den Plan.",
            aufrufe=[Aufruf("inventar_ansehen"),
                     Aufruf("notizbuch_schreiben", {"text": "Plan: Schuppen suchen, dort nach Hilfe für die Fahrradkette schauen."})]),
    Antwort(text="Dorthin möchte ich gehen.", aufrufe=[_zug("gehen", "Ein Ort, den es nicht gibt – ein Fehler kostet keine Runde.", ziel="Mars")]),
    Antwort(text="Dann eben zum Schuppen.", aufrufe=[_zug("gehen", "Im Schuppen gibt es vielleicht Hilfe.", ziel="Schuppen")]),
    Antwort(text="Der Blumentopf sieht verdächtig aus.", aufrufe=[_zug("untersuchen", "Unter Blumentöpfen liegt oft etwas.", objekt="Blumentopf")]),
    Antwort(aufrufe=[Aufruf("notizbuch_schreiben", {"text": "Unter dem Blumentopf liegt ein Schlüssel."}),
                     _zug("nehmen", "Der Schlüssel könnte eine Tür öffnen.", objekt="Schlüssel")]),
]

# Ein Modell, das sich verzettelt: nur freie Aktionen -> Aufruflimit -> neutraler Ersatzzug.
VERZETTELT_ANTWORTEN: list[Antwort] = [Antwort(aufrufe=[Aufruf("notizbuch_lesen")]) for _ in range(20)]
