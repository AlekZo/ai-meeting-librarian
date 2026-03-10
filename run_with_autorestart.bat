@echo off
REM Auto-restart wrapper for Auto Meeting Video Renamer
REM Automatically restarts the application on crash

setlocal enabledelayedexpansion

set "MAX_RESTARTS=20"
set "RESTART_DELAY=5"
set "RESTART_COUNT=0"
set "CRASH_TIME=0"

:start_app
set /a RESTART_COUNT+=1

REM Check if too many restarts in short time
if !RESTART_COUNT! gtr !MAX_RESTARTS! (
    echo.
    echo ========================================
    echo ERROR: Application crashed !MAX_RESTARTS! times
    echo Maximum restart attempts exceeded
    echo ========================================
    echo.
    echo Please check the logs for details:
    echo   logs/auto_renamer.log
    echo.
    pause
    exit /b 1
)

REM Alert if frequent crashes
if !RESTART_COUNT! gtr 5 (
    echo.
    echo WARNING: Application has restarted !RESTART_COUNT! times
    echo Starting in recovery mode...
    echo.
)

echo.
echo ========================================
echo Starting Auto Meeting Video Renamer
echo Attempt !RESTART_COUNT! of !MAX_RESTARTS!
echo ========================================
echo.

cd /d "%~dp0"

REM Run the application
python main.py

set "EXIT_CODE=!ERRORLEVEL!"

echo.
echo ========================================
echo Application exited with code: !EXIT_CODE!
echo ========================================
echo.

REM Exit code 0 means graceful shutdown, don't restart
if !EXIT_CODE! equ 0 (
    echo Graceful shutdown detected. Exiting.
    exit /b 0
)

REM Otherwise, wait and restart
echo Waiting !RESTART_DELAY! seconds before restarting...
echo.

timeout /t !RESTART_DELAY!

goto start_app
