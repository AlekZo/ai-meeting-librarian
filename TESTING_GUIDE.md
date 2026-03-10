# Testing Guide - Verify Resilience Features

This guide walks you through testing each resilience feature to ensure everything works correctly.

---

## Quick Test (5 minutes)

### Test 1: Basic Startup ✓
```bash
# Windows
run_with_autorestart.bat

# Or directly
python main.py

# Expected output:
# ✓ Application initialization complete
# ✓ Auto-Meeting Video Renamer is running...
```

### Test 2: Auto-Restart on Crash
```bash
# While app is running in another window:

# Windows PowerShell
$proc = Get-Process python | where {$_.ProcessName -eq 'python'}
Stop-Process -Id $proc.Id -Force

# Or use Task Manager → End Task on python.exe

# Expected: App restarts within 5 seconds

# Check logs:
tail -f logs/auto_renamer.log
# Should see: "Starting application (attempt X)"
```

### Test 3: State Recovery
```bash
# After app restarts from crash:
cat logs/app_state.json

# Expected to show:
# - "restart_count": 1 (increased)
# - "initialization_complete": true
# - "pending_files": [] (empty or with test files)
```

---

## Complete Tests (30 minutes)

### Test Suite 1: Network Resilience

#### Test 1.1: Internet Disconnection
```
Steps:
1. Start app normally
2. Disconnect network (unplug cable or disable NIC)
3. Drop a video file in watch_folder
4. Wait 10 seconds
5. Reconnect network
6. Monitor logs

Expected:
- File gets queued to pending_files
- Telegram message: "Pending files queued (offline)"
- When video reconnects, file auto-processes
- Log shows: "Internet connection restored!"
```

#### Test 1.2: API Timeout Retry
```
Steps:
1. Start app with bad network (throttle connection to 56k)
2. Drop a video file
3. Monitor logs for retry messages
4. Restore network to normal

Expected:
- See "Retrying in 1.0s..."
- Then "Retrying in 2.0s..."
- Then "Retrying in 4.0s..."
- Eventually succeeds or gives up gracefully
```

#### Test 1.3: Circuit Breaker Activation
```
Steps:
1. Start app
2. Block access to api.telegram.org (firewall rule)
3. Trigger action that uses Telegram (drop file)
4. Wait 30+ seconds
5. Unblock api.telegram.org

Expected:
- See "Circuit breaker open for telegram"
- Requests stop being attempted
- After ~60 seconds, circuit attempts reset
- When Telegram is accessible again, requests resume
```

### Test Suite 2: Crash Recovery

#### Test 2.1: Graceful Shutdown
```
Steps:
1. Start app
2. Press Ctrl+C
3. Check logs and state file

Expected:
- App stops cleanly
- Log shows: "Received interrupt signal"
- app_state.json shows "restart_count": 0 (reset)
- No auto-restart (different from crash)
```

#### Test 2.2: Forced Crash
```
Steps:
1. Start with: run_with_autorestart.bat
2. Kill process via Task Manager
3. Wait 6 seconds
4. Check if app restarted

Expected:
- App restarts within 5 seconds
- restart_count increases in state file
- Recovery mode NOT entered (single crash is normal)
```

#### Test 2.3: Crash Loop Detection
```
Steps:
1. Introduce a bug that crashes on startup
   (e.g., delete config.json temporarily)
2. Run: run_with_autorestart.bat
3. Watch it restart multiple times
4. After 5+ restarts, check state file

Expected:
- App tries up to 20 times
- State file eventually shows: "crash_recovery_mode": true
- After restart 5, should show reduced activity
- Fix the bug and restart - recovery mode clears
```

#### Test 2.4: Pending Files Survival
```
Steps:
1. Disconnect network
2. Drop 3 video files in watch_folder
3. Observe files get queued
4. Force crash: Kill the process
5. Auto-restart via wrapper
6. Reconnect network

Expected:
- After restart, files still in pending_files
- Files auto-process when network available
- No data loss occurred
```

### Test Suite 3: Health Monitoring

#### Test 3.1: Health Check Reports
```
Steps:
1. Start app normally
2. Wait 5 minutes
3. Check logs for health monitoring

Expected:
- No alerts (app is healthy)
- Or see warnings if there are issues
- app_state.json updates with health metrics
```

