"""
DPDF 3D System Uninstall Wizard
Refactored and styled according to UXUI_Design_Principles.md
"""

import os
import sys
import tempfile
import subprocess
import tkinter as tk
from tkinter import messagebox

import theme
from ui_components import (
    AppFonts,
    DangerButton,
    SecondaryButton,
    CardFrame
)


class UninstallApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - Uninstall Wizard")
        self.geometry("480x280")
        self.minsize(420, 240)
        self.configure(bg=theme.BG_DARK)
        self.resizable(False, False)
        
        # Initialize fonts & theme
        self.fonts = AppFonts.get(self)
        theme.apply_ttk_theme(self)
        
        # Determine paths
        if getattr(sys, 'frozen', False):
            self.base_path = sys._MEIPASS
            self.install_dir = os.path.dirname(sys.executable)
        else:
            self.base_path = os.path.dirname(os.path.abspath(__file__))
            self.install_dir = self.base_path
            
        # Load window icon
        icon_path = os.path.join(self.base_path, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
                
        self.setup_ui()

    def setup_ui(self):
        # Header Banner
        header = tk.Frame(self, bg=theme.SURFACE_CARD, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        header.pack(fill="x", side="top")
        
        lbl_title = tk.Label(
            header, text="⚠️ ถอนการติดตั้ง PRE-FALL DETECTION 3D", 
            font=self.fonts.H3, bg=theme.SURFACE_CARD, fg=theme.DANGER
        )
        lbl_title.pack(anchor="w")
        
        lbl_subtitle = tk.Label(
            header, text="ระบบช่วยนำไฟล์โปรแกรมและปุ่มลัดออกจากเครื่องคอมพิวเตอร์ของคุณ", 
            font=self.fonts.CAPTION, bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_subtitle.pack(anchor="w", pady=(theme.SPACE_XS, 0))
        
        # Main body container
        body = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        body.pack(fill="both", expand=True)
        
        # Target Path Card
        card = CardFrame(body)
        card.pack(fill="x", pady=(0, theme.SPACE_MD))
        
        lbl_info = tk.Label(
            card, text="โปรแกรมจะทำการลบไฟล์ทั้งหมดในโฟลเดอร์ติดตั้ง:", 
            font=self.fonts.BODY, bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_info.pack(anchor="w")
        
        lbl_path = tk.Label(
            card, text=self.install_dir, 
            font=self.fonts.MONO, bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_SECONDARY,
            padx=theme.SPACE_SM, pady=theme.SPACE_XS
        )
        lbl_path.pack(fill="x", anchor="w", pady=(theme.SPACE_XS, theme.SPACE_XS))
        
        lbl_note = tk.Label(
            card, text="พร้อมนำปุ่มลัด Shortcut 'DPDF' ออกจากหน้าจอเดสก์ท็อป", 
            font=self.fonts.CAPTION, bg=theme.SURFACE_CARD, fg=theme.TEXT_MUTED
        )
        lbl_note.pack(anchor="w")
        
        # Action Buttons
        btn_bar = tk.Frame(body, bg=theme.BG_DARK)
        btn_bar.pack(fill="x", side="bottom")
        
        btn_cancel = SecondaryButton(btn_bar, text="ยกเลิก (Cancel)", command=self.destroy)
        btn_cancel.pack(side="right", padx=(theme.SPACE_SM, 0))
        
        btn_uninstall = DangerButton(
            btn_bar, text="🗑️ ยืนยันถอนการติดตั้ง", command=self.do_uninstall
        )
        btn_uninstall.pack(side="right")

    def do_uninstall(self):
        confirm = messagebox.askyesno(
            "Confirm Uninstall", 
            "คุณแน่ใจหรือไม่ว่าต้องการถอนการติดตั้งโปรแกรม DPDF 3D ออกจากเครื่องคอมพิวเตอร์ของคุณ?",
            parent=self
        )
        if not confirm:
            return
            
        try:
            # 1. Delete desktop shortcut
            desktop = os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Desktop")
            shortcut_path = os.path.join(desktop, "DPDF.lnk")
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                except Exception:
                    pass
                
            # 2. Write self-deleting cleanup batch file in Temp directory
            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, "dpdf_cleanup.bat")
            
            escaped_install_dir = self.install_dir.replace('"', '\\"')
            
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
rmdir /s /q "{escaped_install_dir}"
del "%~f0"
"""
            with open(bat_path, "w", encoding="cp874") as f:
                f.write(bat_content)
                
            # 3. Launch batch script in non-blocking mode
            subprocess.Popen([bat_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # 4. Show success and destroy self
            messagebox.showinfo("Uninstall Complete", "ถอนการติดตั้งโปรแกรม DPDF 3D เสร็จสิ้นแล้ว!", parent=self)
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Uninstall Error", f"การถอนการติดตั้งเกิดความล้มเหลว: {e}", parent=self)


if __name__ == "__main__":
    app = UninstallApp()
    app.mainloop()
