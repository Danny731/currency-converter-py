from __future__ import annotations

import math

from .currency import Currency, supported_currencies


def parse_amount(text: str) -> float | None:
    """Parses user-entered amount text into a non-negative, finite float.

    Returns None for anything that is not a valid amount: non-numeric text,
    negative values, and the special floats nan / inf / -inf. Guarding against
    nan/inf matters because `float("nan") < 0.0` is False, so a naive
    `float(text)` check would let them slip through into totals.
    """
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0.0:
        return None
    return value


class CurrencyConverter:
    """Converts amounts between currencies using stored exchange rates.

    Rates are keyed by (source, target) currency pairs. A missing rate for a
    pair yields 0.0 from rate() and -1.0 from convert(), so callers can tell
    'no rate' apart from a legitimate zero result.
    """

    def __init__(self) -> None:
        self._rates: dict[tuple[Currency, Currency], float] = {}

    def set_rate(self, frm: Currency, to: Currency, rate: float) -> None:
        self._rates[(frm, to)] = rate

    def seed_from_base(self, base: Currency,
                       base_rates: dict[Currency, float]) -> None:
        """Populate rates from a base->targets table, deriving inverse and
        cross rates so any supported pair resolves.

        Shared by the mock snapshot, the persisted offline snapshot, and the
        live API result so the derivation logic lives in exactly one place.
        """
        for cur, rate in base_rates.items():
            self.set_rate(base, cur, rate)
            if rate > 0.0:
                self.set_rate(cur, base, 1.0 / rate)
        for frm in supported_currencies():
            for to in supported_currencies():
                if frm == to or self.has_rate(frm, to):
                    continue
                from_base = self.convert(1.0, frm, base)
                base_to = self.convert(1.0, base, to)
                if from_base > 0.0 and base_to > 0.0:
                    self.set_rate(frm, to, from_base * base_to)

    def rate(self, frm: Currency, to: Currency) -> float:
        if frm == to:
            return 1.0
        return self._rates.get((frm, to), 0.0)

    def convert(self, amount: float, frm: Currency, to: Currency) -> float:
        if frm == to:
            return amount
        r = self.rate(frm, to)
        if r <= 0.0:
            return -1.0
        return amount * r

    def has_rate(self, frm: Currency, to: Currency) -> bool:
        if frm == to:
            return True
        return (frm, to) in self._rates

    @staticmethod
    def decimal_places(currency: Currency) -> int:
        return 0 if currency == Currency.JPY else 2

    @staticmethod
    def format_result(value: float, currency: Currency) -> str:
        if value < 0.0:
            return "--"
        return f"{value:,.{CurrencyConverter.decimal_places(currency)}f}"
