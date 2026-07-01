from __future__ import annotations

from datetime import date
import sys
import tkinter.ttk as ttk

import customtkinter as ctk

from core.currency import (
    Currency,
    CurrencyInfo,
    currency_to_string,
    default_available_currency_codes,
    default_available_currency_names,
    set_supported_currencies,
    supported_currencies,
)
from core.converter import CurrencyConverter
from core.rate_service import ExchangeRateService
from storage import currency_storage
from storage import rate_storage
from storage import settings as settings_storage
from storage.settings import AppSettings
from ui.converter_page import ConverterPage
from ui.history_page import HistoryPage
from ui.settings_page import SettingsPage
from ui.tally_page import TallyBookPage


def _ui_font_family() -> str:
    """Pick a sane default UI font for the current platform.

    The original Windows port hardcoded "Segoe UI", which does not exist on
    macOS/Linux and silently falls back to an arbitrary default there.
    """
    if sys.platform == "darwin":
        return "SF Pro Text"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def _relative_rate_date(rate_date: str, today: date | None = None) -> str:
    """Return a user-friendly age label for an ISO rate date."""
    if not rate_date:
        return "unknown date"
    today = today or date.today()
    try:
        parsed = date.fromisoformat(rate_date)
    except ValueError:
        return rate_date
    days = (today - parsed).days
    if days == 0:
        return "today"
    if days > 0:
        unit = "day" if days == 1 else "days"
        return f"{days} {unit} ago"
    future_days = abs(days)
    unit = "day" if future_days == 1 else "days"
    return f"in {future_days} {unit}"

