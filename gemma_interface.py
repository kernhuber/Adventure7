"""GemmaInterface — lokales LLM-Backend über Ollama (Gemma).

Implementiert dieselbe Oberfläche wie ``GeminiInterface`` (siehe ``services/interfaces.py``
``LLMClient`` + wie die NPCs sie via ``gs.llm._impl`` nutzen), damit es hinter dem
``LLMClient``-Interface 1:1 austauschbar ist. Ausgewählt wird das Backend über
``utils.LLM_BACKEND`` -> ``services.llm_factory.make_llm()``.

Wichtige Designentscheidungen (siehe docs/PROMPT-OPTIMIZATION-PLAN.md und die Recherche):
- **Kein natives Function-Calling** bei Gemma 3. Stattdessen **Ollama Structured Outputs**:
  wir übergeben ein JSON-Schema (mit ``enum``s für gültige IDs) als ``format=``. Ollama nutzt
  constrained decoding (XGrammar) -> nur schema-gültige Tokens sind erlaubt -> **garantiert**
  gültiges JSON mit gültigen IDs. Das ersetzt (und härtet) die Gemini-``enum``-Qualitätssicherung.
- Rückgabe von ``parse_user_input_to_commands`` im GLEICHEN Format wie GeminiInterface:
  ``[{"function_call": {"name": ..., "args": {...}}}, ...]`` -> die Engine bleibt unverändert.

VORAUSSETZUNGEN auf dem Rechner: ``pip install ollama``, laufender Ollama-Dienst (:11434) und
ein gezogenes Modell (z.B. ``ollama pull gemma3``). Ohne das schlägt erst der ``__init__`` fehl
(bewusst -> die Factory importiert diese Datei nur, wenn LLM_BACKEND="gemma").

STATUS: Gerüst. ``parse_user_input_to_commands`` ist ausimplementiert (Kernstück);
``gen_narration_prompt`` ist noch eine kondensierte Erst-Fassung (TODO: den reichen
Narrations-Prompt mit GeminiInterface teilen, statt duplizieren).
"""
from __future__ import annotations

import os
import json
from utils import dprint, dpprint, dl


