import os
from typing import List, Dict, Any, TypedDict
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
import re

# Google API Key (Du musst deinen eigenen API-Key hier eintragen)
# os.environ["GOOGLE_API_KEY"] = "dein-google-api-key"
os.environ["GOOGLE_API_KEY"] = "AIzaSyBAD9VSVcw47HSj6I63qSGpY4vuuu7WXTA"

# Initialisiere das Gemini-Modell
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")


# Spielzustand definieren
class GameState(TypedDict):
    messages: List[Dict[str, Any]]  # Chat-Verlauf
    current_room: str  # Aktueller Raum-ID
    inventory: List[str]  # Gegenstände, die der Spieler trägt
    discovered: Dict[str, bool]  # Spezielle Zustandsflags (z.B. gefundene Gegenstände)
    visited_rooms: List[str]  # Räume, die der Spieler besucht hat
    debug_mode: bool  # Schalter für Debug-Informationen
    game_over: bool  # Flag, um das Spiel zu beenden


# System-Prompt wie in der Beschreibung angegeben
SYSTEM_PROMPT = """
Du bist Parser UND Erzähler eines textbasierten Abenteuerspiels.

Bei jeder Benutzereingabe lieferst du sowohl einen Content als auch einen Tool-Call. Achte darauf, 
die Himmelsrichtungen (Norden, Süden, Osten, Westen) innerhalb eines Raumes und beim Übergang zwischen Räumen konsistent 
zu behandeln. Hier die generellen Regeln. Generell lieferst Du für jeden Raum:

1. Eine kurze, atmosphärische Beschreibung der Handlung im Textfeld (content) – z.B.:

   "Du bückst dich und hebst das Kissen auf. Darunter liegt etwas Glänzendes."

2. Eine oder mehrere Funktionsaufrufe (ToolCalls), mit denen das Spielsystem die Welt verändern kann.

Beispiel:

Spielereingabe:
"Ich nehme das Kissen und öffne die Tür nach Norden."

Antwort:

Content:
"Du nimmst das Kissen an dich. Dahinter entdeckst du einen alten Schlüssel. Mit einem Knacken öffnet sich die Tür."

ToolCalls:
- nimm("kissen")
- nimm("schlüssel")
- benutze("schlüssel", "norden")
- gehe("norden")

Wenn der Spieler „Q", „Quit" oder „Ende" eingibt, ist das ein Wunsch, das Spiel zu verlassen.
In diesem Fall sollst du die Funktion `beenden()` aufrufen.

---

### 🧠 Wichtig für den Spielablauf:

Jede Antwort muss einen kurzen Text im Feld `content` enthalten – auch wenn nur ToolCalls zurückgegeben werden.  
Wenn du nichts beschreiben möchtest, gib einen Platzhalter-Text wie z. B.  
- "(Du führst die Aktion aus.)"  
- "(Nichts weiter geschieht.)"  
- oder einen stimmungsvollen Erzählerkommentar an.  
- Gib niemals eine Antwort ohne `content`.
- Erwähne immer alle Türen und Wege des Raums; beschreibe dem Spieler, wohin er gehen kann

---

### 🎮 Deine Regeln für das Spiel:

* Wenn Du um Hilfe gebeten wirst, hilf dem Spieler gemäß den Anweisungen in den einzelnen Räumen, und
  liefere 'nop()' zurück.
* Wenn der Spieler sehen möchte, was er dabei hat, bzw. was er schon aufgesammelt hat, oder was er im
  "Inventory hat", dann liefere 'inventory()' zurück
* Wenn der Spieler den Debug-Modus an oder ausschalten will, dann liefere 'debug("an")' oder debug("aus") 
  zurück, je nachdem was der Spieler wünscht. Wenn der Spieler nur den Status des Debug-Modus wissen will,
  dann liefere 'debug("status")' zurück
* Wenn Du einen Raum beschreiben sollst, so beschreibe den Raum gemäß den Anweisungen in den einzelnen 
  Räumen, danach lieferst Du 'nop()' zurück
* Du darfst mehrere Tool-Calls gleichzeitig ausgeben, wenn sinnvoll.
* Du darfst **implizite Aktionen erkennen** – z.B. wenn jemand „Ich gehe in die Bibliothek" sagt, dann:
   - `benutze("schlüssel", "norden")`
   - `gehe("norden")`
* Verwende nur Objekte, Räume und Richtungen, die dir bekannt sind.
* Der Spieler kann die Tür angeben, durch die er gehen will (Beispiel: "Gehe durch die Tür im Norden"), er kann 
  aber auch nur die Richtung angeben, in die er gehen will (Beispiel: "Gehe nach westen"). Liefere in allen Fällen
  -- Eine Bestätigung als content, etwa: "Du gehst durch die Tür im Westen"
  -- den korrekten Tool-call 'gehe()'
* Wenn du etwas nicht nnst (z.B. Tür verschlossen, kein Objekt vorhanden), überlasse die Erklärung dem Spielsystem.

---

### 🧰 Verfügbare Funktionen:

- `umsehen()` → beschreibt den aktuellen Raum
- `untersuche(gegenstand)` → untersucht ein Objekt
- `nimm(gegenstand)` → nimmt ein Objekt ins Inventar
- `benutze(gegenstand, ziel)` → verwendet z.B. Schlüssel auf Tür
- `gehe(richtung)` → geht in einen anderen Raum
- `eingabe_code(code)` → gibt einen vierstelligen Code ein
- `hilfe()` → gibt einen Hinweis, was der Spieler tun könnte
- `beenden()` → beendet das Spiel
- `inventory()` → Zeigt das Inventory an (also alles, was der Spieler aufgesammelt hat)
- `debug(modus)` → Schaltet den Debug-Modus an oder aus
- `nop()` → "No Operation".

---

Verwende in jeder Antwort mindestens einen passenden Funktionsaufruf, sofern dies durch die Eingabe des Spielers sinnvoll ausgelöst wird.
"""

