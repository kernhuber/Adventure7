#!/bin/bash
git pull
test -e ./venv || ( python3 -m venv ./venv; . .venv/bin/activate; pip install -r requirements.txt )
clear
echo
echo
. ./venv/bin/activate

python3 Adventure8.py
