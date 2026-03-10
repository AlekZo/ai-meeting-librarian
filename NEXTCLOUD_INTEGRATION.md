# Nextcloud Integration Guide

Your Auto Meeting Video Renamer is designed to work seamlessly with Nextcloud synced folders.

---

## 🎯 Overview

All your app folders are synced with Nextcloud:
- ✓ `watch_folder` - Synced
- ✓ `to_transcribe_folder` - Synced
- ✓ `renamed_folder` - Synced
- ✓ `transcribed_folder` - Synced
- ✓ `logs/` - Synced (for backup)

This guide explains how the app handles Nextcloud-specific issues.

---

## 🔒 File Locking (Most Common Issue)

### What Happens
When Nextcloud syncs files, it may temporarily lock them:
```
1. File uploaded to Nextcloud
2. Nextcloud locks file during sync
3. App tries to rename/move file
4. Gets "file locked" error
5. App automatically retries
6. After 2-5 seconds, lock releases
7. App successfully processes file
```

### How App Handles It
- **Automatic retry**: Up to 10 attempts
- **Backoff delay**: 2 seconds between retries
- **Total wait**: ~20 seconds before giving up
- **Logging**: All lock attempts logged

### What You'll See in Logs
```
[WATCH_FOLDER] Processing video file for renaming: file.mp4
Move attempt 1/10 failed, retrying in 2s...: [Errno 32] The process cannot access the file...
Move attempt 2/10 failed, retrying in 2s...
Move attempt 3/10 succeeded
✓ File moved to renamed folder
```

### Best Practices
1. **Don't manually edit files** while app is running
2. **Wait for sync to complete** before starting app
3. **Check Nextcloud status** - green checkmarks = synced
4. **Avoid network interruptions** during file operations

---

## 🌐 Nextcloud Sync Status

### Healthy Sync
```
✓ All folders show green checkmarks
✓ No "sync in progress" indicators
✓ File status shows "synced"
✓ No error messages in Nextcloud
```

### Unhealthy Sync
```
⚠️ Folders show blue arrows (syncing)
⚠️ "Sync in progress" indicator
⚠️ File status shows "syncing"
✗ Error messages in Nextcloud
```

### What App Does
- **During sync**: Waits for lock to release
- **After sync**: Processes file normally
- **If sync fails**: Queues file for retry

---

## 📡 Internet & Nextcloud Connection

### Scenario 1: Internet Down
```
Timeline:
1. Internet disconnects
2. Nextcloud shows "offline" status
3. App detects no internet
4. New files get queued locally
5. Telegram notified: "Pending files queued (offline)"
6. Internet reconnects
7. Nextcloud syncs queued files
8. App processes files
```

### Scenario 2: Nextcloud Server Down
```
Timeline:
1. Nextcloud server is down
2. Nextcloud client shows "error"
3. App detects sync failure
4. Files queued locally
5. Telegram notified
6. Nextcloud server comes back
7. Nextcloud syncs files
8. App processes files
```

### Scenario 3: Network Slow
```
Timeline:
1. Network is slow (high latency)
2. File operations take longer
3. App retries with backoff
4. Eventually succeeds
5. Nextcloud syncs result
```

---

## 🔄 Sync Workflow

### Normal Processing (With Nextcloud)
```
1. File created in watch_folder
   ↓ (Nextcloud syncs to server)
2. App detects file
   ↓ (Waits for Nextcloud lock to release)
3. App renames file
   ↓ (Nextcloud syncs renamed file)
4. App moves to renamed_folder
   ↓ (Nextcloud syncs move)
5. App moves to to_transcribe_folder
   ↓ (Nextcloud syncs to server)
6. Processing continues
```

### With File Lock
```
1. File created in watch_folder
   ↓ (Nextcloud locks file during sync)
2. App detects file
   ↓ (Tries to rename, gets lock error)
3. App waits 2 seconds
   ↓ (Nextcloud still syncing)
4. App retries rename
   ↓ (Lock released, rename succeeds)
5. Nextcloud syncs renamed file
   ↓ (Normal processing continues)
```

---

## 📊 Monitoring Nextcloud Status

