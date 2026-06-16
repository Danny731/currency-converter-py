from __future__ import annotations

import json
import os

from core.currency import Currency, currency_to_string, currency_from_string
from . import app_data_dir

FILE_NAME = "rates.json"

_DEFAULT_BASE = Currency.USD


def storage_file_path() -> str:
    """Returns the absolute path of the cached-rates JSON file."""
    return os.path.join(app_data_dir(), FILE_NAME)


def save(base: Currency, base_rates: dict[Currency, float], date: str) -> bool:
    """Persists a base->targets rate snapshot so it can be reused offline.

    Only the base rates (as returned by the API) are stored; inverse and cross
    rates are re-derived on load via MainWindow._seed_rates.
    """
    data = {
        "base": currency_to_string(base),
        "date": date,
        "rates": {currency_to_string(c): v for c, v in base_rates.items()},
    }
    try:
        with open(storage_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load() -> tuple[bool, Currency, dict[Currency, float], str]:
    """Reads the cached rate snapshot from disk.

    Returns (ok, base, base_rates, date). On any error (file missing,
    unreadable, corrupt, or no usable rates) returns
    (False, USD, {}, "") and leaves state untouched.
    """
    path = storage_file_path()
    if not os.path.exists(path):
        return False, _DEFAULT_BASE, {}, ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, _DEFAULT_BASE, {}, ""

    base = currency_from_string(data.get("base", "")) or _DEFAULT_BASE
    date = str(data.get("date", "") or "")

    rates: dict[Currency, float] = {}
    for code, value in (data.get("rates") or {}).items():
        currency = currency_from_string(code)
        if currency is None:
            continue  # skip unrecognized currency codes
        try:
            rates[currency] = float(value)
        except (TypeError, ValueError):
            continue

    if not rates:
        return False, _DEFAULT_BASE, {}, ""
    return True, base, rates, date
