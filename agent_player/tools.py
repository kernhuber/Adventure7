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

from agent_player.observation import anwesende_figuren


@dataclass(frozen=True)
class Parameter:
    name: str
    beschreibung: str
    pflicht: bool = True


@dataclass(frozen=True)
class Werkzeug:
    name: str
    beschreibung: str
    parameter: tuple[Parameter, ...] = ()


# Jeder Zug hat das Pflichtargument `warum`: keine Spiellogik, sondern damit Zuschauer und Log
# sehen, WARUM der Agent etwas tut.
_WARUM = Parameter("warum", "Ein Satz: Warum tust du das?")

# =====================================================================================
# FREIE AKTIONEN (kosten keine Runde)
# =====================================================================================
FREIE_AKTIONEN: list[Werkzeug] = [
    Werkzeug("situation_lesen", "Liest die aktuelle Lage noch einmal (Ort, Szene, Objekte, Wege, Inventar)."),
    Werkzeug("inventar_ansehen", "Zeigt, was du bei dir trägst."),
    Werkzeug("notizbuch_lesen", "Liest dein Notizbuch."),
    Werkzeug("notizbuch_schreiben", "Hängt einen Eintrag an dein Notizbuch an (Codes, Hinweise, Ideen, Gelerntes).",
             (Parameter("text", "Der Eintrag."),)),
    Werkzeug("spielstand_speichern", "Speichert den Spielstand samt deinem Notizbuch. Nutze es VOR riskanten oder "
             "unumkehrbaren Entscheidungen. Deine Notiz erinnert dein späteres Ich, falls der Spielstand wieder geladen wird.",
             (Parameter("notiz", "Warnung/Erinnerung an dein späteres Ich: Was hast du vor, und warum ist es gefährlich?"),)),
    Werkzeug("was_weiss_ich_ueber", "Sucht in deinem Notizbuch und deinen letzten Zügen nach einem Ort oder Begriff. "
             "Fragt NICHT die Spielwelt.", (Parameter("begriff", "Ort oder Begriff, z. B. 'Schuppen'."),)),
]

# =====================================================================================
# ZÜGE (kosten genau eine Runde)
# =====================================================================================
ZUEGE: list[Werkzeug] = [
    Werkzeug("gehen", "Gehe zu einem Ort aus der Liste der begehbaren Wege.",
             (Parameter("ziel", "Name des Ortes, genau wie bei 'Begehbare Wege'."), _WARUM)),
    Werkzeug("nehmen", "Nimm ein Objekt vom aktuellen Ort ins Inventar.",
             (Parameter("objekt", "Name des Objekts, genau wie bei 'Objekte hier'."), _WARUM)),
    Werkzeug("ablegen", "Lege ein Objekt aus dem Inventar am aktuellen Ort ab.",
             (Parameter("objekt", "Name des Objekts aus deinem Inventar."), _WARUM)),
    Werkzeug("anwenden", "Wende ein Objekt an, optional auf ein anderes Objekt (z. B. Schlüssel auf Schuppen).",
             (Parameter("objekt", "Das Objekt, das du anwendest (hier oder im Inventar)."),
              Parameter("auf", "Optional: das Zielobjekt.", pflicht=False), _WARUM)),
    Werkzeug("untersuchen", "Untersuche ein Objekt genauer (hier oder im Inventar).",
             (Parameter("objekt", "Name des Objekts."), _WARUM)),
    Werkzeug("umsehen", "Sieh dich am aktuellen Ort um.", (_WARUM,)),
    Werkzeug("geben", "Gib ein Objekt aus deinem Inventar an eine anwesende Figur.",
             (Parameter("objekt", "Objekt aus deinem Inventar."), Parameter("an", "Name der anwesenden Figur."), _WARUM)),
    Werkzeug("angreifen", "Greife eine anwesende Figur an.", (Parameter("wen", "Name der anwesenden Figur."), _WARUM)),
    Werkzeug("ansprechen", "Beginne ein Gespräch mit einer anwesenden Figur.",
             (Parameter("wen", "Name der anwesenden Figur."),
              Parameter("erste_nachricht", "Optional: womit du das Gespräch eröffnest.", pflicht=False), _WARUM)),
    Werkzeug("abwarten", "Tu eine Runde lang nichts.", (_WARUM,)),
]

# =====================================================================================
# CHAT-WERKZEUGE (nur während eines Gesprächs; Spielzüge sind dort nicht erlaubt)
# =====================================================================================
CHAT_WERKZEUGE: list[Werkzeug] = [
    Werkzeug("sage", "Sage deinem Gesprächspartner etwas. Du bekommst seine Antwort zurück.",
             (Parameter("text", "Was du sagst."),)),
    Werkzeug("gespraech_beenden", "Beende das Gespräch. Die Zusammenfassung wird in dein Notizbuch übernommen.",
             (Parameter("zusammenfassung", "Kurz für dein Notizbuch: Was hast du erfahren, was wurde vereinbart oder versprochen?"),)),
]

# =====================================================================================
# ERFAHRUNGS-WERKZEUG (nur beim Resümee nach dem Spiel, siehe experience.py)
# =====================================================================================
ERFAHRUNG_WERKZEUGE: list[Werkzeug] = [
    Werkzeug("erfahrung_notieren", "Hält eine Erkenntnis für künftige Spiele fest (ein kurzer, konkreter Satz).",
             (Parameter("erkenntnis", "Was du dir fürs nächste Spiel merkst."),)),
]

