"""Die INNERE Schleife des Agenten – das Lehrstück dieses Pakets.

Zwei verschachtelte Schleifen:
  außen: die Spielrunden (runner.py) – das Spiel schreitet Zug für Zug fort
  innen: DIESE Datei – in einer Runde fragt der Agent das Modell, führt Werkzeuge aus, sieht die
         Ergebnisse und fragt erneut, bis er einen Zug macht.
Eine Agentenschleife ist im Kern genau das: Modell fragen -> Werkzeug ausführen -> Ergebnis zurückgeben
-> wiederholen. Alles andere in diesem Paket ist Zubehör.
"""
from dataclasses import dataclass

from agent_player import config
from agent_player.context import AgentKontext, RundenEintrag, runden_nachricht
from agent_player.llm import Aufruf, AufrufErgebnis, Nachricht
from agent_player.observation import beobachtung_als_text, ereignisse_auswerten
from agent_player.tools import FREIE_AKTIONEN, ZUEGE, FREIE_NAMEN, ZUG_NAMEN, zug_vorbereiten

HINWEIS_KEIN_WERKZEUG = "Du hast kein Werkzeug aufgerufen. Rufe jetzt ein Werkzeug auf – am Ende der Runde einen Zug."


@dataclass
class RundenErgebnis:
    zug: str
    warum: str
    ergebnis: str
    neutral: bool = False      # True, wenn das Aufruflimit zu einem Ersatzzug geführt hat


async def spiele_runde(ctx: AgentKontext) -> RundenErgebnis:
    """Eine Spielrunde des Agenten: so lange Werkzeuge nutzen, bis er einen Zug macht."""
    ctx.neue_runde()
    # LERNPUNKT: frischer Kontext je Runde (siehe context.py) – der Verlauf der Runde lebt nur in `nachrichten`.
    nachrichten = [runden_nachricht(ctx)]
    werkzeuge = FREIE_AKTIONEN + ZUEGE
    while ctx.aufrufe_runde < config.MAX_AUFRUFE_PRO_RUNDE:
        antwort = await ctx.frage_modell(nachrichten, werkzeuge)              # 1. Modell fragen
        nachrichten.append(Nachricht.vom_modell(antwort))
        if not antwort.aufrufe:                                               # Modell hat nur geredet
            ctx.aufrufe_runde += 1
            nachrichten.append(Nachricht.vom_nutzer(HINWEIS_KEIN_WERKZEUG))
            continue
        ergebnisse = []
        for aufruf in antwort.aufrufe:
            await ctx.steuerung.vor_schritt()                                 # Pause / Einzelschritt / Tempo
            ctx.aufrufe_runde += 1
            ctx.schritt += 1
            ergebnis, war_zug = await fuehre_werkzeug_aus(ctx, aufruf)        # 2. Werkzeug ausführen
            ergebnisse.append(ergebnis)
            await ctx.sende_status()
            if war_zug:                                                       # ein Zug beendet die Runde,
                return RundenErgebnis(aufruf.name, str(aufruf.args.get("warum", "")), ergebnis.text)  # der Kontext wird verworfen
        nachrichten.append(Nachricht.werkzeug_ergebnisse(ergebnisse))         # 3. Ergebnis zurück ans Modell, dann von vorn
    return await erzwinge_zug(ctx, nachrichten)                               # Limit erreicht


# ---------------------------------------------------------------------------------------
# Hilfsfunktionen (bewusst außerhalb der Schleife, damit diese lesbar bleibt)
# ---------------------------------------------------------------------------------------
async def fuehre_werkzeug_aus(ctx: AgentKontext, aufruf: Aufruf) -> tuple[AufrufErgebnis, bool]:
    """Führt ein Werkzeug aus. Rückgabe: (Ergebnis fürs Modell, wurde ein Zug ausgeführt?)."""
    if aufruf.name in FREIE_NAMEN:
        text = frei_ausfuehren(ctx, aufruf)
        await ctx.melde({"type": "agent_event", "kind": "free", "tool": aufruf.name, "args": aufruf.args,
                         "result": text, "round": ctx.runde, "step": ctx.schritt})
        if aufruf.name == "notizbuch_schreiben":
            await ctx.melde({"type": "agent_notebook", "text": ctx.notizbuch.lesen()})
        return AufrufErgebnis(aufruf.name, text), False
    if aufruf.name in ZUG_NAMEN:
        if not str(aufruf.args.get("warum", "")).strip():
            return await _fehler(ctx, aufruf, "Jeder Zug braucht das Argument 'warum' (ein Satz).")
        function_call, fehler = zug_vorbereiten(aufruf.name, aufruf.args, ctx.hole_ansicht())
        if function_call is None:
            return await _fehler(ctx, aufruf, fehler)
        return await zug_ausfuehren(ctx, aufruf, function_call)
    return await _fehler(ctx, aufruf, f"Unbekanntes Werkzeug '{aufruf.name}'.")


