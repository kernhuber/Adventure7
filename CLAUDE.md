# CLAUDE.md — project guide for Claude Code

A German-language text-adventure game with a browser GUI, driven by an LLM
(Google Gemini) for scene narration, command parsing, and NPC behaviour.

## How to run

```bash
./start.sh        # sources .apikey -> exports GOOGLE_API_KEY, activates venv,
                  # runs `python3 ./web_backend_server.py`, opens the browser
```

`web_backend_server.py` is a thin **entry-point shim**; the implementation lives in
the `webserver/` package. Do not move the shim — `start.sh`/`start.bat` and
PyInstaller depend on this path.

Note: `start.sh` only runs `pip install -r requirements.txt` when `venv/` is
absent. The project uses the new unified SDK **`google-genai`** (`from google import
genai`); if a stale venv has the old `google-generativeai` instead, install
`google-genai` manually.

## Architecture

**Web backend — `webserver/` package** (split out of a 1245-line monolith; see
`docs/REFACTORING-2026-06-24-webserver.md`):

- `server.py` — `WebAdventureServer`: wiring + session/client lifecycle. Inherits
  `CommandEngineMixin` and `NPCRunnerMixin` (MRO:
  `WebAdventureServer -> CommandEngineMixin -> NPCRunnerMixin -> object`).
- `command_engine.py` — `handle_command`, `execute_single_command` (the core loop:
  per-session command queue, the LLM "rest" continuation, pending input, thirst,
  turn advance, game-over, pinpad).
- `npc_runner.py` — `collect_npc_actions`, `handle_minigame_result`, switch-timer.
- `serialization.py` — `serialize_real_game_state` (GameState -> GUI JSON).
- `demo.py` — demo-mode fallbacks (used when game modules / LLM are unavailable).
- `http_server.py`, `session.py` (`SessionManager`), `game_modules.py`
  (`GAME_MODULES_AVAILABLE`), `texts.py`, `__init__.py` (lazy PEP-562 exports).

`webserver/__init__.py` imports the server **lazily** so leaf modules can be
imported/tested without pulling in the google/LLM stack.

**Game engine (root):** `GameState.py` (~1234 lines — next refactor target),
`PlayerState.py`, `NPCDogState.py`, `NPCZombieState.py`, `ExplosionState.py`,
`GeminiInterface.py` (LLM), `Utils.py` (logging via `dprint(dl.…, …)`, flags like
`GHOSTMODE`/`NODOG`). The browser front-end is in `web/`.

## LLM / model notes

- Models (`GeminiInterface.py`): `gemini-2.5-flash-lite` (text / command parsing),
  `gemini-2.5-flash` (NPC reasoning).
- If **tool/function calls** misbehave, suspect the request/response shape
  differing between the old and new google SDK before suspecting model IDs. Code:
  `GeminiInterface.parse_user_input_to_commands` and the `generate_content(...)`
  calls.

## Conventions

- **No automated test suite.** Verify changes by importing modules
  (`./venv/bin/python3 -m py_compile …`) and by a browser play-through. Leaf
  `webserver/` modules import standalone for quick checks.
- Keep refactors in **small, bisectable commits**; do not change behaviour while
  relocating code.
- Without `GOOGLE_API_KEY`, connecting falls back to **demo mode** cleanly.
- Commit/push only when asked. Default working branch for this effort:
  `Adventure10-2026-06-24-Zombie-Claude-refac`. Remote: `kernhuber/Adventure7`.

## Status & next steps

Step 1 (web-layer split) is **done**. Planned: convert sessions to a typed
`GameSession` dataclass; **Step 2** refactor `GameState.py`; **Step 3** move game
rules (NPC turns, thirst/turn/game-over) from the web layer into the engine.
Agreed ordering: refactor `GameState` *before* migrating rules into it. Details:
`docs/REFACTORING-2026-06-24-webserver.md`.
