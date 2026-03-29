@echo off
:: sovereign_guardian.bat
:: Self-healing boot loop with clean port recovery for Windows

set PORT=%SOV_PORT%
if "%PORT%"=="" set PORT=8002

echo =======================================================
echo   [SOVEREIGN] Guardian Boot Sequence Initiated
echo   Protocol: Launch -^> Watch -^> Recover
echo =======================================================

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=".venv\Scripts\python.exe"
) else (
    set PYTHON_CMD=python
)

:loop
echo [GUARDIAN] Launching backend on port %PORT%...
%PYTHON_CMD% -m uvicorn main:app --host 0.0.0.0 --port %PORT% --reload

echo.
echo [GUARDIAN] !! Backend exited — resurrecting in 2s...
echo =======================================================
timeout /t 2 /nobreak >nul
goto loop
