"""Shim for local runs: ``python main.py`` (prepends ``src`` when not installed)."""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
_src = _root / "src"
if _src.is_dir():
    sys.path.insert(0, str(_src))

from astchunk.cli import app

if __name__ == "__main__":
    app()
