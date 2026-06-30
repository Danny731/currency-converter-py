from __future__ import annotations

from datetime import date

from ui.main_window import _relative_rate_date


def test_relative_rate_date_today():
    assert _relative_rate_date("2026-06-30", date(2026, 6, 30)) == "today"


def test_relative_rate_date_days_ago():
    assert _relative_rate_date("2026-06-27", date(2026, 6, 30)) == "3 days ago"


def test_relative_rate_date_future_date():
    assert _relative_rate_date("2026-07-01", date(2026, 6, 30)) == "in 1 day"


def test_relative_rate_date_handles_missing_or_invalid_date():
    assert _relative_rate_date("", date(2026, 6, 30)) == "unknown date"
    assert _relative_rate_date("not-a-date", date(2026, 6, 30)) == "not-a-date"
