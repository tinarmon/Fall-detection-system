"""
Reusable UI Component Library for DPDF Client
Implements buttons, cards, modal dialogs, form fields, and empty states
compliant with UXUI_Design_Principles.md.
"""

import os
import sys
import tkinter as tk
import theme
from theme import AppFonts


def convert_cv2_to_tk_image(frame, target_width=None, target_height=None):
    """
    High-performance converter from OpenCV BGR numpy array to tk.PhotoImage.
    Uses direct PPM raw byte buffer or PIL ImageTk for ultra-low CPU overhead (10-12x faster than PNG encoding).
    """
    if frame is None:
        return None
    import cv2
    import numpy as np
    try:
        from PIL import Image, ImageTk
        has_pil = True
    except ImportError:
        has_pil = False
    if frame is None or frame.size == 0:
        return None
        
    h, w = frame.shape[:2]
    if target_width and target_height and target_width > 10 and target_height > 10:
        if target_width != w or target_height != h:
            frame = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_NEAREST)
            h, w = target_height, target_width
            
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    if has_pil:
        img = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image=img)
    else:
        ppm_header = f"P6 {w} {h} 255\n".encode('ascii')
        return tk.PhotoImage(data=ppm_header + rgb.tobytes(), format='PPM')


class Tooltip:
    """Hover tooltip for any Tkinter/TTK widget."""
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 15
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
            self.tip_window = tw = tk.Toplevel(self.widget)
            tw.wm_overrideredirect(True)
            tw.wm_geometry(f"+{x}+{y}")
            
            fonts = theme.AppFonts.get(self.widget)
            label = tk.Label(
                tw, text=self.text, justify="left",
                background=theme.SURFACE_ELEVATED, foreground=theme.TEXT_PRIMARY,
                relief="solid", borderwidth=1, highlightbackground=theme.BORDER_SUBTLE,
                font=fonts.CAPTION, padx=theme.SPACE_SM, pady=theme.SPACE_XS
            )
            label.pack(ipadx=1)
        except Exception:
            pass

    def hide_tip(self, event=None):
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except Exception:
                pass
            self.tip_window = None


class StyledButton(tk.Button):
    """Base interactive button with standardized hover/active states, cursor and padding."""
    def __init__(self, master, text="", command=None, bg_color=theme.SECONDARY_BG, 
                 fg_color=theme.SECONDARY_FG, hover_bg=theme.SECONDARY_HOVER, 
                 active_bg=theme.SECONDARY_ACTIVE, font=None, padx=theme.SPACE_MD, 
                 pady=theme.SPACE_SM, tooltip="", **kwargs):
        
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_bg = hover_bg
        self.active_bg = active_bg
        
        fonts = theme.AppFonts.get(master)
        btn_font = font if font else fonts.BODY_BOLD
        
        super().__init__(
            master, text=text, command=command, font=btn_font,
            bg=self.bg_color, fg=self.fg_color,
            activebackground=self.active_bg, activeforeground=self.fg_color,
            bd=0, relief="flat", cursor="hand2", padx=padx, pady=pady,
            highlightthickness=0, **kwargs
        )
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        if tooltip:
            Tooltip(self, tooltip)

    def _on_enter(self, event=None):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.hover_bg)

    def _on_leave(self, event=None):
        if str(self["state"]) != "disabled":
            self.configure(bg=self.bg_color)

    def set_disabled(self, disabled=True):
        if disabled:
            self.configure(state="disabled", bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_DISABLED, cursor="arrow")
        else:
            self.configure(state="normal", bg=self.bg_color, fg=self.fg_color, cursor="hand2")


class PrimaryButton(StyledButton):
    """Dominant call-to-action button (Cyan)."""
    def __init__(self, master, text="", command=None, **kwargs):
        super().__init__(
            master, text=text, command=command,
            bg_color=theme.PRIMARY, fg_color=theme.PRIMARY_FG,
            hover_bg=theme.PRIMARY_HOVER, active_bg=theme.PRIMARY_ACTIVE,
            **kwargs
        )


class SecondaryButton(StyledButton):
    """Subtle secondary action button."""
    def __init__(self, master, text="", command=None, **kwargs):
        super().__init__(
            master, text=text, command=command,
            bg_color=theme.SECONDARY_BG, fg_color=theme.SECONDARY_FG,
            hover_bg=theme.SECONDARY_HOVER, active_bg=theme.SECONDARY_ACTIVE,
            **kwargs
        )


class DangerButton(StyledButton):
    """Destructive action button (Red)."""
    def __init__(self, master, text="", command=None, **kwargs):
        super().__init__(
            master, text=text, command=command,
            bg_color=theme.DANGER, fg_color=theme.DANGER_FG,
            hover_bg=theme.DANGER_HOVER, active_bg=theme.DANGER_ACTIVE,
            **kwargs
        )


class IconButton(StyledButton):
    """Compact icon button with consistent proportions and tooltip."""
    def __init__(self, master, icon="⚙", command=None, tooltip="", 
                 bg_color=theme.SECONDARY_BG, fg_color=theme.TEXT_PRIMARY, 
                 hover_bg=theme.SECONDARY_HOVER, font=None, **kwargs):
        fonts = theme.AppFonts.get(master)
        btn_font = font if font else fonts.BODY_BOLD
        super().__init__(
            master, text=icon, command=command,
            bg_color=bg_color, fg_color=fg_color,
            hover_bg=hover_bg, active_bg=theme.SURFACE_CARD,
            font=btn_font, padx=theme.SPACE_SM, pady=theme.SPACE_XS,
            tooltip=tooltip, **kwargs
        )


