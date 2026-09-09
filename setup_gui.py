"""Backwards-compatibility facade delegating to scripts.setup_gui."""

from __future__ import annotations

from scripts.setup_gui import main

if __name__ == "__main__":
    main()
