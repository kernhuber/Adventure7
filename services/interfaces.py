from __future__ import annotations
from typing import Protocol, Any, Mapping, Sequence


class Storable(Protocol):
    """Anything that can be part of a save game (GameState, players/NPCs, objects,
    ways, the LLM layer, ...).

    A saver serialises every live ``Storable`` into a self-describing envelope
    ``{"type": STORE_TYPE, "id": store_id(), "data": save()}`` and writes one JSON
    file. A loader rebuilds them in two phases: (1) instantiate every object by
    type+id, (2) call ``load(data, ctx)`` so each object restores its values AND
    resolves its references (location, ownedby, inventory, ...) via the
    ``LoadContext``. See ``docs/SAVE-LOAD-DESIGN.md``.

    Rules for implementers:
    - ``save()`` returns ONLY the ``data`` part (plain JSON-able values). The saver
      wraps type/id around it.
    - Serialise references as **ids** (``p_*``/``o_*``/``w_*``/player name), never as
      nested objects — this keeps cycles (Place<->GameObject) harmless.
    - Enums -> ``.name``; deques -> list; callables & live resources (LLM client) are
      NOT serialised (callables come back from the world definition / class).
    """
    STORE_TYPE: str

    def store_id(self) -> str: ...
    def save(self) -> dict: ...
    def load(self, data: Mapping[str, Any], ctx: Any) -> None: ...


class LLMClient(Protocol):
    def gen_narration_prompt(self, gs: Any, pl: Any) -> str: ...
    def clean_truncated_sentence(self, text: str) -> str: ...
    def narrate(self, gs: Any, pl: Any) -> str: ...
    def validate_llm_tools_schema(self, tools_list: Sequence[Mapping[str, Any]]) -> None: ...
    def parse_user_input_to_commands(self, user_input: str, game_context_for_tools: Mapping[str, Any]) -> list[Mapping[str, Any]]: ...


class PlayerDialogs(Protocol):
    """Interactive UI prompts the engine may need during a turn.

    The web GUI's WebDialogs satisfies this protocol. The engine depends on this
    port (not on WebDialogs) and receives a dialogs object per call, so it stays
    free of any GUI import.
    """
    async def ask_for_playername(self) -> str: ...
    async def ask_for_pin(self, expected_md5_hash: str) -> str: ...
    async def do_minigame(self) -> str: ...
    async def do_chat(self, gs: Any, pl: Any, whom: Any, firstmessage: str = "") -> Any: ...
    async def do_game_over(self, won: bool, text: str) -> None: ...
