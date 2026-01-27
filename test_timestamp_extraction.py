#!/usr/bin/env python3
"""
Test script to verify timestamp extraction from various filename formats
"""

import re
from datetime import datetime

# Pattern to match timestamps in filenames:
# - 2026-01-22_14-26-31 (date with time)
# - 2026-01-22 (date only)
# - 2026-01-23T10:01:46Z (ISO 8601 format with timezone)
# - 2026-01-23T10:01:46 (ISO 8601 format without timezone)
TIMESTAMP_PATTERN = r'(\d{4})-(\d{2})-(\d{2})(?:[T_](\d{2}):(\d{2}):(\d{2})|_(\d{2})-(\d{2})-(\d{2}))?'

def extract_timestamp(filename):
    """Extract timestamp from filename"""
    match = re.search(TIMESTAMP_PATTERN, filename)
    if match:
        groups = match.groups()
        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
        
        # Check for ISO 8601 format with colons (groups 3, 4, 5)
        if groups[3] is not None and groups[4] is not None and groups[5] is not None:
            hour, minute, second = int(groups[3]), int(groups[4]), int(groups[5])
            format_type = "ISO 8601"
        # Check for underscore format with hyphens (groups 6, 7, 8)
        elif groups[6] is not None and groups[7] is not None and groups[8] is not None:
            hour, minute, second = int(groups[6]), int(groups[7]), int(groups[8])
            format_type = "underscore with hyphens"
        else:
            # No time component, use midnight (00:00:00)
            hour, minute, second = 0, 0, 0
            format_type = "date-only"
        
        try:
            dt = datetime(year, month, day, hour, minute, second)
            timestamp_str = f"{year:04d}-{month:02d}-{day:02d}_{hour:02d}-{minute:02d}-{second:02d}"
            return True, timestamp_str, format_type, dt
        except ValueError as e:
            return False, None, None, str(e)
    return False, None, None, "No match"

# Test cases
test_cases = [
    ("2026-01-23_DION Video (1).mp4", "2026-01-23_00-00-00", "date-only"),
    ("2026-01-22_14-26-31.mp4", "2026-01-22_14-26-31", "underscore with hyphens"),
    ("2026-01-23_Team Meeting.mp4", "2026-01-23_00-00-00", "date-only"),
    ("2026-01-22_14-26-31_backup.mp4", "2026-01-22_14-26-31", "underscore with hyphens"),
    ("Ердакова Надежда_2026-01-23T10:01:46Z.mp4", "2026-01-23_10-01-46", "ISO 8601"),
    ("Ердакова Надежда_2026-01-23T10:01:46.mp4", "2026-01-23_10-01-46", "ISO 8601"),
    ("Meeting_2026-01-25T14:30:00Z.mp4", "2026-01-25_14-30-00", "ISO 8601"),
    ("2026-01-20_10-00-00.mp4", "2026-01-20_10-00-00", "underscore with hyphens"),
]

print("=" * 100)
print("TIMESTAMP EXTRACTION TEST RESULTS")
print("=" * 100)

passed = 0
failed = 0

for filename, expected_timestamp, expected_format in test_cases:
    success, timestamp, format_type, result = extract_timestamp(filename)
    
    if success and timestamp == expected_timestamp and format_type == expected_format:
        status = "✓ PASS"
        passed += 1
    else:
        status = "✗ FAIL"
        failed += 1
    
    print(f"\n{status}")
    print(f"  Filename:          {filename}")
    print(f"  Expected:          {expected_timestamp} ({expected_format})")
    if success:
        print(f"  Got:               {timestamp} ({format_type})")
        print(f"  DateTime:          {result}")
    else:
        print(f"  Error:             {result}")

print("\n" + "=" * 100)
print(f"SUMMARY: {passed} passed, {failed} failed out of {len(test_cases)} tests")
print("=" * 100)

if failed == 0:
    print("✓ All tests passed!")
else:
    print(f"✗ {failed} test(s) failed!")
