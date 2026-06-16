from __future__ import annotations

import os
import sys

# Distinct from the C++ app's "CurrencyConverter" directory so this Python
# version starts with its own fresh data files.
ORG_NAME = "FloatingO"
APP_NAME = "CurrencyConverterPy"


def app_data_dir() -> str:
    """Returns the per-user application data directory, creating it if needed.

    Location follows per-user OS conventions. Shared by all storage modules
    so tally data and cached rates land side by side.
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        path = os.path.join(base, ORG_NAME, APP_NAME)
    elif sys.platform == "darwin":
        path = os.path.expanduser(f"~/Library/Application Support/{ORG_NAME}/{APP_NAME}")
    else:
        path = os.path.expanduser(f"~/.local/share/{ORG_NAME}/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path
