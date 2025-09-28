#!/bin/bash
git pull
git checkout Adventure10-2025-09-15
test -e ./venv || ( python3 -m venv ./venv; . ./venv/bin/activate; pip install -r requirements.txt )
test -e ./.apikey && . ./.apikey
clear
echo
echo
. ./venv/bin/activate

if test "$GOOGLE_API_KEY" = ""; then
  echo "GOOGLE_API_KEY ist nicht gesetzt. Der API-Key muss manuell eingegeben werden"
else
  export GOOGLE_API_KEY
fi

python3 ./web_backend_server.py

