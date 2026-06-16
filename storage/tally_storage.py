from __future__ import annotations

import json
import os
import sys
from datetime import datetime

from core.currency import Currency, currency_to_string, currency_from_string
from core.tally import TallyEntry

FILE_NAME = "tallybook.json"
# Distinct from the C++ app's "CurrencyConverter" directory so this Python
# version starts with its own fresh data file.
ORG_NAME = "FloatingO"
APP_NAME = "CurrencyConverterPy"

_DEFAULT_TARGET = Currency.USD


def storage_file_path() -> str:
    """Returns the absolute path of the JSON storage file, creating its
    parent directory if needed. Location follows per-user OS conventions."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, ORG_NAME, APP_NAME)
    elif sys.platform == "darwin":
        path = os.path.expanduser(f"~/Library/Application Support/{ORG_NAME}/{APP_NAME}")
    else:
        path = os.path.expanduser(f"~/.local/share/{ORG_NAME}/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, FILE_NAME)


def save(entries: list[TallyEntry], target_currency: Currency) -> bool:
    data = {
        "targetCurrency": currency_to_string(target_currency),
        "entries": [
            {
                "amount": e.amount,
                "currency": currency_to_string(e.currency),
                "convertedAmount": e.converted_amount,
                "note": e.note,
                "createdAt": e.created_at.isoformat() if e.created_at else "",
            }
            for e in entries
        ],
    }
    try:
        with open(storage_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load() -> tuple[bool, list[TallyEntry], Currency]:
    """Reads entries and the target currency from disk.

    Returns (ok, entries, target_currency). On any error (file missing,
    unreadable, or corrupt) returns (False, [], USD) and leaves state untouched.
    """
    path = storage_file_path()
    if not os.path.exists(path):
        return False, [], _DEFAULT_TARGET
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, [], _DEFAULT_TARGET

    entries: list[TallyEntry] = []
    for item in data.get("entries", []):
        currency = currency_from_string(item.get("currency", ""))
        if currency is None:
            continue  # skip unrecognized currency codes
        created_raw = item.get("createdAt", "")
        try:
            created_at = datetime.fromisoformat(created_raw) if created_raw else datetime.now()
        except ValueError:
            created_at = datetime.now()
        entries.append(TallyEntry(
            amount=float(item.get("amount", 0.0)),
            currency=currency,
            converted_amount=float(item.get("convertedAmount", 0.0)),
            note=item.get("note", ""),
            created_at=created_at,
        ))

    target = currency_from_string(data.get("targetCurrency", "")) or _DEFAULT_TARGET
    return True, entries, target
