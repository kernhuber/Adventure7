from Adventure6 import log_error, rooms, items
from Door import Door


#
# Everything with regards to interactin with the LLM goes
#

def internal_note_to_llm(llm, promptgen, state, note_text: str):
    note_prompt = f"""[INTERNAL SYSTEM UPDATE]
Folgende neue Information muss in den Spielkontext übernommen werden:
{note_text}
(Keine Tool-Calls erzeugen. Einfach im Gedächtnis behalten.)"""
    try:
        _ = llm.invoke(promptgen.build_prompt(state, note_prompt))
    except Exception as e:
        log_error(f"Fehler bei interner LLM-Notiz: {e}")


def system_message_to_player(message: str):
    print(f"📢 {message}")


class PromptGenerator:
    def build_prompt_for_multiple_tool_calls(self, state, user_input, tool_calls, system_feedbacks):
        """
        Baut einen Prompt für das LLM, der mehrere Tool-Calls und deren Systemrückmeldungen zusammenfasst.
        """
        room_prompt = state.get("place_prompt", "")
        inventory = state.get("inventory", [])
        location = state.get("location", "")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("ways", {}) if location else {}

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
        room_prompt = state.get("place_prompt", "")
        inventory = state.get("inventory", [])
        actions = state.get("available_actions", [])
        location = state.get("location", "")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("ways", {}) if location else {}

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
        room_prompt = state.get("place_prompt", "")
        inventory = state.get("inventory", [])
        location = state.get("location","")
        rin = rooms[location].get("gegenstaende", []) if location else []
        wege = rooms[location].get("ways", {}) if location else {}

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
