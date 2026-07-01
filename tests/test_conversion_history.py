from __future__ import annotations

from datetime import datetime

from core.conversion_history import ConversionHistory
from core.currency import Currency


def test_conversion_history_adds_newest_first():
    history = ConversionHistory()

    history.add(10.0, Currency.USD, datetime(2026, 7, 1, 9, 0))
    history.add(20.0, Currency.CNY, datetime(2026, 7, 1, 10, 0))

    entries = history.entries()
    assert [e.amount for e in entries] == [20.0, 10.0]
    assert [e.source_currency for e in entries] == [Currency.CNY, Currency.USD]


def test_conversion_history_caps_entries():
    history = ConversionHistory(max_entries=3)

    for i in range(5):
        history.add(float(i), Currency.USD, datetime(2026, 7, 1, 9, i))

    assert history.count() == 3
    assert [e.amount for e in history.entries()] == [4.0, 3.0, 2.0]


def test_conversion_history_clear():
    history = ConversionHistory()
    history.add(10.0, Currency.USD)

    history.clear()

    assert history.entries() == []
