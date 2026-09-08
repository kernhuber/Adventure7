#!/usr/bin/env bash
# Startet das Adventure-Web-Backend. Läuft unter macOS und Linux.
# (Windows: siehe start.bat mit derselben Funktionalität.)
# Aus dem Projektverzeichnis heraus aufrufen (dort, wo requirements.txt liegt).

# --- Repo aktualisieren (dient zugleich als Installer/Updater) -----------------------
# Der Spielstand liegt auf dieser Branch -> beim Umzug auf eine neue Branch hier ändern.
# 'git checkout' stellt zugleich das Upstream-Tracking her, damit 'git pull' funktioniert
# (ein frischer Klon landet sonst auf 'main' ohne Bezug zu dieser Branch, und pull scheitert).
# Fehler (lokale Änderungen, kein Netz, kein Git-Repo) sind nicht kritisch -> Skript läuft weiter.
BRANCH="Adventure-10-2026-07-09-Gemma"
git fetch origin 2>/dev/null                 # Remote-Refs holen, damit checkout die Branch kennt
git checkout "$BRANCH" 2>/dev/null || echo "Hinweis: Branch '$BRANCH' nicht ausgecheckt (lokale Änderungen? kein Git-Repo?)."
git pull --ff-only 2>/dev/null || echo "Hinweis: 'git pull' übersprungen (nicht kritisch)."

# --- Python-venv anlegen (falls nicht vorhanden) ------------------------------------
if [ ! -d "./venv" ]; then
    echo "Erstelle Python-venv ..."
    python3 -m venv ./venv
fi

# venv aktivieren
# shellcheck disable=SC1091
. ./venv/bin/activate

# --- Abhängigkeiten sicherstellen ---------------------------------------------------
# Idempotent bei jedem Start: bereits installierte Pakete werden übersprungen, neu
# hinzugekommene (z.B. 'ollama') aber nachinstalliert - auch in einem bestehenden venv.
pip install -q -r requirements.txt

# --- API-Key laden ------------------------------------------------------------------
test -e ./.apikey && . ./.apikey

echo
echo

# --- Ollama-Check (nur für das lokale Gemma-Backend nötig) --------------------------
if ! command -v ollama >/dev/null 2>&1; then
    echo "  'ollama' ist nicht installiert - es wird für das lokale LLM-Backend (Gemma) benötigt."
    case "$(uname -s)" in
        Darwin) echo "    Installation (macOS):  brew install ollama"
                echo "                           oder Download: https://ollama.com/download" ;;
        Linux)  echo "    Installation (Linux):  curl -fsSL https://ollama.com/install.sh | sh" ;;
        *)      echo "    Installation:          https://ollama.com/download" ;;
    esac
    echo "    Danach: Dienst starten ('ollama serve') und das Modell ziehen ('ollama pull gemma4:latest')."
    echo "    Hinweis: Für das Gemini-Cloud-Backend wird Ollama NICHT benötigt."
    echo
fi

# --- Google-API-Key prüfen ----------------------------------------------------------
if test "$GOOGLE_API_KEY" = ""; then
    echo "GOOGLE_API_KEY ist nicht gesetzt. Der API-Key muss manuell eingegeben werden, sofern Gemini als Backend genutzt werden soll."
else
    export GOOGLE_API_KEY
fi

python3 ./web_backend_server.py
