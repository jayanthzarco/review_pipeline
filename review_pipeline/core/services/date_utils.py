"""
Date range helpers used by pipelines that filter versions by day/range
(Artist Dailies, Project Dailies, Dept Dailies).

Ported from main_ui.py's old DATETIME class, generalized from "is it
today" to "is it within [date_from, date_to)" so Artist Dailies can use
an arbitrary date range per the sketch (From/To fields), while the other
review types can keep defaulting to "today" by simply not passing a range.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone, timedelta
from typing import Optional, Union


def today_range() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _to_utc_datetime(value: Union[date, datetime], end_of_day: bool = False) -> datetime:
    """
    Normalize either a `datetime.date` or `datetime.datetime` into a
    tz-aware UTC datetime.

    Qt's QDateEdit.date().toPyDate() (used by the Artist Dailies From/To
    fields) returns a plain `datetime.date`, which isn't directly
    comparable to the tz-aware `datetime` this module otherwise works
    with. A bare date is treated as midnight UTC for a lower bound
    (`date_from`), or the end of that day UTC for an upper bound
    (`date_to`) via `end_of_day=True`, so "To: 2026-07-05" includes all
    of July 5th rather than excluding it entirely.
    """
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    # plain datetime.date
    day_time = time(23, 59, 59, 999999) if end_of_day else time.min
    return datetime.combine(value, day_time, tzinfo=timezone.utc)


def is_within_range(
    timestamp_str: str,
    date_from: Optional[Union[date, datetime]] = None,
    date_to: Optional[Union[date, datetime]] = None,
) -> bool:
    """
    True if timestamp_str (ISO 8601) falls within [date_from, date_to].

    Accepts either `datetime.date` or `datetime.datetime` for the bounds
    (QDateEdit gives plain dates; other callers may pass full datetimes).
    If both bounds are None, defaults to "is it today" (UTC) — matching
    the original DATETIME.is_today behaviour used by Project/Dept Dailies.
    """
    ts = datetime.fromisoformat(timestamp_str)
    ts = ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else ts.astimezone(timezone.utc)

    if date_from is None and date_to is None:
        start, end = today_range()
        return start <= ts < end

    start = _to_utc_datetime(date_from, end_of_day=False) if date_from else datetime.min.replace(tzinfo=timezone.utc)
    end = _to_utc_datetime(date_to, end_of_day=True) if date_to else (datetime.now(timezone.utc) + timedelta(days=1))
    return start <= ts <= end
