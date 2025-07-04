
import google.generativeai as genai
import os
import json # Für strukturierte Prompts/Antworten/Funktionsaufrufe
from pprint import pprint
from Utils import dprint


# Konfiguration der Gemini API mit deinem API-Schlüssel
# Es wird dringend empfohlen, den API-Schlüssel nicht direkt im Code zu speichern!
# Besser: Als Umgebungsvariable setzen (z.B. GEMINI_API_KEY)
# genai.configure(api_key="DEIN_API_KEY_HIER_ODER_AUS_UMGEBUNGSVARIABLE")
# Alternativ:

class GeminiInterface:
    def  __init__(self):
        apikey = os.environ.get("GOOGLE_API_KEY",None)
        while apikey == None:
            apikey = input("Google API Key: ")

        genai.configure(api_key=apikey)
        #


# Globale Model-Instanzen, die wir wiederverwenden können
# Wir könnten verschiedene Modelle für verschiedene Aufgaben nutzen, z.B. Flash für schnelle Parser, Pro für Reasoning
        self.gemini_text_model = genai.GenerativeModel('gemini-1.5-flash') # Gut für schnelle Textgenerierung/Parsing
        self.gemini_reasoning_model = genai.GenerativeModel('gemini-1.5-pro') # Gut für komplexes Reasoning des NPC
        self.txt_prev_description = {}
        self.tokens = 0
        self.numcalls = 0
        self.token_details = []


    def gen_narration_prompt(self, gs:"GameState", pl:"PlayerState") -> str:
        from typing import cast
        if pl.location.place_prompt_f:
            pl_loc_prompt = pl.location.place_prompt_f(gs,pl)
        else:
            pl_loc_prompt = pl.location.place_prompt

        r = f"""
Du bist der Erzähler in einem Adventure-Spiel. Deine Aufgabe ist es, die folgenden Informationen
zu einem Stimmungsvollen Text zusammenzufassen. Halte Dich dabei strikt an die Vorgaben und erfinde
keine neuen Orte, Gegenstände, Akteure oder sonstige Dinge. Deine Zusammenfassung sollte 500 Zeichen
nicht überschreiten.
    
+---------------------+
+ Generelles Szenario +
+---------------------+
Sofern der Spieler sich an den Orten start, warenautomat, geldautomat, dach oder felsen befindet,
gilt folgendes generelles Szenario
- Wüste
- Greller Sonnenschein
- extrem heiss

An anderen Orten wird das Szenario in der Ortsbeschreibung beschrieben. In diesem Fall 
verwende das dort angegebene Szenario


+-------------------------------------+  
+ Ort des Spielers oder der Spielerin +
+-------------------------------------+
- {pl.name} (Spieler/Spielerin) befindet sich am Ort "{pl.location.callnames[0]}"

Die Ortsbeschreibung:
=====================

{pl_loc_prompt}

+-----------------------+
+ Objekte an diesem Ort +
+-----------------------+
        """
        for obj in pl.location.place_objects:
            if not obj.hidden:
                r = r+obj.prompt_f(gs,pl)
        r=r+"""
+----------------------------+        
+ Wege, die hier existrieren +
+----------------------------+
"""
        for w in pl.location.ways:
            if w.visible:
                r = r+f"- {w.destination.callnames[0]}"
                f = w.obstruction_check(gs)
                if f != "Free":
                    r=r+f" (Spezielle Information NUR FÜR DIESEN WEG: {f})"
                r = r+"\n"

        dog = None
        from NPCPlayerState import NPCPlayerState
        for d in gs.players:
            if type(d) is NPCPlayerState:
                dog = d
                break
        if dog:
            r = r + "\n" + dog.dog_prompt(gs,pl)
        if self.txt_prev_description.get(pl.location.name,None):

            r = r + f"""
 +----------------------------------+           
 + Vorherige Beschreibung des Ortes +
 +----------------------------------+
 
 Der Ort des Geschehens ({pl.location.callnames[0]}) ist schon beschrieben worden. 
 Generiere die Beschreibung der Situation ausschließlich aus den oben angegebenen
 Informationen, und greife auf die vorherige Beschreibung nur zurück, um Konsistenz
 zu wahren, was die Stimmung und die generelle Szenerie betrifft. Keinesfalls darfst
 Du Gegenstände, Objekte, Wege und Beschreibungen des Hundes aus der vorherigen
 Beschreibung übernehmen, denn dies kann sich im Spielverlauf geändert haben. Diese
 Informationen dürfen ausschließlich nur aus den obigen Angaben genommen werden. Die
 
 Vorherige Beschreibung
 ======================
 {self.txt_prev_description[pl.location.name]}            
            """
        return r

    def clean_truncated_sentence(self, text: str) -> str:
        """
        Bereinigt einen möglicherweise durch das Token-Limit abgeschnittenen Text.
        Sucht nach dem letzten vollständigen Satzende. Findet sich keins,
        wird der Text am letzten Leerzeichen abgeschnitten und Ellipsen hinzugefügt.

        Args:
            text (str): Der vom LLM generierte Text.

        Returns:
            str: Der bereinigte Text, der mit einem Satzende oder Ellipsen schließt.
        """
        # Muster, das ein Satzendezeichen (Punkt, Fragezeichen, Ausrufezeichen)
        # gefolgt von optionalen Leerzeichen, Anführungszeichen oder Zeilenumbrüchen am Ende des Strings findet.
        # [\p{P}] ist eine Unicode-Eigenschaft für Satzzeichen, um internationaler zu sein.
        # Alternativ: r'[.?!][\s"\'»“‘]*$' für einfache ASCII-Satzzeichen.
        import regex as re
        sentence_end_pattern = r'[\p{P}][\s"\'»“‘\r\n]*$'

        # Finde das letzte Vorkommen eines Satzendzeichens, das sich am Ende des Strings befindet
        match = re.search(sentence_end_pattern, text)

        if match:
            # Wenn ein Satzendezeichen gefunden wurde, schneide den Text dort ab.
            # match.end() gibt das Ende des gefundenen Musters zurück.
            cleaned_text = text[:match.end()].strip()
            return cleaned_text
        else:
            # Wenn kein vollständiger Satz gefunden (d.h. der Text mitten im Satz abbricht),
            # schneide am letzten Leerzeichen ab, um keine Wörter zu zerhacken.
            last_space_index = text.rfind(' ')
            if last_space_index != -1:
                return text[:last_space_index].strip() + "..."  # Füge Ellipsen hinzu
            else:
                # Wenn der Text sehr kurz ist und kein Leerzeichen enthält (z.B. nur ein Wort oder Fragment)
                return text.strip() + "..."  # Füge Ellipsen direkt an

    def narrate(self, gs:"GameState", pl:"PlayerState") -> str:
        prompt = self.gen_narration_prompt(gs,pl)
        try:
            response = self.gemini_text_model.generate_content(prompt,
                                                               generation_config = genai.types.GenerationConfig(
                                                                       max_output_tokens=200  # Beispiel: Maximal 200 Tokens für Szenenbeschreibungen
                                                                                                                )
                                                               )

            self.tokens = self.tokens + response.usage_metadata.total_token_count
            self.numcalls = self.numcalls + 1
            self.token_details.append(response.usage_metadata.total_token_count)
            r = self.clean_truncated_sentence(response.text)
            self.txt_prev_description[pl.location.name] = r
            return r
        except Exception as e:
            # Wenn die LLM-Interaktion nicht funktioniert hat, gebe den Prompt zurück
            print("Exception!!")
            pprint(e) #
            return prompt


