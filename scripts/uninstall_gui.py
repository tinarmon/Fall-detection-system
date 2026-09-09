"""System uninstallation wizard GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox

from src.fall_detection import theme
from src.fall_detection.ui.components import AppFonts, CardFrame, DangerButton, SecondaryButton


class UninstallApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - Uninstall Wizard")
        self.geometry("480x280")
        self.minsize(420, 240)
        self.configure(bg=theme.BG_DARK)
        self.resizable(False, False)

        self.fonts = AppFonts.get(self)
        theme.apply_ttk_theme(self)

        if getattr(sys, "frozen", False):
            self.base_path = sys._MEIPASS
            self.install_dir = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.install_dir = self.base_path

        icon_path = os.path.join(self.base_path, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except tk.TclError:
                pass

        self.setup_ui()

    def setup_ui(self) -> None:
        header = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        header.pack(fill="x", side="top")

        lbl_title = tk.Label(
            header,
            text="⚠️ UNINSTALL PRE-FALL DETECTION 3D",
            font=self.fonts.H3,
            bg=theme.SURFACE_CARD,
            fg=theme.DANGER,
        )
        lbl_title.pack(anchor="w")

        body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        body.pack(fill="both", expand=True)

        card = CardFrame(body)
        card.pack(fill="both", expand=True)

        lbl_msg = tk.Label(
            card,
            text="Are you sure you want to remove DPDF 3D and all associated local files?",
            font=self.fonts.BODY,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_PRIMARY,
            wraplength=380,
            justify="left",
        )
        lbl_msg.pack(anchor="w", pady=(0, theme.SPACE_SM))

        lbl_path = tk.Label(
            card,
            text=f"Location: {self.install_dir}",
            font=self.fonts.CAPTION,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_MUTED,
            wraplength=380,
            justify="left",
        )
        lbl_path.pack(anchor="w")

        footer = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        footer.pack(fill="x", side="bottom")

        btn_cancel = SecondaryButton(footer, text="Cancel", command=self.destroy)
        btn_cancel.pack(side="left")

        btn_uninstall = DangerButton(
            footer, text="Uninstall Completely", command=self.confirm_uninstall
        )
        btn_uninstall.pack(side="right")

    def confirm_uninstall(self) -> None:
        if not messagebox.askyesno("Confirm Uninstall", "This action cannot be undone. Proceed?"):
            return

        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
        shortcut_path = os.path.join(desktop, "DPDF.lnk")
        if os.path.exists(shortcut_path):
            try:
                os.remove(shortcut_path)
            except OSError:
                pass

        bat_path = os.path.join(tempfile.gettempdir(), "dpdf_uninstaller.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(
                f"@echo off\n"
                f"timeout /t 2 /nobreak >nul\n"
                f'rmdir /s /q "{self.install_dir}"\n'
                f'del "{bat_path}"\n'
            )

        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.destroy()


def main() -> None:
    app = UninstallApp()
    app.mainloop()


if __name__ == "__main__":
    main()