# Räume definieren
ROOMS = {
    "start": {
        "beschreibung": "Du wachst in einem schlichten Zimmer auf. Es gibt ein Bett mit einem Kissen darauf. In der Ecke stehen eine Schaufel und eine Schere. Eine Nudelpackung liegt auf dem Boden. Es gibt zwei Türen: nach Westen (offen) und nach Norden (verschlossen).",
        "hinweis": "Vielleicht solltest du dich umsehen oder das Kissen genauer betrachten.",
        "gegenstaende": ["schaufel", "schere", "nudelpackung", "kissen"],
        "tueren": {
            "norden": {"ziel": "bibliothek", "verschlossen": True, "benoetigt": "schlüssel"},
            "westen": {"ziel": "durchgang", "verschlossen": False}
        },
        "extra_prompt": """
        Wenn der Spieler sich umsieht, beschreibe ihm den Raum. Dabei kannst Du etwas geheimnisvoll tun. Du bist ein guter Erzähler.
        * Beschreibe alle Objekte im Raum und auch alle Türen und Durchgänge. 
        * Wenn eine Tür verschlossen ist, erwähne das extra. 
        * Wenn der Spieler um Hilfe bittet, weise ihn darauf hin, dass das Kissen doch sehr weich aussieht.
        * Unter dem Kissen befindet sich ein Schlüssel, den der Spieler aber am Anfang nicht sieht.
        * Wenn der Spieler das Kissen untersucht oder aufnimmt, erwähne den Schlüssel unter dem Kissen
        """
    },
    "durchgang": {
        "beschreibung": "Ein schmuckloser Raum mit kahlen Wänden. Auf einem alten Stuhl liegt ein Kochlöffel. Eine Luftpumpe lehnt an der Wand. Ein Radio steht auf einem kleinen Tisch und spielt leise vor sich hin. Türen führen nach Osten und Westen.",
        "hinweis": "Vielleicht findest du hier etwas Nützliches oder auch nicht.",
        "gegenstaende": ["radio", "luftpumpe", "kochlöffel"],
        "tueren": {
            "osten": {"ziel": "start", "verschlossen": False},
            "westen": {"ziel": "endraum", "verschlossen": False}
        },
        "extra_prompt": """
            Wenn der Spieler sich umsieht, beschreibe den Raum und erwähne, dass der Stuhl mit dem Kochlöffel im Osten steht und die Luftpumpe im Westen lehnt. Erwähne auch das Radio und die Türen nach Osten (zum Startraum) und Westen (zum Endraum).
    Wenn der Spieler um Hilfe bittet, erwähne, dass er Gegenstände untersuchen und die Türen nach Osten (zum Startraum) oder Westen (zum Endraum) nutzen kann.
    Beschreibe die Gegenstände humorvoll, wenn der Spieler sie untersucht.
        """
    },
    "bibliothek": {
        "beschreibung": """
        Du befindest dich in einer geheimen, staubigen Bibliothek. Bücher in unbekannter Sprache füllen die Regale. 
        In der Ecke steht ein alter Ohrensessel. Es war lange niemand mehr hier, 
        deswegen ist alles mit Staub und Spinnweben überzogen. In einer Ecke des Raums befindet sich ein verschlissener 
        Ohrensessel, daneben ein kleiner Tisch. Der Ohrensessel war bestimmt einmal gemütlich, aber er ist nun mit Staub 
        bedeckt, und eine fette Spinne hat sich oben rechts auf ihm eingenistet und ein Spinnennetz 
        zwischen Sessel und Tisch gebaut. Auf dem Tisch liegt ein geheimnisvolles Buch.
        """,
        "hinweis": "Das Buch auf dem Tisch sieht anders aus als die anderen.",
        "gegenstaende": ["sessel", "tisch", "geheimnisvolles_buch"],
        "tueren": {
            "sueden": {"ziel": "start", "verschlossen": False}
        },
        "extra_prompt": """Du bist ein guter Erzähler! Wenn der Spieler sich umsieht, beschreibe ihm den Raum, alle Objekte
        und die Tür, die der einzige Ausgang ist.
        * Wenn der Spieler sich umsieht musst du ihm den Raum beschreiben, dabei 
          kannst du ihn in recht düsteren Worten beschreiben. 
        * Der Spieler kann sich auch einzelne Bücher aus den Regalen ansehen, aber sie sind in 
          Geheimschrift verfasst, sodass der Spieler sie nicht verstehen kann. Das gilt nur für die Bücher im regal.
        * Das Buch auf dem Tisch kann der spieler untersuchen. Sobald er das tut, musst du ihn auf den Geheimcode hinweisen.
        * Wenn der Spieler das geheimnisvolle Buch auf dem Tisch untersucht findet er darin einen vierstelligen Geheimcode.
        * Der Spieler erfährt den Geheimcode dadurch, dass er das geheimnisvolle Buch untersucht. Wenn er das Buch untersucht, gib ihm den Geheimcode
        * Der Spieler kann nur durch die Türe gehen, durch die er gekommen ist.
        """
    },
    "endraum": {
        "beschreibung": "Ein karger Betonraum mit einem Tastenfeld an der westlichen Wand. Sonst ist der Raum leer.",
        "hinweis": "Vielleicht brauchst du einen Code, um weiterzukommen.",
        "gegenstaende": [],
        "tueren": {
            "osten": {"ziel": "durchgang", "verschlossen": False},
            "westen": {"ziel": "freiheit", "verschlossen": True, "code": True}
        },
        "extra_prompt": """
        Der Endraum enthält nichts außer dem Tastenfeld an der westlichen Wand. Weisen Sie den Spieler darauf hin, dass er einen Code eingeben muss, 
        um weiterzukommen. Der korrekte Code ist 4283, den der Spieler im geheimnisvollen Buch in der Bibliothek gefunden haben sollte.
        """
    },
    "freiheit": {
        "beschreibung": "Du trittst hinaus auf eine sonnige Sommerwiese. Du hast das Spiel erfolgreich beendet!",
        "hinweis": "",
        "gegenstaende": [],
        "tueren": {},
        "extra_prompt": """
        Dies ist der Gewinnerraum. Gratuliere dem Spieler zum erfolgreichen Abschluss des Spiels. Er kann hier nichts weiter tun.
        """
    }
}

