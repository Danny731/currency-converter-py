from __future__ import annotations

import tkinter.ttk as ttk
from typing import Callable

import customtkinter as ctk

from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    is_currency_code_shape,
)
from storage.settings import AppSettings, DECIMAL_PLACES, THEMES


class SettingsPage(ctk.CTkFrame):
    """Application preferences persisted to settings.json."""

    def __init__(self, master, settings: AppSettings,
                 on_save: Callable[[AppSettings], bool], **kwargs):
        super().__init__(master, **kwargs)
        self._on_save = on_save
        self._settings = settings
        self._currency_vars: dict[str, ctk.BooleanVar] = {}
        self._currency_tree: ttk.Treeview | None = None
        self._available_codes: list[str] = []
        self._currency_names: dict[str, str] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        self._available_codes = codes
        pad = {"padx": 12, "pady": (6, 2)}

        ctk.CTkLabel(self, text="Theme").pack(anchor="w", **pad)
        self._theme_var = ctk.StringVar(value=self._settings.theme)
        ctk.CTkOptionMenu(self, variable=self._theme_var, values=list(THEMES)).pack(
            fill="x", **pad)

        ctk.CTkLabel(self, text="Default source currency").pack(anchor="w", **pad)
        self._source_var = ctk.StringVar(
            value=currency_to_string(self._settings.default_source_currency))
        self._source_menu = ctk.CTkOptionMenu(
            self, variable=self._source_var, values=codes,
        )
        self._source_menu.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Default target currency").pack(anchor="w", **pad)
        self._target_var = ctk.StringVar(
            value=currency_to_string(self._settings.default_target_currency))
        self._target_menu = ctk.CTkOptionMenu(
            self, variable=self._target_var, values=codes,
        )
        self._target_menu.pack(fill="x", **pad)

        ctk.CTkLabel(self, text="Decimal places").pack(anchor="w", **pad)
        self._decimal_var = ctk.StringVar(value=str(self._settings.decimal_places))
        ctk.CTkSegmentedButton(
            self,
            variable=self._decimal_var,
            values=[str(v) for v in DECIMAL_PLACES],
        ).pack(fill="x", **pad)

        currency_header = ctk.CTkFrame(self, fg_color="transparent")
        currency_header.pack(fill="x", padx=12, pady=(10, 2))
        ctk.CTkLabel(currency_header, text="Enabled currencies").pack(side="left")
        ctk.CTkButton(
            currency_header, text="Select All", width=90,
            command=self._select_all_currencies,
        ).pack(side="right", padx=(4, 0))
        ctk.CTkButton(
            currency_header, text="Clear", width=70,
            command=self._clear_currencies,
        ).pack(side="right")

        currency_frame = ctk.CTkFrame(self, fg_color="transparent")
        currency_frame.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        currency_frame.grid_columnconfigure(0, weight=1)
        currency_frame.grid_rowconfigure(0, weight=1)
        self._currency_tree = ttk.Treeview(
            currency_frame,
            columns=("enabled", "currency"),
            show="headings",
            height=6,
            selectmode="browse",
        )
        currency_scrollbar = ctk.CTkScrollbar(
            currency_frame,
            height=1,
            orientation="vertical",
            command=self._currency_tree.yview,
        )
        self._currency_tree.configure(yscrollcommand=currency_scrollbar.set)
        self._currency_tree.heading("enabled", text="On", anchor="center")
        self._currency_tree.heading("currency", text="Currency", anchor="w")
        self._currency_tree.column("enabled", width=56, minwidth=56, anchor="center",
                                   stretch=False)
        self._currency_tree.column("currency", width=420, anchor="w")
        self._currency_tree.grid(row=0, column=0, sticky="nsew")
        currency_scrollbar.grid(row=0, column=1, sticky="ns")
        self._currency_tree.bind("<ButtonRelease-1>", self._on_currency_tree_click)
        self._currency_tree.bind("<space>", self._on_currency_tree_space)
        self._rebuild_currency_checkboxes(codes)

        ctk.CTkButton(self, text="Save Settings", command=self._on_save_clicked).pack(
            fill="x", padx=12, pady=(14, 6))

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))

    def refresh_supported_currencies(self, available_codes: list[str] | None = None,
                                     currency_names: dict[str, str] | None = None) -> None:
        codes = available_codes or [currency_to_string(c) for c in supported_currencies()]
        if not codes:
            return
        if currency_names is not None:
            self._currency_names = currency_names
        self._available_codes = codes
        self._source_menu.configure(values=codes)
        self._target_menu.configure(values=codes)
        if self._source_var.get() not in codes:
            self._source_var.set(codes[0])
        if self._target_var.get() not in codes:
            self._target_var.set(codes[0])
        self._rebuild_currency_checkboxes(codes, self._currency_names)

    def _enabled_currency_codes(self) -> list[str]:
        return [
            code for code, var in self._currency_vars.items()
            if var.get()
        ]

    def _select_all_currencies(self) -> None:
        for var in self._currency_vars.values():
            var.set(True)
        self._refresh_currency_tree_marks()

    def _clear_currencies(self) -> None:
        for var in self._currency_vars.values():
            var.set(False)
        self._refresh_currency_tree_marks()

    def _selected_currency(self, value: str, fallback: Currency) -> Currency:
        return Currency(value) if is_currency_code_shape(value) else fallback

    def _rebuild_currency_checkboxes(self, available_codes: list[str] | None = None,
                                     currency_names: dict[str, str] | None = None) -> None:
        if self._currency_tree is None:
            return
        if currency_names is not None:
            self._currency_names = currency_names
        selected = set(self._enabled_currency_codes())
        if not selected:
            selected = set(self._settings.enabled_currencies)
        codes = (
            available_codes
            or self._available_codes
            or [currency_to_string(c) for c in supported_currencies()]
        )
        if not selected:
            selected = set(codes)

        self._currency_tree.delete(*self._currency_tree.get_children())
        self._currency_vars.clear()

        for code in codes:
            var = ctk.BooleanVar(value=code in selected)
            self._currency_vars[code] = var
            self._currency_tree.insert(
                "",
                "end",
                iid=code,
                values=(self._currency_mark(code), self._currency_label(code)),
            )

    def _currency_label(self, code: str) -> str:
        name = self._currency_names.get(code, "").strip()
        if not name or name.upper() == code:
            return code
        return f"{code} · {name}"

    def _currency_mark(self, code: str) -> str:
        var = self._currency_vars.get(code)
        return "✓" if var is not None and var.get() else ""

    def _refresh_currency_tree_marks(self) -> None:
        if self._currency_tree is None:
            return
        for code in self._currency_tree.get_children():
            self._currency_tree.set(code, "enabled", self._currency_mark(str(code)))

    def _toggle_currency_row(self, code: str) -> None:
        if self._currency_tree is None:
            return
        var = self._currency_vars.get(code)
        if var is None:
            return
        var.set(not var.get())
        self._currency_tree.set(code, "enabled", self._currency_mark(code))
        self._currency_tree.selection_set(code)
        self._currency_tree.focus(code)

    def _on_currency_tree_click(self, event) -> None:
        if self._currency_tree is None:
            return
        row = self._currency_tree.identify_row(event.y)
        if row:
            self._toggle_currency_row(str(row))

    def _on_currency_tree_space(self, _event) -> str:
        if self._currency_tree is None:
            return "break"
        row = self._currency_tree.focus()
        if row:
            self._toggle_currency_row(str(row))
        return "break"

    def _on_save_clicked(self) -> None:
        settings = AppSettings(
            theme=self._theme_var.get(),
            default_source_currency=self._selected_currency(
                self._source_var.get(), Currency.USD),
            default_target_currency=self._selected_currency(
                self._target_var.get(), Currency.USD),
            decimal_places=int(self._decimal_var.get()),
            enabled_currencies=tuple(self._enabled_currency_codes()),
        )
        if len(settings.enabled_currencies) < 2:
            self._status.configure(text="Select at least two enabled currencies.")
            return
        if self._on_save(settings):
            self._settings = settings
            self._status.configure(text="Settings saved.")
        else:
            self._status.configure(text="Warning: could not save settings to disk.")