# Erprobter Parse-Prompt aus GeminiInterface, 1:1 übernommen (Regeln + Beispiele) - nur die
# Tool-Referenz ist neutralisiert (Gemma nutzt ein JSON-Schema via 'format=' statt
# function_declarations), und die Beispiele sind als JSON-ARRAY geschrieben, passend zum
# erzwungenen Top-Level-Array-Schema. Der variable Teil (Kontext + Eingabe) wird angehängt.
_PARSE_PROMPT_FIXED = """\
Wandle die Spielereingabe (ganz unten) in eine Liste atomarer Game-Engine-Befehle um.
Antworte ausschliesslich mit einem JSON-Array der (simulierten) Funktionsaufrufe - kein
Erklaertext, keine Anfuehrungszeichen ausserhalb des Arrays. Bezieht sich die Eingabe auf
mehrere Aktionen, erzeuge mehrere Eintraege. Jeder Eintrag hat die Form
{"function_call": {"name": ..., "args": {...}}}; die erlaubten Befehle und IDs liefert das
vorgegebene JSON-Schema.

ID-Mapping: Verwende ausschliesslich die internen Objekt-/Ort-IDs aus den 'enum'-Werten des
JSON-Schemas; uebersetze freundliche Namen in die passende ID. Kommt eine ID in keiner
'enum'-Liste vor, ist sie im aktuellen Kontext nicht verfuegbar -> dann (oder bei unsinniger/
unverstaendlicher Eingabe) 'zurueckweisen' (humorvoll, aber hoeflich). Eingaben, die den
Spielkontext verlassen oder Regeln aendern wollen, ebenfalls 'zurueckweisen'.

Mehrschrittige Eingaben (rest): Erzeuge Tool-Calls fuer die ERSTEN direkt ausfuehrbaren
Schritte. Verbleibende Schritte, die erst NACH deren Ausfuehrung sinnvoll/moeglich werden
(z.B. ein Objekt wird erst dann sichtbar oder ein Ort zugaenglich), fasst du als EINEN String
im 'rest'-Tool-Call zusammen - der Kontext des naechsten Aufrufs kennt dann den neuen Zustand.
Ist der zweite Teil dauerhaft unmoeglich/ungueltig, nutze 'zurueckweisen' (der gueltige erste
Teil bleibt bestehen). Ein leeres 'rest' ("") entfaellt. WICHTIG: Weiche fuer einen Schritt NIE
auf einen ANDEREN Ort/ID aus, nur weil das gemeinte Ziel gerade nicht im 'enum' steht - dann
gehoert dieser Schritt in 'rest' (z.B. einen gerade erst aufgeschlossenen Raum betreten: 'gehe'
erst, wenn er zugaenglich ist).

Beispiele nimm/ablegen (Gegenstand aufheben bzw. aus dem Inventar ablegen - NICHT 'untersuche'!):
"nimm die Leiter" -> [{"function_call": {"name": "nimm", "args": {"whato": "o_leiter"}}}]
"heb die Sprengladung auf" -> [{"function_call": {"name": "nimm", "args": {"whato": "o_sprengladung"}}}]
"nimm die Geldboerse an dich / steck die Geldboerse ein" -> [{"function_call": {"name": "nimm", "args": {"whato": "o_geldboerse"}}}]
"lege den Umschlag ab / lass den Umschlag hier" -> [{"function_call": {"name": "ablegen", "args": {"whato": "o_umschlag"}}}]

Beispiele rest (Grund jeweils: das Ziel wird erst nach Schritt 1 verfuegbar):
"gehe zum Schuppen und schliesse ihn mit dem Schluessel auf, dann sieh dich um" -> [{"function_call": {"name": "gehe", "args": {"direction": "p_schuppen"}}}, {"function_call": {"name": "rest", "args": {"remaining_input": "Schliesse den Schuppen mit dem Schluessel auf und sieh dich um"}}}]
"untersuche das skelett und nimm die geldboerse" -> [{"function_call": {"name": "untersuche", "args": {"what": "o_skelett"}}}, {"function_call": {"name": "rest", "args": {"remaining_input": "nimm die geldboerse"}}}]
"oeffne den Schuppen mit dem Schluessel und tritt ein" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_schluessel", "towhat": "o_schuppen"}}}, {"function_call": {"name": "rest", "args": {"remaining_input": "betritt den Schuppen"}}}]
"schliesse die Stahltuer auf und geh hindurch" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_stahltuer"}}}, {"function_call": {"name": "rest", "args": {"remaining_input": "geh durch die Stahltuer"}}}]

Beispiele anwenden (Dokument lesen bzw. Tuer ohne Werkzeug oeffnen = 'anwenden' des Objekts selbst):
"Oeffne/Schliesse die Tuer mit dem Schluessel auf" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_schluessel", "towhat": "o_schuppen"}}}]
"Zuende die Sprengladung auf dem Felsen" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_sprengladung", "towhat": "o_felsen"}}}]
"Druecke den Knopf der Sprengladung" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_sprengladung"}}}]
"Stelle den Hebel um" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_hebel"}}}]
"Lies das Manual / die Bedienungsanleitung" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_manual"}}}]
"Oeffne die Stahltuer / Drehe das Handrad" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_stahltuer"}}}]

Beispiele trinken/auffuellen (TRINKEN = 'anwenden' NUR des Getraenk-/Quell-Objekts, EIN Argument;
das AUFFUELLEN der Flasche ist etwas anderes = 'anwenden Flasche Quelle', ZWEI Argumente - nicht verwechseln!):
"trinke vom Wasserspender / trink aus dem Brunnen" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_wasserspender"}}}]
"trinke aus der Flasche / stille deinen Durst" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_flasche"}}}]
"fuelle die Flasche am Wasserspender auf" -> [{"function_call": {"name": "anwenden", "args": {"what": "o_flasche", "towhat": "o_wasserspender"}}}]

Beispiele zurueckweisen:
"Oeffne den Warenautomaten" -> [{"function_call": {"name": "zurueckweisen", "args": {"why": "Du kannst den Warenautomat nicht oeffnen. Du braeuchtest schon Geld, um an die Waren zu gelangen."}}}]
"Schlurbsdiwurps kadjhaslasdk" -> [{"function_call": {"name": "zurueckweisen", "args": {"why": "Sei mir nicht boese - aber das habe ich wirklich nicht verstanden."}}}]

Beispiele interagieren (nur ANWESENDE NPCs, niemals der Spieler selbst):
"rede mit dem Hund" -> [{"function_call": {"name": "interagieren", "args": {"who": "Hund"}}}]
"sag dem Hund 'hallo!'" -> [{"function_call": {"name": "interagieren", "args": {"who": "Hund", "firstmessage": "hallo!"}}}]"""


