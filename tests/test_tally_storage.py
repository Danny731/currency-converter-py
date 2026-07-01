from __future__ import annotations

from datetime import datetime
import json

from core.currency import Currency
from core.tally import TallyEntry
from storage import tally_storage


def test_tally_storage_save_writes_schema_version(tmp_path, monkeypatch):
    monkeypatch.setattr(tally_storage, "app_data_dir", lambda: str(tmp_path))
    entry = TallyEntry(
        amount=12.5,
        currency=Currency.CNY,
        converted_amount=1.75,
        note="lunch",
        created_at=datetime(2026, 7, 1, 12, 30),
    )

    assert tally_storage.save([entry], Currency.USD) is True

    data = json.loads((tmp_path / tally_storage.FILE_NAME).read_text(encoding="utf-8"))
    assert data["version"] == tally_storage.SCHEMA_VERSION
    assert data["targetCurrency"] == "USD"
    assert data["entries"][0]["note"] == "lunch"


def test_tally_storage_load_accepts_legacy_file_without_version(tmp_path, monkeypatch):
    monkeypatch.setattr(tally_storage, "app_data_dir", lambda: str(tmp_path))
    (tmp_path / tally_storage.FILE_NAME).write_text(
        json.dumps({
            "targetCurrency": "CNY",
            "entries": [
                {
                    "amount": 10,
                    "currency": "USD",
                    "convertedAmount": 72,
                    "note": "legacy",
                    "createdAt": "2026-07-01T09:30:00",
                }
            ],
        }),
        encoding="utf-8",
    )

    ok, entries, target = tally_storage.load()

    assert ok is True
    assert target == Currency.CNY
    assert len(entries) == 1
    assert entries[0].amount == 10.0
    assert entries[0].currency == Currency.USD
    assert entries[0].note == "legacy"
