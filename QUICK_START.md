# Quick Start Guide

## 🚀 How to START the Application

### Method 1: Using the Executable (Recommended)
```powershell
.\dist\AutoMeetingVideoRenamer.exe
```

### Method 2: Using Python (Development)
```powershell
.\venv\Scripts\python.exe main.py
```

---

## ❓ Python Command: Which One Should I Use?

**What you'll see:**
```
2026-01-23 10:30:45 - INFO - ==================================================
2026-01-23 10:30:45 - INFO - Auto-Meeting Video Renamer - Initializing
2026-01-23 10:30:45 - INFO - ==================================================
2026-01-23 10:30:46 - INFO - Configuration validated successfully
2026-01-23 10:30:47 - INFO - Google Calendar authenticated successfully
2026-01-23 10:30:47 - INFO - File monitor initialized for: D:\Nextcloud\Videos\ScreenRecordings\JustRecorded
2026-01-23 10:30:47 - INFO - Auto-Meeting Video Renamer is running...
2026-01-23 10:30:47 - INFO - Press Ctrl+C to exit
```

### Method 2: Activate Virtual Environment First
```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
.\venv\Scripts\Activate.ps1
python main.py
```

**Notice:** Your prompt will change to show `(venv)` prefix:
```
(venv) PS D:\Nextcloud\Apps\sync-meeting-name-with-google>
```

### Method 3: VS Code Task
1. Press `Ctrl+Shift+P` (Command Palette)
2. Type: `Tasks: Run Task`
3. Select: `Run Application`
4. App runs in background terminal

---

## 🛑 How to STOP the Application

### Method 1: Keyboard Shortcut (Easiest)
Press `Ctrl+C` in the terminal where the app is running.

**You'll see:**
```
2026-01-23 10:35:22 - INFO - Received interrupt signal, shutting down...
2026-01-23 10:35:22 - INFO - Shutting down application...
2026-01-23 10:35:22 - INFO - File monitor stopped
2026-01-23 10:35:22 - INFO - Application shutdown complete
```

### Method 2: Close the Terminal
Simply close the PowerShell/terminal window.

### Method 3: Task Manager
1. Press `Ctrl+Shift+Esc` (Task Manager)
2. Find `AutoMeetingVideoRenamer.exe` (or `python.exe` if running via script)
3. Click "End Task"

---

## 📊 How It Works (Step by Step)

### Workflow (Normal - Google Calendar Available)
```
1. You save a video to: D:\Nextcloud\Videos\ScreenRecordings\JustRecorded
   Example filename: 2026-01-23_14-30-45.mp4
                     ↓
2. App detects the new file
                     ↓
3. App extracts timestamp: 2026-01-23 14:30:45 (LOCAL TIME)
                     ↓
4. App converts to UTC: 2026-01-23 11:30:45 (if timezone_offset_hours = 3)
                     ↓
5. App queries Google Calendar: "What meeting at 11:30 UTC?"
                     ↓
6. Calendar returns: "Team Standup"
                     ↓
7. App renames file: Team_Standup_2026-01-23_14-30-45.mp4
                     ↓
8. App copies to: D:\Nextcloud\Videos\ScreenRecordings\NameSynced
                     ↓
9. App deletes original from: D:\Nextcloud\Videos\ScreenRecordings\JustRecorded
                     ↓
10. Result:
    - JustRecorded folder: EMPTY (original deleted)
    - NameSynced folder: Team_Standup_2026-01-23_14-30-45.mp4 (renamed copy)
```

### Workflow (Fallback - Google Calendar Unavailable)
```
1. You save a video to: D:\Nextcloud\Videos\ScreenRecordings\JustRecorded
   Example filename: 2026-01-23_14-30-45.mp4
                     ↓
2. App detects the new file
                     ↓
3. App tries to query Google Calendar
                     ↓
4. Google Calendar is UNAVAILABLE (network error, API down, etc.)
                     ↓
5. App retries 3 times with 2-second delays
                     ↓
6. Still unavailable - FALLBACK MODE ACTIVATED
                     ↓
7. App copies file with ORIGINAL NAME to output folder
                     ↓
8. App deletes original from: D:\Nextcloud\Videos\ScreenRecordings\JustRecorded
                     ↓
9. Result:
    - JustRecorded folder: EMPTY (original deleted)
    - NameSynced folder: 2026-01-23_14-30-45.mp4 (original name preserved)
    - Log: "Attempting to copy original file to output folder (rename failed)"
```

### Example

**Before processing:**
- **JustRecorded folder:**
  ```
  2026-01-23_14-30-45.mp4
  ```
- **NameSynced folder:**
  ```
  (empty)
  ```

**After processing:**
- **JustRecorded folder** (original deleted):
  ```
  (empty)
  ```

