def system_message_to_player(message: str):
    print(f"📢 {message}")

def internal_note_to_llm(llm, promptgen, state, note_text: str):
    note_prompt = f"""[INTERNAL SYSTEM UPDATE]
Folgende neue Information muss in den Spielkontext übernommen werden:
{note_text}
(Keine Tool-Calls erzeugen. Einfach im Gedächtnis behalten.)"""
    try:
        _ = llm.invoke(promptgen.build_prompt(state, note_prompt))
    except Exception as e:
        log_error(f"Fehler bei interner LLM-Notiz: {e}")
import re
import json
from IPython.display import HTML, Markdown, display

ALLOWED_TOOL_CALLS = ["gehe", "nimm", "untersuche", "anwenden", "umsehen", "inventory"]
#
# Nächste Version des Adventures, 2025-04-22
#
# Siehe Koversation in ChatGPT/Projekt AI Training/Sprachmodell und Agentenarchitektur
#
#
# PromptGenerator-Klasse für Adventure5
#

class PromptGenerator:
    def build_prompt_for_multiple_tool_calls(self, state, user_input, tool_calls, system_feedbacks):
        """
        Baut einen Prompt für das LLM, der mehrere Tool-Calls und deren Systemrückmeldungen zusammenfasst.
        """
        room_prompt = state.get("room_prompt", "")
        inventory = state.get("inventory", [])
        location = state.get("location", "")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("wege", {}) if location else {}

        # Formatierte Gegenstände-Liste (mit IDs)
        if rin:
            formatted_objekte = "\n".join([
                f"- {obj} ({items[obj].name})" if obj in items else f"- {obj}"
                for obj in rin
            ])
        else:
            formatted_objekte = "Keine Gegenstände vorhanden."

        # Formatierte Wege- und Türen-Liste
        if wege:
            lines = []
            for richtung, daten in wege.items():
                zielraum = daten.get("raum", "unbekannt")
                status = "offen" if not daten.get("verschlossen", False) else "verschlossen"
                tueren = [
                    obj for obj in rin
                    if isinstance(items.get(obj), Door)
                    and items[obj].direction.lower() == richtung.lower()
                    and items[obj].target_room == zielraum
                ]
                if tueren:
                    tueren_str = ", ".join([f"{items[t].name} [ID: {t}]" for t in tueren])
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status} | Tür: {tueren_str}"
                    )
                else:
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status}"
                    )
            formatted_wege_tueren = "\n".join(lines)
        else:
            formatted_wege_tueren = "Keine Ausgänge vorhanden."

        # Tool-Calls und Systemfeedbacks zusammenfassen
        tc_lines = []
        for tc, feedback in zip(tool_calls, system_feedbacks):
            tc_lines.append(f'- Tool-Call: {tc}\n  Antwort: {feedback}')
        tc_block = "\n".join(tc_lines)

        return f"""=== BENUTZEREINGABE ===
"{user_input}"

=== TOOL-CALLS UND SYSTEMRÜCKMELDUNGEN ===
{tc_block}

== AUFGABE ==
Formuliere eine kurze, stimmungsvolle Erzählung auf Basis dieser Aktionen und ihrer Auswirkungen.
"""
    def __init__(self, system_prompt: str):
        self.system_prompt = """
Du bist der Spielleiter eines Text-Adventures im Stil der 1980er-Jahre auf dem C64. Deine Aufgabe ist es, stimmungsvolle, geheimnisvolle Geschichten zu erzählen und auf die Aktionen des Spielers in einer strukturierten Form zu reagieren.

=== FORMAT DER ANTWORT ===
Gib deine gesamte Antwort ausschließlich im folgenden JSON-Format aus:

{
  "story": "Hier steht die atmosphärische Erzählung, die beschreibt, was der Spieler erlebt.",
  "tool_calls": [
    "tool_call_1",
    "tool_call_2",
    ...
  ]
}

Hinweise:
- Das Feld "story" enthält eine stimmungsvolle Beschreibung der aktuellen Situation. Bleibe immer bei den Fakten der Spielwelt.
- Das Feld "tool_calls" enthält eine Liste aller aus der Eingabe abgeleiteten Aktionen als Strings. Jeder Tool-Call einzeln.
- Wenn keine Tool-Calls nötig sind, gib ein leeres Array [] zurück.
- Keine weiteren Kommentare, keine Markdown-Formatierung, keine zusätzlichen Texte außerhalb des JSON.

=== ZULÄSSIGE TOOL-CALLS ===
  'gehe("richtung")'
  'nimm("gegenstand")'
  'anwenden("objekt1", "objekt2")'
  'untersuche("gegenstand")'
  'umsehen()'
  'inventory()'

=== REGELN ZUR TOOL-CALL-GENERIERUNG ===
- Jede einzelne logische Aktion muss ein eigener Tool-Call sein!
- Wenn der Spieler mehrere Bewegungen beschreibt (z.B. "Ich gehe nach Süden und dann zweimal nach Westen"), erzeuge für jede Bewegung einen eigenen 'gehe()'-Tool-Call in korrekter Reihenfolge.
- Objekt1 ist das, was der Spieler benutzt (z.B. Schlüssel, Zahlencode).
- Objekt2 ist das Zielobjekt (z.B. Tür, Zahlenschloss).
- Benutze exakt die angegebenen Tool-Call-Syntax.
- Nutze nur die IDs und Begriffe, die im aktuellen Raum verfügbar sind.

=== BEISPIELE ===
Eingabe: "Ich schließe die Tür auf und gehe hindurch."
Antwort:
{
  "story": "Mit einem satten Klicken öffnet sich die Tür. Ein dunkler Gang liegt vor dir.",
  "tool_calls": [
    "anwenden(\"Schluessel\", \"Tuer_Norden\")",
    "gehe(\"norden\")"
  ]
}

Eingabe: "Ich schaue mich um."
Antwort:
{
  "story": "Du blickst dich um und entdeckst staubige Regale und eine alte Tür im Westen.",
  "tool_calls": [
    "umsehen()"
  ]
}
"""

    def build_prompt(self, state: dict, user_input: str, allowed_tool_calls: list = None) -> str:
        """
        Kombiniert den Systemprompt mit Raumkontext, Inventar und der aktuellen Benutzereingabe zu einem vollständigen Prompt.
        """
        room_prompt = state.get("room_prompt", "")
        inventory = state.get("inventory", [])
        actions = state.get("available_actions", [])
        location = state.get("location", "")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("wege", {}) if location else {}

        tool_section = ""
        if allowed_tool_calls:
            tool_section = f"\n=== ZULÄSSIGE TOOL-CALLS (JETZT ERLAUBT) ===\n" + "\n".join(allowed_tool_calls)

        # Formatierte Gegenstände-Liste (mit IDs)
        if rin:
            formatted_objekte = "\n".join([
                f"- {obj} ({items[obj].name})" if obj in items else f"- {obj}"
                for obj in rin
            ])
        else:
            formatted_objekte = "Keine Gegenstände vorhanden."

        # Formatierte Wege- und Türen-Liste
        if wege:
            lines = []
            for richtung, daten in wege.items():
                zielraum = daten.get("raum", "unbekannt")
                status = "offen" if not daten.get("verschlossen", False) else "verschlossen"
                # Versuche, die Tür zu finden (Gegenstand mit Typ Door, Richtung und Zielraum passend)
                tueren = [
                    obj for obj in rin
                    if isinstance(items.get(obj), Door)
                    and items[obj].direction.lower() == richtung.lower()
                    and items[obj].target_room == zielraum
                ]
                if tueren:
                    tueren_str = ", ".join([f"{items[t].name} [ID: {t}]" for t in tueren])
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status} | Tür: {tueren_str}"
                    )
                else:
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status}"
                    )
            formatted_wege_tueren = "\n".join(lines)
        else:
            formatted_wege_tueren = "Keine Ausgänge vorhanden."

        return f"""{self.system_prompt}
{tool_section}

=== RAUMKONTEXT ===
{room_prompt}

=== SPIELZUSTAND ===
Inventar: {', '.join(inventory) if inventory else 'nichts'}
Aktionen: {', '.join(actions) if actions else 'keine'}

=== VERFÜGBARE GEGENSTÄNDE ===
{formatted_objekte}

=== VERFÜGBARE WEGE UND TÜREN ===
{formatted_wege_tueren}

=== BENUTZEREINGABE ===
"{user_input}"

== AUFGABE ==
Reagiere gemäß den Regeln. Sei stimmungsvoll, aber halte dich exakt an die vorhandenen strukturierten Daten.
"""

    def build_prompt_for_llm_answer(self, state: dict, user_input: str, tool_call_text: str, system_response_text:str, allowed_tool_calls: list = None) -> str:
        """
        Kombiniert den Systemprompt mit Raumkontext, Inventar, der aktuellen Benutzereingabe, dem aktuellen
        Tool-Call und der Rückmeldung der Game-Engine zu einem vollständigen Prompt.
        """
        room_prompt = state.get("room_prompt", "")
        inventory = state.get("inventory", [])
        location = state.get("location","")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("wege", {}) if location else {}

        tool_section = ""
        if allowed_tool_calls:
            tool_section = f"\n=== ZULÄSSIGE TOOL-CALLS (JETZT ERLAUBT) ===\n" + "\n".join(allowed_tool_calls)

        # Formatierte Gegenstände-Liste (mit IDs)
        if rin:
            formatted_objekte = "\n".join([
                f"- {obj} ({items[obj].name})" if obj in items else f"- {obj}"
                for obj in rin
            ])
        else:
            formatted_objekte = "Keine Gegenstände vorhanden."

        # Formatierte Wege- und Türen-Liste
        if wege:
            lines = []
            for richtung, daten in wege.items():
                zielraum = daten.get("raum", "unbekannt")
                status = "offen" if not daten.get("verschlossen", False) else "verschlossen"
                # Versuche, die Tür zu finden (Gegenstand mit Typ Door, Richtung und Zielraum passend)
                tueren = [
                    obj for obj in rin
                    if isinstance(items.get(obj), Door)
                    and items[obj].direction.lower() == richtung.lower()
                    and items[obj].target_room == zielraum
                ]
                if tueren:
                    tueren_str = ", ".join([f"{items[t].name} [ID: {t}]" for t in tueren])
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status} | Tür: {tueren_str}"
                    )
                else:
                    lines.append(
                        f"- {richtung.capitalize()} ➔ {zielraum} | {status}"
                    )
            formatted_wege_tueren = "\n".join(lines)
        else:
            formatted_wege_tueren = "Keine Ausgänge vorhanden."

        return f"""{self.system_prompt}
{tool_section}

=== RAUMKONTEXT ===
{room_prompt}

=== SPIELZUSTAND ===
Inventar: {', '.join(inventory) if inventory else 'nichts'}

=== VERFÜGBARE GEGENSTÄNDE ===
{formatted_objekte}

=== VERFÜGBARE WEGE UND TÜREN ===
{formatted_wege_tueren}

=== BENUTZEREINGABE ===
"{user_input}"

=== TOOL-CALL UND SYSTEMRÜCKMELDUNG ===
Tool-Call: {tool_call_text}
Antwort der Game-Engine: {system_response_text}

== AUFGABE ==
Formuliere eine passende Antwort für den Spieler gemäß der Regeln und der Rückmeldung. Erzeuge KEINE tool calls!
"""

    def is_game_related(self, llm, user_input: str, room_context: str) -> bool:
        """
        Fragt das LLM, ob die Eingabe sich auf das Spiel bezieht. Gibt True zurück, wenn ja, sonst False.
        """
        check_prompt = f"""{self.system_prompt}

=== SYSTEMPRÜFUNG ===
Du bist ein Prüfer für ein Text-Adventure. Prüfe, ob die folgende Eingabe sich auf das Spiel bezieht.

=== RAUMKONTEXT ===
{room_context}

=== BENUTZEREINGABE ===
"{user_input}"

Antwort nur mit JA oder NEIN.
"""
        response = llm.invoke(check_prompt)
        answer = response.content.strip().lower()
        return answer.startswith("ja")


