"""Spielstände mit Agentenzustand: Notizbuch, Verlauf und eine Notiz an das künftige Ich.

LERNPUNKT: Ein Agent ist mehr als die Spielwelt. Ohne sein Gedächtnis (Notizbuch, kurzer Verlauf) wäre ein
geladener Spielstand für ihn ein Fremder. Deshalb hängt der Agentenzustand als eigener Block "agent" am
Spielstand (services/save_load.py). Er trägt eine eigene Formatkennung und Version, und beim Laden wird er
geprüft (pruefen): so merkt das Spiel, ob das Format passt, statt später an einem Feld zu scheitern.
Eine Notiz an das künftige Ich ("Vorsicht: gleich zünde ich die Sprengladung!") bleibt dabei erhalten.
"""
import json
import os
import re
import time

FORMAT = "agent-zustand"
VERSION = 1
SAVE_DIR = "saves"          # derselbe Ordner wie "speichere <name>" im normalen Spiel


# --- Slot-Namen -------------------------------------------------------------------------
def sicherer_name(name: str) -> str:
    """Nur Buchstaben, Ziffern, '-' und '_' (kein Pfadtrick wie '../')."""
    return re.sub(r"[^\w\-]", "", str(name).strip().replace(" ", "_")).strip("_")


def pfad_fuer(name: str) -> str:
    return os.path.join(SAVE_DIR, sicherer_name(name) + ".json")


# --- Export / Import / Prüfung ----------------------------------------------------------
def exportieren(ctx, notiz: str = "") -> dict:
    """Macht aus dem Gedächtnis des Agenten einen JSON-fähigen Block."""
    return {
        "format": FORMAT,
        "version": VERSION,
        "gespeichert_am": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modell": ctx.llm.modell,
        "runde": ctx.runde,
        "notiz_an_mich": notiz.strip(),
        "notizbuch": list(ctx.notizbuch.eintraege),
        "verlauf": [{"runde": e.runde, "zug": e.zug, "warum": e.warum, "ergebnis": e.ergebnis} for e in ctx.verlauf],
        "letztes_ergebnis": ctx.letztes_ergebnis,
        "npc_meldungen": list(ctx.npc_meldungen),
        "orte": sorted(ctx.orte),
        "schritt": ctx.schritt,
    }


def pruefen(daten) -> list[str]:
    """Kurze Analyse des Blocks. Rückgabe: Liste der Probleme (leer = Format in Ordnung)."""
    if not isinstance(daten, dict):
        return ["Der Agentenblock ist kein Objekt."]
    if daten.get("format") != FORMAT:
        return [f"Unbekanntes Format {daten.get('format')!r} (erwartet {FORMAT!r})."]
    version = daten.get("version")
    if not isinstance(version, int):
        return ["Die Version fehlt oder ist keine Zahl."]
    if version > VERSION:
        return [f"Der Agentenzustand hat Version {version}, dieses Programm kennt nur bis Version {VERSION}."]
    probleme = []
    if not (isinstance(daten.get("notizbuch"), list) and all(isinstance(e, str) for e in daten["notizbuch"])):
        probleme.append("'notizbuch' muss eine Liste von Texten sein.")
    verlauf = daten.get("verlauf")
    if not (isinstance(verlauf, list) and all(
            isinstance(e, dict) and isinstance(e.get("runde"), int)
            and all(isinstance(e.get(k), str) for k in ("zug", "warum", "ergebnis")) for e in verlauf)):
        probleme.append("'verlauf' muss eine Liste von Einträgen mit runde (Zahl) und zug/warum/ergebnis (Texte) sein.")
    if not isinstance(daten.get("orte", []), list):
        probleme.append("'orte' muss eine Liste sein.")
    if not isinstance(daten.get("notiz_an_mich", ""), str):
        probleme.append("'notiz_an_mich' muss ein Text sein.")
    return probleme


def importieren(ctx, daten: dict) -> None:
    """Spielt einen GEPRÜFTEN Block in den Kontext des Agenten zurück (Tokenzähler beginnen bewusst neu)."""
    from agent_player.context import RundenEintrag
    ctx.notizbuch.eintraege = list(daten.get("notizbuch", []))
    ctx.verlauf = [RundenEintrag(e["runde"], e["zug"], e["warum"], e["ergebnis"]) for e in daten.get("verlauf", [])]
    ctx.letztes_ergebnis = str(daten.get("letztes_ergebnis", ""))
    ctx.npc_meldungen = list(daten.get("npc_meldungen", []))
    ctx.orte = set(daten.get("orte", []))
    ctx.schritt = int(daten.get("schritt", 0))
    notiz = str(daten.get("notiz_an_mich", "")).strip()
    if notiz:
        # Einmal prominent im ersten Prompt (context.runden_nachricht) UND dauerhaft im Notizbuch.
        ctx.erinnerung = notiz
        ctx.notizbuch.schreiben(f"[Notiz an mich aus dem Spielstand, Runde {daten.get('runde', '?')}] {notiz}")


# --- Speichern / Laden / Auflisten ------------------------------------------------------
def speichern(game, ctx, name: str, notiz: str = "") -> str:
    """Speichert Spiel + (falls der Agent schon läuft) Agentenzustand. Rückgabe: Pfad."""
    from services.save_load import save_to_file
    os.makedirs(SAVE_DIR, exist_ok=True)
    pfad = pfad_fuer(name)
    save_to_file(game, pfad, agent=exportieren(ctx, notiz) if ctx is not None else None)
    return pfad


def laden(name: str, llm):
    """Lädt einen Spielstand. Rückgabe: (GameState | None, Agentenblock | None, Meldungen für den Zuschauer).

    GameState None heißt: nicht laden (Datei fehlt oder der Agentenblock ist ungültig) – der Server startet
    dann ein neues Spiel."""
    from services.save_load import load_from_file_with_agent
    pfad = pfad_fuer(name)
    if not os.path.exists(pfad):
        return None, None, [f"❌ Kein Spielstand '{name}' gefunden – es startet ein neues Spiel."]
    game, block = load_from_file_with_agent(pfad, llm=llm)
    if block is None:
        return game, None, [f"⚠️ Der Spielstand '{name}' enthält keinen Agentenzustand – der Agent startet ohne Gedächtnis."]
    probleme = pruefen(block)
    if probleme:
        return None, None, [f"❌ Agentenzustand in '{name}' ungültig ({' '.join(probleme)}) – es startet ein neues Spiel."]
    meldung = f"📂 Spielstand '{name}' geladen (Agentenzustand vom {block.get('gespeichert_am', '?')})."
    if block.get("notiz_an_mich"):
        meldung += f" Notiz an den Agenten: {block['notiz_an_mich']}"
    return game, block, [meldung]


def auflisten() -> list[dict]:
    """Alle Spielstände; 'agent' = enthält einen gültigen Agentenblock (mit seiner Notiz)."""
    if not os.path.isdir(SAVE_DIR):
        return []
    ergebnis = []
    for datei in sorted(os.listdir(SAVE_DIR)):
        if not datei.endswith(".json"):
            continue
        eintrag = {"name": datei[:-5], "agent": False, "notiz": ""}
        try:
            with open(os.path.join(SAVE_DIR, datei), encoding="utf-8") as f:
                block = json.load(f).get("agent")
            if block is not None and not pruefen(block):
                eintrag.update(agent=True, notiz=block.get("notiz_an_mich", ""), runde=block.get("runde"))
        except Exception:
            pass
        ergebnis.append(eintrag)
    return ergebnis
