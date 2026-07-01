from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .currency import Currency
from .converter import CurrencyConverter


@dataclass
class TallyEntry:
    amount: float = 0.0
    currency: Currency = Currency.CNY
    converted_amount: float = 0.0
    note: str = ""
    created_at: datetime = field(default_factory=datetime.now)


class TallyBook:
    """A collection of tally entries with a total computed in a target currency."""

    def __init__(self) -> None:
        self._entries: list[TallyEntry] = []

    def add_entry(self, entry: TallyEntry, target_currency: Currency,
                  converter: CurrencyConverter) -> bool:
        converted = converter.convert(entry.amount, entry.currency, target_currency)
        if converted < 0.0 and entry.currency != target_currency:
            return False  # missing rate for this pair
        stored = TallyEntry(
            amount=entry.amount,
            currency=entry.currency,
            converted_amount=(entry.amount if entry.currency == target_currency else converted),
            note=entry.note,
            created_at=entry.created_at,
        )
        self._entries.append(stored)
        return True

    def remove_entry(self, index: int) -> None:
        if 0 <= index < len(self._entries):
            del self._entries[index]

    def update_entry(self, index: int, amount: float, currency: Currency,
                     target_currency: Currency, converter: CurrencyConverter,
                     note: str) -> bool:
        if not 0 <= index < len(self._entries):
            return False
        converted = converter.convert(amount, currency, target_currency)
        if converted < 0.0 and currency != target_currency:
            return False
        existing = self._entries[index]
        self._entries[index] = TallyEntry(
            amount=amount,
            currency=currency,
            converted_amount=(amount if currency == target_currency else converted),
            note=note,
            created_at=existing.created_at,
        )
        return True

    def clear(self) -> None:
        self._entries.clear()

    def set_entries(self, entries: list[TallyEntry]) -> None:
        """Bulk-replace entries without conversion (used to restore persisted data)."""
        self._entries = list(entries)

    def entries(self) -> list[TallyEntry]:
        return list(self._entries)

    def recalculate(self, target_currency: Currency, converter: CurrencyConverter) -> None:
        for entry in self._entries:
            converted = converter.convert(entry.amount, entry.currency, target_currency)
            if entry.currency == target_currency:
                entry.converted_amount = entry.amount
            else:
                entry.converted_amount = 0.0 if converted < 0.0 else converted

    def total(self) -> float:
        return sum(e.converted_amount for e in self._entries)

    def count(self) -> int:
        return len(self._entries)
