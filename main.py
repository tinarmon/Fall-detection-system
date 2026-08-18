import os
import sys

# Catch and mock matplotlib if missing to prevent MediaPipe drawing_utils static import crash
try:
    import matplotlib
except ImportError:
    from types import ModuleType
    class DummyModule(ModuleType):
        def __getattr__(self, name):
            return DummyModule(name)
        def __call__(self, *args, **kwargs):
            return None
    sys.modules['matplotlib'] = DummyModule('matplotlib')
    sys.modules['matplotlib.pyplot'] = DummyModule('matplotlib.pyplot')

import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from collections import deque
import cv2
import numpy as np
import tensorflow as tf

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from core.pose_estimator import PoseEstimator
from core.angle_calculator import AngleCalculator
from core.ui_manager import UIManager

# Reconfigure stdout/stderr to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

from core.camera_monitor import CameraMonitor, send_line_notify_async

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - Pre-Fall Detection Dashboard")
        self.geometry("1200x800")
        self.configure(bg="#0c0c0e")
        
        # Load window icon
        icon_path = os.path.join(config.BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
                
        self.global_line_token = ""
        self.last_line_notify_time = {}
        self.fall_threshold = 0.6
        self.line_cooldown = 60
        self.audio_alert_enabled = True
        self.last_audio_alert_time = 0.0
        
        # Load config
        self.config_path = os.path.join(config.BASE_DIR, "client_config.json")
        self.camera_configs = self.load_camera_config()
        # Initialize camera monitor
        self.monitor = CameraMonitor(self)
        self.active_streams = self.monitor.active_streams
        self.available_cameras = CameraMonitor.detect_available_cameras()
        
        self.setup_ui_styles()
        self.create_layout()
        self.auto_start_streams()
        
        # Periodical GUI frame update loop
        self.update_gui_loop()

    def setup_ui_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", bg="#0c0c0e", foreground="#f0f0f5", fieldbackground="#16161e")
        style.configure("TFrame", background="#0c0c0e")
        style.configure("Action.TButton", font=("Segoe UI", 9, "bold"), background="#00f0ff", foreground="#000000", borderwidth=0, padding=10)
        style.map("Action.TButton", background=[("active", "#00d0e0")])

    def create_layout(self):
        # Master workspace container
        self.workspace = ttk.Frame(self)
        self.workspace.pack(fill="both", expand=True, padx=25, pady=25)
        
        # Header frame containing title and help button
        header_frame = ttk.Frame(self.workspace)
        header_frame.pack(fill="x", pady=(0, 20))
        
        header = tk.Label(header_frame, text="Pre-Fall Detection 3D Monitoring Grid", font=("Segoe UI", 16, "bold"), bg="#0c0c0e", fg="#f0f0f5")
        header.pack(side="left")
        
        btn_help = tk.Button(
            header_frame, text="❔ วิธีใช้งานโปรแกรม", font=("Segoe UI", 9, "bold"), 
            bg="#1e1e24", fg="#00f0ff", activebackground="#2a2a35", activeforeground="#00f0ff", 
            bd=0, padx=12, pady=5, command=self.show_main_help
        )
        btn_help.pack(side="right")
        
        btn_settings = tk.Button(
            header_frame, text="⚙️ ตั้งค่าระบบ", font=("Segoe UI", 9, "bold"), 
            bg="#1e1e24", fg="#f0f0f5", activebackground="#2a2a35", activeforeground="#ffffff", 
            bd=0, padx=12, pady=5, command=self.open_global_settings
        )
        btn_settings.pack(side="right", padx=(0, 10))
        
        # Grid container
        self.grid_container = ttk.Frame(self.workspace)
        self.grid_container.pack(fill="both", expand=True)
        
        # Global LINE Notify Token frame
        line_frame = ttk.Frame(self.workspace)
        line_frame.pack(fill="x", side="bottom", pady=(10, 5))
        
        lbl_line = tk.Label(line_frame, text="LINE Notify Token หลัก:", font=("Segoe UI", 9, "bold"), bg="#0c0c0e", fg="#8a8a98")
        lbl_line.pack(side="left", padx=(0, 10))
        
        self.ent_global_token = tk.Entry(line_frame, bg="#16161e", fg="#ffffff", insertbackground="#ffffff", font=("Segoe UI", 9), bd=1)
        self.ent_global_token.insert(0, self.global_line_token)
        self.ent_global_token.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_token_help = tk.Button(
            line_frame, text="❔", font=("Segoe UI", 9, "bold"), 
            bg="#1e1e24", fg="#00f0ff", activebackground="#2a2a35", activeforeground="#00f0ff", 
            bd=0, padx=8, pady=2, command=self.show_line_token_help
        )
        btn_token_help.pack(side="left", padx=2)
        
        btn_test_notify = tk.Button(
            line_frame, text="🧪 ทดสอบส่ง", font=("Segoe UI", 9, "bold"), 
            bg="#1e1e24", fg="#f0f0f5", activebackground="#2a2a35", activeforeground="#ffffff", 
            bd=0, padx=10, pady=2, command=self.test_global_line_notify
        )
        btn_test_notify.pack(side="left", padx=2)
        
        btn_save_token = tk.Button(
            line_frame, text="💾 บันทึก Token", font=("Segoe UI", 9, "bold"), 
            bg="#00f0ff", fg="#000000", activebackground="#00d0e0", activeforeground="#000000", 
            bd=0, padx=12, pady=2, command=self.save_global_token
        )
        btn_save_token.pack(side="left", padx=(10, 0))
        
        # Alert Banner
        self.alert_banner = tk.Label(self.workspace, text="", font=("Segoe UI", 12, "bold"), bg="#0c0c0e", fg="#ff0055", pady=10)
        self.alert_banner.pack(fill="x", side="bottom", pady=(5, 0))
        
        self.rebuild_grid_view()

    def open_global_settings(self):
        modal = tk.Toplevel(self)
        modal.title("Global System Settings")
        modal.geometry("380x320")
        modal.configure(bg="#0c0c0e")
        modal.transient(self)
        modal.grab_set()
        modal.resizable(False, False)
        
        # Load window icon for settings dialog
        icon_path = os.path.join(config.BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                modal.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
                
        # 1. Fall Threshold (Sensitivity Slider)
        tk.Label(modal, text="AI Fall Detection Threshold (0.1 - 0.9):", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(20, 2))
        
        threshold_frame = ttk.Frame(modal)
        threshold_frame.pack(fill="x", padx=20, pady=2)
        
        self.lbl_threshold_val = tk.Label(threshold_frame, text=f"{self.fall_threshold:.2f}", font=("Segoe UI", 9, "bold"), bg="#0c0c0e", fg="#00f0ff", width=6)
        self.lbl_threshold_val.pack(side="right")
        
        def on_slider_move(val):
            self.lbl_threshold_val.configure(text=f"{float(val):.2f}")
            
        slider = tk.Scale(
            threshold_frame, from_=0.1, to=0.9, resolution=0.05, orient="horizontal", 
            bg="#0c0c0e", fg="#ffffff", highlightthickness=0, activebackground="#00f0ff", 
            command=on_slider_move
        )
        slider.set(self.fall_threshold)
        slider.pack(side="left", fill="x", expand=True)
        
        # 2. LINE Cooldown Time (Spinbox)
        tk.Label(modal, text="LINE Alert Cooldown (seconds):", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        
        sp_cooldown = tk.Spinbox(modal, from_=10, to=300, increment=10, bg="#16161e", fg="#ffffff", bd=1, insertbackground="#ffffff")
        sp_cooldown.delete(0, "end")
        sp_cooldown.insert(0, str(self.line_cooldown))
        sp_cooldown.pack(fill="x", padx=20, pady=2)
        
        # 3. Audio Alarm (Checkbox)
        chk_val = tk.BooleanVar(value=self.audio_alert_enabled)
        chk_audio = tk.Checkbutton(
            modal, text="Enable Local Beep Alarm on Fall Detection", variable=chk_val, 
            bg="#0c0c0e", fg="#f0f0f5", selectcolor="#16161e", activebackground="#0c0c0e", activeforeground="#ffffff"
        )
        chk_audio.pack(anchor="w", padx=20, pady=15)
        
        # Save Settings
        def do_save():
            try:
                self.fall_threshold = float(slider.get())
                self.line_cooldown = int(sp_cooldown.get())
                self.audio_alert_enabled = bool(chk_val.get())
                self.save_camera_config()
                modal.destroy()
                messagebox.showinfo("Settings Saved", "บันทึกการตั้งค่าระบบเรียบร้อยแล้ว!")
            except Exception as ex:
                messagebox.showerror("Error", f"ข้อมูลไม่ถูกต้อง: {ex}")
                
        btn_save = tk.Button(
            modal, text="Save System Settings", font=("Segoe UI", 9, "bold"), bg="#00f0ff", fg="#000000", bd=0, pady=8,
            command=do_save
        )
        btn_save.pack(fill="x", padx=20, pady=10)

    def show_main_help(self):
        msg = (
            "วิธีใช้งานโปรแกรม Pre-Fall Detection 3D:\n\n"
            "1. เชื่อมต่อกล้อง: กดปุ่ม '+ Add Camera Stream' บนหน้าต่างกริด\n"
            "2. ตั้งค่ากล้อง: ดับเบิ้ลคลิกหรือกดปุ่มรูปฟันเฟือง (⚙) เพื่อตั้งชื่อกล้องและกรอก Source\n"
            "   - กล้อง Webcam เสียบสาย: กรอกตัวเลข '0' หรือ '1'\n"
            "   - กล้อง IP/RTSP: กรอกลิงก์เครือข่าย 'rtsp://...'\n"
            "3. ปิดกล้อง: กดปุ่ม '✕' เพื่อปิดสัญญาณภาพและนำออกจากการบันทึก\n"
            "4. การแจ้งเตือน LINE: กรอก LINE Token ของกลุ่มท่านที่ช่องด้านล่างโปรแกรม เพื่อให้บอทแจ้งเหตุการณ์ทันทีที่มีผู้ล้ม"
        )
        messagebox.showinfo("วิธีใช้งานระบบ DPDF 3D", msg)

    def show_line_token_help(self):
        msg = (
            "วิธีออกรหัส LINE Notify Token สำหรับแจ้งเตือนภัยล้ม:\n\n"
            "1. ไปที่เว็บไซต์ https://notify-bot.line.me จากบราวเซอร์\n"
            "2. ล็อกอินด้วยบัญชี LINE หลักของคุณ\n"
            "3. เข้าไปหน้าส่วนตัว (My Page) และคลิกปุ่ม 'ออก Token' (Generate Token)\n"
            "4. ระบุชื่อบอทแสดงแจ้งเตือน (เช่น DPDF Alert) และเลือกกลุ่มแชตที่คุณต้องการแชร์ข้อมูล\n"
            "5. คัดลอกรหัส Token ที่เว็บแจกให้ นำมาวางที่ช่องรหัสในโปรแกรมนี้แล้วกดบันทึก\n"
            "6. *สำคัญ* อย่าลืมกดเชิญบอทที่ชื่อว่า 'LINE Notify' เข้าร่วมกลุ่มแชตนั้นด้วยเสมอก่อนใช้งาน"
        )
        messagebox.showinfo("คู่มือการติดตั้ง LINE Notify", msg)

    def test_global_line_notify(self):
        token = self.ent_global_token.get().strip()
        if not token:
            messagebox.showerror("Error", "กรุณาระบุ LINE Token ก่อนทำการทดสอบ")
            return
            
        def test_callback(success):
            if success:
                messagebox.showinfo("LINE Notify Test", "ส่งข้อความทดสอบเข้ากลุ่มไลน์สำเร็จแล้ว!")
            else:
                messagebox.showerror("LINE Notify Test", "ส่งข้อความทดสอบล้มเหลว กรุณาตรวจสอบความถูกต้องของรหัส Token หรือสัญญาณเน็ตเวิร์ก")
                
        msg = f"\n🧪 [DPDF Alert Test]\nการทดสอบการเชื่อมต่อระบบเตือนภัยสำเร็จแล้ว!\n⏰ เวลาทดสอบ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_line_notify_async(msg, token, callback=test_callback)

    def save_global_token(self):
        self.global_line_token = self.ent_global_token.get().strip()
        self.save_camera_config()
        messagebox.showinfo("Success", "บันทึกรหัส LINE Token หลักลงระบบเรียบร้อยแล้ว!")

    def rebuild_grid_view(self):
        for widget in self.grid_container.winfo_children():
            widget.destroy()
            
        num_cameras = len(self.camera_configs)
        rows, cols = (1, 1) if num_cameras <= 1 else ((1, 2) if num_cameras == 2 else (2, 2))
        
        for r in range(rows):
            self.grid_container.rowconfigure(r, weight=1)
        for c in range(cols):
            self.grid_container.columnconfigure(c, weight=1)
            
        for i in range(4):
            r = i // cols
            c = i % cols
            
            if i < num_cameras:
                cfg = self.camera_configs[i]
                cam_name = cfg["name"]
                
                cell = tk.Frame(self.grid_container, bg="#16161e", bd=1, highlightbackground="#3c3c4b", highlightthickness=1)
                cell.grid(row=r, column=c, sticky="nsew", padx=10, pady=10)
                
                lbl = tk.Label(cell, bg="#040406")
                lbl.pack(fill="both", expand=True)
                
                # Title
                lbl_title = tk.Label(lbl, text=cam_name.upper(), font=("Segoe UI", 9, "bold"), bg="#16161e", fg="#f0f0f5", padx=8, pady=4)
                lbl_title.place(relx=0.0, rely=1.0, anchor="sw", x=15, y=-15)
                
                # Gear and Close button overlays
                overlay = tk.Frame(lbl, bg="#1c1c24")
                overlay.place(relx=1.0, rely=0.0, anchor="ne", x=-15, y=15)
                
                btn_gear = tk.Button(overlay, text="⚙", font=("Segoe UI Symbol", 10), bg="#2a2a35", fg="#a0a0b0", activebackground="#3a3a48", activeforeground="#ffffff", bd=0, padx=8, pady=2, command=lambda idx=i: self.open_camera_settings(idx))
                btn_gear.pack(side="left")
                
                btn_close = tk.Button(overlay, text="✕", font=("Segoe UI Symbol", 10), bg="#ff0055", fg="#ffffff", activebackground="#cc0044", activeforeground="#ffffff", bd=0, padx=8, pady=2, command=lambda idx=i: self.delete_camera(idx))
                btn_close.pack(side="left", padx=(1, 0))
                
                cfg["label_widget"] = lbl
            elif i == num_cameras and num_cameras < 4:
                cell = tk.Frame(self.grid_container, bg="#121216", bd=1, highlightbackground="#3c3c4b", highlightthickness=1)
                cell.grid(row=r, column=c, sticky="nsew", padx=10, pady=10)
                
                btn_add = tk.Button(cell, text="+ Add Camera Stream", font=("Segoe UI", 11, "bold"), bg="#16161e", fg="#00f0ff", activebackground="#1e1e28", activeforeground="#00f0ff", bd=0, command=self.add_camera)
                btn_add.pack(fill="both", expand=True)

    def show_camera_source_help(self):
        msg = (
            "วิธีกรอกรหัสแหล่งสัญญาณกล้อง (Camera Source):\n\n"
            "1. กล้องเว็บแคมในตัว หรือ เสียบสาย USB:\n"
            "   - ให้กรอกตัวเลขลำดับกล้อง เริ่มจาก '0' (กล้องตัวแรก), '1' (กล้องตัวที่สอง), เป็นต้น\n\n"
            "2. กล้องเน็ตเวิร์ก IP Camera หรือกล้องวงจรปิดผ่านเน็ต:\n"
            "   - ให้กรอกลิงก์สตรีม RTSP ของกล้องให้ครบถ้วน\n"
            "   - ตัวอย่างรูปแบบ: rtsp://username:password@ip_address:port/stream_path"
        )
        messagebox.showinfo("คู่มือแหล่งสัญญาณกล้อง", msg)

    def test_camera_line_notify(self, token, cam_name):
        if not token:
            messagebox.showerror("Error", "กรุณาระบุ LINE Token เฉพาะกล้องก่อนทำการทดสอบ")
            return
            
        def test_callback(success):
            if success:
                messagebox.showinfo("LINE Notify Test", f"ส่งข้อความทดสอบสำหรับกล้อง '{cam_name}' สำเร็จแล้ว!")
            else:
                messagebox.showerror("LINE Notify Test", "ส่งข้อความทดสอบล้มเหลว กรุณาตรวจสอบความถูกต้องของรหัส Token หรือสัญญาณเน็ตเวิร์ก")
                
        msg = f"\n🧪 [DPDF Camera Alert Test]\nการทดสอบเตือนภัยเฉพาะกล้อง: {cam_name.upper()}\n⏰ เวลาทดสอบ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_line_notify_async(msg, token, callback=test_callback)

    def open_camera_settings(self, idx):
        cfg = self.camera_configs[idx]
        modal = tk.Toplevel(self)
        modal.title("Camera Configuration")
        modal.geometry("420x350")
        modal.configure(bg="#0c0c0e")
        modal.transient(self)
        modal.grab_set()
        modal.resizable(False, False)
        
        # UI inputs
        tk.Label(modal, text="Camera Name:", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(20, 2))
        ent_name = tk.Entry(modal, bg="#16161e", fg="#ffffff", bd=1)
        ent_name.insert(0, cfg["name"])
        ent_name.pack(fill="x", padx=20, pady=2)
        
        # Source Selection Dropdown
        src_lbl_frame = ttk.Frame(modal)
        src_lbl_frame.pack(fill="x", padx=20, pady=(10, 2))
        tk.Label(src_lbl_frame, text="Select Camera Source:", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(
            src_lbl_frame, text="❔", font=("Segoe UI", 8, "bold"), 
            bg="#1e1e24", fg="#00f0ff", activebackground="#2a2a35", activeforeground="#00f0ff", 
            bd=0, padx=5, pady=0, command=self.show_camera_source_help
        ).pack(side="left", padx=5)
        
        # Build dropdown options based on detected cameras
        choices = []
        for cam_idx in self.available_cameras:
            choices.append(f"Local Camera {cam_idx} (Detected)")
        for cam_idx in range(5):
            if cam_idx not in self.available_cameras:
                choices.append(f"Local Camera {cam_idx}")
        choices.append("IP Network Camera (RTSP URL)")
        
        # Determine initial selection
        curr_src = str(cfg["source"])
        initial_val = "IP Network Camera (RTSP URL)"
        if curr_src.isdigit():
            val_int = int(curr_src)
            if val_int in self.available_cameras:
                initial_val = f"Local Camera {val_int} (Detected)"
            else:
                initial_val = f"Local Camera {val_int}"
                
        combo_src = ttk.Combobox(modal, values=choices, state="readonly")
        combo_src.set(initial_val)
        combo_src.pack(fill="x", padx=20, pady=2)
        
        # Entry for custom RTSP URL
        rtsp_lbl = tk.Label(modal, text="RTSP Stream URL:", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold"))
        rtsp_lbl.pack(anchor="w", padx=20, pady=(5, 2))
        
        ent_src = tk.Entry(modal, bg="#16161e", fg="#ffffff", bd=1)
        ent_src.pack(fill="x", padx=20, pady=2)
        if not curr_src.isdigit():
            ent_src.insert(0, curr_src)
            
        def on_source_changed(event):
            selected = combo_src.get()
            if "Local Camera" in selected:
                ent_src.delete(0, "end")
                ent_src.configure(state="disabled", background="#0c0c0e")
            else:
                ent_src.configure(state="normal", background="#16161e")
                
        combo_src.bind("<<ComboboxSelected>>", on_source_changed)
        on_source_changed(None) # Call once to set initial state
        
        # LINE Notify settings per camera
        token_lbl_frame = ttk.Frame(modal)
        token_lbl_frame.pack(fill="x", padx=20, pady=(10, 2))
        tk.Label(token_lbl_frame, text="LINE Notify Token เฉพาะกล้อง (ข้ามค่าหลัก):", bg="#0c0c0e", fg="#8a8a98", font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Button(
            token_lbl_frame, text="❔", font=("Segoe UI", 8, "bold"), 
            bg="#1e1e24", fg="#00f0ff", activebackground="#2a2a35", activeforeground="#00f0ff", 
            bd=0, padx=5, pady=0, command=self.show_line_token_help
        ).pack(side="left", padx=5)
        
        token_entry_frame = ttk.Frame(modal)
        token_entry_frame.pack(fill="x", padx=20, pady=2)
        
        ent_token = tk.Entry(token_entry_frame, bg="#16161e", fg="#ffffff", bd=1)
        ent_token.insert(0, cfg.get("line_token", ""))
        ent_token.pack(side="left", fill="x", expand=True)
        
        tk.Button(
            token_entry_frame, text="🧪 ทดสอบ", font=("Segoe UI", 8, "bold"), 
            bg="#1e1e24", fg="#f0f0f5", activebackground="#2a2a35", activeforeground="#ffffff", 
            bd=0, padx=8, pady=2, command=lambda: self.test_camera_line_notify(ent_token.get().strip(), cfg["name"])
        ).pack(side="left", padx=(5, 0))
        
        # Save Button
        def do_save():
            selected = combo_src.get()
            if "Local Camera" in selected:
                parts = selected.split()
                final_source = parts[2]
            else:
                final_source = ent_src.get().strip()
                if not final_source:
                    messagebox.showerror("Error", "กรุณาระบุ RTSP URL สำหรับกล้องเน็ตเวิร์ก")
                    return
            self.save_camera_settings(modal, idx, ent_name.get(), final_source, ent_token.get())
            
        btn_save = tk.Button(
            modal, text="Save Settings", font=("Segoe UI", 9, "bold"), bg="#00f0ff", fg="#000000", bd=0, pady=8,
            command=do_save
        )
        btn_save.pack(fill="x", padx=20, pady=20)

    def save_camera_settings(self, modal, idx, name, source, line_token):
        name = name.strip() or f"Camera {idx+1}"
        source = source.strip()
        line_token = line_token.strip()
        
        # Stop stream if running
        old_name = self.camera_configs[idx]["name"]
        self.monitor.stop_camera_stream(old_name)
            
        self.camera_configs[idx]["name"] = name
        self.camera_configs[idx]["source"] = source
        self.camera_configs[idx]["line_token"] = line_token
        self.save_camera_config()
        modal.destroy()
        self.rebuild_grid_view()
        
        # Restart stream
        self.monitor.start_camera_stream(name, source)

    def add_camera(self):
        new_idx = len(self.camera_configs)
        if new_idx >= 4:
            return
        self.camera_configs.append({"name": f"Camera {new_idx+1}", "source": "0", "line_token": ""})
        self.save_camera_config()
        self.rebuild_grid_view()

    def delete_camera(self, idx):
        cfg = self.camera_configs[idx]
        cam_name = cfg["name"]
        
        self.monitor.stop_camera_stream(cam_name)
            
        self.camera_configs.pop(idx)
        self.save_camera_config()
        self.rebuild_grid_view()

    def auto_start_streams(self):
        self.monitor.stop_all_streams()
        for cfg in self.camera_configs:
            name = cfg["name"]
            source = cfg["source"]
            self.monitor.start_camera_stream(name, source)

    def stop_all_streams(self):
        self.monitor.stop_all_streams()

    def save_camera_config(self):
        config_data = {
            "global_line_token": self.global_line_token,
            "fall_threshold": self.fall_threshold,
            "line_cooldown": self.line_cooldown,
            "audio_alert_enabled": self.audio_alert_enabled,
            "cameras": [{"name": c["name"], "source": c["source"], "line_token": c.get("line_token", "")} for c in self.camera_configs]
        }
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def load_camera_config(self):
        self.global_line_token = ""
        self.fall_threshold = 0.6
        self.line_cooldown = 60
        self.audio_alert_enabled = True
        default_cameras = [{"name": "Webcam 3D", "source": "0", "line_token": ""}]
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.global_line_token = data.get("global_line_token", "")
                        self.fall_threshold = data.get("fall_threshold", 0.6)
                        self.line_cooldown = data.get("line_cooldown", 60)
                        self.audio_alert_enabled = data.get("audio_alert_enabled", True)
                        return data.get("cameras", default_cameras)
                    elif isinstance(data, list):
                        # Backward compatibility for old list-only config format
                        return [{"name": c["name"], "source": c["source"], "line_token": ""} for c in data]
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_cameras

    def update_gui_loop(self):
        any_fall = False
        fall_cam_name = ""
        
        for cfg in self.camera_configs:
            cam_name = cfg["name"]
            if cam_name in self.active_streams:
                stream = self.active_streams[cam_name]
                frame = stream.last_frame
                
                if frame is not None:
                    w = cfg["label_widget"].winfo_width()
                    h = cfg["label_widget"].winfo_height()
                    frame_resized = cv2.resize(frame, (w, h)) if w > 10 and h > 10 else cv2.resize(frame, (320, 240))
                    
                    ret_val, png_data = cv2.imencode('.png', frame_resized)
                    if ret_val:
                        imgtk = tk.PhotoImage(data=png_data.tobytes())
                        if "label_widget" in cfg and cfg["label_widget"].winfo_exists():
                            cfg["label_widget"].imgtk = imgtk
                            cfg["label_widget"].configure(image=imgtk)
                            
                if stream.last_status == "FALL DETECTED":
                    any_fall = True
                    fall_cam_name = cam_name
                    
                    # Trigger Line Notify with Cooldown Check
                    curr_time = time.time()
                    last_sent = self.last_line_notify_time.get(cam_name, 0.0)
                    if curr_time - last_sent > self.line_cooldown:
                        self.last_line_notify_time[cam_name] = curr_time
                        
                        # Determine token (camera override -> global token)
                        token = cfg.get("line_token", "").strip() or self.global_line_token
                        if token:
                            msg = f"\n🚨 แจ้งเตือนตรวจพบการล้ม!\n📷 กล้อง: {cam_name.upper()}\n⏰ เวลา: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            send_line_notify_async(msg, token)
                    
        # Update Alert Banner & Audio Alert
        if any_fall:
            self.alert_banner.configure(text=f"⚠️ WARNING! FALL DETECTED ON CAMERA: {fall_cam_name.upper()} ⚠️", bg="#ff0055", fg="#ffffff")
            
            # Sound alarm if enabled and cooldown passed (5 seconds)
            if self.audio_alert_enabled:
                curr_t = time.time()
                if curr_t - self.last_audio_alert_time > 5.0:
                    self.last_audio_alert_time = curr_t
                    # Beep asynchronously in a separate thread so it doesn't block GUI
                    try:
                        import winsound
                        threading.Thread(target=lambda: winsound.Beep(1000, 600), daemon=True).start()
                    except Exception:
                        pass
        else:
            self.alert_banner.configure(text="", bg="#0c0c0e")
            
        self.after(33, self.update_gui_loop)

    def destroy(self):
        self.stop_all_streams()
        super().destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()
