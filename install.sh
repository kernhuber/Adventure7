#!/usr/bin/env bash
# Installer / Bootstrap für das Adventure-Spiel (macOS + Linux).
# Klont das Repository frisch, richtet das venv ein, installiert die Abhängigkeiten und
# legt die .env mit dem API-Key an. (Windows: install.bat mit gleicher Funktion.)
#
# Aufruf:  ./install.sh
#          GOOGLE_API_KEY=AIza... ./install.sh   (nicht-interaktiv, Key aus der Umgebung)

set -e

BRANCH="Adventure-10-2026-07-09-Gemma"
REPO="https://github.com/kernhuber/Adventure7.git"

# --- Repository klonen und auf die richtige Branch stellen --------------------------
git clone "$REPO"
cd Adventure7/
git fetch origin
git checkout "$BRANCH"

# --- Python-Umgebung -----------------------------------------------------------------
python3 -m venv venv
# shellcheck disable=SC1091
. ./venv/bin/activate
pip install -r requirements.txt

# --- API-Key in .env schreiben (python-dotenv liest sie beim Start) ------------------
# Sicherheitshinweis: KEINEN echten Schlüssel fest ins Skript schreiben, wenn es
# öffentlich liegt - er wäre sofort kompromittiert. Daher: aus der Umgebung nehmen,
# sonst interaktiv erfragen. (Leer lassen = nur lokales Gemma-Backend / Demo-Modus.)
if [ -z "$GOOGLE_API_KEY" ]; then
    read -r -p "Google-API-Key (für das Gemini-Backend; leer lassen für nur Gemma/Demo): " GOOGLE_API_KEY || true
fi
echo "GOOGLE_API_KEY=$GOOGLE_API_KEY" > .env

# --- Ollama-Hinweis (nur für das lokale Gemma-Backend nötig) -------------------------
if ! command -v ollama >/dev/null 2>&1; then
    echo
    echo "Hinweis: 'ollama' ist nicht installiert (nur für das lokale Gemma-Backend nötig)."
    case "$(uname -s)" in
        Darwin) echo "  Installation (macOS):  brew install ollama" ;;
        Linux)  echo "  Installation (Linux):  curl -fsSL https://ollama.com/install.sh | sh" ;;
        *)      echo "  Installation:          https://ollama.com/download" ;;
    esac
    echo "  Danach: 'ollama serve' und 'ollama pull gemma4:latest'."
fi

cat << 'EOF'

************************************************************
*                                                          *
* Fertig! Wechsle in das Verzeichnis 'Adventure7' und      *
* starte das Spiel mit  ./start.sh                          *
*                                                          *
************************************************************
EOF
