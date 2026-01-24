# SETUP GUIDE - Auto-Meeting Video Renamer

## Quick Start (5 minutes)

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

Or use the VS Code task: `Tasks > Run Task > Install Dependencies`

### 2. Get Google Credentials
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable "Google Calendar API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Choose "Desktop application"
6. Download the JSON file as `credentials.json` in the project root

### 3. Configure (Optional)
Edit `config.json` to customize:
- `watch_folder`: Where to monitor (default: `D:\Nextcloud\Videos\ScreenRecordings\JustRecorded`)
- `output_folder`: Where to copy renamed files (default: `D:\Nextcloud\Videos\ScreenRecordings\NameSynced`)
- `video_extensions`: File types to detect
- `dry_run`: Set to `true` to test without renaming

### 4. Run the App
**Recommended:**
```bash
.\dist\AutoMeetingVideoRenamer.exe
```

**Development:**
```bash
.\venv\Scripts\python.exe main.py
```

Or use VS Code task: `Tasks > Run Task > Run Application`

The first time you run it, a browser will open for Google authentication. Sign in and approve calendar access.

## Setup for Auto-Startup

### Option 1: Using Batch File (Easiest)
Right-click `setup_autostart.bat` and select **Run as Administrator**. This will automatically setup Windows Task Scheduler to use the compiled executable.

### Option 2: Manual Task Scheduler
1. Press `Win + R`, type `taskschd.msc`
2. Click "Create Basic Task"
3. Name: `AutoMeetingVideoRenamer`
4. Trigger: `At startup`
5. Action: Start program
   - Program: `d:\Nextcloud\Apps\sync-meeting-name-with-google\dist\AutoMeetingVideoRenamer.exe`
   - Start in: `d:\Nextcloud\Apps\sync-meeting-name-with-google`

## Verify Setup

### Test Modules
Run `test_modules.py` to verify sanitization logic:
```bash
python test_modules.py
```

Or use: `Tasks > Run Task > Test Modules`

### Check Logs
Monitor the application:
```bash
Tasks > Run Task > View Logs
```

Or directly view: `logs/auto_renamer.log`

## Configuration Files

- **config.json** - Application settings
- **.vscode/tasks.json** - VS Code shortcuts
- **.vscode/settings.json** - Editor preferences

## File Structure

```
sync-meeting-name-with-google/
├── main.py                          # Entry point
├── config/
│   └── config.py                    # Configuration handler
├── google_calendar_handler.py        # Google API integration
├── file_monitor.py                  # Folder monitoring
├── file_renamer.py                  # Renaming logic
├── logger.py                        # Logging setup
├── test_modules.py                  # Module tests
├── requirements.txt                 # Python dependencies
├── config.json                      # Settings file
├── run_on_startup.bat               # Startup setup
├── README.md                        # Full documentation
├── SETUP.md                         # This file
├── .vscode/
│   ├── tasks.json                   # Task definitions
│   └── settings.json                # Editor settings
├── logs/                            # Log files (auto-created)
└── .gitignore                       # Git ignore rules
```

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Python not recognized
- Install Python 3.8+ from [python.org](https://www.python.org/)
- Check "Add Python to PATH" during installation
- Restart terminal after installation

### Google authentication fails
- Verify `credentials.json` is in the project root
- Check your internet connection
- Try deleting `token.json` and running again

### Files not getting renamed
1. Check `logs/auto_renamer.log` for errors
2. Verify the watch folder path in `config.json`
3. Ensure you're logged into Google Calendar
4. Check if a meeting is actually scheduled at the time of recording

### Application won't start at startup
1. Run `run_on_startup.bat` as Administrator
2. Or manually create the Task Scheduler task (see above)
3. Check Task Scheduler for errors

## Next Steps

1. ✅ Install dependencies
2. ✅ Download credentials.json
3. ✅ Run `python main.py` (first-time Google login)
4. ✅ Test with a video file
5. ✅ Setup auto-startup with `run_on_startup.bat`

## Support

- Check README.md for detailed documentation
- Review logs in `logs/auto_renamer.log`
- Verify configuration in `config.json`
