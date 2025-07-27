@echo off
REM Git-Repository aktualisieren
git pull
git checkout Adventure9-Zombie-EnhancedUI

REM Virtualenv prüfen und ggf. erstellen
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)



cls
echo.
echo.

REM Virtualenv aktivieren
call venv\Scripts\activate.bat



REM Python-Backend starten
python web_backend_server.py
