"""Backwards-compatibility entry point for model training delegating to scripts/train.py."""

from __future__ import annotations

from scripts.train import main

if __name__ == "__main__":
    main()
