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

**Step 3.4 (NOT STARTED):** introduce a `PlayerDialogs` Protocol
(services/interfaces.py); inject `dialogs` into `async_verb_interact` instead of
`self.web_sessions[sid]["WebDialogs"]`; move the web-session registry
(register/unregister/minigame-session, web_sessions/active_minigames/cmd_q,
get_session_id_for_player, debug_web_status) OUT of GameState into the webserver
SessionManager; drop the engine's `from WebDialogs import`. Changes method bodies +
~6 files -> higher risk, validate with live playthrough. NB PlayerState.cmd_q is a
separate legacy-CLI field, not part of this move.

**Why:** the user explicitly wants to refactor GameState too.
**How to apply:** agreed ordering is to refactor GameState *before* migrating
rules into it, so rules land in their final home (not moved twice). Each sub-step
should stay one bisectable commit; verify by play-through since there is no test
suite. See [[game-runtime-notes]].
