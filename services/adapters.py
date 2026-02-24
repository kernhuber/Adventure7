from __future__ import annotations
from typing import Any, Mapping, Sequence

from services.interfaces import LLMClient
from GeminiInterface import GeminiInterface as _GeminiInterface

class LLMClientGemini(LLMClient):
    def __init__(self, **kwargs: Any) -> None:
        self._impl = _GeminiInterface()

    def gen_narration_prompt(self, gs: Any, pl: Any) -> str:
        return self._impl.gen_narration_prompt(gs, pl)

    def clean_truncated_sentence(self, text: str) -> str:
        return self._impl.clean_truncated_sentence(text)

    def simple_message(self, text: str, maxtokens: int) -> str:
        return self._impl.simple_message(text, maxtokens)

    def narrate(self, gs: Any, pl: Any) -> str:
        return self._impl.narrate(gs, pl)

    def validate_llm_tools_schema(self, tools_list: Sequence[Mapping[str, Any]]) -> None:
        return self._impl.validate_gemini_tools_schema(tools_list)

    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return self._impl.parse_user_input_to_commands(user_input, game_context_for_tools)

    def get_npc_action(self, game_state_for_npc: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._impl.get_npc_action(game_state_for_npc)
