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
        self.cached_tokens = 0   # implizit gecachte Prompt-Tokens (A1-Messung)
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
        # Reicher, faktentreuer Erzähler-Prompt - jetzt in narration_prompt.build_narration_prompt
        # gebündelt, damit Gemini UND Gemma exakt denselben Prompt nutzen (inkl. Wege + Hund/Zombie).
        from narration_prompt import build_narration_prompt
        return build_narration_prompt(gs, pl)

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

    def _log_tokens(self, response, caller: str) -> None:
        """Token-Verbrauch eines LLM-Calls zentral verbuchen - MIT Aufrufer-Label, damit
        man am Ende sieht, WO die meisten Tokens verbraten werden (siehe token_report())."""
        try:
            n = response.usage_metadata.total_token_count
        except Exception:
            n = 0
        # Implizit gecachte Prompt-Tokens (Gemini 2.5: 75% Rabatt bei Prefix-Hit). A1-Messung:
        # so sehen wir empirisch, ob/wie viel Caching greift, statt es aus der Doku zu raten.
        # Feldname im google-genai SDK: cached_content_token_count (defensiv gelesen).
        try:
            um = response.usage_metadata
            cached = (getattr(um, "cached_content_token_count", None)
                      or getattr(um, "total_cached_tokens", None) or 0)
        except Exception:
            cached = 0
        self.tokens += n
        self.cached_tokens += cached
        self.numcalls += 1
        self.token_details.append({"caller": caller, "tokens": n, "cached": cached})
        dprint(dl.LLM_TOKENS, f"[tokens] {caller}: {n} (davon {cached} cached) "
                              f"(kumuliert {self.tokens}, cached {self.cached_tokens}, calls {self.numcalls})")

    def token_report(self) -> dict:
        """Aggregiert token_details nach Aufrufer -> {caller: {'calls':n,'tokens':t}} plus
        '_gesamt'. Robust gegenüber alten Bare-Int-Einträgen (Label 'unbekannt')."""
        report: dict = {}
        total = 0
        total_cached = 0
        for e in self.token_details:
            if isinstance(e, dict):
                caller, tok, cached = e.get("caller", "unbekannt"), e.get("tokens", 0), e.get("cached", 0)
            else:
                caller, tok, cached = "unbekannt", (e if isinstance(e, int) else 0), 0
            slot = report.setdefault(caller, {"calls": 0, "tokens": 0, "cached": 0})
            slot["calls"] += 1
            slot["tokens"] += tok
            slot["cached"] += cached
            total += tok
            total_cached += cached
        report["_gesamt"] = {"calls": self.numcalls, "tokens": total, "cached": total_cached}
        return report

    def _log_prompt_sections(self, caller: str, sections: dict, response) -> None:
        """Instrumentierung fürs Prompt-Tuning: zeigt, wie sich der Input-Prompt eines
        LLM-Calls auf seine Abschnitte aufteilt (Zeichen + geschätzte Tokens). Die
        Token-Schätzung je Abschnitt verteilt den ECHTEN prompt_token_count der Antwort
        proportional zur Zeichenzahl - so ist die Summe realistisch geerdet. Der Split ist
        eine Näherung (strukturiertes Tools-Schema hat ein anderes Zeichen/Token-Verhältnis
        als Prosa), reicht aber, um zu sehen, WO die Tokens sitzen. Läuft bei dl.LLM_TOKENS."""
        try:
            prompt_tokens = response.usage_metadata.prompt_token_count
        except Exception:
            prompt_tokens = 0
        total_chars = sum(len(v) for v in sections.values()) or 1
        lines = [f"[promptsize] {caller}: input≈{prompt_tokens} tok, {total_chars} Zeichen"]
        for name, text in sections.items():
            c = len(text)
            est = round(prompt_tokens * c / total_chars)
            lines.append(f"    {name:<22}{c:>7} Zeichen  ~{est:>6} tok  ({100 * c / total_chars:4.1f}%)")
        dprint(dl.LLM_TOKENS, "\n".join(lines))

    def simple_message(self, message, maxtokens=80, caller="simple_message"):
        #
        # Send a message to the LLM and return the answer.
        # Retries transient server errors (503 UNAVAILABLE / 429 / 504) with a short
        # backoff before giving up, so demand spikes don't surface as a "hang".
        #
        # ``caller`` labels the token accounting (token_report / dl.LLM_TOKENS) so we can
        # tell WHO spent the tokens (dog chat, zombie chat, zombie reasoning, ...). All
        # these paths share this one method, so without a label they were indistinguishable.
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

                self._log_tokens(response, f"GeminiInterface.{caller}")
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

    def _call_reasoning_llm(self, gs, prompt: str) -> str:
        """NPC-Reasoning (z.B. Zombie-HUNTING): EIN Textaufruf gegen das stärkere
        Reasoning-Modell. Backend-Nahtstelle: der NPC ruft ``gs.llm._impl._call_reasoning_llm``
        auf, GemmaInterface hat dieselbe Methode - so bleibt der NPC-Code LLM-unabhängig.
        Gibt bei Fehler "" zurück (der Aufrufer hat einen eigenen Fallback)."""
        try:
            response = self.client.models.generate_content(
                model=self.gemini_reasoning_model_id,
                contents=prompt,
                config=genai.types.GenerateContentConfig(max_output_tokens=400),
            )
            self._log_tokens(response, "NPCZombieState._call_reasoning_llm")
            return response.text or ""
        except Exception as e:
            dprint(dl.LLM, f"GeminiInterface._call_reasoning_llm: Exception! {e}")
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

            self._log_tokens(response, "GeminiInterface.narrate")
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

        # B2 (enum-Scoping): engere, korrektere ID-Listen pro Verb -> kleineres Schema UND
        # weniger ungültige Tool-Calls. 'nimm' nur Objekte am Ort, 'ablegen' nur Inventar.
        # Fallback auf die volle Liste, falls eine Teil-Liste leer ist (kein leeres enum).
        nimm_object_ids = game_context_for_tools.get("available_object_ids_here", []) or available_object_ids
        ablegen_object_ids = game_context_for_tools.get("player_inventory_ids", []) or available_object_ids




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
                        enum=nimm_object_ids
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
                        enum=ablegen_object_ids
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
        t_gib = FunctionDeclaration(
            name="gib",
            description="Der Spieler gibt einen Gegenstand aus seinem Inventar an einen anwesenden Charakter (NPC).",
            parameters=Schema(
                type=Type.OBJECT,
                properties={
                    "what": Schema(
                        type=Type.STRING,
                        description="Die eindeutige ID des Objekts aus dem Inventar, das übergeben wird (z.B. 'o_knochen').",
                        enum=ablegen_object_ids
                    ),
                    "towhom": Schema(
                        type=Type.STRING,
                        description="Der Name des anwesenden Charakters, der den Gegenstand erhält (z.B. 'Hund').",
                        enum=available_target_player_ids
                    )
                },
                required=["what", "towhom"]
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

        function_declarations_list = [t_gehen, t_nimm, t_anwenden, t_interagieren, t_ablegen, t_gib, t_umsehen, t_angreifen, t_untersuche, t_rest, t_zurueckweisen, t_nichts, t_quit, t_hilfe]
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

        # HINWEIS (Prompt-Optimierung B1+B1b, 2026-07-08): Der FIXE Teil (Regeln + Beispiele)
        # steht komplett vorne, der VARIABLE Teil (Kontext + User-Eingabe) ganz am Ende. So
        # ist der große, bei jeder Eingabe identische Prefix stabil und später cachebar. Die
        # Beispiele wurden nur entrümpelt (Duplikate + ```json-Ballast raus), inhaltlich aber
        # NICHT beschnitten - die enum-/Kontext-basierte Qualitätssicherung bleibt unangetastet.
        prompt_str = f"""
        Wandle die Spielereingabe (ganz unten) in eine Liste atomarer Game-Engine-Befehle um.
        Antworte **ausschließlich** mit einem **JSON-Array** der (simulierten) Funktionsaufrufe -
        kein Erklärtext, keine Anführungszeichen außerhalb des Arrays. Bezieht sich die Eingabe
        auf mehrere Aktionen, erzeuge mehrere Einträge. Die genaue Semantik der Befehle liefert
        das Tool-Schema (`function_declarations`).

        **ID-Mapping:** Verwende ausschließlich die internen Objekt-/Ort-IDs aus den 'enum'-Werten
        der Tool-Definitionen; übersetze freundliche Namen in die passende ID. Kommt eine ID in
        keiner 'enum'-Liste vor, ist sie im aktuellen Kontext nicht verfügbar -> dann (oder bei
        unsinniger/unverständlicher Eingabe) 'zurueckweisen' (humorvoll, aber höflich). Eingaben,
        die den Spielkontext verlassen oder Regeln ändern wollen, ebenfalls 'zurueckweisen' mit
        Hinweis, dass nur Eingaben im Spielkontext erlaubt sind.

        **Mehrschrittige Eingaben (`rest`):** Erzeuge Tool-Calls für die **ersten direkt
        ausführbaren** Schritte. Verbleibende Schritte, die erst **nach** deren Ausführung
        sinnvoll/möglich werden (z.B. ein Objekt wird erst dann sichtbar oder ein Ort zugänglich),
        fasst du als **einen** String im `rest`-Tool-Call zusammen - der Kontext des nächsten
        Aufrufs kennt dann den neuen Zustand. Ist der zweite Teil dauerhaft unmöglich/ungültig,
        nutze dafür 'zurueckweisen' (der gültige erste Teil bleibt bestehen). Ein leeres `rest`
        ("") entfällt.

        *Beispiele `rest`* (Grund jeweils: das Ziel-Objekt/der Ort wird erst nach Schritt 1 verfügbar):
        "gehe zum Schuppen und schließe ihn mit dem Schlüssel auf, dann sieh dich um" -> [{{"function_call": {{"name": "gehe", "args": {{"direction": "p_schuppen"}}}}}}, {{"function_call": {{"name": "rest", "args": {{"remaining_input": "Schließe den Schuppen mit dem Schlüssel auf und sieh dich um"}}}}}}]
        "untersuche das skelett und nimm die geldbörse" -> [{{"function_call": {{"name": "untersuche", "args": {{"what": "o_skelett"}}}}}}, {{"function_call": {{"name": "rest", "args": {{"remaining_input": "nimm die geldbörse"}}}}}}]
        "steige auf das Dach, betätige dort den Hebel, und klettere wieder herunter" -> [{{"function_call": {{"name": "gehe", "args": {{"direction": "p_dach"}}}}}}, {{"function_call": {{"name": "rest", "args": {{"remaining_input": "betätige den Hebel und klettere wieder herunter"}}}}}}]

        *Beispiele `anwenden`* (Dokument lesen bzw. Tür ohne Werkzeug öffnen = 'anwenden' des Objekts selbst):
        "Öffne/Schließe die Tür mit dem Schlüssel auf" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_schluessel", "towhat": "o_schuppen"}}}}}}
        "Zünde die Sprengladung auf dem Felsen" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_sprengladung", "towhat": "o_felsen"}}}}}}
        "Drücke den Knopf der Sprengladung" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_sprengladung"}}}}}}
        "Stelle den Hebel um" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_hebel"}}}}}}
        "Lies das Manual / die Bedienungsanleitung" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_manual"}}}}}}
        "Öffne die Stahltür / Drehe das Handrad" -> {{"function_call": {{"name": "anwenden", "args": {{"what": "o_stahltuer"}}}}}}

        *Beispiele `zurueckweisen`:*
        "Öffne den Warenautomaten" -> {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Du kannst den Warenautomat nicht öffnen. Du bräuchtest schon Geld, um an die Waren zu gelangen."}}}}}}
        "puste den Schuppen um" -> {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Interessante Idee - aber du kannst den Schuppen nicht umpusten."}}}}}}
        "Schlurbsdiwurps kadjhaslasdk" -> {{"function_call": {{"name": "zurueckweisen", "args": {{"why": "Sei mir nicht böse - aber das habe ich wirklich nicht verstanden."}}}}}}

        *Beispiele `interagieren`:*
        "rede mit dem Hund" -> {{"function_call": {{"name": "interagieren", "args": {{"who": "Hund"}}}}}}
        "sage 'hallo!' zu Chris" -> {{"function_call": {{"name": "interagieren", "args": {{"who": "Chris", "firstmessage": "hallo!"}}}}}}

        *Beispiele `gib`* (Gegenstand aus dem Inventar an einen ANWESENDEN NPC übergeben; NICHT 'ablegen'):
        "gib dem Hund den Knochen / überreiche dem Hund den Knochen" -> {{"function_call": {{"name": "gib", "args": {{"what": "o_knochen", "towhom": "Hund"}}}}}}
        "gib dem Zombie die Geldbörse" -> {{"function_call": {{"name": "gib", "args": {{"what": "o_geldboerse", "towhom": "Zombie"}}}}}}

        --- Aktueller Ort und wichtige Objekte/Charaktere (nur zum Verständnis, NICHT fürs ID-Mapping) ---
        {json.dumps(narration_context_for_llm, indent=2)}

        **Spielereingabe: "{user_input}"**
        Antworte ausschließlich mit dem JSON-Array der Tool-Calls."""

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
                self._log_tokens(response, "GeminiInterface.parse_user_input_to_commands")
                # Prompt-Aufschlüsselung fürs Optimieren: Instruktionen+Beispiele vs.
                # Narrations-Kontext vs. Tools-Schema. (context_json ist wörtlich in
                # prompt_str eingebettet -> per replace() sauber herauslösbar.)
                context_json = json.dumps(narration_context_for_llm, indent=2)
                self._log_prompt_sections(
                    "parse",
                    {
                        "instruktionen+bsp": prompt_str.replace(context_json, ""),
                        "narrations-kontext": context_json,
                        "tools-schema": str(configured_tools),
                    },
                    response,
                )

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

                # Fallback: leere/unparsebare Antwort (kein function_call, kein
                # verwertbarer Text). FAIL-SAFE: hier bewusst KEIN Retry — ein
                # zweiter Versuch rät oft ein plausibles, aber falsches Kommando,
                # das dann still ausgeführt würde (beobachtet: ein ungewollter
                # "gehe"-Zug). Stattdessen sofort als Systemfehler zurückweisen ->
                # das "Spielleitung"-Modal erscheint, der Spieler bleibt stehen und
                # kann es erneut versuchen. (Der Exception-Pfad unten behält seinen
                # Retry für transiente 503/Netzwerkfehler — der liefert bei Erfolg
                # ein korrekt geparstes Kommando, kein geratenes.)
                dprint(dl.LLM, f"⚠️ Leere/unparsebare LLM-Antwort für '{user_input}' — als Systemfehler zurückgewiesen (kein Retry).")
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