import os
from typing import TypedDict, Annotated
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from collections.abc import Iterable
from langchain_core.messages.tool import ToolMessage
from langchain_core.messages.ai import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

os.environ["GOOGLE_API_KEY"] = input("Google API key:")

class AdventureState(TypedDict):
    messages: Annotated[list, add_messages]
    inventory: list[str]
    location: str
    discovered: dict[str, bool]
    known_code: str | None
    finished: bool

ROOMS = {
    "start": {
        "beschreibung": "Du wachst in einem schlichten Zimmer auf. Es gibt ein Bett mit einem Kissen darauf. In der Ecke stehen eine Schaufel und eine Schere. Eine Nudelpackung liegt auf dem Boden. Es gibt zwei Türen: nach Westen (offen) und nach Norden (verschlossen).",
        "hinweis": "Vielleicht solltest du dich umsehen oder das Kissen genauer betrachten.",
        "gegenstaende": ["schaufel", "schere", "nudelpackung", "kissen"],
        "tueren": {
            "norden": {"ziel": "bibliothek", "verschlossen": True, "benoetigt": "schlüssel"},
            "westen": {"ziel": "durchgang", "verschlossen": False}
        }
    },
    "durchgang": {
        "beschreibung": "Ein schmuckloser Raum mit kahlen Wänden. Auf einem alten Stuhl liegt ein Kochlöffel. Eine Luftpumpe lehnt an der Wand. Ein Radio steht auf einem kleinen Tisch und spielt leise vor sich hin. Türen führen nach Osten und Westen.",
        "hinweis": "Vielleicht findest du hier etwas Nützliches oder auch nicht.",
        "gegenstaende": ["radio", "luftpumpe", "kochlöffel"],
        "tueren": {
            "osten": {"ziel": "start", "verschlossen": False},
            "westen": {"ziel": "endraum", "verschlossen": False}
        }
    },
    "bibliothek": {
        "beschreibung": "Du befindest dich in einer geheimen, staubigen Bibliothek. Bücher in unbekannter Sprache füllen die Regale. In der Ecke steht ein alter Ohrensessel. Daneben befindet sich ein kleiner Tisch, auf dem ein geheimnisvolles Buch liegt.",
        "hinweis": "Das Buch auf dem Tisch sieht anders aus als die anderen.",
        "gegenstaende": ["sessel", "tisch", "geheimnisvolles_buch"],
        "tueren": {
            "sueden": {"ziel": "start", "verschlossen": False}
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
    "schaufel": {"hinweis": "Eine rostige alte Schaufel. Vielleicht mal nützlich gewesen."},
    "schere": {"hinweis": "Eine stumpfe Bastelschere. Nicht gefährlich."},
    "nudelpackung": {"hinweis": "Eine halb volle Packung Spaghetti. Haltbar bis 2027."},
    "kissen": {"hinweis": "Ein gemütliches Kissen. Vielleicht liegt etwas darunter?",
                "untersuchen": lambda state: _entdecke_schluessel(state)},
    "schlüssel": {"hinweis": "Ein kleiner, leicht angerosteter Schlüssel.",
                  "sichtbar": lambda state: state["discovered"].get("schlüssel_entdeckt", False)},
    "radio": {"hinweis": "Ein altes Radio, aus dem leise Musik dringt."},
    "luftpumpe": {"hinweis": "Eine quietschende Luftpumpe."},
    "kochlöffel": {"hinweis": "Ein Holzlöffel mit eingebrannter Gravur: 'Mama'."},
    "geheimnisvolles_buch": {"hinweis": "Ein altes, schweres Buch mit mystischem Einband.", "code": "4283"},
    "sessel": {"hinweis": "Ein alter Sessel mit staubigen Armlehnen.", "nimmbar": False},
    "tisch": {"hinweis": "Ein kleiner Tisch aus dunklem Holz.", "nimmbar": False}
}

TOOL_REGISTRY = {}

def register_tool(name):
    def decorator(func):
        TOOL_REGISTRY[name] = func
        return tool(name=name)(func)
    return decorator

@register_tool("umsehen")
def tool_umsehen(state: AdventureState) -> str:
    location = state["location"]
    room = ROOMS[location]
    beschreibung = room.get("beschreibung", "Es ist leer hier.")
    sichtbare_objekte = [o for o in room.get("gegenstaende", []) if not ITEMS.get(o, {}).get("sichtbar") or ITEMS[o]["sichtbar"](state)]
    tuer_text = "Türen führen nach: " + ", ".join(room.get("tueren", {}).keys())
    objekt_text = "Du siehst: " + ", ".join(sichtbare_objekte) if sichtbare_objekte else "Du siehst nichts Besonderes."
    return f"{beschreibung}\n{objekt_text}\n{tuer_text}"

@register_tool("untersuche")
def tool_untersuche(state: AdventureState, gegenstand: str) -> str:
    g = gegenstand.lower()
    if g in ITEMS:
        untersuchung = ITEMS[g].get("untersuchen")
        if callable(untersuchung):
            return untersuchung(state)
        else:
            if "code" in ITEMS[g]:
                state["known_code"] = ITEMS[g]["code"]
            return untersuchung or "Du siehst nichts Besonderes."
    return f"Du untersuchst {g}, aber findest nichts Interessantes."

@register_tool("nimm")
def tool_nimm(state: AdventureState, gegenstand: str) -> str:
    g = gegenstand.lower()
    room = ROOMS[state["location"]]
    inventory = state["inventory"]
    if g in room["gegenstaende"] and (not ITEMS.get(g, {}).get("sichtbar") or ITEMS[g]["sichtbar"](state)):
        if ITEMS.get(g, {}).get("nimmbar", True):
            if g not in inventory:
                inventory.append(g)
                room["gegenstaende"].remove(g)
                return f"Du nimmst {g} an dich."
            else:
                return f"Du hast {g} bereits."
        else:
            return f"Du kannst {g} nicht mitnehmen."
    else:
        return f"{g} ist hier nicht sichtbar."

def spielaktion_node(state: AdventureState) -> AdventureState:
    tool_msg = state["messages"][-1]
    outbound_msgs = []

    def antwort(name: str, content: str):
        outbound_msgs.append(
            ToolMessage(
                content=content,
                name=name,
                tool_call_id=tool_call["id"]
            )
        )

    for tool_call in tool_msg.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        func = TOOL_REGISTRY.get(name)
        if func:
            try:
                response = func(state, **args)
            except Exception as e:
                response = f"Fehler bei '{name}': {e}"
        else:
            response = f"Tool '{name}' nicht implementiert."
        antwort(name, response)

    return {**state, "messages": outbound_msgs}

def _entdecke_schluessel(state: AdventureState) -> str:
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