@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Python 3 is required.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Failed to install dependencies.
        pause
        exit /b 1
    )
)
start "" ".venv\Scripts\pythonw.exe" -m tomato_timer