#### Test 3.2: High Error Detection
```
Steps:
1. Configure invalid credentials (wrong API key)
2. Start app
3. Try to process file
4. Watch error count increase
5. After 10+ errors, check for recovery mode

Expected:
- Errors logged to app_state.json
- After 10 errors, recovery mode activates
- Telegram notification sent
- app_state.json shows high error count
```

### Test Suite 4: Offline Queue Management

#### Test 4.1: Queue Persistence
```
Steps:
1. Disconnect internet
2. Drop 5 video files
3. Observe: logs/meeting_log_queue.json grows
4. Kill app (crash simulation)
5. Restart app
6. Reconnect internet

Expected:
- Queue survived the restart
- Files process despite the crash
- Queue clears as files process
```

#### Test 4.2: Large Queue Handling
```
Steps:
1. Offline mode, drop 50+ files
2. Telegram should notify with queue summary
3. Reconnect internet
4. Monitor processing

Expected:
- Queue shows all files
- Processing batches them intelligently
- No "out of memory" errors
- Files eventually all process
```

---

## Validation Checks

### Log File Analysis
```bash
# What to look for in logs/auto_renamer.log

✓ Good signs:
- "✓ Application initialization complete"
- "✓ Internet connection restored!"
- "✓ File moved to transcription folder"
- No ERROR or CRITICAL messages

✗ Bad signs:
- "ERROR:" or "CRITICAL:" anywhere
- "Circuit breaker open" too often
- "Crash recovery mode" unexpectedly
- Repeated "Retrying" messages forever
```

### State File Validation
```bash
# What to look for in logs/app_state.json

✓ Good state:
{
  "initialization_complete": true,
  "internet_available": true,
  "restart_count": 0,              # 0 = graceful shutdown, 1-2 = normal, 5+ = issues
  "error_count": 0,                # 0-5 is good, 10+ is problem
  "crash_recovery_mode": false,
  "pending_files": []              # Empty when online
}

✗ Bad state:
{
  "error_count": 25,               # Too many errors
  "crash_recovery_mode": true,     # App detected issues
  "restart_count": 15,             # Restart loop detected
  "pending_files": ["100 files"]   # Large queue
}
```

### File Processing Validation
```bash
# Verify files are being processed

# Check watch folder for new files
ls logs/processed_watch_files.json

# Check transcribe folder
ls logs/processed_transcribe_files.json

# Should show recent entries with timestamps matching current time
```

---

## Performance Validation

### Resource Usage Check
```bash
# Monitor while app is running

# Windows Task Manager:
# - Memory: Should be 50-70 MB
# - CPU: Should be < 5% (mostly idle)
# - Network: Should see activity only during processing

# Terminal commands:
ps aux | grep python              # Linux/Mac memory usage
tasklist | findstr python         # Windows process list
```

### Response Time Check
```bash
# Check file processing latency

# From when file is detected to when processing starts:
grep "Processing video file" logs/auto_renamer.log

# Good latency: < 1 second
# Acceptable: 1-5 seconds
# Poor: > 10 seconds
```

---

## Stress Testing

### Test 1: High File Volume
```bash
Steps:
1. Create 100+ test video files
2. Copy all to watch_folder
3. Monitor system while processing
4. Check for:
   - Memory leaks
   - CPU spikes
   - Graceful degradation

Expected:
- App handles volume gracefully
- No crashes
- Steady processing rate
```

### Test 2: Long Network Outage
```bash
Steps:
1. Start processing files
2. Disconnect network for 1+ hour
3. Drop new files during outage
4. Reconnect
5. Monitor recovery

Expected:
- All files queued
- Queue survives restart
- Processing resumes cleanly
- No data loss
```

### Test 3: Repeated Crashes
```bash
Steps:
1. Kill app 10 times rapidly
2. Each time, restart via wrapper
3. Monitor state progression

Expected:
- Restarts 1-5: restart_count increments
- After restart 5: enters recovery mode
- After restart 20: stops trying
- Can manually reset by deleting app_state.json
```

---

## Automated Test Suite

Create `test_resilience.py`:

