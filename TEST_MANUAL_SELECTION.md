# Testing Manual Meeting Selection Feature

## Prerequisites
- Application is running and monitoring the watch folder
- Google Calendar is configured with meetings
- Telegram bot is configured and connected
- Internet connection is available

## Test Case 1: No Exact Time Match - Multiple Meetings on Date

### Setup
1. Create a meeting in Google Calendar for today at 09:00 AM: "Team Standup"
2. Create another meeting for today at 02:00 PM: "Project Review"
3. Create a video file with a timestamp that doesn't match any meeting exactly
   - Example: `2026-01-26_11-30-00.mp4` (11:30 AM - between the two meetings)

### Expected Behavior
1. App detects the video file
2. App queries for meetings at 11:30 AM - finds none
3. App queries for all meetings on 2026-01-26 - finds 2 meetings
4. Telegram notification shows:
   ```
   📂 Multiple meetings found for: 2026-01-26_11-30-00.mp4
   Which one should I use?
   
   [Team Standup (09:00)]
   [Project Review (14:00)]
   [❌ Cancel]
   ```
5. Click "Team Standup (09:00)"
6. File is renamed to: `Team Standup_2026-01-26_11-30-00.mp4`
7. File is processed normally (copied, uploaded, etc.)

### Verification
- Check logs for: "Found X meetings on date"
- Check logs for: "Selected meeting: Team Standup"
- Verify file is renamed correctly
- Verify Telegram notification confirms selection

---

## Test Case 2: No Meetings on Date

### Setup
1. Create a video file with a timestamp for a date with no meetings
   - Example: `2026-01-20_10-00-00.mp4` (a date with no calendar events)

### Expected Behavior
1. App detects the video file
2. App queries for meetings at that time - finds none
3. App queries for all meetings on that date - finds none
4. Telegram notification shows:
   ```
   ❓ No meeting found for: 2026-01-20_10-00-00.mp4
   
   Please add it to Google Calendar and click Retry.
   
   [🔄 Retry] [❌ Cancel]
   ```
5. User can click "Retry" after adding a meeting to calendar

### Verification
- Check logs for: "No meetings found on YYYY-MM-DD"
- Verify Telegram shows retry prompt
- Add a meeting to calendar and click Retry
- Verify file is processed after retry

---

## Test Case 3: Exact Time Match (Existing Behavior)

### Setup
1. Create a meeting in Google Calendar for today at 10:00 AM: "Daily Standup"
2. Create a video file with a timestamp matching the meeting time
   - Example: `2026-01-26_10-00-00.mp4`

### Expected Behavior
1. App detects the video file
2. App queries for meetings at 10:00 AM - finds "Daily Standup"
3. File is automatically renamed to: `Daily Standup_2026-01-26_10-00-00.mp4`
4. No Telegram prompt needed (automatic processing)

### Verification
- Check logs for: "Found meeting: Daily Standup"
- Verify file is renamed automatically
- No manual selection prompt should appear

---

## Test Case 4: Multiple Meetings at Same Time

### Setup
1. Create two overlapping meetings for today at 10:00 AM:
   - "Team Meeting"
   - "Project Sync"
2. Create a video file with a timestamp matching that time
   - Example: `2026-01-26_10-00-00.mp4`

### Expected Behavior
1. App detects the video file
2. App queries for meetings at 10:00 AM - finds 2 meetings
3. Telegram notification shows both meetings:
   ```
   📂 Multiple meetings found for: 2026-01-26_10-00-00.mp4
   Which one should I use?
   
   [Team Meeting (10:00)]
   [Project Sync (10:00)]
   [❌ Cancel]
   ```
4. User selects one
5. File is renamed with selected meeting title

### Verification
- Check logs for: "Multiple meetings found"
- Verify both meetings appear in Telegram
- Verify correct meeting is selected and file is renamed

---

## Test Case 5: Cancel Selection

### Setup
1. Create multiple meetings on a date
2. Create a video file that triggers the selection prompt

### Expected Behavior
1. Telegram shows meeting selection prompt
2. User clicks "❌ Cancel"
3. File is NOT renamed
4. File remains in watch folder

### Verification
- Check logs for: "skip" action
- Verify file is not renamed
- Verify file remains in watch folder

---

## Test Case 6: ISO Format Timestamp

### Setup
1. Create a video file with ISO format timestamp
   - Example: `2026-01-26T10-30-00Z.mp4`
2. Create meetings on that date

### Expected Behavior
1. App correctly extracts date from ISO format
2. App queries for meetings on that date
3. Selection prompt appears if needed

### Verification
- Check logs for: "Extracted timestamp from filename"
- Verify date is correctly parsed
- Verify meeting selection works

---

## Logging Verification

### Key Log Messages to Look For

**Successful automatic match:**
```
Found meeting: Meeting Title
```

**No exact match, showing all meetings:**
```
No active meetings found at YYYY-MM-DD HH:MM:SS
Found X meetings on date YYYY-MM-DD
Multiple meetings found for: filename.mp4
```

**User selection:**
```
Selected meeting: Meeting Title
Manual selection successful
```

**No meetings on date:**
```
No meetings found on YYYY-MM-DD
```

**Error handling:**
```
Error processing manual selection: [error details]
Invalid select callback format: [data]
```

---

## Troubleshooting

### Issue: Selection prompt doesn't appear
- Check if Google Calendar API is accessible
- Verify timezone_offset_hours is correct
- Check logs for API errors
- Ensure Telegram bot token is valid

### Issue: Wrong meeting is selected
- Verify meeting times in Google Calendar
- Check timezone settings
- Review logs for timestamp extraction

### Issue: File not renamed after selection
- Check if file is still locked
- Verify output folder is configured
- Check logs for rename errors
- Ensure dry_run is set to false

### Issue: Telegram notification not received
- Verify telegram_bot_token is correct
- Check internet connection
- Review logs for Telegram API errors
- Ensure chat_id is configured

---

## Performance Notes

- First query (exact time match): ~1-2 seconds
- Second query (all meetings on date): ~1-2 seconds
- Total time for manual selection flow: ~3-5 seconds
- Retry logic adds up to 9 seconds on network errors

---

## Edge Cases to Test

1. **Very long meeting titles**: Verify they fit in Telegram buttons
2. **Special characters in meeting titles**: Verify proper encoding
3. **All-day events**: Verify they appear in selection
4. **Recurring meetings**: Verify all instances appear
5. **Meetings from other calendars**: Verify only primary calendar is used
6. **Very old/future dates**: Verify API handles them correctly
7. **Rapid file creation**: Verify queue handles multiple files
8. **Network interruption**: Verify retry logic works
