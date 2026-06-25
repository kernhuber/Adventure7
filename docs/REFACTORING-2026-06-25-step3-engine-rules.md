# Refactoring: game rules → engine (Step 3)

**Date:** 2026-06-25
**Branch:** `Adventure10-2026-06-24-Zombie-Claude-refac`
**Scope:** Step 3 of the larger effort. Builds on Step 1
(`docs/REFACTORING-2026-06-24-webserver.md`) and Step 2
(`docs/REFACTORING-2026-06-25-gamestate.md`).
**Status:** Parts 1 (3.1–3.3) and 2 (3.4a–3.4b) **done**, plus follow-up
robustness fixes. The engine is now GUI-free.

---

## 1. Why

After Steps 1–2, several genuine **game rules still lived in the web layer**
(`webserver/command_engine.py`, `webserver/npc_runner.py`): the per-turn NPC moves,
the switch-timer countdown, and the thirst / turn-advance / game-over logic. The web
layer should only do I/O (parse input, drive dialogs, render); the rules belong in
the engine so they live in one place and are testable without the GUI.

Conversely, `GameState` still owns a **web-session registry** (an inward dependency
on the GUI). Moving that out is the second half of Step 3.

The agreed split (see the Step 1 doc) put the rule-relocation first, then the
trickier decoupling.

## 2. Part 1 — rules moved into the engine (DONE)

New mixin **`game_turn.py` → `GameTurnMixin`**, inherited by `GameState` alongside
`GameVerbsMixin`. MRO: `GameState → GameVerbsMixin → GameTurnMixin → object`.

| Commit | Sub-step | What moved from the web layer into `GameTurnMixin` |
|---|---|---|
| `ab45e2b` | 3.1 | `tick_switch_timers()` — control-room / generator-room switch countdown (was inline in `collect_npc_actions`). |
| `28b2b20` | 3.2 | `run_npc_turns(session_id)` — the full NPC-turn loop (dog/zombie/explosion move + execute, explosion cleanup, switch-timer tick), moved verbatim. `webserver/npc_runner.collect_npc_actions` is now a thin wrapper (error handling + refreshing `session["state"]`). |
| `fadf1eb` | 3.3 | `consume_thirst` / `evaluate_thirst` / `advance_time` — thirst decrement (system errors are free), the threshold warnings + verdursten→`game_over`, and the turn clock. `execute_single_command` calls these at the same points, preserving the exact ordering. |

### What deliberately stays in the web layer
The genuinely web/UI concerns: LLM input parsing, the command queue / `rest` /
pending-input loop, the interactive **dialogs** (pin-pad, mini-game, zombie-chat),
the game-over **presentation** (`do_game_over` + narration texts), serialization,
and NPC-action rendering. The demo-mode thirst path (operates on the serialized
dict, not a player object) is unchanged.

### Result
`GameState.py` 481 → 482 lines (it *gained* the small turn methods but the bulk had
already left in Step 2); the rules now live in `game_turn.py` (~169 lines).
`webserver/npc_runner.py` shrank to a thin wrapper (~132 lines).

### Verification
- Headless (stub LLM, no API key): `tick_switch_timers` (countdown + cooperative
  keeps switch on), `consume_thirst` (real −1 / system-error 0), `advance_time`
  (+1 / 0), `evaluate_thirst` at levels 20/10/5/7/0 (exact original strings +
  verdursten→game_over), and `run_npc_turns` end-to-end with no NPCs.
- Browser playthrough confirmed the LLM-dependent paths: blasting the rock
  (explosion branch + `felsen`), the main switch (`hauptschalter`), and waking the
  zombie (zombie branch of `run_npc_turns`).

## 3. Part 2 — Step 3.4 (DONE): decouple the engine from the GUI

Goal: remove the last inward dependency `GameState → WebDialogs` and move the
web-session registry out of the engine.

| Commit | Sub-step | What |
|---|---|---|
| `c88e064` | 3.4a | **`PlayerDialogs` port** (`services/interfaces.py`): `ask_for_pin`, `do_minigame`, `do_chat`, `do_game_over`, `ask_for_playername` — `WebDialogs` already satisfies it. `async_verb_interact` now takes an injected `dialogs` argument and calls `dialogs.do_chat(...)` instead of looking up `self.web_sessions[sid]["WebDialogs"]`. The three callers pass the session's dialogs (player interaction in `command_engine`; NPC interactions via `run_npc_turns`, forwarded by the `collect_npc_actions` wrapper). Stray `from WebDialogs import` in the verbs removed. |
| `5ef642c` | 3.4b | **Web-session registry removed from `GameState`.** Investigation showed it was largely *redundant*: the webserver's own `SessionManager` already holds per-session state; `active_minigames` was never populated (`start_minigame_session` had no callers, so `complete_minigame_session` was a no-op); and the three web-session context fields (`web_interface_active`, `active_web_sessions`, `minigames_active`) were written but never read. So this became a removal: drop those ContextBuilder fields, the `verb_context` web-status debug dump, and the 7 registry methods + the `web_sessions`/`active_minigames` dicts + the engine's `from WebDialogs import`. `register_client` now constructs `WebDialogs` itself. `cmd_q` stays (the web server sets `game.cmd_q` to a deque; `GameApplyFunctions` appends to it). |

End state: `GameState` is GUI-free and depends only on the `PlayerDialogs` protocol.
`PlayerState.cmd_q` is a separate legacy-CLI field and was not involved.

## 4. Follow-up robustness fixes (commit `51aa914`)

Prompted by a playthrough (a malformed Gemini tool-call crashed a move once; a
dog-chat hung on a 503 high-demand error):

1. **Dispatch hardening** (`verb_execute_json`): a malformed/unknown LLM tool-call
   (e.g. `gehe` without `direction`) no longer raises a raw `TypeError` to the
   player — it is logged, returns a clean rejection, and sets
   `self.last_command_was_system_error`.
2. **System errors must not cost a round** (`execute_single_command`): the bomb
   timer (3 rounds), the dog and the switch timers are round-driven, so NPC turns
   (`collect_npc_actions`) are now gated on `not is_system_error` (previously they
   ran even on a system error; time advance was already gated). A failed dispatch
   also refunds the pre-action thirst; LLM-parse failures flag their `zurueckweisen`
   with `is_system_error=True`.
3. **Transient-error retry on the chat path** (`GeminiInterface.simple_message`):
   retry 503 / 429 / 504 with a short backoff (1s, 2s) instead of returning empty.

## 5. Optional later cleanups (not scheduled)

- Retire the flag-mirror shim (`__getattr__`/`__setattr__`/`FLAG_FIELDS`) — wide
  (13-file) sweep.
- Convert web sessions to a typed `GameSession` dataclass.
- Remove dead verbs (`verb_lookaround_old`, `verb_lookaround_llm`) and the `emit_*`
  dev codegen helpers.