# Gegenstände definieren
ITEMS = {
    "schaufel": {
        "hinweis": "Eine rostige alte Schaufel. Vielleicht mal nützlich gewesen.",
    },
    "schere": {
        "hinweis": "Eine stumpfe Bastelschere. Nicht gefährlich.",
    },
    "nudelpackung": {
        "hinweis": "Eine halb volle Packung Spaghetti. Haltbar bis 2027.",
    },
    "kissen": {
        "hinweis": "Ein gemütliches Kissen. Vielleicht liegt etwas darunter?",
    },
    "schlüssel": {
        "hinweis": "Ein kleiner, leicht angerosteter Schlüssel.",
        "sichtbar": False,  # Anfangs unter dem Kissen versteckt
    },
    "radio": {
        "hinweis": "Ein altes Radio, aus dem leise Musik dringt.",
    },
    "luftpumpe": {
        "hinweis": "Eine quietschende Luftpumpe.",
    },
    "kochlöffel": {
        "hinweis": "Ein Holzlöffel mit eingebrannter Gravur: 'Mama'.",
    },
    "geheimnisvolles_buch": {
        "hinweis": "Ein altes, schweres Buch mit mystischem Einband.",
        "code": "4283"
    },
    "sessel": {
        "hinweis": "Ein alter Sessel mit staubigen Armlehnen.",
        "nimmbar": False
    },
    "tisch": {
        "hinweis": "Ein kleiner Tisch aus dunklem Holz.",
        "nimmbar": False
    }
}


