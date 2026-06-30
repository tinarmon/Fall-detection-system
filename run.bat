@echo off
if not exist .\venv\Scripts\activate.bat (
    echo [ERROR] ❌ Virtual environment not found.
    echo Please run 'setup.bat' first to install the environment and dependencies.
    pause
    exit /b 1
)

echo Starting Pre-Fall Detection System...
call .\venv\Scripts\activate.bat
python main.py
pause
