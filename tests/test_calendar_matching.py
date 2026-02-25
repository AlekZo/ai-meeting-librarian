import datetime

from google_calendar_handler import GoogleCalendarHandler


def _event(summary, start, end):
    return {
        "summary": summary,
        "start": {"dateTime": start},
        "end": {"dateTime": end},
    }


def test_active_meeting_exact_boundary_start():
    events = [
        _event("A", "2026-02-25T10:00:00Z", "2026-02-25T11:00:00Z"),
    ]
    check_time = datetime.datetime(2026, 2, 25, 10, 0, 0)
    active = GoogleCalendarHandler._filter_active_meetings(events, check_time)
    assert len(active) == 1
    assert active[0]["summary"] == "A"


def test_active_meeting_exact_boundary_end():
    events = [
        _event("A", "2026-02-25T10:00:00Z", "2026-02-25T11:00:00Z"),
    ]
    check_time = datetime.datetime(2026, 2, 25, 11, 0, 0)
    active = GoogleCalendarHandler._filter_active_meetings(events, check_time)
    assert len(active) == 1


def test_inactive_before_start():
    events = [
        _event("A", "2026-02-25T10:00:00Z", "2026-02-25T11:00:00Z"),
    ]
    check_time = datetime.datetime(2026, 2, 25, 9, 59, 59)
    active = GoogleCalendarHandler._filter_active_meetings(events, check_time)
    assert active == []


def test_inactive_after_end():
    events = [
        _event("A", "2026-02-25T10:00:00Z", "2026-02-25T11:00:00Z"),
    ]
    check_time = datetime.datetime(2026, 2, 25, 11, 0, 1)
    active = GoogleCalendarHandler._filter_active_meetings(events, check_time)
    assert active == []


def test_multiple_active_events():
    events = [
        _event("A", "2026-02-25T10:00:00Z", "2026-02-25T11:00:00Z"),
        _event("B", "2026-02-25T10:30:00Z", "2026-02-25T12:00:00Z"),
    ]
    check_time = datetime.datetime(2026, 2, 25, 10, 45, 0)
    active = GoogleCalendarHandler._filter_active_meetings(events, check_time)
    assert {e["summary"] for e in active} == {"A", "B"}
