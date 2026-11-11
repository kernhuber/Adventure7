"""Die Gesprächsschleife des Agenten (Baustein B).

Sie hat denselben Aufbau wie die Rundenschleife in loop.py – Modell fragen, Werkzeug ausführen, Ergebnis
zurückgeben, wiederholen – nur mit anderen Werkzeugen: `sage` und `gespraech_beenden`.

LERNPUNKT: Hier verhandeln ZWEI Modelle miteinander. Der Agent (Gemini mit Werkzeugen) spricht mit dem
Zombie bzw. Hund (ein anderer, unabhängiger Prompt in npc_zombie_state.py / npc_dog_state.py). Das NPC-seitige
Verhalten ist unverändert: Wir liefern nur den Text, den sonst ein Mensch tippen würde.
"""
from typing import Awaitable, Callable

from utils import dprint, dl
from agent_player import config
from agent_player.context import AgentKontext, chat_nachricht
from agent_player.llm import AufrufErgebnis, Nachricht
from agent_player.tools import CHAT_WERKZEUGE

# npc_antwort(chat) -> Antworttext des Partners;  zeige(sprecher, text) -> Anzeige im Chat-Modal
NpcAntwort = Callable[[list[dict]], Awaitable[str]]
Zeige = Callable[[str, str], Awaitable[None]]


async def fuehre_gespraech(ctx: AgentKontext, partner: str, npc_antwort: NpcAntwort, zeige: Zeige,
                           npc_start: str = "", agent_start: str = "") -> list[dict]:
    """Führt ein Gespräch bis es endet. Rückgabe: der Gesprächsverlauf (Format wie im Browser-Modal)."""
    dprint(dl.AGENT, f"💬 Gespräch mit {partner} beginnt (NPC-Eröffnung: {npc_start!r}, Agent-Eröffnung: {agent_start!r})")
    chat: list[dict] = []
    if npc_start:                                                        # der NPC hat das Gespräch eröffnet
        chat.append({"zombiemessage": npc_start})
    wortwechsel = 0
    if agent_start:                                                      # der Agent hat eröffnet (ansprechen mit erster Nachricht)
        await _sage(ctx, partner, agent_start, chat, npc_antwort, zeige)
        wortwechsel += 1
    nachrichten = [chat_nachricht(ctx, partner, chat)]
    zusammenfassung, partner_beendet = "", False
    versuche = 0                                                         # Sicherung gegen endlose Fehlaufrufe
    while (wortwechsel < config.MAX_CHAT_WORTWECHSEL and versuche < 2 * config.MAX_CHAT_WORTWECHSEL + 2
           and not zusammenfassung and not partner_beendet):
        versuche += 1
        antwort = await ctx.frage_modell(nachrichten, CHAT_WERKZEUGE)    # 1. Modell fragen
        nachrichten.append(Nachricht.vom_modell(antwort))
        if not antwort.aufrufe:
            wortwechsel += 1
            nachrichten.append(Nachricht.vom_nutzer("Rufe 'sage' oder 'gespraech_beenden' auf."))
            continue
        ergebnisse = []
        for aufruf in antwort.aufrufe:
            dprint(dl.AGENT, f"💬 Chat: warte auf Freigabe für '{aufruf.name}' (laufend={ctx.steuerung.laufend})")
            await ctx.steuerung.vor_schritt()                            # Pause / Einzelschritt gilt auch im Chat
            ctx.schritt += 1
            if aufruf.name == "sage":                                    # 2. Werkzeug ausführen
                reply = await _sage(ctx, partner, str(aufruf.args.get("text", "")), chat, npc_antwort, zeige)
                wortwechsel += 1
                partner_beendet = reply.strip().lower() == "quit"        # so beendet ein NPC das Gespräch
                ergebnisse.append(AufrufErgebnis("sage", f"{partner} beendet das Gespräch." if partner_beendet
                                                 else f'{partner} antwortet: "{reply}"'))
            elif aufruf.name == "gespraech_beenden":
                zusammenfassung = str(aufruf.args.get("zusammenfassung", "")).strip() or "(keine Zusammenfassung)"
                break
            else:
                ergebnisse.append(AufrufErgebnis(aufruf.name, "FEHLER: Im Gespräch gibt es nur 'sage' und 'gespraech_beenden'."))
            if partner_beendet:
                break
        while len(ergebnisse) < len(antwort.aufrufe):                    # jeder Aufruf braucht ein Ergebnis (Gemini verlangt das)
            ergebnisse.append(AufrufErgebnis(antwort.aufrufe[len(ergebnisse)].name, "Nicht ausgeführt."))
        nachrichten.append(Nachricht.werkzeug_ergebnisse(ergebnisse))    # 3. Ergebnis zurück, dann von vorn
    if not zusammenfassung:                                              # Limit oder Partner hat beendet
        zusammenfassung = await _abschluss(ctx, partner, nachrichten, partner_beendet)
    await _ins_notizbuch(ctx, partner, zusammenfassung)
    dprint(dl.AGENT, f"💬 Gespräch mit {partner} beendet: {zusammenfassung[:80]!r}")
    return chat


async def _sage(ctx: AgentKontext, partner: str, text: str, chat: list[dict],
                npc_antwort: NpcAntwort, zeige: Zeige) -> str:
    """Der Agent spricht, der Partner antwortet; beides erscheint im Chat-Modal und im Panel."""
    text = text.strip() or "..."
    chat.append({"playermessage": text})
    await zeige("agent", text)
    reply = (await npc_antwort(chat)).strip() or "(schweigt)"
    chat.append({"zombiemessage": reply})
    await zeige("npc", reply)
    await ctx.melde({"type": "agent_event", "kind": "chat", "tool": "sage", "args": {},
                     "result": f"Agent: {text}\n{partner}: {reply}", "round": ctx.runde, "step": ctx.schritt})
    return reply


async def _abschluss(ctx: AgentKontext, partner: str, nachrichten: list[Nachricht], partner_beendet: bool) -> str:
    """Gespräch zu Ende, ohne dass der Agent es selbst beendet hat: einmal nach der Zusammenfassung fragen."""
    grund = f"{partner} hat das Gespräch beendet." if partner_beendet else "Das Gesprächslimit ist erreicht."
    nachrichten.append(Nachricht.vom_nutzer(f"{grund} Rufe jetzt 'gespraech_beenden' mit deiner Zusammenfassung auf."))
    antwort = await ctx.frage_modell(nachrichten, [CHAT_WERKZEUGE[1]])
    for aufruf in antwort.aufrufe:
        if aufruf.name == "gespraech_beenden":
            return str(aufruf.args.get("zusammenfassung", "")).strip() or "(keine Zusammenfassung)"
    return f"({grund})"


async def _ins_notizbuch(ctx: AgentKontext, partner: str, zusammenfassung: str) -> None:
    ctx.notizbuch.schreiben(f"Gespräch mit {partner} (Runde {ctx.runde}): {zusammenfassung}")
    await ctx.melde({"type": "agent_event", "kind": "chat", "tool": "gespraech_beenden", "args": {},
                     "result": f"Zusammenfassung fürs Notizbuch: {zusammenfassung}", "round": ctx.runde, "step": ctx.schritt})
    await ctx.melde({"type": "agent_notebook", "text": ctx.notizbuch.lesen()})
