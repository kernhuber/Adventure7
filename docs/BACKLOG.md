# Backlog — future work (not yet scheduled)

Captured ideas for after the current refactoring series (Steps 1–3 done; see the
`docs/REFACTORING-*.md` files). Nothing here is in progress.

---

## ✅ DONE (2026-06-26) — unify naming convention to snake_case

All 20 PascalCase module files were renamed to snake_case (classes kept PascalCase);
all imports, the bare-module qualifier usages, the `module_map` registry keys, and
the `data/world.json` callback prefixes were updated consistently. Verified: world
loads and callbacks resolve, full server graph imports. (`create_world.py` remains
broken by a pre-existing, unrelated syntax error — see cleanups below.)

The original plan, for reference:

The codebase mixed two file/module naming styles: **PascalCase** (`GameState.py`,
`PlayerState.py`, …) and **snake_case** (`game_verbs.py`, `game_turn.py`,
`web_backend_server.py`, `services/…`). Standardize on **snake_case for module
files** (PEP 8), keeping **class names in PascalCase** (e.g. module `game_state.py`
still defines `class GameState`).

**Files to rename (PascalCase → snake_case), classes unchanged:**
`GameState.py`→`game_state.py`, `PlayerState.py`→`player_state.py`,
`NPCDogState.py`→`npc_dog_state.py`, `NPCZombieState.py`→`npc_zombie_state.py`,
`ExplosionState.py`→`explosion_state.py`, `GameObject.py`→`game_object.py`,
`GameApplyFunctions.py`→`game_apply_functions.py`,
`GameTakeFunctions.py`→`game_take_functions.py`,
`GameRevealFunctions.py`→`game_reveal_functions.py`,
`GameObstructionCheckFunctions.py`→`game_obstruction_check_functions.py`,
`ObjectPrompts.py`→`object_prompts.py`, `PlacePrompts.py`→`place_prompts.py`,
`WayPrompts.py`→`way_prompts.py`, `Place.py`→`place.py`, `Way.py`→`way.py`,
`PopulateLibrary.py`→`populate_library.py`, `Utils.py`→`utils.py`,
`GeminiInterface.py`→`gemini_interface.py`, `WebDialogs.py`→`web_dialogs.py`,
`SysTest.py`→`sys_test.py`.

**Approach:** `git mv` each file, then update every `import`/`from … import` —
including the many **local imports inside functions/methods** (e.g.
`from NPCDogState import NPCDogState` inside `game_verbs`/`game_turn`), not just
module-top imports.

**⚠️ Gotchas to handle:**
- **World callback strings.** `data/world.json` and `create_world.py` reference
  callbacks as strings like `"GameApplyFunctions.o_xxx"`, resolved by
  `services/world_loader.WorldLoader.resolve_func_from_string` via the `module_map`
  built in `GameState.init_game`. After renaming the modules, either update those
  string prefixes **and** the `module_map` keys consistently, or keep the
  `module_map` keys as the old names mapping to the renamed modules. Pick one and be
  consistent, or the world will fail to load.
- **macOS case-insensitive filesystem.** A rename that only changes case (e.g.
  `Utils.py`→`utils.py`) can confuse git on macOS; use `git mv` (two-step via a temp
  name if needed).
- **`__pycache__`** holds stale `.pyc` under old names — clear it after renaming.
- Do it as **one focused PR/commit per logical group**, verify imports compile and
  the app starts after each, since there is no automated test suite.

This is mechanical but wide (touches nearly every file's imports). Keep behavior
identical; verify with a play-through.

---

## Later option — optional shell (CLI) interface

The game began as a shell text-adventure; the web GUI was added later. Now that
`GameState` is **GUI-free** (Step 3: no `WebDialogs` import; interaction goes through
the `PlayerDialogs` port, and the web-session registry lives in the web layer), a
**CLI front-end could be offered again** without touching the engine: implement a
console `PlayerDialogs` (ask_for_pin/do_minigame/do_chat/do_game_over/
ask_for_playername via stdin/stdout) and a simple read-eval loop calling the engine's
turn methods. **Not the next step** — just enabled by the current architecture.

---

## Optional cleanups (low priority)

- Convert web sessions to a typed `GameSession` dataclass (the webserver
  `SessionManager` is already dict-compatible to make this clean).
- Retire the flag-mirror shim in `GameState` (`__getattr__`/`__setattr__`/
  `FLAG_FIELDS`) so code uses `get_flags()`/`_flags` directly — wide (13-file) sweep.
- Remove dead verbs (`verb_lookaround_old`, `verb_lookaround_llm`) and the `emit_*`
  dev codegen helpers in `game_state` / `game_verbs`.
- Fix `create_world.py` — the world-definition dev tool has a pre-existing syntax
  error (unclosed `{` near line 416) and does not compile. Not used at runtime (the
  game loads the committed `data/world.json`), but it should be repaired if world
  regeneration is needed.
