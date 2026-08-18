import os
import sys
import zipfile
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D System Setup")
        self.geometry("500x380")
        self.configure(bg="#0c0c0e")
        self.resizable(False, False)
        
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
        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", bg="#0c0c0e", foreground="#f0f0f5")
        style.configure("TProgressbar", thickness=15, background="#00f0ff")
        
        # Header Banner
        header = tk.Label(
            self, text="DPDF 3D SYSTEM SETUP WIZARD", 
            font=("Segoe UI", 14, "bold"), bg="#121216", fg="#00f0ff", pady=15
        )
        header.pack(fill="x")
        
        # Description
        desc_text = (
            "ระบบตรวจจับความเสี่ยงและพยากรณ์ก่อนการล้ม (Pre-Fall Detection 3D)\n"
            "เวอร์ชัน 2.0 Standalone Desktop Application\n\n"
            "ตัวติดตั้งนี้จะคลายพิกัดรันไทม์ Python พร้อมจำสร้าง Shortcut ปุ่มลัดบนหน้าจอหลัก"
        )
        desc = tk.Label(
            self, text=desc_text, font=("Segoe UI", 9), 
            bg="#0c0c0e", fg="#8a8a98", justify="left", pady=15
        )
        desc.pack(anchor="w", padx=25)
        
        # Path Selector Frame
        path_frame = tk.Frame(self, bg="#0c0c0e")
        path_frame.pack(fill="x", padx=25, pady=10)
        
        tk.Label(
            path_frame, text="ตำแหน่งติดตั้ง (Installation Folder):", 
            font=("Segoe UI", 9, "bold"), bg="#0c0c0e", fg="#8a8a98"
        ).pack(anchor="w")
        
        entry_frame = tk.Frame(path_frame, bg="#0c0c0e")
        entry_frame.pack(fill="x", pady=5)
        
        self.entry_path = tk.Entry(
            entry_frame, textvariable=self.install_path_var, 
            bg="#16161e", fg="#ffffff", font=("Segoe UI", 9), bd=1, insertbackground="#ffffff"
        )
        self.entry_path.pack(side="left", fill="x", expand=True, ipady=3)
        
        btn_browse = tk.Button(
            entry_frame, text="Browse...", font=("Segoe UI", 9, "bold"), 
            bg="#2a2a35", fg="#ffffff", activebackground="#3a3a48", activeforeground="#ffffff",
            bd=0, padx=12, command=self.browse_folder
        )
        btn_browse.pack(side="right", padx=(10, 0))
        
        # Progress Bar & Status (Initially hidden)
        self.progress_frame = tk.Frame(self, bg="#0c0c0e")
        self.lbl_status = tk.Label(
            self.progress_frame, text="พร้อมทำการติดตั้ง...", 
            font=("Segoe UI", 9, "bold"), bg="#0c0c0e", fg="#00f0ff"
        )
        self.lbl_status.pack(anchor="w")
        
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=5)
        
        # Action Buttons
        self.btn_install = tk.Button(
            self, text="🚀 เริ่มติดตั้งโปรแกรม (Install)", font=("Segoe UI", 10, "bold"),
            bg="#00f0ff", fg="#000000", activebackground="#00d0e0", activeforeground="#000000",
            bd=0, pady=10, command=self.start_installation
        )
        self.btn_install.pack(fill="x", side="bottom", padx=25, pady=25)

    def browse_folder(self):
        folder = filedialog.askdirectory(parent=self, initialdir=self.install_path_var.get())
        if folder:
            # Append /DPDF if the selected folder doesn't end with it
            folder = os.path.normpath(folder)
            if not folder.lower().endswith("dpdf"):
                folder = os.path.join(folder, "DPDF")
            self.install_path_var.set(folder)

    def start_installation(self):
        target_dir = self.install_path_var.get().strip()
        if not target_dir:
            messagebox.showerror("Error", "กรุณาระบุตำแหน่งติดตั้งที่ถูกต้อง")
            return
            
        if not os.path.exists(self.zip_path):
            messagebox.showerror("Error", f"ไม่พบไฟล์ติดตั้งหลัก (payload.zip) ที่ตำแหน่ง: {self.zip_path}")
            return
            
        # UI updates to show installation progress
        self.btn_install.configure(state="disabled", bg="#2e2e38", fg="#8a8a98")
        self.entry_path.configure(state="disabled")
        self.progress_frame.pack(fill="x", padx=25, side="bottom", before=self.btn_install)
        
        # Launch extraction inside background thread
        threading.Thread(target=self.install_task, args=(target_dir,), daemon=True).start()

    def install_task(self, dest_path):
        try:
            self.update_status("กำลังเตรียมการติดตั้ง...")
            os.makedirs(dest_path, exist_ok=True)
            
            # Read zip contents
            with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                total_files = len(file_list)
                
                self.update_status(f"กำลังสกัดไฟล์ติดตั้งทั้งหมด ({total_files} ไฟล์)...")
                
                for idx, file_name in enumerate(file_list):
                    zip_ref.extract(file_name, dest_path)
                    
                    # Update progress every 25 files
                    if idx % 25 == 0 or idx == total_files - 1:
                        pct = int(((idx + 1) / total_files) * 100)
                        self.update_progress(pct, f"กำลังติดตั้ง: {idx+1}/{total_files} ไฟล์")
                        
            # Create Windows Desktop Shortcut using PowerShell
            self.update_status("กำลังสร้าง Shortcut ปุ่มลัดบนหน้าจอเดสก์ท็อป...")
            target_exe = os.path.join(dest_path, "DPDF.exe")
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop, "DPDF.lnk")
            
            self.create_windows_shortcut(target_exe, shortcut_path)
            
            self.update_status("ติดตั้งเสร็จสมบูรณ์เรียบร้อยแล้ว!")
            self.after(0, lambda: messagebox.showinfo(
                "Installation Complete", 
                "การติดตั้งระบบ DPDF 3D เสร็จสมบูรณ์แล้ว!\n\n"
                "สามารถเปิดใช้งานได้ทันทีจากปุ่มลัด 'DPDF' บนเดสก์ท็อปของคุณ"
            ))
            self.after(0, self.destroy)
            
        except Exception as e:
            self.update_status(f"เกิดข้อผิดพลาดในการติดตั้ง: {e}")
            self.after(0, lambda: messagebox.showerror("Installation Failed", f"การติดตั้งล้มเหลว: {e}"))
            self.after(0, lambda: self.btn_install.configure(state="normal", bg="#00f0ff", fg="#000000"))

    def update_status(self, text):
        self.after(0, lambda: self.lbl_status.configure(text=text))

    def update_progress(self, value, text):
        self.after(0, lambda: self.progress.configure(value=value))
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
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except Exception as e:
            print(f"Error creating shortcut: {e}")

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
