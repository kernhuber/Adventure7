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

**DONE 2026-06-26 — snake_case file-naming unification.** All 20 PascalCase module
files renamed to snake_case (classes kept PascalCase: game_state.py defines class
GameState). Updated all imports, the 4 bare-module qualifier files
(sys_test/server→utils, web_dialogs→player_state/npc_zombie_state/game_state,
npc_zombie_state→game_state), the module_map keys in game_state.py + create_world.py,
and the data/world.json callback prefixes (all consistent → world loads, callbacks
resolve, server graph imports). NB create_world.py has a PRE-EXISTING unrelated syntax
error (unclosed { ~line 416) and does not compile — not runtime-relevant.

**Later option (NOT next): optional shell/CLI interface.** The game was originally a
shell text-adventure; the GUI came later. Step 3 made GameState GUI-free
(PlayerDialogs port + web-session registry moved to the web layer), so a CLI
front-end could be added by implementing a console PlayerDialogs + a read-eval loop,
without touching the engine.

**Low-priority cleanups:** typed GameSession dataclass; retire flag-mirror shim
(__getattr__/__setattr__/FLAG_FIELDS, 13-file sweep); remove dead verbs
(verb_lookaround_old/llm) + emit_* dev helpers.
