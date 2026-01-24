# How to Start the App (Easy & Autostart)

## 🚀 Option 1: Simple Click to Start (No Background)

### Method A: Double-Click
1. Open File Explorer
2. Navigate to: `d:\Nextcloud\Apps\sync-meeting-name-with-google\`
3. Double-click: **`start_app.bat`**
4. A terminal window opens and the app starts
5. You'll see: `Auto-Meeting Video Renamer is running...`

### Method B: PowerShell
```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
.\start_app.bat
```

---

## 🔄 Option 2: Background Mode (Minimized, No Window)

Use this if you want the app to run **without showing a terminal window**.

### Step 1: Start in Background
Double-click: **`start_app_background.bat`**

What happens:
- ✅ App starts silently in the background
- ✅ No terminal window appears
- ✅ Window closes automatically with instructions
- ✅ App continues running

### Step 2: Monitor the App (While Running in Background)

**Option A: View Logs in PowerShell (Recommended)**
```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
Get-Content logs\auto_renamer.log -Wait
```

What you'll see:
```
2026-01-23 10:30:47 - INFO - Auto-Meeting Video Renamer is running...
2026-01-23 10:31:05 - INFO - New video file detected: 2026-01-23_14-30-45.mp4
2026-01-23 10:31:10 - INFO - Successfully renamed: Team_Standup_2026-01-23_14-30-45.mp4
2026-01-23 10:31:12 - INFO - File copied to output folder
2026-01-23 10:31:13 - INFO - Renamed file deleted
```

**Option B: View Last 50 Lines**
```powershell
Get-Content logs\auto_renamer.log -Tail 50
```

**Option C: Search for Errors**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
```

**Option D: View in Real-Time (Follow Mode)**
Press `Ctrl+C` to stop watching logs.

### Step 3: Stop the App (While Running in Background)

**Method 1: Task Manager (Easiest)**
1. Press `Ctrl+Shift+Esc` (Open Task Manager)
2. Find `python.exe` in the list
3. Click it to select
4. Click "End Task" button
5. App stops immediately

**Method 2: PowerShell**
```powershell
Stop-Process -Name python.exe -Force
```

**Method 3: Command Prompt**
```cmd
taskkill /IM python.exe /F
```

---

## ⏰ Option 3: Autostart on Windows Startup (Always Running)

Use this if you want the app to start **automatically when Windows boots up**.

### Step 1: Setup Autostart
1. Right-click: **`setup_autostart.bat`**
2. Select: **"Run as administrator"** (Important!)
3. Click "Create" when prompted
4. You'll see: `SUCCESS! Task created.`

### Step 2: Verify It Works
Next time you restart Windows:
- ✅ App starts automatically in background
- ✅ No terminal window appears
- ✅ App silently monitors your videos
- ✅ You can still view logs anytime

### Step 3: Monitor Auto-Started App

**While Windows is Running:**
Open PowerShell and check logs:
```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
Get-Content logs\auto_renamer.log -Wait
```

### Step 4: Remove Autostart (If You Change Your Mind)

**Method 1: Task Scheduler (Easiest)**
1. Press `Win` key
2. Type: `Task Scheduler`
3. Press Enter
4. Look for: `AutoMeetingVideoRenamer`
5. Right-click → Delete

**Method 2: PowerShell (Admin)**
```powershell
schtasks /delete /tn "AutoMeetingVideoRenamer" /f
```

---

## 📊 Comparison Table

| Method | Ease | Window | Stop Method | Best For |
|--------|:---:|:------:|:-----------:|----------|
| **Double-click start_app.bat** | ⭐⭐⭐⭐⭐ | Visible | Close window | Testing, manual use |
| **start_app_background.bat** | ⭐⭐⭐⭐⭐ | Hidden | Task Manager | Daily use, no UI |
| **Autostart Setup** | ⭐⭐⭐⭐ | Hidden | Task Manager | Always-on monitoring |

---

## 🔧 File Reference

| File | Purpose |
|------|---------|
| `start_app.bat` | Start app with visible terminal (see output) |
| `start_app_background.bat` | Start app hidden in background |
| `setup_autostart.bat` | Configure Windows autostart |

---

## 📝 Logs Location

Logs are saved here:
```
d:\Nextcloud\Apps\sync-meeting-name-with-google\logs\auto_renamer.log
```

You can also open in any text editor:
1. Open File Explorer
2. Navigate to: `logs` folder
3. Open: `auto_renamer.log`

---

## 🆘 Troubleshooting

### "Task Manager says python.exe is not responding"
**Solution:** Click "End Task" again, it will force close

### "Can't stop the app"
**Solution:** Restart your computer

### "setup_autostart.bat didn't work"
**Solution:** Right-click and select "Run as administrator" (must have admin rights)

### "Where's the app window?"
**Solution:** It's in the background! Check logs using PowerShell (see above)

### "App crashed - how do I know?"
**Solution:** Check logs for ERROR messages:
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
```

---

## ✅ Quick Start (Choose One)

**I want to start now:**
```powershell
cd d:\Nextcloud\Apps\sync-meeting-name-with-google
.\start_app.bat
```

**I want to start in background:**
Double-click: `start_app_background.bat`

**I want it to run automatically at startup:**
Right-click: `setup_autostart.bat` → "Run as administrator"

---

## 📞 Need Help?

Check `logs\auto_renamer.log` for detailed error messages.

All errors are logged with timestamps for easy debugging!
