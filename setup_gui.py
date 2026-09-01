"""
DPDF 3D System Setup Wizard
Refactored and styled according to UXUI_Design_Principles.md
"""

import os
import sys
import zipfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import theme
from ui_components import (
    AppFonts,
    PrimaryButton,
    SecondaryButton,
    CardFrame
)


class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - System Setup Wizard")
        self.geometry("540x440")
        self.minsize(480, 380)
        self.configure(bg=theme.BG_DARK)
        self.resizable(False, False)
        
        # Initialize fonts & theme
        self.fonts = AppFonts.get(self)
        theme.apply_ttk_theme(self)
        
        # Determine path of payload.zip
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.zip_path = os.path.join(self.base_path, "payload.zip")
        
        # Load icon if it exists
        icon_path = os.path.join(self.base_path, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
        
        # Default Install Path
        user_profile = os.environ.get("USERPROFILE", "C:\\")
        self.default_path = os.path.join(user_profile, "AppData", "Local", "Programs", "DPDF")
        self.install_path_var = tk.StringVar(value=self.default_path)
        
        self.setup_ui()

    def setup_ui(self):
        # Header Banner
        header = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(
            header, text="🛡️ DPDF 3D SYSTEM SETUP WIZARD", 
            font=self.fonts.H2, bg=theme.SURFACE_CARD, fg=theme.PRIMARY
        )
        lbl_title.pack(anchor="w")
        
        lbl_subtitle = tk.Label(
            header, text="โปรแกรมติดตั้งระบบตรวจจับและแจ้งเตือนก่อนการล้ม (Pre-Fall Detection 3D v2.0)", 
            font=self.fonts.CAPTION, bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_subtitle.pack(anchor="w", pady=(theme.SPACE_XS, 0))
        
        # Main body container
        body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        body.pack(fill="both", expand=True)
        
        # Description Card
        desc_card = CardFrame(body)
        desc_card.pack(fill="x", pady=(0, theme.SPACE_MD))
        
        desc_text = (
            "ตัวติดตั้งนี้จะทำการคัดลอกไฟล์ระบบรันไทม์ AI Model, ชุดคำนวณ 3D Pose Landmarker,\n"
            "และสร้าง Shortcut ปุ่มลัดสำหรับเปิดใช้งานทันทีบนหน้าจอหลัก (Desktop)"
        )
        lbl_desc = tk.Label(
            desc_card, text=desc_text, font=self.fonts.BODY, 
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY, justify="left"
        )
        lbl_desc.pack(anchor="w")
        
        # Installation Path Card
        path_card = CardFrame(body)
        path_card.pack(fill="x", pady=(0, theme.SPACE_MD))
        
        lbl_path_title = tk.Label(
            path_card, text="ตำแหน่งติดตั้งโปรแกรม (Installation Folder):", 
            font=self.fonts.BODY_BOLD, bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_path_title.pack(anchor="w", pady=(0, theme.SPACE_SM))
        
        entry_row = tk.Frame(path_card, bg=theme.SURFACE_CARD)
        entry_row.pack(fill="x")
        
        self.entry_path = tk.Entry(
            entry_row, textvariable=self.install_path_var, font=self.fonts.BODY,
            bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY, insertbackground=theme.TEXT_PRIMARY,
            bd=1, relief="solid", highlightthickness=0
        )
        self.entry_path.pack(side="left", fill="x", expand=True, ipady=4)
        
        btn_browse = SecondaryButton(
            entry_row, text="Browse...", command=self.browse_folder,
            padx=theme.SPACE_MD, pady=theme.SPACE_XS
        )
        btn_browse.pack(side="right", padx=(theme.SPACE_SM, 0))
        
        # Progress Card (Initially Hidden)
        self.progress_card = CardFrame(body)
        
        self.lbl_status = tk.Label(
            self.progress_card, text="พร้อมเริ่มการติดตั้ง...", 
            font=self.fonts.BODY_BOLD, bg=theme.SURFACE_CARD, fg=theme.PRIMARY
        )
        self.lbl_status.pack(anchor="w", pady=(0, theme.SPACE_XS))
        
        self.progress = ttk.Progressbar(self.progress_card, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(0, theme.SPACE_XS))
        
        self.lbl_pct = tk.Label(
            self.progress_card, text="0%", font=self.fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        self.lbl_pct.pack(anchor="e")
        
        # Action Buttons
        btn_bar = tk.Frame(body, bg=theme.BG_DARK)
        btn_bar.pack(fill="x", side="bottom")
        
        self.btn_install = PrimaryButton(
            btn_bar, text="🚀 เริ่มติดตั้งโปรแกรม (Install)", command=self.start_installation,
            pady=theme.SPACE_SM
        )
        self.btn_install.pack(fill="x")

    def browse_folder(self):
        folder = filedialog.askdirectory(parent=self, initialdir=self.install_path_var.get())
        if folder:
            folder = os.path.normpath(folder)
            if not folder.lower().endswith("dpdf"):
                folder = os.path.join(folder, "DPDF")
            self.install_path_var.set(folder)

    def start_installation(self):
        target_dir = self.install_path_var.get().strip()
        if not target_dir:
            messagebox.showerror("Error", "กรุณาระบุตำแหน่งติดตั้งที่ถูกต้อง", parent=self)
            return
            
        if not os.path.exists(self.zip_path):
            messagebox.showerror("Error", f"ไม่พบไฟล์ติดตั้งหลัก (payload.zip) ที่ตำแหน่ง: {self.zip_path}", parent=self)
            return
            
        self.btn_install.set_disabled(True)
        self.entry_path.configure(state="disabled", bg=theme.SURFACE_CARD)
        self.progress_card.pack(fill="x", pady=(0, theme.SPACE_MD), before=self.btn_install.master)
        
        threading.Thread(target=self.install_task, args=(target_dir,), daemon=True).start()

    def install_task(self, dest_path):
        try:
            self.update_status("กำลังเตรียมโครงสร้างโฟลเดอร์...")
            os.makedirs(dest_path, exist_ok=True)
            
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                self.update_status(f"กำลังติดตั้งไฟล์ระบบ ({total_files} รายการ)...")
                
                for idx, file_name in enumerate(file_list):
                    zip_ref.extract(file_name, dest_path)
                    
                    if idx % 20 == 0 or idx == total_files - 1:
                        pct = int(((idx + 1) / total_files) * 100)
                        self.update_progress(pct, f"กำลังติดตั้ง: {idx+1}/{total_files} ไฟล์ ({pct}%)")
                        
            self.update_status("กำลังสร้างปุ่มลัด Shortcut บน Desktop...")
            target_exe = os.path.join(dest_path, "DPDF.exe")
            desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
            shortcut_path = os.path.join(desktop, "DPDF.lnk")
            
            self.create_windows_shortcut(target_exe, shortcut_path)
            
            self.update_progress(100, "การติดตั้งเสร็จสมบูรณ์เรียบร้อยแล้ว!")
            self.after(0, lambda: messagebox.showinfo(
                "Installation Complete", 
                "การติดตั้งระบบ DPDF 3D เสร็จสมบูรณ์แล้ว!\n\n"
                "สามารถเปิดใช้งานได้ทันทีจากปุ่มลัด 'DPDF' บนเดสก์ท็อปของคุณ",
                parent=self
            ))
            self.after(500, self.destroy)
            
        except Exception as e:
            self.update_status(f"เกิดข้อผิดพลาดในการติดตั้ง: {e}")
            self.after(0, lambda: messagebox.showerror("Installation Failed", f"การติดตั้งล้มเหลว: {e}", parent=self))
            self.after(0, lambda: self.btn_install.set_disabled(False))

    def update_status(self, text):
        self.after(0, lambda: self.lbl_status.configure(text=text))

    def update_progress(self, value, text):
        self.after(0, lambda: self.progress.configure(value=value))
        self.after(0, lambda: self.lbl_pct.configure(text=f"{value}%"))
        self.after(0, lambda: self.lbl_status.configure(text=text))

    def create_windows_shortcut(self, target_exe, shortcut_path):
        ps_cmd = (
            f'$WshShell = New-Object -ComObject WScript.Shell; '
            f'$Shortcut = $WshShell.CreateShortcut("{shortcut_path}"); '
            f'$Shortcut.TargetPath = "{target_exe}"; '
            f'$Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"; '
            f'$Shortcut.IconLocation = "{target_exe},0"; '
            f'$Shortcut.Save()'
        )
        try:
            subprocess.run(
                ["powershell", "-Command", ps_cmd], 
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"Error creating shortcut: {e}")


if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
