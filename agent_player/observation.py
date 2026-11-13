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
VISIBLE_NPC_MESSAGES = {"do_explosion", "explosion_message", "zombie_bite", "zombie_event", "minigame"}


@dataclass
class EventSummary:
    """Was bei einem Zug im Browser angekommen ist, aufgeteilt für den Agenten."""
    text: str = ""                                          # Ergebnis der Aktion (inkl. gelesener Popups)
    npc_messages: list[str] = field(default_factory=list)  # sichtbare NPC-Ereignisse
    error: bool = False                                    # Systemfehler: der Zug hat KEINE Runde gekostet


def evaluate_events(events: list[dict]) -> EventSummary:
    """Macht aus den mitgeschnittenen Browser-Nachrichten einen Text für den Agenten."""
    a = EventSummary()
    chunks: list[str] = []
    for e in events:
        if not isinstance(e, dict):
            continue                                  # z. B. None aus dem Minispiel-Zweig von handle_command
        msg_type = e.get("type")
        if msg_type == "command_result":
            for r in e.get("results", []):
                result = r.get("result")
                if result is not None and str(result).strip():
                    chunks.append(str(result).strip())
                if r.get("is_game_move") is False:
                    a.error = True
        elif msg_type == "manual_popup":
            # Das Popup liest auch ein Mensch -> der Agent liest es ebenfalls.
            chunks.append(f"[Du liest: {e.get('title', 'Dokument')}]\n{e.get('content', '')}")
        elif msg_type == "minigame_complete":
            # Ausgang des Hundekampfs (im Agentenmodus gewürfelt, siehe AgentDialogs.do_minigame).
            if e.get("message"):
                a.npc_messages.append(str(e["message"]).strip())
        elif msg_type == "npc_actions":
            for npc_action in e.get("actions", []):
                if isinstance(npc_action, dict) and npc_action.get("command") in VISIBLE_NPC_MESSAGES and npc_action.get("message"):
                    a.npc_messages.append(str(npc_action["message"]).strip())
    a.text = "\n".join(chunks)
    return a


def present_characters(view: dict) -> list[str]:
    """Hund/Zombie sind für einen Menschen als Icon sichtbar, sobald sie am selben Ort sind."""
    present = []
    if view.get("dog", {}).get("here"):
        present.append("Hund")
    if view.get("zombie", {}).get("here"):
        present.append("Zombie")
    return present


def observation_as_text(view: dict, last_result: str = "", npc_messages: list[str] | None = None) -> str:
    """Die aktuelle Lage als Text – der Hauptteil des Rundenprompts."""
    player = view.get("player", {})
    environment = view.get("environment", {})
    lines = [
        f"Spielrunde: {view.get('round', '?')}",
        f"Ort: {player.get('location', '?')}",
        f"Durst-Zähler: {player.get('thirst', '?')} (bei 0 verdurstest du)",
        "",
        "Szene:",
        str(view.get("scene_description", "")).strip() or "(keine Beschreibung)",
        "",
        "Objekte hier: " + (", ".join(environment.get("objects", [])) or "keine sichtbaren"),
        "Begehbare Wege: " + (", ".join(environment.get("ways", [])) or "keine"),
    ]
    if environment.get("blockedWays"):
        lines.append("Versperrte Wege: " + ", ".join(environment["blockedWays"]))
    lines.append("Inventar: " + (", ".join(player.get("inventory", [])) or "leer"))
    present = present_characters(view)
    if present:
        lines.append("Anwesend: " + ", ".join(present))
    if last_result:
        lines += ["", "Ergebnis deiner letzten Aktion:", last_result]
    if npc_messages:
        lines += ["", "Ereignisse seit deinem letzten Zug:"] + [f"- {m}" for m in npc_messages]
    return "\n".join(lines)
