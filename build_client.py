"""Backwards-compatibility facade delegating to scripts.build_client."""

from __future__ import annotations

from scripts.build_client import build

if __name__ == "__main__":
    build()
