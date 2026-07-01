from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import threading
from typing import Callable

import requests

from .currency import (
    Currency,
    CurrencyInfo,
    supported_currencies,
    currency_to_string,
    currency_from_string,
    is_currency_code_shape,
    set_supported_currencies,
)
from .converter import CurrencyConverter

API_ROOT_URL = "https://api.frankfurter.dev/v1"
API_BASE_URL = f"{API_ROOT_URL}/latest"
API_CURRENCIES_URL = f"{API_ROOT_URL}/currencies"
_TIMEOUT = 15  # seconds


@dataclass(frozen=True)
class HistoricalRatePoint:
    date: str
    rate: float


def parse_history_rates(data: dict, target_currency: Currency) -> list[HistoricalRatePoint]:
    points: list[HistoricalRatePoint] = []
    target_code = currency_to_string(target_currency)
    rates_by_date = data.get("rates") or {}
    if not isinstance(rates_by_date, dict):
        return points

    for rate_date, rates in sorted(rates_by_date.items()):
        if not isinstance(rates, dict):
            continue
        try:
            value = float(rates[target_code])
        except (KeyError, TypeError, ValueError):
            continue
        points.append(HistoricalRatePoint(date=str(rate_date), rate=value))
    return points


def parse_supported_currency_codes(data: dict) -> list[str]:
    return [info.code for info in parse_supported_currency_info(data)]


def parse_supported_currency_info(data: dict) -> list[CurrencyInfo]:
    infos: list[CurrencyInfo] = []
    for code, name in data.items():
        if not isinstance(code, str) or not is_currency_code_shape(code):
            continue
        clean = code.strip().upper()
        display_name = str(name).strip() if name else clean
        infos.append(CurrencyInfo(code=clean, name=display_name))
    return sorted(infos, key=lambda info: info.code)


def currency_info_codes(infos: list[CurrencyInfo]) -> list[str]:
    return [info.code for info in infos]


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
        # Original base->target rates from the last successful fetch, kept so
        # callers can persist them for offline reuse.
        self._base_currency = Currency.USD
        self._base_rates: dict[Currency, float] = {}

    @property
    def converter(self) -> CurrencyConverter:
        return self._converter

    @property
    def has_rates(self) -> bool:
        return self._has_rates

    @property
    def last_update_date(self) -> str:
        return self._last_update_date

    @property
    def base_currency(self) -> Currency:
        return self._base_currency

    @property
    def base_rates(self) -> dict[Currency, float]:
        # Return a copy so callers cannot mutate the service's internal state.
        return dict(self._base_rates)

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

            base = self._pending_base
            base_rates: dict[Currency, float] = {}
            for code, rate in rates_obj.items():
                target = currency_from_string(code)
                if target is None:
                    continue
                try:
                    value = float(rate)
                except (TypeError, ValueError):
                    continue
                base_rates[target] = value

            # Derive inverse and cross rates in one shared place.
            converter = CurrencyConverter()
            converter.seed_from_base(base, base_rates)

            self._converter = converter
            self._base_currency = base
            self._base_rates = base_rates
            self._has_rates = True
            self._last_update_date = data.get("date", "")
            on_success()

        threading.Thread(target=worker, daemon=True).start()

    def fetch_supported_currencies(self, on_success: Callable[[list[CurrencyInfo]], None],
                                   on_failure: Callable[[str], None]) -> None:
        def worker() -> None:
            try:
                resp = requests.get(API_CURRENCIES_URL, timeout=_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                on_failure(f"Network error: {e}")
                return
            except ValueError:
                on_failure("Invalid JSON in API response.")
                return

            if not isinstance(data, dict):
                on_failure("Invalid currencies in API response.")
                return

            infos = parse_supported_currency_info(data)
            if not infos:
                on_failure("No currencies found in API response.")
                return

            codes = currency_info_codes(infos)
            set_supported_currencies(codes)
            on_success(infos)

    def fetch_history(self, base_currency: Currency, target_currency: Currency,
                      days: int, on_success: Callable[[list[HistoricalRatePoint]], None],
                      on_failure: Callable[[str], None]) -> None:
        if base_currency == target_currency:
            on_failure("Choose two different currencies.")
            return
        if days <= 0:
            on_failure("History range must be positive.")
            return

        end = date.today()
        start = end - timedelta(days=days)
        url = f"{API_ROOT_URL}/{start.isoformat()}..{end.isoformat()}"
        params = {
            "from": currency_to_string(base_currency),
            "to": currency_to_string(target_currency),
        }

        def worker() -> None:
            try:
                resp = requests.get(url, params=params, timeout=_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                on_failure(f"Network error: {e}")
                return
            except ValueError:
                on_failure("Invalid JSON in API response.")
                return

            points = parse_history_rates(data, target_currency)
            if not points:
                on_failure("No historical rates found in API response.")
                return
            on_success(points)

        threading.Thread(target=worker, daemon=True).start()
