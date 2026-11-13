"""Experience.md: das Gedächtnis des Agenten über Spiele hinweg.

LERNPUNKT: Das Notizbuch (notebook.py) lebt nur ein Spiel lang. Was ein menschlicher Spieler sich nach dem
Spiel merkt ("Die Sprengladung ist gefährlich", "Die Leiter kann man an den Schuppen lehnen"), landet hier in
einer Datei. Am Spielende zieht der Agent selbst ein Resümee (write_summary), beim nächsten Spielstart steht
die Datei im System-Prompt (context.AgentContext.system_prompt). So wird der Agent von Spiel zu Spiel schlauer –
ganz ohne Training: Das "Lernen" ist nur Text, den der Agent liest und schreibt. Man kann die Datei auch selbst
lesen und von Hand bearbeiten (z. B. falsche Erkenntnisse löschen).

Fairness: Die Datei enthält nur, was der Agent in seinen eigenen Spielen erlebt oder gelesen hat – kein
Lösungswissen von außen (es sei denn, jemand schreibt es hinein).
"""
import os
import time

from utils import dprint, dl
from agent_player import config
from agent_player.context import AgentContext
from agent_player.llm import Message
from agent_player.tools import EXPERIENCE_TOOLS

HEADER = """# Erfahrungen des Agenten

Diese Datei schreibt der Agent nach jedem Spiel selbst fort (agent_player/experience.py) und liest sie beim
nächsten Start. Man darf sie von Hand bearbeiten: falsche Erkenntnisse löschen, eigene Tipps ergänzen.
"""


def read(max_chars: int | None = None) -> str:
    """Inhalt der Datei (leer, wenn es sie noch nicht gibt). Zu lange Dateien werden vorne gekürzt:
    die neuesten Erfahrungen stehen unten und sind am wichtigsten."""
    max_chars = max_chars or config.EXPERIENCE_MAX_CHARS
    if not os.path.exists(config.EXPERIENCE_FILE):
        return ""
    with open(config.EXPERIENCE_FILE, encoding="utf-8") as f:
        text = f.read().strip()
    if len(text) > max_chars:
        text = "(… ältere Einträge gekürzt …)\n" + text[-max_chars:]
    return text


def append_insights(result: str, rounds: int, insights: list[str]) -> list[str]:
    """Hängt einen Abschnitt für dieses Spiel an. Schon vorhandene Erkenntnisse (gleicher Wortlaut) werden
    nicht doppelt geschrieben. Rückgabe: die tatsächlich neu geschriebenen."""
    existing = read(10 ** 9).lower()
    new = [e.strip() for e in insights if e.strip() and e.strip().lower() not in existing]
    if not new:
        return []
    if not os.path.exists(config.EXPERIENCE_FILE):
        with open(config.EXPERIENCE_FILE, "w", encoding="utf-8") as f:
            f.write(HEADER)
    with open(config.EXPERIENCE_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n## {time.strftime('%Y-%m-%d %H:%M')} – {result} (Runde {rounds})\n")
        for e in new:
            f.write(f"- {e}\n")
    return new


async def write_summary(ctx: AgentContext, result: str) -> list[str]:
    """Fragt den Agenten nach dem Spiel nach seinen Erkenntnissen und schreibt sie in Experience.md."""
    history = ("\n".join(e.as_text() for e in ctx.history[-config.EXPERIENCE_HISTORY_ROUNDS:])
               or config.PROMPT_SUMMARY_NO_MOVES)
    ending = ("\n".join([ctx.last_result] + [f"- {m}" for m in ctx.npc_messages]).strip()
              or config.PROMPT_SUMMARY_NO_MESSAGES)
    text = config.PROMPT_SUMMARY.format(result_upper=result.upper(), round_number=ctx.round_number, ending=ending,
                                        notebook=ctx.notebook.read(), history=history,
                                        max_insights=config.EXPERIENCE_MAX_INSIGHTS)
    response = await ctx.ask_model([Message.from_user(text)], EXPERIENCE_TOOLS)
    insights = [str(a.args.get("erkenntnis", "")) for a in response.calls if a.name == "erfahrung_notieren"]
    new = append_insights(result, ctx.round_number, insights[:config.EXPERIENCE_MAX_INSIGHTS])
    dprint(dl.AGENT, f"📒 Experience.md: {len(new)} neue Erkenntnis(se)")
    await ctx.report({"type": "agent_event", "kind": "exp", "tool": "Experience.md", "args": {},
                     "result": ("Neu festgehalten:\n" + "\n".join(f"• {e}" for e in new)) if new
                     else "Keine neuen Erkenntnisse festgehalten.",
                     "round": ctx.round_number, "step": ctx.step})
    return new