class GemmaInterface:
    # Verb-Namen (müssen zu den Gemini-Tool-Namen / der Engine-Verb-Dispatch passen) und die
    # Arg-Schlüssel je Verb -> zum Nachbauen der {"function_call": {...}}-Struktur.
    _VERB_ARGS = {
        "gehe": ["direction"],
        "anwenden": ["what", "towhat"],
        "interagieren": ["who", "firstmessage"],
        "nimm": ["whato"],
        "ablegen": ["whato"],
        "untersuche": ["what"],
        "angreifen": ["whom"],
        "zurueckweisen": ["why"],
        "rest": ["remaining_input"],
        "umsehen": [],
        "hilfe": [],
        "nichts": [],
        "quit": [],
    }

    class _narration_cache:
        def __init__(self):
            self.cache = {}
        def update(self, room, prompt, narration):
            self.cache[room] = {"prompt": prompt, "narration": narration}
        def invalidate(self, room):
            self.cache.pop(room, None)
        def get(self, room, prompt):
            e = self.cache.get(room)
            return e["narration"] if (e and e["prompt"] == prompt) else None

    def __init__(self):
        import ollama  # lazy -> nur nötig, wenn Gemma wirklich gewählt ist
        self._ollama = ollama
        host = os.environ.get("OLLAMA_HOST")  # z.B. "http://localhost:11434"
        self._client = ollama.Client(host=host) if host else ollama.Client()
        # Modellwahl: Env GEMMA_MODEL übersteuert das utils-Flag, sonst utils.GEMMA_MODEL, sonst Default.
        try:
            import utils as _u
            _utils_model = getattr(_u, "GEMMA_MODEL", None)
        except Exception:
            _utils_model = None
        self.model_id = os.environ.get("GEMMA_MODEL") or _utils_model or "gemma3"
        # Token-Buchhaltung analog GeminiInterface (tokenstats/token_report bleiben kompatibel).
        self.tokens = 0
        self.cached_tokens = 0          # lokal: kein impliziter Cache -> bleibt 0
        self.numcalls = 0
        self.token_details = []
        self.txt_prev_description = {}
        self.narration_cache = self._narration_cache()
        dprint(dl.LLM, f"🦙 GemmaInterface bereit (Modell='{self.model_id}', host='{host or 'default'}')")

    # ---------------- Ollama-Aufruf + Token-Buchhaltung ----------------
    def _generate(self, prompt: str, caller: str, fmt=None, num_predict: int | None = None) -> str:
        """Ein Ollama-Textaufruf. ``fmt`` = JSON-Schema (dict) für structured outputs oder None."""
        options = {"temperature": 0}
        if num_predict:
            options["num_predict"] = num_predict
        # think=False: "Thinking"-Modelle (z.B. gemma4) verbrauchen sonst das Token-Budget im
        # Denk-Teil und lassen 'response' leer -> das war die fehlende Narration. Bei Modellen
        # ohne Thinking wird der Parameter ignoriert.
        kwargs = {"model": self.model_id, "prompt": prompt, "options": options, "think": False}
        if fmt:                      # 'format' nur setzen, wenn ein Schema vorliegt (None ist heikel)
            kwargs["format"] = fmt
        # Voller Prompt (+ ggf. Schema) ins Log, NICHT gekürzt. Vor dem Call, damit er auch bei
        # einem Fehler sichtbar ist.
        dprint(dl.LLM_PROMPT, f"===== [gemma {caller}] MODELL={self.model_id} =====\n"
                              f"----- PROMPT -----\n{prompt}\n----- FORMAT/SCHEMA -----\n{fmt}\n----- ENDE PROMPT -----")
        try:
            resp = self._client.generate(**kwargs)
        except Exception as e:
            dprint(dl.LLM, f"GemmaInterface._generate: Ollama-Fehler ({caller}): {e}")
            return ""
        self._log_tokens(resp, caller)
        # Komplette Antwortstruktur ins Log, NICHT gekürzt. Nur der opake 'context'-Token-Array
        # wird auf seine Länge reduziert (sonst Seiten voller Token-IDs).
        try:
            dump = resp.model_dump() if hasattr(resp, "model_dump") else (dict(resp) if isinstance(resp, dict) else vars(resp))
            dump = dict(dump)
            if isinstance(dump.get("context"), (list, tuple)):
                dump["context"] = f"<{len(dump['context'])} tokens weggelassen>"
        except Exception:
            dump = {"repr": str(resp)}
        dpprint(dl.LLM_PROMPT, {"gemma_caller": caller, "response_full": dump})
        return (resp.get("response") if isinstance(resp, dict) else getattr(resp, "response", None)) or ""

    def _log_tokens(self, resp, caller: str) -> None:
        def _f(key):
            if isinstance(resp, dict):
                return resp.get(key, 0) or 0
            return getattr(resp, key, 0) or 0
        n = _f("prompt_eval_count") + _f("eval_count")  # Input- + Output-Tokens
        self.tokens += n
        self.numcalls += 1
        self.token_details.append({"caller": caller, "tokens": n, "cached": 0})
        dprint(dl.LLM_TOKENS, f"[tokens] {caller}: {n} (kumuliert {self.tokens}, calls {self.numcalls})")

    def token_report(self) -> dict:
        report, total, total_cached = {}, 0, 0
        for e in self.token_details:
            caller, tok, cached = e.get("caller", "unbekannt"), e.get("tokens", 0), e.get("cached", 0)
            slot = report.setdefault(caller, {"calls": 0, "tokens": 0, "cached": 0})
            slot["calls"] += 1; slot["tokens"] += tok; slot["cached"] += cached
            total += tok; total_cached += cached
        report["_gesamt"] = {"calls": self.numcalls, "tokens": total, "cached": total_cached}
        return report

    def clean_truncated_sentence(self, text: str) -> str:
        """Schneidet einen evtl. abgeschnittenen letzten Satz ab (einfachere Fassung)."""
        if not text:
            return text
        t = text.rstrip()
        if t and t[-1] in ".!?…\"":
            return t
        cut = max(t.rfind("."), t.rfind("!"), t.rfind("?"))
        return t[:cut + 1] if cut > 0 else t

    def validate_llm_tools_schema(self, tools_list) -> None:
        # Gemma nutzt kein Gemini-Tool-Schema -> nichts zu validieren.
        return None

    # ---------------- Narration ----------------
    def gen_narration_prompt(self, gs, pl) -> str:
        # TODO: den reichen Narrations-Prompt mit GeminiInterface.gen_narration_prompt teilen
        # (in ein gemeinsames services/llm_prompts.py extrahieren), statt hier zu duplizieren.
        # Erst-Fassung: kompakter, konsistenz-betonter Prompt aus dem Ortszustand.
        if pl.location.place_prompt_f:
            loc = pl.location.place_prompt_f(gs, pl)
        else:
            loc = pl.location.place_prompt
        objs = "".join(o.prompt_f(gs, pl) for o in pl.location.place_objects if not o.hidden)
        return (
            "Du bist der Erzähler eines Text-Adventures. Fasse die Fakten stimmungsvoll zusammen "
            "(<=500 Zeichen), erfinde NICHTS dazu, bleibe konsistent, rede den Spieler in der 1. Person an.\n"
            f"Ort: {pl.location.callnames[0]}\n{loc}\nObjekte:\n{objs}\n"
        )

    def narrate(self, gs, pl) -> str:
        prompt = self.gen_narration_prompt(gs, pl)
        room = pl.location.name
        cached = self.narration_cache.get(room, prompt)
        if cached is not None:
            return cached
        text = self.clean_truncated_sentence(self._generate(prompt, "GemmaInterface.narrate", num_predict=300))
        if text:
            self.narration_cache.update(room, prompt, text)
            self.txt_prev_description[room] = text
        return text

    def simple_message(self, message, maxtokens=80, caller="simple_message") -> str:
        return self.clean_truncated_sentence(
            self._generate(message, f"GemmaInterface.{caller}", num_predict=maxtokens)
        )

    def _call_reasoning_llm(self, gs, prompt: str) -> str:
        # Vom Zombie via gs.llm._impl aufgerufen (HUNTING-Reasoning).
        return self._generate(prompt, "GemmaInterface._call_reasoning_llm", num_predict=400)

    # ---------------- Parse (Kernstück: structured outputs) ----------------
    def _build_command_schema(self, ctx: dict) -> dict:
        """JSON-Schema für ein Array atomarer Commands als ``oneOf`` PRO VERB. Jedes Verb hat
        seine **required** Args (mit ``enum`` für gültige IDs), sodass constrained decoding
        nicht nur die IDs erzwingt, sondern auch, dass die Args überhaupt DA sind (das war der
        Bug: nur 'name' required -> Gemma ließ 'direction' weg). Verben, deren Pflicht-Arg gerade
        keine gültige Auswahl hat (leere Liste), werden weggelassen (dann nicht produzierbar)."""
        obj_ids = ctx.get("available_object_ids", [])
        here_ids = ctx.get("available_object_ids_here", []) or obj_ids
        inv_ids = ctx.get("player_inventory_ids", []) or obj_ids
        place_ids = ctx.get("available_place_ids", [])
        target_ids = ctx.get("available_target_player_ids", [])
        take_ids = list(dict.fromkeys(here_ids))
        drop_ids = list(dict.fromkeys(inv_ids))

        variants: list = []

        def verb(name, required=None, optional=None):
            # Variante in der GLEICHEN Form wie die (Gemini-)Prompt-Beispiele:
            # {"function_call": {"name": <enum>, "args": {…}}}. So passen Beispiele und
            # erzwungenes Schema zusammen und die Ausgabe braucht KEIN Remapping.
            argprops, argreq = {}, []
            for argname, enum in (required or []):
                if enum is not None and len(enum) == 0:
                    return  # kein gültiges Ziel -> Verb aktuell nicht produzierbar
                argprops[argname] = {"type": "string"}
                if enum:
                    argprops[argname]["enum"] = list(enum)
                argreq.append(argname)
            for argname, enum in (optional or []):
                argprops[argname] = {"type": "string"}
                if enum:
                    argprops[argname]["enum"] = list(enum)
            variants.append({
                "type": "object",
                "properties": {"function_call": {
                    "type": "object",
                    "properties": {
                        "name": {"enum": [name]},
                        "args": {"type": "object", "properties": argprops,
                                 "required": argreq, "additionalProperties": False},
                    },
                    "required": ["name", "args"],
                    "additionalProperties": False,
                }},
                "required": ["function_call"],
                "additionalProperties": False,
            })

        verb("gehe", [("direction", place_ids)])
        verb("nimm", [("whato", take_ids)])
        verb("ablegen", [("whato", drop_ids)])
        verb("untersuche", [("what", obj_ids)])
        verb("anwenden", [("what", obj_ids)], [("towhat", obj_ids)])
        verb("interagieren", [("who", target_ids)], [("firstmessage", None)])
        verb("angreifen", [("whom", target_ids)])
        verb("zurueckweisen", [("why", None)])
        verb("rest", [("remaining_input", None)])
        for n in ("umsehen", "hilfe", "nichts", "quit"):
            verb(n)

        # Top-Level-Array wie in den (Gemini-)Beispielen; anyOf über die Verb-Varianten
        # (breiter unterstützt als oneOf; 'name'-enums sind disjunkt -> äquivalent).
        return {"type": "array", "items": {"anyOf": variants}}

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: dict) -> list:
        # Nutzt den ERPROBTEN Gemini-Parse-Prompt (Regeln + Beispiele, siehe _PARSE_PROMPT_FIXED)
        # - der Unterschied zu Gemini ist NUR der Ausgabe-Mechanismus: statt function_declarations
        # ein JSON-Schema via 'format=' (constrained decoding). Schema und Beispiele haben dieselbe
        # Form {"function_call": {...}}, daher braucht die Ausgabe kein Remapping.
        # TODO: _PARSE_PROMPT_FIXED langfristig mit GeminiInterface in ein gemeinsames Modul teilen.
        ctx = game_context_for_tools or {}
        schema = self._build_command_schema(ctx)
        narration = ctx.get("narration_details", {})
        prompt = (
            _PARSE_PROMPT_FIXED
            + "\n\n--- Aktueller Ort und wichtige Objekte/Charaktere (nur zum Verständnis, NICHT fürs ID-Mapping) ---\n"
            + json.dumps(narration, ensure_ascii=False, indent=2)
            + f'\n\n**Spielereingabe: "{user_input}"**\nAntworte ausschließlich mit dem JSON-Array der Tool-Calls.'
        )
        raw = self._generate(prompt, "GemmaInterface.parse_user_input_to_commands", fmt=schema, num_predict=400)
        try:
            data = json.loads(raw)
        except Exception as e:
            dprint(dl.LLM, f"GemmaInterface.parse: JSON-Fehler: {e} | raw={raw!r}")
            return [{"function_call": {"name": "zurueckweisen",
                                       "args": {"why": "Interne Befehlsstruktur konnte nicht interpretiert werden.",
                                                "is_system_error": True}}}]
        # Ausgabe ist bereits die Liste [{"function_call": {...}}]; als Fallback ein Objekt mit
        # 'commands'/'function_calls' akzeptieren.
        if isinstance(data, dict):
            data = data.get("commands") or data.get("function_calls") or []
        out = []
        for entry in (data or []):
            fc = entry.get("function_call") if isinstance(entry, dict) else None
            if not isinstance(fc, dict) or fc.get("name") not in self._VERB_ARGS:
                continue
            args = {k: v for k, v in (fc.get("args") or {}).items() if v not in (None, "")}
            out.append({"function_call": {"name": fc["name"], "args": args}})
        # Führendes/alleiniges 'rest' (die Engine kennt kein Verb 'rest') -> ablehnen.
        if not out or out[0]["function_call"]["name"] == "rest":
            return [{"function_call": {"name": "zurueckweisen",
                                       "args": {"why": "Das habe ich nicht verstanden.", "is_system_error": True}}}]
        return out

    # ---------------- Storable (Save/Load) ----------------
    STORE_TYPE = "GeminiInterface"   # backend-übergreifend ladbar; nur Caches werden gesichert

    def store_id(self) -> str:
        return "llm"

    def save(self) -> dict:
        return {"narration_cache": dict(self.narration_cache.cache),
                "txt_prev_description": dict(self.txt_prev_description)}

    def load(self, data, ctx=None) -> None:
        self.narration_cache.cache = dict(data.get("narration_cache", {}))
        self.txt_prev_description = dict(data.get("txt_prev_description", {}))
