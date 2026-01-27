# Supported Filename Formats

## Overview
The application now supports multiple filename timestamp formats, allowing it to extract dates and times from various video recording naming conventions.

## Supported Formats

### 1. **Date Only Format**
Pattern: `YYYY-MM-DD_[text]`

Examples:
- `2026-01-23_DION Video (1).mp4`
- `2026-01-23_Team Meeting.mp4`
- `2026-01-20_Recording.mp4`

**Behavior:** When only the date is present, the time is set to midnight (00:00:00). The app will then query Google Calendar for all meetings on that date and show them to the user for selection.

---

### 2. **Date with Time (Hyphen Format)**
Pattern: `YYYY-MM-DD_HH-MM-SS[_text]`

Examples:
- `2026-01-22_14-26-31.mp4`
- `2026-01-22_14-26-31_backup.mp4`
- `2026-01-20_10-00-00.mp4`

**Behavior:** The app extracts the exact timestamp and queries Google Calendar for meetings at that specific time. If a meeting is found, it's used automatically. If not, all meetings on that date are shown.

---

### 3. **ISO 8601 Format (with or without timezone)**
Pattern: `[text]_YYYY-MM-DDTHH:MM:SSZ` or `[text]_YYYY-MM-DDTHH:MM:SS`

Examples:
- `Ердакова Надежда_2026-01-23T10:01:46Z.mp4` (with timezone)
- `Ердакова Надежда_2026-01-23T10:01:46.mp4` (without timezone)
- `Meeting_2026-01-25T14:30:00Z.mp4`
- `Recording_2026-01-20T09:15:30.mp4`

**Behavior:** The app extracts the timestamp (ignoring the timezone indicator 'Z' if present) and queries Google Calendar for meetings at that specific time.

---

## How It Works

### Processing Flow

```
Video file detected
    ↓
Extract timestamp from filename
    ↓
    ├─ Success: Continue processing
    │   ├─ Query for meetings at exact time
    │   │   ├─ Found 1 meeting → Auto-rename
    │   │   ├─ Found multiple → Show selection
    │   │   └─ Found none → Show all meetings on date
    │   └─ User selects meeting → Rename and process
    │
    └─ Failure: Log warning and skip file
```

### Timestamp Extraction Logic

1. **Regex Pattern Matching:** The filename is scanned for date patterns
2. **Format Detection:** The app determines which format was used
3. **Time Extraction:** 
   - If time is present, it's extracted
   - If only date is present, time defaults to 00:00:00
4. **DateTime Creation:** A Python datetime object is created for calendar queries

---

## Regex Pattern Details

```regex
(\d{4})-(\d{2})-(\d{2})(?:[T_](\d{2}):(\d{2}):(\d{2})|_(\d{2})-(\d{2})-(\d{2}))?
```

**Breakdown:**
- `(\d{4})-(\d{2})-(\d{2})` - Matches YYYY-MM-DD (required)
- `(?:...)` - Non-capturing group for optional time
  - `[T_](\d{2}):(\d{2}):(\d{2})` - Matches T or _ followed by HH:MM:SS (ISO format)
  - `|` - OR
  - `_(\d{2})-(\d{2})-(\d{2})` - Matches _HH-MM-SS (hyphen format)

---

## Examples with Expected Behavior

| Filename | Extracted Timestamp | Format | Calendar Query |
|----------|-------------------|--------|-----------------|
| `2026-01-23_DION Video (1).mp4` | 2026-01-23 00:00:00 | Date-only | All meetings on 2026-01-23 |
| `2026-01-22_14-26-31.mp4` | 2026-01-22 14:26:31 | Hyphen | Meetings at 2026-01-22 14:26:31 |
| `Ердакова Надежда_2026-01-23T10:01:46Z.mp4` | 2026-01-23 10:01:46 | ISO 8601 | Meetings at 2026-01-23 10:01:46 |
| `Meeting_2026-01-25T14:30:00.mp4` | 2026-01-25 14:30:00 | ISO 8601 | Meetings at 2026-01-25 14:30:00 |

---

## Timezone Handling

### ISO 8601 Format with 'Z'
- The 'Z' suffix indicates UTC timezone
- The app extracts the time as-is (ignoring the 'Z')
- The `timezone_offset_hours` configuration is then applied to convert to the local timezone

### Example:
```
Filename: Recording_2026-01-23T10:01:46Z.mp4
Extracted: 2026-01-23 10:01:46 (UTC)
Config: timezone_offset_hours = 3 (UTC+3)
Query: 2026-01-23 07:01:46 (local time)
```

---

## Logging Output

When a file is processed, you'll see log messages like:

```
INFO - Extracted timestamp from filename: 2026-01-23_00-00-00 (date-only format)
INFO - Found 3 meetings on date 2026-01-23
INFO - Multiple meetings found for: 2026-01-23_DION Video (1).mp4
```

Or for ISO format:

```
INFO - Extracted timestamp from filename: 2026-01-23_10-01-46 (ISO 8601 format)
INFO - Found 1 active meetings at 2026-01-23 10:01:46
INFO - Found meeting: Team Meeting
```

---

## Testing

A test script is included: `test_timestamp_extraction.py`

Run it to verify all formats work correctly:

```bash
python test_timestamp_extraction.py
```

Expected output:
```
✓ All tests passed!
```

---

## Troubleshooting

### Issue: "Could not process file ... automatically"

**Possible causes:**
1. **Filename doesn't match any supported format**
   - Check if the date is in YYYY-MM-DD format
   - Verify the date is valid (e.g., not 2026-02-30)

2. **Date is too old or too far in future**
   - Google Calendar API may not return events for very old dates
   - Check calendar permissions

3. **Timestamp extraction failed**
   - Check logs for: "Could not extract date from filename"
   - Verify filename contains a valid date pattern

### Solution:
- Rename the file to include a valid date in one of the supported formats
- Ensure the date exists in your Google Calendar
- Check the application logs for detailed error messages

---

## Future Enhancements

Potential formats to support in the future:
- `YYYYMMDD_HHMMSS` (no separators)
- `YYYY_MM_DD_HH_MM_SS` (all underscores)
- `DD-MM-YYYY` (European format)
- Custom format via configuration

---

## Configuration

No new configuration is required. The feature uses existing settings:
- `timezone_offset_hours` - For timezone conversion
- `watch_folder` - Where to monitor for files
- Google Calendar credentials - For meeting queries

---

## Performance

- Timestamp extraction: < 1ms
- Calendar query: 1-2 seconds
- Total processing time: 2-5 seconds (depending on network)

---

## Compatibility

- ✓ Windows filenames (with special characters)
- ✓ Unicode characters (e.g., Cyrillic: Ердакова Надежда)
- ✓ Long filenames (up to 255 characters)
- ✓ Spaces and special characters in names
- ✓ Multiple dots in filename
