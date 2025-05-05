from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# Gemini vorbereiten
import os
import google.generativeai as genai
from pyasn1.type.univ import Boolean

# Setze deinen echten API-Key hier
os.environ["GEMINI_API_KEY"] = "AIzaSyBAD9VSVcw47HSj6I63qSGpY4vuuu7WXTA"

# Konfiguration
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.0-flash")

from typing import List, Tuple
ActionList = List[Tuple[str, str]]

#
# der "Backbone" des Adventures kennt folgende atomare Anweisungen
#
# show
# take
# examine
# walk
# open
# help
# look
# noop
# unknown
# success
# failure
#
# Alle Anweisungen können null oder ein Objekt enthalten.

#
# Für jeden Raum eine Beschreibung
#
room_names = {
    "start":"Start",
    "middle":"Durchgang",
    "middle_alt":"Geheime Bibliothek",
    "end":"Ausgangskontrolle"
}
room_conditions = {
    "start": """
Dies ist der erste Raum. Der Spieler wacht hier auf. Er hat Kopfschmerzen und weiss nicht, wie er
hierhin gekommen ist. Der Raum ist mit groben Sandsteinen gemauert und eine Fackel spendet flackernd Licht.
Es liegt ein rostiger Schlüssel auf dem Boden. Es gibt zwei Türen: eine normale Tür 
und eine geheime Tür, die nur mit dem Schlüssel geöffnet werden kann. 

* Wenn der Spieler durch die normale Tür geht, lieferst du "walk":"middle" zurück. 
* Wenn der Spieler durch die geheime Tür, also die Geheimtür, geht, lieferst du "walk":"middle_alt" zurück. 
* Wenn der Spieler den Schlüssel aufnimmt, lieferst du "take":"key" zurück.
* Wenn der Spieler die geheime Tür öffnet, lieferst du "open":"secretdoor" zurück.
* Wenn der Spieler sich umsehen will, beschreibe ihm den Raum, und liefere "noop":"" zurück
* Bei allen anderen Eingaben reagiere angemessen und liefere "noop":"" zurück.
* Mit "walk" darfst Du nur "middle" oder "middle_alt" zurückliefern, keinen Türnamen wir Tür oder geheimtür oder secretdoor
""",

    "middle": """
Der Spieler steht in einer steinernen Halle. Es hängen ein paar verstaubte Bilder an der Wand, 
ansonsten ist es sehr langweilig hier. Der Spieler kann in den vorigen Raum zurückgehen, oder 
er kann in den nächsten Raum gehen, oder er kann sich umsehen.

* Wenn der Spieler in den vorigen Raum zurückgeht lieferst du "walk":"start" zurück
* Wenn der Spieler in den nächsten Raum geht, lieferst Du "walk":"ende" zurück.
* Wenn der Spieler sich umsehen will, liefere "show":"" zurück
* Wenn der Spieler nach Hilfe fragt, liefere "help":"" zurück. 
* Bei allen anderen Eingaben reagiere angemessen und liefere "noop":"" zurück.  


""",

    "middle_alt": """
Bei dem Raum handelt es sich um eine versteckte Bibliothek. Es war lange niemand mehr hier, 
deswegen ist alles mit Staub und Spinnweben überzogen. Es gibt wandhohe Regale voller Bücher 
und Folianten. Der Spieler kann sich umsehen, und du musst ihm den Raum beschreiben, dabei 
kannst du ihn in recht düsteren Worten beschreiben. Der Spieler kann sich auch einzelne Bücher 
aus den Regalen ansehen, aber sie sind in Geheimschrift verfasst, sodass der Spieler sie nicht 
verstehen kann. In einer Ecke des Raums befindet sich ein verschlissener Ohrensessel, daneben 
ein kleiner Tisch. Der Ohrensessel war bestimmt einmal gemütlich, aber er ist nun mit Staub 
bedeckt, und eine fette Spinne hat sich oben rechts auf ihm eingenistet und ein Spinnennetz 
zwischen Sessel und Tisch gebaut. 

Auf dem Tisch befindet sich ein altes Buch mit dem Titel "Des Rätsels Lösung". Dieser Titel 
ist der Einzige Titel, den der Spieler lesen kann. Das Buch ist das einzige, welches der Spieler 
mitnehmen kann, sodass es in seinem Inventory landet.

Der Raum hat zwei Türen. Durch die erste ist der Spieler in den Raum gelangt, die zweite führt 
in einen weiteren Raum. Der Spieler kann durch beide Türen hindurchgehen.

* Wenn der Spieler um Hilfe bittet, lieferst Du "help":"" zurück.
* Wenn der Spieler in den vorigen Raum zurückgeht, lieferst du "walk":"start" zurück
* Wenn der Spieler in den nächsten Raum geht, lieferst du "walk":"end" zurück.
* Wenn der Spieler das alte Buch, welches auf dem Tisch liegt, aufnimmt oder ansieht, lieferst du "take":"oldbook" zurück
* Wenn der Spieler sich umschaut liefere "show":"" zurück.
* Bei allen anderen Aktionen reagiere angemessen, und liefere "noop":"" zurück

""",
    "end":"""
Dies ist der letzte Raum des Spiels. In ihm sitzt ein Beamter an einem alten Holzschreibtisch. Die Tür, durch 
die der Spieler gekommen ist, fällt ins Schloss und ist verschlossen. Der Spieler kann nicht mehr zurück. Es gibt aber 
eine Ausgangstür. Der Spieler kann sich umsehen, aber bis auf den Beamten am Schreibtisch gibt es nichts zu sehen. der Beamte blickt 
von seinem Schreibtisch auf und fragt: "Haben sie das Buch?"     

* Wenn der Spieler mit "ja" antwortet und das Buch (oldbook) im Inventory hat, lieferst Du success zurück
* Wenn der Spieler antwortet und das Buch (oldbook) nicht im Inventory hat, liefers du failure zurück
* Wenn der Spieler sich umsehen möchte, lieferst Du "show":"" zurück
* Wenn der Spieler um Hilfe bittet, lieferst Du "help":"" zurück.
"""
}

