@echo off
REM Installer / Bootstrap fuer das Adventure-Spiel (Windows).
REM Klont das Repository frisch, richtet das venv ein, installiert die Abhaengigkeiten und
REM legt die .env mit dem API-Key an. (macOS/Linux: install.sh mit gleicher Funktion.)
REM
REM Aufruf:  install.bat
REM          set GOOGLE_API_KEY=AIza... & install.bat   (nicht-interaktiv, Key aus der Umgebung)

set BRANCH=Adventure-10-2026-07-09-Gemma
set REPO=https://github.com/kernhuber/Adventure7.git

REM --- Repository klonen und auf die richtige Branch stellen ----------------------
git clone %REPO%
cd Adventure7
git fetch origin
git checkout %BRANCH%

REM --- Python-Umgebung -----------------------------------------------------------
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

REM --- API-Key in .env schreiben (python-dotenv liest sie beim Start) -------------
REM Sicherheitshinweis: KEINEN echten Schluessel fest ins Skript schreiben, wenn es
REM oeffentlich liegt. Aus der Umgebung nehmen, sonst interaktiv erfragen.
if "%GOOGLE_API_KEY%"=="" (
    set /p GOOGLE_API_KEY="Google-API-Key (fuer Gemini; leer lassen fuer nur Gemma/Demo): "
)
echo GOOGLE_API_KEY=%GOOGLE_API_KEY%>.env

REM --- Ollama-Hinweis (nur fuer das lokale Gemma-Backend noetig) ------------------
where ollama >nul 2>nul
if errorlevel 1 (
    echo.
    echo Hinweis: 'ollama' ist nicht installiert (nur fuer das lokale Gemma-Backend noetig).
    echo   Installation (Windows): https://ollama.com/download
    echo   Danach: Ollama starten und 'ollama pull gemma4:latest'.
)

echo.
echo ************************************************************
echo *                                                        *
echo * Fertig! Wechsle in das Verzeichnis 'Adventure7' und    *
echo * starte das Spiel mit  start.bat                        *
echo *                                                        *
echo ************************************************************
pause
