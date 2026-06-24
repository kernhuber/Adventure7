# Refactoring: `web_backend_server.py` → `webserver/` package

**Date:** 2026-06-24
**Branch:** `Adventure10-2026-06-24-Zombie-Claude-refac`
**Scope:** Step 1 of a larger refactoring effort — splitting the web backend.
Steps 2 (`GameState`) and 3 (moving game rules into the engine) are planned but
**not yet done**.

---

## 1. Why

`web_backend_server.py` had grown to **1245 lines** in a single class
(`WebAdventureServer`) that mixed six unrelated concerns:

1. HTTP static-file serving
2. WebSocket lifecycle
3. Per-client session management
4. GameState → JSON serialization
5. The player command engine (queue / LLM "rest" continuation / pending input)
6. NPC orchestration (dog / zombie / explosion turns, mini-game results)

…plus demo-mode fallbacks scattered throughout, two large narration string
constants, and a block of dead code. It was hard to read, hard to test, and hid
at least one real concurrency bug.

The goal of **Step 1** was to split this monolith into a focused `webserver/`
package **without changing behaviour**, fix the bugs found along the way, and do
it in small, independently revertable commits.

---

## 2. The result at a glance

`web_backend_server.py` is now a **10-line entry-point shim**; the implementation
lives in a `webserver/` package:

| Module | Lines | Responsibility |
|---|---|---|
| `webserver/server.py` | ~273 | Wiring + session/client lifecycle (`__init__`, `register_client`, `unregister_client`, `send_game_state`, `handle_client`, `start_*server`) |
| `webserver/command_engine.py` | ~447 | `CommandEngineMixin`: `handle_command`, `execute_single_command` — the core loop |
| `webserver/npc_runner.py` | ~241 | `NPCRunnerMixin`: `collect_npc_actions`, `handle_minigame_result`, switch-timer |
| `webserver/serialization.py` | ~123 | `serialize_real_game_state` (GameState → GUI JSON) |
| `webserver/demo.py` | ~69 | Demo-mode fallbacks: `create_demo_game_state`, `process_demo_command_execution`, `process_simple_command_execution` |
| `webserver/http_server.py` | ~64 | Static-file server (`NoListingHandler`, `start_http_server`) |
| `webserver/session.py` | ~46 | `SessionManager` — dict-compatible registry of active sessions |
| `webserver/game_modules.py` | ~33 | Shared optional import of `GameState`/`PlayerState` + `GAME_MODULES_AVAILABLE` flag |
| `webserver/texts.py` | ~64 | The two game-over narration text blocks |
| `webserver/__init__.py` | ~20 | Lazy package exports (PEP 562) |

**Why the entry point stayed:** `start.sh` / `start.bat` launch the game with
`python3 ./web_backend_server.py`. Keeping that file as a shim means **the start
command did not change** and PyInstaller packaging is unaffected.

### How to start (unchanged)
```bash
./start.sh        # sources .apikey, exports GOOGLE_API_KEY, runs web_backend_server.py
```

---

## 3. What changed, sub-step by sub-step

Each sub-step is one commit, so any regression is bisectable.

| Commit | Sub-step | Summary |
|---|---|---|
| `f3e7e66` | 1.1 | Create `webserver/` package; move the two narration text blocks to `texts.py`; reduce `web_backend_server.py` to a shim (via `git mv` to keep history). |
| `73eda58` | 1.2 | Extract `http_server.py`; **fix the port-collision bug**; make `__init__` lazy. |
| `666c3fb` | 1.3 | Extract `serialization.py` + `demo.py`. |
| `9b7802a` | 1.4 | Introduce `SessionManager`; **fix the cross-session `self.wd` bug**; fold the scene cache into the session; **fix a latent `NameError`** in the demo-fallback path. |
| `ae3be3c` | 1.5a | Create `game_modules.py` (shared flag, avoids circular import); **delete dead code**. |
| `7108987` | 1.5b | Extract `npc_runner.py` (`NPCRunnerMixin`). |
| `82042e7` | 1.5c | Extract `command_engine.py` (`CommandEngineMixin`); remove now-dead imports. `server.py` reaches its final ~273-line size. |

---

## 4. Bugs fixed (real, not cosmetic)

### 4.1 Cross-session dialog routing (the important one) — commit `9b7802a`
`WebDialogs` (the object that drives the pin-pad, mini-game, game-over and
zombie-chat popups for a given browser) was stored in a single **server-wide**
attribute `self.wd`. Every newly connecting client overwrote it in
`register_client`. With two players connected at once, a command in session A
could send its dialogs to session B's websocket.

**Fix:** `WebDialogs` is now stored **per session** (`session["web_dialogs"]`).
All nine call sites were updated. The old `self.wd` no longer exists.

### 4.2 Latent `NameError` in the demo fallback — commit `9b7802a`
`register_client`'s `except` block did `game.cmd_q = …`, but `game` can be
**undefined** there if `GameState(...)` (or, in practice, `LLMClientGemini()`
before it) raised. That would crash client registration with a `NameError`
instead of falling back to demo mode.

**Verified live:** with no `GOOGLE_API_KEY`, `LLMClientGemini()` raises *before*
`game` is bound; with the fix the connection now cleanly falls back to demo mode
(the client receives a valid `game_state`, ping/pong works, no crash). With the
old code this exact path would have raised `NameError`.

### 4.3 HTTP port-collision recursion — commit `73eda58`
The old "address in use" handler did `self.http_port += 1; self.start_http_server()`,
which **recursed and spawned a brand-new daemon thread** on every collision.
**Fix:** `start_http_server` now retries on the next port **within the same
thread** and returns the port actually bound, which `__init__` stores so the
browser is opened at the right URL.

