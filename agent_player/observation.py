"""Spielersicht als Text: Was sieht der Agent?

LERNPUNKT (Fairness): Der Agent bekommt NUR, was auch ein Mensch im Browser sähe.
Deshalb kommt alles aus denselben zwei Quellen wie die GUI:
  1. dem serialisierten Spielzustand (`session["state"]`, derselbe Dict, den der Browser bekommt)
  2. den Nachrichten, die der Browser bei einem Zug bekam (mitgeschnitten in `session["tap"]`)
Dieses Modul greift NIRGENDS auf GameState, Flags, interne IDs (o_/p_), world.json, den
Zustand der NPCs oder die PIN zu – man sieht es schon an den Importen: es gibt keine.
"""
from dataclasses import dataclass, field

# NPC-Meldungen, die die GUI einem Menschen tatsächlich zeigt (siehe handleNPCActions in
# web/websockets.js). Bewusst NICHT dabei: dog_message / zombie_message (nur Debug in der GUI).
SICHTBARE_NPC_MELDUNGEN = {"do_explosion", "explosion_message", "zombie_bite", "zombie_event", "minigame"}


@dataclass
class Auswertung:
    """Was bei einem Zug im Browser angekommen ist, aufgeteilt für den Agenten."""
    text: str = ""                                          # Ergebnis der Aktion (inkl. gelesener Popups)
    npc_meldungen: list[str] = field(default_factory=list)  # sichtbare NPC-Ereignisse
    fehler: bool = False                                    # Systemfehler: der Zug hat KEINE Runde gekostet


def ereignisse_auswerten(ereignisse: list[dict]) -> Auswertung:
    """Macht aus den mitgeschnittenen Browser-Nachrichten einen Text für den Agenten."""
    a = Auswertung()
    teile: list[str] = []
    for e in ereignisse:
        if not isinstance(e, dict):
            continue                                  # z. B. None aus dem Minispiel-Zweig von handle_command
        typ = e.get("type")
        if typ == "command_result":
            for r in e.get("results", []):
                ergebnis = r.get("result")
                if ergebnis is not None and str(ergebnis).strip():
                    teile.append(str(ergebnis).strip())
                if r.get("is_game_move") is False:
                    a.fehler = True
        elif typ == "manual_popup":
            # Das Popup liest auch ein Mensch -> der Agent liest es ebenfalls.
            teile.append(f"[Du liest: {e.get('title', 'Dokument')}]\n{e.get('content', '')}")
        elif typ == "minigame_complete":
            # Ausgang des Hundekampfs (im Agentenmodus gewürfelt, siehe AgentDialogs.do_minigame).
            if e.get("message"):
                a.npc_meldungen.append(str(e["message"]).strip())
        elif typ == "npc_actions":
            for akt in e.get("actions", []):
                if isinstance(akt, dict) and akt.get("command") in SICHTBARE_NPC_MELDUNGEN and akt.get("message"):
                    a.npc_meldungen.append(str(akt["message"]).strip())
    a.text = "\n".join(teile)
    return a


def anwesende_figuren(ansicht: dict) -> list[str]:
    """Hund/Zombie sind für einen Menschen als Icon sichtbar, sobald sie am selben Ort sind."""
    anwesend = []
    if ansicht.get("dog", {}).get("here"):
        anwesend.append("Hund")
    if ansicht.get("zombie", {}).get("here"):
        anwesend.append("Zombie")
    return anwesend


def beobachtung_als_text(ansicht: dict, letztes_ergebnis: str = "", npc_meldungen: list[str] | None = None) -> str:
    """Die aktuelle Lage als Text – der Hauptteil des Rundenprompts."""
    spieler = ansicht.get("player", {})
    umgebung = ansicht.get("environment", {})
    zeilen = [
        f"Spielrunde: {ansicht.get('round', '?')}",
        f"Ort: {spieler.get('location', '?')}",
        f"Durst-Zähler: {spieler.get('thirst', '?')} (bei 0 verdurstest du)",
        "",
        "Szene:",
        str(ansicht.get("scene_description", "")).strip() or "(keine Beschreibung)",
        "",
        "Objekte hier: " + (", ".join(umgebung.get("objects", [])) or "keine sichtbaren"),
        "Begehbare Wege: " + (", ".join(umgebung.get("ways", [])) or "keine"),
    ]
    if umgebung.get("blockedWays"):
        zeilen.append("Versperrte Wege: " + ", ".join(umgebung["blockedWays"]))
    zeilen.append("Inventar: " + (", ".join(spieler.get("inventory", [])) or "leer"))
    anwesend = anwesende_figuren(ansicht)
    if anwesend:
        zeilen.append("Anwesend: " + ", ".join(anwesend))
    if letztes_ergebnis:
        zeilen += ["", "Ergebnis deiner letzten Aktion:", letztes_ergebnis]
    if npc_meldungen:
        zeilen += ["", "Ereignisse seit deinem letzten Zug:"] + [f"- {m}" for m in npc_meldungen]
    return "\n".join(zeilen)