# --- Spielwelt-Strukturen ---

rooms = {
    "halle": {
        "name": "Karger Raum",
        "beschreibung": """
        Du wachst in einem kargen Raum ohne Fenster auf. Der Raum hat Sandsteinmauern. Es liegen einige 
        Gegenstände im Raum herum. 
        """,
        "gegenstaende": ["Kissen", "Luftpumpe", "Schraubstock", "Schuhloeffel", "Schluessel", "Tuer_Norden", "Tuer_Westen"],
        "wege": {
            "norden": {
                "raum": "bibliothek",
                "verschlossen": True
            },
            "westen": {
                "raum": "durchgang",
                "verschlossen": False
            }
        },
        "room_prompt": """
        * Du bist ein begabter Erzähler, der gerne geheimnisvolle Geschichten erzählt. Halte dich an 
          die vorgegebenen Fakten. 
        * Wenn der Spieler sich umsieht:
          - Beschreibe, in welcher Himmelsrichtung Türen sind, und ob 
            diese verschlossen sind, 
            und halte dich an die Beschreibung der Türen. Erwähne dabei im Text die raumID nicht, 
            diese wird nur bei den tool-Calls verwendet, die weiter unten kommen. 
         -  Erwähne immer alle Gegenstände im Raum, aber erfinde keine neuen.
        * Wenn der Spieler um Hilfe bittet, unterscheide zwei Fälle:
          1) Wenn ein Schlüssel bei den Gegenständen im Raum, oder im Inventory des Spielers ist, weise ihn darauf 
             hin, dass dieser doch in die Tür im Norden passen könnte. Erzähle dies passend.
          2) Wenn KEIN Schlüssel im Raum oder im Inventory des Spielers ist, weise den Spieler daruf hin, dass das 
             Kissen doch recht gemütlich aussieht.
        """
    },
    "bibliothek": {
        "name": "Alte Bibliothek",
        "beschreibung": "Eine staubige Bibliothek mit hohen Regalen voller Bücher.",
        "gegenstaende": ["buch"],
        "wege": {
            "sueden": {
                "raum": "halle",
                "verschlossen": False,
                "beschreibung": "Die Tür zur Halle steht offen."
            }
        },
        "room_prompt": "Hier riecht es nach altem Papier. Erwähne die Vielzahl an Büchern."
    },
    "durchgang": {
        "name": "Durchgang",
        "beschreibung": "Ein schmuckloser Durchgang. ",
        "wege": {
            "osten": {
                "raum": "halle",
                "verschlossen": False,
                "beschreibung": "Die Tür zurück zum Eingangsraum steht offen."
            },
            "westen": {
                "raum": "finalraum",
                "verschlossen": False,
                "beschreibung": "Die Tür zum nächsten raum steht offen."
            }
        },
        "room_prompt": "Es ist viel Staub hier. Man könnte hier mal wieder putzen. Ansonsten ist es rech langweilig hier"
    },
    "finalraum":{
        "name": "Letzter Raum",
        "beschreibung": "Dieser Raum ist eigentlich auch recht öde. Da hätten sie sich in diesem Game echt mal mehr ausdenken können!",
        "wege": {
            "osten": {
                "raum":"durchgang",
                "verschlossen": False,
                "beschreibung": "Hier geht es wieder in den Durchgang"
            },
            "westen": {
                "raum": "ende",
                "verschlossen": True,
                "beschreibung": 'Eine Stahltür, darüber ein Schild, auf dem "Exit" steht'
            }
        },
        "gegenstaende": ["zahlenschloss"],
        "room_prompt":"Der Raum ist aus Beton und völlig schmucklos. An der Wand hängt ein Zahlenschloss"
    },
    "ende": {
        "name": "wunderschöne Wiese",
        "beschreibung":
            """Eine wunderschöne Wiese mit Blumen. Die Sonne scheint. Die Luft duftet nach Sommer. Hinter Dir ein 
               Betonklotz mit der Stahltür, durch die du gekommen bist. Die Tür ist nun verschlossen. 
               Du hast das Spiel gewonnen.      
            """,
        "wege": {},
        "gegenstaende": [],
        "room_prompt": """
        Der Spieler hat das Spiel gewonnen. Beschreibe ihm den Raum (also die Wiese) mit blumigen Worten
        """
    }
}


