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

**Game engine (root):** `GameState.py` (~481 lines — a coordinator after the Step 2
split) wires `WorldModel`/`GameFlags`/`ContextBuilder` (`services/world.py`),
`WorldLoader` (`services/world_loader.py`, builds the world from `data/world.json`),
and inherits `GameVerbsMixin` (`game_verbs.py`, the `verb_*` command engine). Plus
`PlayerState.py`, `NPCDogState.py`, `NPCZombieState.py`, `ExplosionState.py`,
`GeminiInterface.py` (LLM), `Utils.py` (logging via `dprint(dl.…, …)`, flags like
`GHOSTMODE`/`NODOG`). The browser front-end is in `web/`.

Note: `GameState()` builds a real `GeminiInterface` only when `llm is None`; pass a
stub (`GameState(llm=object())`) to construct it without an API key for tests.

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

Step 1 (web-layer split), Step 2 (`GameState` decomposition), and **Step 3**
(game rules → engine via `game_turn.py` `GameTurnMixin`; `PlayerDialogs` port; web-session
registry removed from `GameState`) are **done** — the engine is now GUI-free.
Follow-up robustness fixes are in: malformed tool-calls fail soft, system errors no
longer cost a round (NPC turns gated on `not is_system_error`), and the chat path
retries 503s.

Optional later cleanups: typed `GameSession` dataclass; retire the flag-mirror shim;
remove dead verbs / `emit_*` dev helpers. Details:
`docs/REFACTORING-2026-06-24-webserver.md` (Step 1),
`docs/REFACTORING-2026-06-25-gamestate.md` (Step 2),
`docs/REFACTORING-2026-06-25-step3-engine-rules.md` (Step 3 + robustness).