# Hilfsfunktionen für spezielle Spielmechaniken
def _entdecke_schluessel(state):
    """Entdeckt den Schlüssel unter dem Kissen."""
    if "schlüssel" not in state["inventory"] and "kissen" in ROOMS[state["current_room"]]["gegenstaende"]:
        # Mache den Schlüssel sichtbar und verfügbar
        ITEMS["schlüssel"]["sichtbar"] = True
        if "schlüssel" not in ROOMS[state["current_room"]]["gegenstaende"]:
            ROOMS[state["current_room"]]["gegenstaende"].append("schlüssel")
        state["discovered"]["schlüssel_entdeckt"] = True
        return "Du findest einen kleinen, rostigen Schlüssel unter dem Kissen!"
    return "Du untersuchst das Kissen. Es ist weich und gemütlich."


def _entdecke_geheimnummer(state):
    """Entdeckt den Geheimcode im mysteriösen Buch."""
    state["discovered"]["code_entdeckt"] = True
    return f"Du blätterst durch das mysteriöse Buch und findest eine Seite mit einer handgeschriebenen Notiz: 'Der Code lautet {ITEMS['geheimnisvolles_buch']['code']}'"


# Tool-Funktionen, die vom LLM aufgerufen werden können
def umsehen(state):
    """Schaut sich im aktuellen Raum um."""
    current_room = state["current_room"]
    room_info = ROOMS[current_room]

    # Markiere den Raum als besucht
    if current_room not in state["visited_rooms"]:
        state["visited_rooms"].append(current_room)

    # Gib die Raumbeschreibung zurück
    return room_info["beschreibung"]


def untersuche(state, gegenstand):
    """Untersucht einen Gegenstand im Raum."""
    current_room = state["current_room"]

    # Prüfe, ob der Gegenstand im Raum oder Inventar ist
    if gegenstand in ROOMS[current_room]["gegenstaende"] or gegenstand in state["inventory"]:
        # Prüfe auf spezielle Interaktionen
        if gegenstand == "kissen" and state["current_room"] == "start":
            return _entdecke_schluessel(state)
        elif gegenstand == "geheimnisvolles_buch" and state["current_room"] == "bibliothek":
            return _entdecke_geheimnummer(state)
        elif gegenstand in ITEMS:
            return ITEMS[gegenstand]["hinweis"]
        else:
            return f"Du untersuchst {gegenstand}, findest aber nichts Besonderes."
    else:
        return f"Hier gibt es kein {gegenstand} zum Untersuchen."


