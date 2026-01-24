# Auto-Meeting Video Renamer

## Overview

The **Auto-Meeting Video Renamer** is a Windows background utility that automatically renames video recordings based on Google Calendar event titles. When a new video file is saved to the monitored folder, the system:

1. **Detects the new video file** with a timestamp-based name (e.g., `2026-01-22_14-26-31.mp4`)
2. **Extracts the timestamp** from the filename
3. **Queries Google Calendar** for the meeting at that exact time
4. **Automatically renames the file** to include the meeting title while preserving the original timestamp
5. **Copies the renamed file** to a separate output folder for easy access
6. **Deletes the original file** from the source folder after successful copy

## Features

- **Timestamp-Based Lookup**: Extracts recording time from filename and matches exact calendar event
- **Automatic Detection**: Monitors a specified folder for new video files
- **Google Calendar Integration**: Queries your primary calendar for meetings at the exact recording time
- **Smart Renaming**: Format `{MeetingTitle}_{original_timestamp}.{extension}`
- **Auto-Copy**: Automatically copies renamed files to a separate output folder
- **Auto-Delete**: Removes original files from source folder after successful copy
- **Batch Processing**: Automatically processes all existing files on startup
- **Network Resilience**: Retries Google Calendar API calls on network failures
- **Fallback Mode**: Copies files with original names if Google Calendar is unavailable
- **File Safety**: Checks that files are fully written before processing
- **Comprehensive Logging**: Tracks all operations with detailed timestamps
- **Error Handling**: Gracefully handles API issues and missing meetings
- **Offline Mode**: Automatically queues files when internet is unavailable and processes them when connection is restored
- **Persistent Interactions**: Telegram callback buttons survive app restarts via JSON storage
- **OS-Level File Safety**: Uses Windows-specific file handle checks to ensure recordings are finished before processing
- **Configuration File**: Easy-to-customize JSON config
- **Virtual Environment**: Isolated Python environment with all dependencies

## Requirements

### Hardware
- Modern processor (Intel i3+ or AMD Ryzen 3+)
- 4GB RAM minimum
- Active internet connection

### Software
- Windows 10 or Windows 11
- Python 3.8+
- Google Cloud Project with Calendar API enabled

## Installation

### Step 1: Install Python

