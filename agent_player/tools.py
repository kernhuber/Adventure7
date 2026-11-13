"""Die Werkzeuge des Agenten – hier wird aus der Spielwelt eine Werkzeug-Umgebung.

LERNPUNKT: Es gibt zwei Klassen von Werkzeugen, und diese Trennung ist der Kern des Designs:

  FREIE AKTIONEN  – kosten keine Spielrunde. Der Agent darf so oft nachsehen/notieren, wie er will
                    (bis zum Limit pro Runde). Die Welt bleibt dabei stehen, kein NPC handelt.
  ZÜGE            – verändern die Welt und kosten GENAU EINE Runde. Danach handeln die NPCs,
                    der Durst steigt, und der Agent bekommt eine neue Beobachtung.

Wie bei Claude Code: Dateien LESEN ändert nichts (frei), einen Befehl AUSFÜHREN schon (Zug).
Hier steht nur die Beschreibung der Werkzeuge und die Prüfung/Übersetzung der Züge; ausgeführt
werden sie in loop.py.
"""
from dataclasses import dataclass

from agent_player.observation import present_characters


@dataclass(frozen=True)
class Parameter:
    name: str
    description: str
    required: bool = True


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters: tuple[Parameter, ...] = ()


# Jeder Zug hat das Pflichtargument `warum`: keine Spiellogik, sondern damit Zuschauer und Log
# sehen, WARUM der Agent etwas tut.
_WHY = Parameter("warum", "Ein Satz: Warum tust du das?")

# =====================================================================================
# FREIE AKTIONEN (kosten keine Runde)
# =====================================================================================
FREE_ACTIONS: list[ToolSpec] = [
    ToolSpec("situation_lesen", "Liest die aktuelle Lage noch einmal (Ort, Szene, Objekte, Wege, Inventar)."),
    ToolSpec("inventar_ansehen", "Zeigt, was du bei dir trägst."),
    ToolSpec("notizbuch_lesen", "Liest dein Notizbuch."),
    ToolSpec("notizbuch_schreiben", "Hängt einen Eintrag an dein Notizbuch an (Codes, Hinweise, Ideen, Gelerntes).",
             (Parameter("text", "Der Eintrag."),)),
    ToolSpec("spielstand_speichern", "Speichert den Spielstand samt deinem Notizbuch. Nutze es VOR riskanten oder "
             "unumkehrbaren Entscheidungen. Deine Notiz erinnert dein späteres Ich, falls der Spielstand wieder geladen wird.",
             (Parameter("notiz", "Warnung/Erinnerung an dein späteres Ich: Was hast du vor, und warum ist es gefährlich?"),)),
    ToolSpec("was_weiss_ich_ueber", "Sucht in deinem Notizbuch und deinen letzten Zügen nach einem Ort oder Begriff. "
             "Fragt NICHT die Spielwelt.", (Parameter("begriff", "Ort oder Begriff, z. B. 'Schuppen'."),)),
]

# =====================================================================================
# ZÜGE (kosten genau eine Runde)
# =====================================================================================
MOVES: list[ToolSpec] = [
    ToolSpec("gehen", "Gehe zu einem Ort aus der Liste der begehbaren Wege.",
             (Parameter("ziel", "Name des Ortes, genau wie bei 'Begehbare Wege'."), _WHY)),
    ToolSpec("nehmen", "Nimm ein Objekt vom aktuellen Ort ins Inventar.",
             (Parameter("objekt", "Name des Objekts, genau wie bei 'Objekte hier'."), _WHY)),
    ToolSpec("ablegen", "Lege ein Objekt aus dem Inventar am aktuellen Ort ab.",
             (Parameter("objekt", "Name des Objekts aus deinem Inventar."), _WHY)),
    ToolSpec("anwenden", "Wende ein Objekt an, optional auf ein anderes Objekt (z. B. Schlüssel auf Schuppen).",
             (Parameter("objekt", "Das Objekt, das du anwendest (hier oder im Inventar)."),
              Parameter("auf", "Optional: das Zielobjekt.", required=False), _WHY)),
    ToolSpec("untersuchen", "Untersuche ein Objekt genauer (hier oder im Inventar).",
             (Parameter("objekt", "Name des Objekts."), _WHY)),
    ToolSpec("umsehen", "Sieh dich am aktuellen Ort um.", (_WHY,)),
    ToolSpec("geben", "Gib ein Objekt aus deinem Inventar an eine anwesende Figur.",
             (Parameter("objekt", "Objekt aus deinem Inventar."), Parameter("an", "Name der anwesenden Figur."), _WHY)),
    ToolSpec("angreifen", "Greife eine anwesende Figur an.", (Parameter("wen", "Name der anwesenden Figur."), _WHY)),
    ToolSpec("ansprechen", "Beginne ein Gespräch mit einer anwesenden Figur.",
             (Parameter("wen", "Name der anwesenden Figur."),
              Parameter("erste_nachricht", "Optional: womit du das Gespräch eröffnest.", required=False), _WHY)),
    ToolSpec("abwarten", "Tu eine Runde lang nichts.", (_WHY,)),
]

# =====================================================================================
# CHAT-WERKZEUGE (nur während eines Gesprächs; Spielzüge sind dort nicht erlaubt)
# =====================================================================================
CHAT_TOOLS: list[ToolSpec] = [
    ToolSpec("sage", "Sage deinem Gesprächspartner etwas. Du bekommst seine Antwort zurück.",
             (Parameter("text", "Was du sagst."),)),
    ToolSpec("gespraech_beenden", "Beende das Gespräch. Die Zusammenfassung wird in dein Notizbuch übernommen.",
             (Parameter("zusammenfassung", "Kurz für dein Notizbuch: Was hast du erfahren, was wurde vereinbart oder versprochen?"),)),
]

