"""
UX/UI Theme & Design Token System for DPDF Client
Compliant with UXUI_Design_Principles.md specification.
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

# ==========================================
# 🎨 COLOR PALETTE TOKENS (Constants)
# ==========================================

# Neutrals / Backgrounds / Surfaces
BG_DARK = "#0d1117"           # Master background
BG_ALT = "#161b22"            # Secondary background
SURFACE_CARD = "#161b22"      # Card / Panel background
SURFACE_ELEVATED = "#21262d"  # Raised components / Inputs
SURFACE_HOVER = "#30363d"     # Item hover state
BORDER_SUBTLE = "#30363d"     # Default borders
BORDER_FOCUS = "#58a6ff"      # Focused borders

# Brand / Primary
PRIMARY = "#00d2ff"           # Bright Cyan accent
PRIMARY_HOVER = "#33dcff"     # Hover state
PRIMARY_ACTIVE = "#00b4db"    # Pressed state
PRIMARY_FG = "#0d1117"        # Text on primary button

# Secondary Actions
SECONDARY_BG = "#21262d"      # Button neutral background
SECONDARY_HOVER = "#30363d"   # Button neutral hover
SECONDARY_ACTIVE = "#161b22"  # Button neutral pressed
SECONDARY_FG = "#f0f6fc"      # Text on secondary button

# Status & Feedback
SUCCESS = "#3fb950"           # Green - Normal / Connected
SUCCESS_BG = "#13231b"        # Subtle green background
WARNING = "#d29922"           # Yellow/Amber - Caution / Connecting
WARNING_BG = "#2a1e0b"        # Subtle amber background
DANGER = "#f85149"            # Red - Fall Detected / Destructive
DANGER_HOVER = "#da3633"      # Red hover
DANGER_ACTIVE = "#b62324"     # Red pressed
DANGER_BG = "#2c1517"         # Subtle red background
DANGER_FG = "#ffffff"         # Text on danger button

# Typography / Text Colors
TEXT_PRIMARY = "#f0f6fc"      # High contrast white
TEXT_SECONDARY = "#8b949e"    # Subtitle / Labels
TEXT_MUTED = "#6e7681"        # Placeholders / Hints / Disabled
TEXT_DISABLED = "#484f58"     # Inactive text

# Video / Canvas Overlays
OVERLAY_BG = "#040406"        # Deep black for video frames
GRID_LINE = "#22272e"         # Subtle grid lines

# ==========================================
# 📐 SPACING TOKENS (Base Unit: 4px / 8px)
# ==========================================
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 16
SPACE_LG = 24
SPACE_XL = 32

# ==========================================
# 🔤 TYPOGRAPHY SYSTEM
# ==========================================
class AppFonts:
    """Centralized font registry returning tkinter.font.Font objects."""
    _instance = None
    
    @classmethod
    def get(cls, root=None):
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


# ==========================================
# 🎛️ TTK STYLE CONFIGURATION
# ==========================================
def apply_ttk_theme(root):
    """Configures global ttk styling to match the design system tokens."""
    style = ttk.Style(root)
    style.theme_use("clam")
    
    # Global root defaults
    style.configure(".", 
        background=BG_DARK, 
        foreground=TEXT_PRIMARY, 
        fieldbackground=SURFACE_ELEVATED,
        font=("Segoe UI", 10),
        borderwidth=0
    )
    
    # Frame Styles
    style.configure("TFrame", background=BG_DARK)
    style.configure("Card.TFrame", background=SURFACE_CARD)
    style.configure("Elevated.TFrame", background=SURFACE_ELEVATED)
    
    # Label Styles
    style.configure("TLabel", background=BG_DARK, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
    style.configure("Card.TLabel", background=SURFACE_CARD, foreground=TEXT_PRIMARY)
    style.configure("Secondary.TLabel", background=BG_DARK, foreground=TEXT_SECONDARY, font=("Segoe UI", 9))
    style.configure("CardSecondary.TLabel", background=SURFACE_CARD, foreground=TEXT_SECONDARY, font=("Segoe UI", 9))
    
    # Entry Styles
    style.configure("TEntry", 
        fieldbackground=SURFACE_ELEVATED, 
        foreground=TEXT_PRIMARY, 
        insertcolor=TEXT_PRIMARY,
        padding=SPACE_SM,
        borderwidth=1,
        relief="solid"
    )
    
    # Combobox Styles
    style.configure("TCombobox", 
        background=SURFACE_ELEVATED, 
        foreground=TEXT_PRIMARY, 
        fieldbackground=SURFACE_ELEVATED, 
        darkcolor=BORDER_SUBTLE, 
        lightcolor=BORDER_SUBTLE,
        arrowcolor=PRIMARY,
        padding=SPACE_SM
    )
    style.map("TCombobox", 
        fieldbackground=[("readonly", SURFACE_ELEVATED), ("active", SURFACE_HOVER)],
        background=[("active", SURFACE_HOVER)],
        selectbackground=[("readonly", PRIMARY)],
        selectforeground=[("readonly", PRIMARY_FG)]
    )
    
    # Progressbar Styles
    style.configure("TProgressbar", 
        background=PRIMARY, 
        troughcolor=SURFACE_ELEVATED, 
        borderwidth=0, 
        thickness=12
    )
    
    # Notebook / Tabs
    style.configure("TNotebook", background=BG_DARK, borderwidth=0)
    style.configure("TNotebook.Tab", 
        background=SURFACE_CARD, 
        foreground=TEXT_SECONDARY, 
        padding=[SPACE_MD, SPACE_SM],
        font=("Segoe UI", 10, "bold")
    )
    style.map("TNotebook.Tab", 
        background=[("selected", SURFACE_ELEVATED), ("active", SURFACE_HOVER)],
        foreground=[("selected", PRIMARY), ("active", TEXT_PRIMARY)]
    )

    # Scrollbar
    style.configure("TScrollbar", 
        background=SURFACE_ELEVATED, 
        troughcolor=BG_DARK, 
        borderwidth=0, 
        arrowcolor=TEXT_SECONDARY
    )
