# CLAUDE.md — project guide for Claude Code

A German-language text-adventure game with a browser GUI, driven by an LLM
(Google Gemini) for scene narration, command parsing, and NPC behaviour.

## Purpose (important context)

This is **teaching material**, not a product. It is used in courses on: Python; "Python
programming with AI" (Gemini); and using a coding assistant (Claude Code). It also
contains some JavaScript (the `web/` front-end). Optimize for **clarity and
explainability** over cleverness — code is meant to be read and understood by
learners. The author (Chris) wrote the dog NPC himself (with help from ChatGPT and
Gemini); the **zombie NPC was written autonomously by Claude Code**, so the author
wants to understand how it works.

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

**Game engine (root):** `game_state.py` (~481 lines — a coordinator after the Step 2
split) wires `WorldModel`/`GameFlags`/`ContextBuilder` (`services/world.py`),
`WorldLoader` (`services/world_loader.py`, builds the world from `data/world.json`),
and inherits `GameVerbsMixin` (`game_verbs.py`, the `verb_*` command engine). Plus
`player_state.py`, `npc_dog_state.py`, `npc_zombie_state.py`, `explosion_state.py`,
`gemini_interface.py` (LLM), `utils.py` (logging via `dprint(dl.…, …)`, flags like
`GHOSTMODE`/`NODOG`). The browser front-end is in `web/`.

Module files are snake_case; class names stay PascalCase (e.g. `game_state.py`
defines `class GameState`).

Note: `GameState()` builds a real `GeminiInterface` only when `llm is None`; pass a
stub (`GameState(llm=object())`) to construct it without an API key for tests.

**NPCs.** Both NPCs subclass `PlayerState` and expose `NPC_game_move(gs)` which the
engine runs once per turn (`GameState.run_npc_turns`, called from the web layer).
- `npc_dog_state.py` — a hand-written **finite state machine** (`DogState`:
  START/EATING/ATTACK/TRACE/GOHOME); attacks trigger a mini-game.
- `npc_zombie_state.py` — Claude-authored, then reworked (2026-06-29) into a richer
  arc (Harald Kronstein). State machine `ZombieState`:
  AWAKENING/HUNTING/COOPERATIVE/DOUBTING/CONVINCED/REDEEMED/PETRIFIED. **HUNTING** moves
  are decided by an **LLM reasoning call** (`gemini-2.5-flash`, notebook pattern + bite);
  the cooperative states are **scripted** (cheap). A graded `trust` value drives
  COOPERATIVE↔DOUBTING↔HUNTING; a hostile chat or `verb_attack` erodes it. The
  **operations manual** (`o_manual` in the control room) is the solution key: reading it
  (himself via a U-Bahn "memory" route, or the player reading it next to him) makes him
  CONVINCED, after which he pursues the player to win their buy-in for the two-switch
  redemption. Life energy (the old `zombie_thirst`) drains each turn; he can ask to
  share it, and at 0 he PETRIFIES (EC card destroyed → game lost). Awoken by taking the
  wallet (`game_take_functions._awaken_zombie`); on AWAKENING it opens the chat modal.
  Player-visible story beats use the `zombie_event` action (→ "Letzte Aktion");
  `zombie_message` is debug-only. See `docs/ZOMBIE-NPC-erklaert.md`.
NPCs can talk to the player via the `interaktion` action → `async_verb_interact` →
`PlayerDialogs.do_chat` → the chat modal.

**Web front-end (`web/`).** `Adventure9.html` (served via `index.html` redirect) +
plain JS. `websockets.js` is the core: it owns the WebSocket, dispatches server
messages (`game_state`, `command_result`, `npc_actions`, `start_minigame`,
`zombie_chat`, `pinpad`, `game_over`, …), and renders the panels (2×2 grid: Szene |
Umgebung / Letzte Aktion | Status). The dog/zombie/power are corner **icon overlays**
(`dog_overlay.js`, `zombie_overlay.js`, `power_main.js`); `zombie_chat.js` is the chat
modal (red for the zombie, green for the dog); `bite_overlay.js`, `minigames.js`,
`explosion_message.js`, `pinpad.js`, `game_over.js` handle their events. "Letzte
Aktion" is a transcript: the user input + each atomic command (`action_label`) and
the engine response. Dialogs go to the chat modal; dog/zombie status lines are
debug-only.

## LLM / model notes

- Models (`gemini_interface.py`): `gemini-2.5-flash-lite` (text / command parsing),
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
- Commit/push only when asked (the author reviews, then says "push it"). Current
  working branch: `Adventure-10-2026-07-08-Prompts` (prompt-optimization; branched off
  `Adventure-10-2026-06-26-Gameplay`). Remote: `kernhuber/Adventure7`.
- Item/place names shown to the player should use **call-names** (pretty), never the
  internal `o_`/`p_` ids.

## Status & next steps

Step 1 (web-layer split), Step 2 (`GameState` decomposition), and **Step 3**
(game rules → engine via `game_turn.py` `GameTurnMixin`; `PlayerDialogs` port; web-session
registry removed from `GameState`) are **done** — the engine is now GUI-free.
Follow-up robustness fixes are in: malformed tool-calls fail soft, system errors no
longer cost a round (NPC turns gated on `not is_system_error`), and the chat path
retries 503s.

