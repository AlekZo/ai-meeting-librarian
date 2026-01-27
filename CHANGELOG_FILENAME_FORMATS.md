# Changelog - Filename Format Support

## Version: Enhanced Timestamp Extraction

### 🎯 Problem Solved
Previously, the application only supported filenames with the exact format: `YYYY-MM-DD_HH-MM-SS.mp4`

Files like `2026-01-23_DION Video (1).mp4` would fail with:
```
WARNING - Could not process file ... automatically.
```

### ✨ Solution Implemented
Updated the timestamp extraction logic to support **3 different filename formats**:

1. **Date-only format** (new)
   - `2026-01-23_DION Video (1).mp4`
   - `2026-01-23_Team Meeting.mp4`

2. **Date with time (hyphen format)** (existing, improved)
   - `2026-01-22_14-26-31.mp4`
   - `2026-01-20_10-00-00.mp4`

3. **ISO 8601 format** (new)
   - `Ердакова Надежда_2026-01-23T10:01:46Z.mp4`
   - `Meeting_2026-01-25T14:30:00.mp4`

### 📝 Files Modified

#### `file_renamer.py`
- **Updated:** `TIMESTAMP_PATTERN` regex
  - Old: `r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})'`
  - New: `r'(\d{4})-(\d{2})-(\d{2})(?:[T_](\d{2}):(\d{2}):(\d{2})|_(\d{2})-(\d{2})-(\d{2}))?'`

- **Updated:** `extract_timestamp_from_filename()` method
  - Now handles optional time component
  - Detects format type (ISO 8601, hyphen, or date-only)
  - Defaults to midnight (00:00:00) when time is missing
  - Improved logging with format type information

### 🔄 Behavior Changes

#### Before
```
File: 2026-01-23_DION Video (1).mp4
Result: ❌ Could not process file automatically
Reason: Timestamp pattern didn't match
```

#### After
```
File: 2026-01-23_DION Video (1).mp4
Extracted: 2026-01-23 00:00:00 (date-only format)
Query: All meetings on 2026-01-23
Result: ✓ Shows meetings for user to select
```

### 🧪 Testing

Created comprehensive test suite: `test_timestamp_extraction.py`

**Test Results:**
```
✓ 8/8 tests passed
✓ All supported formats verified
✓ Edge cases handled correctly
```

**Test Coverage:**
- Date-only format (2 tests)
- Hyphen format (2 tests)
- ISO 8601 format (3 tests)
- Edge cases (1 test)

### 📊 Impact

| Aspect | Before | After |
|--------|--------|-------|
| Supported formats | 1 | 3 |
| Date-only files | ❌ Failed | ✓ Works |
| ISO 8601 files | ❌ Failed | ✓ Works |
| Unicode filenames | ✓ Works | ✓ Works |
| Backward compatible | N/A | ✓ Yes |

### 🔧 Technical Details

#### Regex Groups
The new pattern creates up to 9 capture groups:
- Groups 1-2: Year, Month, Day (always present)
- Groups 3-5: Hour, Minute, Second (ISO 8601 format)
- Groups 6-8: Hour, Minute, Second (hyphen format)

#### Logic Flow
```python
if groups[3:6] all present:
    # ISO 8601 format (HH:MM:SS with colons)
    use groups[3:6]
elif groups[6:9] all present:
    # Hyphen format (HH-MM-SS with hyphens)
    use groups[6:9]
else:
    # Date-only format
    use 00:00:00
```

### 📚 Documentation

Created 3 new documentation files:
1. **FILENAME_FORMAT_SUPPORT.md** - Comprehensive format guide
2. **QUICK_REFERENCE.md** - Quick lookup guide
3. **CHANGELOG_FILENAME_FORMATS.md** - This file

### 🚀 Deployment

**No configuration changes required!**

The update is backward compatible and uses existing settings:
- `timezone_offset_hours` - Still applies to all formats
- `watch_folder` - Still monitors the same folder
- Google Calendar credentials - Still used for queries

### ✅ Verification Checklist

- [x] Regex pattern updated
- [x] Extraction logic updated
- [x] Logging improved
- [x] All formats tested
- [x] Edge cases handled
- [x] Backward compatible
- [x] Documentation created
- [x] No new dependencies
- [x] No configuration changes needed

### 🎓 Examples

#### Example 1: Date-only file
```
Input:  2026-01-23_DION Video (1).mp4
Output: Extracted 2026-01-23 00:00:00
Action: Query all meetings on 2026-01-23
Result: Show selection prompt
```

#### Example 2: ISO 8601 file
```
Input:  Ердакова Надежда_2026-01-23T10:01:46Z.mp4
Output: Extracted 2026-01-23 10:01:46
Action: Query meetings at 2026-01-23 10:01:46
Result: Auto-rename if match found
```

#### Example 3: Hyphen format file
```
Input:  2026-01-22_14-26-31.mp4
Output: Extracted 2026-01-22 14:26:31
Action: Query meetings at 2026-01-22 14:26:31
Result: Auto-rename if match found
```

### 🔮 Future Enhancements

Potential improvements for future versions:
- Support for `YYYYMMDD_HHMMSS` (no separators)
- Support for `DD-MM-YYYY` (European format)
- Configurable date format via settings
- Custom regex pattern support

### 📞 Support

If you encounter issues:
1. Check the logs for: "Extracted timestamp from filename"
2. Run: `python test_timestamp_extraction.py`
3. Verify the filename contains a valid date in YYYY-MM-DD format
4. Ensure the date exists in your Google Calendar

### 🎉 Summary

The application now handles **3 different filename formats** seamlessly, making it compatible with various video recording tools and naming conventions. Files that previously failed with "Could not process file automatically" will now be processed correctly with user-friendly Telegram prompts for meeting selection.
