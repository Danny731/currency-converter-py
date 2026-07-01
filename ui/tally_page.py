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
from core.converter import CurrencyConverter, parse_amount
from core.tally import TallyEntry, TallyBook
from storage import tally_storage


class TallyBookPage(ctk.CTkFrame):
    """Add/delete/clear entries in mixed currencies, totalled in a target currency.

    Entries and the chosen target currency are persisted to disk and restored
    on startup; any change is auto-saved.
    """

    def __init__(self, master, default_source: Currency = Currency.CNY,
                 default_target: Currency = Currency.USD,
                 decimal_places: int = 2, **kwargs):
        super().__init__(master, **kwargs)
        self._converter: CurrencyConverter | None = None
        self._tally = TallyBook()
        self._loaded = False
        self._default_source = default_source
        self._default_target = default_target
        self._decimal_places = decimal_places
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

    def apply_preferences(self, default_source: Currency, default_target: Currency,
                          decimal_places: int) -> None:
        self._default_source = default_source
        self._default_target = default_target
        self._decimal_places = decimal_places
        self._source_var.set(currency_to_string(default_source))
        self._target_var.set(currency_to_string(default_target))
        if self._converter:
            self._tally.recalculate(self._current_target_currency(), self._converter)
            self._refresh_table()
            self._update_total()
        if self._loaded and not self._save_state():
            self._status.configure(text="Warning: could not save to disk.")

    # --- UI construction ---
    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        pad = {"padx": 12, "pady": (6, 2)}

        ctk.CTkLabel(self, text="Target currency (for total)").pack(anchor="w", **pad)
        self._target_var = ctk.StringVar(value=currency_to_string(self._default_target))
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
        self._source_var = ctk.StringVar(value=currency_to_string(self._default_source))
        self._source_menu = ctk.CTkOptionMenu(
            self, variable=self._source_var, values=codes,
        )
        self._source_menu.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Note (optional)").pack(anchor="w", **pad)
        self._note_entry = ctk.CTkEntry(self, placeholder_text="e.g. Lunch")
        self._note_entry.pack(fill="x", **pad)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkButton(btns, text="Add Entry", command=self._on_add).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btns, text="Edit Selected", command=self._on_edit_selected).pack(
            side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(btns, text="Delete Selected", command=self._on_delete).pack(
            side="left", expand=True, fill="x", padx=4)
        ctk.CTkButton(btns, text="Clear All", command=self._on_clear).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        # Entries table.
        table_frame = ctk.CTkFrame(self, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=12, pady=6)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        self._tree = ttk.Treeview(
            table_frame, columns=("time", "amount", "currency", "converted", "note"),
            show="headings", height=8, selectmode="extended",
        )
        table_scrollbar = ctk.CTkScrollbar(
            table_frame, height=1, orientation="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=table_scrollbar.set)
        for col, label, width, anchor in (
            ("time", "Time", 145, "center"),
            ("amount", "Amount", 110, "e"),
            ("currency", "Currency", 90, "w"),
            ("converted", "Converted", 120, "e"),
            ("note", "Note", 200, "center"),
        ):
            self._tree.heading(col, text=label, anchor=anchor)
            self._tree.column(col, width=width, anchor=anchor)
        self._tree.grid(row=0, column=0, sticky="nsew")
        table_scrollbar.grid(row=0, column=1, sticky="ns")
        self._tree.bind("<Double-1>", self._on_tree_double_click)

        self._total_label = ctk.CTkLabel(
            self, text="Total: --", anchor="w", font=ctk.CTkFont(weight="bold"))
        self._total_label.pack(fill="x", padx=12)

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

    def refresh_supported_currencies(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        if not codes:
            return
        self._target_menu.configure(values=codes)
        self._source_menu.configure(values=codes)
        if self._target_var.get() not in codes:
            self._target_var.set(codes[0])
        if self._source_var.get() not in codes:
            self._source_var.set(codes[0])
        if self._converter:
            self._tally.recalculate(self._current_target_currency(), self._converter)
            self._refresh_table()
            self._update_total()

    # --- helpers ---
    def _current_target_currency(self) -> Currency:
        return currency_from_string(self._target_var.get()) or Currency.USD

    def _current_source_currency(self) -> Currency:
        return currency_from_string(self._source_var.get()) or Currency.CNY

    def _entry_time_text(self, entry: TallyEntry) -> str:
        return entry.created_at.strftime("%Y-%m-%d %H:%M")

    def _on_target_changed(self, _value: str) -> None:
        # Recompute totals for the new target, then persist the choice.
        if self._converter:
            self._tally.recalculate(self._current_target_currency(), self._converter)
            self._refresh_table()
            self._update_total()
        if not self._save_state():
            self._status.configure(text="Warning: could not save to disk.")

    def _on_add(self) -> None:
        if self._converter is None:
            self._status.configure(text="No converter available.")
            return
        text = self._amount_entry.get().strip()
        if not text:
            self._status.configure(text="Please enter an amount.")
            return
        amount = parse_amount(text)
        if amount is None:
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
        self._finish("Entry added.")

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
        self._finish("Entry deleted.")

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
            self._finish("All entries cleared.")

    def _on_tree_double_click(self, event) -> None:
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        self._tree.selection_set(iid)
        self._tree.focus(iid)
        self._on_edit_selected()

    def _on_edit_selected(self) -> None:
        if self._converter is None:
            self._status.configure(text="No converter available.")
            return
        selected = self._tree.selection()
        if not selected:
            self._status.configure(text="Please select a row to edit.")
            return
        if len(selected) > 1:
            self._status.configure(text="Please select only one row to edit.")
            return
        row = self._tree.index(selected[0])
        entries = self._tally.entries()
        if not 0 <= row < len(entries):
            self._status.configure(text="Selected row is no longer available.")
            return
        self._show_edit_dialog(row, entries[row])

    def _show_edit_dialog(self, row: int, entry: TallyEntry) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Entry")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        dialog.resizable(False, False)

        body = ctk.CTkFrame(dialog, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(body, text="Amount").pack(anchor="w", pady=(0, 4))
        decimals = CurrencyConverter.decimal_places(entry.currency, self._decimal_places)
        amount_var = ctk.StringVar(value=f"{entry.amount:.{decimals}f}")
        amount_entry = ctk.CTkEntry(body, textvariable=amount_var, width=280)
        amount_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(body, text="Currency").pack(anchor="w", pady=(0, 4))
        currency_var = ctk.StringVar(value=currency_to_string(entry.currency))
        ctk.CTkOptionMenu(body, variable=currency_var, values=codes).pack(
            fill="x", pady=(0, 10))

        ctk.CTkLabel(body, text="Note").pack(anchor="w", pady=(0, 4))
        note_var = ctk.StringVar(value=entry.note)
        ctk.CTkEntry(body, textvariable=note_var, width=280).pack(
            fill="x", pady=(0, 10))

        status = ctk.CTkLabel(body, text="", anchor="w", justify="left",
                              wraplength=280)
        status.pack(fill="x", pady=(0, 10))

        def save() -> None:
            amount = parse_amount(amount_var.get().strip())
            if amount is None:
                status.configure(text="Enter a non-negative amount.")
                return
            currency = currency_from_string(currency_var.get()) or entry.currency
            if self._converter is None:
                status.configure(text="No converter available.")
                return
            ok = self._tally.update_entry(
                row, amount, currency, self._current_target_currency(),
                self._converter, note_var.get().strip(),
            )
            if not ok:
                status.configure(text="Failed to convert. Exchange rate may be missing.")
                return
            self._refresh_table()
            self._update_total()
            self._finish("Entry updated.")
            dialog.destroy()

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x")
        ctk.CTkButton(buttons, text="Cancel", command=dialog.destroy).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(buttons, text="Save", command=save).pack(
            side="left", expand=True, fill="x", padx=(4, 0))

        amount_entry.bind("<Return>", lambda _e: save())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        amount_entry.focus_set()

    def _refresh_table(self) -> None:
        self._tree.delete(*self._tree.get_children())
        target_currency = self._current_target_currency()
        for e in self._tally.entries():
            self._tree.insert("", "end", values=(
                self._entry_time_text(e),
                CurrencyConverter.format_result(e.amount, e.currency, self._decimal_places),
                currency_to_string(e.currency),
                CurrencyConverter.format_result(
                    e.converted_amount, target_currency, self._decimal_places),
                e.note,
            ))

    def _update_total(self) -> None:
        if self._tally.count() == 0:
            self._total_label.configure(text="Total: --")
        else:
            target_currency = self._current_target_currency()
            self._total_label.configure(
                text=f"Total: {CurrencyConverter.format_result(self._tally.total(), target_currency, self._decimal_places)} "
                     f"{currency_to_string(target_currency)}"
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

    def _save_state(self) -> bool:
        return tally_storage.save(self._tally.entries(), self._current_target_currency())

    def _finish(self, success_msg: str) -> None:
        """Persist state and report the outcome. On a save failure the user is
        warned explicitly rather than silently risking lost data."""
        if self._save_state():
            self._status.configure(text=success_msg)
        else:
            self._status.configure(
                text="Warning: could not save to disk. Your changes may be "
                     "lost on exit."
            )