# --- Klassen für Spielobjekte ---

class GameObject:
    def __init__(self, name, examine, help_text="", fixed=False):
        self.name = name
        self.examine = examine
        self.help_text = help_text
        self.fixed = fixed  # False bedeutet: Kann aufgenommen werden

class Door(GameObject):
    def __init__(self, name, examine, direction, target_room, locked=True, help_text="Eine massive Tür."):
        super().__init__(name, examine, help_text, fixed=True)
        self.locked = locked
        self.direction = direction
        self.target_room = target_room

# --- Neues Items-Dictionary basierend auf den Klassen ---

items = {
    "Laterne": GameObject(
        name="verbeulte Laterne",
        examine="Die Laterne ist verbeult, aber sieht noch funktionstüchtig aus."
    ),
    "Schluessel": GameObject(
        name="großer Schlüssel",
        examine="Ein großer Schlüssel aus Eisen. Könnte in ein Türschloss passen"
    ),
    "Zettel": GameObject(
        name="zerknitterter Zettel",
        examine="Ein alter Zettel mit einer kaum lesbaren Notiz: 'Der Schlüssel liegt unter der Laterne...'"
    ),
    "Kissen": GameObject(
        name="Kissen",
        examine="Ein weiches, recht zerschlissenes Kissen. Liegt eventuell etwas darunter?"
    ),
    "Luftpumpe": GameObject(
        name="Luftpumpe",
        examine="Eine gewöhnliche Luftpumpe für ein Fahrrad. Muss jemand hier verloren haben"
    ),
    "Schraubstock": GameObject(
        name="Schraubstock",
        examine="Ein Schraubstock. Merkwürdig – was der hier soll?"
    ),
    "Schuhloeffel": GameObject(
        name="Schuhlöffel",
        examine="Ein Schuhlöffel – Zeichen von Anstand und Zivilisation"
    ),
    "buch": GameObject(
        name="altes geheimnisvolles Buch",
        examine="Ein altes Buch voller Geheimnisse! Auf der ersten Seite steht eine Zahl: 8513"
    ),
    "zahlenschloss": GameObject(
        name="Zahlenschloss",
        examine="Sieht aus, als könntest du hier vier Zahlen eingeben. Ob das wohl eine Tür öffnet?",
        fixed=True  # Feste Installation
    ),
    "Tuer_Norden": Door(
        name="Massives Holztor",
        examine="Ein massives Tor aus dunklem Holz. Es ist verschlossen.",
        direction="norden",
        target_room="bibliothek",
        locked=True
    ),
    "Tuer_Westen": Door(
        name="Schlichte Holztür",
        examine="Eine einfache Tür aus Holz. Sie steht offen.",
        direction="westen",
        target_room="durchgang",
        locked=False
    )
}

