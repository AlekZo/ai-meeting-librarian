@echo off
REM Start the Auto-Meeting Video Renamer in BACKGROUND mode (minimized)
REM This batch file starts the app without showing a terminal window

cd /d "%~dp0"

REM Get the absolute path to the app directory
set APP_DIR=%~dp0

REM Start the Python app in the background (minimized)
REM The /B flag runs the command without opening a new window
start /B "" "%APP_DIR%venv\Scripts\python.exe" main.py

echo.
echo ====================================================
echo Auto-Meeting Video Renamer - BACKGROUND MODE
echo ====================================================
echo.
echo Application started in background!
echo.
echo To monitor the app:
echo   - Open PowerShell in this folder
echo   - Run: Get-Content logs\auto_renamer.log -Wait
echo.
echo To stop the app:
echo   - Open Task Manager (Ctrl+Shift+Esc)
echo   - Find "python.exe" in the list
echo   - Click "End Task"
echo.
echo Press any key to close this window...
pause >nul