def nimm(state, gegenstand):
    """Nimmt einen Gegenstand auf und fügt ihn dem Inventar hinzu."""
    current_room = state["current_room"]

    # Prüfe, ob der Gegenstand im Raum ist
    if gegenstand in ROOMS[current_room]["gegenstaende"]:
        # Prüfe, ob der Gegenstand aufnehmbar ist
        if gegenstand in ITEMS and ITEMS.get(gegenstand, {}).get("nimmbar", True) == False:
            return f"Du kannst {gegenstand} nicht mitnehmen."

        # Spezialfall für das Kissen - enthülle den Schlüssel
        if gegenstand == "kissen" and state["current_room"] == "start":
            _entdecke_schluessel(state)

        # Zum Inventar hinzufügen und aus dem Raum entfernen
        if gegenstand not in state["inventory"]:
            state["inventory"].append(gegenstand)
            ROOMS[current_room]["gegenstaende"].remove(gegenstand)
            return f"Du nimmst {gegenstand} auf und steckst es ein."
        else:
            return f"Du hast {gegenstand} bereits bei dir."
    else:
        return f"Hier gibt es kein {gegenstand} zum Aufnehmen."


def benutze(state, gegenstand, ziel):
    """Verwendet einen Gegenstand auf ein Ziel (z.B. Schlüssel an Tür)."""
    current_room = state["current_room"]

    # Prüfe, ob der Gegenstand im Inventar ist
    if gegenstand not in state["inventory"]:
        return f"Du hast kein {gegenstand} zum Benutzen."

    # Prüfe, ob ein Schlüssel an einer Tür verwendet wird
    if gegenstand == "schlüssel" and ziel in ROOMS[current_room]["tueren"]:
        door = ROOMS[current_room]["tueren"][ziel]
        if door["verschlossen"] and door.get("benoetigt") == "schlüssel":
            door["verschlossen"] = False
            return f"Du benutzt den Schlüssel an der Tür nach {ziel}. Die Tür ist jetzt aufgeschlossen."
        elif not door["verschlossen"]:
            return f"Die Tür nach {ziel} ist bereits aufgeschlossen."
        else:
            return f"Der Schlüssel passt nicht zur Tür nach {ziel}."

    # Generischer Anwendungsfall
    return f"Du versuchst, {gegenstand} auf {ziel} anzuwenden, aber nichts passiert."


def gehe(state, richtung):
    """Bewegt sich in einen anderen Raum in der angegebenen Richtung."""
    current_room = state["current_room"]

    # Prüfe, ob es eine Tür in der angegebenen Richtung gibt
    if richtung in ROOMS[current_room]["tueren"]:
        door = ROOMS[current_room]["tueren"][richtung]

        # Prüfe, ob die Tür verschlossen ist
        if door["verschlossen"]:
            if door.get("code", False):
                return f"Die Tür nach {richtung} hat ein Codeschloss. Du musst zuerst den richtigen Code eingeben."
            else:
                return f"Die Tür nach {richtung} ist verschlossen. Vielleicht brauchst du einen Schlüssel?"

        # Wechsle den Raum
        next_room = door["ziel"]
        state["current_room"] = next_room

        # Markiere den neuen Raum als besucht
        if next_room not in state["visited_rooms"]:
            state["visited_rooms"].append(next_room)

        return f"Du gehst durch die Tür nach {richtung} und befindest dich nun in: {ROOMS[next_room]['beschreibung']}"
    else:
        return f"Es gibt keine Tür in Richtung {richtung}."


def eingabe_code(state, code):
    """Gibt einen vierstelligen Code ein, z.B. für eine Tür mit Codeschloss."""
    current_room = state["current_room"]

    # Prüfe, ob wir im Endraum sind und die westliche Tür einen Code hat
    if current_room == "endraum" and "westen" in ROOMS[current_room]["tueren"]:
        door = ROOMS[current_room]["tueren"]["westen"]

        if door.get("code", False) and code == ITEMS["geheimnisvolles_buch"]["code"]:
            # Code ist korrekt
            door["verschlossen"] = False
            return "Das Tastenfeld blinkt grün auf. Mit einem Klicken öffnet sich die Tür nach Westen."
        else:
            return "Das Tastenfeld blinkt rot. Der Code scheint falsch zu sein."
    else:
        return "Hier gibt es kein Codeschloss, für das du einen Code eingeben könntest."


