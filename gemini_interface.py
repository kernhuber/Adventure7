from __future__ import annotations
from player_state import PlayerState
from game_state import GameState
# import google.generativeai as genai
from google import genai
import os
import time
import json # Für strukturierte Prompts/Antworten/Funktionsaufrufe
from pprint import pprint
from utils import dprint, dpprint, dl, ddiff
#from google.api_core import retry
#from google.api_core import exceptions as gexc
import os
from dotenv import load_dotenv
import traceback

# Konfiguration der Gemini API mit deinem API-Schlüssel
# Es wird dringend empfohlen, den API-Schlüssel nicht direkt im Code zu speichern!
# Besser: Als Umgebungsvariable setzen (z.B. GEMINI_API_KEY)
# genai.configure(api_key="DEIN_API_KEY_HIER_ODER_AUS_UMGEBUNGSVARIABLE")
# Alternativ:

class GeminiInterface:
    # --- LLM-generic alias (compatibility) ---
    def validate_llm_tools_schema(self, tools_list):
        return self.validate_gemini_tools_schema(tools_list)
    class _narration_cache:
        def __init__(self):
            self.cache = {}

        def update(self,room:str,prompt:str, narration:str):
            self.cache[room] = {"prompt":prompt,"narration":narration}

        def invalidate(self,room:str):
            if room in self.cache:
                del self.cache[room]

        def get(self, room:str, prompt:str):
            if room in self.cache:
                if prompt == self.cache[room]["prompt"]:
                    return self.cache[room]["narration"]
                else:
                    ddiff(dl.LLM,self.cache[room]["prompt"], prompt)
                    return None
            else:
                return None

    def  __init__(self):


        apikey = os.environ.get("GOOGLE_API_KEY",None)
        if not apikey:
            load_dotenv("apikey.env")
            apikey = os.getenv("GOOGLE_API_KEY")  # Ausgabe: bar


        #genai.configure(api_key=apikey)
        self.client = genai.Client(api_key=apikey)
        #
        # Retry-Mechanismus
        # Wiederholen bei typischen transienten Fehlern (429: ResourceExhausted, 503: ServiceUnavailable, 504: DeadlineExceeded)
        #is_retriable = lambda e: isinstance(e, (gexc.ResourceExhausted, gexc.ServiceUnavailable, gexc.DeadlineExceeded))
        #genai.GenerativeModel.generate_content = retry.Retry(
        #    predicate=is_retriable
        #)(genai.GenerativeModel.generate_content)




# Globale Model-Instanzen, die wir wiederverwenden können
# Wir könnten verschiedene Modelle für verschiedene Aufgaben nutzen, z.B. Flash für schnelle Parser, Pro für Reasoning
        self.gemini_text_model_id = 'gemini-2.5-flash-lite' # Gut für schnelle Textgenerierung/Parsing
        self.gemini_reasoning_model_id = 'gemini-2.5-flash' # Gut für komplexes Reasoning des NPC
        self.txt_prev_description = {}
        self.tokens = 0
        self.numcalls = 0
        self.token_details = []
        self.narration_cache = self._narration_cache()

    # --- Storable (Save/Load) --------------------------------------------------------
    # Die LLM ist ein lebendes Singleton: der Client/Config/Token-Stats werden NICHT
    # gespeichert (der Client bleibt live). Gesichert werden nur die beiden Caches, die
    # die exakten Szenenbeschreibungen tragen - sonst würde nach dem Laden neu (und damit
    # anders) generiert. GameState orchestriert save()/load() explizit (nicht @savable).
    STORE_TYPE = "GeminiInterface"

    def store_id(self) -> str:
        return "llm"

    def save(self) -> dict:
        return {
            "narration_cache": dict(self.narration_cache.cache),
            "txt_prev_description": dict(self.txt_prev_description),
        }

    def load(self, data, ctx=None) -> None:
        self.narration_cache.cache = dict(data.get("narration_cache", {}))
        self.txt_prev_description = dict(data.get("txt_prev_description", {}))

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