Download Python 3.8+ from [python.org](https://www.python.org/) and install it. Check "Add Python to PATH" during installation.

### Step 2: Setup Virtual Environment

```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Setup Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Calendar API
4. Create an OAuth 2.0 Client ID (Desktop Application type)
5. Download the credentials as `credentials.json`
6. Place `credentials.json` in the project root directory

### Step 5: Configure the Application

Edit `config.json`:

```json
{
  "watch_folder": "D:\\Nextcloud\\Videos\\ScreenRecordings\\JustRecorded",
  "output_folder": "D:\\Nextcloud\\Videos\\ScreenRecordings\\NameSynced",
  "google_credentials_path": "credentials.json",
  "google_token_path": "token.json",
  "video_extensions": [".mp4", ".mkv", ".mov", ".avi", ".flv", ".wmv"],
  "file_lock_check_delay": 2,
  "file_lock_check_attempts": 5,
  "log_level": "INFO",
  "dry_run": false,
  "timezone_offset_hours": 3
}
```

**Key Settings:**
- `watch_folder`: Where new recordings are saved (source folder)
- `output_folder`: Where renamed files are copied (destination folder)
- `timezone_offset_hours`: Your UTC offset (e.g., 3 for GMT+3, -5 for EST, 0 for UTC)

## Running the Application

### 🚀 Executable Mode (Recommended)

The application is now compiled into a standalone Windows executable for better performance and visibility in Task Manager.

**Option 1: Direct Run**
- Double-click `dist\AutoMeetingVideoRenamer.exe` in the app directory.

**Option 2: Windows Autostart**
- Right-click `setup_autostart.bat` and select **Run as Administrator**.
- This creates a task in Windows Task Scheduler to run the app automatically when Windows starts.

**Option 3: Command Line**
```powershell
.\dist\AutoMeetingVideoRenamer.exe
```

### 💻 Development Mode (Python)

If you want to run the source code directly:

**Option 1: Direct Command**
```powershell
.\venv\Scripts\python.exe main.py
```

**Option 2: Using VS Code Tasks**
1. Open Command Palette: `Ctrl+Shift+P`
2. Type: `Tasks: Run Task`
3. Select: `Run Application`

### Stopping the Application

- Open **Task Manager** (Ctrl+Shift+Esc)
- Find **AutoMeetingVideoRenamer.exe** (or `python.exe` if running in dev mode)
- Click **End Task**
- If running in a terminal, press `Ctrl+C`.
- Press `Ctrl+C` in the terminal
- You'll see: `Shutting down application...`

### Viewing Logs

**GUI Mode (Recommended):**
1. Open the GUI
2. Click the **📋 Logs** tab
3. Logs update automatically every 2 seconds

**Command Line:**
```powershell
Get-Content logs\auto_renamer.log -Wait
```

**File Explorer:**
- Open `logs/auto_renamer.log` in your text editor

**View last 50 lines:**
```powershell
Get-Content logs\auto_renamer.log -Tail 50
```

**Search for errors:**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
```

## How It Works

### Filename Pattern
The application expects video filenames in this format:
```
YYYY-MM-DD_HH-MM-SS.{extension}
Example: 2026-01-22_14-26-31.mp4
```

The timestamp in the filename is assumed to be in **LOCAL TIME** (your system timezone).

### Processing Steps

1. **File Detection**: Watches folder for new video files
2. **Timestamp Extraction**: Reads timestamp from filename (e.g., `2026-01-22_14-26-31`)
3. **Timezone Conversion**: Converts local time to UTC using configured timezone offset
4. **Calendar Query**: Queries Google Calendar at the UTC time for the meeting
5. **Auto-Rename**: Renames to `{MeetingTitle}_{original_timestamp}.mp4` (preserves original local time)
6. **Auto-Copy**: Copies renamed file to output folder
7. **Auto-Delete**: Deletes original file from source folder

### Timezone Handling

**Important:** Google Calendar API operates in UTC. This application handles the timezone conversion automatically:

- **File timestamp**: In LOCAL TIME (e.g., GMT+3)
- **Config setting**: `timezone_offset_hours: 3` (your local offset from UTC)
- **Conversion**: Local time - offset = UTC time for calendar query
- **Example**: `2026-01-22_14-26-31` (local, GMT+3) → `2026-01-22_11-26-31` (UTC) for calendar search

**Configure your timezone in `config.json`:**
```json
{
  "timezone_offset_hours": 3  // Change 3 to your UTC offset (e.g., -5 for EST, 0 for UTC, 5 for IST)
}
```

### Processing Example

| Step | Value |
|------|-------|
| **File created in JustRecorded** | `2026-01-22_14-26-31.mp4` |
| **Extracted local time** | `2026-01-22 14:26:31` |
| **Timezone offset** | `GMT+3` (3 hours ahead of UTC) |
| **Converted to UTC** | `2026-01-22 11:26:31` |
| **Calendar lookup** | "What meeting at 11:26 UTC on Jan 22?" |
| **Found meeting** | "Team Standup" |
| **Renamed file** | **`Team_Standup_2026-01-22_14-26-31.mp4`** |
| **Copied to NameSynced** | ✓ Copy created |
| **Deleted from JustRecorded** | ✓ Original removed |

Note: The filename keeps the original LOCAL timestamp, only the calendar lookup is converted to UTC.

## Logs

Logs are saved in `logs/auto_renamer.log`. Check this file for:
- Successfully renamed files
- Calendar API responses
- Error messages and timestamps
- File processing details

**View last 50 lines:**
```powershell
Get-Content logs\auto_renamer.log -Tail 50
```

**Search for errors:**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
```

## Network & Offline Handling

### What Happens When Google Calendar is Unavailable?

The application is designed to work even when Google Calendar API is unreachable:

1. **Automatic Retries**: The app retries Google Calendar queries up to 3 times with 2-second delays
2. **Fallback Mode**: If Google Calendar fails, files are still copied to the output folder with their **original names**
3. **No Data Loss**: Files are never deleted if the copy operation fails
4. **Logging**: All failures are logged for debugging

**Example:**
```
Original file: 2026-01-23_14-30-45.mp4
Google Calendar: UNAVAILABLE
Result: File copied as 2026-01-23_14-30-45.mp4 (original name preserved)
```

### Batch Processing (Mass Import)

When you start the application, it automatically processes all existing files in the watch folder:

1. **Startup Scan**: App scans watch folder for all video files
2. **Sequential Processing**: Files are processed one by one with 1-second delays
3. **Progress Logging**: Each file's status is logged
4. **No Duplicates**: Already processed files are skipped

**Example Output:**
```
==================================================
Processing existing files in watch folder...
==================================================
Found 5 existing video file(s) to process
Processing existing file: D:\...\2026-01-22_14-00-00.mp4
Processing existing file: D:\...\2026-01-22_15-00-00.mp4
...
==================================================
Finished processing existing files
==================================================
```

## Troubleshooting

### "Credentials file not found"
- Ensure `credentials.json` is in the project root
- Download it from Google Cloud Console
- Re-run: `.\venv\Scripts\python.exe main.py` to trigger authentication

### "File not ready after checks"
- Recording software is still writing the file
- Increase `file_lock_check_attempts` in `config.json`

### "No meeting found at YYYY-MM-DD HH-MM-SS"
- No calendar event exists at the recording time
- Create the event on Google Calendar with the desired title
- File is copied with original name if no meeting found (fallback mode)

### "Google Calendar API error" (network issues)
- App automatically retries 3 times with 2-second delays
- If still unavailable, files are copied with original names
- Check your internet connection
- Verify Google Cloud credentials are still valid

### "TypeError: 'handle' must be a _ThreadHandle"
- Use the virtual environment: `.\venv\Scripts\python.exe main.py`
- Don't use plain `python main.py`

### Application won't start
1. Check Python in venv: `.\venv\Scripts\python.exe --version`
2. Verify dependencies: `.\venv\Scripts\pip.exe list`
3. Check logs: `Get-Content logs\auto_renamer.log -Tail 20`
4. Ensure watch folder exists in config.json

### Files not being processed
1. Check if watch folder path is correct in `config.json`
2. Verify video file extensions match `video_extensions` setting
3. Check logs for error messages
4. Ensure file is fully written before app processes it

## Configuration Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `watch_folder` | string | `D:\Nextcloud\Videos\ScreenRecordings\JustRecorded` | **Source folder** - where new recordings are saved |
| `output_folder` | string | `D:\Nextcloud\Videos\ScreenRecordings\NameSynced` | **Destination folder** - where renamed files are copied |
| `google_credentials_path` | string | `credentials.json` | Path to Google API credentials |
| `google_token_path` | string | `token.json` | Path to stored auth token |
| `video_extensions` | array | `[".mp4", ".mkv", ...]` | Video file types to detect |
| `file_lock_check_delay` | number | `2` | Seconds between file checks |
| `file_lock_check_attempts` | number | `5` | Number of checks before timeout |
| `log_level` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `timezone_offset_hours` | number | `3` | **Hours ahead of UTC** (e.g., 3 for GMT+3, -5 for EST, 0 for UTC) |
| `dry_run` | bool | `false` | Test mode - don't actually rename |
| `enable_logging` | bool | `true` | Enable/disable logging to file |
| `log_file` | string | `logs/auto_renamer.log` | Path to log file |

## Architecture

### Modules

- **main.py**: Application entry point and orchestration
- **config/config.py**: Configuration management
- **google_calendar_handler.py**: Google Calendar API integration
- **file_monitor.py**: File system monitoring using watchdog
- **file_renamer.py**: Filename parsing, calendar lookup, and renaming logic
- **logger.py**: Logging setup

### Processing Flow

```
Video File Created
        ↓
Monitor Detects File
        ↓
Internet Available?
    ↙       ↘
  YES       NO
   ↓         ↓
   ↓      Queue File
   ↓         ↓
   ↓      Wait for Internet
   ↓         ↓
   ↓      Internet Restored
   ↓         ↓
   ↓      Process Queue
    ↘       ↙
Extract Timestamp from Filename (2026-01-22_14-26-31)
        ↓
Check if File is Ready (fully written)
        ↓
Query Google Calendar at that exact time
        ↓
Found Meeting? → Get Title
        ↓
Generate New Filename: {Title}_{Timestamp}.mp4
        ↓
Rename File & Log Result
```

## System Tray UI (Optional Enhancement)

### Current Status
The application currently runs as a **command-line background service**. It monitors folders silently and logs all activity to `logs/auto_renamer.log`.

### Future Enhancement: System Tray Application

To convert this into a **system tray application with UI**, you would need to:

1. **Add PyQt5 or PySimpleGUI** for the GUI framework
2. **Create a system tray icon** that shows:
   - Application status (running/stopped)
   - Real-time file processing notifications
   - Quick access to logs and settings
3. **Add a settings window** to:
   - Configure folders without editing JSON
   - View processing history
   - Start/stop monitoring with a button click
4. **Add notifications** for:
   - New files detected
   - Successful renames
   - Errors or warnings

### Why Not Currently a Tray App?

- **Simpler deployment**: No GUI dependencies needed
- **Lower resource usage**: Minimal memory footprint
- **Reliable background operation**: Runs without user interaction
- **Easy logging**: All activity logged to file for debugging

### If You Want a Tray App

Would you like me to create an enhanced version with:
- ✅ System tray icon
- ✅ GUI settings panel
- ✅ Real-time notifications
- ✅ Start/stop button
- ✅ Log viewer

**Let me know and I can build this for you!** It would require adding PyQt5 to requirements.txt and creating a new `gui.py` module.

## Support

For issues:
1. Check `logs/auto_renamer.log` for detailed error messages
2. Verify Google Calendar API credentials are valid
3. Ensure watch folder path exists and is accessible
4. Review the Troubleshooting section above

## License

This project is provided as-is for personal use.
