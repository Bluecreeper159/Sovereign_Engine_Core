@echo off
:: Sovereign Engine Core — Windows Installer
echo === Sovereign Engine Core Setup ===
cd /d "%~dp0"

where python3 >nul 2>&1 || where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3 is required but not installed.
    echo Download from https://python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python3 -m venv .venv 2>nul || python -m venv .venv

echo Installing dependencies...
.venv\Scripts\pip install --upgrade pip
.venv\Scripts\pip install -r requirements.txt

echo Setting up configuration...
if not exist .env (
    if exist .env.example (
        copy .env.example .env
        echo Generated .env from .env.example
    )
)

echo.
echo INSTALLATION COMPLETE
echo =====================
