import datetime

from file_renamer import FileRenamer


def test_extract_iso8601_with_z():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename(
        "User_2026-01-23T10:01:46Z.mp4"
    )
    assert fmt == "ISO 8601"
    assert timestamp_str == "2026-01-23_10-01-46"
    assert dt == datetime.datetime(2026, 1, 23, 10, 1, 46)


def test_extract_iso8601_without_z():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename(
        "User_2026-01-23T10:01:46.mp4"
    )
    assert fmt == "ISO 8601"
    assert timestamp_str == "2026-01-23_10-01-46"
    assert dt == datetime.datetime(2026, 1, 23, 10, 1, 46)


def test_extract_date_only():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename(
        "Meeting_2026-01-23.mp4"
    )
    assert fmt == "date-only"
    assert timestamp_str == "2026-01-23_00-00-00"
    assert dt == datetime.datetime(2026, 1, 23, 0, 0, 0)


def test_extract_short_format():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename(
        "Meeting-2602061401.mp4"
    )
    assert fmt == "YYMMDDHHMM"
    assert timestamp_str == "2026-02-06_14-01-00"
    assert dt == datetime.datetime(2026, 2, 6, 14, 1, 0)


def test_extract_dd_mon_yy():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename(
        "Notes_18_Feb_26.mp4"
    )
    assert fmt == "DD_Mon_YY"
    assert timestamp_str == "2026-02-18_00-00-00"
    assert dt == datetime.datetime(2026, 2, 18, 0, 0, 0)


def test_extract_invalid_returns_none():
    dt, timestamp_str, fmt = FileRenamer.extract_timestamp_from_filename("no_time_here.mp4")
    assert dt is None
    assert timestamp_str is None
    assert fmt is None
