@echo off
:: sovereign_guardian.bat
:: Self-healing boot loop with clean port recovery for Windows

cd /d "%~dp0"
set LOGFILE=start.log
echo ======================================================= > %LOGFILE%
echo   [SOVEREIGN] Guardian Boot Sequence Initiated >> %LOGFILE%
echo   Time: %time% >> %LOGFILE%
echo ======================================================= >> %LOGFILE%

set PORT=%SOV_PORT%
if "%PORT%"=="" set PORT=8002

if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=".venv\Scripts\python.exe"
) else (
    set PYTHON_CMD=python
)

:loop
echo [GUARDIAN] Launching backend on port %PORT%... >> %LOGFILE%
%PYTHON_CMD% -m uvicorn main:app --host 0.0.0.0 --port %PORT% --reload >> %LOGFILE% 2>&1

echo. >> %LOGFILE%
echo [GUARDIAN] !! Backend exited — resurrecting in 2s... >> %LOGFILE%
echo ======================================================= >> %LOGFILE%
timeout /t 2 /nobreak >nul
goto loop