All module files are now snake_case (classes stay PascalCase). The refactor phase is
complete; current work is **gameplay & UI** on branch
`Adventure-10-2026-06-26-Gameplay` (see `docs/GAMEPLAY-2026-06-27.md`): UI declutter
(dog as a status icon), zombie awakening opens the chat modal, dramatic bite popup +
status flash, pretty item names, the "Letzte Aktion" transcript, the 2×2 layout, the
Felsnische place rename, the refillable bottle, and a debug-level log prefix.

The **zombie NPC was reworked** (2026-06-29) into a richer arc — graded trust, the
operations manual as solution key, a U-Bahn "memory" route to CONVINCED, a
convince-the-player endgame, and a life-energy/petrify/share mechanic; the bite/event
GUI channel was fixed (`zombie_event` for visible beats). Details + teaching notes:
`docs/ZOMBIE-NPC-erklaert.md`. Needs an in-browser play-through to validate the
LLM-driven paths (sandbox can't import the google SDK — it hangs).

The **underground graph was reconnected** (2026-06-29). The deep rooms (Kontrollraum,
U-Bahn-Schacht, Korridor, Labor, Bibliothek, Besenkammer, Generatorraum) were
unreachable because their `obstruction_check` callbacks were TODO stubs returning `""`
— and the serializer treats anything `!= "Free"` as **blocked**. They're now gated
behind the `korridor_offen` flag via a shared `_deep_locked(gs)` helper
(`game_obstruction_check_functions.py`), and the **opener** is the new steel door
`o_stahltuer` in the Höhle (`anwenden o_stahltuer` → sets `korridor_offen`). Also fixed
the Werbeplakat secret door (ubahn2↔solaranlage), a duplicate obstruction def, and a
Höhle↔Korridor direction asymmetry. ⚠️ **Gotcha for any new passage:** an
`obstruction_check` must return `"Free"` (not `""`) when passable, or the way silently
vanishes from *Umgebung*. GHOSTMODE (`utils.py`) nulls all obstruction checks, so it
masks this.

**Dungeon layout & the U-Bahn route (2026-07-01, browser-tested & traversable).** Not a
single master gate anymore — **two independent entrances**: (1) Höhle→Korridor via the
steel door (`korridor_offen`); (2) the U-Bahn route — the Werbeplakat in U-Bahn-2 opens
the **Kontrollraum** (`kontrollraum_offen`); there the **U-Bahn-Steuerung**
(`o_u_bahn_steuerung`) sends the wagon to platform 1 (`wagen_ubahn2`, shared helper
`_shuttle_wagon`), which exposes U-Bahn-2↔U-Bahn-Schacht, and U-Bahn-Schacht→Korridor is
then free. The **inner** dungeon passages now `return "Free"` (roam freely; gate
individual doors on their own flag later for riddles). `korridor_offen` now gates ONLY
the Höhle steel door. Control room = manual + Kontrollraumschalter + U-Bahn-Steuerung.
Room descriptions (`place_prompts.py`) are being filled in room by room.

**Save / Load is implemented** (2026-07-01; design + per-class field tables in
`docs/SAVE-LOAD-DESIGN.md`). A `Storable` Protocol (`services/interfaces.py`) with an
`@savable` registry + `LoadContext` and `save_game`/`load_game`/`save_to_file`/
`load_from_file` (`services/save_load.py`); every actor/object/way + GameState + the LLM
(caches only) serialise the whole graph to one JSON (`saves/<name>.json`, gitignored).
Triggers: text `speichere <name>`/`lade <name>` and GUI buttons + a named-slot modal
(`web/save_load.js`). The LLM `narration_cache` is persisted so the scene is identical
after load. **When adding a new savable field**, add it to that class's `save()`/`load()`
— except **GameFlags** fields, which persist automatically (see next).

**Flags are single-source-of-truth in `GameFlags`** (2026-07-05, `services/world.py`).
`GameState.FLAG_FIELDS` is derived by reflection (`dataclasses.fields(GameFlags)`) instead
of a hand-kept literal that had silently drifted (`handrad_geschmiert` was missing). The
constructor no longer double-books flag start values — it only overrides the one that
differs from the dataclass default (the random ATM PIN), via the `GameFlags(...)` call in
`init_game`. Save/load is already dataclass-driven (`asdict` + a generic restore loop), so
**adding a new flag is now ONE line in `GameFlags`** — name registration, the `gs.<flag>`
legacy mirror, and persistence all follow automatically. The `__getattr__`/`__setattr__`
flag-mirror shim itself still stands. Removed the dead `ubahn_in_otherstation` alias.

**New objects/ways are highlighted in *Umgebung* until the next turn** (2026-07-05,
GUI-only). When a game action reveals an object/way *without a location change*, the new
entries get a golden `.env-new` highlight that persists until the next turn.
`web/websockets.js` freezes an `envBaseline` at the start of each user command (before that
turn's results are applied) and `updateUI()` marks entries present now but absent from the
baseline (only when location is unchanged) — robust against the several renders per turn
(`command_result` + `npc_actions`). CSS in `web/Adventure9.html`.

**Höhle steel-door puzzle is two-step** (2026-07-05). The Handrad on the steel door is
stuck until greased with the Ölkanne (`o_olkanne` → `handrad_geschmiert`); then `anwenden
o_handrad`/`o_stahltuer` in the Höhle sets `korridor_offen`. Both openers guard on location
(`p_hoehle`) and the greased flag. `korridor_offen` now **defaults to `False`** (was
hand-forced `True`).

**Gemini-error UX + fail-safe parse** (2026-07-07). When an input fails because of an LLM
error, a centered full-screen **"Spielleitung" modal** (`web/spielleitung_modal.js`, image
`web/gemini_large.png`, pulsing red glow) now appears — deliberately NOT a top-right icon,
so the player can't mistake it for a game character. It is triggered in `web/websockets.js`
when a `command_result` carries `is_game_move === false` (the backend sets that only for
`zurueckweisen` + `is_system_error`). Related engine fix: the command parser
(`gemini_interface.parse_user_input_to_commands`) **no longer retries an empty/unparseable
response** — a retry there tends to hallucinate a plausible-but-wrong command that then runs
silently (observed: an unwanted `gehe` teleport). It now fails safe straight to
`is_system_error` (→ modal, player stays put, no round consumed). The **exception** path
(503/network) keeps its single retry, since a successful network retry yields a correctly
parsed command, not a guess.

**Prompt-optimization sub-project** (2026-07-08/09, branch `Adventure-10-2026-07-08-Prompts`;
full design in `docs/PROMPT-OPTIMIZATION-PLAN.md`). Goal: cut LLM token cost **without**
weakening quality (the `enum`s + `compile_*` context + `narrate` structure are load-bearing —
they exist because the LLM otherwise returns invalid IDs and inconsistent narration) and
**keep the LLM swappable** (optimizations live behind the `LLMClient` abstraction, not tied to
Gemini). Tooling added: `_log_tokens`/`token_report` + `dl.LLM_TOKENS`, per-caller labels
(`dog_chat`/`zombie_chat`/…), the `tokenstats` debug command, and `_log_prompt_sections`
(per-section prompt breakdown). Baseline: the **parser is ~74 %** of tokens; within it
**tool-schema ~58–72 % / instructions ~30 % / context ~12 %**. Done: **B1+B1b** — slimmed &
reordered the parse prompt (fixed prefix first, variable last), measured **−17 % per parse
call**, zero quality change; **B2** — per-verb `enum` scoping (`nimm`=here, `ablegen`=inventory),
a **quality** win (fewer invalid tool-calls) but ~token-neutral. **A1 (caching): measured &
stopped** — implicit caching is on by default (Gemini 2.5) and `tokenstats` now reports cached
tokens, but only **3/34 parse calls hit** (though each hit cached ~80 %): the per-location
`enum`s sit at the front of the request and break the common prefix on almost every move (~4 %
overall). Caching only pays off if the tool schema becomes **location-invariant** → that's an
`enum` change, so the **token part of the project is wrapped** at B1 (−17 %) + B2 (quality) + the
measurement tooling. Deferred (plan §5): A2 (rest-loop — future-state deps, e.g. a key only known
after examining), C1 (narrate/compile dedup), and **A1' — full-world-id `enum`s** to get cache
hits (Gemini-specific; conflicts a bit with the provider-agnostic goal).

**Next project — swappable local LLM (Gemma) behind `LLMClient`.** Add a `GemmaInterface`
selectable via a switch in `utils.py`. Plugging in is easy (the `LLMClient` Protocol +
`services/adapters.py` already isolate the engine from the concrete LLM); the real work is
`GemmaInterface` itself — esp. that a local Gemma has no native Gemini-style function-calling/tool
schema, so `parse_user_input_to_commands` must prompt for JSON and parse it, and a local runtime
(Ollama / llama.cpp / transformers) must be wired. (Game logic/dungeon work continues in parallel,
possibly later.)

**Next — bring the dungeon to life (game-design phase):** step by step populate the
deep rooms — riddles/puzzles, items, NPC/atmosphere, and passageways that open/close
via flags (model them on `korridor_offen`/`o_stahltuer`: a `*_offen` flag in
`services/world.py` `GameFlags`, an `obstruction_check` gating on it, and an
object-`apply`/reveal that toggles it). Also outstanding: in-browser validation of the
zombie LLM paths and the `"öffne die Stahltür"` parse; balancing the trust/energy
thresholds; optional `gib <obj> an <NPC>` verb. Backlog: `docs/BACKLOG.md` (optional CLI
front-end — now feasible since the engine is GUI-free; typed `GameSession`; retire the
flag-mirror shim; remove dead verbs/`emit_*`; fix the long-broken `create_world.py`).

Refactor history: `docs/REFACTORING-2026-06-24-webserver.md` (Step 1),
`docs/REFACTORING-2026-06-25-gamestate.md` (Step 2),
`docs/REFACTORING-2026-06-25-step3-engine-rules.md` (Step 3 + robustness/perf).
