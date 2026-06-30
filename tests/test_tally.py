from __future__ import annotations

import pytest

from core.currency import Currency
from core.converter import CurrencyConverter
from core.tally import TallyEntry, TallyBook


def _converter() -> CurrencyConverter:
    conv = CurrencyConverter()
    # USD base; CNY 7.0, GBP 0.8 -> cross rates derived.
    conv.seed_from_base(Currency.USD, {Currency.CNY: 7.0, Currency.GBP: 0.8})
    return conv


def test_add_entry_converts_to_target():
    conv = _converter()
    book = TallyBook()
    ok = book.add_entry(TallyEntry(amount=7.0, currency=Currency.CNY),
                        Currency.USD, conv)
    assert ok is True
    assert book.count() == 1
    assert book.entries()[0].converted_amount == pytest.approx(1.0)


def test_add_entry_same_currency_keeps_amount():
    conv = _converter()
    book = TallyBook()
    book.add_entry(TallyEntry(amount=50.0, currency=Currency.USD),
                   Currency.USD, conv)
    assert book.entries()[0].converted_amount == 50.0


def test_add_entry_rejected_on_missing_rate():
    conv = CurrencyConverter()  # empty, no rates
    book = TallyBook()
    ok = book.add_entry(TallyEntry(amount=10.0, currency=Currency.JPY),
                        Currency.USD, conv)
    assert ok is False
    assert book.count() == 0


def test_total_sums_converted_amounts():
    conv = _converter()
    book = TallyBook()
    book.add_entry(TallyEntry(amount=7.0, currency=Currency.CNY), Currency.USD, conv)
    book.add_entry(TallyEntry(amount=10.0, currency=Currency.USD), Currency.USD, conv)
    assert book.total() == pytest.approx(11.0)


def test_remove_entry():
    conv = _converter()
    book = TallyBook()
    book.add_entry(TallyEntry(amount=7.0, currency=Currency.CNY), Currency.USD, conv)
    book.add_entry(TallyEntry(amount=10.0, currency=Currency.USD), Currency.USD, conv)
    book.remove_entry(0)
    assert book.count() == 1
    assert book.entries()[0].converted_amount == 10.0


def test_remove_entry_out_of_range_is_noop():
    book = TallyBook()
    book.remove_entry(5)  # must not raise
    assert book.count() == 0


def test_clear():
    conv = _converter()
    book = TallyBook()
    book.add_entry(TallyEntry(amount=10.0, currency=Currency.USD), Currency.USD, conv)
    book.clear()
    assert book.count() == 0
    assert book.total() == 0.0


def test_recalculate_updates_for_new_target():
    conv = _converter()
    book = TallyBook()
    book.add_entry(TallyEntry(amount=10.0, currency=Currency.USD), Currency.USD, conv)
    # Re-total in CNY: 10 USD * 7.0 = 70 CNY.
    book.recalculate(Currency.CNY, conv)
    assert book.total() == pytest.approx(70.0)


def test_recalculate_missing_rate_zeroes_entry():
    conv = _converter()  # has no rate to JPY
    book = TallyBook()
    book.set_entries([TallyEntry(amount=5.0, currency=Currency.JPY,
                                 converted_amount=999.0)])
    book.recalculate(Currency.USD, conv)
    assert book.entries()[0].converted_amount == 0.0
