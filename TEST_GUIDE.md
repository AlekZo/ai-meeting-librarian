# Testing Guide

## Quick Test Scenarios

### Test 1: Single File Processing ✅
**Goal:** Verify basic rename, copy, and delete workflow

**Steps:**
1. Create a test video file with timestamp in filename:
   ```
   2026-01-23_14-30-00.mp4
   ```
2. Place it in: `D:\Nextcloud\Videos\ScreenRecordings\JustRecorded\`
3. Start the app: `.\venv\Scripts\python.exe main.py`
4. Wait 10 seconds

**Expected Results:**
- ✅ File is renamed with meeting title
- ✅ Renamed file appears in `NameSynced` folder
- ✅ Original file is deleted from `JustRecorded` folder
- ✅ Logs show all three operations

**Check Logs:**
```powershell
Get-Content logs\auto_renamer.log -Tail 20
```

---

### Test 2: Batch Processing (Mass Import) 📦
**Goal:** Verify batch processing of multiple files on startup

**Steps:**
1. Create 5 test video files with different timestamps:
   ```
   2026-01-22_10-00-00.mp4
   2026-01-22_11-00-00.mp4
   2026-01-22_12-00-00.mp4
   2026-01-22_13-00-00.mp4
   2026-01-22_14-00-00.mp4
   ```
2. Place all in: `D:\Nextcloud\Videos\ScreenRecordings\JustRecorded\`
3. Start the app: `.\venv\Scripts\python.exe main.py`
4. Watch the logs

**Expected Results:**
- ✅ App shows "Found 5 existing video file(s) to process"
- ✅ Each file is processed sequentially
- ✅ All files appear in `NameSynced` folder
- ✅ All files deleted from `JustRecorded` folder
- ✅ Processing takes ~10-15 seconds total

**Check Progress:**
```powershell
Get-Content logs\auto_renamer.log -Wait
```

---

### Test 3: Dry Run Mode (Safe Testing) 🧪
**Goal:** Test without actually modifying files

**Steps:**
1. Edit `config.json`:
   ```json
   {
     "dry_run": true
   }
   ```
2. Place a test file in `JustRecorded` folder
3. Start the app: `.\venv\Scripts\python.exe main.py`
4. Check logs

**Expected Results:**
- ✅ Logs show `[DRY RUN]` messages
- ✅ No actual files are modified
- ✅ No files are deleted
- ✅ Safe way to test without risk

**Check Logs:**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "DRY RUN"
```

**Reset After Testing:**
```json
{
  "dry_run": false
}
```

---

### Test 4: Network Failure Simulation 🌐
**Goal:** Verify fallback mode when Google Calendar is unavailable

**Steps:**
1. Disconnect internet or block Google API:
   ```powershell
   # Block Google API (Windows Firewall)
   New-NetFirewallRule -DisplayName "Block Google API" -Direction Outbound -Action Block -RemoteAddress "*.googleapis.com"
   ```
2. Place a test file in `JustRecorded` folder
3. Start the app: `.\venv\Scripts\python.exe main.py`
4. Wait 10 seconds

**Expected Results:**
- ✅ App shows retry attempts (3 times)
- ✅ File is copied with **original name** (fallback mode)
- ✅ File appears in `NameSynced` folder
- ✅ Original deleted from `JustRecorded` folder
- ✅ Logs show "Attempting to copy original file to output folder (rename failed)"

**Check Logs:**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "error|unavailable|retry"
```

**Restore Internet:**
```powershell
# Remove the firewall rule
Remove-NetFirewallRule -DisplayName "Block Google API"
```

---

### Test 5: File Lock Detection ⏱️
**Goal:** Verify app waits for file to be fully written

**Steps:**
1. Create a large test file (100+ MB)
2. While it's being copied to `JustRecorded`, start the app
3. App should wait until file is fully written

**Expected Results:**
- ✅ App detects file but waits
- ✅ Logs show "File not ready" messages
- ✅ Once file is ready, processing begins
- ✅ No errors or corruption

**Check Logs:**
```powershell
Select-String -Path logs\auto_renamer.log -Pattern "not ready|ready"
```

---

### Test 6: Real-Time Monitoring 👁️
**Goal:** Verify app monitors for new files while running

**Steps:**
1. Start the app: `.\venv\Scripts\python.exe main.py`
2. Let it run for 5 seconds
3. Place a new file in `JustRecorded` folder
4. Watch the logs

**Expected Results:**
- ✅ App detects new file immediately
- ✅ File is processed
- ✅ No need to restart app
- ✅ Continuous monitoring works

**Check Logs:**
```powershell
Get-Content logs\auto_renamer.log -Wait
```

---

## Automated Test Script

Create a file `test_batch.ps1`:

```powershell
# Create test files
$testFolder = "D:\Nextcloud\Videos\ScreenRecordings\JustRecorded"
$outputFolder = "D:\Nextcloud\Videos\ScreenRecordings\NameSynced"

