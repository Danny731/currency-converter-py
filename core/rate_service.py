from __future__ import annotations

import threading
from typing import Callable

import requests

from .currency import (
    Currency,
    supported_currencies,
    currency_to_string,
    currency_from_string,
)
from .converter import CurrencyConverter

API_BASE_URL = "https://api.frankfurter.dev/v1/latest"
_TIMEOUT = 15  # seconds


class ExchangeRateService:
    """Fetches live exchange rates from the Frankfurter API (free, no key).

    fetch_rates() runs the network request on a background thread and invokes
    one of the callbacks on completion. Callers are responsible for marshalling
    the callback onto their UI thread (Tkinter: use widget.after(0, ...)).
    """

    def __init__(self) -> None:
        self._converter = CurrencyConverter()
        self._has_rates = False
        self._last_update_date = ""
        self._pending_base = Currency.USD

    @property
    def converter(self) -> CurrencyConverter:
        return self._converter

    @property
    def has_rates(self) -> bool:
        return self._has_rates

    @property
    def last_update_date(self) -> str:
        return self._last_update_date

    def fetch_rates(self, base_currency: Currency,
                    on_success: Callable[[], None],
                    on_failure: Callable[[str], None]) -> None:
        self._pending_base = base_currency
        targets = [currency_to_string(c) for c in supported_currencies() if c != base_currency]
        params = {"from": currency_to_string(base_currency), "to": ",".join(targets)}

        def worker() -> None:
            try:
                resp = requests.get(API_BASE_URL, params=params, timeout=_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                on_failure(f"Network error: {e}")
                return
            except ValueError:
                on_failure("Invalid JSON in API response.")
                return

            rates_obj = data.get("rates") or {}
            if not rates_obj:
                on_failure("No rates found in API response.")
                return

            converter = CurrencyConverter()
            base = self._pending_base
            for code, rate in rates_obj.items():
                target = currency_from_string(code)
                if target is None:
                    continue
                value = float(rate)
                converter.set_rate(base, target, value)
                if value > 0.0:
                    converter.set_rate(target, base, 1.0 / value)

            # Cross rates through the base for any pair not yet covered.
            for frm in supported_currencies():
                for to in supported_currencies():
                    if frm == to or converter.has_rate(frm, to):
                        continue
                    from_base = converter.convert(1.0, frm, base)
                    base_to = converter.convert(1.0, base, to)
                    if from_base > 0.0 and base_to > 0.0:
                        converter.set_rate(frm, to, from_base * base_to)

            self._converter = converter
            self._has_rates = True
            self._last_update_date = data.get("date", "")
            on_success()

        threading.Thread(target=worker, daemon=True).start()
