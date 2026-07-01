from __future__ import annotations

import tkinter.ttk as ttk

import customtkinter as ctk

from core.conversion_history import ConversionHistory, ConversionHistoryEntry
from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
)
from core.converter import CurrencyConverter, parse_amount


class ConverterPage(ctk.CTkFrame):
    """Source currency + amount input, and a results table for all currencies."""

    def __init__(self, master, default_source: Currency = Currency.USD,
                 decimal_places: int = 2, **kwargs):
        super().__init__(master, **kwargs)
        self._converter: CurrencyConverter | None = None
        self._default_source = default_source
        self._decimal_places = decimal_places
        self._history = ConversionHistory()
        self._setup_ui()

    def set_converter(self, converter: CurrencyConverter) -> None:
        self._converter = converter

    def apply_preferences(self, default_source: Currency,
                          decimal_places: int) -> None:
        self._default_source = default_source
        self._decimal_places = decimal_places
        self._source_var.set(currency_to_string(default_source))
        if parse_amount(self._amount_entry.get().strip()) is not None:
            self._on_convert(record_history=False)

    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        pad = {"padx": 12, "pady": (6, 2)}

        ctk.CTkLabel(self, text="Source currency").pack(anchor="w", **pad)
        self._source_var = ctk.StringVar(value=currency_to_string(self._default_source))
        self._source_menu = ctk.CTkOptionMenu(
            self, variable=self._source_var, values=codes,
        )
        self._source_menu.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Amount").pack(anchor="w", **pad)
        self._amount_entry = ctk.CTkEntry(self, placeholder_text="Enter amount, e.g. 100.00")
        self._amount_entry.pack(fill="x", **pad)
        self._amount_entry.bind("<Return>", lambda _e: self._on_convert())

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkButton(btns, text="Convert", command=self._on_convert).pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        ctk.CTkButton(
            btns, text="Swap with Selected", command=self._on_swap_selected,
        ).pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Results table (Currency | Amount).
        self._tree = ttk.Treeview(
            self, columns=("currency", "amount"), show="headings", height=9
        )
        self._tree.heading("currency", text="Currency")
        self._tree.heading("amount", text="Amount")
        self._tree.column("currency", width=170, anchor="w")
        self._tree.column("amount", width=170, anchor="e")
        for c in supported_currencies():
            code = currency_to_string(c)
            self._tree.insert("", "end", iid=code, values=(code, "--"))
        self._tree.pack(fill="both", expand=True, padx=12, pady=6)

        history_bar = ctk.CTkFrame(self, fg_color="transparent")
        history_bar.pack(fill="x", padx=12, pady=(4, 2))
        ctk.CTkLabel(
            history_bar, text="Conversion History", anchor="w",
            font=ctk.CTkFont(weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            history_bar, text="Clear History", width=110,
            command=self._on_clear_history,
        ).pack(side="right")

        self._history_tree = ttk.Treeview(
            self, columns=("time", "source", "amount"), show="headings", height=5
        )
        self._history_tree.heading("time", text="Time")
        self._history_tree.heading("source", text="Source")
        self._history_tree.heading("amount", text="Amount")
        self._history_tree.column("time", width=145, anchor="center")
        self._history_tree.column("source", width=90, anchor="w")
        self._history_tree.column("amount", width=170, anchor="e")
        self._history_tree.pack(fill="both", expand=False, padx=12, pady=(0, 6))
        self._history_tree.bind("<Double-1>", self._on_history_double_click)

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

    def refresh_supported_currencies(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        if not codes:
            return
        self._source_menu.configure(values=codes)
        if self._source_var.get() not in codes:
            self._source_var.set(codes[0])

        self._tree.delete(*self._tree.get_children())
        for code in codes:
            self._tree.insert("", "end", iid=code, values=(code, "--"))
        if parse_amount(self._amount_entry.get().strip()) is not None:
            self._on_convert(record_history=False)

    def _source_currency(self) -> Currency:
        return currency_from_string(self._source_var.get()) or Currency.USD

    def _selected_currency(self) -> Currency | None:
        selected = self._tree.selection()
        if not selected:
            return None
        return currency_from_string(str(selected[0]))

    def _format_amount_input(self, value: float, currency: Currency) -> str:
        decimals = CurrencyConverter.decimal_places(currency, self._decimal_places)
        return f"{value:.{decimals}f}"

    def _clear_results(self) -> None:
        for c in supported_currencies():
            self._tree.set(currency_to_string(c), "amount", "--")

    def _history_time_text(self, entry: ConversionHistoryEntry) -> str:
        return entry.created_at.strftime("%Y-%m-%d %H:%M")

    def _refresh_history(self) -> None:
        self._history_tree.delete(*self._history_tree.get_children())
        for index, entry in enumerate(self._history.entries()):
            self._history_tree.insert("", "end", iid=str(index), values=(
                self._history_time_text(entry),
                currency_to_string(entry.source_currency),
                CurrencyConverter.format_result(
                    entry.amount, entry.source_currency, self._decimal_places),
            ))

    def _on_history_double_click(self, event) -> None:
        iid = self._history_tree.identify_row(event.y)
        if not iid:
            return
        try:
            index = int(iid)
        except ValueError:
            return
        entries = self._history.entries()
        if not 0 <= index < len(entries):
            return
        entry = entries[index]
        if currency_from_string(currency_to_string(entry.source_currency)) is None:
            self._history_tree.selection_set(iid)
            self._history_tree.focus(iid)
            self._status.configure(
                text=f"{currency_to_string(entry.source_currency)} is disabled in "
                     f"Settings. Enable it to reuse this conversion."
            )
            return
        self._source_var.set(currency_to_string(entry.source_currency))
        self._amount_entry.delete(0, "end")
        self._amount_entry.insert(
            0, self._format_amount_input(entry.amount, entry.source_currency))
        self._on_convert(record_history=False)
        self._history_tree.selection_set(iid)
        self._history_tree.focus(iid)
        self._status.configure(text="Loaded conversion from history.")

    def _on_clear_history(self) -> None:
        self._history.clear()
        self._refresh_history()
        self._status.configure(text="Conversion history cleared.")

    def _on_swap_selected(self) -> None:
        if self._converter is None:
            self._status.configure(text="No converter available.")
            return

        target = self._selected_currency()
        if target is None:
            self._status.configure(text="Select a result row to swap with.")
            return

        source = self._source_currency()
        if target == source:
            self._status.configure(text="Select a different currency to swap with.")
            return

        amount = parse_amount(self._amount_entry.get().strip())
        if amount is None:
            self._status.configure(text="Enter a valid amount before swapping.")
            self._clear_results()
            return

        swapped_amount = self._converter.convert(amount, source, target)
        if swapped_amount < 0.0:
            self._status.configure(text="Cannot swap because the exchange rate is missing.")
            return

        self._source_var.set(currency_to_string(target))
        self._amount_entry.delete(0, "end")
        self._amount_entry.insert(0, self._format_amount_input(swapped_amount, target))
        self._on_convert()
        self._tree.selection_set(currency_to_string(source))
        self._tree.focus(currency_to_string(source))
        self._status.configure(text="Swapped with selected currency.")

    def _on_convert(self, record_history: bool = True) -> None:
        if self._converter is None:
            self._status.configure(text="No converter available.")
            return

        text = self._amount_entry.get().strip()
        if not text:
            self._status.configure(text="Please enter an amount.")
            self._clear_results()
            return
        amount = parse_amount(text)
        if amount is None:
            self._status.configure(text="Invalid amount. Please enter a non-negative number.")
            self._clear_results()
            return

        source = self._source_currency()
        missing = 0
        for c in supported_currencies():
            result = self._converter.convert(amount, source, c)
            code = currency_to_string(c)
            if result < 0.0:
                self._tree.set(code, "amount", "--")
                if c != source:
                    missing += 1
            else:
                self._tree.set(
                    code, "amount",
                    CurrencyConverter.format_result(result, c, self._decimal_places),
                )

        if missing > 0:
            self._status.configure(text=f"Conversion complete. {missing} rate(s) missing.")
        else:
            self._status.configure(text="Converted successfully.")
        if record_history:
            self._history.add(amount, source)
            self._refresh_history()