# Clear folders
Remove-Item "$testFolder\*" -Force -ErrorAction SilentlyContinue
Remove-Item "$outputFolder\*" -Force -ErrorAction SilentlyContinue

# Create 5 test files
for ($i = 0; $i -lt 5; $i++) {
    $date = (Get-Date).AddHours(-$i).ToString("yyyy-MM-dd_HH-00-00")
    $filename = "$testFolder\$date.mp4"
    
    # Create dummy file (1 MB)
    $file = New-Item -Path $filename -ItemType File -Force
    $file.Length = 1MB
    
    Write-Host "Created: $filename"
}

Write-Host "Test files created. Starting app..."
Write-Host "Run: .\venv\Scripts\python.exe main.py"
```

**Run the test:**
```powershell
.\test_batch.ps1
.\venv\Scripts\python.exe main.py
```

---

## Verification Checklist

### After Each Test, Verify:

- [ ] Logs show no errors
- [ ] Files in `JustRecorded` folder are deleted
- [ ] Files in `NameSynced` folder are created
- [ ] Filenames are correct (with meeting title or original)
- [ ] File sizes match (no corruption)
- [ ] Timestamps are preserved in filename

### Check File Integrity:

```powershell
# Compare file sizes
Get-Item "D:\Nextcloud\Videos\ScreenRecordings\NameSynced\*" | Select-Object Name, Length

# Check file dates
Get-Item "D:\Nextcloud\Videos\ScreenRecordings\NameSynced\*" | Select-Object Name, LastWriteTime
```

---

## Troubleshooting Tests

### If Files Aren't Being Processed:

1. **Check watch folder path:**
   ```powershell
   Test-Path "D:\Nextcloud\Videos\ScreenRecordings\JustRecorded"
   ```

2. **Check file extensions:**
   ```powershell
   Get-Item "D:\Nextcloud\Videos\ScreenRecordings\JustRecorded\*" | Select-Object Extension
   ```

3. **Check logs for errors:**
   ```powershell
   Select-String -Path logs\auto_renamer.log -Pattern "ERROR"
   ```

4. **Verify Google Calendar credentials:**
   ```powershell
   Test-Path "credentials.json"
   Test-Path "token.json"
   ```

### If Files Aren't Being Deleted:

1. **Check if copy succeeded:**
   ```powershell
   Get-Item "D:\Nextcloud\Videos\ScreenRecordings\NameSynced\*"
   ```

2. **Check logs for delete errors:**
   ```powershell
   Select-String -Path logs\auto_renamer.log -Pattern "delete|Delete"
   ```

3. **Verify file permissions:**
   ```powershell
   Get-Acl "D:\Nextcloud\Videos\ScreenRecordings\JustRecorded\*"
   ```

---

## Performance Benchmarks

### Expected Processing Times:

| Scenario | Time | Notes |
|----------|------|-------|
| Single file | 5-10 seconds | Includes Google Calendar query |
| 5 files (batch) | 15-20 seconds | 1 second delay between files |
| 10 files (batch) | 30-40 seconds | Sequential processing |
| Network retry | +6 seconds | 3 attempts × 2 second delays |

### Optimization Tips:

- Increase `file_lock_check_delay` if files are large
- Decrease delays if you have fast internet
- Use `dry_run: true` for testing without side effects

---

## Success Criteria

✅ **All tests pass when:**
- Files are renamed with meeting titles
- Files are copied to output folder
- Original files are deleted
- Batch processing works for multiple files
- Fallback mode works when Google Calendar is unavailable
- Logs are clear and informative
- No data loss occurs
- Performance is acceptable

🎉 **You're ready for production!**
