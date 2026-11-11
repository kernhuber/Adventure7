"""Experience.md: das Gedächtnis des Agenten über Spiele hinweg.

LERNPUNKT: Das Notizbuch (notebook.py) lebt nur ein Spiel lang. Was ein menschlicher Spieler sich nach dem
Spiel merkt ("Die Sprengladung ist gefährlich", "Die Leiter kann man an den Schuppen lehnen"), landet hier in
einer Datei. Am Spielende zieht der Agent selbst ein Resümee (resuemee_ziehen), beim nächsten Spielstart steht
die Datei im System-Prompt (context.AgentKontext.system_prompt). So wird der Agent von Spiel zu Spiel schlauer –
ganz ohne Training: Das "Lernen" ist nur Text, den der Agent liest und schreibt. Man kann die Datei auch selbst
lesen und von Hand bearbeiten (z. B. falsche Erkenntnisse löschen).

Fairness: Die Datei enthält nur, was der Agent in seinen eigenen Spielen erlebt oder gelesen hat – kein
Lösungswissen von außen (es sei denn, jemand schreibt es hinein).
"""
import os
import time

from utils import dprint, dl
from agent_player import config
from agent_player.context import AgentKontext
from agent_player.llm import Nachricht
from agent_player.tools import ERFAHRUNG_WERKZEUGE

KOPF = """# Erfahrungen des Agenten

Diese Datei schreibt der Agent nach jedem Spiel selbst fort (agent_player/experience.py) und liest sie beim
nächsten Start. Man darf sie von Hand bearbeiten: falsche Erkenntnisse löschen, eigene Tipps ergänzen.
"""


def lesen(max_zeichen: int | None = None) -> str:
    """Inhalt der Datei (leer, wenn es sie noch nicht gibt). Zu lange Dateien werden vorne gekürzt:
    die neuesten Erfahrungen stehen unten und sind am wichtigsten."""
    max_zeichen = max_zeichen or config.EXPERIENCE_MAX_ZEICHEN
    if not os.path.exists(config.EXPERIENCE_DATEI):
        return ""
    with open(config.EXPERIENCE_DATEI, encoding="utf-8") as f:
        text = f.read().strip()
    if len(text) > max_zeichen:
        text = "(… ältere Einträge gekürzt …)\n" + text[-max_zeichen:]
    return text


def anhaengen(ergebnis: str, runden: int, erkenntnisse: list[str]) -> list[str]:
    """Hängt einen Abschnitt für dieses Spiel an. Schon vorhandene Erkenntnisse (gleicher Wortlaut) werden
    nicht doppelt geschrieben. Rückgabe: die tatsächlich neu geschriebenen."""
    vorhanden = lesen(10 ** 9).lower()
    neu = [e.strip() for e in erkenntnisse if e.strip() and e.strip().lower() not in vorhanden]
    if not neu:
        return []
    if not os.path.exists(config.EXPERIENCE_DATEI):
        with open(config.EXPERIENCE_DATEI, "w", encoding="utf-8") as f:
            f.write(KOPF)
    with open(config.EXPERIENCE_DATEI, "a", encoding="utf-8") as f:
        f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M')} – {ergebnis} (Runde {runden})\n")
        for e in neu:
            f.write(f"- {e}\n")
    return neu


async def resuemee_ziehen(ctx: AgentKontext, ergebnis: str) -> list[str]:
    """Fragt den Agenten nach dem Spiel nach seinen Erkenntnissen und schreibt sie in Experience.md."""
    verlauf = "\n".join(e.als_text() for e in ctx.verlauf[-config.EXPERIENCE_VERLAUF_RUNDEN:]) or "(keine Züge)"
    schluss = "\n".join([ctx.letztes_ergebnis] + [f"- {m}" for m in ctx.npc_meldungen]).strip() or "(nichts)"
    text = (f"=== DAS SPIEL IST ZU ENDE: {ergebnis.upper()} (Runde {ctx.runde}) ===\n\n"
            f"=== LETZTE MELDUNGEN ===\n{schluss}\n\n"
            f"=== DEIN NOTIZBUCH ===\n{ctx.notizbuch.lesen()}\n\n"
            f"=== DEINE LETZTEN ZÜGE ===\n{verlauf}\n\n"
            "Ziehe jetzt Resümee – so, wie ein menschlicher Spieler sich nach dem Spiel etwas fürs nächste Mal merkt. "
            "Was hast du über die Spielwelt gelernt (Orte, Wege, Objekte und was man damit tun kann, Gefahren, Figuren)? "
            "Was würdest du beim nächsten Mal anders machen? Formuliere jede Erkenntnis als einen kurzen, konkreten, "
            "allgemeingültigen Satz, z. B. 'Vorsicht: <Aktion> am Ort <X> hat <Folge>.' oder '<Objekt> kann man <Verb> – "
            "dann passiert <Wirkung>.' Nur, was du in diesem Spiel selbst erlebt oder gelesen hast – nichts erfinden, "
            "nichts wiederholen, was schon unter 'Erfahrungen aus früheren Spielen' steht. Rufe für jede Erkenntnis "
            f"'erfahrung_notieren' auf (höchstens {config.EXPERIENCE_MAX_ERKENNTNISSE}).")
    antwort = await ctx.frage_modell([Nachricht.vom_nutzer(text)], ERFAHRUNG_WERKZEUGE)
    erkenntnisse = [str(a.args.get("erkenntnis", "")) for a in antwort.aufrufe if a.name == "erfahrung_notieren"]
    neu = anhaengen(ergebnis, ctx.runde, erkenntnisse[:config.EXPERIENCE_MAX_ERKENNTNISSE])
    dprint(dl.AGENT, f"📒 Experience.md: {len(neu)} neue Erkenntnis(se)")
    await ctx.melde({"type": "agent_event", "kind": "exp", "tool": "Experience.md", "args": {},
                     "result": ("Neu festgehalten:\n" + "\n".join(f"• {e}" for e in neu)) if neu
                     else "Keine neuen Erkenntnisse festgehalten.",
                     "round": ctx.runde, "step": ctx.schritt})
    return neu
