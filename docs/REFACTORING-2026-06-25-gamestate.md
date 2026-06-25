# Refactoring: `GameState.py` decomposition (Step 2)

**Date:** 2026-06-25
**Branch:** `Adventure10-2026-06-24-Zombie-Claude-refac`
**Scope:** Step 2 of the larger effort. Builds on Step 1
(`docs/REFACTORING-2026-06-24-webserver.md`). Step 3 is planned, not started.

---

## 1. Why

After Step 1 split the web backend, `GameState.py` was the next monolith:
**1234 lines** mixing world construction, the verb/command engine, flags, win/lose
logic, and a web-session registry.

A partial decomposition **already existed** in `services/world.py` and signalled the
intended direction — `GameState` should become a thin coordinator that wires
collaborators:

- `WorldModel` (`self._world`) — holds `places`/`ways`/`objects` + name lookup +
  `find_shortest_path`; `GameState` already exposed these via properties.
- `GameFlags` (`self._flags`) — structured flag container; ~25 flags are **mirrored**
  into it through a `__getattr__`/`__setattr__` + `FLAG_FIELDS` shim so legacy
  `gs.hauptschalter`-style access keeps working.
- `ContextBuilder` (`self._context`) — builds the LLM context.

Step 2 continued in that direction.

## 2. Result at a glance

`GameState.py`: **1234 → 481 lines.** New modules:

| Module | Lines | Responsibility |
|---|---|---|
| `services/world_loader.py` | ~307 | `WorldLoader`: load `data/world.json`, resolve dotted callback refs to callables, validate, build Place/Way/GameObject into a `WorldModel` |
| `game_verbs.py` | ~457 | `GameVerbsMixin`: `verb_execute_json` (dispatch table) + all ~25 `verb_*` handlers |

`GameState` now wires: `WorldModel`, `GameFlags`, `ContextBuilder` (pre-existing),
`WorldLoader` (used in `init_game`), and inherits `GameVerbsMixin`. It still owns
runtime state (`players`, `time`, `llm`, `gamelog`, flags) and — for now — the
web-session registry (see §5).

## 3. Sub-steps (each one bisectable commit)

| Commit | Sub-step | Summary |
|---|---|---|
| `479708b` | 2.1 | Extract `WorldLoader`. Moved `_resolve_func_from_string`, `_maybe_load_world_from_json` → `load`, `_validate_world_defs` → `validate`, `_init_places/_ways/_objects`, and `from_definitions` → `WorldLoader.build`. `init_game` now delegates to `WorldLoader`. |
| `9099156` | 2.2 | Extract `GameVerbsMixin` (`verb_execute_json` + all `verb_*`) into `game_verbs.py`; `class GameState(GameVerbsMixin)`. Method bodies byte-for-byte unchanged. |
| `c76e0ed` | 2.4 | Delete dead `check_game_over_old` (no caller; superseded by `check_game_over`). |

(2.3 — moving the web-session registry out of `GameState` — was deliberately
deferred to Step 3; see §5.)

## 4. Design notes

### 4.1 `WorldLoader` — pure construction
World *construction* (JSON → objects) is separated from `WorldModel` (which *holds*
the built world). `WorldLoader` touches no LLM and no runtime state, so it is
unit-testable standalone. `init_game` now reads:

```python
from services.world_loader import WorldLoader
loader = WorldLoader()
external_defs = loader.load(module_map)         # data/world.json -> defs (resolved)
...
loader.validate(place_defs, way_defs, object_defs)
loader.build(self._world, place_defs, way_defs, object_defs)
```

The methods were `GameState`-internal (only a stale doc comment in `create_world.py`
referenced one — updated), so no backward-compat wrappers were needed.

### 4.2 `GameVerbsMixin` — mixin, not free functions
Same approach as Step 1's `CommandEngineMixin`/`NPCRunnerMixin`: the verbs call each
other and reach deeply into `self` (world, flags, players, llm, context,
web-sessions), so extracting them as a **mixin** keeps the method bodies unchanged
and behaviour identical by construction. MRO: `GameState -> GameVerbsMixin -> object`.
`NPCDogState` / `pprint` / `WebDialogs` / `asyncio` stay **locally imported** inside
the methods to avoid an import cycle with `GameState`.

## 5. Scope decisions (deliberately out of Step 2)

1. **The flag-mirror shim stays.** `gs.<flag>` reads are spread across **13 files**
   (every game-logic module + NPCs + apply/take/reveal/obstruction functions).
   Removing `__getattr__`/`__setattr__`/`FLAG_FIELDS` would be a wide, risky sweep
   with no automated tests — a separate optional cleanup.
2. **The web-session registry stays in `GameState` for now.** `register/unregister_web_session`,
   `start/complete_minigame_session`, `web_sessions`/`cmd_q`/`active_minigames`,
   `get_session_id_for_player` (and the inward `from WebDialogs import WebDialogs`)
   are a web-layer concern, but `async_verb_interact` and the verbs are entangled
   with `session_id`/`web_sessions`. This shares Step 3's engine↔web boundary, so it
   is handled there.
3. **`emit_waydefs`/`emit_objdefs`** (dev codegen helpers) and possibly-dead verbs
   (`verb_lookaround_old`, `verb_lookaround_llm`) were left in place — not in scope.

## 6. Verification

With `google-genai` now installed, `GameState` can be constructed without an API key
by passing a **stub LLM** (`GameState(llm=StubLLM())` — `init_game` only builds a real
`GeminiInterface` when `llm is None`, and no LLM calls happen during init). Verified:

- ✅ `WorldLoader` builds the real `data/world.json` standalone: 20 places, 52 ways,
  36 objects; `p_start` present with 3 ways; callbacks resolved.
- ✅ `GameState()` constructs end-to-end through the rewired `init_game`; flags and
  name lookups work.
- ✅ Verb dispatch through the real `vtab`: `hilfe`, `inventory`, `ablegen`, and an
  unknown verb all behave correctly; flag access still flows through the shim.
- ✅ `check_game_over()` still returns a bool.

**Still recommended:** a browser play-through with a real `GOOGLE_API_KEY` to confirm
the **LLM-driven** verbs (`verb_walk`/`verb_examine`/`verb_context` → narration/context,
`async_verb_interact`, `verb_apply` with `apply_f` callbacks), which the headless
checks do not exercise. The mixin preserves bodies verbatim, so risk is low.

## 7. Next steps (Step 3, not started)

- Move game rules from the web layer into the engine: `collect_npc_actions`, the
  per-turn switch-timer countdown, and the thirst/turn-advance/game-over logic
  currently in `webserver/command_engine.execute_single_command`.
- Move the **web-session registry** out of `GameState` toward the webserver
  `SessionManager` (the deferred 2.3). These two share the engine↔web boundary.
- Optional later cleanups: retire the flag-mirror shim; remove dead verbs and the
  `emit_*` dev helpers; convert web sessions to a typed `GameSession` dataclass.
