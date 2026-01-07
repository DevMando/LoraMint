@echo off
REM LoraMint Python Backend Setup Script for Windows
REM This script manually sets up the Python backend environment

echo.
echo Setting up Python backend for LoraMint...
echo.

REM Navigate to Python backend directory
cd src\python-backend

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10 or higher.
    pause
    exit /b 1
)

echo [OK] Using Python
python --version

REM Create virtual environment
if exist "venv\" (
    echo [WARNING] Virtual environment already exists. Skipping creation.
) else (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install dependencies
echo [INFO] Installing dependencies...
echo        This may take several minutes...
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [OK] Python backend setup complete!
echo.
echo To start the Python backend manually:
echo   cd src\python-backend
echo   venv\Scripts\activate
echo   python main.py
echo.
echo Or simply run: start.bat
echo.
pause
