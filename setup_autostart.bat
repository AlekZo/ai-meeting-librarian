@echo off
REM Setup Windows Task Scheduler to run the app on startup
REM This script creates an automated startup task

echo.
echo ====================================================
echo Setting Up Windows Autostart
echo ====================================================
echo.
echo This will create a task in Task Scheduler to run the app
echo when Windows starts (in background mode).
echo.
pause

REM Get the absolute path to the app directory
set APP_DIR=%~dp0
set APP_NAME=Auto-Meeting Video Renamer
set TASK_NAME=AutoMeetingVideoRenamer

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires administrator privileges!
    echo.
    echo Please run this as Administrator:
    echo   1. Right-click on this file
    echo   2. Select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo Creating Task Scheduler task...
echo.

REM Create the scheduled task
schtasks /create /tn "%TASK_NAME%" /tr "\"%APP_DIR%dist\AutoMeetingVideoRenamer.exe\"" /sc onstart /f /rl highest

if %errorLevel% equ 0 (
    echo.
    echo SUCCESS! Task created.
    echo.
    echo The app will now run automatically when Windows starts.
    echo.
    echo To verify:
    echo   - Open Task Scheduler
    echo   - Look for task: %TASK_NAME%
    echo.
    echo To stop the app:
    echo   - Open Task Manager (Ctrl+Shift+Esc^)
    echo   - Find "AutoMeetingVideoRenamer.exe"
    echo   - Click "End Task"
    echo.
    echo To monitor logs while app is running:
    echo   - Open PowerShell in this folder
    echo   - Run: Get-Content logs\auto_renamer.log -Wait
    echo.
) else (
    echo.
    echo ERROR: Failed to create the task!
    echo.
    echo Make sure you ran this script as Administrator.
    echo.
)

pause
