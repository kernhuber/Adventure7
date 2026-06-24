---
name: webserver-architecture
description: Module layout and key design decisions of the webserver/ package
metadata: 
  node_type: memory
  type: reference
  originSessionId: de4a68f5-57c9-4f86-9442-a2d5f29750d7
---

`webserver/` package (Step 1 refactor). `web_backend_server.py` is a 10-line shim
that delegates to `webserver.run_working_adventure`.

Modules: `server.py` (wiring + register/unregister/send/handle_client/start_*),
`command_engine.py` (`CommandEngineMixin`: handle_command, execute_single_command),
`npc_runner.py` (`NPCRunnerMixin`: collect_npc_actions, handle_minigame_result,
switch-timer), `serialization.py`, `demo.py`, `http_server.py`, `session.py`
(`SessionManager`), `game_modules.py` (`GAME_MODULES_AVAILABLE`+GameState/PlayerState),
`texts.py`, `__init__.py`.

Key decisions:
- The command/NPC code is **mixins** so method bodies stayed byte-for-byte; MRO is
  `WebAdventureServer(CommandEngineMixin, NPCRunnerMixin)`.
- `__init__.py` exports `WebAdventureServer`/`run_working_adventure` **lazily**
  (PEP 562 `__getattr__`) so leaf modules import without the google/LLM stack.
- `game_modules.py` holds the shared optional import to avoid a circular import
  between server.py and the mixins.
- Sessions are dicts; per-session `session["web_dialogs"]` replaced the old
  server-wide `self.wd` (that was a cross-session bug). See [[webserver-refactor-status]].
