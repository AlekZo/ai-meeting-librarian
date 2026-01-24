# Offline Mode - Quick Start Guide

## What Changed?
Your application now works even when you don't have internet! 🎉

## How It Works

### ✅ No Internet at Startup?
The app will **wait** for internet to become available before starting. Just reconnect and it will continue automatically.

### ✅ Internet Drops While Running?
Any video files created while offline will be **automatically queued** and processed as soon as internet returns.

### ✅ Internet Restored?
The app **automatically detects** the connection and processes all queued files.

## What You'll See in Logs

### When Internet is Lost
```
✗ Internet connection lost!
Internet not available. Queueing file for later processing: video.mp4
```

### When Internet Returns
```
✓ Internet connection detected!
Processing 3 pending file(s) from offline period...
```

## No Configuration Needed!
Everything works automatically. Just run the app as usual:
```bash
python main.py
```

## Important Notes

- **Files are queued in memory**: If you restart the app while offline, files created during that offline period won't be in the queue anymore
- **Automatic processing**: You don't need to do anything - the app handles everything
- **Check logs**: Look at `logs/auto_renamer.log` to see what's happening

## Troubleshooting

| Problem | Solution |
|---------|----------|
| App stuck waiting for internet | Check your internet connection |
| Files not processing after internet returns | Check logs for errors, verify files still exist |
| Too many pending files | App processes them sequentially, may take a few minutes |

## For More Details
See `OFFLINE_MODE.md` for complete documentation.
