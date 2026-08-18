import os
import sys
import time
import shutil
import tempfile
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

class UninstallApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - Uninstall Wizard")
        self.geometry("450x220")
        self.configure(bg="#0c0c0e")
        self.resizable(False, False)
        
        # Get path of uninstall.exe
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
        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", bg="#0c0c0e", foreground="#f0f0f5", fieldbackground="#16161e")
        style.configure("TFrame", background="#0c0c0e")
        
        # Title Label
        title_lbl = tk.Label(
            self, text="ถอนการติดตั้ง Pre-Fall Detection 3D", 
            font=("Segoe UI", 13, "bold"), bg="#0c0c0e", fg="#ff0055"
        )
        title_lbl.pack(pady=(25, 5))
        
        desc_text = (
            f"ระบบจะทำการลบไฟล์ทั้งหมดในโฟลเดอร์ติดตั้ง:\n"
            f"{self.install_dir}\n"
            f"และนำปุ่มลัด Shortcut DPDF บนเดสก์ท็อปออก"
        )
        desc_lbl = tk.Label(
            self, text=desc_text, font=("Segoe UI", 9), 
            bg="#0c0c0e", fg="#8a8a98", justify="center"
        )
        desc_lbl.pack(pady=10)
        
        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", side="bottom", pady=25)
        
        btn_cancel = tk.Button(
            btn_frame, text="ยกเลิก", font=("Segoe UI", 9, "bold"), 
            bg="#1e1e24", fg="#f0f0f5", activebackground="#2a2a35", activeforeground="#ffffff",
            bd=0, padx=25, pady=8, command=self.destroy
        )
        btn_cancel.pack(side="right", padx=(10, 40))
        
        btn_uninstall = tk.Button(
            btn_frame, text="เริ่มถอนการติดตั้ง", font=("Segoe UI", 9, "bold"), 
            bg="#ff0055", fg="#ffffff", activebackground="#e0004c", activeforeground="#ffffff",
            bd=0, padx=20, pady=8, command=self.do_uninstall
        )
        btn_uninstall.pack(side="right")

    def do_uninstall(self):
        confirm = messagebox.askyesno(
            "Confirm Uninstall", 
            "คุณแน่ใจหรือไม่ว่าต้องการถอนการติดตั้งโปรแกรม DPDF 3D ออกจากเครื่องคอมพิวเตอร์ของคุณ?"
        )
        if not confirm:
            return
            
        try:
            # 1. Delete desktop shortcut
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop, "DPDF.lnk")
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                
            # 2. Write self-deleting cleanup batch file in Temp directory
            temp_dir = tempfile.gettempdir()
            bat_path = os.path.join(temp_dir, "dpdf_cleanup.bat")
            
            # Escape paths for cmd
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
            messagebox.showinfo("Uninstall Complete", "ถอนการติดตั้งโปรแกรม DPDF 3D เสร็จสิ้นแล้ว!")
            self.destroy()
            
        except Exception as e:
            messagebox.showerror("Uninstall Error", f"การถอนการติดตั้งเกิดความล้มเหลว: {e}")

if __name__ == "__main__":
    app = UninstallApp()
    app.mainloop()
