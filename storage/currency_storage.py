from __future__ import annotations

import json
import os

from core.currency import CurrencyInfo, is_currency_code_shape
from . import app_data_dir

FILE_NAME = "currencies.json"
SCHEMA_VERSION = 1


def storage_file_path() -> str:
    return os.path.join(app_data_dir(), FILE_NAME)


def save(codes: list[str], names: dict[str, str] | None = None) -> bool:
    names = names or {}
    normalized_codes = _normalize_codes(codes)
    normalized_names = {
        code.strip().upper(): name.strip()
        for code, name in names.items()
        if is_currency_code_shape(code) and isinstance(name, str) and name.strip()
    }
    data = {
        "version": SCHEMA_VERSION,
        "currencies": normalized_codes,
        "names": {
            code: normalized_names[code]
            for code in normalized_codes
            if code in normalized_names
        },
    }
    try:
        with open(storage_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load() -> tuple[bool, list[str]]:
    ok, infos = load_info()
    return ok, [info.code for info in infos]


def load_info() -> tuple[bool, list[CurrencyInfo]]:
    path = storage_file_path()
    if not os.path.exists(path):
        return False, []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, []

    codes = _normalize_codes(data.get("currencies", []))
    if not codes:
        return False, []
    names_obj = data.get("names") or {}
    names = names_obj if isinstance(names_obj, dict) else {}
    return True, [
        CurrencyInfo(code=code, name=str(names.get(code, "") or code))
        for code in codes
    ]


def _normalize_codes(codes: object) -> list[str]:
    if not isinstance(codes, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if not isinstance(code, str):
            continue
        clean = code.strip().upper()
        if not is_currency_code_shape(clean) or clean in seen:
            continue
        normalized.append(clean)
        seen.add(clean)
    return normalized