### Check Nextcloud Sync Status
```bash
# Windows - Check Nextcloud client
# Look for: Green checkmark = synced
#           Blue arrows = syncing
#           Red X = error

# Linux/Mac - Check sync status
# Command: nextcloud-cmd status
```

### Check App Logs for Sync Issues
```bash
# Watch for file lock messages
grep -i "lock" logs/auto_renamer.log

# Watch for sync errors
grep -i "sync" logs/auto_renamer.log

# Watch for retry messages
grep -i "retry" logs/auto_renamer.log
```

### Check State File
```bash
cat logs/app_state.json

# Look for:
# - "internet_available": true/false
# - "error_count": should be low
# - "pending_files": should be empty when online
```

---

## ⚙️ Configuration for Nextcloud

### Recommended Settings
```python
# In main.py, these are already optimized for Nextcloud:

# File lock retry settings
file_lock_check_delay = 2        # Wait 2 seconds between retries
file_lock_check_attempts = 20    # Try up to 20 times

# HTTP timeout settings (for Nextcloud API)
connection_timeout = 10          # 10 seconds
read_timeout = 30                # 30 seconds

# Retry settings
max_retries = 3                  # 3 attempts per request
```

### Tuning for Slow Nextcloud
If your Nextcloud is slow:
```python
# Increase delays
file_lock_check_delay = 5        # Wait 5 seconds
file_lock_check_attempts = 30    # Try 30 times

# Increase timeouts
connection_timeout = 20          # 20 seconds
read_timeout = 60                # 60 seconds
```

### Tuning for Fast Nextcloud
If your Nextcloud is fast:
```python
# Decrease delays
file_lock_check_delay = 1        # Wait 1 second
file_lock_check_attempts = 10    # Try 10 times

# Decrease timeouts
connection_timeout = 5           # 5 seconds
read_timeout = 15                # 15 seconds
```

---

## 🚨 Common Nextcloud Issues

### Issue 1: "File is locked" Errors
**Cause**: Nextcloud is syncing the file
**Solution**: App automatically retries (built-in)
**What to do**: Nothing - app handles it

**Check logs**:
```bash
grep "locked" logs/auto_renamer.log
# Should see: "Move attempt X/10 failed, retrying..."
# Eventually: "Move attempt X/10 succeeded"
```

### Issue 2: Files Not Syncing to Nextcloud
**Cause**: Nextcloud sync is paused or offline
**Solution**: Check Nextcloud client status
**What to do**: 
1. Open Nextcloud client
2. Check if sync is paused
3. Check if online
4. Resume sync if paused

**Check logs**:
```bash
tail -f logs/auto_renamer.log
# Should see: "Internet connection restored!"
# Then: "Processing X pending files..."
```

### Issue 3: Nextcloud Server Error
**Cause**: Nextcloud server is down or unreachable
**Solution**: Wait for server to come back online
**What to do**:
1. Check Nextcloud server status
2. Check network connectivity
3. Wait for recovery
4. App will auto-retry

**Check logs**:
```bash
grep -i "error" logs/auto_renamer.log
# Look for: "Circuit breaker open for"
# This means service is temporarily unavailable
```

### Issue 4: Sync Conflicts
**Cause**: File modified in multiple places
**Solution**: Nextcloud creates conflict copies
**What to do**:
1. Check Nextcloud for conflict files
2. Resolve conflicts manually
3. App will process resolved files

**Check logs**:
```bash
ls -la watch_folder/
# Look for: "filename (conflicted copy).mp4"
```

---

## 🔍 Troubleshooting Nextcloud Issues

### Step 1: Check Nextcloud Status
```bash
# Windows: Open Nextcloud client
# Look for: Green checkmark (synced)
#           Blue arrows (syncing)
#           Red X (error)

# If error: Click to see details
```

### Step 2: Check Network
```bash
ping 8.8.8.8                    # Internet
ping <nextcloud-server>         # Nextcloud server
```

### Step 3: Check App Logs
```bash
tail -f logs/auto_renamer.log

# Look for:
# - "locked" = file lock (normal, auto-retried)
# - "error" = actual error
# - "retry" = retry in progress
```

### Step 4: Check App State
```bash
cat logs/app_state.json | python -m json.tool

# Look for:
# - "internet_available": true
# - "error_count": should be low
# - "pending_files": should be empty
```