state = {
    "location": "halle",
    "inventory": [],
    "last_input": "Ich sehe mich erst einmal um."
}


# --- Helper-Funktionen für Inventar und Raumgegenstände ---

def get_inventory(state):
    return state.get("inventory", [])

def add_inventory(state, item):
    inv = state.setdefault("inventory", [])
    if item not in inv:
        inv.append(item)

def rem_inventory(state, item):
    inv = state.get("inventory", [])
    if item in inv:
        inv.remove(item)

def get_objects(state):
    location = state.get("location", "")
    if location and location in rooms:
        return rooms[location].get("gegenstaende", [])
    return []

def add_object(state, item):
    location = state.get("location", "")
    if location and location in rooms:
        objs = rooms[location].setdefault("gegenstaende", [])
        if item not in objs:
            objs.append(item)

def rem_object(state, item):
    location = state.get("location", "")
    if location and location in rooms:
        objs = rooms[location].get("gegenstaende", [])
        if item in objs:
            objs.remove(item)


# --- Neue Hilfsfunktionen ---

def log_error(message: str):
    with open("game_error_log.txt", "a") as logfile:
        logfile.write(message + "\n")

def execute_tool_call(tool_call: str):
    """
    Führt einen Tool-Call sicher aus, wenn erlaubt.
    """
    try:
        func_name = tool_call.split("(")[0].strip()

        if func_name not in ALLOWED_TOOL_CALLS:
            log_error(f"❌ Nicht erlaubter Tool-Call: {tool_call}")
            return "Fehler: Unbekannte Aktion."

        # Spezieller Umbau für untersuche()
        if func_name == "untersuche":
            import ast
            # Extrahiere Argument
            match = re.match(r'untersuche\("([^"]+)"\)', tool_call)
            if match:
                gegenstand = match.group(1)
                inventar = get_inventory(state)
                objekte = get_objects(state)
                all_items = inventar + objekte
                matched_obj_key = next((obj for obj in all_items if obj.lower() == gegenstand.lower()), None)
                if matched_obj_key:
                    item_info = items.get(matched_obj_key)
                    # Wenn examine-Text vorhanden, Spezialprompt
                    if item_info and getattr(item_info, "examine", None):
                        # Prompt bauen
                        examine_text = item_info.examine
                        name = item_info.name
                        # Prompt für LLM bauen, KEINE Tool-Calls erlauben
                        llm_prompt = f"""Du betrachtest {name}. Hier ist die Beschreibung: {examine_text}
Beschreibe stimmungsvoll, was du erkennst, aber füge keine neuen Elemente hinzu."""
                        # KEINE Tool-Calls erlauben
                        if "llm" in globals() and "promptgen" in globals():
                            mini_prompt = promptgen.build_prompt(state, llm_prompt, allowed_tool_calls=[])
                            mini_response = llm.invoke(mini_prompt)
                            mini_content = mini_response.content.strip()

                            # Versuche JSON herauszuziehen (wegen Standard-LLM-Ausgabe)
                            try:
                                cleaned = extract_json_from_response(mini_content)
                                parsed = json.loads(cleaned)
                                mini_story = parsed.get("story", "").strip()
                                return mini_story
                            except Exception:
                                # Falls Parsing fehlschlägt, gib Rohtext aus
                                return mini_content
                        else:
                            return f"Erfolg: {examine_text}"
                    elif item_info:
                        return f"Erfolg: {item_info.examine}"
                    else:
                        return "Fehler: Keine Informationen zum Gegenstand vorhanden."
                return f"Fehler: {gegenstand} ist nicht hier vorhanden."
            # Fallback auf Standard
            result = eval(tool_call)
            if result and isinstance(result, str):
                system_message_to_player(f"📢 {result}")
            return result

        # Umbau für gehe(): Nach erfolgreichem Raumwechsel, explizites Prompt für umsehen()
        if func_name == "gehe":
            result = eval(tool_call)
            if isinstance(result, str) and result.startswith("Erfolg"):
                # Nach Raumwechsel: explizites Prompt für umsehen()
                if "llm" in globals() and "promptgen" in globals():
                    # Systemmeldung für Raumwechsel explizit (kurz, fett)
                    # Hole Richtung aus Tool-Call
                    match = re.match(r'gehe\("([^"]+)"\)', tool_call)
                    richtung = match.group(1) if match else "unbekannt"
                    ziel = state.get("location", "")
                    raumname = rooms[ziel].get("name", "Unbekannt") if ziel in rooms else "Unbekannt"
                    system_message_to_player(f"🚪 Du gehst nach **{richtung.capitalize()}** und betrittst die **{raumname}**.")
                    internal_note_to_llm(llm, promptgen, state, f"Spieler befindet sich jetzt im Raum '{raumname}'.")
                    # Automatisches "umsehen()" nach Raumwechsel, aber gekürzt: nur Gegenstände und Türen
                    room = rooms.get(ziel, {})
                    gegenstaende = room.get("gegenstaende", [])
                    wege = room.get("wege", {})
                    text = ""
                    if gegenstaende:
                        text += "🧸 Gegenstände: " + ", ".join([items[obj].name for obj in gegenstaende if obj in items]) + ". "
                    if wege:
                        exits = []
                        for richt, daten in wege.items():
                            status = "verschlossen" if daten.get("verschlossen", False) else "offen"
                            exits.append(f"{richt.capitalize()} ({status})")
                        if exits:
                            text += "🚪 Ausgänge: " + ", ".join(exits) + "."
                    if text:
                        system_message_to_player(f"{text.strip()}")
                    return result
            if result and isinstance(result, str):
                system_message_to_player(f"📢 {result}")
            return result

        result = eval(tool_call)
        if result and isinstance(result, str):
            system_message_to_player(f"📢 {result}")
        return result

    except Exception as e:
        log_error(f"❌ Fehler beim Ausführen von Tool-Call '{tool_call}': {e}")
        return "Fehler: Aktion fehlgeschlagen."




