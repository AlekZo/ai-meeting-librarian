# Filename Formats - Visual Guide

## 📋 All Supported Formats at a Glance

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPPORTED FILENAME FORMATS                               │
└─────────────────────────────────────────────────────────────────────────────┘

FORMAT 1: DATE ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pattern:  YYYY-MM-DD_[text].mp4
Examples:
  ✓ 2026-01-23_DION Video (1).mp4
  ✓ 2026-01-23_Team Meeting.mp4
  ✓ 2026-01-20_Recording.mp4

Extracted Time: 00:00:00 (midnight)
Calendar Query: All meetings on that date
User Action:   Select from list


FORMAT 2: DATE + TIME (HYPHENS)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pattern:  YYYY-MM-DD_HH-MM-SS[_text].mp4
Examples:
  ✓ 2026-01-22_14-26-31.mp4
  ✓ 2026-01-20_10-00-00.mp4
  ✓ 2026-01-22_14-26-31_backup.mp4

Extracted Time: HH:MM:SS (exact)
Calendar Query: Meetings at exact time
User Action:   Auto-rename (if match) or select


FORMAT 3: ISO 8601 (WITH/WITHOUT TIMEZONE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pattern:  [text]_YYYY-MM-DDTHH:MM:SSZ.mp4
Examples:
  ✓ Ердакова Надежда_2026-01-23T10:01:46Z.mp4
  ✓ Meeting_2026-01-25T14:30:00Z.mp4
  ✓ Recording_2026-01-20T09:15:30.mp4

Extracted Time: HH:MM:SS (exact)
Calendar Query: Meetings at exact time
User Action:   Auto-rename (if match) or select
```

---

## 🔄 Processing Flow

```
                    VIDEO FILE DETECTED
                           │
                           ▼
                  EXTRACT TIMESTAMP
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    SUCCESS            PARTIAL            FAILURE
    (All parts)        (Date only)         (No date)
        │                  │                  │
        ▼                  ▼                  ▼
   Query exact        Query all          Log warning
   time meetings      date meetings      Skip file
        │                  │
        ├─ 1 match ────────┼─ 1+ matches
        │                  │
        ▼                  ▼
    AUTO-RENAME      SHOW SELECTION
    (No prompt)      (Telegram prompt)
        │                  │
        └──────────┬───────┘
                   │
                   ▼
            USER SELECTS MEETING
                   │
                   ▼
              RENAME FILE
                   │
                   ▼
            COPY & UPLOAD
```

---

## 📊 Decision Tree

```
                    FILE DETECTED
                         │
                         ▼
                  CAN EXTRACT DATE?
                    /          \
                  YES           NO
                  /              \
                 ▼                ▼
            EXTRACT TIME?      SKIP FILE
             /        \        (warning)
           YES        NO
           /            \
          ▼              ▼
      QUERY EXACT    QUERY ALL
      TIME MEETINGS  DATE MEETINGS
         /  |  \         /  \
        /   |   \       /    \
       ▼    ▼    ▼     ▼      ▼
      0    1   2+     0      1+
      │    │    │     │      │
      │    │    │     │      │
      ▼    ▼    ▼     ▼      ▼
    SHOW  AUTO SHOW  SHOW   SHOW
    ALL   RENAME SELECT SELECT
    DATES        PROMPT  PROMPT
```

---

## 🎯 Quick Lookup Table

```
┌──────────────────────────────┬──────────────────┬──────────────────┐
│ FILENAME EXAMPLE             │ EXTRACTED TIME   │ CALENDAR QUERY   │
├──────────────────────────────┼──────────────────┼──────────────────┤
│ 2026-01-23_DION Video.mp4    │ 00:00:00         │ All on 2026-01-23│
│ 2026-01-22_14-26-31.mp4      │ 14:26:31         │ At 14:26:31      │
│ Надежда_2026-01-23T10:01:46Z │ 10:01:46         │ At 10:01:46      │
│ Meeting_2026-01-25T14:30:00  │ 14:30:00         │ At 14:30:00      │
│ 2026-01-20_10-00-00.mp4      │ 10:00:00         │ At 10:00:00      │
└──────────────────────────────┴──────────────────┴──────────────────┘
```

---

## 🔍 Regex Pattern Visualization

```
PATTERN: (\d{4})-(\d{2})-(\d{2})(?:[T_](\d{2}):(\d{2}):(\d{2})|_(\d{2})-(\d{2})-(\d{2}))?

EXAMPLE 1: 2026-01-23_DION Video.mp4
           ├─ Group 1: 2026 (year)
           ├─ Group 2: 01 (month)
           ├─ Group 3: 23 (day)
           └─ Groups 4-9: None (no time)
           → Result: 2026-01-23 00:00:00

EXAMPLE 2: 2026-01-22_14-26-31.mp4
           ├─ Group 1: 2026 (year)
           ├─ Group 2: 01 (month)
           ├─ Group 3: 22 (day)
           ├─ Groups 4-5: None
           ├─ Group 6: 14 (hour)
           ├─ Group 7: 26 (minute)
           ├─ Group 8: 31 (second)
           └─ Group 9: None
           → Result: 2026-01-22 14:26:31

EXAMPLE 3: Надежда_2026-01-23T10:01:46Z.mp4
           ├─ Group 1: 2026 (year)
           ├─ Group 2: 01 (month)
           ├─ Group 3: 23 (day)
           ├─ Group 4: 10 (hour)
           ├─ Group 5: 01 (minute)
           ├─ Group 6: 46 (second)
           └─ Groups 7-9: None
           → Result: 2026-01-23 10:01:46
```

---

## 📈 Format Support Timeline

```
BEFORE UPDATE:
┌─────────────────────────────────────────┐
│ Supported: 1 format                     │
│ ✓ YYYY-MM-DD_HH-MM-SS.mp4              │
│ ✗ YYYY-MM-DD_[text].mp4                │
│ ✗ [text]_YYYY-MM-DDTHH:MM:SSZ.mp4      │
└─────────────────────────────────────────┘

AFTER UPDATE:
┌─────────────────────────────────────────┐
│ Supported: 3 formats                    │
│ ✓ YYYY-MM-DD_HH-MM-SS.mp4              │
│ ✓ YYYY-MM-DD_[text].mp4                │
│ ✓ [text]_YYYY-MM-DDTHH:MM:SSZ.mp4      │
└─────────────────────────────────────────┘
```

---

## 🎬 Real-World Examples

### Example 1: OBS Studio Recording
```
Filename: 2026-01-23_DION Video (1).mp4
          └─ Date only (OBS default naming)

Processing:
  1. Extract: 2026-01-23 00:00:00
  2. Query: All meetings on 2026-01-23
  3. Result: Show 3 meetings
  4. User selects: "Team Standup"
  5. Renamed: Team Standup_2026-01-23_00-00-00.mp4
```

### Example 2: Zoom Recording
```
Filename: Ердакова Надежда_2026-01-23T10:01:46Z.mp4
          └─ ISO 8601 format (Zoom default)

Processing:
  1. Extract: 2026-01-23 10:01:46
  2. Query: Meetings at 10:01:46
  3. Result: Found "Team Meeting"
  4. Auto-renamed: Team Meeting_2026-01-23_10-01-46.mp4
  5. No user action needed!
```

### Example 3: Manual Recording
```
Filename: 2026-01-22_14-26-31.mp4
          └─ Hyphen format (manual naming)

Processing:
  1. Extract: 2026-01-22 14:26:31
  2. Query: Meetings at 14:26:31
  3. Result: Found "Project Review"
  4. Auto-renamed: Project Review_2026-01-22_14-26-31.mp4
  5. No user action needed!
```

---

## ✅ Validation Checklist

When you have a video file, check:

```
□ Does filename contain a date in YYYY-MM-DD format?
  └─ If NO: Rename file to include date

□ Is the date valid? (not 2026-02-30)
  └─ If NO: Use correct date

□ Are there meetings on that date in Google Calendar?
  └─ If NO: Add meeting to calendar

□ Is the app running and connected to Telegram?
  └─ If NO: Start the app

□ Is internet connection available?
  └─ If NO: Check network connection
```

---

## 🚀 Performance Metrics

```
Operation                    Time
─────────────────────────────────
Timestamp extraction         < 1ms
Regex matching              < 1ms
Calendar query              1-2s
User selection (Telegram)   Variable
Total processing            2-5s
```

---

## 📞 Troubleshooting Guide

```
PROBLEM: "Could not process file automatically"

STEP 1: Check filename format
  ✓ 2026-01-23_Video.mp4
  ✓ 2026-01-22_14-26-31.mp4
  ✓ Name_2026-01-23T10:01:46Z.mp4
  ✗ Video_2026-01-23.mp4 (missing underscore)
  ✗ 23-01-2026_Video.mp4 (wrong date format)

STEP 2: Check date validity
  ✓ 2026-01-23 (valid)
  ✗ 2026-02-30 (invalid - no Feb 30)
  ✗ 2026-13-01 (invalid - no month 13)

STEP 3: Check Google Calendar
  ✓ Meetings exist on that date
  ✗ No meetings on that date

STEP 4: Check logs
  Run: tail -f logs/auto_renamer.log
  Look for: "Extracted timestamp from filename"
```

---

## 🎓 Learning Resources

- **FILENAME_FORMAT_SUPPORT.md** - Detailed format documentation
- **QUICK_REFERENCE.md** - Quick lookup guide
- **test_timestamp_extraction.py** - Test all formats
- **CHANGELOG_FILENAME_FORMATS.md** - What changed and why
