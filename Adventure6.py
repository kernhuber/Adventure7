
import re
import json

from Door import Door
from GameObject import GameObject
from InteractLLM import internal_note_to_llm, system_message_to_player, PromptGenerator
from SysTest import SysTest


#
# Nächste Version des Adventures, 2025-04-22
#
# Siehe Koversation in ChatGPT/Projekt AI Training/Sprachmodell und Agentenarchitektur
#
#
# PromptGenerator-Klasse für Adventure5
#


#
# Diverse Prompts erzeugen
#


ALLOWED_TOOL_CALLS = ["gehe", "nimm", "untersuche", "anwenden", "umsehen", "inventory"]

# --- Spielwelt-Strukturen ---

rooms = {
    "halle": {
        "name": "Karger Raum",
        "description": """
        Du wachst in einem kargen Raum ohne Fenster auf. Der Raum hat Sandsteinmauern. Es liegen einige 
        Gegenstände im Raum herum. 
        """,
        "gegenstaende": ["Kissen", "Luftpumpe", "Schraubstock", "Schuhloeffel", "Schluessel", "Tuer_Norden", "Tuer_Westen"],
        "ways": {
            "norden": {
                "raum": "bibliothek",
                "verschlossen": True
            },
            "westen": {
                "raum": "durchgang",
                "verschlossen": False
            }
        },
        "place_prompt": """
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
        "description": "Eine staubige Bibliothek mit hohen Regalen voller Bücher.",
        "gegenstaende": ["buch"],
        "ways": {
            "sueden": {
                "raum": "halle",
                "verschlossen": False,
                "description": "Die Tür zur Halle steht offen."
            }
        },
        "place_prompt": "Hier riecht es nach altem Papier. Erwähne die Vielzahl an Büchern."
    },
    "durchgang": {
        "name": "Durchgang",
        "description": "Ein schmuckloser Durchgang. ",
        "ways": {
            "osten": {
                "raum": "halle",
                "verschlossen": False,
                "description": "Die Tür zurück zum Eingangsraum steht offen."
            },
            "westen": {
                "raum": "finalraum",
                "verschlossen": False,
                "description": "Die Tür zum nächsten raum steht offen."
            }
        },
        "place_prompt": "Es ist viel Staub hier. Man könnte hier mal wieder putzen. Ansonsten ist es rech langweilig hier"
    },
    "finalraum":{
        "name": "Letzter Raum",
        "description": "Dieser Raum ist eigentlich auch recht öde. Da hätten sie sich in diesem Game echt mal mehr ausdenken können!",
        "ways": {
            "osten": {
                "raum":"durchgang",
                "verschlossen": False,
                "description": "Hier geht es wieder in den Durchgang"
            },
            "westen": {
                "raum": "ende",
                "verschlossen": True,
                "description": 'Eine Stahltür, darüber ein Schild, auf dem "Exit" steht'
            }
        },
        "gegenstaende": ["zahlenschloss"],
        "place_prompt":"Der Raum ist aus Beton und völlig schmucklos. An der Wand hängt ein Zahlenschloss"
    },
    "ende": {
        "name": "wunderschöne Wiese",
        "description":
            """Eine wunderschöne Wiese mit Blumen. Die Sonne scheint. Die Luft duftet nach Sommer. Hinter Dir ein 
               Betonklotz mit der Stahltür, durch die du gekommen bist. Die Tür ist nun verschlossen. 
               Du hast das Spiel gewonnen.      
            """,
        "ways": {},
        "gegenstaende": [],
        "place_prompt": """
        Der Spieler hat das Spiel gewonnen. Beschreibe ihm den Raum (also die Wiese) mit blumigen Worten
        """
    }
}


# --- Klassen für Spielobjekte ---


# --- Neues Items-Dictionary basierend auf den Klassen ---

items = {
    "Laterne": GameObject(
        name="verbeulte Laterne",
        examine="Die Laterne ist verbeult, aber sieht noch funktionstüchtig aus."
    ),
    "Schluessel": GameObject(
        name="großer Schlüssel",
        examine="Ein großer Schlüssel aus Eisen. Könnte in ein Türschloss passen",
        # apply_fn =
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
                    wege = room.get("ways", {})
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

    wege = rooms[location].get("ways", {})
    weg = wege.get(richtung.lower())
    if not weg:
        return "Fehler: Weg existiert hier nicht."

    if weg["verschlossen"]:
        return "Fehler: Weg verschlossen."

    ziel = weg["raum"]
    state["location"] = ziel
    beschreibung = rooms[ziel].get("description", "Du wechselst den Raum.")
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
    wege = rooms[location].get("ways", {})

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
    beschreibung = room.get("description", "").strip()
    gegenstaende = room.get("gegenstaende", [])
    wege = room.get("ways", {})

    text = beschreibung + "\n\n"

    if gegenstaende:
        text += "🧸 Du siehst folgende Gegenstände:\n" + "\n".join([f"- {items[obj].name}" for obj in gegenstaende if obj in items]) + "\n"

    if wege:
        text += "🚪 Ausgänge:\n"
        for richtung, daten in wege.items():
            status = "verschlossen" if daten.get("verschlossen", False) else "offen"
            text += f"- {richtung.capitalize()}: {status} ({daten.get('description', '').strip()})\n"

    return text.strip()

# --- SysTest Klasse ---
#
# Hier gibt es Methoden, die verschiedene Aspekte des Spiels auf Funktion testen
#

def validate_game_data():
    print("🔍 Validierung der Spielwelt-Strukturen...")
    valid = True

    # Prüfe Gegenstände in Räumen
    for room_id, room in rooms.items():
        for obj in room.get("gegenstaende", []):
            if obj not in items:
                print(f"⚠️  Raum '{room_id}' verweist auf nicht vorhandenen Gegenstand: '{obj}'")
                valid = False

        for richtung, weginfo in room.get("ways", {}).items():
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
