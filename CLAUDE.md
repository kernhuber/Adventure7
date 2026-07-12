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
- **Backend switch** (`utils.py`): `LLM_BACKEND` = `"gemini"` (cloud) or `"gemma"`
  (local via Ollama); `services/llm_factory.make_llm()` picks the adapter. The Gemma
  side is imported lazily, so the Gemini path runs without `ollama` installed. See the
  Gemma sub-project note under *Status & next steps* and `gemma_interface.py`.
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
  working branch: `Adventure-10-2026-07-09-Gemma` (local-LLM/Gemma; branched off
  `Adventure-10-2026-07-08-Prompts`). Remote: `kernhuber/Adventure7`.
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

**Swappable local LLM (Gemma via Ollama) behind `LLMClient` — IMPLEMENTED & browser-tested**
(2026-07-09/10, branch `Adventure-10-2026-07-09-Gemma`). `GemmaInterface` (`gemma_interface.py`)
implements the same surface as `GeminiInterface`; select it with `utils.LLM_BACKEND="gemma"`
(+ `GEMMA_MODEL`, or the `GEMMA_MODEL` env var). Runtime = **Ollama** (`pip install ollama`,
service on :11434, a pulled model). Key design: a local Gemma has **no native function-calling**,
so instead of a tool schema we use **Ollama Structured Outputs** — pass a JSON Schema (per-verb
`anyOf`, `enum`s for valid IDs) via `format=`; XGrammar constrained decoding then guarantees
schema-valid JSON with valid IDs (this *replaces & hardens* the Gemini-`enum` quality guard).
`parse_user_input_to_commands` returns the **same** `[{"function_call": …}]` shape, so the engine
is unchanged. `think=False` is required (thinking models otherwise spend the token budget in the
"think" phase and leave `response` empty).

**Model choice matters** (32 GB M3): `gemma4:31b` (19 GB) overwhelmed the machine — on 32 GB the
GPU-wired limit is ~⅔ RAM ≈ 21 GB. Default is **`gemma4:latest` (9.6 GB)**; `gemma3:latest`
(3.3 GB) for max headroom. ("Gemma 4" tags are likely community-tagged, not an official Google
release — treat quoted benchmarks skeptically.)