# --- Inventar anzeigen ---

def inventory() -> str:
    inv = get_inventory(state)
    if not inv:
        return "Du hast momentan nichts bei dir."
    else:
        return "Du hast folgende Gegenstände bei dir:\n- " + "\n- ".join(inv)

# --- Spiellogik-Verben ---

def gehe(richtung: str) -> str:
    location = state.get("location", "")
    if not location or location not in rooms:
        return "Fehler: Unbekannter Standort."

    wege = rooms[location].get("wege", {})
    weg = wege.get(richtung.lower())
    if not weg:
        return "Fehler: Weg existiert hier nicht."

    if weg["verschlossen"]:
        return "Fehler: Weg verschlossen."

    ziel = weg["raum"]
    state["location"] = ziel
    beschreibung = rooms[ziel].get("beschreibung", "Du wechselst den Raum.")
    # Systemmessage und interne Notiz (Ausgabe erfolgt jetzt in execute_tool_call)
    return f"Erfolg: {beschreibung.strip()}"

def nimm(gegenstand: str) -> str:
    objekte = get_objects(state)
    matched_obj_key = next((obj for obj in objekte if obj.lower() == gegenstand.lower()), None)

    if matched_obj_key:
        item_info = items.get(matched_obj_key)
        if isinstance(item_info, GameObject) or isinstance(item_info, Door):
            if hasattr(item_info, "fixed") and item_info.fixed:
                return "Fehler: Dieser Gegenstand ist fest installiert und kann nicht aufgenommen werden."
            else:
                rem_object(state, matched_obj_key)
                add_inventory(state, matched_obj_key)
                # Systemmessage und interne Notiz
                if "llm" in globals() and "promptgen" in globals():
                    system_message_to_player(f"🎒 Du hast '{items[matched_obj_key].name}' aufgenommen.")
                    internal_note_to_llm(llm, promptgen, state, f"Spieler hat '{items[matched_obj_key].name}' im Inventar.")
                return "Erfolg: Gegenstand aufgenommen."
        else:
            return "Fehler: Unbekanntes Objekt."
    else:
        return f"Fehler: {gegenstand} existiert hier nicht."

def untersuche(gegenstand: str) -> str:
    inventar = get_inventory(state)
    objekte = get_objects(state)
    all_items = inventar + objekte
    matched_obj_key = next((obj for obj in all_items if obj.lower() == gegenstand.lower()), None)
    if matched_obj_key:
        item_info = items.get(matched_obj_key)
        if item_info:
            return f"Erfolg: {item_info.examine}"
        else:
            return "Fehler: Keine Informationen zum Gegenstand vorhanden."
    return f"Fehler: {gegenstand} ist nicht hier vorhanden."

