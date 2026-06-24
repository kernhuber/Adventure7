# Conversation archive

Preserved Claude Code session transcripts, kept under version control so the
original working conversations cannot be lost to timeouts or accidental deletion.

## Files

- **`2026-06-24-webserver-refactor-session.jsonl`** — the session that split
  `web_backend_server.py` into the `webserver/` package (Step 1). See
  `docs/REFACTORING-2026-06-24-webserver.md` for the human-readable summary.

## Format

JSON-lines: one JSON object per line, in chronological order (user messages,
assistant turns, tool calls and their results). To read it, e.g.:

```bash
# pretty-print message roles and text
python3 - <<'PY'
import json
for line in open("docs/conversation-archive/2026-06-24-webserver-refactor-session.jsonl"):
    rec = json.loads(line)
    print(rec.get("type"), "-", str(rec.get("message", ""))[:120])
PY
```

These files were scanned for secrets (Google API key patterns) before being
committed; none were found. `.apikey.env` remains gitignored.
