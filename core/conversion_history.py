from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .currency import Currency


@dataclass(frozen=True)
class ConversionHistoryEntry:
    amount: float
    source_currency: Currency
    created_at: datetime = field(default_factory=datetime.now)


class ConversionHistory:
    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max(1, max_entries)
        self._entries: list[ConversionHistoryEntry] = []

    def add(self, amount: float, source_currency: Currency,
            created_at: datetime | None = None) -> None:
        self._entries.insert(
            0,
            ConversionHistoryEntry(
                amount=amount,
                source_currency=source_currency,
                created_at=created_at or datetime.now(),
            ),
        )
        del self._entries[self._max_entries:]

    def clear(self) -> None:
        self._entries.clear()

    def entries(self) -> list[ConversionHistoryEntry]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)
