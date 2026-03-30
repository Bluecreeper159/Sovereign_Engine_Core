@echo off
:: Sovereign Engine Core — Windows Installer
cd /d "%~dp0"
set LOGFILE=install.log
echo === Sovereign Engine Core Setup === > %LOGFILE%
echo Time: %time% >> %LOGFILE%

::: Check Python
where python3 >nul 2>&1
if %errorlevel% equ 0 (
    set SYS_PYTHON=python3
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set SYS_PYTHON=python
    ) else (
        echo [ERROR] Python not found. >> %LOGFILE%
        exit /b 1
    )
)

echo Using system python: %SYS_PYTHON% >> %LOGFILE%

echo Creating virtual environment... >> %LOGFILE%
%SYS_PYTHON% -m venv .venv >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment. >> %LOGFILE%
    exit /b 1
)

echo Installing dependencies... >> %LOGFILE%

.venv\Scripts\python.exe -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [GUARDIAN] pip missing in venv. Bootstrapping via local get-pip.py... >> %LOGFILE%
    .venv\Scripts\python.exe vendor\get-pip.py --no-index --find-links=vendor pip setuptools wheel >> %LOGFILE% 2>&1
)

.venv\Scripts\python.exe -m pip install --no-index --find-links=vendor --upgrade pip >> %LOGFILE% 2>&1
.venv\Scripts\python.exe -m pip install --no-index --find-links=vendor -r requirements.txt >> %LOGFILE% 2>&1
if errorlevel 1 (
    echo [ERROR] PIP installation failed. See log. >> %LOGFILE%
) else (
    echo [OK] Dependencies installed successfully. >> %LOGFILE%
)

echo Setting up configuration... >> %LOGFILE%
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo Generated .env from .env.example >> %LOGFILE%
    )
)

echo INSTALLATION COMPLETE >> %LOGFILE%
exit /b 0