def interpret_user_input_as_actions(free_text: str, room: str, inventory: List[str], room_conditions: dict) -> ActionList:
    context = room_conditions.get(room, "")
    inventory_str = ", ".join(inventory) if inventory else "nichts"

    prompt = f"""
Du bist ein Parser für ein Text-Adventure. 
Aufgrund der Eingabe des Spielers, dem Raum, dem Inhalt des Inventories und den 
speziellen Anweisungen für den Raum lieferst Du Anworten zurück, die von der 
Spiele-Logik weiterverarbeitet werden. Die Antworten müssen einem genauen Format folgen.
Dabei handelt es sich um eine Liste von Verb,Objekt-Kombinationen. Die Antwort kann
eine oder mehrere Zeilen umfassen.

Beispiel:

"verb1","Objekt1"
"verb2","Objekt2"

Als Verben darfst Du ausschließlich nur die Verben

show
take
examine
walk
open
help
look
noop
unknown

verwenden. Die Objekte werden in der Beschreibung des Raums dargestellt. 

Der Spieler befindet sich im Raum: "{room_names[room]}".
Er hat im Inventar: {inventory_str}

Folge zusätzlich der folgenden Beschreibung und den Anweisungen des Raumes bei der Erzeugung der Antwort:

{context}

Der Spieler schreibt:
"{free_text}"



"""
    # print(f"Generated Prompt:\n {prompt}")
    response = model.generate_content(prompt)
    raw_output = response.text.strip()
 #   print(f"------------------------------\n\nGenerated Response: {raw_output}\n----------------------\n\n")
    # einfache Parserfunktion: extrahiere Tupel aus Text
    import re
    actions = re.findall(r'"([^"]+)",\s*"([^"]*)"', raw_output)
#    actions
#    print("--------------------------------")
    return actions
#
# Test
#
#text = "Ich nehme das alte Buch, dann gehe ich weiter."
#actions = interpret_user_input_as_actions(text, "middle_alt", [], room_conditions)
#actions
#

def narrate(room: str, inventory: List[str], input_type: str, prompt="") -> str:
    """
    input_type ist entweder: 'umsehen' oder 'hilfe'
    """
    base_context = room_conditions.get(room, "Keine Beschreibung verfügbar.")
    inventory_str = ", ".join(inventory) if inventory else "nichts"

    if input_type == "show":
        instruction = "Beschreibe den Raum für den Spieler. Gehe dabei auf Details ein, die für ihn interessant sein könnten. Berücksichtige auch die Eingabe des Spielers. Liefere Noop zurück."
    elif input_type == "help":
        instruction = "Gib dem Spieler einen nützlichen Hinweis, was er als nächstes tun kann. Sprich ruhig geheimnisvoll oder andeutend, wenn es passt. Liefer Noop zurück."
    else:
        instruction = ""

    prompt = f"""
Du bist der Erzähler beziehungsweise Spielleiter eines Text-Adventures. 


Der Spieler befindet sich im Raum "{room_names[room]}".

Er hat im Inventar: {inventory_str}

Er hat folgendes gefragt: {prompt}

Hier ist die Beschreibung des Raumes und wichtige Hinweise:
{base_context}

Deine Aufgabe: {instruction}
"""

    response = model.generate_content(prompt)
    return response.text.strip()


