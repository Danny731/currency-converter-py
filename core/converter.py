from __future__ import annotations

from .currency import Currency


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
    def format_result(value: float) -> str:
        if value < 0.0:
            return "--"
        return f"{value:,.2f}"
