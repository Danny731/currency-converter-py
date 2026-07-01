from __future__ import annotations

import json

from core.currency import CurrencyInfo
from storage import currency_storage


def test_currency_storage_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(currency_storage, "app_data_dir", lambda: str(tmp_path))

    assert currency_storage.save(
        ["usd", "mxn", "bad-code", "JPY"],
        {"USD": "US Dollar", "mxn": "Mexican Peso", "bad": ""},
    ) is True

    ok, codes = currency_storage.load()
    assert ok is True
    assert codes == ["USD", "MXN", "JPY"]
    assert currency_storage.load_info() == (
        True,
        [
            CurrencyInfo(code="USD", name="US Dollar"),
            CurrencyInfo(code="MXN", name="Mexican Peso"),
            CurrencyInfo(code="JPY", name="JPY"),
        ],
    )
    data = json.loads((tmp_path / currency_storage.FILE_NAME).read_text(encoding="utf-8"))
    assert data["version"] == currency_storage.SCHEMA_VERSION
    assert data["names"] == {"USD": "US Dollar", "MXN": "Mexican Peso"}


def test_currency_storage_load_missing_or_corrupt_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(currency_storage, "app_data_dir", lambda: str(tmp_path))

    assert currency_storage.load() == (False, [])

    (tmp_path / currency_storage.FILE_NAME).write_text("{bad json", encoding="utf-8")
    assert currency_storage.load() == (False, [])


def test_currency_storage_load_filters_invalid_codes(tmp_path, monkeypatch):
    monkeypatch.setattr(currency_storage, "app_data_dir", lambda: str(tmp_path))
    (tmp_path / currency_storage.FILE_NAME).write_text(
        json.dumps({"currencies": ["USD", "USD", "bad-code", 123, "EUR"]}),
        encoding="utf-8",
    )

    assert currency_storage.load() == (True, ["USD", "EUR"])
    assert currency_storage.load_info() == (
        True,
        [
            CurrencyInfo(code="USD", name="USD"),
            CurrencyInfo(code="EUR", name="EUR"),
        ],
    )
