# Manual Meeting Selection Feature

## Overview
When a video file cannot be automatically matched to a meeting (because no meeting was found at the exact recording time), the application now shows all meetings on that date, allowing the user to manually select the correct meeting via Telegram.

## Changes Made

### 1. **google_calendar_handler.py**
Added new method `get_all_meetings_on_date()`:
- Fetches all meetings on a specific date (not just those overlapping with a specific time)
- Returns up to 50 meetings for the given date
- Includes retry logic for network errors
- Handles both timezone-aware and naive datetime objects

### 2. **main.py - _notify_no_meeting() method**
Updated to show all meetings on the date instead of just asking to retry:
- Extracts the date from the video filename
- Calls `get_all_meetings_on_date()` to fetch all meetings on that date
- If meetings are found, shows them as selection options via `_prompt_meeting_selection()`
- If no meetings are found on that date, shows the original "Retry" prompt

### 3. **main.py - _prompt_meeting_selection() method**
Enhanced to support both automatic and manual selection scenarios:
- Shows up to 10 meetings (increased from 5)
- Includes meeting time in button labels for clarity (e.g., "Team Meeting (14:30)")
- Uses URL-safe encoding for file paths in callback data
- Format: `select:meeting_id:encoded_file_path`
- Stores meeting metadata in callback map for reference

### 4. **main.py - handle_telegram_callback() method**
Updated the "select:" callback handler:
- Properly decodes URL-encoded file paths
- Fetches the selected meeting from Google Calendar
- Extracts the meeting start time for logging
- Renames the file with the selected meeting title
- Continues with the normal post-rename flow (copy, upload, etc.)

## User Flow

### Scenario: No Exact Time Match
1. Video file is detected: `2026-01-23_DION Video (1).mp4`
2. App extracts timestamp: `2026-01-23 10:44:24`
3. App queries Google Calendar for meetings at that exact time
4. No meetings found at that exact time
5. App queries for ALL meetings on `2026-01-23`
6. Telegram notification shows all meetings on that date:
   ```
   📂 Multiple meetings found for: 2026-01-23_DION Video (1).mp4
   Which one should I use?
   
   [Team Meeting (09:00)]
   [Project Review (10:30)]
   [Client Call (14:00)]
   [❌ Cancel]
   ```
7. User clicks the correct meeting
8. File is renamed and processed normally

### Scenario: No Meetings on Date
1. Video file is detected
2. App extracts timestamp
3. No meetings found at exact time
4. No meetings found on that entire date
5. Telegram notification shows:
   ```
   ❓ No meeting found for: 2026-01-23_DION Video (1).mp4
   
   Please add it to Google Calendar and click Retry.
   
   [🔄 Retry] [❌ Cancel]
   ```

## Technical Details

### Date Extraction
The app supports multiple date formats in filenames:
- `2026-01-23_14-26-31` (standard format)
- `2026-01-23T10:01:46Z` (ISO format)

### Timezone Handling
- Respects the `timezone_offset_hours` configuration
- Converts local time to UTC for Google Calendar queries
- Properly handles timezone-aware and naive datetime objects

### Callback Data Format
- Uses URL encoding to safely pass file paths in Telegram callback data
- Format: `select:meeting_id:encoded_file_path`
- Automatically decoded when processing the callback

## Configuration
No new configuration options are required. The feature uses existing settings:
- `timezone_offset_hours`: For timezone conversion
- `telegram_bot_token`: For Telegram notifications
- `google_credentials_path` and `google_token_path`: For Calendar access

## Error Handling
- Network errors during Calendar queries are retried up to 3 times
- Invalid callback formats are logged and user is notified
- File path encoding/decoding is handled safely
- Meeting fetch errors are caught and reported to the user

## Logging
All actions are logged with appropriate levels:
- INFO: Meeting selection prompts, user selections
- WARNING: No meetings found scenarios
- ERROR: API errors, invalid formats
- DEBUG: Calendar query details

## Testing
To test this feature:
1. Create a video file with a timestamp that doesn't match any meeting exactly
2. Ensure there are meetings on that date in Google Calendar
3. The app should show all meetings on that date
4. Click on the correct meeting
5. Verify the file is renamed correctly and processed

## Future Enhancements
- Add pagination for dates with many meetings (>10)
- Add search/filter functionality for meeting selection
- Add ability to create a new meeting from Telegram if none match
- Add confirmation dialog before renaming with manually selected meeting
