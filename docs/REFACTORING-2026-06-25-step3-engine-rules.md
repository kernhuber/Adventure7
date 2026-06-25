# Refactoring: game rules → engine (Step 3)

**Date:** 2026-06-25
**Branch:** `Adventure10-2026-06-24-Zombie-Claude-refac`
**Scope:** Step 3 of the larger effort. Builds on Step 1
(`docs/REFACTORING-2026-06-24-webserver.md`) and Step 2
(`docs/REFACTORING-2026-06-25-gamestate.md`).
**Status:** Part 1 (3.1–3.3) **done**. 3.4 **planned, not started**.

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

## 3. Part 2 — Step 3.4 (planned, NOT started)

Goal: remove the last inward dependency `GameState → WebDialogs` and move the
web-session registry out of the engine.

The knot: the engine still reaches into `self.web_sessions[session_id]["WebDialogs"]`
inside `async_verb_interact` (game_verbs.py), and the moved turn methods rely on that
registry being present on `GameState`.

Planned moves:
1. **Define a `PlayerDialogs` port** (a `Protocol` in `services/interfaces.py`) with
   `ask_for_pin`, `do_minigame`, `do_chat`, `do_game_over`, `ask_for_playername`.
   `WebDialogs` already satisfies it.
2. **Inject dialogs instead of looking them up.** `async_verb_interact` (and any
   turn method that needs interaction) takes a `dialogs` argument instead of
   reaching into `web_sessions`. The engine depends on the *protocol*, not on
   `WebDialogs`; drop the `from WebDialogs import …` from the engine.
3. **Move the web-session registry to the web layer.** `register/unregister_web_session`,
   `is_web_interface_active`, `start/complete_minigame_session`, `debug_web_status`,
   `get_session_id_for_player`, and the `web_sessions` / `active_minigames` / `cmd_q`
   dicts move out of `GameState` into the webserver `SessionManager`.

Why it is a separate, higher-risk step: unlike 3.1–3.3 (verbatim relocations), 3.4
**changes method bodies** (the dialog seam) and touches ~6 files
(`game_verbs.py`, `GameState.py`, `services/interfaces.py`,
`webserver/{server,command_engine,npc_runner,session}.py`). It must be validated
with a live playthrough (pin-pad, mini-game, zombie-chat, game-over).

Note: `PlayerState.cmd_q` is its own legacy-CLI field and is **not** part of the
registry move.

## 4. Optional later cleanups (not scheduled)

- Retire the flag-mirror shim (`__getattr__`/`__setattr__`/`FLAG_FIELDS`) — wide
  (13-file) sweep.
- Convert web sessions to a typed `GameSession` dataclass.
- Remove dead verbs (`verb_lookaround_old`, `verb_lookaround_llm`) and the `emit_*`
  dev codegen helpers.
