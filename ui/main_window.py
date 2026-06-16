from __future__ import annotations

import tkinter.ttk as ttk

import customtkinter as ctk

from core.currency import Currency, supported_currencies
from core.converter import CurrencyConverter
from core.rate_service import ExchangeRateService
from ui.converter_page import ConverterPage
from ui.tally_page import TallyBookPage

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
        self.geometry("780x580")
        self.minsize(620, 480)
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._converter = CurrencyConverter()
        self._setup_mock_rates()
        self._rate_service = ExchangeRateService()

        self._tabview = ctk.CTkTabview(self)
        self._tabview.pack(fill="both", expand=True, padx=12, pady=(12, 0))
        self._tabview.add("Currency Converter")
        self._tabview.add("Tally Book")

        self._converter_page = ConverterPage(self._tabview.tab("Currency Converter"))
        self._converter_page.pack(fill="both", expand=True)
        self._converter_page.set_converter(self._converter)

        self._tally_page = TallyBookPage(self._tabview.tab("Tally Book"))
        self._tally_page.pack(fill="both", expand=True)
        self._tally_page.set_converter(self._converter)

        self._status = ctk.CTkLabel(
            self, text="Using mock exchange rates. Fetching live rates...",
            anchor="w",
        )
        self._status.pack(fill="x", padx=12, pady=(6, 12))

        self.after(50, self._style_treeview)
        self._fetch_live_rates()

    # --- rates ---
    def _setup_mock_rates(self) -> None:
        for cur, rate in _MOCK_USD_RATES.items():
            self._converter.set_rate(Currency.USD, cur, rate)
            if rate > 0.0:
                self._converter.set_rate(cur, Currency.USD, 1.0 / rate)
        for frm in supported_currencies():
            for to in supported_currencies():
                if frm == to or self._converter.has_rate(frm, to):
                    continue
                from_usd = self._converter.convert(1.0, frm, Currency.USD)
                usd_to = self._converter.convert(1.0, Currency.USD, to)
                if from_usd > 0.0 and usd_to > 0.0:
                    self._converter.set_rate(frm, to, from_usd * usd_to)

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
        self._status.configure(
            text=f"Live rates loaded (source: Frankfurter API, date: "
                 f"{self._rate_service.last_update_date})"
        )

    def _on_fetch_failed(self, reason: str) -> None:
        self.after(0, lambda r=reason: self._show_failure(r))

    def _show_failure(self, reason: str) -> None:
        self._status.configure(
            text=f"Could not load live rates: {reason} — using mock rates."
        )

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
        style.configure(
            "Treeview", background=bg, foreground=fg, fieldbackground=bg,
            rowheight=26, borderwidth=0, font=("Segoe UI", 12),
        )
        style.configure(
            "Treeview.Heading", background=head_bg, foreground=fg,
            borderwidth=0, font=("Segoe UI", 12, "bold"),
        )
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        style.map("Treeview.Heading", background=[("active", head_bg)])
