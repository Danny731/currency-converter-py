from __future__ import annotations

from core.currency import Currency
from storage import settings as settings_storage
from storage.settings import AppSettings


def test_settings_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_storage, "app_data_dir", lambda: str(tmp_path))
    saved = AppSettings(
        theme="Dark",
        default_source_currency=Currency.GBP,
        default_target_currency=Currency.CNY,
        decimal_places=4,
        enabled_currencies=("USD", "CNY", "JPY"),
    )

    assert settings_storage.save(saved) is True

    ok, loaded = settings_storage.load()
    assert ok is True
    assert loaded == saved


def test_settings_load_missing_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_storage, "app_data_dir", lambda: str(tmp_path))

    ok, loaded = settings_storage.load()

    assert ok is False
    assert loaded == AppSettings()


def test_settings_load_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_storage, "app_data_dir", lambda: str(tmp_path))
    settings_storage.storage_file_path()
    (tmp_path / settings_storage.FILE_NAME).write_text("{bad json", encoding="utf-8")

    ok, loaded = settings_storage.load()

    assert ok is False
    assert loaded == AppSettings()


def test_settings_load_invalid_values_falls_back_field_by_field(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_storage, "app_data_dir", lambda: str(tmp_path))
    (tmp_path / settings_storage.FILE_NAME).write_text(
        """
        {
          "theme": "Solarized",
          "defaultSourceCurrency": "GBP",
          "defaultTargetCurrency": "NOPE",
          "decimalPlaces": 99,
          "enabledCurrencies": ["usd", "bad-code", "USD", 123, "eur"]
        }
        """,
        encoding="utf-8",
    )

    ok, loaded = settings_storage.load()

    assert ok is True
    assert loaded == AppSettings(
        theme="System",
        default_source_currency=Currency.GBP,
        default_target_currency=Currency.USD,
        decimal_places=2,
        enabled_currencies=("USD", "EUR"),
    )


def test_settings_load_keeps_valid_dynamic_currency_codes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings_storage, "app_data_dir", lambda: str(tmp_path))
    (tmp_path / settings_storage.FILE_NAME).write_text(
        """
        {
          "defaultSourceCurrency": "MXN",
          "defaultTargetCurrency": "ZAR"
        }
        """,
        encoding="utf-8",
    )

    ok, loaded = settings_storage.load()

    assert ok is True
    assert loaded.default_source_currency == Currency("MXN")
    assert loaded.default_target_currency == Currency("ZAR")
