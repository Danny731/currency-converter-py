from __future__ import annotations

from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
    is_valid_currency_code,
)


def test_supported_currencies_stable_order():
    codes = [c.value for c in supported_currencies()]
    assert codes == ["CNY", "USD", "GBP", "EUR", "AUD", "CAD", "JPY", "SGD"]


def test_supported_currencies_returns_fresh_list():
    # Callers must not be able to mutate the canonical order.
    first = supported_currencies()
    first.append(Currency.USD)
    assert len(supported_currencies()) == 8


def test_round_trip_string():
    for c in supported_currencies():
        assert currency_from_string(currency_to_string(c)) is c


def test_from_string_is_case_insensitive_and_trims():
    assert currency_from_string("  usd ") is Currency.USD
    assert currency_from_string("Cny") is Currency.CNY


def test_from_string_rejects_unknown():
    assert currency_from_string("XYZ") is None
    assert currency_from_string("") is None


def test_is_valid_currency_code():
    assert is_valid_currency_code("EUR") is True
    assert is_valid_currency_code("eur") is True
    assert is_valid_currency_code("BTC") is False
