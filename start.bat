@echo off
REM LoraMint Startup Script for Windows
REM This script starts the Blazor application which will automatically
REM set up and start the Python backend

echo.
echo Starting LoraMint...
echo.

REM Check if .NET SDK is installed
where dotnet >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] .NET SDK not found. Please install .NET 8.0 SDK first.
    echo         Visit: https://dotnet.microsoft.com/download
    pause
    exit /b 1
)

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please install Python 3.10 or higher.
    echo         Visit: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Navigate to Blazor app directory
cd src\LoraMint.Web

echo [OK] Starting Blazor application...
echo      The Python backend will start automatically.
echo.
echo [NOTE] First run may take a few minutes to:
echo        - Create Python virtual environment
echo        - Install dependencies
echo        - Download AI models (~6GB)
echo.

REM Start the application
dotnet run

echo.
echo LoraMint stopped.
pause
