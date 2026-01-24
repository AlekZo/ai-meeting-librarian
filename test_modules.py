"""
Example: Simple test to verify the application modules work correctly
Run this to test without Google Calendar API (use dry_run mode)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_renamer import FileRenamer

# Test sanitization
test_titles = [
    "Team Standup: 2026",
    "Client <Meeting>",
    'Project "Review"',
    "Q&A | Discussion",
]

print("Testing filename sanitization...")
print("-" * 50)

for title in test_titles:
    sanitized = FileRenamer.sanitize_filename(title)
    print(f"Original:   {title}")
    print(f"Sanitized:  {sanitized}")
    print()

# Test filename generation (dry run)
print("\nTesting filename generation...")
print("-" * 50)

test_file = "test_recording.mp4"
for title in test_titles:
    new_name = FileRenamer.generate_new_filename(title, test_file)
    print(f"Meeting: {title}")
    print(f"Result:  {new_name}")
    print()

print("\nAll tests completed!")
