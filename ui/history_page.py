from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

import customtkinter as ctk

from core.currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
)
from core.rate_service import ExchangeRateService, HistoricalRatePoint


class HistoryPage(ctk.CTkFrame):
    """Historical exchange-rate trend chart for a selected currency pair."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._rate_service: ExchangeRateService | None = None
        self._points: list[HistoricalRatePoint] = []
        self._chart_title = ""
        self._request_id = 0
        self._setup_ui()

    def set_rate_service(self, rate_service: ExchangeRateService) -> None:
        self._rate_service = rate_service

    def _setup_ui(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=12, pady=(12, 8))
        controls.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(controls, text="From").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkLabel(controls, text="To").grid(row=0, column=1, sticky="w", padx=6)
        ctk.CTkLabel(controls, text="Range").grid(row=0, column=2, sticky="w", padx=6)

        self._source_var = ctk.StringVar(value=currency_to_string(Currency.USD))
        self._source_menu = ctk.CTkOptionMenu(
            controls, variable=self._source_var, values=codes,
        )
        self._source_menu.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=(4, 0))

        self._target_var = ctk.StringVar(value=currency_to_string(Currency.CNY))
        self._target_menu = ctk.CTkOptionMenu(
            controls, variable=self._target_var, values=codes,
        )
        self._target_menu.grid(row=1, column=1, sticky="ew", padx=6, pady=(4, 0))

        self._range_var = ctk.StringVar(value="30 days")
        ctk.CTkSegmentedButton(
            controls, variable=self._range_var, values=["30 days", "90 days"],
        ).grid(row=1, column=2, sticky="ew", padx=6, pady=(4, 0))

        self._load_button = ctk.CTkButton(
            controls, text="Load Trend", command=self._on_load,
        )
        self._load_button.grid(row=1, column=3, sticky="ew", padx=(6, 0), pady=(4, 0))

        self._canvas = tk.Canvas(self, highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self._canvas.bind("<Configure>", lambda _e: self._draw_chart())

        self._status = ctk.CTkLabel(self, text="", anchor="w", justify="left",
                                    wraplength=540)
        self._status.pack(fill="x", padx=12, pady=(0, 8))
        self._draw_chart()

    def refresh_supported_currencies(self) -> None:
        codes = [currency_to_string(c) for c in supported_currencies()]
        if not codes:
            return
        self._source_menu.configure(values=codes)
        self._target_menu.configure(values=codes)
        if self._source_var.get() not in codes:
            self._source_var.set(codes[0])
        if self._target_var.get() not in codes:
            self._target_var.set(codes[1] if len(codes) > 1 else codes[0])

    def _source_currency(self) -> Currency:
        return currency_from_string(self._source_var.get()) or Currency.USD

    def _target_currency(self) -> Currency:
        return currency_from_string(self._target_var.get()) or Currency.CNY

    def _range_days(self) -> int:
        return 90 if self._range_var.get() == "90 days" else 30

    def _on_load(self) -> None:
        if self._rate_service is None:
            self._status.configure(text="No rate service available.")
            return

        source = self._source_currency()
        target = self._target_currency()
        if source == target:
            self._status.configure(text="Choose two different currencies.")
            self._points = []
            self._chart_title = ""
            self._draw_chart()
            return

        self._request_id += 1
        request_id = self._request_id
        days = self._range_days()
        self._load_button.configure(state="disabled")
        self._status.configure(
            text=f"Loading {days}-day trend for "
                 f"{currency_to_string(source)} → {currency_to_string(target)}..."
        )

        self._rate_service.fetch_history(
            source,
            target,
            days,
            on_success=lambda points, rid=request_id:
                self.after(0, lambda: self._apply_history(rid, source, target, points)),
            on_failure=lambda reason, rid=request_id:
                self.after(0, lambda: self._show_failure(rid, reason)),
        )

    def _apply_history(self, request_id: int, source: Currency, target: Currency,
                       points: list[HistoricalRatePoint]) -> None:
        if request_id != self._request_id:
            return
        self._load_button.configure(state="normal")
        self._points = points
        self._chart_title = f"{currency_to_string(source)} → {currency_to_string(target)}"
        self._status.configure(
            text=f"Loaded {len(points)} rate points from "
                 f"{points[0].date} to {points[-1].date}."
        )
        self._draw_chart()

    def _show_failure(self, request_id: int, reason: str) -> None:
        if request_id != self._request_id:
            return
        self._load_button.configure(state="normal")
        self._points = []
        self._chart_title = ""
        self._status.configure(text=f"Could not load historical rates: {reason}")
        self._draw_chart()

    def _draw_chart(self) -> None:
        self._canvas.delete("all")
        width = max(self._canvas.winfo_width(), 1)
        height = max(self._canvas.winfo_height(), 1)
        dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if dark else "#f4f4f5"
        fg = "#f5f5f5" if dark else "#1f2933"
        muted = "#a8a8a8" if dark else "#667085"
        grid = "#3d3d3d" if dark else "#d0d5dd"
        line = "#3b82f6"
        self._canvas.configure(bg=bg)

        if width < 80 or height < 80:
            return

        if not self._points:
            self._canvas.create_text(
                width / 2, height / 2, text="No trend loaded",
                fill=muted, font=("TkDefaultFont", 13),
            )
            return

        right, top, bottom = 18, 28, 46
        rates = [p.rate for p in self._points]
        min_rate = min(rates)
        max_rate = max(rates)
        if min_rate == max_rate:
            padding = max(abs(min_rate) * 0.05, 1.0)
            min_rate -= padding
            max_rate += padding
        else:
            padding = (max_rate - min_rate) * 0.08
            min_rate -= padding
            max_rate += padding

        tick_labels = [
            self._format_rate(max_rate - (max_rate - min_rate) * (i / 4))
            for i in range(5)
        ]
        label_font = tkfont.Font(font=("TkDefaultFont", 10))
        left = max(58, max(label_font.measure(label) for label in tick_labels) + 18)
        chart_w = max(width - left - right, 1)
        chart_h = max(height - top - bottom, 1)

        self._canvas.create_text(
            left, 12, text=self._chart_title, anchor="w", fill=fg,
            font=("TkDefaultFont", 13, "bold"),
        )

        for i in range(5):
            ratio = i / 4
            y = top + chart_h * ratio
            value_label = tick_labels[i]
            self._canvas.create_line(left, y, width - right, y, fill=grid)
            self._canvas.create_text(
                left - 8, y, text=value_label,
                anchor="e", fill=muted, font=("TkDefaultFont", 10),
            )

        coords: list[float] = []
        count = len(self._points)
        for index, point in enumerate(self._points):
            x = left + (chart_w / 2 if count == 1 else chart_w * index / (count - 1))
            y = top + chart_h * (1 - (point.rate - min_rate) / (max_rate - min_rate))
            coords.extend([x, y])

        if len(coords) >= 4:
            self._canvas.create_line(coords, fill=line, width=2)
        for x, y in zip(coords[0::2], coords[1::2]):
            self._canvas.create_oval(x - 2, y - 2, x + 2, y + 2, fill=line, outline=line)

        self._canvas.create_line(left, top, left, height - bottom, fill=muted)
        self._canvas.create_line(left, height - bottom, width - right, height - bottom, fill=muted)
        self._canvas.create_text(
            left, height - 20, text=self._points[0].date,
            anchor="w", fill=muted, font=("TkDefaultFont", 10),
        )
        self._canvas.create_text(
            width - right, height - 20, text=self._points[-1].date,
            anchor="e", fill=muted, font=("TkDefaultFont", 10),
        )

    def _format_rate(self, value: float) -> str:
        if abs(value) >= 100:
            return f"{value:,.2f}"
        if abs(value) >= 1:
            return f"{value:,.4f}"
        return f"{value:,.6f}"
