import google.generativeai as genai
import os
import json # Für strukturierte Prompts/Antworten/Funktionsaufrufe

# Konfiguration der Gemini API mit deinem API-Schlüssel
# Es wird dringend empfohlen, den API-Schlüssel nicht direkt im Code zu speichern!
# Besser: Als Umgebungsvariable setzen (z.B. GEMINI_API_KEY)
# genai.configure(api_key="DEIN_API_KEY_HIER_ODER_AUS_UMGEBUNGSVARIABLE")
# Alternativ:

apikey = os.environ.get("GOOGLE_API_KEY",None)
while apikey == None:
    apikey = input("Google API Key: ")

genai.configure(api_key=apikey)


# Globale Model-Instanzen, die wir wiederverwenden können
# Wir könnten verschiedene Modelle für verschiedene Aufgaben nutzen, z.B. Flash für schnelle Parser, Pro für Reasoning
gemini_text_model = genai.GenerativeModel('gemini-1.5-flash') # Gut für schnelle Textgenerierung/Parsing
gemini_reasoning_model = genai.GenerativeModel('gemini-1.5-pro') # Gut für komplexes Reasoning des NPC

def generate_scene_description(scene_elements: dict) -> str:
    """
    Generiert eine flüssige und immersive Szenenbeschreibung basierend auf Stichpunkten.

    Args:
        scene_elements: Ein Dictionary mit Stichpunkten zur Szene (Ort, Objekte, Stimmung etc.).
                        Beispiel: {"Ort": "Wueste", "Zustand": "verfallen", "Objekte": ["Fahrrad", "Umschlag"], "Atmosphäre": "einsam"}

    Returns:
        Eine detaillierte und stimmungsvolle Textbeschreibung der Szene.
    """
    prompt = f"""
    Generiere eine detaillierte und atmosphärische Szenenbeschreibung für ein Text-Adventure basierend auf den folgenden Elementen.
    Der Text sollte immersiv und gut lesbar sein. Vermeide es, die Elemente als Liste aufzuzählen, sondern webe sie in eine flüssige Beschreibung ein.

    Szenen-Elemente:
    {json.dumps(scene_elements, indent=2)}

    Szenenbeschreibung:
    """
    try:
        response = gemini_text_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Fehler bei der Generierung der Szenenbeschreibung: {e}")
        return "Eine merkwürdige und unerklärliche Szene." # Fallback-Text



def parse_user_input_to_commands(user_input: str, current_game_context: dict) -> list[str]:
    """
    Parst eine Benutzereingabe in eine Liste von atomaren Game-Engine-Befehlen.

    Args:
        user_input: Die vom Spieler eingegebene natürliche Sprache.
        current_game_context: Ein Dictionary mit relevanten Informationen über den Spielzustand,
                              insbesondere verfügbare Orte und Objekte mit ihren IDs.
                              Beispiel: {"current_location": "p_schuppen", "available_objects": {"Blumentopf": "o_blumentopf"}, "available_places": {"Schuppen": "p_schuppen"}}

    Returns:
        Eine Liste von Strings, wobei jeder String ein atomarer Befehl ist (z.B. ["gehe p_schuppen", "untersuche o_blumentopf"]).
        Gibt eine leere Liste zurück, wenn die Eingabe nicht verstanden wird.
    """
    prompt = f"""
    Wandle die folgende Spielereingabe in eine Liste atomarer Game-Engine-Befehle um.
    Die Befehle sollen in einem JSON-Array von Strings zurückgegeben werden.
    Jeder Befehl muss das Format 'befehl_name objekt_id' oder 'befehl_name objekt_id ziel_objekt_id' haben.
    Folgende Befehle stehen zur Verfügung:
    
    gehe <ort>
    anwenden <objekt>
    anwenden <objekt> <zielobjekt>
    nimm <objekt>
    ablegen <objekt>
    untersuche <objekt>
    umsehen
    hilfe
    
    Beispiele für Befehle: 'gehe Schuppen', 'untersuche Blumentopf', 'nimm Schluessel', 'anwenden Schluessel Schuppen'.

    Falls die Eingabe sich auf mehr als eine Aktion bezieht, teile sie in separate atomare Befehle auf.
    Falls ein Befehl nicht verstanden wird, gib '[ "unbekannt" ]' zurück.

    Verfügbare Orte und Objekte (mit ihren IDs) im aktuellen Kontext:
    {json.dumps(current_game_context, indent=2)}

    Spielereingabe: "{user_input}"

    Gib nur das JSON-Array der Befehle aus, ohne zusätzlichen Text.
    """
    try:
        response = gemini_text_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        commands = json.loads(response.text)
        if not isinstance(commands, list):
            return ["unbekannt"]
        return commands
    except Exception as e:
        print(f"Fehler beim Parsen der Benutzereingabe: {e}")
        return ["unbekannt"] # Fallback

def get_npc_action(game_state_for_npc: dict) -> dict:
    """
    Generiert eine strategische Aktion für den NPC (Hund) basierend auf dem Spielzustand.

    Args:
        game_state_for_npc: Ein Dictionary mit dem relevanten Spielzustand für den NPC,
                            z.B. Spielerposition, NPC-Position, relevante Objekte, Ziele etc.

    Returns:
        Ein Dictionary mit der Strategie und der Liste der atomaren Befehle des NPC.
        Beispiel: {"strategy": "Ich werde den Spieler verfolgen.", "commands": ["gehe p_player_location"]}
    """
    prompt = f"""
    Du bist ein Non-Player-Charakter (NPC), ein Hund, in einem Text-Adventure.
    Dein Hauptziel ist es, den Spieler daran zu hindern, sein Fahrrad zu reparieren und somit die Welt zu retten.
    Du bist listig, kannst den Spielzustand analysieren und deine Strategie dynamisch anpassen.

    Aktueller Spielzustand (JSON):
    {json.dumps(game_state_for_npc, indent=2)}

    Überlege dir eine prägnante Strategie (1-2 Sätze) für deine nächste Aktion und generiere dann
    eine Liste von atomaren Game-Engine-Befehlen, die deine Strategie umsetzen.
    Die Befehle sollen in einem JSON-Objekt mit den Schlüsseln "strategy" (String) und "commands" (Liste von Strings) zurückgegeben werden.

    Beispiel-Output:
    {{
        "strategy": "Ich werde die Salami fressen, um den Spieler abzulenken.",
        "commands": ["gehe o_salami_location", "nimm o_salami", "anwenden o_salami"]
    }}

    Gib nur das JSON-Objekt aus, ohne zusätzlichen Text.
    """
    try:
        response = gemini_reasoning_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        action = json.loads(response.text)
        if not isinstance(action, dict) or "strategy" not in action or "commands" not in action:
            return {"strategy": "Ich bin verwirrt und tue nichts.", "commands": ["nichts"]}
        return action
    except Exception as e:
        print(f"Fehler bei der Generierung der NPC-Aktion: {e}")
        return {"strategy": "Ich bin verwirrt und tue nichts.", "commands": ["nichts"]} # Fallback