def anwenden(gegenstand1: str, gegenstand2: str = None) -> str:
    inventar = get_inventory(state)
    objekte = get_objects(state)
    all_items = inventar + objekte
    location = state.get("location", "")
    wege = rooms[location].get("wege", {})

    matched_obj1_key = next((obj for obj in all_items if obj.lower() == gegenstand1.lower()), None)
    matched_obj2_key = next((obj for obj in all_items if obj.lower() == gegenstand2.lower()), None) if gegenstand2 else None

    if not matched_obj1_key and not matched_obj2_key:
        return "Fehler: Ungültige Aktion. Keine gültigen Objekte angegeben."

    # Spezialfall: Codeeingabe am Zahlenschloss
    if matched_obj2_key and matched_obj2_key.lower() == "zahlenschloss":
        if gegenstand1 == "8513":
            if "westen" in wege and wege["westen"].get("verschlossen", False):
                wege["westen"]["verschlossen"] = False
                # Systemmessage und interne Notiz
                if "llm" in globals() and "promptgen" in globals():
                    system_message_to_player("🔓 Das Zahlenschloss klickt und die Tür nach Westen öffnet sich!")
                    internal_note_to_llm(llm, promptgen, state, "Die Tür nach Westen im Finalraum ist jetzt offen.")
                return "Erfolg: Das Zahlenschloss klickt und die Tür nach Westen öffnet sich!"
            else:
                return "Fehler: Hier gibt es nichts mehr zu entriegeln."
        else:
            return "Fehler: Die Kombination scheint falsch zu sein."

    if matched_obj2_key:
        item_info = items.get(matched_obj2_key)
        if isinstance(item_info, Door):
            richtung = item_info.direction
            if richtung in wege and wege[richtung]["verschlossen"]:
                wege[richtung]["verschlossen"] = False
                # Systemmessage und interne Notiz
                if "llm" in globals() and "promptgen" in globals():
                    system_message_to_player(f"🔓 Die Tür nach {richtung.capitalize()} ist jetzt offen.")
                    internal_note_to_llm(llm, promptgen, state, f"Die Tür nach {richtung.capitalize()} wurde aufgeschlossen.")
                return f"Erfolg: Die Tür nach {richtung.capitalize()} ist jetzt offen."
            else:
                return f"Fehler: Die Tür nach {richtung.capitalize()} ist bereits offen oder existiert nicht."
        else:
            return "Fehler: Dieses Objekt kann nicht auf diese Weise verwendet werden."
    elif gegenstand2:
        return "Fehler: Unvollständige Aktion. Was willst du womit verwenden?"
    else:
        if matched_obj1_key == "zahlenschloss":
            return "Hinweis: Das Zahlenschloss erwartet eine vierstellige Kombination. Bitte gib den Code ein, z.B. 'anwenden(\"8513\", \"zahlenschloss\")'."
        return "Fehler: Einzelne Anwendung dieses Gegenstands nicht möglich."

def umsehen() -> str:
    location = state.get("location")
    if not location or location not in rooms:
        return "Fehler: Unbekannter Raum."

    room = rooms[location]
    beschreibung = room.get("beschreibung", "").strip()
    gegenstaende = room.get("gegenstaende", [])
    wege = room.get("wege", {})

    text = beschreibung + "\n\n"

    if gegenstaende:
        text += "🧸 Du siehst folgende Gegenstände:\n" + "\n".join([f"- {items[obj].name}" for obj in gegenstaende if obj in items]) + "\n"

    if wege:
        text += "🚪 Ausgänge:\n"
        for richtung, daten in wege.items():
            status = "verschlossen" if daten.get("verschlossen", False) else "offen"
            text += f"- {richtung.capitalize()}: {status} ({daten.get('beschreibung', '').strip()})\n"

    return text.strip()

# --- SysTest Klasse ---
#
# Hier gibt es Methoden, die verschiedene Aspekte des Spiels auf Funktion testen
#

