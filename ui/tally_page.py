from __future__ import annotations

import tkinter.ttk as ttk
from tkinter import messagebox

import customtkinter as ctk

from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
)
from core.converter import CurrencyConverter
from core.tally import TallyEntry, TallyBook
from storage import tally_storage


class TallyBookPage(ctk.CTkFrame):
    """Add/delete/clear entries in mixed currencies, totalled in a target currency.

    Entries and the chosen target currency are persisted to disk and restored
    on startup; any change is auto-saved.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._converter: CurrencyConverter | None = None
        self._tally = TallyBook()
        self._loaded = False
        self._setup_ui()

    def set_converter(self, converter: CurrencyConverter) -> None:
        self._converter = converter
        # Restore persisted entries once a converter is available, then keep
        # converted totals consistent whenever rates change.
        if not self._loaded:
            self._loaded = True
            self._load_state()
        if self._converter and self._tally.count() > 0:
            self._tally.recalculate(self._current_target_currency(), self._converter)
            self._refresh_table()
            self._update_total()

    # --- UI construction ---
    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        pad = {"padx": 12, "pady": (6, 2)}

        ctk.CTkLabel(self, text="Target currency (for total)").pack(anchor="w", **pad)
        self._target_var = ctk.StringVar(value=currency_to_string(Currency.USD))
        self._target_menu = ctk.CTkOptionMenu(
            self, variable=self._target_var, values=codes,
            command=self._on_target_changed,
        )
        self._target_menu.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Amount").pack(anchor="w", **pad)
        self._amount_entry = ctk.CTkEntry(self, placeholder_text="e.g. 123.45")
        self._amount_entry.pack(fill="x", **pad)
        self._amount_entry.bind("<Return>", lambda _e: self._on_add())

        ctk.CTkLabel(self, text="Currency").pack(anchor="w", **pad)
        self._source_var = ctk.StringVar(value=currency_to_string(Currency.CNY))
        ctk.CTkOptionMenu(self, variable=self._source_var, values=codes).pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Note (optional)").pack(anchor="w", **pad)
        self._note_entry = ctk.CTkEntry(self, placeholder_text="e.g. Lunch")
        self._note_entry.pack(fill="x", **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkButton(btns, text="Add Entry", command=self._on_add).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btns, text="Delete Selected", command=self._on_delete).pack(
            side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(btns, text="Clear All", command=self._on_clear).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # Entries table.
        self._tree = ttk.Treeview(
            self, columns=("amount", "currency", "converted", "note"),
            show="headings", height=8, selectmode="extended",
        )
        for col, label, width, anchor in (
            ("amount", "Amount", 110, "e"),
            ("currency", "Currency", 90, "w"),
            ("converted", "Converted", 120, "e"),
            ("note", "Note", 200, "w"),
        ):
            self._tree.heading(col, text=label, anchor=anchor)
            self._tree.column(col, width=width, anchor=anchor)
        self._tree.pack(fill="both", expand=True, padx=12, pady=6)

        self._total_label = ctk.CTkLabel(
            self, text="Total: --", anchor="w", font=ctk.CTkFont(weight="bold"))
        self._total_label.pack(fill="x", padx=12)

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

    # --- helpers ---
    def _current_target_currency(self) -> Currency:
        return currency_from_string(self._target_var.get()) or Currency.USD

    def _current_source_currency(self) -> Currency:
        return currency_from_string(self._source_var.get()) or Currency.CNY

    def _on_target_changed(self, _value: str) -> None:
        # Recompute totals for the new target, then persist the choice.
        if self._converter:
            self._tally.recalculate(self._current_target_currency(), self._converter)
            self._refresh_table()
            self._update_total()
        self._save_state()

    def _on_add(self) -> None:
        if self._converter is None:
            self._status.configure(text="No converter available.")
            return
        text = self._amount_entry.get().strip()
        if not text:
            self._status.configure(text="Please enter an amount.")
            return
        try:
            amount = float(text)
        except ValueError:
            amount = -1.0
        if amount < 0.0:
            self._status.configure(text="Invalid amount. Please enter a non-negative number.")
            return

        entry = TallyEntry(
            amount=amount,
            currency=self._current_source_currency(),
            note=self._note_entry.get().strip(),
        )
        if not self._tally.add_entry(entry, self._current_target_currency(), self._converter):
            self._status.configure(text="Failed to convert. Exchange rate may be missing.")
            return

        self._amount_entry.delete(0, "end")
        self._note_entry.delete(0, "end")
        self._refresh_table()
        self._update_total()
        self._save_state()
        self._status.configure(text="Entry added.")

    def _on_delete(self) -> None:
        selected = self._tree.selection()
        if not selected:
            self._status.configure(text="Please select a row to delete.")
            return
        # Delete highest model index first so earlier indices stay valid.
        rows = sorted((self._tree.index(iid) for iid in selected), reverse=True)
        for row in rows:
            self._tally.remove_entry(row)
        self._refresh_table()
        self._update_total()
        self._save_state()
        self._status.configure(text="Entry deleted.")

    def _on_clear(self) -> None:
        if self._tally.count() == 0:
            return
        if messagebox.askyesno(
            "Clear All",
            f"Delete all {self._tally.count()} entry/entries?",
            default="no", parent=self,
        ):
            self._tally.clear()
            self._refresh_table()
            self._update_total()
            self._save_state()
            self._status.configure(text="All entries cleared.")

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        for e in self._tally.entries():
            self._tree.insert("", "end", values=(
                CurrencyConverter.format_result(e.amount),
                currency_to_string(e.currency),
                CurrencyConverter.format_result(e.converted_amount),
                e.note,
            ))

    def _update_total(self) -> None:
        if self._tally.count() == 0:
            self._total_label.configure(text="Total: --")
        else:
            self._total_label.configure(
                text=f"Total: {CurrencyConverter.format_result(self._tally.total())} "
                     f"{currency_to_string(self._current_target_currency())}"
            )

    def _load_state(self) -> None:
        ok, entries, target = tally_storage.load()
        if not ok:
            return  # nothing stored (or corrupt): keep a fresh tally book
        self._tally.set_entries(entries)
        # Restore the target selection without triggering a save of what we
        # just read by temporarily detaching the change callback.
        self._target_menu.configure(command=None)
        self._target_var.set(currency_to_string(target))
        self._target_menu.configure(command=self._on_target_changed)
        if self._converter:
            self._tally.recalculate(self._current_target_currency(), self._converter)
        self._refresh_table()
        self._update_total()

    def _save_state(self) -> None:
        tally_storage.save(self._tally.entries(), self._current_target_currency())
