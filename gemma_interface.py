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
from utils import dprint, dl


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
        self.model_id = os.environ.get("GEMMA_MODEL", "gemma3")
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
        try:
            resp = self._client.generate(model=self.model_id, prompt=prompt, format=fmt, options=options)
        except Exception as e:
            dprint(dl.LLM, f"GemmaInterface._generate: Ollama-Fehler ({caller}): {e}")
            return ""
        self._log_tokens(resp, caller)
        return (resp.get("response") if isinstance(resp, dict) else getattr(resp, "response", "")) or ""

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
        """JSON-Schema für ein Array atomarer Commands. IDs werden als ``enum`` erzwungen
        (constrained decoding). Leere Listen lassen wir als freie Strings (kein leeres enum)."""
        obj_ids = ctx.get("available_object_ids", [])
        here_ids = ctx.get("available_object_ids_here", []) or obj_ids
        inv_ids = ctx.get("player_inventory_ids", []) or obj_ids
        place_ids = ctx.get("available_place_ids", [])
        target_ids = ctx.get("available_target_player_ids", [])

        def s(enum_list):
            sc = {"type": "string"}
            if enum_list:
                sc["enum"] = list(enum_list)
            return sc

        item_props = {
            "name": {"type": "string", "enum": list(self._VERB_ARGS.keys())},
            "direction": s(place_ids),
            "what": s(obj_ids),
            "towhat": s(obj_ids),
            "whato": s(here_ids + [i for i in inv_ids if i not in here_ids]),
            "who": s(target_ids),
            "whom": s(target_ids),
            "firstmessage": {"type": "string"},
            "remaining_input": {"type": "string"},
            "why": {"type": "string"},
        }
        return {
            "type": "object",
            "properties": {
                "commands": {
                    "type": "array",
                    "items": {"type": "object", "properties": item_props, "required": ["name"]},
                }
            },
            "required": ["commands"],
        }

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: dict) -> list:
        ctx = game_context_for_tools or {}
        schema = self._build_command_schema(ctx)
        narration = ctx.get("narration_details", {})
        prompt = (
            "Zerlege die Spielereingabe in atomare Game-Engine-Befehle und gib sie als JSON "
            "(Feld 'commands') zurück. Verwende ausschließlich IDs, die im Kontext/Schema erlaubt "
            "sind; ist etwas nicht möglich oder unverständlich, nutze das Kommando 'zurueckweisen' "
            "mit 'why'. Mehrschrittiges, das erst nach einem früheren Schritt möglich wird, kommt "
            "als 'rest' mit 'remaining_input'.\n\n"
            f"Kontext (nur zum Verständnis):\n{json.dumps(narration, ensure_ascii=False)}\n\n"
            f'Spielereingabe: "{user_input}"'
        )
        raw = self._generate(prompt, "GemmaInterface.parse_user_input_to_commands", fmt=schema, num_predict=400)
        try:
            data = json.loads(raw)
        except Exception as e:
            dprint(dl.LLM, f"GemmaInterface.parse: JSON-Fehler: {e} | raw={raw[:200]}")
            return [{"function_call": {"name": "zurueckweisen",
                                       "args": {"why": "Interne Befehlsstruktur konnte nicht interpretiert werden.",
                                                "is_system_error": True}}}]
        out = []
        for cmd in (data.get("commands") or []):
            name = cmd.get("name")
            if name not in self._VERB_ARGS:
                continue
            args = {k: cmd[k] for k in self._VERB_ARGS[name] if cmd.get(k) not in (None, "")}
            out.append({"function_call": {"name": name, "args": args}})
        if not out:
            out = [{"function_call": {"name": "zurueckweisen",
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