### 4.4 Dead code removed — commit `ae3be3c`
`WebAdventureServer.do_game_over` and `clean_game_over_text` were unreachable
(their only callers were commented out; the live path uses
`WebDialogs.do_game_over`). Also removed a stray class-body `import re`.

---

## 5. Design decisions (and why)

### 5.1 Mixins for the command/NPC code (not free functions)
`handle_command`, `execute_single_command`, `collect_npc_actions` and
`handle_minigame_result` call each other heavily via `self`. They were extracted
as **mixins** (`CommandEngineMixin`, `NPCRunnerMixin`) that `WebAdventureServer`
inherits:

```python
class WebAdventureServer(CommandEngineMixin, NPCRunnerMixin):
    ...
```

The method bodies are **byte-for-byte unchanged**, so behaviour is identical by
construction. This was deliberately chosen over converting to free functions
because the app could not be run end-to-end during most of the work (see §6), and
a mixin split is the lowest-risk way to break up a large class. MRO:
`[WebAdventureServer, CommandEngineMixin, NPCRunnerMixin, object]`.

### 5.2 Lazy `__init__` (PEP 562) — keeps leaf modules testable
`webserver/server.py` imports the full game/LLM stack (`services.adapters` →
`google.genai`). If `__init__.py` imported `server` eagerly, importing *any*
submodule (e.g. `webserver.texts`) would drag in that whole chain. So
`__init__.py` resolves `WebAdventureServer` / `run_working_adventure` **lazily**
via a module-level `__getattr__`. Result: leaf modules (`texts`, `http_server`,
`serialization`, `demo`, `session`, `game_modules`) import standalone and can be
unit-tested without the LLM dependency.

### 5.3 `game_modules.py` — shared flag, no circular import
`GAME_MODULES_AVAILABLE`, `GameState` and `PlayerState` are needed by `server.py`
*and* by the command/NPC mixins. Putting the optional import in its own module
lets all three import it without importing each other. In demo mode the names are
`None`.

### 5.4 `SessionManager` is still dict-backed (intentional)
Sessions are still plain dicts (`session["type"]`, `session["cmd_q"]`, …). A typed
`GameSession` dataclass would mean rewriting ~50 access sites — almost all inside
the command code — which was **deferred** because it couldn't be runtime-verified
during the work. `SessionManager` is deliberately dict-compatible
(`__getitem__`/`__setitem__`/`__delitem__`/`__contains__`/`get`/`items`/`len`/
`iter`) so that conversion can happen later (good candidate to do alongside the
`GameState` refactor, with a live test). **This is the main piece of remaining
polish in the web layer.**

---

## 6. Verification

There is no automated test suite. Verification was done per sub-step with:
`py_compile`, standalone module imports, targeted unit tests
(`SessionManager` drop-in, demo command behaviours), byte-fidelity checks (the
demo scene-description string), and MRO composition checks.

**Environment gap during the work:** the `venv` was missing `google-genai`
(listed in `requirements.txt` but not installed — the stale `google-generativeai`
was present instead). This made it impossible to import `server.py` or run the app
for most of the refactor. It was installed at the end (`google-genai 2.10.0`).

**Live check performed (2026-06-24, without an API key):**
- ✅ Full module graph imports, including `server.py` + both mixins.
- ✅ Server boots (HTTP thread + WebSocket server).
- ✅ Serves the GUI (`index.html`, `websockets.js` → HTTP 200).
- ✅ WebSocket accepts a connection; `register_client` runs.
- ✅ Demo-fallback path works (confirms bug 4.2 fixed live).
- ✅ `ping` → `pong` routing works; initial `game_state` delivered.

**Still requires a manual browser play-through with `GOOGLE_API_KEY`:** the
LLM-driven gameplay — scene narration, command parsing, and the dialog flows
(pin-pad, mini-game, zombie-chat, game-over). Worth specifically exercising the
mini-game and zombie-chat (they touch the per-session `web_dialogs`) and a
**two-browser** session (to confirm the cross-session fix 4.1).

---

## 7. Known environment / model notes

- **SDK migration:** the code now runs against the new unified SDK
  `google-genai` (`from google import genai`), installed to match
  `requirements.txt`. If the code last worked against the old
  `google-generativeai` SDK, **function-calling request/response shapes differ**
  between the two SDKs — the most likely place for tool calls to break after the
  upgrade (not the model IDs themselves).
- **Model IDs** (`GeminiInterface.py:72-73`): `gemini-2.5-flash-lite` (text /
  command parsing) and `gemini-2.5-flash` (NPC reasoning).
- The **Dog NPC** does not appear in the running game; this is understood to be
  intentional (see `GHOSTMODE` / `NODOG` flags in `Utils.py`) and is **not** a
  regression from this refactor.

---

## 8. Next steps (planned, not started)

- **Web-layer polish:** convert sessions to a typed `GameSession` dataclass (see
  §5.4); optionally move `register`/`unregister` logic fully into `SessionManager`.
- **Step 2 — refactor `GameState.py`** (~1234 lines, same monolith smell: world /
  flags / turn loop / LLM-context compilation / web-session registry).
- **Step 3 — move game rules out of the web layer into the engine:**
  `collect_npc_actions`, the per-turn switch-timer countdown, and the thirst /
  turn-advance / game-over logic currently in `execute_single_command` belong in
  `GameState`/`PlayerState` (cf. the `Todo` note about `user_input()` having
  migrated out of `PlayerState`).

The agreed ordering is: refactor `GameState` *before* migrating rules into it, so
the rules land in their final home rather than being moved twice.

---

## 9. Conversation archive

The full Claude Code session that produced this refactor is preserved verbatim at:

```
docs/conversation-archive/2026-06-24-webserver-refactor-session.jsonl
```

(Claude Code transcript, JSON-lines. Verified to contain no API keys before
committing.)
