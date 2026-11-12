@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: Django Project Restart Script  (Windows batch)
:: Reusable: copy this file into ANY Django project root.
:: It activates the venv, installs/verifies requirements,
:: runs `manage.py check`, stops any old runserver, and
:: starts a fresh one.
::
:: Optional per-project config: create `restart.env` next to
:: this file with lines like:
::   set PROJECT_PORT=8000
::   set MANAGE_PY=manage.py
::   set VENV_DIR=venv
::   set AUTO_INSTALL=1
:: ============================================================

:: -------------------- Defaults --------------------
set "MANAGE_PY=manage.py"
set "VENV_DIR=venv"
set "PROJECT_PORT=8000"
set "BIND_ADDR=0.0.0.0"
set "AUTO_INSTALL=1"
set "RUN_CHECK=1"
set "OPEN_BROWSER=0"

:: -------------------- Load per-project config --------------------
if exist "%~dp0restart.env" (
    echo [INFO] Loading config: %~dp0restart.env
    call "%~dp0restart.env"
)

:: -------------------- Resolve project root --------------------
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"
set "PROJECT_ROOT=%CD%"

echo.
echo ============================================================
echo [%date% %time%] Django Restart Script
echo [%date% %time%] Project root : %PROJECT_ROOT%
echo [%date% %time%] Manage.py    : %MANAGE_PY%
echo [%date% %time%] Bind         : %BIND_ADDR%:%PROJECT_PORT%
echo ============================================================
echo.

:: -------------------- Verify manage.py --------------------
if not exist "%MANAGE_PY%" (
    echo [ERROR] %MANAGE_PY% not found in %PROJECT_ROOT%
    echo       Place this script next to manage.py in your Django project root.
    exit /b 1
)

:: -------------------- Activate virtualenv --------------------
set "VENV_ACTIVATE=%VENV_DIR%\Scripts\activate.bat"
if exist "%VENV_ACTIVATE%" (
    echo [INFO] Activating virtualenv: %VENV_DIR%
    call "%VENV_ACTIVATE%"
    if errorlevel 1 (
        echo [WARN]  Could not activate virtualenv; continuing with system python.
    )
) else (
    echo [WARN]  Virtualenv "%VENV_DIR%" not found. Using system python.
)

:: -------------------- Verify python --------------------
echo [INFO] Python version:
python --version
if errorlevel 1 (
    echo [ERROR] python not found on PATH.
    exit /b 1
)

:: -------------------- Install requirements --------------------
if exist "requirements.txt" (
    if "%AUTO_INSTALL%"=="1" (
        echo [INFO] Installing requirements from requirements.txt...
        pip install -r requirements.txt >nul 2>&1
        if errorlevel 1 (
            echo [WARN]  pip install failed pip may be blocked or offline.
            echo [WARN]  Continuing; manage.py check and pip check will validate the environment.
        ) else (
            echo [OK]   Requirements installed.
        )
    )
    echo [INFO] Verifying installed packages pip check...
    pip check >nul 2>&1
    if errorlevel 1 (
        echo [WARN]  pip check reported dependency issues non-fatal continuing.
    ) else (
        echo [OK]   pip check passed.
    )
) else (
    echo [WARN]  requirements.txt not found; skipping install/check.
)

:: -------------------- Django system check --------------------
if "%RUN_CHECK%"=="1" (
    echo [INFO] Running "python %MANAGE_PY% check"...
    python %MANAGE_PY% check
    if errorlevel 1 (
        echo [ERROR] Django system check FAILED.
        echo         Fix the errors above before restarting the server.
        exit /b 1
    )
    echo [OK]   Django check passed.
)

:: -------------------- Stop existing server on the port --------------------
echo [INFO] Stopping any existing server on port %PROJECT_PORT%...
set "KILLED=0"
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /C:":%PROJECT_PORT% "') do (
    set "PID=%%a"
    if defined PID if not "!PID!"=="" (
        echo [INFO]   Killing PID !PID! listening on :%PROJECT_PORT%
        taskkill /PID !PID! /F >nul 2>&1
        set "KILLED=1"
    )
)
taskkill /FI "WINDOWTITLE eq Django Server*" /F >nul 2>&1

if "%KILLED%"=="1" (
    echo [INFO] Waiting 2s for the port to release...
    timeout /t 2 >nul
) else (
    echo [INFO]   No existing server found on port %PROJECT_PORT%.
)

:: -------------------- Start the server --------------------
echo [INFO] Starting Django server on %BIND_ADDR%:%PROJECT_PORT%...
echo [INFO]   Logs appear in a new console window.
start "Django Server (%PROJECT_PORT%)" cmd /k "python %MANAGE_PY% runserver %BIND_ADDR%:%PROJECT_PORT%"

if "%OPEN_BROWSER%"=="1" (
    start "" "http://127.0.0.1:%PROJECT_PORT%/"
)

echo.
echo [OK]   Restart complete.
echo [INFO] Visit: http://127.0.0.1:%PROJECT_PORT%/
echo ============================================================
endlocal
