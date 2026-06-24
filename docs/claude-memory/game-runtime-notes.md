---
name: game-runtime-notes
description: "How to run the adventure game, the google-genai SDK gotcha, and model IDs"
metadata: 
  node_type: memory
  type: reference
  originSessionId: de4a68f5-57c9-4f86-9442-a2d5f29750d7
---

**Start:** `./start.sh` (sources `.apikey` → exports `GOOGLE_API_KEY`, activates
venv, runs `python3 ./web_backend_server.py`, opens browser). The start command was
NOT changed by the refactor — `web_backend_server.py` is still the entry point.

**SDK gotcha:** code uses the new unified SDK `google-genai` (`from google import
genai`), listed in `requirements.txt`. On 2026-06-24 the venv was stale (had the
old `google-generativeai`, not `google-genai`); installed `google-genai 2.10.0`.
`start.sh` only pip-installs when `venv/` is absent, so a stale venv won't auto-fix.
If LLM **tool/function calls** break, the most likely cause is the request/response
shape differing between the old and new SDK — not the model IDs. Relevant code:
`GeminiInterface.parse_user_input_to_commands` and the `generate_content(...)` calls.

**Model IDs** (`GeminiInterface.py:72-73`): `gemini-2.5-flash-lite` (text/parsing),
`gemini-2.5-flash` (NPC reasoning).

**Dog NPC** intentionally absent in-game (GHOSTMODE/NODOG flags in `Utils.py`) — not
a regression. Without `GOOGLE_API_KEY`, connecting falls back to demo mode cleanly.

See [[webserver-refactor-status]].
