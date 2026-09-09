"""Backwards-compatibility facade delegating to scripts.uninstall_gui."""

from __future__ import annotations

from scripts.uninstall_gui import main

if __name__ == "__main__":
    main()
