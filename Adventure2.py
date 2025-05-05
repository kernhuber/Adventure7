import os
from typing import TypedDict, Annotated
from langchain_core.messages import AIMessage
from langgraph.graph.message import add_messages
from typing import Tuple, List
from langchain_core.messages.base import BaseMessage
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langchain_core.messages.tool import ToolMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode
import logging  # Importiere das logging-Modul


from IPython.display import Markdown, display
# os.environ["GOOGLE_API_KEY"] = input("Google API key:")
os.environ["GOOGLE_API_KEY"] = "AIzaSyBAD9VSVcw47HSj6I63qSGpY4vuuu7WXTA"



#
# -------------- Variables and Classes ----------------
#

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
        Wenn der Spieler sich unmsieht, beschreibe ihm den Raum. Dabei kannst Du etwas geheimnisvoll tun. Du bist ein guter Erzähler.
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
            "westen": {"ziel": "endraum", "verschlossen": False},
        "extra_prompt": """
            Wenn der Spieler sich umsieht, beschreibe den Raum und erwähne, dass der Stuhl mit dem Kochlöffel im Osten steht und die Luftpumpe im Westen lehnt. Erwähne auch das Radio und die Türen nach Osten (zum Startraum) und Westen (zum Endraum).
    Wenn der Spieler um Hilfe bittet, erwähne, dass er Gegenstände untersuchen und die Türen nach Osten (zum Startraum) oder Westen (zum Endraum) nutzen kann.
    Beschreibe die Gegenstände humorvoll, wenn der Spieler sie untersucht.
        """
        }
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
            "sueden": {"ziel": "start", "verschlossen": False},
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
        }
    },
    "endraum": {
        "beschreibung": "Ein karger Betonraum mit einem Tastenfeld an der westlichen Wand. Sonst ist der Raum leer.",
        "hinweis": "Vielleicht brauchst du einen Code, um weiterzukommen.",
        "gegenstaende": [],
        "tueren": {
            "osten": {"ziel": "durchgang", "verschlossen": False},
            "westen": {"ziel": "freiheit", "verschlossen": True, "code": True}
        }
    },
    "freiheit": {
        "beschreibung": "Du trittst hinaus auf eine sonnige Sommerwiese. Du hast das Spiel erfolgreich beendet!",
        "hinweis": "",
        "gegenstaende": [],
        "tueren": {}
    }
}

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
        "untersuchen": lambda state: _entdecke_schluessel(state)
    },
    "schlüssel": {
        "hinweis": "Ein kleiner, leicht angerosteter Schlüssel.",
        "sichtbar": lambda state: state["discovered"].get("schlüssel_entdeckt", False),
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
        "untersuchen": lambda state: _entdecke_geheimnummer(state),
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

DEBUG=True

logger = logging.getLogger("MiniAdventure")
logging.basicConfig(filename='MiniAdventure.log', encoding='utf-8', level=logging.DEBUG)

def dprint(x):
    if DEBUG:
        logging.warning(x)

class AdventureState(TypedDict):
    messages: Annotated[list, add_messages]  # Nachrichtenverlauf für das LLM
    inventory: list[str]  # Liste der aufgenommenen Objekte
    location: str  # Aktueller Raum (z. B. "start")
    discovered: dict[str, bool]  # Dinge, die der Spieler aufgedeckt hat
    known_code: str | None  # Geheimcode (falls entdeckt)
    finished: bool  # Wurde das Spiel abgeschlossen?
    current_input: str
    last_action: str




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

Wenn der Spieler „Q“, „Quit“ oder „Ende“ eingibt, ist das ein Wunsch, das Spiel zu verlassen.
In diesem Fall sollst du die Funktion `beenden()` aufrufen.

---

### 🧠 Wichtig für den Spielablauf:

Jede Antwort muss einen kurzen Text im Feld `content` enthalten – auch wenn nur ToolCalls zurückgegeben werden.  
Wenn du nichts beschreiben möchtest, gib einen Platzhalter-Text wie z. B.  
- "(Du führst die Aktion aus.)"  
- "(Nichts weiter geschieht.)"  
- oder einen stimmungsvollen Erzählerkommentar an.  
- Gib niemals eine Antwort ohne `content`.
- Erwähne immer alle Türen und Wege des Raums; beschreibe dem Spieler, wohin er gehen kann

---

### 🎮 Deine Regeln für das Spiel:

* Wenn Du um Hilfe gebeten wirst, hilf dem Spieler gemäß den Anweisungen in den einzelnen Räumen und liefere 'nop()' zurück.
* **Verwende 'inventory()' nur, wenn der Spieler explizit nach seinem Inventar fragt (z.B. "Was habe ich dabei?", "Zeige mein Inventar").**
* Liefere 'nop()' zurück, wenn der Spieler eine reine Informationsabfrage stellt (z.B. "Beschreibe den Raum erneut").
* Wenn der Spieler den Debug-Modus an oder ausschalten will, dann liefere 'debug("an")' oder debug("aus") 
  zurück, je nachdem was der Spieler wünscht. Wenn der Spieler nur den Status des Debug-Modus wissen will,
  dann liefere 'debug("status")' zurück
* Wenn Du einen Raum beschreiben sollst, so beschreibe den Raum gemäß den Anweisungen in den einzelnen 
  Räumen, danach lieferst Du 'nop()' zurück
* Du darfst mehrere Tool-Calls gleichzeitig ausgeben, wenn sinnvoll.
* Du darfst **implizite Aktionen erkennen** – z.B. wenn jemand „Ich gehe in die Bibliothek“ sagt, dann:
   - `benutze("schlüssel", "norden")`
   - `gehe("norden")`
* Verwende nur Objekte, Räume und Richtungen, die dir bekannt sind.
* Der Spieler kann die Tür angeben, durch die er gehen will (Beispiel: "Gehe durch die Tür im Norden"), er kann 
  aber auch nur die Richtung angeben, in die er gehen will (Beispiel: "Gehe nach westen"). Liefere in allen Fällen
  -- Eine Bestätigung als content, etwa: "Du gehst durch die Tür im Westen"
  -- den korrekten Tool-call 'gehe()'
* Wenn du etwas nicht tun kannst (z.B. Tür verschlossen, kein Objekt vorhanden), überlasse die Erklärung dem Spielsystem.

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
- `debug()` → Schaltet den Debug-Modus an oder aus
- `nop()` → "No Operation".

---

Verwende in jeder Antwort mindestens einen passenden Funktionsaufruf, sofern dies durch die Eingabe des Spielers sinnvoll ausgelöst wird.
"""
ADVENTURE_TOOL_REGISTRY = {}



#
# ------- Tools for the Model to return ----------
#
def adventure_tool(func):
    decorated = tool(func)
    ADVENTURE_TOOL_REGISTRY[decorated.name] = decorated
    return decorated


def do_umsehen(state: AdventureState) -> str:
    """Beschreibt den aktuellen Raum und zeigt Objekte und Durchgänge (Türen) an"""
    room = ROOMS[state["location"]]
    sichtbare_objekte = [
        o for o in room.get("gegenstaende", [])
        if not ITEMS.get(o, {}).get("sichtbar") or ITEMS[o]["sichtbar"](state)
    ]
    beschreibung = room.get("beschreibung", "Es ist leer hier.")
    tuer_text = "Türen führen nach: " + ", ".join(room.get("tueren", {}).keys())
    objekt_text = "Du siehst: " + ", ".join(sichtbare_objekte) if sichtbare_objekte else "Du siehst nichts Besonderes."
    return f"{beschreibung}\n{objekt_text}\n{tuer_text}"
@tool
def umsehen():
    """Beschreibt den aktuellen Raum"""
    return "__CALL_DO_UMSEHEN__"


def do_untersuche(state: AdventureState, gegenstand: str) -> str:
    """Untersuchung von Gegenständen. Die Gegenstände sollen beschrieben werden"""
    g = gegenstand.lower()
    if g in ITEMS:
        untersuchung = ITEMS[g].get("untersuchen")
        if callable(untersuchung):
            result = untersuchung(state)
        else:
            result = untersuchung or "Du siehst nichts Besonderes."
        if "code" in ITEMS[g]:
            state["known_code"] = ITEMS[g]["code"]
        return result
    else:
        return f"Du untersuchst {g}, aber findest nichts Interessantes."
@tool
def untersuche(gegenstand: str) -> str:
    """Untersuche den Gegenstand"""
    return f"__CALL_DO_UNTERSUCHE__:{gegenstand}"


def do_nimm(state: AdventureState, gegenstand: str) -> str:
    """Ein Gegenstand wird ins Inventory aufgenommen"""
    g = gegenstand.lower()
    room = ROOMS[state["location"]]
    if g in room["gegenstaende"] and (not ITEMS.get(g, {}).get("sichtbar") or ITEMS[g]["sichtbar"](state)):
        if ITEMS.get(g, {}).get("nimmbar", True):
            if g not in state["inventory"]:
                state["inventory"].append(g)
                room["gegenstaende"].remove(g)
                return f"Du nimmst {g} an dich."
            else:
                return f"Du hast {g} bereits."
        else:
            return f"Du kannst {g} nicht mitnehmen."
    else:
        return f"{g} ist hier nicht sichtbar."
@tool
def nimm(gegenstand: str) -> str:
    """Nimm den gegenstand ins Inventory auf"""
    return f"__CALL_DO_NIMM__:{gegenstand}"


def do_benutze(state: AdventureState, gegenstand: str, ziel: str) -> str:
    """Ein Gegenstand wird benutzt"""
    g = gegenstand.lower()
    ziel = ziel.lower()
    room = ROOMS[state["location"]]
    for richtung, tuer in room.get("tueren", {}).items():
        if ziel == richtung:
            if tuer.get("verschlossen") and tuer.get("benoetigt") == g and g in state["inventory"]:
                tuer["verschlossen"] = False
                return f"Du benutzt {g}, um die Tür nach {richtung} zu öffnen."
            elif not tuer.get("verschlossen"):
                return f"Die Tür nach {richtung} ist bereits offen."
            else:
                return f"Der {g} funktioniert hier nicht."
    return f"Du kannst {g} hier nicht benutzen."
@tool
def benutze(gegenstand: str, ziel: str) -> str:
    """Wende einen Gegenstand an, ggf. auf ein Ziel"""
    return f"__CALL_DO_BENUTZE__:{gegenstand}:{ziel}"


def do_gehe(state: AdventureState, richtung: str) -> str:
    """Der Spieler geht in eine Richtung oder durch eine Tür"""
    richtung = richtung.lower()
    room = ROOMS[state["location"]]
    tuer = room.get("tueren", {}).get(richtung)
    if not tuer:
        return f"In Richtung {richtung} ist keine Tür."
    elif tuer.get("verschlossen", False):
        return f"Die Tür nach {richtung} ist verschlossen."
    else:
        new_location = tuer["ziel"]
        state["location"] = new_location
        if new_location == "freiheit":
            state["finished"] = True
            return "🌳 Du trittst hinaus in die Freiheit. Du hast das Spiel erfolgreich beendet!"
        else:
            return f"Du gehst nach {richtung} in den Raum '{new_location}'."
@tool
def gehe(richtung: str) -> str:
    """gehe in die vorgegebene Richtung"""
    return f"__CALL_DO_GEHE__:{richtung}"


def do_eingabe_code(state: AdventureState, code: str) -> str:
    """Ein Geheimcode wird eingegeben"""
    room = ROOMS[state["location"]]
    for richtung, tuer in room.get("tueren", {}).items():
        if tuer.get("code") and code == state.get("known_code"):
            tuer["verschlossen"] = False
            return f"✅ Der Code {code} war korrekt. Die Tür nach {richtung} öffnet sich."
    return "❌ Der Code war falsch oder hier nicht anwendbar."
@tool
def eingabe_code(code: str) -> str:
    """geheimcode eingeben"""
    return f"__CALL_DO_EINGABE_CODE__:{code}"


def do_hilfe(state: AdventureState) -> str:
    """Es wird Hilfetext ausgegeben"""
    return ROOMS[state["location"]].get("hinweis",
                                        "Vielleicht hilft es, dich etwas umzusehen oder Dinge zu untersuchen.")
@tool
def hilfe() -> str:
    """Hilfe anfordern"""
    return "__CALL_DO_HILFE__"


def do_beenden(state: AdventureState) -> str:
    """Das Spiel wird beendet"""
    state["finished"] = True
    return "🛑 Du hast das Spiel beendet. Bis bald!"
@tool
def beenden() -> str:
    """Das Spiel beenden"""
    return "__CALL_DO_BEENDEN__"

def do_nop(state: AdventureState) -> str:
    return "(Es war keine weitere Aktion auszuführen))"
@tool
def nop() -> str:
    """ NOP (No Operation). Wir nach reinen Info-Calls verwendet """
    return ""

def do_inventory(state: AdventureState) -> str:
    return "\n".join([
                         f"👜 Du trägst bei dir:"
                     ] + [
                         f"- {item}: {ITEMS[item]['hinweis']}" for item in state["inventory"]
                     ])
@tool
def inventory()->str:
    """Zeige das Inventory an"""
    return "__CALL_DO_INVENTORY__"

def do_debug(state: AdventureState, anaus: str) -> str:
    """Ein Geheimcode wird eingegeben"""
    global DEBUG
    if anaus == "an":
        DEBUG = True
        return "(Debug-Modus ist nun angeschaltet)"
    elif anaus == "aus":
        DEBUG = False
        return "(Debug-Modus ist nun ausgeschaltet)"
    elif DEBUG: # --- bei etwas anderem als "an" oder "aus" liefere den Status zurück
        return "(Der DEBUG-Modus ist zur Zeit wie vor angeschaltet)"
    else:
        return "(Der DEBUG-Modus ist zur Zeit ausgeschaltet)"
@tool
def debug()->str:
    """Debug-Modus an oder ausschalten"""
    return "__CALL_DO_DEBUG__"

def _entdecke_schluessel(state: AdventureState) -> str:
    dprint(f"This is _entdecke_schlüssel({state})")
    if state["location"] != "start":
        return "Hier findest du kein Kissen."
    if not state["discovered"].get("schlüssel_entdeckt"):
        state["discovered"]["schlüssel_entdeckt"] = True
        raum = ROOMS[state["location"]]
        if "schlüssel" not in raum["gegenstaende"]:
            raum["gegenstaende"].append("schlüssel")
        return "Du hebst das Kissen an und entdeckst einen Schlüssel darunter!"
    else:
        return "Du hast das Kissen bereits angehoben. Der Schlüssel liegt bereit."

def _entdecke_geheimnummer(state: AdventureState) -> str:
    if state["location"] != "bibliothek":
        return "Was den für ein Geheimcode? Hier ist kein Geheimcode!"
    if not state["discovered"].get("geheimcode_entdeckt"):
        state["discovered"]["geheimcode_entdeckt"] = True
        raum = ROOMS[state["location"]]
        if "geheimcode" not in raum["gegenstaende"]:
            raum["gegenstaende"].append("geheimcode")
        return f"Du hast einen Geheimcode entdeckt! Es ist {ITEMS["geheimnisvolles_buch"]["code"]}"
    else:
        return f"Den Geheimcode hattest du bereits entdeckt, er ist {ITEMS["geheimnisvolles_buch"]["code"]}"

def parse_tool_call_marker_clean(marker: str) -> Tuple[str, List[str]]:
    """
    Zerlegt einen Tool-Call-Marker wie '__CALL_DO_UNTERSUCHEN__:kissen'
    oder '__CALL_DO_BENUTZE__:schlüssel:norden'
    in ('untersuche', ['kissen']) oder ('benutze', ['schlüssel', 'norden']).
    """
    # Entferne Prefix
    if not marker.startswith("__CALL_DO_"):
        raise ValueError(f"Kein gültiger Marker: {marker}")

    content = marker[len("__CALL_DO_"):]  # z. B. "UNTERSUCHEN__:kissen" oder "BENUTZE__:schlüssel:norden"

    # Trenne an der ersten Instanz von ":"
    func_part, *arg_parts = content.split(":")

    # Entferne etwaige abschließende Unterstriche
    func_name = func_part.lower().rstrip("_")

    return func_name, arg_parts

#
# ----------- Routing ------------
#
def maybe_route_from_chatbot(state: AdventureState) -> str:
    msg = state["messages"][-1]

    if state.get("finished", False):
        dprint("maybe_route: Spiel ist beendet → __end__")
        return "__end__"

    if hasattr(msg, "tool_calls") and msg.tool_calls:
        dprint("maybe_route: Tool Calls vorhanden → spielaktion")
        return "spielaktion"

    if state.get("last_action") in ["chatbot", "chatbot_no_response", "error", "chatbot_start"]:
        dprint("maybe_route: chatbot hat geantwortet oder es gab einen Fehler → human")
        return "human"

    dprint("maybe_route: Standard-Fall → human")
    return "human"
#
#  ---------- Nodes --------------
#

def check_messages(messages):
    if not isinstance(messages, list):
        print("Fehler: messages ist kein List-Objekt")
        return False

    valid_roles = {"user", "model", "system"}

    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            dprint(f"Fehler bei Nachricht {i}: Kein Dictionary")
            return False
        if "role" not in msg or "content" not in msg:
            dprint(f"Fehlende Felder bei Nachricht {i}: {msg}")
            return False
        if msg["role"] not in valid_roles:
            dprint(f"Ungültige Rolle bei Nachricht {i}: {msg['role']}")
            return False
        if not isinstance(msg["content"], str) or not msg["content"].strip():
            dprint(f"Leerer oder ungültiger Inhalt bei Nachricht {i}: {msg['content']}")
            return False

    return True

from langchain_core.messages import HumanMessage

def human_node_old(state: AdventureState) -> AdventureState:
    dprint("---------------------------- human_node():")
    last_msg = state["messages"][-1]
    model_output = getattr(last_msg, "content", "(keine Nachricht)")
    dprint(f"Last message from Model: {model_output}")
    dprint("\n")

    user_input = ""
    while user_input == "":
        user_input = input("🧍 Was tust du? ").strip()

    dprint(f"User Input is: {user_input}")

    if user_input.lower() in {"q", "quit", "ende"}:
        state["finished"] = True

    state["last_action"] = "user_input"
    h = HumanMessage(content=user_input)
    dprint(f"Adding to message: [{h}]")
    return state | {
        "messages": state["messages"] + [h]
    }

def human_node(state: AdventureState) -> AdventureState:
    dprint("---------------------------- human_node():")
    last_msg = state["messages"][-1] if state["messages"] else AIMessage(content="(Spielstart)")
    model_output = getattr(last_msg, "content", "(keine Nachricht)")
    dprint(f"Last message from Model: {model_output}")
    dprint("\n")

    user_input = ""
    while user_input == "":
        user_input = input("🧍 Was tust du? ").strip()

    dprint(f"User Input is: {user_input}")

    if user_input.lower() in {"q", "quit", "ende"}:
        state["finished"] = True

    state["current_input"] = user_input  # Speichere den User-Input im State
    state["last_action"] = "user_input"
    return state

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
import logging  # Importiere das logging-Modul

def debug_check_messages(messages: list[BaseMessage]):
    if not messages:
        return

    last = messages[-1]
    if not getattr(last, "content", "").strip() and not getattr(last, "tool_calls", None):
        dprint("⚠️  Letzte Nachricht ist leer UND hat keine Tool-Calls!")

    seen_ids = set()
    for i, m in enumerate(messages):
        mid = id(m)
        if mid in seen_ids:
            dprint(f"⚠️  Nachricht an Position {i} ist ein Duplikat (Objekt-ID doppelt)")
        seen_ids.add(mid)

        if not isinstance(m, (HumanMessage, AIMessage, SystemMessage, BaseMessage)):
            dprint(f"⚠️  Unerwarteter Nachrichtentyp an {i}: {type(m).__name__}")

def chatbot_node(state: AdventureState) -> AdventureState:
    dprint("---------------------------- chatbot_node():")

    if state["messages"]:
        dprint("message does exist in state\n\n")

        room = ROOMS[state["location"]]
        beschreibung = room["beschreibung"]
        extra_prompt = room.get("extra_prompt", "")
        objekte = ", ".join(room["gegenstaende"]) if room["gegenstaende"] else "keine"
        tueren = ", ".join(room["tueren"].keys()) if room["tueren"] else "keine"

        # user_input = state.pop("current_input", "") # Lese und lösche den User-Input
        user_input = state["current_input"] # Lese User-Input, lösche ihn NICHT
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"""Aktueller Raum: {state['location']}

Beschreibung: {beschreibung}

Objekte im Raum: {objekte}
Türen führen nach: {tueren}
Spezielle Anweisungen für diesen Raum: {extra_prompt}

Deine letzte Aktion war: {user_input}
""")
        ] + state["messages"]

        # 🧹 Nur gültige Messages behalten
        messages = [
            m for m in messages
            if isinstance(m, BaseMessage) and (
                (getattr(m, "content", "") and m.content.strip()) or
                getattr(m, "tool_calls", None)
            )
        ]

        # ✂️ Kontextreduktion
        messages = messages[:6]

        # 🔍 Debug-Ausgabe
        dprint("👀 Aufruf von llm_with_tools mit Messages:")
        for i, msg in enumerate(messages):
            content = getattr(msg, "content", "")
            tools = getattr(msg, "tool_calls", None)
            if tools:
                dprint(f"{i}: {type(msg).__name__} | {content[:80].rstrip()+"..."} | tool_calls: {tools}")
            else:
                dprint(f"{i}: {type(msg).__name__} | {content[:80].rstrip()+"..."}")

        # 🔧 LLM-Aufruf mit Fallback
        try:
            if DEBUG:
                debug_check_messages(messages)
            output = llm_with_tools.invoke(messages)
            dprint("🔧 Antwort vom LLM:")
            dprint(output.additional_kwargs)

            # ✅ Überprüfe die Ausgabe des LLM
            if not getattr(output, "content", "").strip() and not getattr(output, "tool_calls", None):
                logging.warning("LLM hat eine leere Antwort generiert!")
                output = AIMessage(content="(Keine Antwort vom Erzähler.)") # Fallback
            state["last_action"] = "chatbot" # Setze last_action NACH erfolgreichem LLM-Aufruf

        except Exception as e:
            logging.error(f"🚨 Fehler beim LLM-Aufruf: {e}", exc_info=True)
            output = AIMessage(content="(Ein Fehler ist aufgetreten. Bitte versuche es erneut.)")
            state["last_action"] = "error" # Oder einen anderen Wert setzen

    else:
        dprint("Looks like first call to chatbot_node - no messages yet in state")
        output = AIMessage(content="Willkommen im Mini-Adventure! Du kannst jederzeit mit 'Q' das Spiel beenden.")
        state["last_action"] = "chatbot_start" # Oder ein anderer Startwert

    # 💬 Ausgabe
    if isinstance(output, AIMessage) and output.content:
        print("💬  Erzähler:\n")
        print(output.content.strip())
        print("📜" * 40 + "\n")

    return state | {"messages": state["messages"] + [output]}

def chatbot_node_old(state: AdventureState) -> AdventureState:
    dprint("---------------------------- chatbot_node():")

    if state["messages"]:
        dprint("message does exist in state\n\n")

        room = ROOMS[state["location"]]
        beschreibung = room["beschreibung"]
        extra_prompt = room.get("extra_prompt", "")
        objekte = ", ".join(room["gegenstaende"]) if room["gegenstaende"] else "keine"
        tueren = ", ".join(room["tueren"].keys()) if room["tueren"] else "keine"

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"""Aktueller Raum: {state['location']}

Beschreibung: {beschreibung}

Objekte im Raum: {objekte}
Türen führen nach: {tueren}
Spezielle Anweisungen für diesen Raum: {extra_prompt}
""")
        ] + state["messages"]

        # 🧹 Nur gültige Messages behalten
        messages = [
            m for m in messages
            if isinstance(m, BaseMessage) and (
                (getattr(m, "content", "") and m.content.strip()) or
                getattr(m, "tool_calls", None)
            )
        ]

        # ✂️ Kontextreduktion: Behalte nur die letzten 10 Nachrichten
        messages = messages[:11]

        # 🔍 Debug-Ausgabe
        dprint("👀 Aufruf von llm_with_tools mit Messages:")
        for i, msg in enumerate(messages):
            content = getattr(msg, "content", "")
            tools = getattr(msg, "tool_calls", None)
            if tools:
                dprint(f"{i}: {type(msg).__name__} | {content[:80].rstrip()+"..."} | tool_calls: {tools}")
            else:
                dprint(f"{i}: {type(msg).__name__} | {content[:80].rstrip()+"..."}")

        # 🔧 LLM-Aufruf mit Fallback
        try:
            if DEBUG:
                debug_check_messages(messages)
            if not isinstance(state["messages"][-1], HumanMessage):
                print("⚠️ Letzte Nachricht ist keine HumanMessage. Kein LLM-Aufruf.")
                return state
            output = llm_with_tools.invoke(messages)
            dprint("🔧 Antwort vom LLM:")
            dprint(output.additional_kwargs)

            # ✅ Überprüfe die Ausgabe des LLM
            if not getattr(output, "content", "").strip() and not getattr(output, "tool_calls", None):
                logging.warning("LLM hat eine leere Antwort generiert!")
                output = AIMessage(content="(Keine Antwort vom Erzähler.)") # Fallback

        except Exception as e:
            logging.error(f"🚨 Fehler beim LLM-Aufruf: {e}", exc_info=True)  # Logge den Fehler mit Stacktrace
            output = AIMessage(content="(Ein Fehler ist aufgetreten. Bitte versuche es erneut.)")

    else:
        dprint("Looks like first call to chatbot_node - no messages yet in state")
        output = AIMessage(content="Willkommen im Mini-Adventure! Du kannst jederzeit mit 'Q' das Spiel beenden.")

    # 💬 Ausgabe
    if isinstance(output, AIMessage) and output.content:
        print("💬  Erzähler:\n")
        print(output.content.strip())
        print("📜" * 40 + "\n")

    state["last_action"] = "chatbot"
    return state | {"messages": state["messages"] + [output]}


import logging  # Importiere das logging-Modul

def spielaktion_node(state: AdventureState) -> AdventureState:
    dprint("---------------------------- spielaktion_node():")
    tool_msg = state["messages"][-1]
    tool_outputs = []

    if hasattr(tool_msg, "tool_calls"):
        for call in tool_msg.tool_calls:
            name = call.get("name")
            args = call.get("args", {})
            tool_call_id = call.get("id")

            # ✅ Validiere Tool-Call-Daten
            if not name or not tool_call_id:
                dprint(f"spielaktion_node: Ungültiger Tool-Call: {call}")
                continue  # Überspringe ungültige Tool-Calls

            try:
                match name:
                    case "umsehen":
                        result = do_umsehen(state)
                    case "untersuche":
                        result = do_untersuche(state, args.get("gegenstand"))
                    case "nimm":
                        result = do_nimm(state, args.get("gegenstand"))
                    case "benutze":
                        result = do_benutze(state, args.get("gegenstand"), args.get("ziel"))
                    case "gehe":
                        result = do_gehe(state, args.get("richtung"))
                    case "eingabe_code":
                        result = do_eingabe_code(state, args.get("code"))
                    case "hilfe":
                        result = do_hilfe(state)
                    case "beenden":
                        result = do_beenden(state)
                    case "nop":
                        result = "(Keine Aktion ausgeführt.)"  # Stelle sicher, dass do_nop() auch einen sinnvollen Wert zurückgibt
                    case "debug":
                        result = do_debug(state, args.get("anaus"))
                    case "inventory":
                        result = do_inventory(state)
                    case _:
                        result = f"⚠️ Tool '{name}' nicht erkannt."
            except Exception as e:
                logging.error(f"Fehler bei Tool '{name}': {e}", exc_info=True)  # Logge den Fehler mit Stacktrace
                result = f"❌ Fehler bei '{name}': {e}"

            tool_outputs.append(ToolMessage(content=str(result), tool_call_id=tool_call_id))

    state["last_action"] = "spielaktion"
    return state | {"messages": state["messages"] + tool_outputs}





#
# ---------- Global Actions ------------
#
# Mit dem LLM (Gemini) verbinden
#
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

ALL_TOOLS = [umsehen, untersuche, nimm, benutze, gehe, eingabe_code, hilfe, beenden, nop, inventory, debug]
llm_with_tools = llm.bind_tools(ALL_TOOLS)



# Graph erstellen
graph_builder = StateGraph(AdventureState)

graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("spielaktion", spielaktion_node)
# graph_builder.add_node("tools", tool_node)
graph_builder.add_node("human", human_node)

graph_builder.set_entry_point("chatbot")
graph_builder.add_conditional_edges("chatbot", maybe_route_from_chatbot)

graph_builder.add_edge("spielaktion", "chatbot")
# graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge("human", "chatbot")

# graph_builder.add_edge(END, END)  # optional

adventure_graph = graph_builder.compile()
initial_state = {
    "messages": [],
    "inventory": [],
    "location": "start",
    "discovered": {},
    "known_code": None,
    "finished": False,
    "last_action": "keine",
    "current_input": "keiner"
}

config = {"recursion_limit": 100}  # erlaubt viele Schritte

adventure_graph.invoke(initial_state, config=config)
