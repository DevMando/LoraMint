@echo off
REM Helper script to wait for server and open browser
REM This runs in the background

echo [BROWSER] Waiting for server to be ready...

:loop
timeout /t 2 /nobreak >nul

REM Check if port 5001 is listening
netstat -an | findstr ":5001" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [BROWSER] Server is ready! Opening browser...
    timeout /t 1 /nobreak >nul
    start https://localhost:5001
    exit /b 0
)

goto loop
