# Offline Mode Support

## Overview
The application now gracefully handles situations where there is no internet connection. Instead of crashing or failing to start, it will:

1. **Wait for Internet During Startup**: If internet is not available when the app starts, it will wait and keep checking until internet is restored before attempting to authenticate with Google Calendar.

2. **Queue Files While Offline**: If a video file is created while internet is unavailable, the file will be queued and processed later when internet returns.

3. **Monitor Connection Status**: The app continuously monitors internet connectivity in the background and automatically processes queued files when internet is restored.

4. **Graceful Degradation**: The file monitoring system starts immediately (doesn't require internet), so files are detected and queued even when offline.

## How It Works

### Internet Connection Check
The app uses a simple but reliable method to check internet connectivity:
- Attempts to connect to Google's DNS server (8.8.8.8:53)
- Timeout is set to 5 seconds
- Non-blocking check that doesn't interfere with normal operation

### Startup Behavior
1. **Configuration validation** - Always happens first
2. **File monitor initialization** - Starts immediately (no internet needed)
3. **Google Calendar authentication** - Waits for internet if needed
4. **Existing files processing** - Processes any files already in the watch folder
5. **Internet monitoring thread** - Starts in background to monitor connection

### Runtime Behavior
- **When internet is available**: Files are processed immediately as they're created
- **When internet is unavailable**: Files are queued in memory
- **When internet is restored**: 
  - All queued files are automatically processed
  - New files continue to be processed normally
  - A log message indicates the number of pending files being processed

### Pending Files Queue
- Files are stored in memory (not persisted to disk)
- If the app is restarted while offline, files created during the offline period will need to be manually processed
- The queue is cleared after files are successfully processed

## Configuration

No additional configuration is required. The offline mode works automatically with default settings:
- Internet check interval: 30 seconds (during normal operation)
- Initial internet wait interval: 10 seconds (during startup)
- Google Calendar API retry attempts: 3 (with 5-second delays)

## Logging

The app logs all offline-related events:
- When internet is lost: `✗ Internet connection lost!`
- When internet is restored: `✓ Internet connection detected!`
- When files are queued: `Internet not available. Queueing file for later processing: [filename]`
- When pending files are processed: `Processing X pending file(s) from offline period...`

## Example Scenarios

### Scenario 1: No Internet at Startup
```
[INFO] Auto-Meeting Video Renamer - Initializing
[INFO] Configuration validated successfully
[INFO] File monitor initialized for: C:\Videos
[WARNING] No internet connection. Waiting for internet before authenticating with Google Calendar...
[DEBUG] Still waiting for internet... (checking again in 10s)
[DEBUG] Still waiting for internet... (checking again in 10s)
[INFO] ✓ Internet connection restored!
[INFO] ✓ Google Calendar authenticated successfully
[INFO] Auto-Meeting Video Renamer is running...
```

### Scenario 2: Internet Loss During Operation
```
[INFO] Processing video file: C:\Videos\2026-01-23_14-30-00.mp4
[WARNING] ✗ Internet connection lost!
[WARNING] Internet not available. Queueing file for later processing: C:\Videos\2026-01-23_14-30-00.mp4
[INFO] ✓ Internet connection detected!
[INFO] Processing 1 pending file(s) from offline period...
[INFO] Processing pending file: C:\Videos\2026-01-23_14-30-00.mp4
[INFO] Successfully renamed '2026-01-23_14-30-00.mp4' to 'Team Meeting_2026-01-23_14-30-00.mp4'
```

## Technical Details

### Modified Files
1. **main.py**
   - Added `socket` import for internet connectivity checks
   - Added `pending_files` list to queue files
   - Added `internet_available` flag to track connection status
   - Added `check_internet_connection()` static method
   - Added `wait_for_internet()` method for startup
   - Added `process_pending_files()` method to handle queued files
   - Added `monitor_internet_connection()` method for background monitoring
   - Modified `initialize()` to wait for internet before Google Calendar auth
   - Modified `on_video_created()` to queue files when offline
   - Modified `run()` to start internet monitoring thread

2. **google_calendar_handler.py**
   - Enhanced `authenticate()` method with retry logic for network errors
   - Added `retry_attempts` and `retry_delay` parameters
   - Better error handling for network-related exceptions

## Troubleshooting

### Files Not Being Processed After Internet Returns
- Check the logs to see if the internet connection was properly detected
- Verify that the files still exist in the watch folder
- Check that Google Calendar authentication is working

### App Stuck Waiting for Internet
- Verify your internet connection is actually working
- Check if there's a firewall blocking connections to 8.8.8.8:53
- Try restarting the app

### Too Many Pending Files
- The app processes pending files sequentially with 1-second delays between them
- Large queues may take several minutes to process
- Check the logs for any errors during processing