# =====================================================================================
# PIN-WERKZEUGE (nur, solange das PIN-Pad des Geldautomaten offen ist)
# =====================================================================================
PIN_WERKZEUGE: list[Werkzeug] = [
    FREIE_AKTIONEN[2],                                    # notizbuch_lesen: die Zahl muss der Agent selbst gemerkt haben
    Werkzeug("pin_eingeben", "Gib die vierstellige Geheimzahl am Geldautomaten ein.",
             (Parameter("ziffern", "Genau vier Ziffern, z. B. '0815'."),)),
]

FREIE_NAMEN = {w.name for w in FREIE_AKTIONEN}
ZUG_NAMEN = {w.name for w in ZUEGE}


# =====================================================================================
# Prüfung und Übersetzung der Züge
# =====================================================================================
def _finde(gesucht: str, kandidaten: list[str]) -> str | None:
    """Findet einen Namen aus der Liste (Groß-/Kleinschreibung egal)."""
    g = str(gesucht).strip().lower()
    return next((k for k in kandidaten if k.lower() == g), None)


def _wege_namen(ansicht: dict) -> list[str]:
    return list(ansicht.get("environment", {}).get("ways", []))


def zug_vorbereiten(name: str, args: dict, ansicht: dict) -> tuple[dict | None, str]:
    """Prüft einen Zug gegen das, was der Agent sehen kann, und übersetzt ihn in das Format der Engine.

    Rückgabe: (function_call, "")  bei Erfolg, sonst (None, Fehlermeldung).

    LERNPUNKT (hier verhindern wir, dass der Agent schummelt UND dass er Runden verschwendet):
    Der Agent kennt nur Rufnamen, die er in der Beobachtung sieht. Etwas, das er nicht sehen
    kann, wird abgewiesen – mit einer verständlichen Meldung als Werkzeugergebnis und OHNE Runde.
    Die Übersetzung Rufname -> interne ID macht die Engine (obj_name_from_friendly_name) selbst,
    das Modell sieht nie eine ID.
    """
    umg = ansicht.get("environment", {})
    hier = list(umg.get("objects", []))
    inventar = list(ansicht.get("player", {}).get("inventory", []))
    figuren = anwesende_figuren(ansicht)

    def objekt_hier_oder_dabei(n: str) -> tuple[str | None, str]:
        treffer = _finde(n, hier + inventar)
        if treffer:
            return treffer, ""
        return None, f"'{n}' ist weder hier noch in deinem Inventar. Objekte hier: {', '.join(hier) or 'keine'}. Inventar: {', '.join(inventar) or 'leer'}."

    def figur(n: str) -> tuple[str | None, str]:
        treffer = _finde(n, figuren)
        if treffer:
            return treffer, ""
        return None, f"'{n}' ist nicht hier. Anwesend: {', '.join(figuren) or 'niemand'}."

    def fc(verb: str, **verb_args) -> tuple[dict, str]:
        return {"function_call": {"name": verb, "args": verb_args}}, ""

    if name == "gehen":
        ziel = args.get("ziel", "")
        treffer = _finde(ziel, _wege_namen(ansicht))
        if treffer:
            return fc("gehe", direction=treffer)
        gesperrt = [b for b in umg.get("blockedWays", []) if b.lower().startswith(str(ziel).strip().lower())]
        if gesperrt:
            return None, f"Der Weg ist versperrt: {gesperrt[0]}"
        return None, f"Dorthin führt kein sichtbarer Weg. Begehbare Wege: {', '.join(_wege_namen(ansicht)) or 'keine'}."
    if name == "nehmen":
        treffer = _finde(args.get("objekt", ""), hier)
        if treffer:
            return fc("nimm", whato=treffer)
        return None, f"'{args.get('objekt', '')}' liegt hier nicht herum. Objekte hier: {', '.join(hier) or 'keine'}."
    if name == "ablegen":
        treffer = _finde(args.get("objekt", ""), inventar)
        if treffer:
            return fc("ablegen", whato=treffer)
        return None, f"'{args.get('objekt', '')}' hast du nicht bei dir. Inventar: {', '.join(inventar) or 'leer'}."
    if name == "untersuchen":
        treffer, fehler = objekt_hier_oder_dabei(args.get("objekt", ""))
        return fc("untersuche", what=treffer) if treffer else (None, fehler)
    if name == "anwenden":
        treffer, fehler = objekt_hier_oder_dabei(args.get("objekt", ""))
        if not treffer:
            return None, fehler
        if args.get("auf"):
            ziel, fehler = objekt_hier_oder_dabei(args["auf"])
            return fc("anwenden", what=treffer, towhat=ziel) if ziel else (None, fehler)
        return fc("anwenden", what=treffer)
    if name == "umsehen":
        return fc("umsehen")
    if name == "abwarten":
        return fc("nichts")
    if name == "geben":
        objekt = _finde(args.get("objekt", ""), inventar)
        if not objekt:
            return None, f"'{args.get('objekt', '')}' hast du nicht bei dir. Inventar: {', '.join(inventar) or 'leer'}."
        an, fehler = figur(args.get("an", ""))
        return fc("gib", what=objekt, towhom=an) if an else (None, fehler)
    if name == "angreifen":
        wen, fehler = figur(args.get("wen", ""))
        return fc("angreifen", whom=wen) if wen else (None, fehler)
    if name == "ansprechen":
        wen, fehler = figur(args.get("wen", ""))
        if not wen:
            return None, fehler
        return fc("interagieren", who=wen, firstmessage=str(args.get("erste_nachricht", "") or ""))
    return None, f"Unbekannter Zug '{name}'."