def hilfe(state):
    """Gibt einen Hinweis zum aktuellen Raum."""
    current_room = state["current_room"]
    return ROOMS[current_room]["hinweis"]


def beenden(state):
    """Beendet das Spiel."""
    state["game_over"] = True
    return "Das Spiel wird beendet. Danke fürs Spielen!"


def inventory(state):
    """Zeigt das Inventar des Spielers an."""
    if not state["inventory"]:
        return "Dein Inventar ist leer."
    else:
        return f"In deinem Inventar befinden sich: {', '.join(state['inventory'])}"


def debug(state, modus):
    """Schaltet den Debug-Modus an oder aus."""
    if modus == "an":
        state["debug_mode"] = True
        return "Debug-Modus ist jetzt aktiviert."
    elif modus == "aus":
        state["debug_mode"] = False
        return "Debug-Modus ist jetzt deaktiviert."
    elif modus == "status":
        status = "aktiviert" if state["debug_mode"] else "deaktiviert"
        return f"Debug-Modus ist aktuell {status}."
    else:
        return f"Ungültiger Debug-Modus: {modus}"


def nop(state):
    """No Operation - tut nichts."""
    return "Keine Aktion ausgeführt."


# Funktionsregister (wird vom LLM referenziert)
FUNCTION_MAP = {
    "umsehen": umsehen,
    "untersuche": untersuche,
    "nimm": nimm,
    "benutze": benutze,
    "gehe": gehe,
    "eingabe_code": eingabe_code,
    "hilfe": hilfe,
    "beenden": beenden,
    "inventory": inventory,
    "debug": debug,
    "nop": nop
}


# Funktion zum Parsen der Tool-Calls aus der LLM-Antwort
def parse_tool_calls(response):
    """Extrahiert die Tool-Calls aus der LLM-Antwort."""
    # Regex-Muster für Tool-Calls wie: nimm("kissen"), benutze("schlüssel", "tür"), etc.
    # pattern = r'([a-zA-Z_]+)\("([^"]*)(?:"(?:\s*,\s*"([^"]*)")?)?(?:\)'
    pattern = r'([a-zA-Z_]+)\("([^"]*)"(?:\s*,\s*"([^"]*)")?\)'

    # Alle Treffer finden
    matches = re.findall(pattern, response)

    # Als Liste von Dictionaries zurückgeben
    tool_calls = []
    for match in matches:
        function_name = match[0]
        args = [arg for arg in match[1:] if arg]  # Leere Argumente entfernen

        tool_calls.append({
            "name": function_name,
            "arguments": args
        })

    return tool_calls


# Funktion zum Erstellen eines Raum-Prompts mit Kontext
def create_room_prompt(state):
    """Erstellt einen kontextspezifischen Prompt für den aktuellen Raum."""
    current_room = state["current_room"]
    room_info = ROOMS[current_room]

    # Basis-Prompt mit System-Prompt
    prompt = SYSTEM_PROMPT

    # Raum-spezifische zusätzliche Anweisungen
    if "extra_prompt" in room_info:
        prompt += "\n\n" + room_info["extra_prompt"]

    # Informationen über aktuellen Raum
    prompt += f"\n\nAktueller Raum: {current_room}"
    prompt += f"\nRaumbeschreibung: {room_info['beschreibung']}"

    # Gegenstandsinformationen
    visible_items = []
    for item in room_info["gegenstaende"]:
        # Überspringe versteckte Gegenstände
        if item in ITEMS and not ITEMS[item].get("sichtbar", True):
            continue
        visible_items.append(item)

    prompt += f"\nGegenstände im Raum: {', '.join(visible_items) if visible_items else 'keine'}"

    # Türinformationen
    doors_info = []
    for direction, door in room_info["tueren"].items():
        status = "verschlossen" if door["verschlossen"] else "offen"
        doors_info.append(f"{direction} ({status}, führt nach {door['ziel']})")

    prompt += f"\nTüren: {', '.join(doors_info) if doors_info else 'keine'}"

    # Inventarinformationen
    prompt += f"\nInventar des Spielers: {', '.join(state['inventory']) if state['inventory'] else 'leer'}"

    # Spezielle Zustände
    if state["discovered"]:
        prompt += "\nEntdeckt:"
        for key, value in state["discovered"].items():
            prompt += f"\n- {key}: {value}"

    return prompt