#     def generate_scene_description(self,scene_elements: dict) -> str:
#         """
#         Generiert eine flüssige und immersive Szenenbeschreibung basierend auf Stichpunkten.
#
#         Args:
#             scene_elements: Ein Dictionary mit Stichpunkten zur Szene (Ort, Objekte, Stimmung etc.).
#                             Beispiel: {"Ort": "Wueste", "Zustand": "verfallen", "Objekte": ["Fahrrad", "Umschlag"], "Atmosphäre": "einsam"}
#
#         Returns:
#             Eine detaillierte und stimmungsvolle Textbeschreibung der Szene.
#         """
#         if len(self.txt_prev_descriptions) > 3000:
#             sum_prompt = f"""Fasse den Spielablauf, der gleich folgt, in einem Text von etwa 500 Zeichen zusammen. Fokussiere
#             dich auf wesentliche Elemente der Szenerie:
#
#             * Ortsbeschreibungen
#             * Wegbeschreibungen
#             * Umgebungsbeschreibungen
#
#             Keinesfalls, unter keinen Umständen, sollen die Gegenstände, die der Spieler bei sich trägt, Beschreibungen von Gegenständen,
#             oder Beschreibungen von anderen Spielern, wie etwa Hunden, in der Zusammenfassung vorkommen.
#
#             Anhand der Zusammenfassung soll ein Erzähler in der Lage sein, die beschriebenen Objekte, Orte, Wege und Umgebungen
#             zu rekonstruieren und selber so darüber zu erzählen, dass sie konsistent wiedererkannt werden können. Halte dich an Fakten
#             und erfinde keine neuen Orte, Objekte, Wege, Umgebungen oder Spielfiguren.
#
#             Deine Beschreibung sollte prägnant sein und idealerweise mit einem abgeschlossenen Satz oder einem passenden Satzfragment enden,
#             falls das Token-Limit erreicht wird. Vermeide das Abschneiden mitten im Wort oder Satz.
#
#             --------------
#
#             {self.txt_prev_descriptions}
# """
#             try:
#                 dprint(f"{'#'*80}")
#                 dprint("Creating Summary".center(80))
#                 dprint(f"{'#' * 80}")
#                 dprint(self.txt_prev_descriptions)
#                 response = self.gemini_text_model.generate_content(sum_prompt#,
#                                                                    #generation_config = genai.types.GenerationConfig(
#                                                                    #         max_output_tokens=200  # Beispiel: Maximal 200 Tokens für Szenenbeschreibungen
#                                                                    #                                                 )
#                                                                    )
#                 self.txt_prev_descriptions = response.text
#                 self.tokens = self.tokens+response.usage_metadata.total_token_count
#                 self.numcalls = self.numcalls+1
#                 self.token_details.append(response.usage_metadata.total_token_count)
#                 dprint(f"{'#' * 80}")
#                 dprint(self.txt_prev_descriptions)
#                 dprint(f"{'#' * 80}")
#             except Exception as e:
#                 print(f"Fehler bei der Generierung der Zusammenfassung: {e}")
#
#
#         prompt = f"""
# Generiere eine detaillierte und atmosphärische Szenenbeschreibung für ein Text-Adventure basierend auf den folgenden Elementen.
# Der Text sollte immersiv und gut lesbar sein. Vermeide es, die Elemente als Liste aufzuzählen, sondern webe sie in eine flüssige
# Beschreibung ein.
#
# Achte unbedingt darauf, dass bei der Szenenbeschreibung keine Wiedersprüche zu dem entstehen, was vorher schon beschrieben
# wurde. Insbesondere dürfen Beschreibungen von Orten, Dingen, Wegen und Himmelsrichtungen inhaltlich nicht von einer vorherigen
# Beschreibung abweichen, ausser, wenn es in der weiter unten gegebenen Beschreibung explizit abweicht. Dies ist aber nur der Fall,
# wenn sich im Verlauf des Spiels etwas ändert, wenn also etwa Gegenstand umkippt oder verschwindet.
#
# Konzentriere dich bei der Erstellung der Beschreibung auf diese Szenen-Elemente:
# {json.dumps(scene_elements, indent=2)}
#
# Greife auf die vorherige Beschreibungen nur zurück, um die neue Beschreibung konsistent zu früheren Beschreibungen zu halten. Verwende
# die vorherige Beschreibung aber ausschließlich dazu und füge sonst nichts in aktuelle Beschreibung ein.
#
# ====== Vorherige Beschreibungen: ======
#
# {self.txt_prev_descriptions}
#
# ====== Ende der vorherigen Beschreibungen ======
#
# Deine Beschreibung sollte prägnant sein und idealerweise mit einem abgeschlossenen Satz oder einem passenden Satzfragment enden,
# falls das Token-Limit erreicht wird. Vermeide das Abschneiden mitten im Wort oder Satz.
#
# Szenenbeschreibung:
#         """
#         try:
#             response = self.gemini_text_model.generate_content(prompt#,
#                                     #generation_config = genai.types.GenerationConfig(
#                                     #    max_output_tokens=200  # Beispiel: Maximal 200 Tokens für Szenenbeschreibungen
#                                     #)
#             )
#             #
#             # Generate a crisp description of the place and environment only
#             #
#             loc_only_prompt=f"""
# Fasse aus folgendem Text nur die Beschreibung des Ortes, der Stimmung und der Umgebung zusammen. Lasse alles andere weg,
# insbesondere Beschreibungen von Objekten, Tieren und Handlungen! Fasse dich kurz und prägnant, und fokussiere dich auf
# wichtige Details.
#
# Text:
# {response.text}
#
# Zusammenfassung:
#             """
#             summary = self.gemini_text_model.generate_content(loc_only_prompt)
#
#             self.txt_prev_descriptions = self.txt_prev_descriptions + "\n" + f"Ort: {next(iter(scene_elements["Aktueller Ort"]["Ortsname"]))}\n{summary.text}" + "\n"+f'{"-"*80}'+"\n"
#             self.tokens = self.tokens + summary.usage_metadata.total_token_count
#             self.numcalls = self.numcalls + 1
#             self.token_details.append(summary.usage_metadata.total_token_count)
#
#             self.tokens = self.tokens + response.usage_metadata.total_token_count
#             self.numcalls = self.numcalls + 1
#             self.token_details.append(response.usage_metadata.total_token_count)
#             return response.text
#         except Exception as e:
#             print(f"Fehler bei der Generierung der Szenenbeschreibung: {e}")
#             return "Eine merkwürdige und unerklärliche Szene." # Fallback-Text



    def parse_user_input_to_commands(self,user_input: str, current_game_context: dict) -> list[str]:
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
Jeder Befehl muss das Format 'befehl_name objekt' oder 'befehl_name objekt ziel_objekt' haben.