- **NameSynced folder** (renamed copy):
  ```
  Team_Standup_2026-01-23_14-30-45.mp4
  ```

---

## � Batch Processing (Mass Import)

### What is Batch Processing?

When you start the app, it automatically processes **all existing files** in the watch folder. This is useful for:
- Importing a large number of old recordings
- Reprocessing files after fixing Google Calendar issues
- Catching up after the app was offline

### How It Works

1. **App starts** → Scans watch folder
2. **Finds all video files** → Lists them
3. **Processes each file** → One by one with 1-second delays
4. **Logs progress** → Shows what's being processed
5. **Starts monitoring** → Watches for new files

### Example Output

```
==================================================
Processing existing files in watch folder...
==================================================
Found 5 existing video file(s) to process
Processing existing file: D:\...\2026-01-22_14-00-00.mp4
✓ Successfully renamed...
✓ File copied to output folder...
✓ Renamed file deleted...
Processing existing file: D:\...\2026-01-22_15-00-00.mp4
...
==================================================
Finished processing existing files
==================================================
Auto-Meeting Video Renamer is running...
```

### Tips for Batch Processing

- **Large batches**: If you have 100+ files, the app will take time. Let it run!
- **Check logs**: Monitor `logs/auto_renamer.log` to see progress
- **Network issues**: If Google Calendar fails, files are copied with original names
- **No duplicates**: Already processed files won't be reprocessed

---

## 🌐 Network & Offline Mode

### What Happens If Internet is Down?

The app is designed to work even without internet:

1. **Tries to connect** to Google Calendar
2. **Retries 3 times** with 2-second delays
3. **If still unavailable** → Fallback mode activated
4. **Copies files** with original names
5. **No data loss** → Files are never deleted if copy fails

### Example

**Scenario:** Internet is down, Google Calendar unavailable

```
File: 2026-01-23_14-30-45.mp4
Google Calendar: UNAVAILABLE
Result: Copied as 2026-01-23_14-30-45.mp4 (original name)
Log: "Attempting to copy original file to output folder (rename failed)"
```

### Checking Network Status

```powershell
# Test internet connection
Test-NetConnection -ComputerName google.com -Port 443

# View network errors in logs
Select-String -Path logs\auto_renamer.log -Pattern "error|unavailable"
```

---

## �📝 Checking Logs

### View Real-Time Logs (While App is Running)
```powershell
Get-Content logs\auto_renamer.log -Wait
```
Press `Ctrl+C` to stop viewing.

### View Last 50 Lines
```powershell
Get-Content logs\auto_renamer.log -Tail 50
```

### Search for Errors
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
```

### View Entire Log File
```powershell
Get-Content logs\auto_renamer.log
```

---

## ⚙️ Configuration

Edit `config.json` to customize:

```json
{
  "watch_folder": "D:\\Nextcloud\\Videos\\ScreenRecordings\\JustRecorded",
  "output_folder": "D:\\Nextcloud\\Videos\\ScreenRecordings\\NameSynced",
  "timezone_offset_hours": 3,
  "file_lock_check_delay": 2,
  "file_lock_check_attempts": 5,
  "dry_run": false
}
```

**Key Settings:**
- `watch_folder`: Where new recordings are saved
- `output_folder`: Where renamed files are copied
- `timezone_offset_hours`: Your UTC offset
  - `3` = GMT+3 (Middle East, East Africa)
  - `-5` = EST (Eastern US)
  - `0` = UTC (UK, West Africa)
  - `5` = IST (India)
  - `8` = CST (China, Singapore)

---

## 🎯 System Tray UI

### Current Status
The app runs as a **background service** (no UI window).

### Future Enhancement
Would you like me to add:
- ✅ System tray icon
- ✅ GUI settings panel
- ✅ Real-time notifications
- ✅ Start/stop button
- ✅ Log viewer

**Just let me know!** I can create a PyQt5-based GUI version.

---

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'watchdog'"
**Solution:** Use the virtual environment
```powershell
.\venv\Scripts\python.exe main.py
```

### "File not ready after checks"
**Solution:** Increase `file_lock_check_attempts` in config.json
```json
{
  "file_lock_check_attempts": 10
}
```

### "No meeting found at YYYY-MM-DD HH-MM-SS"
**Solution:** Create the event on Google Calendar with the desired title

### "Credentials file not found"
**Solution:** 
1. Download `credentials.json` from Google Cloud Console
2. Place it in: `d:\Nextcloud\Apps\sync-meeting-name-with-google\`
3. Restart the app

---

## 📞 Need Help?

1. Check `logs/auto_renamer.log` for error messages
2. Verify `config.json` settings are correct
3. Ensure watch folder exists and is accessible
4. Check Google Calendar API credentials are valid

