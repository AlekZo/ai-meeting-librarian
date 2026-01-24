# Auto-Meeting Video Renamer - Usage Guide

## Quick Start Commands

### 1. Start the Application

**Option A: Using VS Code Tasks**
- Open Command Palette: `Ctrl+Shift+P`
- Type: `Tasks: Run Task`
- Select: `Run Application`

**Option B: Using PowerShell**
```powershell
cd "d:\Nextcloud\Apps\sync-meeting-name-with-google"
python main.py
```

---

## 2. Stop the Application

**Option A: From the running terminal**
- Press `Ctrl+C` in the terminal where the app is running
- Wait for graceful shutdown message

**Option B: Kill the process**
```powershell
# Find the Python process
Get-Process python

# Stop it
Stop-Process -Name python -Force
```

---

## 3. Check Application Status

**Check if app is running:**
```powershell
Get-Process python | Where-Object {$_.CommandLine -like "*main.py*"}
```

**Monitor logs in real-time:**
- Open Command Palette: `Ctrl+Shift+P`
- Type: `Tasks: Run Task`
- Select: `View Logs`

Or manually:
```powershell
Get-Content "d:\Nextcloud\Apps\sync-meeting-name-with-google\logs\auto_renamer.log" -Wait
```

---

## 4. View Application Logs

**Last 50 lines:**
```powershell
Get-Content "d:\Nextcloud\Apps\sync-meeting-name-with-google\logs\auto_renamer.log" -Tail 50
```

**Watch logs live (auto-updating):**
```powershell
Get-Content "d:\Nextcloud\Apps\sync-meeting-name-with-google\logs\auto_renamer.log" -Wait
```

**Search for errors:**
```powershell
Select-String -Path "d:\Nextcloud\Apps\sync-meeting-name-with-google\logs\auto_renamer.log" -Pattern "ERROR"
```

---

## 5. Test the Application

**Run tests:**
- Open Command Palette: `Ctrl+Shift+P`
- Type: `Tasks: Run Task`
- Select: `Test Modules`

Or manually:
```powershell
cd "d:\Nextcloud\Apps\sync-meeting-name-with-google"
python test_modules.py
```

---

## How It Works

1. **File Detection**: App monitors `D:\Nextcloud\Videos\ScreenRecordings\NameIsSynced` for new video files
2. **Timestamp Extraction**: Reads timestamp from filename (e.g., `2026-01-22_14-26-31.mp4`)
3. **Calendar Lookup**: Queries Google Calendar for meetings at that exact time
4. **Auto-Rename**: Renames file to `{MeetingName}_{timestamp}.mp4`

**Example:**
- Input: `2026-01-22_14-26-31.mp4`
- Calendar lookup: "What meeting was at 2:26 PM on Jan 22?"
- Output: `Team_Standup_2026-01-22_14-26-31.mp4`

---

## Configuration

Edit `config.json` to change:
- `watch_folder`: Folder to monitor for video files
- `video_extensions`: File types to detect (`.mp4`, `.mkv`, etc.)
- `file_lock_check_delay`: Wait time between file checks (seconds)
- `dry_run`: Set to `true` to test without actually renaming
- `log_level`: `DEBUG`, `INFO`, `WARNING`, `ERROR`

---

## Troubleshooting

**App crashes immediately:**
- Check `logs/auto_renamer.log` for errors
- Verify `credentials.json` exists and is valid
- Ensure watch folder path exists

**Files not being renamed:**
- Verify Google Calendar contains events at the timestamp
- Check app logs for "No meeting found" messages
- Ensure file timestamp format matches: `YYYY-MM-DD_HH-MM-SS`

**Permission errors:**
- Run PowerShell as Administrator
- Check folder permissions for watch folder

**Need to restart:**
1. Stop the app: `Ctrl+C`
2. Wait for shutdown complete message
3. Run again: `python main.py`

