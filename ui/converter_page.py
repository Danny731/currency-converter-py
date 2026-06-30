from __future__ import annotations

import tkinter.ttk as ttk

import customtkinter as ctk

from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
)
from core.converter import CurrencyConverter, parse_amount


class ConverterPage(ctk.CTkFrame):
    """Source currency + amount input, and a results table for all currencies."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._converter: CurrencyConverter | None = None
        self._setup_ui()

    def set_converter(self, converter: CurrencyConverter) -> None:
        self._converter = converter

    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        pad = {"padx": 12, "pady": (6, 2)}

        ctk.CTkLabel(self, text="Source currency").pack(anchor="w", **pad)
        self._source_var = ctk.StringVar(value=currency_to_string(Currency.USD))
        ctk.CTkOptionMenu(self, variable=self._source_var, values=codes).pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Amount").pack(anchor="w", **pad)
        self._amount_entry = ctk.CTkEntry(self, placeholder_text="Enter amount, e.g. 100.00")
        self._amount_entry.pack(fill="x", **pad)
        self._amount_entry.bind("<Return>", lambda _e: self._on_convert())

        ctk.CTkButton(self, text="Convert", command=self._on_convert).pack(
            fill="x", padx=12, pady=(10, 6)
        )

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

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

    def _source_currency(self) -> Currency:
        return currency_from_string(self._source_var.get()) or Currency.USD

    def _clear_results(self) -> None:
        for c in supported_currencies():
            self._tree.set(currency_to_string(c), "amount", "--")

    def _on_convert(self) -> None:
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
                self._tree.set(code, "amount", CurrencyConverter.format_result(result))

        if missing > 0:
            self._status.configure(text=f"Conversion complete. {missing} rate(s) missing.")
        else:
            self._status.configure(text="Converted successfully.")