**Teaching lesson from the browser tests:** Structured Outputs guarantee **well-formedness, not
correctness** — a weak local model still makes *valid-but-wrong* semantic choices, and it is
**example-driven**: abstract rules don't steer it, concrete examples in `_PARSE_PROMPT_FIXED` do.
Fixes shipped (each an added example / tightened rule, verified against `gemma4:latest`): `nimm`
was parsed as `untersuche`; a gated compound ("unlock the shed and enter" before the place is a
valid `gehe` target) forced `gehe` onto a *wrong* available place (backward teleport) instead of
deferring to `rest`; "trinke vom Wasserspender" filled the bottle instead of drinking; "stecke die
EC-Karte in den Geldautomaten" applied the *wallet* (`o_geldboerse`) instead of the card
(`o_ec_karte`) — added the ATM-insert example; and "nimm die Geheimzahl" (not a takeable object in
that location's `nimm`-enum) was **substituted** to `nimm(o_wasserspender)` — tightened the
ID-mapping rule (**never substitute a different object/place to satisfy the verb → `zurueckweisen`
if the intended target is in no enum**) + a concrete reject example (2026-07-11, commit `e86da0d`;
both backends in parallel). The rule only triggers when the object truly isn't a valid target, so it
never blocks a legitimate take. Context fix (`services/world.py`): only offer NPCs as object/target
ids when co-located with the player, and drop the player from target ids (stopped bogus
`interagieren <self>` / distant-NPC picks).

**"Geld…" synonym collisions + ATM pinpad + load bug** (2026-07-12). The fixed parse example alone
did NOT fix "stecke die **Geldkarte** in den Geldautomaten" (mapped to `o_geldautomat`; "ec-karte"
worked) — the object-adjacent **`Verwendung` hint** in `o_ec_karte_prompt_f` (the game's own
"Liefere 'anwenden EC-Karte Geldautomat'" idiom, like Ölkanne/Flasche) sharply decoupling
"Geldkarte = EC-Karte = o_ec_karte, NOT Geldautomat/Geldbörse" did (5/5, commit `9cf4187`).
**Lesson: an object-adjacent description hint beats a distant fixed example for synonym
collisions.** Two engine bugs on the EC-card→ATM path: (a) `o_ec_karte_apply_f` chose web-vs-shell
via `hasattr(gs,'web_sessions')`, but that registry was removed in Step 3 → always False → the dead
`input()` shell routine ran in the web backend; fixed (`39ed20d`) by making the GUI-free engine just
enqueue the PIN request (`check_pinpad`+hash) on `gs.cmd_q` for the front-end's PlayerDialogs
(`ask_for_pin` → modal). (b) A **load** replaced `session["game"]` but didn't re-apply the
per-session binding `game.cmd_q = session["cmd_q"]` (only `register_client` did) → a loaded game had
`cmd_q={}` (dict) → `.append` crashed on the pinpad; fixed (`25d8bc3`) by rebinding on load.
More of the same lesson: "nimm die **Geldkarte**" taking the **Geldbörse** turned out to be already
fixed by the EC-card hint (that hint sits in the object description, which is in the context for
*all* verbs incl. `nimm`) — an A/B test (generic "check identifiers" hint vs. concrete decoupling
vs. baseline) scored 5/5 across the board, so **no change**; the generic rule was pure token
overhead on an already-solved case. And "nimm die **Lire** (aus dem Pizzaautomaten)" was parsed as
`nimm(o_pizzaautomat)` — the machine, not the money (`o_geld_lire` lacked the Dollar's
"Verwendung/Beispiele" hint and "Lire" is thematically tied to the Italian pizza machine); fixed
(`c9e3e3f`) by giving `o_geld_lire` the same object-adjacent hint + a sharp "Lire = the money, NOT
the machine" decoupling (5/5).

**Backend-agnostic NPC reasoning** (2026-07-10): `NPCZombieState._call_reasoning_llm` was hardcoded
to Gemini (`from google import genai` + `gs.llm._impl.client…`) → under Gemma it threw and every
zombie turn became `nichts` (HUNTING masked it via the pursuit fallback; **COOPERATIVE froze**). It
now delegates to `gs.llm._impl._call_reasoning_llm` (added to `GeminiInterface`; Gemma already had
it), so the zombie reasons under either backend. Plus a COOPERATIVE/DOUBTING **follow-the-player
nudge** so a cooperative zombie trails the player instead of idling. Still open: rare multi-step
(`rest`) sentences that stop after the first command (not yet reproduced in a captured log); a full
Gemma browser play-through of the deep dungeon.

**`gib <obj> an <NPC>` verb — DONE & browser-confirmed** (2026-07-11, commits
`0e60523`/`019bb17`). `verb_give` (`game_verbs.py`) resolves the object via
`self.objects.get(obj_name_from_friendly_name(...))` (the ID→GameObject two-step, the
earlier bug was passing the raw ID to `is_in_inventory`), checks the recipient is a
co-located NPC, then delegates to a **`gets_given(gs, pl, obj)`** hook on that NPC (each
decides: accept / eat / drop / decline, and returns the player-facing message). Wired into
both parsers (Gemini `t_gib` FunctionDeclaration + Gemma `_VERB_ARGS`/schema/examples;
`what`=inventory, `towhom`=present NPCs). Reactions: **dog** — food (`o_salami`/`o_pizza`)
→ distracted-eating for a few turns (as if found on the ground), else silently dropped;
**zombie** — thanks in persona, `trust += GIFT_TRUST_BONUS (20)` + a notebook entry so the
reasoning "sees" it, and **`o_manual` → CONVINCED** (same as reading it); end states decline.
Deferred (in `docs/BACKLOG.md`): Case 2 (zombie→player, e.g. handing over the EC card on success).

**Zombie endgame + dried Wasserspender + test commands** (2026-07-11, commit `3c2828e`,
browser-tested). Both end states now **remove the zombie from the game** (new `vanished` flag;
`run_npc_turns` drops a vanished zombie post-loop via the existing `players_to_remove` path).
**Redemption** (`_do_redemption`): drops his **entire** inventory at the spot (EC card + gifted
items to reclaim), thanks the player, vanishes (GUI animation = a marked TODO). **Petrify**
(`_do_petrify`): pity message, vanishes, **all inventory destroyed with him**, and it **dries out
the U-Bahn Wasserspender** (`gs.wasserspender_trocken=True`). DESIGN = "slow doom": **no immediate
game over** — without water the player eventually dies of thirst (`evaluate_thirst` at `thirst==0`);
the immediate-game-over alternative is left as a code comment. Test commands (toggled by
`utils.ZOMBIE_TESTCMDS`, bypass-gated in `command_engine.py`): **`zombie_versteinern`** /
**`zombie_erlösen`** (alias `zombie_erloesen`). Related fix: `o_flasche_apply_f` let you drink from a
full bottle even when the fountain is dry (only refilling depends on it), and the "wet" fountain
description had run-on bullets (missing `\n`).

**Narration prompt shared across backends** (2026-07-11, commit `53fffb9`). Under Gemma the
narration was terse and never mentioned the dog/zombie; its `gen_narration_prompt` was a condensed
draft. The rich narrator prompt (scenario + location + objects + ways + present NPCs) now lives in
**`narration_prompt.build_narration_prompt(gs, pl)`** and both `GeminiInterface` and `GemmaInterface`
delegate to it — one source, no duplication.

**Geheimtrakt gate + Strahlenkanone redemption endgame** (2026-07-12; dungeon rooms/switch
authored by Chris in `942eecd`, cannon endgame wired this session). **Opening the deep dungeon
is two-stage now:** the Höhle steel door (`korridor_offen`) gets you into the **Korridor** hub,
but from there you can go no further until the **Geheimtrakt-Schalter** (`o_geheimtraktschalter`
in `p_innen`, needs `hauptschalter`) sets **`dungeon_offen`** — which gates Korridor↔Labor,
Korridor→Bibliothek/Besenkammer, and the U-Bahn-Schacht↔Korridor entrance (Labor↔Generatorraum
stays free, both are inside the gate). Only the entry directions are gated; return ways stay free
(no soft-lock, and `dungeon_offen` can't be toggled from inside). **The redemption is now
cannon-triggered, not auto-on-switches:** the two switches (`o_schalter_kontrollraum` /
`o_schalter_generatorraum`) each arm a `SCHALTER_TIMER`-turn countdown (`utils.SCHALTER_TIMER`,
default 10; ticked in `game_turn.tick_switch_timers`); while **both** timers are >0 the
**Strahlenkanone** (`o_strahlenkanone` in the Labor) is "armed", and firing it (`anwenden
o_strahlenkanone`) with the zombie present in the Labor redeems him (`_do_redemption`, which now
also sets `zombie_cooperative` for the win-ending flavor). In CONVINCED the zombie presses the
**Generatorraum** switch himself, then goes to the **Labor** and waits — he can't fire the cannon,
so the player activates the **Kontrollraum** switch and fires (leaves room for a goodbye). Savable
flags `pressed_endgame_switch` / `announced_endgame_plan`; the old `_do_switch_sequence` /
auto-redeem-on-both-switches path was removed.

**CONVINCED endgame reworked to LLM-primary + script fallback** (2026-07-12). First the
`cooperation_agreed` gate was dropped: the zombie no longer nags for a deal or pursues the player —
he announces his plan **once** and acts. Then the movement itself became **LLM-driven** (option B):
`_do_convinced_move` asks the reasoning LLM each active turn (CONVINCED block in
`compile_zombie_prompt` describes the plan + points the recommended direction at the current
sub-goal), and `_guard_convinced_action` accepts the LLM move unless it would break progress —
otherwise the **side-effect-free** `_cooperative_endgame_fallback` step is used. CONVINCED is
sticky (the LLM's state suggestion is ignored); the switch-press timing invariant (only when the
Kontrollraum is active) lives in the fallback, and the zombie waits at his switch to give the
player time. **Bug found via this path:** `obj_name_from_friendly_name` /
`place_name_from_friendly_name` (`services/world.py`) were **case-SENSITIVE**, but callnames are
stored lowercase — so the zombie's `anwenden Generatorraumschalter` never resolved and the switch
silently failed to arm (broke the endgame). Now case-insensitive (helps any NPC/LLM callname).
Also: fixed a `web_dialogs.do_chat` crash (unbound `r`) on a zombie-initiated chat — which had also
broken the energy-share mechanic (the chat crashed before `end_chat` ran, so `share_agreed` was
never set and the zombie kept petrifying). Water values bumped (Wasserspender → 100, bottle → +40).
GUI aid for the split-up endgame (`c9e3e3f`): the serializer emits `switches:{kontrollraum,
generatorraum}` (the timer counts) and the status panel shows a "Schalter — Kontrollraum: n ·
Generator: m" row (`-` for an inactive/0 switch), visible only while at least one switch is armed.

**Next — bring the dungeon to life (game-design phase):** step by step populate the
deep rooms — riddles/puzzles, items, NPC/atmosphere, and passageways that open/close
via flags (model them on `korridor_offen`/`o_stahltuer`: a `*_offen` flag in
`services/world.py` `GameFlags`, an `obstruction_check` gating on it, and an
object-`apply`/reveal that toggles it). Also outstanding: balancing the trust/energy
thresholds; the zombie endgame's GUI animation + Case 2 (zombie→player), see Backlog. Backlog:
`docs/BACKLOG.md` (optional CLI front-end — now feasible since the engine is GUI-free;
typed `GameSession`; retire the flag-mirror shim; remove dead verbs/`emit_*`; fix the
long-broken `create_world.py`).

Refactor history: `docs/REFACTORING-2026-06-24-webserver.md` (Step 1),
`docs/REFACTORING-2026-06-25-gamestate.md` (Step 2),
`docs/REFACTORING-2026-06-25-step3-engine-rules.md` (Step 3 + robustness/perf).