class SysTest:
    def __init__(self):
        self.test_state = {
            "room_prompt": rooms["halle"],
            "inventory": state["inventory"],
            "available_actions": ["umsehen", "nimm", "gehe", "öffne"]
        }

    def test1(self, llm):
        promptgen = PromptGenerator(system_prompt=None)  # nutzt __init__-Standard
        user_input = input("🧍 Was tust du? ")
        is_related = promptgen.is_game_related(llm, user_input, self.test_state["room_prompt"])
        if not is_related:
            print("💡 Das scheint nichts mit dem Spiel zu tun zu haben.")
        else:
            full_prompt = promptgen.build_prompt(self.test_state, user_input)
            response = llm.invoke(full_prompt)
            print("📜", response.content.strip())

    def test2(self):
        promptgen = PromptGenerator(system_prompt=None)
        test_state = {
            "room_prompt": rooms["halle"]["room_prompt"],
            "inventory": state["inventory"],
            "available_actions": ["umsehen", "nimm", "gehe", "öffne"],
            "location": "halle"
        }
        user_input = "Ich schaue mich um."
        prompt = promptgen.build_prompt(test_state, user_input)
        print("🔍 Test2 Prompt:\n", prompt)

    def test3(self):
        promptgen = PromptGenerator(system_prompt=None)
        test_state = {
            "room_prompt": rooms["halle"]["room_prompt"],
            "inventory": state["inventory"],
            "location": "halle"
        }
        user_input = "Ich gehe nach Norden"
        tool_call = 'gehe("norden")'
        system_response = "Geht nicht - Tür verschlossen"
        prompt = promptgen.build_prompt_for_llm_answer(test_state, user_input, tool_call, system_response)
        print("🛠️ Test3 Prompt mit Rückmeldung:\n", prompt)

    def test4(self):
        promptgen = PromptGenerator(system_prompt=None)
        test_state = {
            "room_prompt": rooms["halle"]["room_prompt"],
            "inventory": state["inventory"],
            "available_actions": ["nimm", "gehe"],
            "location": "halle"
        }
        user_input = "Ich nehme das Kissen und gehe durch die Tür im Westen."
        allowed_calls = ['nimm("Kissen")', 'gehe("westen")']
        prompt = promptgen.build_prompt(test_state, user_input, allowed_tool_calls=allowed_calls)
        print("🧪 Test4 Prompt mit erlaubten Tool-Calls (Raum: Halle):\n", prompt)

    def test5(self):
        print("📦 Test5: Objekt von Raum ins Inventar verschieben")
        inv = get_inventory(state)
        objs = get_objects(state)
        print("Inventar vorher:",inv )
        print("Objekte im Raum vorher:", objs)

        # Beispiel: Nimm 'Kissen' aus Raum und lege es ins Inventar
        objekt = "Kissen"
        if objekt in objs:
            rem_object(state, objekt)
            add_inventory(state, objekt)
            print(f"✔ '{objekt}' wurde ins Inventar verschoben.")
        else:
            print(f"❌ '{objekt}' ist nicht im Raum vorhanden.")

        print("Inventar nachher:", get_inventory(state))
        print("Objekte im Raum nachher:", get_objects(state))

    def test6(self):
        # Anzeige der Wege im aktuellen Raum
        location = state.get("location", "")
        if not location or location not in rooms:
            print("Fehler: Unbekannter Standort.")
            return
        room = rooms[location]
        print("Wege:", ", ".join([
            f"{richtung} ({'verschlossen' if daten['verschlossen'] else 'offen'})"
            for richtung, daten in room.get("wege", {}).items()
        ]))

    def test6(self):
        print("🎮 Starte Adventure-Simulator (manuell ohne LLM)")
        while True:
            # Aktueller Raumstatus anzeigen
            location = state.get("location")
            room = rooms.get(location)
            if not room:
                print("❌ Ungültiger Raum.")
                break

            print("\n📍 Du bist in:", room.get("name", "Unbekannter Raum"))
            print(room.get("beschreibung", "").strip())

            # Gegenstände anzeigen
            gegenstaende = room.get("gegenstaende", [])
            if gegenstaende:
                print("\n🧸 Gegenstände hier:")
                for obj_key in gegenstaende:
                    item = items.get(obj_key)
                    if item:
                        if isinstance(item, Door):
                            locked_str = "locked" if item.locked else "unlocked"
                            print(f"- 🚪 {item.name} (Tür, {locked_str}: {item.locked}, Ziel: {item.target_room})")
                        else:
                            print(f"- 📦 {item.name} (fixed: {item.fixed})")
                    else:
                        print(f"- ❓ Unbekanntes Objekt: {obj_key}")
            else:
                print("\n🧸 Keine Gegenstände hier.")

            # Wege anzeigen
            wege = room.get("wege", {})
            if wege:
                print("\n🚪 Wege:")
                for richtung, daten in wege.items():
                    status = "verschlossen" if daten.get("verschlossen", False) else "offen"
                    zielraum = daten.get("raum", "unbekannt")
                    print(f" - {richtung.capitalize()}: {status} ➔ {zielraum}")
            else:
                print("\n🚪 Keine Ausgänge.")

            # Eingabe
            user_input = input("\n🧍 Was tust du? (Befehl Argument(e)) ➔ ").strip()
            if not user_input:
                continue
            parts = user_input.split()
            command = parts[0].lower()
            args = parts[1:]

            if command == "gehe" and len(args) == 1:
                print(gehe(args[0]))
            elif command == "nimm" and len(args) == 1:
                print(nimm(args[0]))
            elif command == "untersuche" and len(args) == 1:
                print(untersuche(args[0]))
            elif command == "anwenden" and (len(args) == 1 or len(args) == 2):
                if len(args) == 1:
                    print(anwenden(args[0]))
                else:
                    print(anwenden(args[0], args[1]))
            elif command == "umsehen" and len(args) == 0:
                print(umsehen())
            elif command == "inventory" and len(args) == 0:
                print(inventory())
            elif command in ["ende", "quit", "exit"]:
                print("🏁 Spiel beendet.")
                break
            else:
                print("❓ Unbekannter Befehl oder falsche Argumente.")

    def test7(self):
        print("🧪 Test7: Anwenden des Zahlenschlosses allein")

        # Setze Test-Umgebung: Spieler befindet sich im 'finalraum' und hat nichts im Inventar
        state["location"] = "finalraum"

        # Teste, ob anwenden("zahlenschloss") die richtige Hinweis-Meldung ausgibt
        result = anwenden("zahlenschloss")
        print(f"Ergebnis:\n{result}")

    def test8(self):
        print("🧪 Test8: Anwenden von Code '8513' auf das Zahlenschloss")

        # Setze Test-Umgebung: Spieler befindet sich im 'finalraum' und Zahlenschloss existiert
        state["location"] = "finalraum"

        # Teste, ob anwenden("8513", "zahlenschloss") die Tür öffnet
        result = anwenden("8513", "zahlenschloss")
        print(f"Ergebnis:\n{result}")

        # Überprüfe danach, ob der Weg nach Westen jetzt offen ist
        wege = rooms["finalraum"].get("wege", {})
        if wege.get("westen", {}).get("verschlossen") == False:
            print("✅ Tür im Westen erfolgreich geöffnet!")
        else:
            print("❌ Tür im Westen ist noch verschlossen.")

def validate_game_data():
    print("🔍 Validierung der Spielwelt-Strukturen...")
    valid = True

    # Prüfe Gegenstände in Räumen
    for room_id, room in rooms.items():
        for obj in room.get("gegenstaende", []):
            if obj not in items:
                print(f"⚠️  Raum '{room_id}' verweist auf nicht vorhandenen Gegenstand: '{obj}'")
                valid = False

        for richtung, weginfo in room.get("wege", {}).items():
            zielraum = weginfo.get("raum")
            if zielraum not in rooms:
                print(f"⚠️  Raum '{room_id}' hat einen Ausgang nach '{richtung}', aber der Zielraum '{zielraum}' existiert nicht.")
                valid = False

    if valid:
        print("✅ Alle Verweise auf Räume und Gegenstände sind gültig.")
    else:
        print("❌ Es wurden Inkonsistenzen gefunden.")

