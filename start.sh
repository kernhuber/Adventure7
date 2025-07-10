#!/bin/bash
git pull
git checkout Adventure8-LLM
test -e ./venv || ( python3 -m venv ./venv; . .venv/bin/activate; pip install -r requirements.txt )
clear
echo
echo
. ./venv/bin/activate

if test "$GOOGLE_API_KEY" = ""; then
  echo "GOOGLE_API_KEY ist nicht gesetzt. Der API-Key muss manuell eingegeben werden"
else
  export GOOGLE_API_KEY
fi

python3 Adventure8.py

