@echo off
REM Startet das Adventure-Web-Backend unter Windows.
REM (macOS/Linux: siehe start.sh mit derselben Funktionalitaet.)

REM Immer aus dem Verzeichnis dieser Datei arbeiten (egal, von wo aufgerufen).
cd /d "%~dp0"

REM --- Repo best-effort aktualisieren ---------------------------------------------
REM Aktualisiert die AKTUELLE Branch, ohne sie zu wechseln. Fehler sind nicht kritisch.
git pull --ff-only 2>nul
REM Zum Festpinnen einer bestimmten Branch (z.B. fuer Kurse) hier eine Zeile ergaenzen, z.B.:
REM   git checkout Adventure-10-2026-07-09-Gemma

REM --- Python-venv anlegen (falls nicht vorhanden) --------------------------------
if not exist venv (
    echo Erstelle Python-venv ...
    python -m venv venv
)

REM venv aktivieren
call venv\Scripts\activate.bat

REM --- Abhaengigkeiten sicherstellen ---------------------------------------------
REM Idempotent bei jedem Start: neu hinzugekommene Pakete (z.B. 'ollama') werden auch
REM in einem bestehenden venv nachinstalliert.
pip install -q -r requirements.txt

REM --- API-Key laden (optional) ---------------------------------------------------
REM Auf Windows muss .apikey die Zeile  set GOOGLE_API_KEY=...  enthalten.
if exist .apikey call .apikey

cls
echo.
echo.

REM --- Ollama-Check (nur fuer das lokale Gemma-Backend noetig) --------------------
where ollama >nul 2>nul
if errorlevel 1 (
    echo [!] 'ollama' ist nicht installiert - es wird fuer das lokale LLM-Backend ^(Gemma^) benoetigt.
    echo     Installation ^(Windows^):  https://ollama.com/download
    echo     Danach: Ollama starten und ein Modell ziehen ^("ollama pull gemma4:latest"^).
    echo     Hinweis: Fuer das Gemini-Cloud-Backend wird Ollama NICHT benoetigt.
    echo.
)

REM --- Google-API-Key pruefen -----------------------------------------------------
if "%GOOGLE_API_KEY%"=="" (
    echo GOOGLE_API_KEY ist nicht gesetzt. Der API-Key muss manuell eingegeben werden, sofern Gemini als Backend genutzt werden soll.
)

REM Python-Backend starten
python web_backend_server.py
