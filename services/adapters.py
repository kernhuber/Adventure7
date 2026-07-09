from __future__ import annotations
from typing import Any, Mapping, Sequence

from services.interfaces import LLMClient

class LLMClientGemini(LLMClient):
    def __init__(self, **kwargs: Any) -> None:
        from gemini_interface import GeminiInterface as _GeminiInterface  # lazy: zieht google-genai
        self._impl = _GeminiInterface()

    def gen_narration_prompt(self, gs: Any, pl: Any) -> str:
        return self._impl.gen_narration_prompt(gs, pl)

    def clean_truncated_sentence(self, text: str) -> str:
        return self._impl.clean_truncated_sentence(text)

    def simple_message(self, text: str, maxtokens: int = 80, caller: str = "simple_message") -> str:
        return self._impl.simple_message(text, maxtokens, caller=caller)

    def narrate(self, gs: Any, pl: Any) -> str:
        return self._impl.narrate(gs, pl)

    def validate_llm_tools_schema(self, tools_list: Sequence[Mapping[str, Any]]) -> None:
        return self._impl.validate_gemini_tools_schema(tools_list)

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return self._impl.parse_user_input_to_commands(user_input, game_context_for_tools)

    # --- Storable (Save/Load): an die echte GeminiInterface (_impl) delegieren, damit
    #     GameState.save()/load() unabhängig davon funktioniert, ob gs.llm der Adapter
    #     oder direkt eine GeminiInterface ist.
    STORE_TYPE = "GeminiInterface"

    def store_id(self) -> str:
        return self._impl.store_id()

    def save(self) -> dict:
        return self._impl.save()

    def load(self, data: Mapping[str, Any], ctx: Any = None) -> None:
        self._impl.load(data, ctx)


class LLMClientGemma(LLMClient):
    """Adapter für das lokale Gemma-Backend (Ollama). Spiegelt LLMClientGemini, wrappt aber
    eine GemmaInterface. GemmaInterface wird hier lazy importiert, damit der Gemini-Pfad
    ohne installiertes 'ollama' läuft."""
    def __init__(self, **kwargs: Any) -> None:
        from gemma_interface import GemmaInterface as _GemmaInterface  # lazy: braucht 'ollama'
        self._impl = _GemmaInterface()

    def gen_narration_prompt(self, gs: Any, pl: Any) -> str:
        return self._impl.gen_narration_prompt(gs, pl)

    def clean_truncated_sentence(self, text: str) -> str:
        return self._impl.clean_truncated_sentence(text)

    def simple_message(self, text: str, maxtokens: int = 80, caller: str = "simple_message") -> str:
        return self._impl.simple_message(text, maxtokens, caller=caller)

    def narrate(self, gs: Any, pl: Any) -> str:
        return self._impl.narrate(gs, pl)

    def validate_llm_tools_schema(self, tools_list: Sequence[Mapping[str, Any]]) -> None:
        return self._impl.validate_llm_tools_schema(tools_list)

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return self._impl.parse_user_input_to_commands(user_input, game_context_for_tools)

    # --- Storable (Save/Load): an die GemmaInterface (_impl) delegieren. STORE_TYPE bleibt
    #     "GeminiInterface", damit Spielstände backend-übergreifend ladbar sind (gespeichert
    #     werden nur die Narrations-Caches, kein LLM-Client). ---
    STORE_TYPE = "GeminiInterface"

    def store_id(self) -> str:
        return self._impl.store_id()

    def save(self) -> dict:
        return self._impl.save()

    def load(self, data: Mapping[str, Any], ctx: Any = None) -> None:
        self._impl.load(data, ctx)