# =====================================================================================
# ERFAHRUNGS-WERKZEUG (nur beim Resümee nach dem Spiel, siehe experience.py)
# =====================================================================================
EXPERIENCE_TOOLS: list[ToolSpec] = [
    ToolSpec("erfahrung_notieren", "Hält eine Erkenntnis für künftige Spiele fest (ein kurzer, konkreter Satz).",
             (Parameter("erkenntnis", "Was du dir fürs nächste Spiel merkst."),)),
]

# =====================================================================================
# PIN-WERKZEUGE (nur, solange das PIN-Pad des Geldautomaten offen ist)
# =====================================================================================
PIN_TOOLS: list[ToolSpec] = [
    FREE_ACTIONS[2],                                    # notizbuch_lesen: die Zahl muss der Agent selbst gemerkt haben
    ToolSpec("pin_eingeben", "Gib die vierstellige Geheimzahl am Geldautomaten ein.",
             (Parameter("ziffern", "Genau vier Ziffern, z. B. '0815'."),)),
]

FREE_NAMES = {w.name for w in FREE_ACTIONS}
MOVE_NAMES = {w.name for w in MOVES}


# =====================================================================================
# Prüfung und Übersetzung der Züge
# =====================================================================================
def _find(wanted: str, candidates: list[str]) -> str | None:
    """Findet einen Namen aus der Liste (Groß-/Kleinschreibung egal)."""
    g = str(wanted).strip().lower()
    return next((k for k in candidates if k.lower() == g), None)


def _way_names(view: dict) -> list[str]:
    return list(view.get("environment", {}).get("ways", []))


def prepare_move(name: str, args: dict, view: dict) -> tuple[dict | None, str]:
    """Prüft einen Zug gegen das, was der Agent sehen kann, und übersetzt ihn in das Format der Engine.

    Rückgabe: (function_call, "")  bei Erfolg, sonst (None, Fehlermeldung).

    LERNPUNKT (hier verhindern wir, dass der Agent schummelt UND dass er Runden verschwendet):
    Der Agent kennt nur Rufnamen, die er in der Beobachtung sieht. Etwas, das er nicht sehen
    kann, wird abgewiesen – mit einer verständlichen Meldung als Werkzeugergebnis und OHNE Runde.
    Die Übersetzung Rufname -> interne ID macht die Engine (obj_name_from_friendly_name) selbst,
    das Modell sieht nie eine ID.
    """
    env = view.get("environment", {})
    here = list(env.get("objects", []))
    inventory = list(view.get("player", {}).get("inventory", []))
    characters = present_characters(view)

    def object_here_or_carried(n: str) -> tuple[str | None, str]:
        found = _find(n, here + inventory)
        if found:
            return found, ""
        return None, f"'{n}' ist weder hier noch in deinem Inventar. Objekte hier: {', '.join(here) or 'keine'}. Inventar: {', '.join(inventory) or 'leer'}."

    def character(n: str) -> tuple[str | None, str]:
        found = _find(n, characters)
        if found:
            return found, ""
        return None, f"'{n}' ist nicht hier. Anwesend: {', '.join(characters) or 'niemand'}."

    def fc(verb: str, **verb_args) -> tuple[dict, str]:
        return {"function_call": {"name": verb, "args": verb_args}}, ""

    if name == "gehen":
        target = args.get("ziel", "")
        found = _find(target, _way_names(view))
        if found:
            return fc("gehe", direction=found)
        blocked = [b for b in env.get("blockedWays", []) if b.lower().startswith(str(target).strip().lower())]
        if blocked:
            return None, f"Der Weg ist versperrt: {blocked[0]}"
        return None, f"Dorthin führt kein sichtbarer Weg. Begehbare Wege: {', '.join(_way_names(view)) or 'keine'}."
    if name == "nehmen":
        found = _find(args.get("objekt", ""), here)
        if found:
            return fc("nimm", whato=found)
        return None, f"'{args.get('objekt', '')}' liegt hier nicht herum. Objekte hier: {', '.join(here) or 'keine'}."
    if name == "ablegen":
        found = _find(args.get("objekt", ""), inventory)
        if found:
            return fc("ablegen", whato=found)
        return None, f"'{args.get('objekt', '')}' hast du nicht bei dir. Inventar: {', '.join(inventory) or 'leer'}."
    if name == "untersuchen":
        found, error = object_here_or_carried(args.get("objekt", ""))
        return fc("untersuche", what=found) if found else (None, error)
    if name == "anwenden":
        found, error = object_here_or_carried(args.get("objekt", ""))
        if not found:
            return None, error
        if args.get("auf"):
            target, error = object_here_or_carried(args["auf"])
            return fc("anwenden", what=found, towhat=target) if target else (None, error)
        return fc("anwenden", what=found)
    if name == "umsehen":
        return fc("umsehen")
    if name == "abwarten":
        return fc("nichts")
    if name == "geben":
        obj = _find(args.get("objekt", ""), inventory)
        if not obj:
            return None, f"'{args.get('objekt', '')}' hast du nicht bei dir. Inventar: {', '.join(inventory) or 'leer'}."
        recipient, error = character(args.get("an", ""))
        return fc("gib", what=obj, towhom=recipient) if recipient else (None, error)
    if name == "angreifen":
        whom, error = character(args.get("wen", ""))
        return fc("angreifen", whom=whom) if whom else (None, error)
    if name == "ansprechen":
        whom, error = character(args.get("wen", ""))
        if not whom:
            return None, error
        return fc("interagieren", who=whom, firstmessage=str(args.get("erste_nachricht", "") or ""))
    return None, f"Unbekannter Zug '{name}'."
