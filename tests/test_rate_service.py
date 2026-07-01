from __future__ import annotations

from core.currency import Currency
from core.rate_service import parse_history_rates, parse_supported_currency_codes


def test_parse_history_rates_sorts_dates_and_reads_target_currency():
    data = {
        "rates": {
            "2026-06-28": {"CNY": 7.2},
            "2026-06-26": {"CNY": "7.1"},
            "2026-06-27": {"CNY": 7.15},
        }
    }

    points = parse_history_rates(data, Currency.CNY)

    assert [p.date for p in points] == [
        "2026-06-26", "2026-06-27", "2026-06-28",
    ]
    assert [p.rate for p in points] == [7.1, 7.15, 7.2]


def test_parse_history_rates_skips_missing_or_invalid_values():
    data = {
        "rates": {
            "2026-06-26": {"CNY": 7.1},
            "2026-06-27": {"EUR": 0.92},
            "2026-06-28": {"CNY": "bad"},
            "2026-06-29": None,
        }
    }

    points = parse_history_rates(data, Currency.CNY)

    assert len(points) == 1
    assert points[0].date == "2026-06-26"
    assert points[0].rate == 7.1


def test_parse_history_rates_handles_empty_or_malformed_payload():
    assert parse_history_rates({}, Currency.CNY) == []
    assert parse_history_rates({"rates": []}, Currency.CNY) == []


def test_parse_supported_currency_codes_filters_and_sorts_codes():
    data = {
        "usd": "US Dollar",
        "JPY": "Japanese Yen",
        "bad-code": "Bad",
        123: "Not a code",
        "EUR": "Euro",
    }

    assert parse_supported_currency_codes(data) == ["EUR", "JPY", "USD"]
