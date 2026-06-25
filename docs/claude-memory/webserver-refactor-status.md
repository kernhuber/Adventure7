---
name: webserver-refactor-status
description: Status and plan of the multi-step refactor of web_backend_server.py and GameState
metadata: 
  node_type: memory
  type: project
  originSessionId: de4a68f5-57c9-4f86-9442-a2d5f29750d7
---

Multi-step refactor on branch `Adventure10-2026-06-24-Zombie-Claude-refac`.

**Step 1 (DONE, 2026-06-24, commits f3e7e66..82042e7):** split the 1245-line
`web_backend_server.py` into a `webserver/` package. Entry point kept as a thin
shim so `start.sh` is unchanged. Detailed write-up:
`docs/REFACTORING-2026-06-24-webserver.md`. See [[webserver-architecture]].

**Remaining web-layer polish:** sessions are still plain dicts; converting them to
a typed `GameSession` dataclass (~50 access sites, mostly in command_engine) was
deferred because it couldn't be runtime-verified during the work. `SessionManager`
is dict-compatible to make that conversion clean later.

**Step 2 (DONE 2026-06-25, commits 479708b, 9099156, c76e0ed):** GameState.py
1234 -> 481 lines. 2.1 extracted `services/world_loader.py` (`WorldLoader`: world.json
load/validate/build into WorldModel). 2.2 extracted `game_verbs.py`
(`GameVerbsMixin`: verb_execute_json + all verb_*); `class GameState(GameVerbsMixin)`.
2.4 deleted dead `check_game_over_old`. Existing collaborators (services/world.py:
WorldModel/GameFlags/ContextBuilder) unchanged. Verified by instantiating GameState
with a stub LLM (no API key) + dispatching LLM-free verbs. Scope decisions: keep the
flag-mirror shim; defer the web-session registry to Step 3. Browser play-through with
the real API key still recommended to confirm LLM-driven verbs.

**Step 3 part 1 (DONE 2026-06-25, commits ab45e2b, 28b2b20, fadf1eb):** game rules
moved into the engine via new `game_turn.py` `GameTurnMixin`
(`class GameState(GameVerbsMixin, GameTurnMixin)`). 3.1 `tick_switch_timers`;
3.2 `run_npc_turns(session_id)` (NPC loop moved verbatim; `collect_npc_actions` now a
thin web wrapper); 3.3 `consume_thirst`/`evaluate_thirst`/`advance_time`. Web layer
keeps dialogs, game-over presentation, serialization. Verified headless + browser
playthrough (explosion/felsen, hauptschalter, zombie). Doc:
`docs/REFACTORING-2026-06-25-step3-engine-rules.md`.

**Step 3.4 (DONE 2026-06-25, commits c88e064, 5ef642c):** 3.4a added a
`PlayerDialogs` Protocol (services/interfaces.py) and inject `dialogs` into
`async_verb_interact` instead of `self.web_sessions[...]`. 3.4b removed the
web-session registry from GameState (it was redundant: webserver SessionManager
already holds per-session state; active_minigames never populated; the 3 context
fields never read) — dropped those ContextBuilder fields, verb_context debug dump,
the 7 registry methods + web_sessions/active_minigames dicts + `from WebDialogs import`;
register_client now builds WebDialogs itself. cmd_q stays (web sets game.cmd_q to a
deque; GameApplyFunctions appends). **Engine is now GUI-free.**

**Robustness fixes (DONE 2026-06-25, commit 51aa914):** (1) verb_execute_json
catches malformed/unknown tool-calls -> clean reject + sets
self.last_command_was_system_error (no raw TypeError to player). (2) System errors no
longer cost a round: collect_npc_actions gated on `not is_system_error` (bomb/dog/
switch are round-driven); failed dispatch refunds thirst; LLM-parse failures flag
is_system_error=True. (3) GeminiInterface.simple_message retries 503/429/504 with
backoff. Confirmed by playthrough that the 2 issues were external Gemini behavior
(fallback tool-call + 503), not refactor regressions.

**Optional later:** typed GameSession dataclass; retire flag-mirror shim; remove dead
verbs (verb_lookaround_old/llm) + emit_* dev helpers; reduce redundant narrate calls
(serialize_real_game_state narrates each call, ~8x/session).

**Why:** the user explicitly wants to refactor GameState too.
**How to apply:** agreed ordering is to refactor GameState *before* migrating
rules into it, so rules land in their final home (not moved twice). Each sub-step
should stay one bisectable commit; verify by play-through since there is no test
suite. See [[game-runtime-notes]].
