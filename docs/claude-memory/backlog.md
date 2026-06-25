---
name: backlog
description: Planned/optional future work after the Steps 1-3 refactor (paused)
metadata: 
  node_type: memory
  type: project
  originSessionId: de4a68f5-57c9-4f86-9442-a2d5f29750d7
---

Future work, tracked in `docs/BACKLOG.md` (repo). Refactor Steps 1-3 are done and the
series is paused. See [[webserver-refactor-status]].

**NEXT after the pause (user's stated next task): unify file naming to snake_case.**
The repo mixes PascalCase modules (GameState.py, PlayerState.py, NPCDogState.py, …)
and snake_case (game_verbs.py, game_turn.py, services/…). Standardize on snake_case
module files; keep class names PascalCase. `git mv` + fix ALL imports incl. local
imports inside functions.
**Why:** user wants one consistent convention.
**How to apply / gotcha:** `data/world.json` + `create_world.py` reference callbacks
as strings ("GameApplyFunctions.o_xxx") resolved via the `module_map` in
`GameState.init_game` → `WorldLoader.resolve_func_from_string`. Renaming modules
requires updating those string prefixes AND/OR the module_map keys consistently, or
the world won't load. Also: macOS case-insensitive FS (use git mv carefully), clear
__pycache__, verify by play-through (no test suite).

**Later option (NOT next): optional shell/CLI interface.** The game was originally a
shell text-adventure; the GUI came later. Step 3 made GameState GUI-free
(PlayerDialogs port + web-session registry moved to the web layer), so a CLI
front-end could be added by implementing a console PlayerDialogs + a read-eval loop,
without touching the engine.

**Low-priority cleanups:** typed GameSession dataclass; retire flag-mirror shim
(__getattr__/__setattr__/FLAG_FIELDS, 13-file sweep); remove dead verbs
(verb_lookaround_old/llm) + emit_* dev helpers.
