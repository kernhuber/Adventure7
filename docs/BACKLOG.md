# Backlog — future work (not yet scheduled)

Captured ideas, partly done, partly open. **Re-checked against the code on 2026-11-11** — items are tagged
✅ DONE / OPEN below; older notes keep their original wording as history. Steps 1–3 of the refactoring series are
done (`docs/REFACTORING-*.md`); the agent player is implemented (`docs/AGENT-SPIELER-erklaert.md`).

---

## DONE (2026-07-01) — Save / Load (whole-game serialization)

Implemented per `docs/SAVE-LOAD-DESIGN.md`. Core in `services/save_load.py` (Storable
registry, `save_game`/`load_game`, `save_to_file`/`load_from_file`); `save()`/`load()` on
GameState, the players/NPCs (incl. the zombie/dog memory), objects, ways, and
GeminiInterface (caches only). Web: text commands `speichere`/`lade` + GUI buttons and a
named-slot modal. Saves live under `saves/<name>.json` (gitignored). Round-trip +
idempotency tested; the LLM scene-identity after load is verified in the browser.

Persist and restore a full game to/from a single JSON file — **not just the flags**, but
the complete state of `GameState` and every player/NPC.

Design (per the author):
- Each player/NPC class gets its own **`save()` / `load()`** methods — and these are
  declared in the **(duck-type) interface** (`services/interfaces.py`) so every actor
  is expected to implement them. The Zombie/Dog must persist their full state, e.g. the
  **Notizbuch (`notes`)**, `last_chat`, `trust`, `zombie_state`, `zombie_thirst`,
  `dog_state`, etc. — not only the global flags.
- A **saver** walks `GameState` (flags via `GameFlags`, time, ways' visibility, object
  states/locations, …) and calls each player's `save()`, collects everything, and
  writes one JSON file. A **loader** does the inverse: rebuild `GameState`, then hand
  each actor its slice via `load()`.
- The saver/loader only orchestrate; the per-actor detail lives in the actors' methods.

Watch-outs: object visibility/`ownedby`/`hidden` and **way `visible`** are mutated at
runtime (doors, the wagon, the poster) — they must be saved, not just regenerated from
`world.json`. Cross-references (a player's `location`, an object's `ownedby`) need to be
serialized by id and re-linked on load.

## Near-term — understand & document the zombie NPC

`npc_zombie_state.py` was written autonomously by Claude Code and is LLM-driven; the
author wants to understand how it works (states, the reasoning prompt, transitions,
redemption). **Explainer written: `docs/ZOMBIE-NPC-erklaert.md`** (walkthrough along
the three guiding questions, with patterns and discussion points).

Possible follow-ups raised there — ✅ all done: the dead DORMANT/STALKING states are gone, the cooperation is a
graded `trust` value, and the zombie is LLM-driven in COOPERATIVE/DOUBTING/CONVINCED too (see
`docs/ZOMBIE-NPC-erklaert.md`).

**Design intention (the teacher's question):** can an LLM make intelligent in-game
decisions, drive a character that learns / decides for itself / realises the game can
only be won in **cooperation** with the player (HUNTING → COOPERATING/REDEEMED), and
still be a good, entertaining character? Keep the zombie LLM-driven, persuadable, and
legible. See `docs/GAMEPLAY-2026-06-27.md`.

---

## Near-term — `gib`-Verb: open NPC-reaction cases (2026-07-11)

The `gib <obj> an <NPC>` verb + reactions are implemented via a `gets_given(gs, pl, obj)`
hook on each NPC (dog: food → distracted a few turns, else drop silently; zombie: thanks +
`trust += GIFT_TRUST_BONUS`, and `o_manual` → CONVINCED). Still open:

- ✅ **DONE (3c2828e) — Zombie drops ALL items on redemption** (not just the EC card), so gifts
  can be reclaimed. Only the redemption **GUI animation** is still an open TODO in
  `NPCZombieState._do_redemption`.
- **Case 2 — zombie gives the player something** (no engine path yet; `gib` is player→NPC
  only). Future uses: the zombie placates the player with an item (not the EC card), or hands
  over the **EC card on the correct success path** instead of dropping it on the floor.
- Balancing: is `GIFT_TRUST_BONUS = 20` right? A gift shouldn't trivially flip HUNTING →
  COOPERATIVE, but should be a meaningful de-escalation nudge.

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
turn methods. **Not the next step** — just enabled by the current architecture. (The agent player already
proves the port: `agent_player/dialogs.py` `AgentDialogs` is a second `PlayerDialogs` implementation.)

---

## Optional cleanups (low priority)

- Convert web sessions to a typed `GameSession` dataclass (the webserver
  `SessionManager` is already dict-compatible to make this clean).
- Retire the flag-mirror shim in `GameState` (`__getattr__`/`__setattr__`/
  `FLAG_FIELDS`) so code uses `get_flags()`/`_flags` directly — wide (13-file) sweep.
- OPEN (partly done): remove the dead verbs and the `emit_*` dev codegen helpers. `verb_lookaround_llm` is gone;
  `verb_lookaround_old` (`game_verbs.py`) and `emit_waydefs`/`emit_objdefs` (`game_state.py`) still exist.
- `create_world.py` — ✅ it **compiles again** (`py_compile` ok, 2026-11-11; it had an unclosed `{` near line 416).
  Whether it still regenerates a correct `world.json` is unverified. Not used at runtime (the game loads the
  committed `data/world.json`).


---

## Agent player — open ideas (2026-11-11)

The agent player itself is done (`docs/AGENT-SPIELER-erklaert.md`). Possible follow-ups, none scheduled:

- A second model provider (e.g. Claude via the Anthropic API) as another `AgentLLM` implementation in
  `agent_player/llm.py` — for comparing models.
- A small script that prints a JSONL trace (`agent_runs/*.jsonl`) as readable text for course material
  (planned as `spur_anzeigen.py`, not built).
- Consolidating `Experience.md` (it only grows; the prompt shows the newest 6000 characters).
- Ambiguous call-names (several objects called "Schalter") are resolved via the first call-name the agent sees.
- Spectator broadcast (several browsers watching one session) — the design chose "one browser = game + spectator".