class GraphState(TypedDict):
    user_inputs: List[str]
    inventory: List[str]
    last_input: str  # bleibt erhalten
    actions: List[Tuple[str, str]]  # → die noch offenen Aktionen
    visited_start: Boolean


def start_node(state: GraphState) -> GraphState:
    print("\n== Start ==")
    if not state.get("visited_start"):
        state["visited_start"] = True
        print(narrate("start",state["inventory"],"show"))
    # Wenn keine Aktionen im Zustand stehen, frage nach neuer Eingabe
    if not state.get("actions"):
        free_input = input("Was tust du? ").strip()
        state["user_inputs"].append(free_input)
        actions = interpret_user_input_as_actions(free_input, "start", state["inventory"], room_conditions)
        state["actions"] = actions


        
    # Verarbeite Aktionen nacheinander
    remaining_actions = []
    for verb, obj in state["actions"]:
        print(f"🔍 Aktion erkannt: ({verb}, {obj})")

        if verb == "look":
            print(narrate("start", state["inventory"], "show"))

        elif verb == "help":
            print("💡 Hinweis:")
            print(narrate("start", state["inventory"], "help"))

        elif verb == "take" and obj.lower() == "key":
            if "key" not in state["inventory"]:
                state["inventory"].append("key")
                print("Du nimmst den Schlüssel an dich.")
            else:
                print("Du hast den Schlüssel bereits.")

        elif verb == "open" and obj.lower() == "secretdoor":
            if "key" in state["inventory"]:
                print("Du öffnest die geheime Tür.")
                state["secretdoor"] = True
                # Spieler muss Raum aktiv "betreten", kein Autowechsel
            else:
                print("Die geheime Tür ist verschlossen - schau dich nochmal um.")

        elif verb == "walk":
            if obj.lower() == "middle":
                print("Du gehst durch die normale Tür.")
                state["last_input"] = "middle"
                remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                state["actions"] = remaining_actions
                return state
            elif obj.lower() == "middle_alt":
                if state.get("secretdoor"):
                    print("Du gehst durch die Geheimtür.")
                    state["last_input"] = "middle_alt"
                    remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                    state["actions"] = remaining_actions
                    return state
                else:
                    print("Du läufst vor die verschlossene Geheimtuer und tust dir weh. Sieht ziemlich bescheuert aus.")
            else:
                print("Ich habe nicht verstanden, wohin du gehen willst. Schau dich lieber nochmal um!")

        elif verb == "noop":
            pass

        else:
            print(f"Unbekannte Aktion: ({verb}, {obj})")

    # Setze verbleibende Aktionen (für Folgeknoten)
    state["actions"] = remaining_actions
    return state

def middle_node(state: GraphState) -> GraphState:
    print("\n== Halle ==")
    if not state.get("visited_start"):
        state["visited_start"] = True
        print(narrate("start", state["inventory"], "show"))
        # Wenn keine Aktionen im Zustand stehen, frage nach neuer Eingabe
    if not state.get("actions"):
        free_input = input("Was tust du? ").strip()
        state["user_inputs"].append(free_input)
        actions = interpret_user_input_as_actions(free_input, "start", state["inventory"], room_conditions)
        state["actions"] = actions

        # Verarbeite Aktionen nacheinander
    remaining_actions = []
    for verb, obj in state["actions"]:
        print(f"🔍 Aktion erkannt: ({verb}, {obj})")

        if verb == "look":
            print(narrate("start", state["inventory"], "show"))

        elif verb == "help":
            print("💡 Hinweis:")
            print(narrate("start", state["inventory"], "help"))

        elif verb == "take" and obj.lower() == "key":
            if "key" not in state["inventory"]:
                state["inventory"].append("key")
                print("Du nimmst den Schlüssel an dich.")
            else:
                print("Du hast den Schlüssel bereits.")

        elif verb == "open" and obj.lower() == "secretdoor":
            if "key" in state["inventory"]:
                print("Du öffnest die geheime Tür.")
                state["secretdoor"] = True
                # Spieler muss Raum aktiv "betreten", kein Autowechsel
            else:
                print("Die geheime Tür ist verschlossen - schau dich nochmal um.")

        elif verb == "walk":
            if obj.lower() == "middle":
                print("Du gehst durch die normale Tür.")
                state["last_input"] = "middle"
                remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                state["actions"] = remaining_actions
                return state
            elif obj.lower() == "middle_alt":
                if state.get("secretdoor"):
                    print("Du gehst durch die Geheimtür.")
                    state["last_input"] = "middle_alt"
                    remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                    state["actions"] = remaining_actions
                    return state
                else:
                    print("Du läufst vor die verschlossene Geheimtuer und tust dir weh. Sieht ziemlich bescheuert aus.")
            else:
                print("Ich habe nicht verstanden, wohin du gehen willst. Schau dich lieber nochmal um!")

        elif verb == "noop":
            pass

        else:
            print(f"Unbekannte Aktion: ({verb}, {obj})")

    # Setze verbleibende Aktionen (für Folgeknoten)
    state["actions"] = remaining_actions
    return state

