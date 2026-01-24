@echo off
REM Start the Auto-Meeting Video Renamer application
REM This batch file makes it easy to start the app by double-clicking

cd /d "%~dp0"

echo.
echo ====================================================
echo Auto-Meeting Video Renamer
echo ====================================================
echo.
echo Starting application...
echo.

REM Run the Python app using the virtual environment
"%~dp0venv\Scripts\python.exe" main.py

REM If app exits, pause so user can see any error messages
pause
