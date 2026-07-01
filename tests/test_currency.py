from __future__ import annotations

from core.currency import (
    Currency,
    default_available_currency_codes,
    default_available_currency_info,
    default_available_currency_names,
    default_supported_currencies,
    supported_currencies,
    set_supported_currencies,
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


def test_set_supported_currencies_updates_runtime_list():
    original = [currency_to_string(c) for c in supported_currencies()]
    try:
        set_supported_currencies(["usd", "mxn", "usd", "bad-code", "JPY"])

        assert [currency_to_string(c) for c in supported_currencies()] == [
            "USD", "MXN", "JPY",
        ]
        assert currency_from_string("mxn") == Currency("MXN")
        assert is_valid_currency_code("CNY") is False
    finally:
        set_supported_currencies(original)


def test_set_supported_currencies_falls_back_to_defaults_when_empty():
    original = [currency_to_string(c) for c in supported_currencies()]
    try:
        set_supported_currencies([])
        assert supported_currencies() == default_supported_currencies()
    finally:
        set_supported_currencies(original)


def test_default_available_currency_codes_include_frankfurter_set():
    codes = default_available_currency_codes()
    assert len(codes) >= 30
    assert "USD" in codes
    assert "MXN" in codes
    assert "ZAR" in codes


def test_default_available_currency_names_cover_fallback_codes():
    codes = default_available_currency_codes()
    names = default_available_currency_names()

    assert all(code in names for code in codes)
    assert names["USD"] == "United States Dollar"
    assert names["JPY"] == "Japanese Yen"
    assert default_available_currency_info()[0].code == codes[0]