# Mock fallback rates (approximate, relative to USD), used until the first
# live fetch completes or whenever the network is unavailable.
_MOCK_USD_RATES = {
    Currency.CNY: 7.25,
    Currency.USD: 1.0,
    Currency.GBP: 0.79,
    Currency.EUR: 0.92,
    Currency.AUD: 1.54,
    Currency.CAD: 1.37,
    Currency.JPY: 144.50,
    Currency.SGD: 1.34,
}


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Multifunctional Currency Converter")
        self.geometry("820x740")
        self.minsize(720, 640)
        self._available_currency_codes: list[str] = default_available_currency_codes()
        self._available_currency_names: dict[str, str] = default_available_currency_names()
        self._load_cached_supported_currencies()
        self._settings = self._load_settings()
        set_supported_currencies(self._active_currency_codes())
        ctk.set_appearance_mode(self._settings.theme)
        ctk.set_default_color_theme("blue")

        self._converter = CurrencyConverter()
        self._setup_mock_rates()
        self._rate_service = ExchangeRateService()
        # Prefer saved offline rates over the hardcoded mock snapshot so an
        # offline launch starts with the last-known-good rates instead.
        self._offline_loaded_date = self._load_offline_rates()

        self._status = ctk.CTkLabel(
            self, text=self._initial_status_text(), anchor="w",
        )
        self._status.pack(side="bottom", fill="x", padx=12, pady=(6, 12))

        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(side="top", fill="both", expand=True, padx=12, pady=(12, 0))
        self._tabview.add("Currency Converter")
        self._tabview.add("Tally Book")
        self._tabview.add("Rate History")
        self._tabview.add("Settings")

        self._converter_page = ConverterPage(
            self._tabview.tab("Currency Converter"),
            default_source=self._settings.default_source_currency,
            decimal_places=self._settings.decimal_places,
        )
        self._converter_page.pack(fill="both", expand=True)
        self._converter_page.set_converter(self._converter)

        self._tally_page = TallyBookPage(
            self._tabview.tab("Tally Book"),
            default_source=self._settings.default_source_currency,
            default_target=self._settings.default_target_currency,
            decimal_places=self._settings.decimal_places,
        )
        self._tally_page.pack(fill="both", expand=True)
        self._tally_page.set_converter(self._converter)

        self._history_page = HistoryPage(self._tabview.tab("Rate History"))
        self._history_page.pack(fill="both", expand=True)
        self._history_page.set_rate_service(self._rate_service)

        self._settings_page = SettingsPage(
            self._tabview.tab("Settings"), self._settings, self._save_settings,
        )
        self._settings_page.pack(fill="both", expand=True)
        self._settings_page.refresh_supported_currencies(
            self._available_currency_codes,
            self._available_currency_names,
        )

        self.after(50, self._style_treeview)
        self._fetch_live_rates()
        self._fetch_supported_currencies()

    # --- rates ---
    def _load_settings(self) -> AppSettings:
        _ok, settings = settings_storage.load()
        return settings

    def _load_cached_supported_currencies(self) -> None:
        ok, infos = currency_storage.load_info()
        if ok:
            codes = [info.code for info in infos]
            self._available_currency_codes = codes
            self._available_currency_names = self._currency_names_for(infos)
            set_supported_currencies(codes)

    def _currency_names_for(self, infos: list[CurrencyInfo]) -> dict[str, str]:
        names = default_available_currency_names()
        names.update({
            info.code: info.name
            for info in infos
            if info.name and info.name.upper() != info.code
        })
        return names

    def _save_settings(self, settings: AppSettings) -> bool:
        settings = self._normalize_settings(settings)
        saved = settings_storage.save(settings)
        if saved:
            self._settings = settings
            self._apply_settings()
        return saved

    def _normalize_settings(self, settings: AppSettings) -> AppSettings:
        available = self._available_currency_codes or [
            currency_to_string(c) for c in supported_currencies()
        ]
        enabled = settings.enabled_currencies or tuple(available)
        if len(enabled) < 2:
            enabled = tuple(available)
        source = settings.default_source_currency
        target = settings.default_target_currency
        if currency_to_string(source) not in enabled:
            source = Currency(enabled[0])
        if currency_to_string(target) not in enabled:
            target = Currency(enabled[1] if len(enabled) > 1 else enabled[0])
        return AppSettings(
            theme=settings.theme,
            default_source_currency=source,
            default_target_currency=target,
            decimal_places=settings.decimal_places,
            enabled_currencies=tuple(enabled),
        )

    def _apply_settings(self) -> None:
        set_supported_currencies(self._active_currency_codes())
        ctk.set_appearance_mode(self._settings.theme)
        self._refresh_currency_ui()
        self._converter_page.apply_preferences(
            self._settings.default_source_currency,
            self._settings.decimal_places,
        )
        self._tally_page.apply_preferences(
            self._settings.default_source_currency,
            self._settings.default_target_currency,
            self._settings.decimal_places,
        )
        self.after(0, self._style_treeview)
        self._fetch_live_rates()

    def _active_currency_codes(self) -> list[str]:
        available = self._available_currency_codes or [
            currency_to_string(c) for c in supported_currencies()
        ]
        if not self._settings.enabled_currencies:
            return available
        enabled = set(self._settings.enabled_currencies)
        selected = [code for code in available if code in enabled]
        return selected if len(selected) >= 2 else available

    def _refresh_currency_ui(self) -> None:
        self._converter_page.refresh_supported_currencies()
        self._tally_page.refresh_supported_currencies()
        self._history_page.refresh_supported_currencies()
        self._settings_page.refresh_supported_currencies(
            self._available_currency_codes,
            self._available_currency_names,
        )

    def _fetch_supported_currencies(self) -> None:
        self._rate_service.fetch_supported_currencies(
            on_success=lambda currencies:
                self.after(0, lambda: self._apply_supported_currencies(currencies)),
            on_failure=self._on_currencies_failed,
        )

    def _apply_supported_currencies(self, currencies: list[CurrencyInfo]) -> None:
        self._available_currency_codes = [info.code for info in currencies]
        self._available_currency_names = self._currency_names_for(currencies)
        currency_storage.save(self._available_currency_codes, self._available_currency_names)
        set_supported_currencies(self._active_currency_codes())
        self._refresh_currency_ui()
        # Refresh rates again now that the full runtime currency list is known.
        self._fetch_live_rates()

    def _on_currencies_failed(self, reason: str) -> None:
        self.after(0, lambda r=reason: self._show_currencies_failure(r))

    def _show_currencies_failure(self, reason: str) -> None:
        if not self._rate_service.has_rates:
            self._status.configure(
                text=f"Could not load full currency list: {reason}; "
                     f"using cached or built-in currencies."
            )

    def _seed_rates(self, base: Currency,
                    base_rates: dict[Currency, float]) -> None:
        """Populate the converter from a base->targets rate table, deriving
        inverse and cross rates. Shared by mock, offline, and live snapshots."""
        self._converter.seed_from_base(base, base_rates)

    def _setup_mock_rates(self) -> None:
        self._seed_rates(Currency.USD, _MOCK_USD_RATES)

    def _load_offline_rates(self) -> str | None:
        """Loads the last persisted rate snapshot. Returns the snapshot's date
        when available, otherwise None (leaving the mock rates in place)."""
        ok, base, rates, date = rate_storage.load()
        if not ok:
            return None
        self._seed_rates(base, rates)
        return date

    def _initial_status_text(self) -> str:
        if self._offline_loaded_date:
            return (f"Offline cache · {self._relative_offline_date_label()}. "
                    f"Fetching live rates...")
        return "Built-in reference rates. Fetching live rates..."

    def _fetch_live_rates(self) -> None:
        self._rate_service.fetch_rates(
            Currency.USD,
            on_success=lambda: self.after(0, self._apply_rates),
            on_failure=self._on_fetch_failed,
        )

    def _apply_rates(self) -> None:
        self._converter = self._rate_service.converter
        self._converter_page.set_converter(self._converter)
        self._tally_page.set_converter(self._converter)
        # Persist the freshly fetched rates so they're available offline next launch.
        saved = rate_storage.save(
            self._rate_service.base_currency,
            self._rate_service.base_rates,
            self._rate_service.last_update_date,
        )
        status = (
            f"Live rates · {self._rate_service.last_update_date} "
            f"({_relative_rate_date(self._rate_service.last_update_date)})"
        )
        if not saved:
            status += "; note: could not cache rates for offline use."
        self._status.configure(text=status)

    def _on_fetch_failed(self, reason: str) -> None:
        self.after(0, lambda r=reason: self._show_failure(r))

    def _show_failure(self, reason: str) -> None:
        if self._offline_loaded_date:
            self._status.configure(
                text=f"Could not load live rates: {reason}; offline cache · "
                     f"{self._relative_offline_date_label()}"
            )
        else:
            self._status.configure(
                text=f"Could not load live rates: {reason}; built-in reference rates"
            )

    def _relative_offline_date_label(self) -> str:
        return _relative_rate_date(self._offline_loaded_date or "")

    # --- appearance ---
    def _style_treeview(self) -> None:
        """Theme ttk.Treeview to match CustomTkinter's current appearance mode."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if dark else "#ebebeb"
        fg = "#ffffff" if dark else "#1a1a1a"
        head_bg = "#3a3a3a" if dark else "#d6d6d6"
        font_family = _ui_font_family()
        style.configure(
            "Treeview", background=bg, foreground=fg, fieldbackground=bg,
            rowheight=26, borderwidth=0, font=(font_family, 12),
        )
        style.configure(
            "Treeview.Heading", background=head_bg, foreground=fg,
            borderwidth=0, font=(font_family, 12, "bold"),
        )
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        style.map("Treeview.Heading", background=[("active", head_bg)])
