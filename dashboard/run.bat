@echo off
REM ── Core-4 Drive launcher — always uses the project venv ──────────────
cd /d "%~dp0"

if not exist ".\venv\Scripts\python.exe" (
    echo [ERROR] venv not found. Create it first:
    echo     python -m venv venv
    echo     .\venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting Core-4 Drive (venv)...
".\venv\Scripts\python.exe" main.py
pause
