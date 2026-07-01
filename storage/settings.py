from __future__ import annotations

from dataclasses import dataclass
import json
import os

from core.currency import (
    Currency,
    currency_to_string,
    is_currency_code_shape,
)
from . import app_data_dir

FILE_NAME = "settings.json"

THEMES = ("System", "Light", "Dark")
DECIMAL_PLACES = (0, 1, 2, 3, 4)


@dataclass(frozen=True)
class AppSettings:
    theme: str = "System"
    default_source_currency: Currency = Currency.USD
    default_target_currency: Currency = Currency.USD
    decimal_places: int = 2
    enabled_currencies: tuple[str, ...] = ()


def storage_file_path() -> str:
    return os.path.join(app_data_dir(), FILE_NAME)


def _normalize_theme(value: object) -> str:
    return str(value) if value in THEMES else "System"


def _normalize_decimal_places(value: object) -> int:
    try:
        decimals = int(value)
    except (TypeError, ValueError):
        return 2
    return decimals if decimals in DECIMAL_PLACES else 2


def _normalize_currency(value: object, fallback: Currency) -> Currency:
    if not isinstance(value, str):
        return fallback
    return Currency(value) if is_currency_code_shape(value) else fallback


def save(settings: AppSettings) -> bool:
    data = {
        "version": 1,
        "theme": settings.theme,
        "defaultSourceCurrency": currency_to_string(settings.default_source_currency),
        "defaultTargetCurrency": currency_to_string(settings.default_target_currency),
        "decimalPlaces": settings.decimal_places,
        "enabledCurrencies": list(settings.enabled_currencies),
    }
    try:
        with open(storage_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load() -> tuple[bool, AppSettings]:
    path = storage_file_path()
    if not os.path.exists(path):
        return False, AppSettings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, AppSettings()

    settings = AppSettings(
        theme=_normalize_theme(data.get("theme")),
        default_source_currency=_normalize_currency(
            data.get("defaultSourceCurrency"), Currency.USD),
        default_target_currency=_normalize_currency(
            data.get("defaultTargetCurrency"), Currency.USD),
        decimal_places=_normalize_decimal_places(data.get("decimalPlaces")),
        enabled_currencies=_normalize_enabled_currencies(data.get("enabledCurrencies")),
    )
    return True, settings


def _normalize_enabled_currencies(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    codes: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        code = item.strip().upper()
        if not is_currency_code_shape(code) or code in seen:
            continue
        codes.append(code)
        seen.add(code)
    return tuple(codes)
