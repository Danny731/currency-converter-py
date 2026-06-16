# Currency Converter (Python)

A small personal desktop tool for currency conversion and a multi-currency tally
book (expense log). This is the Python port of the original
[Qt6/C++ Multifunctional-Currency-Converter](https://github.com/Danny731/Multifunctional-Currency-Converter),
rebuilt with [CustomTkinter](https://customtkinter.tomschimansky.com/) for a
modern look with minimal dependencies.

## Features

- **Currency Converter** — enter an amount in a source currency and see it
  converted into every supported currency at once.
- **Tally Book** — log expenses in mixed currencies, automatically totalled in a
  chosen target currency. Add / delete / clear entries, with optional notes.
- **Live exchange rates** — fetched on startup from the free, keyless
  [Frankfurter API](https://www.frankfurter.dev/) (ECB reference rates). Falls
  back to built-in mock rates when offline.
- **Persistence** — tally entries and the selected target currency are saved to
  disk and restored on the next launch.

Supported currencies: CNY, USD, GBP, EUR, AUD, CAD, JPY, SGD.

## Requirements

- Python 3.14+
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

On startup the app requests the latest USD-based rates from Frankfurter and
derives direct, inverse, and cross rates so any currency pair resolves
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

## Project structure

```
.
├── main.py                 # entry point
├── pyproject.toml          # uv/PEP 621 project + dependencies
├── core/                   # domain logic (no UI dependencies)
│   ├── currency.py         # Currency enum + helpers
│   ├── converter.py        # rate storage + conversion
│   ├── tally.py            # TallyEntry + TallyBook
│   └── rate_service.py     # threaded Frankfurter fetch
├── storage/
│   └── tally_storage.py    # JSON load/save
└── ui/
    ├── converter_page.py   # converter tab
    ├── tally_page.py       # tally book tab
    └── main_window.py      # window, tabs, rate orchestration
```

## License

Personal project. See the upstream repository for context.
