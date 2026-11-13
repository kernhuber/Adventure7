"""Meilenstein 1: ein Skript-Spieler OHNE LLM.

Er spielt eine feste Liste von Zügen. Zweck: beweisen, dass die Pipeline (Zug in die
Befehlswarteschlange -> derselbe Rundenpfad wie beim Menschen -> Anzeige im Browser) trägt,
bevor ein Modell ins Spiel kommt. Die Namen sind Rufnamen wie in der GUI; die Engine
löst sie selbst in IDs auf (wie bei einem geparsten Menschenbefehl).
"""
from dataclasses import dataclass, field


@dataclass
class ScriptStep:
    verb: str                                   # Engine-Verb: gehe, nimm, untersuche, anwenden, umsehen, nichts ...
    args: dict = field(default_factory=dict)    # Argumente des Verbs (Rufnamen)
    why: str = ""                             # wird im Panel angezeigt (später liefert das der Agent selbst)

    def as_function_call(self) -> dict:
        """Das Format, das auch der LLM-Parser liefert: {"function_call": {"name":..., "args":...}}."""
        return {"function_call": {"name": self.verb, "args": dict(self.args)}}


# Erster Streifzug (angelehnt an sys_test.py). Misserfolge sind erlaubt – sie sind sichtbar im Panel.
SCRIPT: list[ScriptStep] = [
    ScriptStep("umsehen", {}, "Erst mal orientieren."),
    ScriptStep("gehe", {"direction": "Schuppen"}, "Im Schuppen gibt es vielleicht Hilfe."),
    ScriptStep("untersuche", {"what": "Blumentopf"}, "Unter Blumentöpfen liegt oft ein Schlüssel."),
    ScriptStep("nimm", {"whato": "Schlüssel"}, "Den Schlüssel mitnehmen."),
    ScriptStep("anwenden", {"what": "Schlüssel", "towhat": "Schuppen"}, "Den Schuppen aufschließen."),
    ScriptStep("gehe", {"direction": "innen"}, "Hineingehen."),
    ScriptStep("umsehen", {}, "Was liegt hier herum?"),
    ScriptStep("nimm", {"whato": "Sprengladung"}, "Die könnte nützlich sein."),
    ScriptStep("gehe", {"direction": "Schuppen"}, "Wieder hinaus."),
    ScriptStep("nichts", {}, "Kurz durchatmen."),
]
