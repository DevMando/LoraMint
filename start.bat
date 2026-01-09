@echo off
setlocal enabledelayedexpansion

REM LoraMint Startup Script for Windows
REM This script starts the Blazor application which will automatically
REM set up and start the Python backend

echo.
echo ========================================
echo    LoraMint - AI Image Generation
echo ========================================
echo.

REM Kill any existing instances
echo [CHECK] Checking for existing instances...

REM Kill existing LoraMint.Web process if running
tasklist /FI "IMAGENAME eq LoraMint.Web.exe" 2>nul | find /I "LoraMint.Web.exe" >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [CLEANUP] Stopping existing LoraMint.Web instance...
    taskkill /F /IM LoraMint.Web.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM Kill Python process on port 8000 if running
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8000" ^| findstr "LISTENING"') do (
    if not "%%a"=="" (
        echo [CLEANUP] Stopping existing Python backend on port 8000 ^(PID: %%a^)...
        taskkill /F /PID %%a >nul 2>&1
    )
)

echo [OK] No conflicting instances running

REM Check if .NET SDK is installed
echo [CHECK] Verifying .NET SDK installation...
where dotnet >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] .NET SDK not found. Please install .NET 8.0 SDK first.
    echo          Visit: https://dotnet.microsoft.com/download
    pause
    exit /b 1
)
echo [OK] .NET SDK found

REM Check if Python is installed
echo [CHECK] Verifying Python installation...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [FAILED] Python not found. Please install Python 3.10 or higher.
    echo          Visit: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [OK] Python found

REM Navigate to Blazor app directory
cd /d "%~dp0src\LoraMint.Web"
if !ERRORLEVEL! NEQ 0 (
    echo [FAILED] Could not navigate to src\LoraMint.Web directory
    echo          Make sure you're running this script from the LoraMint root folder
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting Application...
echo ========================================
echo.
echo The Python backend will start automatically.
echo.
echo On first run, the following will happen:
echo   [STEP 1/3] Create Python virtual environment (~30-60 seconds)
echo   [STEP 2/3] Install AI dependencies (~2-5 minutes)
echo              - PyTorch (~200MB)
echo              - diffusers, transformers, and more
echo   [STEP 3/3] Start Python FastAPI backend
echo.
echo When you generate your first image:
echo   - Stable Diffusion model will download (~6GB)
echo   - This happens only once
echo.
echo ========================================
echo.

REM Open browser after a short delay (runs in background)
echo [BROWSER] Will open https://localhost:5001 in 5 seconds...
start "" cmd /c "timeout /t 5 /nobreak >nul && start https://localhost:5001"

REM Start the application
dotnet run

:end
echo.
echo ========================================
echo LoraMint stopped.
echo ========================================
echo.
pause
endlocal
