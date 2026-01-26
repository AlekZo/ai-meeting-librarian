@echo off
REM Debug script to run the EXE and capture any errors
REM This will show you what's going wrong with the EXE

echo Starting AutoMeetingVideoRenamer.exe with error output...
echo.

cd /d "%~dp0"

REM Run the EXE and capture output
dist\AutoMeetingVideoRenamer.exe

REM If we get here, the app exited
echo.
echo Application exited with code: %ERRORLEVEL%
echo Check logs\auto_renamer.log for details
pause
