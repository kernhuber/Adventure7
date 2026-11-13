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
def safe_name(name: str) -> str:
    """Nur Buchstaben, Ziffern, '-' und '_' (kein Pfadtrick wie '../')."""
    return re.sub(r"[^\w\-]", "", str(name).strip().replace(" ", "_")).strip("_")


def path_for(name: str) -> str:
    return os.path.join(SAVE_DIR, safe_name(name) + ".json")


# --- Export / Import / Prüfung ----------------------------------------------------------
def export_state(ctx, note: str = "") -> dict:
    """Macht aus dem Gedächtnis des Agenten einen JSON-fähigen Block."""
    return {
        "format": FORMAT,
        "version": VERSION,
        "gespeichert_am": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modell": ctx.llm.model,
        "runde": ctx.round_number,
        "notiz_an_mich": note.strip(),
        "notizbuch": list(ctx.notebook.entries),
        "verlauf": [{"runde": e.round_number, "zug": e.move, "warum": e.why, "ergebnis": e.result} for e in ctx.history],
        "letztes_ergebnis": ctx.last_result,
        "npc_meldungen": list(ctx.npc_messages),
        "orte": sorted(ctx.places),
        "schritt": ctx.step,
    }


def validate(data) -> list[str]:
    """Kurze Analyse des Blocks. Rückgabe: Liste der Probleme (leer = Format in Ordnung)."""
    if not isinstance(data, dict):
        return ["Der Agentenblock ist kein Objekt."]
    if data.get("format") != FORMAT:
        return [f"Unbekanntes Format {data.get('format')!r} (erwartet {FORMAT!r})."]
    version = data.get("version")
    if not isinstance(version, int):
        return ["Die Version fehlt oder ist keine Zahl."]
    if version > VERSION:
        return [f"Der Agentenzustand hat Version {version}, dieses Programm kennt nur bis Version {VERSION}."]
    problems = []
    if not (isinstance(data.get("notizbuch"), list) and all(isinstance(e, str) for e in data["notizbuch"])):
        problems.append("'notizbuch' muss eine Liste von Texten sein.")
    history = data.get("verlauf")
    if not (isinstance(history, list) and all(
            isinstance(e, dict) and isinstance(e.get("runde"), int)
            and all(isinstance(e.get(k), str) for k in ("zug", "warum", "ergebnis")) for e in history)):
        problems.append("'verlauf' muss eine Liste von Einträgen mit runde (Zahl) und zug/warum/ergebnis (Texte) sein.")
    if not isinstance(data.get("orte", []), list):
        problems.append("'orte' muss eine Liste sein.")
    if not isinstance(data.get("notiz_an_mich", ""), str):
        problems.append("'notiz_an_mich' muss ein Text sein.")
    return problems


def import_state(ctx, data: dict) -> None:
    """Spielt einen GEPRÜFTEN Block in den Kontext des Agenten zurück (Tokenzähler beginnen bewusst neu)."""
    from agent_player.context import RoundEntry
    ctx.notebook.entries = list(data.get("notizbuch", []))
    ctx.history = [RoundEntry(e["runde"], e["zug"], e["warum"], e["ergebnis"]) for e in data.get("verlauf", [])]
    ctx.last_result = str(data.get("letztes_ergebnis", ""))
    ctx.npc_messages = list(data.get("npc_meldungen", []))
    ctx.places = set(data.get("orte", []))
    ctx.step = int(data.get("schritt", 0))
    note = str(data.get("notiz_an_mich", "")).strip()
    if note:
        # Einmal prominent im ersten Prompt (context.round_message) UND dauerhaft im Notizbuch.
        ctx.save_memo = note
        ctx.notebook.write(f"[Notiz an mich aus dem Spielstand, Runde {data.get('runde', '?')}] {note}")


# --- Speichern / Laden / Auflisten ------------------------------------------------------
def save_game(game, ctx, name: str, note: str = "") -> str:
    """Speichert Spiel + (falls der Agent schon läuft) Agentenzustand. Rückgabe: Pfad."""
    from services.save_load import save_to_file
    os.makedirs(SAVE_DIR, exist_ok=True)
    file_path = path_for(name)
    save_to_file(game, file_path, agent=export_state(ctx, note) if ctx is not None else None)
    return file_path


def load_game(name: str, llm):
    """Lädt einen Spielstand. Rückgabe: (GameState | None, Agentenblock | None, Meldungen für den Zuschauer).

    GameState None heißt: nicht laden (Datei fehlt oder der Agentenblock ist ungültig) – der Server startet
    dann ein neues Spiel."""
    from services.save_load import load_from_file_with_agent
    file_path = path_for(name)
    if not os.path.exists(file_path):
        return None, None, [f"❌ Kein Spielstand '{name}' gefunden – es startet ein neues Spiel."]
    game, block = load_from_file_with_agent(file_path, llm=llm)
    if block is None:
        return game, None, [f"⚠️ Der Spielstand '{name}' enthält keinen Agentenzustand – der Agent startet ohne Gedächtnis."]
    problems = validate(block)
    if problems:
        return None, None, [f"❌ Agentenzustand in '{name}' ungültig ({' '.join(problems)}) – es startet ein neues Spiel."]
    message = f"📂 Spielstand '{name}' geladen (Agentenzustand vom {block.get('gespeichert_am', '?')})."
    if block.get("notiz_an_mich"):
        message += f" Notiz an den Agenten: {block['notiz_an_mich']}"
    return game, block, [message]


def list_saves() -> list[dict]:
    """Alle Spielstände; 'agent' = enthält einen gültigen Agentenblock (mit seiner Notiz)."""
    if not os.path.isdir(SAVE_DIR):
        return []
    result = []
    for filename in sorted(os.listdir(SAVE_DIR)):
        if not filename.endswith(".json"):
            continue
        entry = {"name": filename[:-5], "agent": False, "notiz": ""}
        try:
            with open(os.path.join(SAVE_DIR, filename), encoding="utf-8") as f:
                block = json.load(f).get("agent")
            if block is not None and not validate(block):
                entry.update(agent=True, note=block.get("notiz_an_mich", ""), round_number=block.get("runde"))
        except Exception:
            pass
        result.append(entry)
    return result
