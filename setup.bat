@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo 🛠️ Setting up Fall Detection System...
echo ==================================================

:: Check for py launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
    echo [OK] Found Python launcher 'py'
) else (
    rem Check for python cmd
    where python >nul 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON_CMD=python
        echo [OK] Found Python command 'python'
    ) else (
        echo [ERROR] ❌ Python is not installed or not in the PATH.
        echo Please install Python 3.10+ from python.org and try again.
        pause
        exit /b 1
    )
)

:: Create virtual environment
if not exist venv (
    echo Creating virtual environment [venv]...
    !PYTHON_CMD! -m venv venv
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] ❌ Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [OK] Virtual environment 'venv' already exists.
)

:: Activate and install dependencies
echo Activating virtual environment...
call .\venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [ERROR] ❌ Failed to install dependencies.
    pause
    exit /b 1
)

echo ==================================================
echo 🎉 Setup completed successfully!
echo You can now run the project by launching 'run.bat'
echo ==================================================
pause
