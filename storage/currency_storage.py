from __future__ import annotations

import json
import os

from core.currency import is_currency_code_shape
from . import app_data_dir

FILE_NAME = "currencies.json"
SCHEMA_VERSION = 1


def storage_file_path() -> str:
    return os.path.join(app_data_dir(), FILE_NAME)


def save(codes: list[str]) -> bool:
    data = {
        "version": SCHEMA_VERSION,
        "currencies": [
            code.strip().upper()
            for code in codes
            if is_currency_code_shape(code)
        ],
    }
    try:
        with open(storage_file_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def load() -> tuple[bool, list[str]]:
    path = storage_file_path()
    if not os.path.exists(path):
        return False, []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return False, []

    codes = []
    seen: set[str] = set()
    for code in data.get("currencies", []):
        if not isinstance(code, str):
            continue
        clean = code.strip().upper()
        if not is_currency_code_shape(clean) or clean in seen:
            continue
        codes.append(clean)
        seen.add(clean)
    if not codes:
        return False, []
    return True, codes
