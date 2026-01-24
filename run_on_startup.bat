@echo off
REM Auto-Meeting Video Renamer - Windows Task Scheduler Setup
REM This script sets up the application to run automatically at startup

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Auto-Meeting Video Renamer Setup
echo ========================================
echo.

REM Get the current script directory
set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%

echo Script directory: %SCRIPT_DIR%
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

python --version
echo.

REM Check if credentials.json exists
if not exist "%SCRIPT_DIR%\credentials.json" (
    echo WARNING: credentials.json not found!
    echo Please download it from Google Cloud Console and place it in the script directory.
    echo.
)

REM Create Task Scheduler task
echo Creating Task Scheduler task...
echo.

REM Delete existing task if it exists
tasklist /FI "TASKNAME eq Auto-Meeting Video Renamer" 2>NUL | find /I /N "Auto-Meeting Video Renamer">NUL
if "%ERRORLEVEL%"=="0" (
    echo Removing existing task...
    schtasks /delete /tn "Auto-Meeting Video Renamer" /f >nul 2>&1
)

REM Create new task
schtasks /create /tn "Auto-Meeting Video Renamer" ^
    /tr "python \"%SCRIPT_DIR%\main.py\"" ^
    /sc onstart ^
    /rl highest ^
    /f

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Setup Complete!
    echo ========================================
    echo.
    echo The application will now run automatically at startup.
    echo.
    echo You can view the task in Task Scheduler:
    echo   - Press Win + R and type: taskschd.msc
    echo   - Look for "Auto-Meeting Video Renamer" in the task list
    echo.
    echo Logs are saved to: %SCRIPT_DIR%\logs\auto_renamer.log
    echo.
) else (
    echo.
    echo ERROR: Failed to create Task Scheduler task
    echo Please run this script as Administrator
    echo.
)

pause