class CardFrame(tk.Frame):
    """Styled card container with consistent border, padding and background."""
    def __init__(self, master, bg=theme.SURFACE_CARD, border_color=theme.BORDER_SUBTLE, 
                 padding=theme.SPACE_MD, **kwargs):
        super().__init__(
            master, bg=bg, bd=1, relief="solid",
            highlightbackground=border_color, highlightthickness=1,
            padx=padding, pady=padding, **kwargs
        )


class BaseModalDialog(tk.Toplevel):
    """Standardized modal dialog wrapper with centered geometry, grab, and Esc to close."""
    def __init__(self, parent, title="Dialog", width=480, height=400, resizable=True, min_width=440, min_height=320):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.BG_DARK)
        self.transient(parent)
        self.grab_set()
        self.resizable(resizable, resizable)
        self.minsize(min_width, min_height)
        
        # Centering on parent window
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        
        cx = px + max(0, (pw - width) // 2)
        cy = py + max(0, (ph - height) // 2)
        self.geometry(f"{width}x{height}+{cx}+{cy}")
        
        # Load app icon if present
        import config
        icon_path = os.path.join(config.BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
                
        # Keyboard navigation: Esc closes dialog
        self.bind("<Escape>", lambda e: self.destroy())
        
        # Header bar
        self.header_frame = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_MD, pady=theme.SPACE_SM)
        self.header_frame.pack(fill="x", side="top")
        
        fonts = theme.AppFonts.get(self)
        self.lbl_title = tk.Label(
            self.header_frame, text=title, font=fonts.H3,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        self.lbl_title.pack(side="left")
        
        btn_close = IconButton(
            self.header_frame, icon="✕", command=self.destroy,
            bg_color=theme.SURFACE_CARD, fg_color=theme.TEXT_SECONDARY,
            hover_bg=theme.DANGER, tooltip="Close (Esc)"
        )
        btn_close.pack(side="right")
        
        # Body container
        self.body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_MD, pady=theme.SPACE_MD)
        self.body.pack(fill="both", expand=True)


class EmptyCameraSlot(tk.Frame):
    """Empty state widget for camera grid conforming to UX/UI Design Principle Section 9."""
    def __init__(self, master, on_add_callback=None, **kwargs):
        super().__init__(
            master, bg=theme.SURFACE_CARD, bd=1, relief="solid",
            highlightbackground=theme.BORDER_SUBTLE, highlightthickness=1,
            **kwargs
        )
        self.on_add_callback = on_add_callback
        fonts = theme.AppFonts.get(master)
        
        # Center contents
        center_frame = tk.Frame(self, bg=theme.SURFACE_CARD)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        lbl_icon = tk.Label(
            center_frame, text="📹", font=("Segoe UI Emoji", 30),
            bg=theme.SURFACE_CARD, fg=theme.TEXT_MUTED
        )
        lbl_icon.pack(pady=(0, theme.SPACE_XS))
        
        lbl_text = tk.Label(
            center_frame, text="Camera Slot Available", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_text.pack(pady=(0, theme.SPACE_XS))
        
        lbl_hint = tk.Label(
            center_frame, text="Connect a USB Webcam or RTSP IP Camera stream", font=fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_MUTED
        )
        lbl_hint.pack(pady=(0, theme.SPACE_MD))
        
        btn_add = PrimaryButton(
            center_frame, text="➕ Add Camera Stream", command=self.on_add_callback,
            padx=theme.SPACE_MD, pady=theme.SPACE_SM
        )
        btn_add.pack()


class ToastBanner(tk.Frame):
    """System notification banner for alerts, warnings, and success feedback."""
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=theme.BG_DARK, **kwargs)
        fonts = theme.AppFonts.get(master)
        
        self.lbl_text = tk.Label(
            self, text="", font=fonts.BODY_BOLD,
            bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY,
            padx=theme.SPACE_MD, pady=theme.SPACE_SM
        )
        self.lbl_text.pack(fill="x", expand=True)
        self._hide_timer = None

    def show_alert(self, text, alert_type="danger", auto_hide_sec=0):
        if self._hide_timer:
            self.after_cancel(self._hide_timer)
            self._hide_timer = None
            
        if alert_type == "danger":
            bg_col, fg_col = theme.DANGER, theme.DANGER_FG
        elif alert_type == "warning":
            bg_col, fg_col = theme.WARNING, "#000000"
        elif alert_type == "success":
            bg_col, fg_col = theme.SUCCESS, "#000000"
        else:
            bg_col, fg_col = theme.SURFACE_ELEVATED, theme.TEXT_PRIMARY
            
        self.configure(bg=bg_col)
        self.lbl_text.configure(text=text, bg=bg_col, fg=fg_col)
        
        if auto_hide_sec > 0:
            self._hide_timer = self.after(int(auto_hide_sec * 1000), self.clear)

    def clear(self):
        self.configure(bg=theme.BG_DARK)
        self.lbl_text.configure(text="", bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY)
