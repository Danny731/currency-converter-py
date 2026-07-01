# Currency Converter (Python)

A small personal desktop tool for currency conversion and a multi-currency tally
book (expense log). This is the Python port of the original
[Qt6/C++ Multifunctional-Currency-Converter](https://github.com/Danny731/Multifunctional-Currency-Converter),
rebuilt with [CustomTkinter](https://customtkinter.tomschimansky.com/) for a
modern look with minimal dependencies.

## Features

- **Currency Converter** — enter an amount in a source currency and see it
  converted into every supported currency at once, with a recent conversion
  history you can clear at any time.
- **Tally Book** — log expenses in mixed currencies, automatically totalled in a
  chosen target currency. Add / delete / clear entries, with optional notes.
- **Rate History** — plot a 30- or 90-day historical trend for any supported
  currency pair using Frankfurter time-series data.
- **Settings** — persist theme, default currencies, and decimal display
  preference across launches, and choose which loaded currencies are enabled.
- **Live exchange rates** — fetched on startup from the free, keyless
  [Frankfurter API](https://www.frankfurter.dev/) (ECB reference rates). Falls
  back to built-in mock rates when offline.
- **Persistence** — tally entries and the selected target currency are saved to
  disk and restored on the next launch.

Supported currencies are loaded dynamically from Frankfurter on startup and can
be enabled or hidden in Settings. If that request fails, the app falls back to
its last cached currency list or the original built-in set: CNY, USD, GBP, EUR,
AUD, CAD, JPY, SGD.

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) — or plain `pip`

## Setup & Run (with uv)

```bash
uv sync          # create the venv and install dependencies
uv run python main.py
```

## Setup & Run (with plain pip)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install customtkinter requests
python main.py
```

## How live rates work

On startup the app immediately requests the latest USD-based rates for the
currently enabled currencies, while also fetching Frankfurter's supported
currency list in the background. When the full list arrives, the app refreshes
the currency selectors and requests rates again for the enabled subset. Direct,
inverse, and cross rates are derived so any loaded currency pair resolves
instantly. The status bar shows the source and the rate date.

Note: Frankfurter sources ECB reference rates, which are published once per
business day and **not on weekends or ECB holidays**. So on a Monday the latest
available rates may still be dated the previous Friday — this is expected, not a
bug. See the C++ project's
[api-notes.md](https://github.com/Danny731/Multifunctional-Currency-Converter/blob/codex-course-project-updates/docs/api-notes.md)
for the full schedule.

## Where data is stored

Tally data is saved as JSON in a per-user application-data directory, kept
**separate** from the C++ version:

- **Windows:** `%LOCALAPPDATA%\FloatingO\CurrencyConverterPy\tallybook.json`
- **macOS:** `~/Library/Application Support/FloatingO/CurrencyConverterPy/tallybook.json`
- **Linux:** `~/.local/share/FloatingO/CurrencyConverterPy/tallybook.json`

Cached rates, supported currencies, and settings live in the same directory as
`rates.json`, `currencies.json`, and `settings.json`.

## Project structure

```
.
├── main.py                 # entry point
├── pyproject.toml          # uv/PEP 621 project + dependencies
├── core/                   # domain logic (no UI dependencies)
│   ├── conversion_history.py
│   ├── currency.py         # Currency value object + dynamic list helpers
│   ├── converter.py        # rate storage + conversion
│   ├── tally.py            # TallyEntry + TallyBook
│   └── rate_service.py     # threaded Frankfurter fetch
├── storage/
│   ├── currency_storage.py # cached supported currency list
│   ├── rate_storage.py     # cached exchange rates
│   ├── settings.py         # persisted UI preferences
│   └── tally_storage.py    # JSON load/save
└── ui/
    ├── converter_page.py   # converter tab
    ├── history_page.py     # historical trend chart tab
    ├── settings_page.py    # preferences tab
    ├── tally_page.py       # tally book tab
    └── main_window.py      # window, tabs, rate orchestration
```

## License

Personal project. See the upstream repository for context.