# --- Hilfsfunktion zum Extrahieren von JSON aus LLM-Antworten ---
def extract_json_from_response(response_text: str) -> str:
    """
    Entfernt ```json und ``` von der LLM-Antwort und liefert reinen JSON-Text zurück.
    """
    if "```json" in response_text:
        response_text = response_text.split("```json",1)[1]
    if "```" in response_text:
        response_text = response_text.split("```",1)[0]
    return response_text.strip()

# --- LLM Game Loop ---
def llm_game_loop(llm, promptgen):
    print("🏰 Starte LLM Adventure Engine")

    while True:
        user_input = input("\n🧍 Was tust du? ➔ ").strip()
        if not user_input:
            continue

        # LOGGING: Schreibe User Input in Logfile
        log_entries = []
        log_entries.append("--- Neue Eingabe ---")
        log_entries.append(f"User Input: {user_input}")

        # Schritt (3): Prompt für User Input bauen (keine Prüfung mehr, jede Eingabe wird verarbeitet)
        prompt = promptgen.build_prompt(state, user_input, allowed_tool_calls=ALLOWED_TOOL_CALLS)
        response = llm.invoke(prompt)

        # Schritt (4): LLM Antwort aufteilen (neu: JSON parsen) mit robuster Fehlerbehandlung
        full_response = response.content.strip()
        json_parse_error = False
        initial_story_text = ""
        tool_calls = []
        try:
            cleaned_response = extract_json_from_response(full_response)
            parsed = json.loads(cleaned_response)
            initial_story_text = parsed.get("story", "").strip()
            tool_calls = parsed.get("tool_calls", [])
        except Exception as e:
            json_parse_error = True
            # print("⚠️ Die Antwort des Sprachmodells konnte nicht verstanden werden (kein gültiges JSON). Bitte versuche es erneut!")
            # print(f"Fehler beim Parsen: {e}")
            with open("game_json_errors_log.txt", "a", encoding="utf-8") as errlog:
                errlog.write("--- JSON Parse Error ---\n")
                errlog.write(f"User Input: {user_input}\n")
                errlog.write(f"Fehler: {e}\n")
                errlog.write(f"LLM-Response:\n{full_response}\n")
                errlog.write("------------------------\n")
            log_entries.append(f"⚠️ JSON-Parsing-Fehler: {e}")
            log_entries.append(f"Unparseable LLM-Response: {full_response}")
            initial_story_text = full_response
            tool_calls = []

        log_entries.append(f"Tool-Calls: {tool_calls if tool_calls else '[]'}")

        # Neue Logik: Tool-Calls sammeln und eine Sammel-Story generieren
        successful_tool_calls = []
        system_feedbacks = []
        if tool_calls and isinstance(tool_calls, list):
            for call in tool_calls:
                log_entries.append(f"Tool-Call: {call}")
                tool_result = execute_tool_call(call)
                log_entries.append(f"System-Feedback: {tool_result}")
                if tool_result and not str(tool_result).startswith("Fehler"):
                    successful_tool_calls.append(call)
                    system_feedbacks.append(tool_result)

        # Log abschließen
        if successful_tool_calls:
            log_entries.append(f"Sammel-Tool-Calls: {successful_tool_calls}")
            log_entries.append(f"Sammel-System-Feedbacks: {system_feedbacks}")
        else:
            log_entries.append(f"Initial Story: {initial_story_text}")

        log_entries.append("---------------------")
        with open("game_tool_calls_log.txt", "a", encoding="utf-8") as logf:
            logf.write("\n".join(log_entries) + "\n")

        # Ausgabe: Nur eine Sammel-Story, falls Tool-Calls erfolgreich
        if successful_tool_calls:
            try:
                multi_prompt = promptgen.build_prompt_for_multiple_tool_calls(state, user_input, successful_tool_calls, system_feedbacks)
                multi_response = llm.invoke(multi_prompt)
                multi_story = multi_response.content.strip()
                try:
                    story_cleaned = extract_json_from_response(multi_story)
                    parsed_story = json.loads(story_cleaned)
                    story_text = parsed_story.get("story", "").strip()
                    if story_text:
                        print(f"📜 {story_text}")
                        # Markdown(story_text)
                    else:
                        print(f"📜 {multi_story.strip()}")
                        # Markdown(multi_story.strip())
                except Exception:
                    print(f"📜 {multi_story.strip()}")
                    # Markdown(multi_story.strip())
            except Exception as e:
                # print(f"⚠️ Fehler bei Zusammenfassung der Aktionen: {e}")
                pass
        elif initial_story_text:
            try:
                story_cleaned = extract_json_from_response(initial_story_text)
                parsed_story = json.loads(story_cleaned)
                story_text = parsed_story.get("story", "").strip()
                if story_text:
                    print(f"📜 {story_text}")
                    # Markdown(story_text)
            except Exception:
                print(f"📜 {initial_story_text.strip()}")
                # Markdown(initial_story_text.strip())

        # Endbedingung prüfen
        if state.get("location") == "ende":
            # print("🎉 Glückwunsch! Du hast das Spiel beendet!")
            print("🎉 Glückwunsch! Du hast das Spiel beendet!")
            break

if __name__ == "__main__":
    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key="AIzaSyBAD9VSVcw47HSj6I63qSGpY4vuuu7WXTA")
    promptgen = PromptGenerator(system_prompt=None)
    validate_game_data()

    test = SysTest()

    # print("\n📋 Starte Tests zur Promptgenerierung...")
    # test.test1(llm)
    # test.test2()
    # test.test3()
    # test.test4()

    # print("\n📋 Starte Tests zur Spielwelt-Interaktion...")
    # test.test5()
    # test.test7()
    # test.test8()

    # Hinweis: Test6 ist der manuelle Adventure-Simulator – kann optional gestartet werden
    # test.test6()

    # print("\n✅ Tests abgeschlossen. Starte Spiel!")

    llm_game_loop(llm, promptgen)
