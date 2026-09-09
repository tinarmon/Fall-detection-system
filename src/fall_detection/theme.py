"""Design system tokens, typography definitions, and TTK theme configuration."""

from __future__ import annotations

import tkinter.font as tkfont
from tkinter import ttk

# Surface & neutral colors
BG_DARK = "#0d1117"
BG_ALT = "#161b22"
SURFACE_CARD = "#161b22"
SURFACE_ELEVATED = "#21262d"
SURFACE_HOVER = "#30363d"
BORDER_SUBTLE = "#30363d"
BORDER_FOCUS = "#58a6ff"

# Brand colors
PRIMARY = "#00d2ff"
PRIMARY_HOVER = "#33dcff"
PRIMARY_ACTIVE = "#00b4db"
PRIMARY_FG = "#0d1117"

# Action colors
SECONDARY_BG = "#21262d"
SECONDARY_HOVER = "#30363d"
SECONDARY_ACTIVE = "#161b22"
SECONDARY_FG = "#f0f6fc"

# Status colors
SUCCESS = "#3fb950"
SUCCESS_BG = "#13231b"
WARNING = "#d29922"
WARNING_BG = "#2a1e0b"
DANGER = "#f85149"
DANGER_HOVER = "#da3633"
DANGER_ACTIVE = "#b62324"
DANGER_BG = "#2c1517"
DANGER_FG = "#ffffff"

# Typography colors
TEXT_PRIMARY = "#f0f6fc"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#6e7681"
TEXT_DISABLED = "#484f58"

# Overlays
OVERLAY_BG = "#040406"
GRID_LINE = "#22272e"

# Spacing
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32


class AppFonts:
    """Font token registry initialized on demand with fallback."""

    _instance: AppFonts | None = None

    @classmethod
    def get(cls, root=None) -> AppFonts:
        if cls._instance is None:
            cls._instance = cls(root)
        return cls._instance

    def __init__(self, root=None):
        font_family = "Segoe UI"
        mono_family = "Consolas"

        self.H1 = tkfont.Font(family=font_family, size=16, weight="bold")
        self.H2 = tkfont.Font(family=font_family, size=13, weight="bold")
        self.H3 = tkfont.Font(family=font_family, size=11, weight="bold")
        self.BODY = tkfont.Font(family=font_family, size=10, weight="normal")
        self.BODY_BOLD = tkfont.Font(family=font_family, size=10, weight="bold")
        self.CAPTION = tkfont.Font(family=font_family, size=9, weight="normal")
        self.CAPTION_BOLD = tkfont.Font(family=font_family, size=9, weight="bold")
        self.MONO = tkfont.Font(family=mono_family, size=10, weight="normal")
        self.MONO_BOLD = tkfont.Font(family=mono_family, size=10, weight="bold")
        self.MONO_LARGE = tkfont.Font(family=mono_family, size=13, weight="bold")


def apply_ttk_theme(root) -> None:
    """Applies high-contrast dark theme tokens to global TTK styles."""
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(
        "TFrame",
        background=BG_DARK,
    )
    style.configure(
        "Card.TFrame",
        background=SURFACE_CARD,
        relief="flat",
    )
    style.configure(
        "TLabel",
        background=BG_DARK,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 10),
    )
    style.configure(
        "Muted.TLabel",
        background=BG_DARK,
        foreground=TEXT_MUTED,
        font=("Segoe UI", 9),
    )
    style.configure(
        "TEntry",
        fieldbackground=SURFACE_ELEVATED,
        foreground=TEXT_PRIMARY,
        insertcolor=TEXT_PRIMARY,
        bordercolor=BORDER_SUBTLE,
        lightcolor=BORDER_SUBTLE,
        darkcolor=BORDER_SUBTLE,
        padding=6,
    )
    style.map(
        "TEntry",
        bordercolor=[("focus", BORDER_FOCUS)],
        lightcolor=[("focus", BORDER_FOCUS)],
    )
    style.configure(
        "TCombobox",
        fieldbackground=SURFACE_ELEVATED,
        background=SURFACE_ELEVATED,
        foreground=TEXT_PRIMARY,
        arrowcolor=TEXT_SECONDARY,
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", SURFACE_ELEVATED)],
        selectbackground=[("readonly", SURFACE_HOVER)],
        selectforeground=[("readonly", TEXT_PRIMARY)],
    )