# LLM-Anfragefunktion
def query_llm(state, user_input):
    """Sendet eine Anfrage an das LLM und verarbeitet die Antwort."""
    # Erstelle den Prompt mit Raumkontext
    context_prompt = create_room_prompt(state)

    # Debug-Ausgabe
    if state["debug_mode"]:
        print("\n--- DEBUG: Prompt für LLM ---")
        print(context_prompt)
        print("-----------------------------\n")

    # Anfrage an das LLM senden
    messages = [
        {"role": "system", "content": context_prompt},
        {"role": "user", "content": user_input}
    ]

    response = llm.invoke(messages)

    # Antwort auswerten
    ai_response = response.content

    # Content und Tool-Calls trennen
    content_parts = ai_response.split("ToolCalls:")

    content = content_parts[0].strip()
    if len(content_parts) > 1:
        tools_text = content_parts[1].strip()
        tool_calls = parse_tool_calls(tools_text)
    else:
        tool_calls = []

    # Debug-Ausgabe
    if state["debug_mode"]:
        print("\n--- DEBUG: LLM-Antwort ---")
        print(f"Content: {content}")
        print(f"Tool-Calls: {tool_calls}")
        print("---------------------------\n")

    return content, tool_calls


# Funktionen für den Zustandsgraphen
def process_input(state: GameState):
    """Verarbeitet die Benutzereingabe und erweitert den Zustand."""
    # Die letzte Nachricht des Benutzers abrufen
    user_input = state["messages"][-1]["content"]

    # Frage das LLM nach Inhalt und Tool-Calls
    content, tool_calls = query_llm(state, user_input)

    # Aktualisiere den Zustand
    #
    ## Changed role from "assistant" to "model"
    #
    state["messages"].append({
        "role": "assistant",
        "content": content,
        "tool_calls": tool_calls
    })

    return state


def execute_tools(state: GameState):
    """Führt die vom LLM angeforderten Tool-Calls aus."""
    # Die letzte Antwort des LLM abrufen
    last_assistant_msg = state["messages"][-1]
    tool_calls = last_assistant_msg.get("tool_calls", [])

    # Keine Tools, nichts zu tun
    if not tool_calls:
        return state

    # Alle Tool-Calls ausführen
    results = []
    for tool in tool_calls:
        function_name = tool["name"]
        arguments = tool["arguments"]

        # Debug-Ausgabe
        if state["debug_mode"]:
            print(f"\n--- DEBUG: Ausführe {function_name}({', '.join(arguments)}) ---")

        # Funktion ausführen, falls vorhanden
        if function_name in FUNCTION_MAP:
            func = FUNCTION_MAP[function_name]

            # Argumente an die Funktion übergeben
            if len(arguments) == 0:
                result = func(state)
            elif len(arguments) == 1:
                result = func(state, arguments[0])
            elif len(arguments) == 2:
                result = func(state, arguments[0], arguments[1])
            else:
                result = f"Fehler: Zu viele Argumente für {function_name}!"

            results.append({
                "name": function_name,
                "result": result
            })

            # Prüfe auf Spielende
            if function_name == "beenden":
                state["game_over"] = True
        else:
            results.append({
                "name": function_name,
                "result": f"Fehler: Unbekannte Funktion {function_name}!"
            })

    # Ergebnisse zum Zustand hinzufügen
    state["messages"][-1]["tool_results"] = results

    return state


