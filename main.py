"""
Pre-Fall Detection 3D - Client Dashboard
Refactored and optimized according to UXUI_Design_Principles.md
"""

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
import datetime
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
import theme
from core.camera_monitor import CameraMonitor, send_line_notify_async
from ui_components import (
    AppFonts,
    PrimaryButton,
    SecondaryButton,
    DangerButton,
    IconButton,
    CardFrame,
    BaseModalDialog,
    EmptyCameraSlot,
    ToastBanner,
    Tooltip,
    convert_cv2_to_tk_image
)

# Reconfigure stdout/stderr to UTF-8
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


class GlobalSettingsDialog(BaseModalDialog):
    """Modal dialog for global system configurations."""
    def __init__(self, parent, app):
        super().__init__(parent, title="Global System Settings", width=500, height=480, resizable=True, min_width=440, min_height=420)
        self.app = app
        fonts = theme.AppFonts.get(self)
        
        # Bottom Action Bar (Packed FIRST at bottom to ensure it is always visible)
        btn_bar = tk.Frame(self.body, bg=theme.BG_DARK)
        btn_bar.pack(fill="x", side="bottom", pady=(theme.SPACE_MD, 0))
        
        btn_cancel = SecondaryButton(btn_bar, text="ยกเลิก (Cancel)", command=self.destroy)
        btn_cancel.pack(side="right", padx=(theme.SPACE_SM, 0))
        
        btn_save = PrimaryButton(btn_bar, text="💾 บันทึกการตั้งค่า (Save)", command=self.do_save)
        btn_save.pack(side="right")
        
        # Form Content Container (Packs in remaining space)
        content = tk.Frame(self.body, bg=theme.BG_DARK)
        content.pack(fill="both", expand=True)
        
        # 1. AI Sensitivity Card
        card_ai = CardFrame(content)
        card_ai.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        lbl_ai_title = tk.Label(
            card_ai, text="AI Fall Detection Threshold (Sensitivity)", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_ai_title.pack(anchor="w")
        
        lbl_ai_sub = tk.Label(
            card_ai, text="ค่าความน่าจะเป็นขั้นต่ำเพื่อส่งสัญญาณเตือนภัย (ค่ามาตรฐาน 0.60)", font=fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_ai_sub.pack(anchor="w", pady=(0, theme.SPACE_SM))
        
        slider_frame = tk.Frame(card_ai, bg=theme.SURFACE_CARD)
        slider_frame.pack(fill="x")
        
        self.lbl_threshold_val = tk.Label(
            slider_frame, text=f"{self.app.fall_threshold:.2f}", font=fonts.MONO_BOLD,
            bg=theme.SURFACE_ELEVATED, fg=theme.PRIMARY, padx=theme.SPACE_SM, pady=theme.SPACE_XS
        )
        self.lbl_threshold_val.pack(side="right", padx=(theme.SPACE_SM, 0))
        
        def on_slider_change(val):
            self.lbl_threshold_val.configure(text=f"{float(val):.2f}")
            
        self.slider = tk.Scale(
            slider_frame, from_=0.10, to=0.90, resolution=0.05, orient="horizontal",
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY, highlightthickness=0,
            activebackground=theme.PRIMARY, troughcolor=theme.SURFACE_ELEVATED,
            command=on_slider_change
        )
        self.slider.set(self.app.fall_threshold)
        self.slider.pack(side="left", fill="x", expand=True)

        # 2. Alert Cooldown Card
        card_alert = CardFrame(content)
        card_alert.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        lbl_cd_title = tk.Label(
            card_alert, text="LINE Alert Cooldown (Seconds)", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_cd_title.pack(anchor="w")
        
        lbl_cd_sub = tk.Label(
            card_alert, text="ระยะเวลาหน่วงก่อนส่งข้อความเตือนซ้ำต่อกล้อง (ป้องกันข้อความสแปม)", font=fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_cd_sub.pack(anchor="w", pady=(0, theme.SPACE_SM))
        
        self.sp_cooldown = tk.Spinbox(
            card_alert, from_=10, to=300, increment=10, font=fonts.BODY,
            bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY, bd=1,
            insertbackground=theme.TEXT_PRIMARY, relief="solid", highlightthickness=0
        )
        self.sp_cooldown.delete(0, "end")
        self.sp_cooldown.insert(0, str(self.app.line_cooldown))
        self.sp_cooldown.pack(fill="x")

        # 3. Audio Alarm Card
        card_audio = CardFrame(content)
        card_audio.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        self.var_audio = tk.BooleanVar(value=self.app.audio_alert_enabled)
        chk_audio = tk.Checkbutton(
            card_audio, text="เปิดเสียงสัญญาณเตือนภัยในเครื่องเมื่อตรวจพบการล้ม (Audio Beep)",
            variable=self.var_audio, font=fonts.BODY,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY, selectcolor=theme.SURFACE_ELEVATED,
            activebackground=theme.SURFACE_CARD, activeforeground=theme.TEXT_PRIMARY,
            highlightthickness=0
        )
        chk_audio.pack(anchor="w")
        
        self.bind("<Return>", lambda e: self.do_save())

    def do_save(self):
        try:
            self.app.fall_threshold = float(self.slider.get())
            self.app.line_cooldown = max(5, int(self.sp_cooldown.get()))
            self.app.audio_alert_enabled = bool(self.var_audio.get())
            self.app.save_camera_config()
            self.destroy()
            self.app.toast.show_alert("บันทึกการตั้งค่าระบบเรียบร้อยแล้ว", "success", auto_hide_sec=3)
        except Exception as ex:
            messagebox.showerror("Error", f"ข้อมูลที่กรอกไม่ถูกต้อง: {ex}", parent=self)


class CameraConfigDialog(BaseModalDialog):
    """Modal dialog for individual camera stream configuration."""
    def __init__(self, parent, app, camera_index):
        super().__init__(parent, title="Camera Configuration", width=540, height=560, resizable=True, min_width=480, min_height=500)
        self.app = app
        self.idx = camera_index
        self.cfg = self.app.camera_configs[camera_index]
        fonts = theme.AppFonts.get(self)

        # Bottom Action Bar (Packed FIRST at bottom to ensure it is ALWAYS visible and never cut off)
        btn_bar = tk.Frame(self.body, bg=theme.BG_DARK)
        btn_bar.pack(fill="x", side="bottom", pady=(theme.SPACE_MD, 0))
        
        btn_cancel = SecondaryButton(btn_bar, text="ยกเลิก (Cancel)", command=self.destroy)
        btn_cancel.pack(side="right", padx=(theme.SPACE_SM, 0))
        
        btn_save = PrimaryButton(btn_bar, text="💾 บันทึกกล้อง (Save)", command=self.do_save)
        btn_save.pack(side="right")

        # Form Content Container (Packs in remaining vertical space)
        content = tk.Frame(self.body, bg=theme.BG_DARK)
        content.pack(fill="both", expand=True)

        # 1. Camera Name Field
        card_name = CardFrame(content)
        card_name.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        lbl_name = tk.Label(
            card_name, text="ชื่อจุดตรวจจับ (Camera Name):", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_name.pack(anchor="w", pady=(0, theme.SPACE_XS))
        
        self.ent_name = tk.Entry(
            card_name, font=fonts.BODY, bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY, bd=1, relief="solid", highlightthickness=0
        )
        self.ent_name.insert(0, self.cfg.get("name", f"Camera {self.idx+1}"))
        self.ent_name.pack(fill="x", ipady=3)

        # 2. Camera Source Field
        card_src = CardFrame(content)
        card_src.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        header_src = tk.Frame(card_src, bg=theme.SURFACE_CARD)
        header_src.pack(fill="x", pady=(0, theme.SPACE_XS))
        
        lbl_src = tk.Label(
            header_src, text="แหล่งสัญญาณภาพ (Camera Source):", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_src.pack(side="left")
        
        btn_src_help = IconButton(
            header_src, icon="❔", command=self.show_source_help,
            bg_color=theme.SURFACE_CARD, fg_color=theme.PRIMARY, hover_bg=theme.SURFACE_HOVER,
            tooltip="คำแนะนำประเภทกล้อง"
        )
        btn_src_help.pack(side="left", padx=theme.SPACE_XS)
        
        # Build dropdown options
        choices = []
        for cam_idx in self.app.available_cameras:
            choices.append(f"Local Camera {cam_idx} (Detected)")
        for cam_idx in range(4):
            if cam_idx not in self.app.available_cameras:
                choices.append(f"Local Camera {cam_idx}")
        choices.append("IP Network Camera (RTSP Stream)")
        
        curr_src = str(self.cfg.get("source", "0"))
        initial_val = "IP Network Camera (RTSP Stream)"
        if curr_src.isdigit():
            val_int = int(curr_src)
            if val_int in self.app.available_cameras:
                initial_val = f"Local Camera {val_int} (Detected)"
            else:
                initial_val = f"Local Camera {val_int}"

        self.combo_src = ttk.Combobox(card_src, values=choices, state="readonly", font=fonts.BODY)
        self.combo_src.set(initial_val)
        self.combo_src.pack(fill="x", pady=(0, theme.SPACE_SM))

        lbl_rtsp = tk.Label(
            card_src, text="ลิงก์สตรีม RTSP (สำหรับกล้องวงจรปิด IP Camera):", font=fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_rtsp.pack(anchor="w", pady=(0, 2))

        self.ent_rtsp = tk.Entry(
            card_src, font=fonts.BODY, bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY, bd=1, relief="solid", highlightthickness=0
        )
        if not curr_src.isdigit():
            self.ent_rtsp.insert(0, curr_src)
        self.ent_rtsp.pack(fill="x", ipady=3)

        def on_src_select(e=None):
            selected = self.combo_src.get()
            if "Local Camera" in selected:
                self.ent_rtsp.configure(state="disabled", bg=theme.SURFACE_CARD)
            else:
                self.ent_rtsp.configure(state="normal", bg=theme.SURFACE_ELEVATED)

        self.combo_src.bind("<<ComboboxSelected>>", on_src_select)
        on_src_select()

        # 3. LINE Token Override Field
        card_token = CardFrame(content)
        card_token.pack(fill="x", pady=(0, theme.SPACE_SM))
        
        lbl_tk = tk.Label(
            card_token, text="LINE Notify Token เฉพาะกล้องนี้ (ไม่จำเป็นต้องระบุ):", font=fonts.BODY_BOLD,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
        )
        lbl_tk.pack(anchor="w")
        
        lbl_tk_sub = tk.Label(
            card_token, text="หากระบุจะส่งแจ้งเตือนแยกกลุ่มไลน์ตามจุด แทน Token หลักของระบบ", font=fonts.CAPTION,
            bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY
        )
        lbl_tk_sub.pack(anchor="w", pady=(0, theme.SPACE_XS))
        
        tk_entry_bar = tk.Frame(card_token, bg=theme.SURFACE_CARD)
        tk_entry_bar.pack(fill="x")
        
        self.ent_token = tk.Entry(
            tk_entry_bar, font=fonts.BODY, bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY, bd=1, relief="solid", highlightthickness=0
        )
        self.ent_token.insert(0, self.cfg.get("line_token", ""))
        self.ent_token.pack(side="left", fill="x", expand=True, ipady=3)
        
        btn_test = SecondaryButton(
            tk_entry_bar, text="🧪 ทดสอบ", command=self.test_line,
            padx=theme.SPACE_SM, pady=theme.SPACE_XS
        )
        btn_test.pack(side="right", padx=(theme.SPACE_SM, 0))

        self.bind("<Return>", lambda e: self.do_save())

    def show_source_help(self):
        msg = (
            "วิธีกรอกแหล่งสัญญาณกล้อง (Camera Source):\n\n"
            "1. กล้องเว็บแคมในตัว หรือ USB Webcam:\n"
            "   - เลือก Local Camera ในดรอปดาวน์ (0, 1, 2...)\n\n"
            "2. กล้องวงจรปิด IP Network Camera (RTSP):\n"
            "   - เลือก 'IP Network Camera' แล้วกรอก URL สตรีม เช่น:\n"
            "   rtsp://username:password@192.168.1.100:554/stream1"
        )
        messagebox.showinfo("คู่มือแหล่งสัญญาณกล้อง", msg, parent=self)

    def test_line(self):
        token = self.ent_token.get().strip()
        cam_name = self.ent_name.get().strip() or "Camera"
        if not token:
            messagebox.showwarning("Warning", "กรุณาระบุ Token เฉพาะกล้องก่อนทำการทดสอบ", parent=self)
            return
            
        def cb(success):
            if success:
                self.after(0, lambda: messagebox.showinfo("LINE Notify", f"ส่งแจ้งเตือนทดสอบสำหรับ '{cam_name}' สำเร็จแล้ว!", parent=self))
            else:
                self.after(0, lambda: messagebox.showerror("LINE Notify", "ส่งแจ้งเตือนล้มเหลว กรุณาตรวจสอบรหัส Token", parent=self))
                
        msg = f"\n🧪 [DPDF Alert Test]\nทดสอบการเชื่อมต่อกล้อง: {cam_name.upper()}\n⏰ เวลา: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_line_notify_async(msg, token, callback=cb)

    def do_save(self):
        name = self.ent_name.get().strip() or f"Camera {self.idx+1}"
        selected = self.combo_src.get()
        if "Local Camera" in selected:
            parts = selected.split()
            source = parts[2]
        else:
            source = self.ent_rtsp.get().strip()
            if not source:
                messagebox.showerror("Error", "กรุณาระบุ RTSP URL สำหรับกล้องเน็ตเวิร์ก", parent=self)
                return
                
        token = self.ent_token.get().strip()
        
        # Stop previous stream
        old_name = self.app.camera_configs[self.idx].get("name", "")
        self.app.monitor.stop_camera_stream(old_name)
        
        # Update config
        self.app.camera_configs[self.idx]["name"] = name
        self.app.camera_configs[self.idx]["source"] = source
        self.app.camera_configs[self.idx]["line_token"] = token
        self.app.save_camera_config()
        self.destroy()
        self.app.rebuild_grid_view()
        
        # Start new stream
        self.app.monitor.start_camera_stream(name, source)
        self.app.toast.show_alert(f"บันทึกและเชื่อมต่อกล้อง '{name}' สำเร็จ", "success", auto_hide_sec=3)


class HelpDialog(BaseModalDialog):
    """Modal dialog displaying comprehensive user guide and instructions."""
    def __init__(self, parent):
        super().__init__(parent, title="DPDF 3D - User Manual & Help Guide", width=620, height=540, resizable=True, min_width=520, min_height=440)
        fonts = theme.AppFonts.get(self)

        btn_ok = PrimaryButton(self.body, text="เข้าใจแล้ว (Close)", command=self.destroy)
        btn_ok.pack(side="bottom", fill="x", pady=(theme.SPACE_MD, 0))

        notebook = ttk.Notebook(self.body)
        notebook.pack(fill="both", expand=True)

        # Tab 1: Quick Start
        tab1 = tk.Frame(notebook, bg=theme.BG_DARK, padx=theme.SPACE_MD, pady=theme.SPACE_MD)
        notebook.add(tab1, text="📹 Camera Setup")

        t1_text = (
            "คู่มือการใช้งานระบบและการเชื่อมต่อกล้อง:\n\n"
            "1. เชื่อมต่อกล้องใหม่:\n"
            "   - กดปุ่ม '+ Add Stream' บนแถบด้านบนหรือกด '+ Add Camera Stream' บนช่องว่าง\n"
            "   - หรือกดปุ่มลัด 'Ctrl + N'\n\n"
            "2. ตั้งค่ากล้องแต่ละจุด (⚙):\n"
            "   - กดปุ่มรูปฟันเฟืองที่มุมกล้องเพื่อเปลี่ยนชื่อและประเภทสัญญาณ\n"
            "   - กล้อง Webcam เสียบสาย: เลือกลำดับกล้อง (Local Camera 0, 1...)\n"
            "   - กล้อง IP RTSP: กรอก URL เครือข่าย (rtsp://...)\n\n"
            "3. การปิดหรือลบกล้อง (✕):\n"
            "   - กดปุ่มเครื่องหมายกากบาทที่มุมขวาบนของกล้องนั้นๆ เพื่อปิดสตรีมและนำออกจากระบบ"
        )
        lbl_t1 = tk.Label(tab1, text=t1_text, font=fonts.BODY, bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY, justify="left", anchor="nw")
        lbl_t1.pack(fill="both", expand=True)

        # Tab 2: LINE Notify
        tab2 = tk.Frame(notebook, bg=theme.BG_DARK, padx=theme.SPACE_MD, pady=theme.SPACE_MD)
        notebook.add(tab2, text="💬 LINE Notify")

        t2_text = (
            "ขั้นตอนการออกรหัส LINE Notify Token สำหรับแจ้งเตือนภัย:\n\n"
            "1. เปิดเว็บเบราว์เซอร์แล้วไปที่: https://notify-bot.line.me\n"
            "2. ล็อกอินด้วยบัญชี LINE ของท่าน\n"
            "3. คลิกที่ชื่อบัญชีมุมขวาบน -> เลือก 'My Page (หน้าของฉัน)'\n"
            "4. เลื่อนลงมาด้านล่างสุด คลิกปุ่ม 'Generate Token (ออก Token)'\n"
            "5. ตั้งชื่อบอท (เช่น DPDF Alert) และเลือก 'กลุ่มแชต' ที่ต้องการรับแจ้งเตือน\n"
            "6. คัดลอกรหัส Token ที่ได้รับ นำมาวางในช่อง 'LINE Notify Token' ด้านล่างโปรแกรม\n\n"
            "⚠️ สำคัญมาก: ต้องกด 'เชิญเพื่อน' นำบอทชื่อ 'LINE Notify' เข้าร่วมกลุ่มแชตนั้นด้วย"
        )
        lbl_t2 = tk.Label(tab2, text=t2_text, font=fonts.BODY, bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY, justify="left", anchor="nw")
        lbl_t2.pack(fill="both", expand=True)

        # Tab 3: Shortcuts & Info
        tab3 = tk.Frame(notebook, bg=theme.BG_DARK, padx=theme.SPACE_MD, pady=theme.SPACE_MD)
        notebook.add(tab3, text="⌨️ Shortcuts & Info")

        t3_text = (
            "แป้นพิมพ์ลัด (Keyboard Shortcuts):\n\n"
            "• Ctrl + N : เพิ่มกล้องใหม่ (Add Camera Stream)\n"
            "• Ctrl + S : บันทึก Token และการตั้งค่าระบบ\n"
            "• F1       : เปิดหน้าต่างคู่มือช่วยเหลือนี้\n"
            "• Esc      : ปิดหน้าต่างการตั้งค่าหรือไดอะล็อก\n\n"
            "ข้อมูลระบบ:\n"
            "• Software: DPDF 3D Pre-Fall Detection System\n"
            "• Core AI: MediaPipe Pose 3D + GRU Temporal Network\n"
            "• Status: Standalone Desktop Client v2.0"
        )
        lbl_t3 = tk.Label(tab3, text=t3_text, font=fonts.BODY, bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY, justify="left", anchor="nw")
        lbl_t3.pack(fill="both", expand=True)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DPDF 3D - Pre-Fall Detection Dashboard")
        self.geometry("1240x820")
        self.minsize(960, 640)
        self.configure(bg=theme.BG_DARK)
        
        # Initialize fonts & theme
        self.fonts = AppFonts.get(self)
        theme.apply_ttk_theme(self)
        
        # Load window icon
        icon_path = os.path.join(config.BASE_DIR, "assets", "icon.png")
        if os.path.exists(icon_path):
            try:
                self.iconphoto(True, tk.PhotoImage(file=icon_path))
            except Exception:
                pass
                
        # App state variables
        self.global_line_token = ""
        self.last_line_notify_time = {}
        self.fall_threshold = 0.6
        self.line_cooldown = 60
        self.audio_alert_enabled = True
        self.last_audio_alert_time = 0.0
        
        # Load configuration
        self.config_path = os.path.join(config.BASE_DIR, "client_config.json")
        self.camera_configs = self.load_camera_config()
        
        # Initialize camera monitor
        self.monitor = CameraMonitor(self)
        self.active_streams = self.monitor.active_streams
        self.available_cameras = CameraMonitor.detect_available_cameras()
        
        # Build UI layout
        self.create_layout()
        self.bind_shortcuts()
        
        # Start streams and GUI render loop
        self.auto_start_streams()
        self.update_gui_loop()

    def bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.add_camera())
        self.bind("<Control-N>", lambda e: self.add_camera())
        self.bind("<Control-s>", lambda e: self.save_global_token())
        self.bind("<Control-S>", lambda e: self.save_global_token())
        self.bind("<F1>", lambda e: self.show_main_help())

    def create_layout(self):
        # Master workspace container with responsive grid weights
        self.workspace = tk.Frame(self, bg=theme.BG_DARK, padx=theme.SPACE_LG, pady=theme.SPACE_MD)
        self.workspace.pack(fill="both", expand=True)
        
        self.workspace.columnconfigure(0, weight=1)
        self.workspace.rowconfigure(0, weight=0) # Row 0: Top Nav Bar (Fixed height)
        self.workspace.rowconfigure(1, weight=1) # Row 1: Camera Grid (Expands to fill all middle space)
        self.workspace.rowconfigure(2, weight=0) # Row 2: Toast Alert Banner (Fixed height)
        self.workspace.rowconfigure(3, weight=0) # Row 3: Bottom LINE Notify Bar (Fixed height, always anchored)
        
        # ==========================================
        # 1. Top Navigation Bar (Row 0)
        # ==========================================
        nav_bar = tk.Frame(self.workspace, bg=theme.BG_DARK)
        nav_bar.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_SM))
        
        # Left: Branding
        brand_frame = tk.Frame(nav_bar, bg=theme.BG_DARK)
        brand_frame.pack(side="left")
        
        lbl_logo = tk.Label(brand_frame, text="🛡️", font=("Segoe UI Emoji", 18), bg=theme.BG_DARK, fg=theme.PRIMARY)
        lbl_logo.pack(side="left", padx=(0, theme.SPACE_SM))
        
        title_group = tk.Frame(brand_frame, bg=theme.BG_DARK)
        title_group.pack(side="left")
        
        lbl_title = tk.Label(title_group, text="PRE-FALL DETECTION 3D", font=self.fonts.H1, bg=theme.BG_DARK, fg=theme.TEXT_PRIMARY)
        lbl_title.pack(anchor="w")
        
        lbl_sub = tk.Label(title_group, text="Real-time AI Biomechanical Risk Monitoring Grid", font=self.fonts.CAPTION, bg=theme.BG_DARK, fg=theme.TEXT_SECONDARY)
        lbl_sub.pack(anchor="w")
        
        # Right: Quick Controls
        ctrl_frame = tk.Frame(nav_bar, bg=theme.BG_DARK)
        ctrl_frame.pack(side="right")
        
        self.lbl_cam_count = tk.Label(
            ctrl_frame, text="", font=self.fonts.CAPTION_BOLD,
            bg=theme.SURFACE_ELEVATED, fg=theme.SUCCESS,
            padx=theme.SPACE_MD, pady=theme.SPACE_SM
        )
        self.lbl_cam_count.pack(side="left", padx=(0, theme.SPACE_SM))
        
        btn_add_cam = SecondaryButton(
            ctrl_frame, text="➕ Add Stream", command=self.add_camera,
            tooltip="Add new camera stream (Ctrl+N)"
        )
        btn_add_cam.pack(side="left", padx=(0, theme.SPACE_SM))
        
        btn_settings = SecondaryButton(
            ctrl_frame, text="⚙️ Settings", command=self.open_global_settings,
            tooltip="Open system settings"
        )
        btn_settings.pack(side="left", padx=(0, theme.SPACE_SM))
        
        btn_help = SecondaryButton(
            ctrl_frame, text="❔ Help Guide", command=self.show_main_help,
            tooltip="Open user manual (F1)"
        )
        btn_help.pack(side="left")

        # ==========================================
        # 2. Camera Grid Container (Row 1)
        # ==========================================
        self.grid_container = tk.Frame(self.workspace, bg=theme.BG_DARK)
        self.grid_container.grid(row=1, column=0, sticky="nsew", pady=(0, theme.SPACE_SM))

        # ==========================================
        # 3. Toast Alert Banner (Row 2)
        # ==========================================
        self.toast = ToastBanner(self.workspace)
        self.toast.grid(row=2, column=0, sticky="ew", pady=(0, theme.SPACE_XS))

        # ==========================================
        # 4. Bottom LINE Notify Bar (Row 3)
        # ==========================================
        line_card = CardFrame(self.workspace, padding=theme.SPACE_SM)
        line_card.grid(row=3, column=0, sticky="ew")
        
        lbl_line = tk.Label(line_card, text="LINE Notify Token หลัก:", font=self.fonts.BODY_BOLD, bg=theme.SURFACE_CARD, fg=theme.TEXT_SECONDARY)
        lbl_line.pack(side="left", padx=(theme.SPACE_SM, theme.SPACE_SM))
        
        self.ent_global_token = tk.Entry(
            line_card, font=self.fonts.BODY, bg=theme.SURFACE_ELEVATED, fg=theme.TEXT_PRIMARY,
            insertbackground=theme.TEXT_PRIMARY, bd=1, relief="solid", highlightthickness=0
        )
        self.ent_global_token.insert(0, self.global_line_token)
        self.ent_global_token.pack(side="left", fill="x", expand=True, padx=theme.SPACE_SM, ipady=3)
        
        btn_line_help = IconButton(
            line_card, icon="❔", command=self.show_line_token_help,
            bg_color=theme.SURFACE_CARD, fg_color=theme.PRIMARY, hover_bg=theme.SURFACE_HOVER,
            tooltip="วิธีขอรหัส LINE Notify Token"
        )
        btn_line_help.pack(side="left", padx=(0, theme.SPACE_SM))
        
        btn_test_line = SecondaryButton(
            line_card, text="🧪 ทดสอบส่ง", command=self.test_global_line_notify,
            padx=theme.SPACE_MD, pady=theme.SPACE_XS, tooltip="ทดสอบการส่งข้อความเข้ากลุ่ม LINE"
        )
        btn_test_line.pack(side="left", padx=(0, theme.SPACE_SM))
        
        btn_save_token = PrimaryButton(
            line_card, text="💾 บันทึก Token", command=self.save_global_token,
            padx=theme.SPACE_MD, pady=theme.SPACE_XS, tooltip="บันทึก Token หลัก (Ctrl+S)"
        )
        btn_save_token.pack(side="left", padx=(0, theme.SPACE_SM))

        # Build initial grid
        self.rebuild_grid_view()

    def open_global_settings(self):
        GlobalSettingsDialog(self, self)

    def show_main_help(self):
        HelpDialog(self)

    def show_line_token_help(self):
        HelpDialog(self)

    def test_global_line_notify(self):
        token = self.ent_global_token.get().strip()
        if not token:
            self.toast.show_alert("กรุณาระบุ LINE Token ก่อนทำการทดสอบ", "warning", auto_hide_sec=3)
            return
            
        def cb(success):
            if success:
                self.after(0, lambda: self.toast.show_alert("ส่งข้อความทดสอบเข้ากลุ่มไลน์สำเร็จแล้ว!", "success", auto_hide_sec=4))
            else:
                self.after(0, lambda: self.toast.show_alert("ส่งข้อความทดสอบล้มเหลว กรุณาตรวจสอบรหัส Token", "danger", auto_hide_sec=5))
                
        msg = f"\n🧪 [DPDF Alert Test]\nการทดสอบการเชื่อมต่อระบบเตือนภัยสำเร็จแล้ว!\n⏰ เวลาทดสอบ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        send_line_notify_async(msg, token, callback=cb)

    def save_global_token(self):
        self.global_line_token = self.ent_global_token.get().strip()
        self.save_camera_config()
        self.toast.show_alert("บันทึกรหัส LINE Token หลักเรียบร้อยแล้ว", "success", auto_hide_sec=3)

    def rebuild_grid_view(self):
        for widget in self.grid_container.winfo_children():
            widget.destroy()
            
        num_cameras = len(self.camera_configs)
        self.lbl_cam_count.configure(text=f"● {num_cameras} Active Stream{'s' if num_cameras != 1 else ''}")
        
        # Grid layout determination
        if num_cameras <= 1:
            rows, cols = 1, 1
        elif num_cameras == 2:
            rows, cols = 1, 2
        else:
            rows, cols = 2, 2
            
        for r in range(rows):
            self.grid_container.rowconfigure(r, weight=1)
        for c in range(cols):
            self.grid_container.columnconfigure(c, weight=1)
            
        total_slots = 4 if num_cameras >= 2 else (1 if num_cameras == 0 else min(2, num_cameras + 1))
        
        for i in range(total_slots):
            r = i // cols
            c = i % cols
            
            if i < num_cameras:
                cfg = self.camera_configs[i]
                cam_name = cfg.get("name", f"Camera {i+1}")
                
                # Active Camera Card (Using grid inside card to cleanly separate header from video container)
                cell = CardFrame(self.grid_container, bg=theme.SURFACE_CARD, padding=theme.SPACE_XS)
                cell.grid(row=r, column=c, sticky="nsew", padx=theme.SPACE_XS, pady=theme.SPACE_XS)
                cell.columnconfigure(0, weight=1)
                cell.rowconfigure(0, weight=0) # Header bar
                cell.rowconfigure(1, weight=1) # Video container
                
                # Top Header Bar (Persistent frame above the video, never covered by image frames)
                top_bar = tk.Frame(cell, bg=theme.SURFACE_CARD, padx=theme.SPACE_SM, pady=theme.SPACE_XS)
                top_bar.grid(row=0, column=0, sticky="ew", pady=(0, theme.SPACE_XS))
                
                lbl_cam_title = tk.Label(
                    top_bar, text=cam_name.upper(), font=self.fonts.BODY_BOLD,
                    bg=theme.SURFACE_CARD, fg=theme.TEXT_PRIMARY
                )
                lbl_cam_title.pack(side="left")
                
                # Right action icons
                btn_close = IconButton(
                    top_bar, icon="✕", command=lambda idx=i: self.delete_camera(idx),
                    bg_color=theme.SURFACE_CARD, fg_color=theme.TEXT_MUTED,
                    hover_bg=theme.DANGER, tooltip="Remove Camera Stream"
                )
                btn_close.pack(side="right", padx=(theme.SPACE_XS, 0))
                
                btn_gear = IconButton(
                    top_bar, icon="⚙", command=lambda idx=i: self.open_camera_settings(idx),
                    bg_color=theme.SURFACE_CARD, fg_color=theme.TEXT_SECONDARY,
                    hover_bg=theme.SURFACE_HOVER, tooltip="Configure Camera"
                )
                btn_gear.pack(side="right")
                
                # Dedicated Video Container Frame with pack_propagate(False)
                video_container = tk.Frame(cell, bg=theme.OVERLAY_BG)
                video_container.grid(row=1, column=0, sticky="nsew")
                video_container.pack_propagate(False)
                
                lbl_video = tk.Label(video_container, bg=theme.OVERLAY_BG)
                lbl_video.pack(fill="both", expand=True)
                
                cfg["label_widget"] = lbl_video
                cfg["container_widget"] = video_container
                
            elif i == num_cameras and num_cameras < 4:
                # Empty Camera Slot conforming to UX/UI Principle Section 9
                slot = EmptyCameraSlot(self.grid_container, on_add_callback=self.add_camera)
                slot.grid(row=r, column=c, sticky="nsew", padx=theme.SPACE_XS, pady=theme.SPACE_XS)

    def open_camera_settings(self, idx):
        CameraConfigDialog(self, self, idx)

    def add_camera(self):
        new_idx = len(self.camera_configs)
        if new_idx >= 4:
            self.toast.show_alert("รองรับการเชื่อมต่อกล้องสูงสุด 4 ช่องสัญญาณพร้อมกัน", "warning", auto_hide_sec=3)
            return
            
        new_source = "0"
        for cam_id in self.available_cameras:
            if not any(str(c.get("source")) == str(cam_id) for c in self.camera_configs):
                new_source = str(cam_id)
                break
                
        self.camera_configs.append({
            "name": f"Camera {new_idx+1}",
            "source": new_source,
            "line_token": ""
        })
        self.save_camera_config()
        self.rebuild_grid_view()
        self.monitor.start_camera_stream(f"Camera {new_idx+1}", new_source)
        self.toast.show_alert(f"เพิ่มกล้อง Camera {new_idx+1} เรียบร้อยแล้ว", "success", auto_hide_sec=3)

    def delete_camera(self, idx):
        cfg = self.camera_configs[idx]
        cam_name = cfg.get("name", f"Camera {idx+1}")
        
        confirm = messagebox.askyesno(
            "Confirm Remove Camera",
            f"คุณแน่ใจหรือไม่ว่าต้องการปิดและนำกล้อง '{cam_name}' ออกจากระบบ?",
            parent=self
        )
        if not confirm:
            return
            
        self.monitor.stop_camera_stream(cam_name)
        self.camera_configs.pop(idx)
        self.save_camera_config()
        self.rebuild_grid_view()
        self.toast.show_alert(f"นำกล้อง '{cam_name}' ออกเรียบร้อยแล้ว", "info", auto_hide_sec=3)

    def auto_start_streams(self):
        self.monitor.stop_all_streams()
        for cfg in self.camera_configs:
            name = cfg.get("name", "")
            source = cfg.get("source", "0")
            if name:
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
                        return [{"name": c["name"], "source": c["source"], "line_token": ""} for c in data]
            except Exception as e:
                print(f"Error loading config: {e}")
        return default_cameras

    def update_gui_loop(self):
        any_fall = False
        fall_cam_name = ""
        
        for cfg in self.camera_configs:
            cam_name = cfg.get("name", "")
            if cam_name in self.active_streams:
                stream = self.active_streams[cam_name]
                frame = stream.last_frame
                
                if frame is not None and "label_widget" in cfg and cfg["label_widget"].winfo_exists():
                    # Calculate dimensions from container frame
                    container = cfg.get("container_widget", cfg["label_widget"])
                    w = container.winfo_width()
                    h = container.winfo_height()
                    
                    # Ultra-fast zero-compression frame conversion (12x faster than PNG)
                    imgtk = convert_cv2_to_tk_image(frame, target_width=w, target_height=h)
                    if imgtk:
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
                        
                        # Trigger local video clip recording
                        video_path = stream.save_fall_clip()
                        video_filename = os.path.basename(video_path)
                        
                        token = cfg.get("line_token", "").strip() or self.global_line_token
                        if token:
                            msg = f"\n🚨 แจ้งเตือนตรวจพบการล้ม!\n📷 กล้อง: {cam_name.upper()}\n⏰ เวลา: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n📂 บันทึกวิดีโอหลักฐาน: {video_filename}"
                            send_line_notify_async(msg, token)
                            
        # Update Alert Banner & Audio Alert
        if any_fall:
            self.toast.show_alert(f"⚠️ WARNING! FALL DETECTED ON CAMERA: {fall_cam_name.upper()} ⚠️", "danger")
            if self.audio_alert_enabled:
                curr_t = time.time()
                if curr_t - self.last_audio_alert_time > 4.0:
                    self.last_audio_alert_time = curr_t
                    try:
                        import winsound
                        threading.Thread(target=lambda: winsound.Beep(1000, 500), daemon=True).start()
                    except Exception:
                        pass
        else:
            # Only clear if it's currently a danger alert
            if self.toast.cget("bg") == theme.DANGER:
                self.toast.clear()
                
        self.after(33, self.update_gui_loop)

    def destroy(self):
        self.stop_all_streams()
        super().destroy()


if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.destroy)
    app.mainloop()