async def zug_ausfuehren(ctx: AgentKontext, aufruf: Aufruf, function_call: dict) -> tuple[AufrufErgebnis, bool]:
    """Schickt einen Zug durch den normalen Rundenpfad (derselbe wie beim Menschen)."""
    ereignisse = await ctx.fuehre_zug_aus(function_call)
    a = ereignisse_auswerten(ereignisse)
    if a.fehler:                                   # Systemfehler der Engine: kostet keine Runde
        return await _fehler(ctx, aufruf, a.text or "Die Engine hat den Zug abgelehnt.")
    ctx.letztes_ergebnis, ctx.npc_meldungen = a.text, a.npc_meldungen
    warum = str(aufruf.args.get("warum", ""))
    ctx.verlauf.append(RundenEintrag(ctx.runde, f"{aufruf.name} {_args_text(aufruf)}", warum, a.text))
    anzeige = a.text + ("\n" if a.text and a.npc_meldungen else "") + "\n".join(f"⚠ {m}" for m in a.npc_meldungen)
    await ctx.melde({"type": "agent_event", "kind": "move", "tool": aufruf.name, "args": _ohne_warum(aufruf.args),
                     "warum": warum, "result": anzeige, "round": ctx.runde, "step": ctx.schritt})
    return AufrufErgebnis(aufruf.name, a.text), True


async def erzwinge_zug(ctx: AgentKontext, nachrichten: list[Nachricht]) -> RundenErgebnis:
    """Aufruflimit erreicht: Agent auffordern, jetzt zu ziehen; sonst neutraler Zug (wird protokolliert)."""
    nachrichten.append(Nachricht.vom_nutzer(
        f"Du hast {config.MAX_AUFRUFE_PRO_RUNDE} Werkzeugaufrufe in dieser Runde verbraucht. Mache JETZT einen Zug."))
    antwort = await ctx.frage_modell(nachrichten, ZUEGE)
    for aufruf in antwort.aufrufe:
        if aufruf.name not in ZUG_NAMEN:               # jetzt zählen nur noch Züge
            continue
        await ctx.steuerung.vor_schritt()
        ctx.schritt += 1
        ergebnis, war_zug = await fuehre_werkzeug_aus(ctx, aufruf)
        if war_zug:
            return RundenErgebnis(aufruf.name, str(aufruf.args.get("warum", "")), ergebnis.text)
    neutral = Aufruf("umsehen", {"warum": "Limit erreicht – neutraler Ersatzzug"})
    ctx.schritt += 1
    ergebnis, _ = await zug_ausfuehren(ctx, neutral, {"function_call": {"name": "umsehen", "args": {}}})
    return RundenErgebnis("umsehen", neutral.args["warum"], ergebnis.text, neutral=True)


def frei_ausfuehren(ctx: AgentKontext, aufruf: Aufruf) -> str:
    """Freie Aktionen: lesen/schreiben nur im eigenen Gedächtnis bzw. in der Beobachtung – die Welt bleibt unberührt."""
    ansicht = ctx.hole_ansicht()
    if aufruf.name == "situation_lesen":
        return beobachtung_als_text(ansicht, ctx.letztes_ergebnis, ctx.npc_meldungen)
    if aufruf.name == "inventar_ansehen":
        return "Inventar: " + (", ".join(ansicht.get("player", {}).get("inventory", [])) or "leer")
    if aufruf.name == "notizbuch_lesen":
        return ctx.notizbuch.lesen()
    if aufruf.name == "notizbuch_schreiben":
        ctx.notizbuch.schreiben(str(aufruf.args.get("text", "")))
        return "Notiert."
    if aufruf.name == "spielstand_speichern":
        if ctx.speichere is None:
            return "Speichern ist hier nicht möglich."
        return ctx.speichere(str(aufruf.args.get("notiz", "")))
    # was_weiss_ich_ueber: nur Notizbuch und eigener Verlauf, NIE die Spielwelt
    begriff = str(aufruf.args.get("begriff", "")).strip().lower()
    treffer = [e for e in ctx.notizbuch.eintraege if begriff in e.lower()]
    treffer += [e.als_text() for e in ctx.verlauf if begriff in e.als_text().lower()]
    return "\n".join(treffer) if begriff and treffer else f"Zu '{begriff}' steht nichts in deinem Notizbuch oder Verlauf."


async def _fehler(ctx: AgentKontext, aufruf: Aufruf, text: str) -> tuple[AufrufErgebnis, bool]:
    """Fehler als Werkzeugergebnis: verständlich, und ohne dass eine Runde vergeht."""
    await ctx.melde({"type": "agent_event", "kind": "error", "tool": aufruf.name, "args": _ohne_warum(aufruf.args),
                     "warum": str(aufruf.args.get("warum", "")), "result": text, "round": ctx.runde, "step": ctx.schritt})
    return AufrufErgebnis(aufruf.name, f"FEHLER (keine Runde verbraucht): {text}"), False


def _ohne_warum(args: dict) -> dict:
    return {k: v for k, v in args.items() if k != "warum"}


def _args_text(aufruf: Aufruf) -> str:
    return " ".join(str(v) for v in _ohne_warum(aufruf.args).values())
