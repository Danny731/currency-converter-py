from __future__ import annotations


class Currency(str):
    """Currency code value object.

    This deliberately behaves like a string so dynamically loaded currency
    codes can flow through the app without changing the JSON storage format.
    """

    def __new__(cls, code: str):
        return str.__new__(cls, code.strip().upper())

    @property
    def value(self) -> str:
        return str(self)


# Stable fallback order (matches the original C++ application).
_DEFAULT_SUPPORTED_CODES = (
    "CNY",
    "USD",
    "GBP",
    "EUR",
    "AUD",
    "CAD",
    "JPY",
    "SGD",
)

_DEFAULT_AVAILABLE_CODES = (
    "AUD",
    "BRL",
    "CAD",
    "CHF",
    "CNY",
    "CZK",
    "DKK",
    "EUR",
    "GBP",
    "HKD",
    "HUF",
    "IDR",
    "ILS",
    "INR",
    "ISK",
    "JPY",
    "KRW",
    "MXN",
    "MYR",
    "NOK",
    "NZD",
    "PHP",
    "PLN",
    "RON",
    "SEK",
    "SGD",
    "THB",
    "TRY",
    "USD",
    "ZAR",
)

_currency_cache: dict[str, Currency] = {}
_supported_codes: list[str] = list(_DEFAULT_SUPPORTED_CODES)


def _currency(code: str) -> Currency:
    normalized = code.strip().upper()
    if normalized not in _currency_cache:
        _currency_cache[normalized] = Currency(normalized)
    return _currency_cache[normalized]


Currency.CNY = _currency("CNY")  # type: ignore[attr-defined]
Currency.USD = _currency("USD")  # type: ignore[attr-defined]
Currency.GBP = _currency("GBP")  # type: ignore[attr-defined]
Currency.EUR = _currency("EUR")  # type: ignore[attr-defined]
Currency.AUD = _currency("AUD")  # type: ignore[attr-defined]
Currency.CAD = _currency("CAD")  # type: ignore[attr-defined]
Currency.JPY = _currency("JPY")  # type: ignore[attr-defined]
Currency.SGD = _currency("SGD")  # type: ignore[attr-defined]


def default_supported_currencies() -> list[Currency]:
    return [_currency(code) for code in _DEFAULT_SUPPORTED_CODES]


def default_available_currency_codes() -> list[str]:
    return list(_DEFAULT_AVAILABLE_CODES)


def supported_currencies() -> list[Currency]:
    return [_currency(code) for code in _supported_codes]


def set_supported_currencies(codes: list[str]) -> None:
    """Replace the runtime-supported currency list.

    Invalid/duplicate codes are ignored. If no usable codes remain, the app
    falls back to the original 8-currency list.
    """
    normalized: list[str] = []
    seen: set[str] = set()
    for code in codes:
        clean = code.strip().upper()
        if not is_currency_code_shape(clean) or clean in seen:
            continue
        normalized.append(clean)
        seen.add(clean)
        _currency(clean)

    global _supported_codes
    _supported_codes = normalized or list(_DEFAULT_SUPPORTED_CODES)


def currency_to_string(c: Currency) -> str:
    return c.value


def currency_from_string(s: str) -> Currency | None:
    code = s.strip().upper()
    if code in _supported_codes:
        return _currency(code)
    return None


def is_currency_code_shape(s: str) -> bool:
    code = s.strip().upper()
    return len(code) == 3 and code.isalpha()


def is_valid_currency_code(s: str) -> bool:
    return currency_from_string(s) is not None
