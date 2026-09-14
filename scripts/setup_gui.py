"""System setup wizard GUI."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk

from src.fall_detection import theme
from src.fall_detection.ui.components import AppFonts, CardFrame, PrimaryButton, SecondaryButton


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - System Setup Wizard v1.3.0")
        self.geometry("540x440")
        self.minsize(480, 380)
        self.configure(bg=theme.BG_DARK)
        self.resizable(False, False)

        self.fonts = AppFonts.get(self)
        theme.apply_ttk_theme(self)

        if getattr(sys, "frozen", False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        self.zip_path = os.path.join(self.base_path, "payload.zip")

        icon_path = os.path.join(self.base_path, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except tk.TclError:
                pass

        default_dir = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "DPDF")
        self.target_dir_var = tk.StringVar(value=default_dir)
        self.create_desktop_shortcut_var = tk.BooleanVar(value=True)

        self.setup_ui()

    def setup_ui(self) -> None:
        header = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        header.pack(fill="x", side="top")

        lbl_title = tk.Label(
            header,
            text="⚙️ DPDF 3D SYSTEM SETUP WIZARD",
            font=self.fonts.H3,
            bg=theme.SURFACE_CARD,
            fg=theme.PRIMARY,
        )
        lbl_title.pack(anchor="w")

        lbl_subtitle = tk.Label(
            header,
            text="Install Pre-Fall Detection 3D Client on this workstation",
            font=self.fonts.CAPTION,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_SECONDARY,
        )
        lbl_subtitle.pack(anchor="w")

        body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        body.pack(fill="both", expand=True)

        card = CardFrame(body)
        card.pack(fill="x", pady=(0, theme.SPACE_MD))

        lbl_dest = tk.Label(
            card,
            text="Destination Installation Folder:",
            font=self.fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_PRIMARY,
        )
        lbl_dest.pack(anchor="w", pady=(0, theme.SPACE_SM))

        dest_row = tk.Frame(card, bg=theme.SURFACE_CARD)
        dest_row.pack(fill="x", pady=(0, theme.SPACE_SM))

        entry_dest = ttk.Entry(dest_row, textvariable=self.target_dir_var, font=self.fonts.BODY)
        entry_dest.pack(side="left", fill="x", expand=True, padx=(0, theme.SPACE_SM))

        btn_browse = SecondaryButton(
            dest_row, text="Browse...", command=self.browse_folder, padx=theme.SPACE_SM
        )
        btn_browse.pack(side="right")

        chk_shortcut = tk.Checkbutton(
            card,
            text="Create Desktop Shortcut",
            variable=self.create_desktop_shortcut_var,
            font=self.fonts.BODY,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_PRIMARY,
            selectcolor=theme.SURFACE_ELEVATED,
            activebackground=theme.SURFACE_CARD,
            activeforeground=theme.TEXT_PRIMARY,
            bd=0,
        )
        chk_shortcut.pack(anchor="w", pady=(theme.SPACE_XS, 0))

        prog_card = CardFrame(body)
        prog_card.pack(fill="x")

        self.lbl_status = tk.Label(
            prog_card,
            text="Ready to install",
            font=self.fonts.CAPTION_BOLD,
            bg=theme.SURFACE_CARD,
            fg=theme.TEXT_SECONDARY,
        )
        self.lbl_status.pack(anchor="w", pady=(0, theme.SPACE_XS))

        self.progress_bar = ttk.Progressbar(prog_card, mode="determinate")
        self.progress_bar.pack(fill="x")

        footer = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        footer.pack(fill="x", side="bottom")

        btn_cancel = SecondaryButton(footer, text="Cancel", command=self.destroy)
        btn_cancel.pack(side="left")

        self.btn_install = PrimaryButton(footer, text="Install Now 🚀", command=self.start_install)
        self.btn_install.pack(side="right")

    def browse_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.target_dir_var.get())
        if selected:
            self.target_dir_var.set(selected)

    def start_install(self) -> None:
        self.btn_install.set_disabled(True)
        threading.Thread(target=self._install_worker, daemon=True).start()

    def _install_worker(self) -> None:
        dest_dir = self.target_dir_var.get().strip()
        try:
            os.makedirs(dest_dir, exist_ok=True)
            self.lbl_status.config(text="Extracting application files...", fg=theme.PRIMARY)

            if os.path.exists(self.zip_path):
                with zipfile.ZipFile(self.zip_path, "r") as zipf:
                    members = zipf.infolist()
                    total = len(members)
                    for i, member in enumerate(members):
                        zipf.extract(member, dest_dir)
                        pct = int((i + 1) / total * 100)
                        self.progress_bar["value"] = pct
                        self.lbl_status.config(text=f"Extracting: {member.filename[:40]}...")

            if self.create_desktop_shortcut_var.get():
                self._create_shortcut(dest_dir)

            self.lbl_status.config(text="Installation completed successfully!", fg=theme.SUCCESS)
            messagebox.showinfo("Setup Complete", "DPDF 3D has been installed successfully.")
            self.destroy()
        except OSError as ex:
            self.lbl_status.config(text=f"Installation failed: {ex}", fg=theme.DANGER)
            messagebox.showerror("Error", f"Failed to install: {ex}")
            self.btn_install.set_disabled(False)

    def _create_shortcut(self, target_folder: str) -> None:
        exe_path = os.path.join(target_folder, "DPDF.exe")
        desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
        shortcut_path = os.path.join(desktop, "DPDF.lnk")
        ps_cmd = (
            f"$WshShell = New-Object -comObject WScript.Shell; "
            f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
            f'$Shortcut.TargetPath = "{exe_path}"; '
            f'$Shortcut.WorkingDirectory = "{target_folder}"; '
            f"$Shortcut.Save()"
        )
        try:
            subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, check=False)
        except OSError:
            pass


def main() -> None:
    app = InstallerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
