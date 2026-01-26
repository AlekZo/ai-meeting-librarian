# EXE Application Troubleshooting Guide

## Problem: EXE doesn't start

If the EXE application (`AutoMeetingVideoRenamer.exe`) doesn't start or closes immediately, follow these steps:

### Step 1: Check the Log File
The application writes detailed logs to `logs/auto_renamer.log`. This is the first place to check for errors.

```bash
# View the log file
type logs\auto_renamer.log
```

### Step 2: Run with Debug Console
I've updated the PyInstaller spec file to include a console window. Rebuild the EXE:

```bash
# Rebuild the EXE with console output
pyinstaller AutoMeetingVideoRenamer.spec
```

Then run the debug batch file:
```bash
run_exe_debug.bat
```

This will show any error messages directly in the console window.

### Step 3: Verify Dependencies
Make sure all required Python packages are installed:

```bash
pip install -r requirements.txt
```

### Step 4: Check Configuration
Verify that `config.json` exists and is properly configured:

```bash
# Check if config file exists
dir config.json
```

If it doesn't exist, copy from the example:
```bash
copy config.json.example config.json
```

### Step 5: Verify Credentials
The application needs Google Calendar credentials. Check if these files exist:

- `credentials.json` - OAuth credentials from Google Cloud Console
- `token.json` - Generated after first authentication

If missing, you'll need to set up Google Calendar authentication again.

### Step 6: Check Folder Permissions
Ensure the application has permission to:
- Read from the watch folder (configured in `config.json`)
- Write to the output folder
- Write to the `logs` folder

### Step 7: Run Python Version First
Test if the Python version works:

```bash
python main.py
```

If the Python version works but the EXE doesn't, the issue is with the PyInstaller build.

### Step 8: Rebuild the EXE
If you've made changes or suspect a corrupted build:

```bash
# Clean old build
rmdir /s /q build dist __pycache__

# Rebuild
pyinstaller AutoMeetingVideoRenamer.spec
```

## Common Issues and Solutions

### Issue: "Module not found" errors
**Solution:** The spec file has been updated with all required hidden imports. Rebuild with:
```bash
pyinstaller AutoMeetingVideoRenamer.spec
```

### Issue: "Cannot find config.json"
**Solution:** The application needs to be run from its installation directory. Make sure the working directory is correct.

### Issue: "Permission denied" errors
**Solution:** Run the EXE as Administrator, or check folder permissions.

### Issue: "Google Calendar authentication failed"
**Solution:** Delete `token.json` and run the application again to re-authenticate.

### Issue: "Port already in use" (if using transcription service)
**Solution:** Check if another instance is running or change the port in `config.json`.

## Getting More Help

1. **Check the log file:** `logs/auto_renamer.log`
2. **Run the debug batch:** `run_exe_debug.bat`
3. **Test with Python:** `python main.py`
4. **Check configuration:** Review `config.json` settings

## Building a New EXE

If you need to rebuild the EXE from scratch:

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Build the EXE
pyinstaller AutoMeetingVideoRenamer.spec

# The EXE will be in: dist\AutoMeetingVideoRenamer.exe
```

## Notes

- The EXE now includes a console window for debugging (changed from `console=False` to `console=True`)
- All required Python modules are explicitly listed in the spec file
- Configuration and logs directories are included in the bundle
- Error handling has been improved to catch and log startup errors