Rede den Spieler in der ersten Person an! 

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
                f = w.obstruction_check(gs)
                if f != "Free":
                    r=r+f" - {f})"
                else:
                    r=r+f"- {w.destination.callnames[0]}"
                r = r+"\n"

        dog = None
        from npc_dog_state import NPCDogState
        for d in gs.players:
            if type(d) is NPCDogState:
                dog = d
                break
        if dog:
            r = r + "\n" + dog.dog_prompt(gs,pl)

        zombie = None
        from npc_zombie_state import NPCZombieState
        for z in gs.players:
            if isinstance(z, NPCZombieState):
                zombie = z
                break
        if zombie:
            zp = zombie.zombie_prompt(gs, pl)
            if zp:
                r = r + "\n" + zp

        # NOTE: the "Vorherige Beschreibung" (previous narration) is intentionally NOT
        # part of this prompt. It is volatile — it is this method's own past output — so
        # including it would make every call's prompt unique and defeat the narration
        # cache (regenerating, and burning tokens, on every serialize). narrate() appends
        # it only for the actual generation (style continuity) while caching on this
        # stable base. See _prev_description_addendum().
        return r

    def _prev_description_addendum(self, pl) -> str:
        """Style-continuity hint appended to the prompt at generation time only.

        Never part of the narration cache key, since it changes on every generation.
        """
        prev = self.txt_prev_description.get(pl.location.name, None)
        if not prev:
            return ""
        return f"""
 +----------------------------------+
 + Vorherige Beschreibung des Ortes +
 +----------------------------------+

 Der Ort des Geschehens ({pl.location.callnames[0]}) ist schon beschrieben worden.
 Generiere die Beschreibung der Situation ausschließlich aus den oben angegebenen
 Informationen, und greife auf die vorherige Beschreibung nur zurück, um Konsistenz
 zu wahren, was die Stimmung und die generelle Szenerie betrifft. Keinesfalls darfst
 Du Gegenstände, Objekte, Wege und Beschreibungen des Hundes oder Zombies aus der vorherigen
 Beschreibung übernehmen, denn dies kann sich im Spielverlauf geändert haben. Diese
 Informationen dürfen ausschließlich nur aus den obigen Angaben genommen werden. Die

 Vorherige Beschreibung
 ======================
 {prev}
            """

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

    def simple_message(self,message, maxtokens=80):
        #
        # Send a message to the LLM and return the answer.
        # Retries transient server errors (503 UNAVAILABLE / 429 / 504) with a short
        # backoff before giving up, so demand spikes don't surface as a "hang".
        #
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                dprint(dl.LLM, f"GeminiInterface.simple_message: sending message: {message}")
                response = self.client.models.generate_content(
                    model=self.gemini_text_model_id,  # <- Modell-ID
                    contents=message,
                    config=genai.types.GenerateContentConfig(
                        max_output_tokens=maxtokens
                    )
                )

                self.tokens = self.tokens + response.usage_metadata.total_token_count
                self.numcalls = self.numcalls + 1
                self.token_details.append(response.usage_metadata.total_token_count)
                r = self.clean_truncated_sentence(response.text)
                return r
            except Exception as e:
                msg = str(e)
                transient = any(code in msg for code in
                                ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "504", "DEADLINE"))
                if transient and attempt < max_attempts - 1:
                    wait = 2 ** attempt  # 1s, 2s
                    dprint(dl.LLM, f"GeminiInterface.simple_message: transienter Fehler ({msg[:70]}), "
                                   f"Retry {attempt + 1}/{max_attempts - 1} in {wait}s")
                    time.sleep(wait)
                    continue
                dprint(dl.LLM, f"GeminiInterface.simple_message: Exception! {e}")
                traceback.print_exc()  # gibt den kompletten Stacktrace auf stderr aus
                return ""

    def narrate(self, gs:GameState, pl) -> str:
        #
        # Generate narration only for human players. NPCs don't need that
        #
        if type(pl) is not PlayerState:
            dprint(dl.LLM,f"Skipping narrate() for Player '{pl.name}'")
            return ""

        room = pl.location.name
        # Cache key = the STABLE scene prompt (without the volatile previous-description
        # block), so narration is only regenerated when the scene actually changes — not
        # on every serialize/turn. This saves tokens and reduces LLM load (503 spikes).
        base_prompt = self.gen_narration_prompt(gs, pl)
        n = self.narration_cache.get(room, prompt=base_prompt)
        if n:
            dprint(dl.LLM,f"GeminiInterface.narrate: using cached narration for room {room}")
            return n

        # Scene changed (or first visit): generate, feeding the previous description for
        # style continuity, but keep the cache key on the stable base prompt.
        prompt = base_prompt + self._prev_description_addendum(pl)
        try:
            dprint(dl.LLM, f"GeminiInterface.narrate: generating new narration for room {room}")
            response = self.client.models.generate_content(
                model=self.gemini_text_model_id,  # <- Modell-ID
                contents=prompt,
                config=genai.types.GenerateContentConfig(  # <- genai.types.GenerateContentConfig
                    max_output_tokens=300
                )
            )

            self.tokens = self.tokens + response.usage_metadata.total_token_count
            self.numcalls = self.numcalls + 1
            self.token_details.append(response.usage_metadata.total_token_count)
            r = self.clean_truncated_sentence(response.text)
            self.txt_prev_description[room] = r
            self.narration_cache.update(room=room, prompt=base_prompt, narration=r)
            return r
        except Exception as e:
            print("Exception!!")
            pprint(e)
            traceback.print_exc()
            self.narration_cache.invalidate(room)
            prev = self.txt_prev_description.get(pl.location.name)
            if prev:
                return prev
            return "Die Szenenbeschreibung ist vorübergehend nicht verfügbar."


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
#                 dprint(dl.LLM,f"{'#'*80}")
#                 dprint(dl.LLM,"Creating Summary".center(80))
#                 dprint(dl.LLM,f"{'#' * 80}")
#                 dprint(dl.LLM,self.txt_prev_descriptions)
#                 response = self.gemini_text_model.generate_content(sum_prompt#,
#                                                                    #generation_config = genai.types.GenerationConfig(
#                                                                    #         max_output_tokens=200  # Beispiel: Maximal 200 Tokens für Szenenbeschreibungen
#                                                                    #                                                 )
#                                                                    )
#                 self.txt_prev_descriptions = response.text
#                 self.tokens = self.tokens+response.usage_metadata.total_token_count
#                 self.numcalls = self.numcalls+1
#                 self.token_details.append(response.usage_metadata.total_token_count)
#                 dprint(dl.LLM,f"{'#' * 80}")
#                 dprint(dl.LLM,self.txt_prev_descriptions)
#                 dprint(dl.LLM,f"{'#' * 80}")
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




    import json
    from typing import List, Dict, Any

    def validate_gemini_tools_schema(self,tools_list: List[Dict[str, Any]]) -> List[str]:
        """
        Prüft eine Gemini-Tools-Liste auf häufige JSON-Schema-Fehler,
        insbesondere bei Typdeklarationen ('type' sollte ein String sein).

        Args:
            tools_list: Die Liste der Tool-Definitionen (Dictionaries).

        Returns:
            Eine Liste von Fehlermeldungen. Ist die Liste leer, ist das Schema gültig.
        """
        errors = []

        # Gültige JSON-Schema-Basistypen
        valid_schema_types = ["object", "string", "number", "integer", "boolean", "array", "null"]

        if not isinstance(tools_list, list):
            errors.append("Gesamte 'tools'-Definition muss eine Liste sein.")
            return errors

        for i, tool_def in enumerate(tools_list):
            tool_name = tool_def.get("name", f"Unbekanntes Tool bei Index {i}")

            if not isinstance(tool_def, dict):
                errors.append(f"Tool '{tool_name}': Definition muss ein Dictionary sein.")
                continue

            if "name" not in tool_def or not isinstance(tool_def["name"], str):
                errors.append(f"Tool bei Index {i}: 'name' fehlt oder ist kein String.")

            if "description" not in tool_def or not isinstance(tool_def["description"], str):
                errors.append(f"Tool '{tool_name}': 'description' fehlt oder ist kein String.")

            if "parameters" in tool_def:
                params_def = tool_def["parameters"]
                if not isinstance(params_def, dict):
                    errors.append(f"Tool '{tool_name}': 'parameters' muss ein Dictionary sein.")
                    continue

                # Prüfen des Top-Level 'type' in 'parameters'
                if "type" not in params_def or not isinstance(params_def["type"], str) or params_def[
                    "type"] != "object":
                    errors.append(f"Tool '{tool_name}': 'parameters.type' muss der String 'object' sein.")

                if "properties" in params_def:
                    properties_def = params_def["properties"]
                    if not isinstance(properties_def, dict):
                        errors.append(f"Tool '{tool_name}': 'parameters.properties' muss ein Dictionary sein.")
                        continue

                    for param_name, param_schema in properties_def.items():
                        if not isinstance(param_schema, dict):
                            errors.append(
                                f"Tool '{tool_name}', Parameter '{param_name}': Schema muss ein Dictionary sein.")
                            continue

                        # Prüfen des 'type' für jeden einzelnen Parameter
                        if "type" not in param_schema or not isinstance(param_schema["type"], str) or param_schema[
                            "type"] not in valid_schema_types:
                            errors.append(
                                f"Tool '{tool_name}', Parameter '{param_name}': 'type' muss ein gültiger JSON-Schema-Typ-String sein (z.B. 'string', 'object'). Aktueller Wert: '{param_schema.get('type')}' ({type(param_schema.get('type'))}).")

                        if "description" in param_schema and not isinstance(param_schema["description"], str):
                            errors.append(
                                f"Tool '{tool_name}', Parameter '{param_name}': 'description' muss ein String sein.")

                        if "enum" in param_schema:
                            if not isinstance(param_schema["enum"], list):
                                errors.append(
                                    f"Tool '{tool_name}', Parameter '{param_name}': 'enum' muss eine Liste sein.")
                            else:
                                if not all(isinstance(item, str) for item in param_schema["enum"]):
                                    errors.append(
                                        f"Tool '{tool_name}', Parameter '{param_name}': Alle Elemente in 'enum' müssen Strings sein.")

                if "required" in params_def:
                    required_params = params_def["required"]
                    if not isinstance(required_params, list):
                        errors.append(f"Tool '{tool_name}': 'parameters.required' muss eine Liste sein.")
                    else:
                        if not all(isinstance(item, str) for item in required_params):
                            errors.append(
                                f"Tool '{tool_name}', Parameter '{param_name}': Alle Elemente in 'required' müssen Strings sein.")

        return errors

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: dict) -> list[dict]:
        # Name angepasst

        # Extrahiere die Listen für die 'enum's aus dem context_data
        available_object_ids = game_context_for_tools.get("available_object_ids", [])
        available_object_ids_in_neighborhood = game_context_for_tools.get("available_object_ids_in_neighborhood", [])
        available_place_ids = game_context_for_tools.get("available_place_ids", [])
        available_target_player_ids = game_context_for_tools.get("available_target_player_ids", [])




        from google.genai.types import FunctionDeclaration, Tool, Schema, Type ,GenerateContentConfig, ToolConfig, FunctionCallingConfig

        # HINWEIS: Sie müssen 'Schema' aus den Typen importieren, z.B. 'from google.genai.types import FunctionDeclaration, Schema'

        t_gehen = FunctionDeclaration(
            name="gehe",
            description="Bewege den Spieler an einen anderen Ort.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "direction": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Zielorts (z.B. 'p_schuppen').",
                        enum=available_place_ids
                    )
                },
                required=["direction"]
            )
        )
        t_anwenden = FunctionDeclaration(
            name="anwenden",
            description="Führe eine Aktion mit einem Objekt aus, optional auf ein Zielobjekt bezogen.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "what": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Objekts, das angewendet wird (z.B. 'o_schluessel').",
                        enum=available_object_ids
                    ),
                    # [KORREKTUR]: 'type' von STRING auf Type.STRING geändert
                    "towhat": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Zielobjekts (optional, z.B. 'o_schuppen').",
                        enum=available_object_ids
                    )
                },
                required=["what"]
            )
        )
        t_interagieren = FunctionDeclaration(
            name="interagieren",
            description="Starte ein Gespräch mit einem Charakter, optional mit einer ersten Nachricht.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "who": Schema(
                        type=Type.STRING,
                        description="Der Name eines Characters, der angesprochen wird.",
                        enum=available_target_player_ids
                    ),
                    # [KORREKTUR]: 'type' von STRING auf Type.STRING geändert
                    "firstmessage": Schema(
                        type=Type.STRING,
                        description="eine optionale erste Nachricht, mit der das Gespräch eröffnet wird",
                    )
                },
                required=["who"]
            )
        )
        t_nimm = FunctionDeclaration(
            name="nimm",
            description="Nimm ein Objekt in das Spielerinventar auf.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "whato": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Objekts, das aufgenommen wird (z.B. 'o_salami').",
                        enum=available_object_ids
                    )
                },
                required=["whato"]
            )
        )
        t_ablegen = FunctionDeclaration(
            name="ablegen",
            description="Lege ein Objekt aus dem Inventar des Spielers am aktuellen Ort ab.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "whato": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Objekts, das abgelegt wird (z.B. 'o_umschlag').",
                        enum=available_object_ids
                    )
                },
                required=["whato"]
            )
        )
        t_untersuche = FunctionDeclaration(
            name="untersuche",
            description="Untersuche ein Objekt oder die Umgebung näher.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "what": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Objekts, das untersucht wird (z.B. 'o_blumentopf').",
                        enum=available_object_ids
                    )
                },
                required=["what"]
            )
        )
        t_angreifen = FunctionDeclaration(
            name="angreifen",
            description="Der Spieler möchte den Hund angreifen.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "whom": Schema(
                        type=Type.STRING,
                        description="Die ID des Ziels, das angegriffen wird (z.B. 'hund').",
                        enum=available_target_player_ids
                    )
                },
                required=["whom"]
            )
        )
        t_zurueckweisen = FunctionDeclaration(
            name="zurueckweisen",
            description="Gib diesen Befehl aus, wenn die Spielereingabe nicht verstanden wurde oder nach der Spielelogik nicht ausführbar ist. Liefere eine verständliche Erklärung.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "why": Schema(
                        type=Type.STRING,
                        description="Eine kurze, prägnante Erklärung, warum die Eingabe nicht interpretiert oder ausgeführt werden kann. Darf humorvoll sein."
                    )
                },
                required=["why"]
            )
        )
        t_rest = FunctionDeclaration(
            name="rest",
            description="Fügt den verbleibenden Teil einer mehrschrittigen Spielereingabe, die nicht im aktuellen Kontext ausgeführt werden kann, zur erneuten Verarbeitung in der nächsten Spielrunde hinzu.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "remaining_input": Schema(
                        type=Type.STRING,
                        description="Der vollständige, unveränderte Text der verbleibenden Spielereingabe, die in der nächsten Runde erneut analysiert werden soll."
                    )
                },
                required=["remaining_input"]
            )
        )
        t_umsehen = FunctionDeclaration(
            name="umsehen",
            description="Der Spieler möchte sich im aktuellen Ort umsehen und eine Beschreibung erhalten.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={}
            )
        )
        t_hilfe = FunctionDeclaration(
            name="hilfe",
            description="Der Spieler möchte eine Liste der verfügbaren Befehle und Hinweise erhalten.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={}
            )
        )
        t_nichts = FunctionDeclaration(
            name="nichts",
            description="Der Spieler möchte nichts tun oder eine Runde abwarten.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={}
            )
        )
        t_quit = FunctionDeclaration(
            name="quit",
            description="Der Spieler möchte das Spiel beenden.",
            parameters=Schema(
                type=Type.OBJECT,
                properties={}
            )
        )

        function_declarations_list = [t_gehen, t_nimm, t_anwenden, t_interagieren, t_ablegen, t_umsehen, t_angreifen, t_untersuche, t_rest, t_zurueckweisen, t_nichts, t_quit, t_hilfe]
        configured_tools = [
            Tool(function_declarations=[decl])  # Jedes Tool MUSS eine Liste von FunctionDeclarations enthalten
            for decl in function_declarations_list
        ]

        # r = self.validate_gemini_tools_schema(tools)
        # dpprint(dl.LLM_PROMPT, r)
        # Der Prompt-String selbst braucht jetzt nicht mehr die Listen der IDs und Callnames,
        # da diese explizit im `tools`-Schema sind. Stattdessen kann er mehr auf die
        # semantische Bedeutung der Objekte eingehen.

        # Du kannst den 'narration_details' Block aus game_context_for_tools nutzen, um dem LLM
        # Kontext zu geben, der über die reinen Enum-Werte hinausgeht.
        narration_context_for_llm = game_context_for_tools.get("narration_details", {})

        prompt_str = f"""
        Wandle die folgende Spielereingabe in eine Liste atomarer Game-Engine-Befehle um.
        Generiere ein **JSON-Array**, das die *simulierten* Funktionsaufrufe als Text enthält. 
        **Du darfst KEINEN Erklärtext und KEINE Anführungszeichen außerhalb des JSON-Arrays generieren.**

        Falls eine Eingabe sich auf mehr als eine Aktion bezieht, generiere mehrere Funktionsaufrufe im Array.

        **Verwende ausschließlich die internen Objekt- und Ort-IDs, die in den Tool-Definitionen als 'enum'-Werte verfügbar sind.**
        Wenn ein Objekt/Ort in der Spieleranfrage mit einem 'freundlichen Namen' genannt wird, übersetze diesen in die korrekte ID.
        Wenn eine ID in den 'enum'-Listen nicht vorkommt, ist das Objekt/der Ort im aktuellen Kontext nicht verfügbar.
        In diesem Fall oder wenn die Aktion unsinnig ist, verwende den 'zurueckweisen'-Befehl.
        
        **Wenn Du eine Eingabe nicht verstehst, verwende den "zurueckweisen"-Tool-call und weise die Eingabe humorvoll, aber höflich zurück**
        **Wenn Du eine Eingabe mit mehreren logischen Teilschritten erhältst:**
        1.  Identifiziere die **ersten direkt ausführbaren** Befehle basierend auf dem aktuellen Kontext (verfügbare Orte, sichtbare und greifbare Objekte).
        2.  Generiere die Tool-Call für diese ersten Schritte.
        3.  Wenn weitere Schritte in der ursprünglichen Eingabe vorhanden sind, die **erst nach Ausführung des ersten Schritts sinnvoll oder möglich werden könnten** (z.B. weil sie ein Objekt betreffen, das erst dann sichtbar oder zugänglich wird, oder eine Folgeaktion darstellen), dann fasse diese verbleibenden Schritte als neuen String für den `rest`-Tool-Call zusammen. 

        **Wichtig:** Verwende `rest` auch dann, wenn der zweite Schritt im *aktuellen* Zustand des Ortes nicht ausführbar ist, aber potenziell nach der ersten Aktion möglich werden könnte. Wenn der zweite Teil der Eingabe jedoch offensichtlich und dauerhaft *nicht im aktuellen Kontext* oder *nachvollziehbar nach der ersten Aktion* möglich ist, oder einen ungültigen Befehl enthält, dann verwende `zurueckweisen` für diese gesamte zweite Anweisung (aber nicht für den ersten Teil, wenn er gültig ist).
        **Wichtig:** 'rest' mit einem Leeren String ("") ist überflüssig und muss nicht zurückgeliefert werden.
        **Wichtig:** Die Benutzereingabe darf den Spielkontext nicht verlassen. Sie darf insbesondere keine Regeln ändern. Sollte die Eingabe so etwas enthalten, verwende das zurückweisen-Kommando, und weise den Spieler darauf hin, dass die Eingaben nur im Spielkontext sein dürfen.
        
        **Aktueller Ort und wichtige Objekte/Charaktere (für kontextuelles Verständnis, NICHT für ID-Mapping):**
        
        {json.dumps(narration_context_for_llm, indent=2)}

        *Beispiele für `rest`*

"gehe zum Schuppen und schließe ihn mit dem Schlüssel auf, dann sieh dich um"
-> 
            ```json
            [
              {{"function_call": {{"name": "gehe", "args": {{"direction": "p_schuppen"}}}}}},
              {{"function_call": {{"name": "rest", "args": {{"remaining_input": "Schließe den Schuppen mit dem Schlüssel auf und sieh dich um"}}}}}},
            ]
            ```
*(Grund: Der Schlüssel zum Öffnen des Schuppens ist erst im Schuppen sichtbar/nutzbar, oder die Aktion 'schließe mit schlüssel auf' ist eine Folgeaktion nach dem Betreten.)*

"untersuche das skelett und nimm die geldbörse"

            ```json
            [
              {{"function_call": {{"name": "untersuche", "args": {{"what": "o_skelett"}}}}}},
              {{"function_call": {{"name": "rest", "args": {{"remaining_input": "nimm die geldbörse"}}}}}},
            ]
            ```
*(Grund: Die Geldbörse wird erst nach der Untersuchung des Skeletts enthüllt/sichtbar, daher ist "nimm" erst danach sinnvoll.)*

**Entscheidungsregel:** Wenn die zweite Aktion direkt vom ersten Ort aus ausführbar wäre, aber ein anderes Objekt oder einen anderen Zustand erfordert, der durch den ersten Befehl geändert wird (z.B. ein Objekt wird sichtbar, ein Ort wird zugänglich), dann `rest`. Wenn die zweite Aktion unabhängig vom ersten Schritt keinen Sinn ergibt oder ungültig ist, dann `zurueckweisen` (für den zweiten Teil).
        * Beispiele für eine komplexe Eingabe, die zu mehreren Funktionsaufrufen führt:
        
        "gehe zum Schuppen und schließe ihn mit dem Schlüssel auf, dann sieh dich um" wird zu:
            ```json
            [
              {{"function_call": {{"name": "gehe", "args": {{"direction": "p_schuppen"}}}}}},
              {{"function_call": {{"name": "rest", "args": {{"remaining_input": "Schließe den Schuppen mit dem Schlüssel auf und sieh dich um"}}}}}},
            ]
            ```
        "springe vom Dach und laufe zum Geldautomaten"
            ```json
            [
              {{"function_call": {{"name": "gehe", "args": {{"direction": "p_schuppen"}}}}}},
              {{"function_call": {{"name": "rest", "args": {{"remaining_input": "laufe zum Geldautomaten"}}}}}},
            ]
            ```
        "steige auf das Dach, betätige dort den Hebel, und klettere wieder herunter"    
             ```json
            [
              {{"function_call": {{"name": "gehe", "args": {{"direction": "p_dach"}}}}}},
              {{"function_call": {{"name": "rest", "args": {{"remaining_input": "betätige den Hebel, und klettere wieder herunter"}}}}}},
            ]
            ```
        Beispiele für die Interpretation von 'anwenden':
            "Öffne die Tür mit dem Schlüssel" ODER "Schließe die Tür mit dem Schlüssel auf" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_schluessel", "towhat": "o_schuppen"}}}}}}
            ```
            "Zünde die Sprengladung auf dem Felsen" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_sprengladung", "towhat": "o_felsen"}}}}}}
            ```
            "Drücke den Knopf der Sprengladung" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_sprengladung"}}}}}}
            ```
            "Stelle den Hebel um" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_hebel"}}}}}}
            ```
            "Lies das Manual" ODER "Lese die Bedienungsanleitung" ODER "Schau ins Handbuch" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_manual"}}}}}}
            ```
            *(Grund: Ein Dokument zu lesen wird als 'anwenden' des Dokuments interpretiert.)*
            "Öffne die Stahltür" ODER "Drehe das Handrad" ODER "Entriegle die Tür" wird zu:
            ```json
            {{"function_call": {{"name": "anwenden", "args": {{"what": "o_stahltuer"}}}}}}
            ```
            *(Grund: Eine Tür ohne Werkzeug zu öffnen wird als 'anwenden' der Tür selbst interpretiert.)*


        Beispiele für 'zurueckweisen'-Befehle:
            "Öffne den Warenautomaten" wird zu:
            ```json
            {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Du kannst den Warenautomat nicht öffnen. Du bräuchtest schon Geld, um an die Waren zu gelangen."}}}}}}
            ```
            "puste den Schuppen um" wird zu:
            ```json
            {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Interessante Idee - aber du kannst den Schuppen nicht umpusten."}}}}}}
            ```
            "Schlurbsdiwurps kadjhaslasdk" wird zu:
            ```json
            {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Sei mir nicht böse - aber das habe ich wirklich nicht verstanden.(tlhIngan Hol Dajatlhʼaʼ?)"}}}}}}
            ```
            
        Beispiele für 'interagieren'-Befehle:
            "Sprich mit dem Hund" oder "rede mit dem Hund" oder wird zu:
            ```json
            {{"function_call": {{"name": "interagieren", "args": {{"who": "Hund"}}}}}}
            ```
            
            "sage 'hallo!' zu Chris" oder "schreie Chris an: 'hallo!'" wird zu:
            ```json
            {{"function_call": {{"name": "interagieren", "args": {{"who": "Chris", "firstmessage":"hallo!"}}}}}}
            ```
            
        **Spielereingabe: "{user_input}"**

        Deine Antwort muss **ausschließlich** das JSON-Array der Tool-Calls sein. 
        Die **Definition und Semantik** der Befehle (gehe, anwenden, zurückweisen) wird durch die bereitgestellten Tools (`function_declarations`) gesteuert.
        """

        for attempt in range(2):
            try:
                #import google.generativeai as genai
                #from google.generativeai.types import GenerationConfig, Tool  # Füge Tool hinzu!
                #from google.generativeai.client import get_default_retriever_client

                # [NEU] Fassen Sie ALLE Konfigurationen (max_tokens, tools, tool_config) im 'config'-Objekt zusammen.
                my_config = genai.types.GenerateContentConfig(
                    max_output_tokens=150,

                    # [KORREKTUR]: Ersetzen Sie 'tools' durch 'function_declarations'!
                    tools = configured_tools,
                    tool_config=genai.types.ToolConfig(
                        function_calling_config=genai.types.FunctionCallingConfig(
                            mode="AUTO"
                        )
                    )
                )

                # [NEU] Aufruf über Client und Übergabe der Modell-ID
                response = self.client.models.generate_content(
                    model=self.gemini_text_model_id, # <- Modell-ID
                    contents=prompt_str,
                    config=my_config # <- generation_config wird zu config
                )


                dprint(dl.LLM, "LLM-Info: ++++++++++++++")
                dprint(dl.LLM_PROMPT,prompt_str)
                dprint(dl.LLM_PROMPT,"+++++++ END OF PROMPT +++++++")
                #dpprint(dl.LLM_PROMPT,tools)
                dprint(dl.LLM_PROMPT,"++++++++ END OF TOOLS Section ++++++++")
                dprint(dl.LLM, f"User input....: {user_input}")
                # Debug: Log raw response details
                dprint(dl.LLM, f"LLM response.function_calls: {response.function_calls}")
                try:
                    dprint(dl.LLM, f"LLM response.text: {response.text}")
                except Exception:
                    dprint(dl.LLM, "LLM response.text: <not available>")
                dprint(dl.LLM, f"LLM response candidates count: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    for ci, cand in enumerate(response.candidates):
                        dprint(dl.LLM, f"  Candidate {ci} finish_reason: {cand.finish_reason}")
                        if cand.content and cand.content.parts:
                            for pi, part in enumerate(cand.content.parts):
                                dprint(dl.LLM, f"  Candidate {ci} part {pi}: {part}")

                # Token-Nutzung aktualisieren
                self.tokens += response.usage_metadata.total_token_count
                self.numcalls += 1
                self.token_details.append(response.usage_metadata.total_token_count)

                if response.function_calls:
                    # FALL 1: Das Modell hat das STANDARD-Function-Calling-Verhalten gezeigt.
                    # Dies ist die korrekte, konforme Art, Tool Calls zu empfangen.
                    # Sie müssen die f_call Objekte manuell in Ihr JSON-Format umwandeln (wie in meiner letzten Antwort beschrieben).

                    commands_list = []
                    for f_call in response.function_calls:
                        commands_list.append({
                            "function_call": {
                                "name": f_call.name,
                                "args": dict(f_call.args)
                            }
                        })
                    return commands_list

                elif response.text:
                    # FALL 2: Das Modell hat auf Anweisung des Prompts das JSON-Array in das 'response.text'-Feld geschrieben.
                    # Dies war Ihr alter, non-konformer, aber funktionierender Weg.
                    # Das Modell wrappet die Antwort manchmal in Markdown-Code-Fences (```json ... ```),
                    # die wir vor dem Parsen entfernen müssen.
                    raw_text = response.text.strip()

                    # Detect Gemini Python-style responses like:
                    #   <ctrl42>call\nprint(default_api.anwenden(arg="value"))
                    #   default_api.gehen(direction="norden")
                    import re
                    python_api_match = re.search(
                        r'default_api\.(\w+)\(([^)]*)\)', raw_text
                    )
                    if python_api_match and ('default_api.' in raw_text or '<ctrl' in raw_text or 'print(' in raw_text):
                        func_name = python_api_match.group(1)
                        args_str = python_api_match.group(2)
                        # Parse keyword arguments like: arg1="val1", arg2="val2"
                        parsed_args = {}
                        for kwarg_match in re.finditer(r'(\w+)\s*=\s*"([^"]*)"', args_str):
                            parsed_args[kwarg_match.group(1)] = kwarg_match.group(2)
                        dprint(dl.LLM, f"⚠️ Python-style Gemini response detected, extracted: {func_name}({parsed_args})")
                        return [{"function_call": {"name": func_name, "args": parsed_args}}]

                    # Markdown-Code-Fences entfernen
                    if raw_text.startswith("```"):
                        # Erste Zeile (```json oder ```) entfernen
                        first_newline = raw_text.find("\n")
                        if first_newline != -1:
                            raw_text = raw_text[first_newline + 1:]
                        # Schließende ``` entfernen
                        if raw_text.rstrip().endswith("```"):
                            raw_text = raw_text.rstrip()[:-3].rstrip()
                        dprint(dl.LLM, f"Markdown-Fences entfernt, bereinigter Text: {raw_text[:200]}")
                    try:
                        commands = json.loads(raw_text)
                        if isinstance(commands, list):
                            return commands
                    except json.JSONDecodeError as je:
                        dprint(dl.LLM, f"JSON parse failed for text: {raw_text[:200]} — error: {je}")

                # Fallback (z.B. wenn response.text kein gültiges JSON war)
                if attempt == 0:
                    dprint(dl.LLM, f"⚠️ Retry: API returned fallback response for '{user_input}', retrying in 1s (attempt {attempt+1}/2)")
                    time.sleep(1)
                    continue
                return [{"function_call": {"name": "zurueckweisen", "args": {
                    "why": "Interne Befehlsstruktur konnte nicht interpretiert werden.",
                    "is_system_error": True}}}]


            except Exception as e:
                # Hier fangen wir jegliche JSONDecodeError oder andere Exceptions ab
                dprint(dl.LLM, f"********** Fehler beim Parsen der Benutzereingabe: {e} **********")
                dprint(dl.LLM, f"User input: {user_input}")
                # Versuche, die rohe Antwort des LLM zu loggen, auch wenn sie ungültiges JSON war
                if 'response' in locals() and hasattr(response, 'text'):
                    dprint(dl.LLM, f"LLM Raw Response (possibly malformed): {response.text}")
                if 'response' in locals():
                    dprint(dl.LLM, "response:")
                    dpprint(dl.LLM,response)
                else:
                    dprint(dl.LLM,"LLM did not send a response")
                dprint(dl.LLM, f"Prompt used: {prompt_str}")
                #dprint(dl.LLM, "tools array:")
                #dpprint(dl.LLM,tools)

                if attempt == 0:
                    dprint(dl.LLM, f"⚠️ Retry: Exception during API call for '{user_input}', retrying in 1s (attempt {attempt+1}/2)")
                    traceback.print_exc()
                    time.sleep(1)
                    continue

                # Bei einem Fehler geben wir einen 'zurueckweisen'-Befehl als Dictionary zurück
                traceback.print_exc()
                return [{"function_call": {"name": "zurueckweisen", "args": {
                    "why": "Ein unerwarteter interner Fehler ist aufgetreten. Bitte versuche es anders.",
                    "is_system_error": True}}}]

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