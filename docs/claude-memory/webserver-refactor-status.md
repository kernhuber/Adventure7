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

**Step 3 (NOT STARTED):** move game rules out of the web layer into the engine
(`collect_npc_actions`, switch-timer countdown, thirst/turn/game-over logic from
`execute_single_command`); and move the web-session registry OUT of GameState
(register/unregister/minigame-session, web_sessions/cmd_q) toward the webserver
SessionManager. These share the engine<->web boundary.

**Why:** the user explicitly wants to refactor GameState too.
**How to apply:** agreed ordering is to refactor GameState *before* migrating
rules into it, so rules land in their final home (not moved twice). Each sub-step
should stay one bisectable commit; verify by play-through since there is no test
suite. See [[game-runtime-notes]].