Folgende Befehle stehen zur Verfügung und so sind sie zu interpretieren:
- 'gehe <ort>': Wenn der Spieler einen Ort betreten oder verlassen möchte. 'gehe' darf nur genau ein Argument haben, nämlich das Ziel
- 'anwenden <objekt>': Wenn der Spieler ein Objekt allein oder eine Aktion am Objekt ausführen möchte (z.B. Hebel umlegen, Zünder drücken).
- 'anwenden <objekt1> <objekt2>': Wenn der Spieler Objekt1 auf Objekt2 anwenden möchte (z.B. Schlüssel an Tür, Salami an Hund).
- 'nimm <objekt>': Wenn der Spieler ein Objekt aufnehmen möchte.
- 'ablegen <objekt>': Wenn der Spieler ein Objekt ablegen möchte.
- 'untersuche <objekt>': Wenn der Spieler ein Objekt oder die Umgebung näher betrachten möchte.
- 'umsehen': Wenn der Spieler sich im aktuellen Ort umsehen möchte.
- 'hilfe': Wenn der Spieler Hilfe benötigt.

Beispiele für komplexere Interpretationen des 'anwenden'-Befehls:
- "Öffne die Tür mit dem Schlüssel" ODER "Schließe die Tür mit dem Schlüssel auf": 'anwenden o_schluessel o_tuer' (wenn o_tuer der Name der Tür ist)
- "Wirf den Schlüssel auf die Tür": 'anwenden schluessel tuer' (auch wenn es "werfen" ist, wird es als "anwenden" interpretiert)
- "Drücke den Knopf der Sprengladung": 'anwenden sprengladung'
- "Stelle den Hebel um": 'anwenden hebel'
- "Füttere den Hund mit der Salami": 'anwenden salami hund' (wenn hund der Name des Hundes ist)

