from __future__ import annotations

from enum import Enum


class Currency(Enum):
    CNY = "CNY"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    AUD = "AUD"
    CAD = "CAD"
    JPY = "JPY"
    SGD = "SGD"


# Stable display order (matches the original C++ application).
_SUPPORTED = (
    Currency.CNY,
    Currency.USD,
    Currency.GBP,
    Currency.EUR,
    Currency.AUD,
    Currency.CAD,
    Currency.JPY,
    Currency.SGD,
)


def supported_currencies() -> list[Currency]:
    return list(_SUPPORTED)


def currency_to_string(c: Currency) -> str:
    return c.value


def currency_from_string(s: str) -> Currency | None:
    code = s.strip().upper()
    for c in _SUPPORTED:
        if c.value == code:
            return c
    return None


def is_valid_currency_code(s: str) -> bool:
    return currency_from_string(s) is not None
