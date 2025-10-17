"""Package initialisation for Colonial Command sources."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the package's directory is available on sys.path so that modules such
# as ``core`` and ``systems`` can be imported both when the game is launched
# via ``python src/main.py`` and when ``src`` is imported as a package
# (e.g. by tooling like PyInstaller or during tests).
_SRC_DIR = Path(__file__).resolve().parent
_SRC_PATH = str(_SRC_DIR)
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

__all__ = [
    "_SRC_DIR",
]