### Step 5: Manual Sync
```bash
# Force Nextcloud to sync
# Windows: Right-click folder → Sync now
# Linux/Mac: nextcloud-cmd sync
```

---

## 📈 Performance Tips

### Optimize for Nextcloud
1. **Keep files small** - Faster sync
2. **Batch operations** - Fewer sync events
3. **Schedule processing** - Off-peak hours
4. **Monitor bandwidth** - Don't saturate connection
5. **Use local network** - Faster than internet

### Monitor Sync Performance
```bash
# Check sync speed
# Windows: Nextcloud client → Activity
# Shows: Files synced, speed, time remaining

# Check app performance
cat logs/app_state.json
# Look for: "error_count" (should be low)
```

### Reduce Lock Contention
1. **Don't edit files manually** while app runs
2. **Close files** before app processes them
3. **Wait for sync** before starting app
4. **Avoid simultaneous operations** on same files

---

## 🔐 Data Safety with Nextcloud

### Backup Strategy
Your app state is automatically backed up:
```
logs/app_state.json          → Synced to Nextcloud
logs/meeting_log_queue.json  → Synced to Nextcloud
logs/processed_*.json        → Synced to Nextcloud
```

### Recovery from Nextcloud
If your local files are lost:
```bash
# Nextcloud has copies on server
# Restore from Nextcloud:
# 1. Open Nextcloud web interface
# 2. Navigate to folder
# 3. Download files
# 4. Or use Nextcloud client to sync
```

### Conflict Resolution
If conflicts occur:
```bash
# Nextcloud creates: filename (conflicted copy).mp4
# App will process both versions
# You can manually delete duplicates later
```

---

## 📞 Support

### Nextcloud-Specific Issues
1. Check Nextcloud client status
2. Check network connectivity
3. Review app logs for details
4. Check Nextcloud server status

### App-Specific Issues
1. Check logs: `tail -f logs/auto_renamer.log`
2. Check state: `cat logs/app_state.json`
3. Review RESILIENCE_FEATURES.md
4. Check TESTING_GUIDE.md

### Combined Issues
1. Verify Nextcloud is synced
2. Verify internet is connected
3. Check app logs
4. Check app state
5. Restart app if needed

---

## ✅ Nextcloud Compatibility Checklist

Before running the app:
- [ ] Nextcloud client installed and running
- [ ] All folders synced (green checkmarks)
- [ ] No active syncs in progress
- [ ] No file locks visible
- [ ] Internet connection stable
- [ ] Nextcloud server accessible
- [ ] Sufficient disk space available
- [ ] File permissions correct

Before upgrading:
- [ ] Nextcloud sync is idle
- [ ] All folders fully synced
- [ ] No pending operations
- [ ] Recent backup exists

---

## 🎯 Best Practices

### Daily
- ✓ Check Nextcloud status (green checkmarks)
- ✓ Monitor app logs for errors
- ✓ Verify files are processing

### Weekly
- ✓ Check app state file
- ✓ Review error count
- ✓ Check pending queue size
- ✓ Verify Nextcloud sync health

### Monthly
- ✓ Review full logs
- ✓ Check storage usage
- ✓ Verify backup integrity
- ✓ Test recovery procedure

---

## 🚀 Optimization Tips

### For Faster Processing
1. **Reduce file size** - Faster sync
2. **Use SSD** - Faster local operations
3. **Increase bandwidth** - Faster Nextcloud sync
4. **Schedule off-peak** - Less network contention

### For Better Reliability
1. **Monitor regularly** - Catch issues early
2. **Keep logs** - For troubleshooting
3. **Test recovery** - Know your backup works
4. **Update regularly** - Get bug fixes

### For Lower Latency
1. **Use local Nextcloud** - If possible
2. **Optimize network** - Reduce hops
3. **Reduce file count** - Fewer sync operations
4. **Batch operations** - Fewer sync events

---

## 📚 Related Documentation

- [RESILIENCE_FEATURES.md](RESILIENCE_FEATURES.md) - General resilience
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Upgrade guide
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing procedures
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick commands

---

**Your app is Nextcloud-optimized and ready to go!** 🎉

All file operations automatically handle Nextcloud locks and sync delays.
Just run the app and let it work!
