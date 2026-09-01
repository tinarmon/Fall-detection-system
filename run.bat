@echo off
setlocal
cd /d "%~dp0"

echo ====================================================
echo  Starting DPDF 3D Client GUI (Development Mode)
echo ====================================================

REM 1. Check local venv
if exist ".\venv\Scripts\python.exe" (
    echo Using local venv Python...
    ".\venv\Scripts\python.exe" main.py
    goto end
)

REM 2. Check Project shared venv
if exist "..\Project\venv\Scripts\python.exe" (
    echo Using shared Project venv Python...
    "..\Project\venv\Scripts\python.exe" main.py
    goto end
)

REM 3. Fallback to system Python
echo Using System Python...
python main.py

:end
if errorlevel 1 (
    echo.
    echo [ERROR] Application exited with an error.
    pause
)
