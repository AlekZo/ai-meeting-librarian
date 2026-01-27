# Quick Reference - Filename Formats

## ✅ Supported Formats

### Format 1: Date Only
```
2026-01-23_DION Video (1).mp4
2026-01-23_Team Meeting.mp4
```
→ Shows all meetings on that date for manual selection

### Format 2: Date + Time (Hyphens)
```
2026-01-22_14-26-31.mp4
2026-01-20_10-00-00.mp4
```
→ Tries to auto-match meeting at that exact time

### Format 3: ISO 8601 (with/without timezone)
```
Ердакова Надежда_2026-01-23T10:01:46Z.mp4
Meeting_2026-01-25T14:30:00.mp4
```
→ Tries to auto-match meeting at that exact time

---

## 🔍 What Happens

| Scenario | Result |
|----------|--------|
| Exact time match found | ✓ Auto-rename (no prompt) |
| Multiple meetings at time | ? Show selection prompt |
| No exact match, but meetings on date | ? Show all meetings on date |
| No meetings on date | ❌ Ask to retry or cancel |

---

## 📝 Examples

### Your File
```
2026-01-23_DION Video (1).mp4
```

**What happens:**
1. App extracts: `2026-01-23 00:00:00`
2. App queries: "Show all meetings on 2026-01-23"
3. Telegram shows:
   ```
   📂 Multiple meetings found for: 2026-01-23_DION Video (1).mp4
   Which one should I use?
   
   [Team Standup (09:00)]
   [Project Review (14:00)]
   [❌ Cancel]
   ```
4. You click the correct meeting
5. File renamed: `Team Standup_2026-01-23_00-00-00.mp4`

---

## ⚙️ Configuration

No changes needed! Uses existing settings:
- `timezone_offset_hours` - Your timezone offset
- Google Calendar credentials - Already configured

---

## 🐛 Troubleshooting

**Problem:** "Could not process file automatically"

**Check:**
1. Does filename have a date in YYYY-MM-DD format?
2. Is the date valid? (not 2026-02-30)
3. Are there meetings on that date in Google Calendar?

**Fix:**
- Rename file to include date: `2026-01-23_Video.mp4`
- Add meeting to Google Calendar
- Click "Retry" in Telegram

---

## 📊 Test Results

All formats tested and working:
```
✓ 2026-01-23_DION Video (1).mp4
✓ 2026-01-22_14-26-31.mp4
✓ 2026-01-23_Team Meeting.mp4
✓ Ердакова Надежда_2026-01-23T10:01:46Z.mp4
✓ Meeting_2026-01-25T14:30:00.mp4
```

Run test: `python test_timestamp_extraction.py`