def format_response(state: GameState):
    """Formatiert die Antwort des Systems für die Ausgabe."""
    # Die letzte Antwort des LLM und der Tools abrufen
    last_assistant_msg = state["messages"][-1]
    content = last_assistant_msg["content"]

    # Tool-Ergebnisse formatieren, falls vorhanden
    tool_results = last_assistant_msg.get("tool_results", [])

    # Grundlegende Formatierung
    formatted_response = content

    # Tool-Ergebnisse hinzufügen
    if tool_results and state["debug_mode"]:
        formatted_response += "\n\n--- Tool-Ergebnisse ---"
        for result in tool_results:
            formatted_response += f"\n{result['name']}: {result['result']}"

    # Füge Raumbeschreibung hinzu, wenn der Raum gewechselt wurde
    current_room = state["current_room"]
    if current_room == "freiheit":
        formatted_response += "\n\n🎉 Glückwunsch! Du hast das Spiel erfolgreich beendet! 🎉"

    # Füge Inventar hinzu, wenn angefragt
    inventory_requested = any(tool["name"] == "inventory" for tool in last_assistant_msg.get("tool_calls", []))
    if inventory_requested:
        inventory_content = inventory(state)
        if "Dein Inventar ist leer" in inventory_content:
            formatted_response += f"\n\n📦 {inventory_content}"
        else:
            formatted_response += f"\n\n📦 Dein Inventar enthält: {', '.join(state['inventory'])}"

    # Update der Nachrichten
    state["messages"][-1]["formatted_content"] = formatted_response

    return state


def should_end(state: GameState):
    """Prüft, ob das Spiel beendet werden soll."""
    # Prüfe, ob das Spiel-Ende-Flag gesetzt ist
    if state["game_over"]:
        return "end"

    # Prüfe, ob der Spieler im Freiheits-Raum ist (Spielgewinn)
    if state["current_room"] == "freiheit":
        # Lass dem Spieler eine letzte Nachricht sehen
        return None

    # Das Spiel geht weiter
    return None


# Erstellen des Zustandsgraphen
def create_game_graph():
    """Erstellt den Spielzustandsgraphen mit Langgraph."""
    # Erstelle einen neuen Zustandsgraphen
    builder = StateGraph(GameState)

    # Hauptzustände und -übergänge definieren
    builder.add_node("process_input", process_input)
    builder.add_node("execute_tools", execute_tools)
    builder.add_node("format_response", format_response)

    # Kanten des Graphen definieren
    builder.set_entry_point("process_input")
    builder.add_edge("process_input", "execute_tools")
    builder.add_edge("execute_tools", "format_response")

    # Entscheidungspunkt: Spiel beenden oder weitermachen
    builder.add_conditional_edges(
        "format_response",
        should_end,
        {
            "end": END,
            None: "process_input"
        }
    )

    # Graph kompilieren
    return builder.compile()


def initialize_game():
    """Initialisiert einen neuen Spielzustand."""
    return {
        "messages": [],  # Leerer Chat-Verlauf
        "current_room": "start",  # Startraum
        "inventory": [],  # Leeres Inventar
        "discovered": {},  # Keine speziellen Entdeckungen
        "visited_rooms": ["start"],  # Startraum ist bereits besucht
        "debug_mode": False,  # Debug-Modus anfangs aus
        "game_over": False  # Spiel läuft anfangs
    }


def run_game():
    """Startet und führt das Spiel aus."""
    print("=" * 60)
    print("Willkommen zu deinem Text-Adventure!")
    print("Gib 'umsehen' ein, um deine Umgebung zu betrachten.")
    print("Gib 'hilfe' ein, um Tipps zu bekommen.")
    print("Gib 'ende' ein, um das Spiel zu beenden.")
    print("=" * 60)

    # Initialisiere den Spielzustand
    state = initialize_game()

    # Erstelle den Spielgraphen
    game = create_game_graph()

    # Erste Raumbeschreibung
    print("\n" + ROOMS[state["current_room"]]["beschreibung"])

    # Hauptspielschleife
    while True:
        # Benutzereingabe
        user_input = input("\n> ")

        # Aktualisiere die Nachrichten
        state["messages"].append({
            "role": "user",
            "content": user_input
        })

        # Führe den Spielgraphen mit der aktuellen Eingabe aus
        state = game.invoke(state)

        # Formatierte Antwort anzeigen
        print("\n" + state["messages"][-1].get("formatted_content", ""))

        # Prüfe, ob das Spiel beendet ist
        if state["game_over"]:
            print("\nDas Spiel wurde beendet. Bis zum nächsten Mal!")
            break


# Haupteinstiegspunkt
if __name__ == "__main__":
    run_game()