```python
#!/usr/bin/env python3
import os
import json
import time
import subprocess
import signal

def test_startup():
    """Test basic startup"""
    print("Testing startup...")
    
    # Remove old state
    if os.path.exists("logs/app_state.json"):
        os.remove("logs/app_state.json")
    
    # Start app
    proc = subprocess.Popen(["python", "main.py"])
    time.sleep(5)
    
    # Check if still running
    assert proc.poll() is None, "App should still be running"
    
    # Check state file created
    assert os.path.exists("logs/app_state.json"), "State file should exist"
    
    with open("logs/app_state.json") as f:
        state = json.load(f)
        assert state["initialization_complete"], "Should be initialized"
    
    proc.terminate()
    print("✓ Startup test passed")

def test_state_persistence():
    """Test that state survives restarts"""
    print("Testing state persistence...")
    
    # Start app
    proc = subprocess.Popen(["python", "main.py"])
    time.sleep(5)
    
    # Read initial state
    with open("logs/app_state.json") as f:
        state1 = json.load(f)
    
    # Kill app
    proc.terminate()
    time.sleep(2)
    
    # Restart app
    proc = subprocess.Popen(["python", "main.py"])
    time.sleep(5)
    
    # Read new state
    with open("logs/app_state.json") as f:
        state2 = json.load(f)
    
    # Restart count should increase
    assert state2["restart_count"] > state1["restart_count"], "Should increment restart count"
    
    proc.terminate()
    print("✓ State persistence test passed")

if __name__ == "__main__":
    test_startup()
    test_state_persistence()
    print("\n✓ All tests passed!")
```

Run it:
```bash
python test_resilience.py
```

---

## Test Report Template

```
Date: _______________
Tester: ______________

STARTUP TESTS
[ ] App starts without errors          Status: _____
[ ] Initialization message appears     Status: _____
[ ] State file created                 Status: _____
[ ] Logs look normal                   Status: _____

CRASH RECOVERY TESTS
[ ] Graceful shutdown (Ctrl+C)         Status: _____
[ ] Process kill recovery              Status: _____
[ ] File recovery after crash          Status: _____
[ ] No data loss on crash              Status: _____

NETWORK TESTS
[ ] File queued when offline           Status: _____
[ ] Circuit breaker works              Status: _____
[ ] Auto-retry on timeout              Status: _____
[ ] Queue processing on reconnect      Status: _____

HEALTH TESTS
[ ] No errors in logs                  Status: _____
[ ] Memory stays stable                Status: _____
[ ] CPU usage reasonable               Status: _____
[ ] Telegram notifications working     Status: _____

STRESS TESTS
[ ] 100+ files handled                 Status: _____
[ ] 1+ hour offline survived           Status: _____
[ ] 10x rapid restart                  Status: _____
[ ] Large queue processed              Status: _____

OVERALL: _______________
Issues found: _________________
Actions taken: _________________
```

---

## Success Criteria

All tests pass if:
- ✓ App starts cleanly
- ✓ Auto-restart works (if using wrapper)
- ✓ State survives crashes
- ✓ Files queue when offline
- ✓ Queue processes on reconnect
- ✓ No error spam in logs
- ✓ Memory stable
- ✓ Telegram works (if configured)
- ✓ CPU < 10% idle
- ✓ No hangs or freezes

---

## Troubleshooting Failed Tests

### If startup fails:
```bash
# Check for syntax errors
python -m py_compile main.py
python -m py_compile resilience_utils.py
python -m py_compile state_recovery.py

# Run with debug
python -c "import resilience_utils; print('OK')"
```

### If crash recovery fails:
```bash
# Check wrapper script
cat run_with_autorestart.bat
# Should have sensible restart logic

# Manual test:
# 1. Start: python main.py
# 2. Kill from another window
# 3. Check if still process or fully dead
```

### If network tests fail:
```bash
# Check connectivity
ping 8.8.8.8
ping api.telegram.org

# Check logs for circuit breaker spam
grep -i "circuit" logs/auto_renamer.log
```

---

## Next Steps After Passing Tests

1. ✅ Deploy to production
2. ✅ Monitor for 24 hours
3. ✅ Set up automated monitoring
4. ✅ Schedule weekly health checks
5. ✅ Document any issues found

You're ready! 🎉