Falls die Eingabe sich auf mehr als eine Aktion bezieht, teile sie in separate atomare Befehle auf, wobei jeder Befehl
ein String der Form "befehl" oder "befehl objekt" oder "befehl objekt1 objekt2" ist. 

Beispiel:
korrekt: ['anwenden schluessel schuppen']
falsch: ['anwenden', 'schluessel', 'schuppen']

Beispiel für eine komplexere Eingabe:

"gehe zum Schuppen und schließe ihn mit dem Schlüssel auf, dann sieh dich um" wird zu:
['gehe schuppen', 'anwenden schluessel schuppen', 'umsehen']

Falls ein Befehl nicht verstanden wird, gib '[ "unbekannt" ]' zurück.
    
Verfügbare Orte und Objekte (mit ihren IDs) im aktuellen Kontext:
{json.dumps(current_game_context, indent=2)}

Spielereingabe: "{user_input}"

Gib nur das JSON-Array der Befehle aus, ohne zusätzlichen Text.
        """
        try:
            response = self.gemini_text_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            commands = json.loads(response.text)

            if not isinstance(commands, list):
                return ["unbekannt"]
            return commands
        except Exception as e:
            print(f"Fehler beim Parsen der Benutzereingabe: {e}")
            return ["unbekannt"] # Fallback

    def get_npc_action(self, game_state_for_npc: dict) -> dict:
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
            response = self.gemini_reasoning_model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            action = json.loads(response.text)
            if not isinstance(action, dict) or "strategy" not in action or "commands" not in action:
                return {"strategy": "Ich bin verwirrt und tue nichts.", "commands": ["nichts"]}
            return action
        except Exception as e:
            print(f"Fehler bei der Generierung der NPC-Aktion: {e}")
            return {"strategy": "Ich bin verwirrt und tue nichts.", "commands": ["nichts"]} # Fallback