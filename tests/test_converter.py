from __future__ import annotations

import math

import pytest

from core.currency import Currency
from core.converter import CurrencyConverter, parse_amount


# --- parse_amount: the nan/inf validation fix ---

@pytest.mark.parametrize("text,expected", [
    ("0", 0.0),
    ("100", 100.0),
    ("123.45", 123.45),
    ("  42 ", 42.0),
    ("1e3", 1000.0),
])
def test_parse_amount_accepts_valid(text, expected):
    assert parse_amount(text) == expected


@pytest.mark.parametrize("text", [
    "",
    "abc",
    "12.3.4",
    "-1",
    "-0.01",
    "nan",          # float("nan") < 0.0 is False -> must be caught explicitly
    "NaN",
    "inf",
    "-inf",
    "infinity",
])
def test_parse_amount_rejects_invalid(text):
    assert parse_amount(text) is None


def test_parse_amount_never_returns_non_finite():
    # The whole point: nothing non-finite escapes into downstream totals.
    for text in ("nan", "inf", "-inf"):
        assert parse_amount(text) is None


# --- basic conversion ---

def test_same_currency_is_identity():
    conv = CurrencyConverter()
    assert conv.rate(Currency.USD, Currency.USD) == 1.0
    assert conv.convert(50.0, Currency.USD, Currency.USD) == 50.0
    assert conv.has_rate(Currency.USD, Currency.USD) is True


def test_missing_rate_signals():
    conv = CurrencyConverter()
    assert conv.rate(Currency.USD, Currency.JPY) == 0.0
    assert conv.convert(10.0, Currency.USD, Currency.JPY) == -1.0
    assert conv.has_rate(Currency.USD, Currency.JPY) is False


def test_set_and_convert():
    conv = CurrencyConverter()
    conv.set_rate(Currency.USD, Currency.CNY, 7.0)
    assert conv.convert(10.0, Currency.USD, Currency.CNY) == 70.0


def test_format_result():
    assert CurrencyConverter.format_result(-1.0, Currency.USD) == "--"
    assert CurrencyConverter.format_result(1234567.89, Currency.USD) == "1,234,567.89"
    assert CurrencyConverter.format_result(0.0, Currency.CNY) == "0.00"


def test_format_result_uses_zero_decimals_for_jpy():
    assert CurrencyConverter.format_result(12345.6, Currency.JPY) == "12,346"
    assert CurrencyConverter.format_result(12345.4, Currency.JPY) == "12,345"


def test_decimal_places_by_currency():
    assert CurrencyConverter.decimal_places(Currency.JPY) == 0
    assert CurrencyConverter.decimal_places(Currency.USD) == 2


# --- seed_from_base: the consolidated derivation logic ---

def test_seed_from_base_sets_direct_and_inverse():
    conv = CurrencyConverter()
    conv.seed_from_base(Currency.USD, {Currency.CNY: 8.0})
    assert conv.rate(Currency.USD, Currency.CNY) == 8.0
    assert conv.rate(Currency.CNY, Currency.USD) == pytest.approx(1.0 / 8.0)


def test_seed_from_base_derives_cross_rate():
    # USD->CNY = 8, USD->GBP = 0.8  =>  CNY->GBP = 0.8/8 = 0.1
    conv = CurrencyConverter()
    conv.seed_from_base(Currency.USD, {Currency.CNY: 8.0, Currency.GBP: 0.8})
    assert conv.convert(100.0, Currency.CNY, Currency.GBP) == pytest.approx(10.0)
    # And the reverse cross rate resolves too.
    assert conv.convert(10.0, Currency.GBP, Currency.CNY) == pytest.approx(100.0)


def test_seed_from_base_skips_non_positive_rate():
    conv = CurrencyConverter()
    conv.seed_from_base(Currency.USD, {Currency.CNY: 0.0})
    # A zero rate yields no usable inverse, so the pair stays unresolved.
    assert conv.has_rate(Currency.CNY, Currency.USD) is False


def test_seed_from_base_all_pairs_resolve():
    rates = {
        Currency.CNY: 7.25, Currency.GBP: 0.79, Currency.EUR: 0.92,
        Currency.AUD: 1.54, Currency.CAD: 1.37, Currency.JPY: 144.5,
        Currency.SGD: 1.34,
    }
    conv = CurrencyConverter()
    conv.seed_from_base(Currency.USD, rates)
    from core.currency import supported_currencies
    for frm in supported_currencies():
        for to in supported_currencies():
            assert conv.has_rate(frm, to), f"{frm}->{to} missing"
            assert math.isfinite(conv.convert(1.0, frm, to))
