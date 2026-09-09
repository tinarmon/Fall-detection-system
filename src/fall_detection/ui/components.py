"""Reusable UI components implementing dark mode theme design tokens."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import TYPE_CHECKING

from src.fall_detection import theme
from src.fall_detection.config import GLOBAL_CONFIG
from src.fall_detection.theme import AppFonts

if TYPE_CHECKING:
    import numpy as np


def convert_cv2_to_tk_image(
    frame: np.ndarray | None,
    target_width: int | None = None,
    target_height: int | None = None,
) -> tk.PhotoImage | None:
    """Converts OpenCV BGR image array into a tk.PhotoImage.

    Uses PPM byte buffer or PIL ImageTk to minimize CPU overhead.
    """
    if frame is None:
        return None

    import cv2

    if frame.size == 0:
        return None

    try:
        from PIL import Image, ImageTk

        has_pil = True
    except ImportError:
        has_pil = False

    h, w = frame.shape[:2]
    if target_width and target_height and target_width > 10 and target_height > 10:
        # Scale while preserving original aspect ratio (letterboxing / pillarboxing)
        scale = min(target_width / float(w), target_height / float(h))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        if new_w != w or new_h != h:
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            h, w = new_h, new_w

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    if has_pil:
        img = Image.fromarray(rgb)
        return ImageTk.PhotoImage(image=img)

    ppm_header = f"P6 {w} {h} 255\n".encode("ascii")
    return tk.PhotoImage(data=ppm_header + rgb.tobytes(), format="PPM")


class Tooltip:
    """Hover tooltip popup for widget elements."""

    def __init__(self, widget: tk.Widget, text: str = ""):
        self.widget = widget
        self.text = text
        self.tip_window: tk.Toplevel | None = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None) -> None:
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
                tw,
                text=self.text,
                justify="left",
                background=theme.SURFACE_ELEVATED,
                foreground=theme.TEXT_PRIMARY,
                relief="solid",
                borderwidth=1,
                highlightbackground=theme.BORDER_SUBTLE,
                font=fonts.CAPTION,
                padx=theme.SPACE_SM,
                pady=theme.SPACE_XS,
            )
            label.pack(ipadx=1)
        except tk.TclError:
            pass

    def hide_tip(self, event=None) -> None:
        if self.tip_window:
            try:
                self.tip_window.destroy()
            except tk.TclError:
                pass
            self.tip_window = None


class StyledButton(tk.Button):
    """Button base class with hover/active state bindings and tokenized styles."""

    def __init__(
        self,
        master,
        text: str = "",
        command: Callable[[], None] | None = None,
        bg_color: str = theme.SECONDARY_BG,
        fg_color: str = theme.SECONDARY_FG,
        hover_bg: str = theme.SECONDARY_HOVER,
        active_bg: str = theme.SECONDARY_ACTIVE,
        font=None,
        padx: int = theme.SPACE_MD,
        pady: int = theme.SPACE_SM,
        tooltip: str = "",
        **kwargs,
    ):
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_bg = hover_bg
        self.active_bg = active_bg

        fonts = theme.AppFonts.get(master)
        btn_font = font if font else fonts.BODY_BOLD

        super().__init__(
            master,
            text=text,
            command=command,
            font=btn_font,
            bg=self.bg_color,
            fg=self.fg_color,
            activebackground=self.active_bg,
            activeforeground=self.fg_color,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=padx,
            pady=pady,
            highlightthickness=0,
            **kwargs,
        )

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

        if tooltip:
            Tooltip(self, tooltip)

    def _on_enter(self, event=None) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self.hover_bg)

    def _on_leave(self, event=None) -> None:
        if str(self["state"]) != "disabled":
            self.configure(bg=self.bg_color)

    def set_disabled(self, disabled: bool = True) -> None:
        if disabled:
            self.configure(
                state="disabled",
                bg=theme.SURFACE_ELEVATED,
                fg=theme.TEXT_DISABLED,
                cursor="arrow",
            )
        else:
            self.configure(
                state="normal",
                bg=self.bg_color,
                fg=self.fg_color,
                cursor="hand2",
            )


class PrimaryButton(StyledButton):
    def __init__(self, master, text: str = "", command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg_color=theme.PRIMARY,
            fg_color=theme.PRIMARY_FG,
            hover_bg=theme.PRIMARY_HOVER,
            active_bg=theme.PRIMARY_ACTIVE,
            **kwargs,
        )


class SecondaryButton(StyledButton):
    def __init__(self, master, text: str = "", command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg_color=theme.SECONDARY_BG,
            fg_color=theme.SECONDARY_FG,
            hover_bg=theme.SECONDARY_HOVER,
            active_bg=theme.SECONDARY_ACTIVE,
            **kwargs,
        )


class DangerButton(StyledButton):
    def __init__(self, master, text: str = "", command=None, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg_color=theme.DANGER,
            fg_color=theme.DANGER_FG,
            hover_bg=theme.DANGER_HOVER,
            active_bg=theme.DANGER_ACTIVE,
            **kwargs,
        )


class IconButton(StyledButton):
    def __init__(
        self,
        master,
        icon: str = "⚙",
        command=None,
        tooltip: str = "",
        bg_color: str = theme.SECONDARY_BG,
        fg_color: str = theme.TEXT_PRIMARY,
        hover_bg: str = theme.SECONDARY_HOVER,
        font=None,
        **kwargs,
    ):
        fonts = theme.AppFonts.get(master)
        btn_font = font if font else fonts.BODY_BOLD
        super().__init__(
            master,
            text=icon,
            command=command,
            bg_color=bg_color,
            fg_color=fg_color,
            hover_bg=hover_bg,
            active_bg=theme.SURFACE_CARD,
            font=btn_font,
            padx=theme.SPACE_SM,
            pady=theme.SPACE_XS,
            tooltip=tooltip,
            **kwargs,
        )


class CardFrame(tk.Frame):
    """Card surface frame with default border and padding."""

    def __init__(
        self,
        master,
        bg: str = theme.SURFACE_CARD,
        border_color: str = theme.BORDER_SUBTLE,
        padding: int = theme.SPACE_MD,
        **kwargs,
    ):
        super().__init__(
            master,
            bg=bg,
            bd=1,
            relief="solid",
            highlightbackground=border_color,
            highlightthickness=1,
            padx=padding,
            pady=padding,
            **kwargs,
        )


class BaseModalDialog(tk.Toplevel):
    """Base modal dialog with centered placement and escape key binding."""

    def __init__(
        self,
        parent,
        title: str = "Dialog",
        width: int = 480,
        height: int = 400,
        resizable: bool = True,
        min_width: int = 440,
        min_height: int = 320,
    ):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=theme.BG_DARK)
        self.transient(parent)
        self.grab_set()
        self.resizable(resizable, resizable)
        self.minsize(min_width, min_height)

        parent.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        cx = px + max(0, (pw - width) // 2)
        cy = py + max(0, (ph - height) // 2)
        self.geometry(f"{width}x{height}+{cx}+{cy}")

        icon_path = GLOBAL_CONFIG.assets_dir / "icon.png"
        if icon_path.is_file():
            try:
                self.iconphoto(True, tk.PhotoImage(file=str(icon_path)))
            except tk.TclError:
                pass

        self.bind("<Escape>", lambda e: self.destroy())

        self.header_frame = tk.Frame(
            self, bg=theme.SURFACE_CARD, padx=theme.SPACE_MD, pady=theme.SPACE_SM
        )
        self.header_frame.pack(fill="x", side="top")

        fonts = theme.AppFonts.get(self)
        self.lbl_title = tk.Label(
            self.header_frame,
            text=title,
            font=fonts.H3,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_PRIMARY,
        )
        self.lbl_title.pack(side="left")

        btn_close = IconButton(
            self.header_frame,
            icon="✕",
            command=self.destroy,
            bg_color=theme.SURFACE_CARD,
            fg_color=theme.TEXT_SECONDARY,
            hover_bg=theme.DANGER,
            tooltip="Close (Esc)",
        )
        btn_close.pack(side="right")

        self.body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_MD, pady=theme.SPACE_MD)
        self.body.pack(fill="both", expand=True)


class EmptyCameraSlot(tk.Frame):
    """Empty placeholder slot for adding camera channels to grid."""

    def __init__(self, master, on_add_callback: Callable[[], None] | None = None, **kwargs):
        super().__init__(
            master,
            bg=theme.SURFACE_CARD,
            bd=1,
            relief="solid",
            highlightbackground=theme.BORDER_SUBTLE,
            highlightthickness=1,
            **kwargs,
        )
        self.on_add_callback = on_add_callback
        fonts = theme.AppFonts.get(master)

        center_frame = tk.Frame(self, bg=theme.SURFACE_CARD)
        center_frame.place(relx=0.5, rely=0.5, anchor="center")

        lbl_icon = tk.Label(
            center_frame,
            text="📹",
            font=("Segoe UI Emoji", 30),
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_MUTED,
        )
        lbl_icon.pack(pady=(0, theme.SPACE_XS))

        lbl_text = tk.Label(
            center_frame,
            text="Camera Slot Available",
            font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_SECONDARY,
        )
        lbl_text.pack(pady=(0, theme.SPACE_XS))

        lbl_hint = tk.Label(
            center_frame,
            text="Connect a USB Webcam or RTSP IP Camera stream",
            font=fonts.CAPTION,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_MUTED,
        )
        lbl_hint.pack(pady=(0, theme.SPACE_MD))

        btn_add = PrimaryButton(
            center_frame,
            text="➕ Add Camera Stream",
            command=self.on_add_callback,
            padx=theme.SPACE_MD,
            pady=theme.SPACE_SM,
        )
        btn_add.pack()


class ToastBanner(tk.Frame):
    """Banner notification strip for status and danger alerts."""

    def __init__(self, master, **kwargs):
        super().__init__(master, bg=theme.BG_DARK, **kwargs)
        fonts = theme.AppFonts.get(master)

        self.lbl_text = tk.Label(
            self,
            text="",
            font=fonts.BODY_BOLD,
            bg=theme.BG_DARK,
            fg=theme.TEXT_PRIMARY,
            padx=theme.SPACE_MD,
            pady=theme.SPACE_SM,
        )
        self.lbl_text.pack(fill="x", expand=True)
        self._hide_timer = None

    def show_alert(self, text: str, alert_type: str = "danger", auto_hide_sec: float = 0.0) -> None:
        if self._hide_timer:
            self.after_cancel(self._hide_timer)
            self._hide_timer = None

        if alert_type == "danger":
            bg_col, fg_col, border_col = theme.DANGER_BG, theme.DANGER, theme.DANGER
        elif alert_type == "warning":
            bg_col, fg_col, border_col = theme.WARNING_BG, theme.WARNING, theme.WARNING
        elif alert_type == "success":
            bg_col, fg_col, border_col = theme.SUCCESS_BG, theme.SUCCESS, theme.SUCCESS
        else:
            bg_col, fg_col, border_col = theme.SURFACE_CARD, theme.TEXT_PRIMARY, theme.BORDER_SUBTLE

        self.configure(
            bg=bg_col,
            highlightbackground=border_col,
            highlightthickness=1,
            relief="solid",
        )
        self.lbl_text.configure(text=text, bg=bg_col, fg=fg_col)

        if auto_hide_sec > 0:
            self._hide_timer = self.after(int(auto_hide_sec * 1000), self.clear)

    def clear(self) -> None:
        self.configure(bg=theme.BG_DARK, highlightthickness=0)
        self.lbl_text.configure(text="", bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY)


__all__ = [
    "convert_cv2_to_tk_image",
    "Tooltip",
    "StyledButton",
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "IconButton",
    "CardFrame",
    "BaseModalDialog",
    "EmptyCameraSlot",
    "ToastBanner",
    "AppFonts",
]
