from __future__ import annotations

import json

from core.currency import Currency
from storage import rate_storage


def test_rate_storage_save_writes_schema_version(tmp_path, monkeypatch):
    monkeypatch.setattr(rate_storage, "app_data_dir", lambda: str(tmp_path))

    assert rate_storage.save(
        Currency.USD, {Currency.CNY: 7.25, Currency.EUR: 0.92}, "2026-07-01",
    ) is True

    data = json.loads((tmp_path / rate_storage.FILE_NAME).read_text(encoding="utf-8"))
    assert data["version"] == rate_storage.SCHEMA_VERSION
    assert data["base"] == "USD"
    assert data["date"] == "2026-07-01"
    assert data["rates"] == {"CNY": 7.25, "EUR": 0.92}


def test_rate_storage_load_accepts_legacy_file_without_version(tmp_path, monkeypatch):
    monkeypatch.setattr(rate_storage, "app_data_dir", lambda: str(tmp_path))
    (tmp_path / rate_storage.FILE_NAME).write_text(
        json.dumps({
            "base": "USD",
            "date": "2026-07-01",
            "rates": {"CNY": "7.25", "BAD": 1.0},
        }),
        encoding="utf-8",
    )

    ok, base, rates, date = rate_storage.load()

    assert ok is True
    assert base == Currency.USD
    assert date == "2026-07-01"
    assert rates == {Currency.CNY: 7.25}