def middle_alt_node(state: GraphState) -> GraphState:
    print("\n== Geheime Bibliothek ==")
    if not state.get("visited_library"):
        state["visited_library"] = True
        print(narrate("middle_alt", state["inventory"], "show"))
        # Wenn keine Aktionen im Zustand stehen, frage nach neuer Eingabe
    if not state.get("actions"):
        free_input = input("Was tust du? ").strip()
        state["user_inputs"].append(free_input)
        actions = interpret_user_input_as_actions(free_input, "middle_alt", state["inventory"], room_conditions)
        state["actions"] = actions

        # Verarbeite Aktionen nacheinander
    remaining_actions = []
    for verb, obj in state["actions"]:
        print(f"🔍 Aktion erkannt: ({verb}, {obj})")

        if verb == "look":
            print(narrate("middle_alt", state["inventory"], "show"))

        elif verb == "help":
            print("💡 Hinweis:")
            print(narrate("middle_alt", state["inventory"], "help"))

        elif verb == "take" and obj.lower() == "oldbook":
            if "oldbook" not in state["inventory"]:
                state["inventory"].append("oldbook")
                print("Du nimmst das alte Buch vom Tisch an dich.")
            else:
                print("Du hast das alte Buch bereits.")


        elif verb == "walk":
            if obj.lower() == "start":
                print("Du gehst zurück zum ersten Raum.")
                state["last_input"] = "start"
                remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                state["actions"] = remaining_actions
                return state
            elif obj.lower() == "end":
                print("Du gehst in das nächste Zimmer")
                state["last_input"] = "end"
                remaining_actions = state["actions"][state["actions"].index((verb, obj)) + 1:]
                state["actions"] = remaining_actions
                return state
            else:
                print("Ich habe nicht verstanden, wohin du gehen willst. Schau dich lieber nochmal um!")

        elif verb == "noop":
            pass

        else:
            print(f"Unbekannte Aktion: ({verb}, {obj})")

    # Setze verbleibende Aktionen (für Folgeknoten)
    state["actions"] = remaining_actions
    return state

def end_node(state: GraphState) -> GraphState:
    print("\n== Ende ==")
    print(narrate("end", state["inventory"], "umsehen"))

    if "altes buch" in state["inventory"]:
        print("✨ Du hast das alte Buch – das Abenteuer ist erfolgreich abgeschlossen!")
    else:
        print("❌ Du hast das Buch nicht – das Abenteuer bleibt unvollständig.")

    return END

def route_from_last_input(state: GraphState) -> str:
    return state["last_input"]

# Routing vom Startknoten
def route_from_start(state: GraphState) -> str:
    return state["last_input"]

# Graph definieren
builder = StateGraph(GraphState)
builder.add_node("start", start_node)
builder.add_node("middle", middle_node)
builder.add_node("middle_alt", middle_alt_node)
builder.add_node("end", end_node)

builder.set_entry_point("start")
builder.add_conditional_edges("start", route_from_last_input)
builder.add_conditional_edges("middle", route_from_last_input)
builder.add_conditional_edges("middle_alt", route_from_last_input)
builder.add_edge("end", END)

graph = builder.compile()

# Anfangszustand
initial_state = {
    "user_inputs": [],
    "last_input": "",
    "inventory": [],
    "actions": [],
    "visited_start": False,
    "visited_library": False,
    "secretdoor": False
}

state = initial_state

while True:
    state = graph.invoke(state)
    if state == END or state.get("last_input") == "end":
        break
        
