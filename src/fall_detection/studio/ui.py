"""Modern CustomTkinter GUI for TrainStudio with stable video blitting, hotkeys, instructions, and live rate telemetry."""

from __future__ import annotations

import glob
import logging
import os
import re
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
import cv2

from src.fall_detection.studio.augmentation import DatasetAugmentor
from src.fall_detection.studio.recorder import StudioSessionRecorder
from src.fall_detection.studio.trainer import ModelTrainer
from src.fall_detection.ui.components import convert_cv2_to_tk_image

logger = logging.getLogger(__name__)


class TrainStudioHelpDialog(ctk.CTkToplevel):
    """Interactive help and instructions dialog for TrainStudio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("📖 TrainStudio User Guide & Instructions")
        self.geometry("800x640")
        self.minsize(720, 540)

        # Center on screen
        self.update_idletasks()
        self.lift()
        self.focus_set()

        self._create_ui()

    def _create_ui(self) -> None:
        # Header banner
        header = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            header,
            text="🎓 Pre-Fall TrainStudio — Step-by-Step Guide",
            font=("Segoe UI", 18, "bold"),
            text_color="#38bdf8",
        ).pack(side="left", padx=20, pady=15)

        # Content container
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=15)

        # Section 1: 20 Variable Biomechanical Telemetry
        self._add_section(
            scroll,
            "1. 🧠 20 Biomechanical Variables Recorded",
            "TrainStudio extracts exactly 20 numeric kinematic features on every valid frame:\n"
            "• 2 Angles: left_angle & right_angle (3D torso-hip-knee planar angles in radians)\n"
            "• 18 Coordinates: Torso-centered and scaled relative (x, y, z) for 6 key joints:\n"
            "   - Shoulders: Left Shoulder [11] (x,y,z), Right Shoulder [12] (x,y,z)\n"
            "   - Hips: Left Hip [23] (x,y,z), Right Hip [24] (x,y,z)\n"
            "   - Knees: Left Knee [25] (x,y,z), Right Knee [26] (x,y,z)\n"
            "• Metadata Columns: timestamp, subject_id, input_source, label (Total 24 CSV columns).\n"
            "• Sequential GRU Input: 10 sliding time-steps x 20 features per decision window.",
        )

        # Section 2: Data Collection & Pose Setup
        self._add_section(
            scroll,
            "2. 📹 Body Posture & Camera Positioning",
            "• Position your camera so that your entire upper body, hips, and knees are in frame.\n"
            "• Look at the top-right indicator: it will display 'POSE: OK' (green) when all 6 required\n"
            "  biomechanical landmarks (shoulders [11, 12], hips [23, 24], knees [25, 26]) are clearly detected.\n"
            "• If 'POSE: ADJUST BODY' appears (orange), step back or adjust camera tilt so your hips and knees are visible.",
        )

        # Section 3: Labeling Activities
        self._add_section(
            scroll,
            "3. 🏷️ Normal (0) vs Fall (1) Labeling",
            "• Normal / ADL Activities [Label 0]:\n"
            "  Standing, walking, turning, sitting down, standing up, bending to pick an object, stretching.\n"
            "• Fall / Pre-fall Activities [Label 1]:\n"
            "  Simulated tripping, slipping, sudden loss of balance, backward/forward tilting, stumbling.\n"
            "• Tip: Record varied angles, lighting, and distances for each activity to improve AI generalization.",
        )

        # Section 4: Keyboard Shortcuts Table
        self._add_hotkeys_table(scroll)

        # Section 5: Dataset & Augmentation
        self._add_section(
            scroll,
            "5. 📊 Dataset Management & Augmentation",
            "• After recording sessions, go to the '📊 Dataset & Augment' tab.\n"
            "• Open CSV files directly in Excel or Notepad using '📂 Open CSV' to inspect rows.\n"
            "• Check the Fall Ratio percentage. If you have fewer Fall samples than Normal samples,\n"
            "  click '✨ 1-Click Auto-Balance Dataset' to generate jittered and scaled variations.\n"
            "• Delete single bad sessions or select multiple sessions for mass deletion.",
        )

        # Section 6: Model Retraining & Deployment
        self._add_section(
            scroll,
            "6. 🚀 1-Click Retraining & Live Deployment",
            "• Switch to the '🚀 Train & Deploy' tab.\n"
            "• Choose epochs (25-30 recommended) and click '🚀 Start Training & Export TFLite'.\n"
            "• The trainer runs in the background and automatically evaluates validation accuracy & loss.\n"
            "• Once training completes, both assets/fall_model.keras and assets/fall_model.tflite are updated.\n"
            "• The live 4-camera monitoring grid will automatically use the newly trained high-speed model!",
        )

        # Close button
        ctk.CTkButton(
            self,
            text="Got It / Close",
            command=self.destroy,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            width=140,
        ).pack(pady=(0, 15))

    def _add_section(self, parent, title: str, content: str) -> None:
        card = ctk.CTkFrame(parent, fg_color="#1e293b", corner_radius=8)
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color="#f8fafc",
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 4))

        ctk.CTkLabel(
            card,
            text=content,
            font=("Segoe UI", 12),
            text_color="#cbd5e1",
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=15, pady=(0, 10))

    def _add_hotkeys_table(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color="#1e293b", corner_radius=8)
        card.pack(fill="x", pady=6)

        ctk.CTkLabel(
            card,
            text="4. ⌨️ Complete Keyboard Shortcuts Reference",
            font=("Segoe UI", 14, "bold"),
            text_color="#f8fafc",
            anchor="w",
        ).pack(fill="x", padx=15, pady=(10, 6))

        shortcuts = [
            ("[C] / [c]", "Toggle Camera ON / OFF"),
            ("[Space]", "Toggle Start / Stop Session Recording"),
            ("[N] / [n]", "Tag Active Label as Normal / ADL (0)"),
            ("[F] / [f]", "Tag Active Label as Fall / Pre-fall (1)"),
            ("[Ctrl + S]", "Save Recorded Session to Dataset CSV"),
            ("[Delete]", "Clear Recorded In-Memory Buffer"),
            ("[F1] / [?]", "Open this Instructions Guide"),
            ("[1], [2], [3]", "Fast Switch between Studio Tabs"),
        ]

        table_frame = ctk.CTkFrame(card, fg_color="#0f172a", corner_radius=6)
        table_frame.pack(fill="x", padx=15, pady=(0, 10))

        for key, desc in shortcuts:
            row = ctk.CTkFrame(table_frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)

            lbl_key = ctk.CTkLabel(
                row,
                text=key,
                font=("Consolas", 12, "bold"),
                text_color="#38bdf8",
                width=120,
                anchor="w",
            )
            lbl_key.pack(side="left")

            lbl_desc = ctk.CTkLabel(
                row,
                text=desc,
                font=("Segoe UI", 12),
                text_color="#e2e8f0",
                anchor="w",
            )
            lbl_desc.pack(side="left", padx=10)


class TrainStudioApp(ctk.CTkToplevel):
    """Integrated TrainStudio window for recording, augmenting, and retraining fall models."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("🎓 Pre-Fall TrainStudio — Data Collection & Model Training")
        self.geometry("1200x780")
        self.minsize(1020, 680)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.recorder = StudioSessionRecorder()
        self.augmentor = DatasetAugmentor()
        self.trainer = ModelTrainer()

        self.cap: cv2.VideoCapture | None = None
        self.is_camera_active = False
        self.camera_thread: threading.Thread | None = None
        self._latest_processed_frame = None
        self._latest_telemetry: dict[str, Any] = {}
        self._frame_lock = threading.Lock()

        # Selection state for dataset files
        self.selected_files: dict[str, ctk.BooleanVar] = {}

        self._create_ui()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start GUI video render loop
        self._render_loop()

        # Automatically discover connected cameras
        self.after(80, self._rescan_cameras)

    def _create_ui(self) -> None:
        # Top Header Bar
        top_bar = ctk.CTkFrame(self, height=48, fg_color="#18181b", corner_radius=0)
        top_bar.pack(fill="x", padx=0, pady=0)

        # Left branding
        lbl_title = ctk.CTkLabel(
            top_bar,
            text="🎓 PRE-FALL TRAINSTUDIO",
            font=("Segoe UI", 16, "bold"),
            text_color="#38bdf8",
        )
        lbl_title.pack(side="left", padx=(15, 10))

        lbl_sub = ctk.CTkLabel(
            top_bar,
            text="Biomechanical 20-Variable Data Studio & AI Retrainer",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
        )
        lbl_sub.pack(side="left")

        # Right Help & Guide Button
        btn_help = ctk.CTkButton(
            top_bar,
            text="❔ Instructions & Guide (F1)",
            command=self.open_instructions,
            fg_color="#334155",
            hover_color="#475569",
            width=180,
            font=("Segoe UI", 12, "bold"),
        )
        btn_help.pack(side="right", padx=15, pady=8)

        # Main Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=(8, 12))

        self.tab_record = self.tabview.add("📹 Record & Label")
        self.tab_dataset = self.tabview.add("📊 Dataset & Augment")
        self.tab_train = self.tabview.add("🚀 Train & Deploy")

        self._build_record_tab()
        self._build_dataset_tab()
        self._build_train_tab()

    # --------------------------------------------------------------------------
    # Tab 1: Record & Label
    # --------------------------------------------------------------------------
    def _build_record_tab(self) -> None:
        # Right: Control Panel (Packed FIRST with fixed width to lock geometry)
        right_panel = ctk.CTkFrame(self.tab_record, width=380, fg_color="#18181b")
        right_panel.pack(side="right", fill="y", padx=(4, 8), pady=8)
        right_panel.pack_propagate(False)

        # Left: Video Feed Container (Packed SECOND, fill="both", expand=True)
        left_frame = ctk.CTkFrame(self.tab_record, fg_color="#09090b", corner_radius=8)
        left_frame.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=8)
        left_frame.pack_propagate(False)

        # Dedicated Video Viewport with pack_propagate(False)
        self.video_container = tk.Frame(left_frame, bg="#09090b")
        self.video_container.pack(fill="both", expand=True, padx=6, pady=6)
        self.video_container.pack_propagate(False)

        self.video_label = tk.Label(
            self.video_container,
            text="Camera is Offline\n\nClick '▶ Start Camera' or press [C] to begin",
            font=("Segoe UI", 14),
            bg="#09090b",
            fg="#94a3b8",
        )
        self.video_label.pack(fill="both", expand=True)

        # ---------------- Right Control Panel Layout ----------------
        scroll_right = ctk.CTkScrollableFrame(right_panel, fg_color="transparent")
        scroll_right.pack(fill="both", expand=True, padx=8, pady=6)

        ctk.CTkLabel(
            scroll_right, text="Data Capture & Labeling", font=("Segoe UI", 15, "bold")
        ).pack(pady=(4, 6))

        # Subject & Source
        self.subject_entry = ctk.CTkEntry(
            scroll_right, placeholder_text="Subject ID (e.g. Subject_A)"
        )
        self.subject_entry.insert(0, "Subject_A")
        self.subject_entry.pack(fill="x", padx=10, pady=3)

        source_bar = ctk.CTkFrame(scroll_right, fg_color="transparent")
        source_bar.pack(fill="x", padx=10, pady=3)

        self.source_combo = ctk.CTkComboBox(
            source_bar,
            values=["Webcam 0 (Default)", "Select Video File..."],
        )
        self.source_combo.set("Webcam 0 (Default)")
        self.source_combo.pack(side="left", fill="x", expand=True)

        self.btn_rescan_cam = ctk.CTkButton(
            source_bar,
            text="🔄",
            width=36,
            command=self._rescan_cameras,
            fg_color="#334155",
            hover_color="#475569",
        )
        self.btn_rescan_cam.pack(side="right", padx=(6, 0))

        # Camera Toggle
        self.btn_cam_toggle = ctk.CTkButton(
            scroll_right,
            text="▶ Start Camera [C]",
            command=self._toggle_camera,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=("Segoe UI", 13, "bold"),
        )
        self.btn_cam_toggle.pack(fill="x", padx=10, pady=(6, 4))

        # Label Selection
        ctk.CTkLabel(scroll_right, text="Active Label Tag:", font=("Segoe UI", 13, "bold")).pack(
            pady=(8, 2)
        )

        self.label_var = ctk.StringVar(value="0")
        label_frame = ctk.CTkFrame(scroll_right, fg_color="transparent")
        label_frame.pack(fill="x", padx=10, pady=2)

        self.rad_normal = ctk.CTkRadioButton(
            label_frame,
            text="Normal [N] (0)",
            variable=self.label_var,
            value="0",
            font=("Segoe UI", 12, "bold"),
        )
        self.rad_normal.pack(side="left", padx=5)

        self.rad_fall = ctk.CTkRadioButton(
            label_frame,
            text="Fall [F] (1)",
            variable=self.label_var,
            value="1",
            font=("Segoe UI", 12, "bold"),
            text_color="#f87171",
        )
        self.rad_fall.pack(side="left", padx=15)

        # Auto-Stop Timer Option
        timer_frame = ctk.CTkFrame(scroll_right, fg_color="#09090b", corner_radius=6)
        timer_frame.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(timer_frame, text="⏱ Auto-Stop Timer:", font=("Segoe UI", 11, "bold")).pack(
            side="left", padx=8, pady=4
        )
        self.combo_timer = ctk.CTkComboBox(
            timer_frame,
            values=["Continuous (Manual)", "5 Seconds", "10 Seconds", "15 Seconds", "30 Seconds"],
            width=160,
        )
        self.combo_timer.set("Continuous (Manual)")
        self.combo_timer.pack(side="right", padx=8, pady=4)

        # Record Actions
        self.btn_record = ctk.CTkButton(
            scroll_right,
            text="● Start Session Record [Space]",
            command=self._toggle_recording,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=("Segoe UI", 13, "bold"),
        )
        self.btn_record.pack(fill="x", padx=10, pady=(8, 4))

        self.btn_save = ctk.CTkButton(
            scroll_right,
            text="💾 Save Session [Ctrl+S]",
            command=self._save_recorded_session,
            fg_color="#059669",
            hover_color="#047857",
            font=("Segoe UI", 12, "bold"),
        )
        self.btn_save.pack(fill="x", padx=10, pady=3)

        self.btn_clear = ctk.CTkButton(
            scroll_right,
            text="🗑️ Clear Buffer [Del]",
            command=self._clear_recorded_session,
            fg_color="#475569",
            hover_color="#334155",
        )
        self.btn_clear.pack(fill="x", padx=10, pady=3)

        # ---------------- Live Telemetry Dashboard Card ----------------
        telemetry_card = ctk.CTkFrame(scroll_right, fg_color="#09090b", corner_radius=8)
        telemetry_card.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(
            telemetry_card,
            text="📊 Live Data Counters & Telemetry",
            font=("Segoe UI", 12, "bold"),
            text_color="#38bdf8",
        ).pack(anchor="w", padx=10, pady=(6, 2))

        # Big Stopwatch & Rate display
        self.lbl_stopwatch = ctk.CTkLabel(
            telemetry_card,
            text="⏱ 00:00.0s  |  0.0 smp/s",
            font=("Consolas", 15, "bold"),
            text_color="#f8fafc",
        )
        self.lbl_stopwatch.pack(padx=10, pady=2)

        # Samples breakdown
        self.lbl_samples_breakdown = ctk.CTkLabel(
            telemetry_card,
            text="Total: 0 frames\n🟢 Normal: 0 (0%)  |  🔴 Fall: 0 (0%)",
            font=("Segoe UI", 11),
            text_color="#94a3b8",
            justify="center",
        )
        self.lbl_samples_breakdown.pack(padx=10, pady=2)

        # Kinematics readouts (Angles & Velocity)
        self.lbl_kinematics = ctk.CTkLabel(
            telemetry_card,
            text="Angles: L: --° | R: --°\nVelocity: 0 °/s",
            font=("Segoe UI", 11),
            text_color="#38bdf8",
            justify="center",
        )
        self.lbl_kinematics.pack(padx=10, pady=(2, 6))

        # Hotkey Help card
        help_card = ctk.CTkFrame(scroll_right, fg_color="#0f172a", corner_radius=6)
        help_card.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(
            help_card,
            text="💡 [C] Cam | [Space] Record\n[N] Normal | [F] Fall | [Ctrl+S] Save",
            font=("Segoe UI", 11),
            text_color="#94a3b8",
            justify="center",
        ).pack(padx=8, pady=6)

    # --------------------------------------------------------------------------
    # Tab 2: Dataset & Augmentation (with Open, Delete, and Mass Delete)
    # --------------------------------------------------------------------------
    def _build_dataset_tab(self) -> None:
        top_stats = ctk.CTkFrame(self.tab_dataset, fg_color="#18181b")
        top_stats.pack(fill="x", padx=10, pady=8)

        self.lbl_dataset_summary = ctk.CTkLabel(
            top_stats,
            text="Dataset Summary: Loading...",
            font=("Segoe UI", 14, "bold"),
            justify="left",
            text_color="#38bdf8",
        )
        self.lbl_dataset_summary.pack(side="left", padx=15, pady=10)

        btn_refresh = ctk.CTkButton(
            top_stats, text="🔄 Refresh", width=90, command=self._refresh_dataset_view
        )
        btn_refresh.pack(side="right", padx=(5, 15), pady=10)

        btn_open_folder = ctk.CTkButton(
            top_stats,
            text="📁 Open Folder",
            width=110,
            command=self._open_dataset_folder,
            fg_color="#334155",
            hover_color="#475569",
        )
        btn_open_folder.pack(side="right", padx=5, pady=10)

        # Action Toolbar (Auto-balance, Mass Delete, Select All)
        action_bar = ctk.CTkFrame(self.tab_dataset, fg_color="transparent")
        action_bar.pack(fill="x", padx=10, pady=4)

        self.btn_auto_balance = ctk.CTkButton(
            action_bar,
            text="✨ 1-Click Auto-Balance Dataset (Minority Fall Augmentation)",
            command=self._auto_balance_dataset,
            fg_color="#7c3aed",
            hover_color="#6d28d9",
            font=("Segoe UI", 12, "bold"),
        )
        self.btn_auto_balance.pack(side="left", padx=4)

        btn_select_all = ctk.CTkButton(
            action_bar,
            text="☑ Select All",
            width=95,
            command=self._select_all_files,
            fg_color="#334155",
            hover_color="#475569",
        )
        btn_select_all.pack(side="left", padx=4)

        btn_delete_selected = ctk.CTkButton(
            action_bar,
            text="🗑️ Delete Selected",
            width=130,
            command=self._delete_selected_files,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=("Segoe UI", 12, "bold"),
        )
        btn_delete_selected.pack(side="left", padx=4)

        btn_del_augmented = ctk.CTkButton(
            action_bar,
            text="🧹 Delete All Augmented (*_aug_*)",
            width=190,
            command=self._delete_all_augmented_files,
            fg_color="#b45309",
            hover_color="#92400e",
        )
        btn_del_augmented.pack(side="right", padx=4)

        # File list scrollable frame
        self.file_scroll = ctk.CTkScrollableFrame(
            self.tab_dataset,
            label_text="Recorded Session CSV Files (20 Variables)",
            fg_color="#09090b",
        )
        self.file_scroll.pack(fill="both", expand=True, padx=10, pady=8)
        self._refresh_dataset_view()

    # --------------------------------------------------------------------------
    # Tab 3: Train & Deploy
    # --------------------------------------------------------------------------
    def _build_train_tab(self) -> None:
        left_ctrl = ctk.CTkFrame(self.tab_train, width=340, fg_color="#18181b")
        left_ctrl.pack(side="left", fill="y", padx=10, pady=10)
        left_ctrl.pack_propagate(False)

        ctk.CTkLabel(left_ctrl, text="Training Configuration", font=("Segoe UI", 16, "bold")).pack(
            pady=(10, 8)
        )

        ctk.CTkLabel(left_ctrl, text="Epochs:").pack(anchor="w", padx=15)
        self.epochs_slider = ctk.CTkSlider(left_ctrl, from_=5, to=100, number_of_steps=19)
        self.epochs_slider.set(25)
        self.epochs_slider.pack(fill="x", padx=15, pady=2)
        self.lbl_epochs_val = ctk.CTkLabel(left_ctrl, text="25 Epochs", font=("Segoe UI", 11))
        self.lbl_epochs_val.pack(anchor="w", padx=15)
        self.epochs_slider.configure(
            command=lambda v: self.lbl_epochs_val.configure(text=f"{int(v)} Epochs")
        )

        ctk.CTkLabel(left_ctrl, text="Batch Size:").pack(anchor="w", padx=15, pady=(8, 0))
        self.batch_combo = ctk.CTkComboBox(left_ctrl, values=["16", "32", "64"])
        self.batch_combo.set("32")
        self.batch_combo.pack(fill="x", padx=15, pady=2)

        ctk.CTkLabel(left_ctrl, text="GRU Units:").pack(anchor="w", padx=15, pady=(8, 0))
        self.gru_entry = ctk.CTkEntry(left_ctrl)
        self.gru_entry.insert(0, "64,32")
        self.gru_entry.pack(fill="x", padx=15, pady=2)

        self.btn_start_train = ctk.CTkButton(
            left_ctrl,
            text="🚀 Start Training & Export TFLite",
            command=self._start_training,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=("Segoe UI", 13, "bold"),
        )
        self.btn_start_train.pack(fill="x", padx=15, pady=(20, 8))

        # Right: Progress & Metrics
        right_panel = ctk.CTkFrame(self.tab_train, fg_color="#18181b")
        right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            right_panel, text="Training Progress & Validation Logs", font=("Segoe UI", 16, "bold")
        ).pack(pady=(10, 5))

        self.train_progress = ctk.CTkProgressBar(right_panel)
        self.train_progress.set(0)
        self.train_progress.pack(fill="x", padx=20, pady=8)

        self.lbl_train_status = ctk.CTkLabel(
            right_panel, text="Status: Ready to train", font=("Segoe UI", 12), text_color="#38bdf8"
        )
        self.lbl_train_status.pack(pady=4)

        self.txt_logs = ctk.CTkTextbox(right_panel, height=280, font=("Consolas", 11))
        self.txt_logs.pack(fill="both", expand=True, padx=20, pady=10)

    # --------------------------------------------------------------------------
    # Keyboard Shortcuts Engine
    # --------------------------------------------------------------------------
    def _bind_shortcuts(self) -> None:
        self.bind("<space>", lambda e: self._toggle_recording())
        self.bind("<Key-c>", lambda e: self._toggle_camera())
        self.bind("<Key-C>", lambda e: self._toggle_camera())
        self.bind("<Key-n>", lambda e: self.label_var.set("0"))
        self.bind("<Key-N>", lambda e: self.label_var.set("0"))
        self.bind("<Key-f>", lambda e: self.label_var.set("1"))
        self.bind("<Key-F>", lambda e: self.label_var.set("1"))
        self.bind("<Control-s>", lambda e: self._save_recorded_session())
        self.bind("<Control-S>", lambda e: self._save_recorded_session())
        self.bind("<Delete>", lambda e: self._clear_recorded_session())
        self.bind("<F1>", lambda e: self.open_instructions())
        self.bind("<question>", lambda e: self.open_instructions())

        # Tab hotkeys
        self.bind("<Key-1>", lambda e: self.tabview.set("📹 Record & Label"))
        self.bind("<Key-2>", lambda e: self.tabview.set("📊 Dataset & Augment"))
        self.bind("<Key-3>", lambda e: self.tabview.set("🚀 Train & Deploy"))

    def open_instructions(self) -> None:
        """Opens the step-by-step Help & Instructions modal dialog."""
        TrainStudioHelpDialog(self)

    # --------------------------------------------------------------------------
    # Camera Stream & Decoupled Render Loop
    # --------------------------------------------------------------------------
    def _rescan_cameras(self) -> None:
        """Asynchronously discovers attached cameras and updates the source combobox."""
        if hasattr(self, "btn_rescan_cam"):
            self.btn_rescan_cam.configure(text="⏳", state="disabled")

        def worker():
            from src.fall_detection.camera import CameraMonitor

            info = CameraMonitor.detect_available_cameras_info()

            def update_ui():
                choices = []
                if info:
                    for c in info:
                        choices.append(
                            f"Webcam {c['index']} ({c.get('resolution', '')} - Detected)"
                        )
                else:
                    choices.append("Webcam 0 (Default)")

                choices.append("Select Video File...")
                self.source_combo.configure(values=choices)

                curr = self.source_combo.get()
                if "Scanning" in curr or (
                    choices
                    and not any(curr.startswith(c.split()[0]) for c in choices if "Webcam" in c)
                ):
                    self.source_combo.set(choices[0])

                if hasattr(self, "btn_rescan_cam"):
                    self.btn_rescan_cam.configure(text="🔄", state="normal")

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_camera(self) -> None:
        if self.is_camera_active:
            self._stop_camera()
        else:
            self._start_camera()

    def _start_camera(self) -> None:
        src_val = self.source_combo.get()
        if "Select Video" in src_val:
            fpath = filedialog.askopenfilename(
                filetypes=[("Video files", "*.mp4;*.avi;*.mov;*.mkv")]
            )
            if not fpath:
                return
            cam_idx: int | str = fpath
        else:
            match = re.search(r"Webcam\s+(\d+)", src_val)
            if match:
                cam_idx = int(match.group(1))
            elif "Webcam 1" in src_val:
                cam_idx = 1
            else:
                cam_idx = 0

        # Open camera using DirectShow backend on Windows to prevent MSMF hangs
        if isinstance(cam_idx, int) and os.name == "nt":
            self.cap = cv2.VideoCapture(cam_idx, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(cam_idx)
        else:
            self.cap = cv2.VideoCapture(cam_idx)

        if not self.cap or not self.cap.isOpened():
            self.video_label.configure(
                text=f"Failed to open video source: {src_val}\nCheck camera connection or permissions."
            )
            return

        self.is_camera_active = True
        self.btn_cam_toggle.configure(
            text="⏹ Stop Camera [C]", fg_color="#dc2626", hover_color="#b91c1c"
        )
        self.recorder.subject_id = self.subject_entry.get().strip() or "Subject"
        self.recorder.input_source = str(cam_idx)

        self.camera_thread = threading.Thread(
            target=self._camera_stream_worker, name="StudioWorker", daemon=True
        )
        self.camera_thread.start()

    def _stop_camera(self) -> None:
        self.is_camera_active = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_cam_toggle.configure(
            text="▶ Start Camera [C]", fg_color="#2563eb", hover_color="#1d4ed8"
        )
        self.video_label.configure(
            image="",
            text="Camera is Offline\n\nClick '▶ Start Camera' or press [C] to begin",
        )

    def _camera_stream_worker(self) -> None:
        """Background thread for camera capture & pose feature processing."""
        while self.is_camera_active and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            active_lbl = int(self.label_var.get())
            processed_frame, _valid_pose, telemetry = self.recorder.process_frame(
                frame, active_label=active_lbl
            )

            with self._frame_lock:
                self._latest_processed_frame = processed_frame
                self._latest_telemetry = telemetry

            time.sleep(0.01)

    def _render_loop(self) -> None:
        """Main UI render tick (30 FPS) updating the stable Tkinter video viewport and live counters."""
        if self.is_camera_active:
            with self._frame_lock:
                frame_to_draw = self._latest_processed_frame
                telemetry = self._latest_telemetry

            if frame_to_draw is not None:
                w = max(100, self.video_container.winfo_width())
                h = max(100, self.video_container.winfo_height())

                photo = convert_cv2_to_tk_image(frame_to_draw, target_width=w, target_height=h)
                if photo:
                    self.video_label.configure(image=photo, text="")
                    self.video_label.image = photo

                if telemetry:
                    # Update live stopwatch & rate
                    elapsed = telemetry.get("elapsed_seconds", 0.0)
                    smp_rate = telemetry.get("samples_per_second", 0.0)
                    em, es = divmod(int(elapsed), 60)
                    ems = int((elapsed - int(elapsed)) * 10)

                    self.lbl_stopwatch.configure(
                        text=f"⏱ {em:02d}:{es:02d}.{ems}  |  {smp_rate:.1f} smp/s"
                    )

                    # Update samples breakdown
                    total_smp = telemetry.get("recorded_count", 0)
                    n_cnt = telemetry.get("normal_count", 0)
                    f_cnt = telemetry.get("fall_count", 0)
                    n_pct = (n_cnt / total_smp * 100) if total_smp > 0 else 0.0
                    f_pct = (f_cnt / total_smp * 100) if total_smp > 0 else 0.0

                    self.lbl_samples_breakdown.configure(
                        text=f"Total: {total_smp} frames ({total_smp * 24 / 1024:.1f} KB)\n"
                        f"🟢 Normal: {n_cnt} ({n_pct:.1f}%)  |  🔴 Fall: {f_cnt} ({f_pct:.1f}%)"
                    )

                    # Update kinematics
                    l_ang = telemetry.get("left_angle", 180.0)
                    r_ang = telemetry.get("right_angle", 180.0)
                    ang_v = telemetry.get("angular_velocity", 0.0)
                    self.lbl_kinematics.configure(
                        text=f"Angles: L: {l_ang:.1f}° | R: {r_ang:.1f}°\nAngular Speed: {ang_v:.0f} °/s"
                    )

                    # Auto-stop timer check
                    if self.recorder.is_recording:
                        timer_val = self.combo_timer.get()
                        limit_sec = 0.0
                        if "5 Second" in timer_val:
                            limit_sec = 5.0
                        elif "10 Second" in timer_val:
                            limit_sec = 10.0
                        elif "15 Second" in timer_val:
                            limit_sec = 15.0
                        elif "30 Second" in timer_val:
                            limit_sec = 30.0

                        if limit_sec > 0 and elapsed >= limit_sec:
                            self._toggle_recording()

        self.after(33, self._render_loop)

    # --------------------------------------------------------------------------
    # Recording & Dataset Handlers
    # --------------------------------------------------------------------------
    def _toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self.recorder.stop_recording()
            self.btn_record.configure(
                text="● Start Session Record [Space]",
                fg_color="#dc2626",
                hover_color="#b91c1c",
            )
        else:
            self.recorder.start_recording(label=int(self.label_var.get()))
            self.btn_record.configure(
                text="⏹ Stop Recording [Space]",
                fg_color="#eab308",
                hover_color="#ca8a04",
            )

    def _save_recorded_session(self) -> None:
        try:
            saved_file = self.recorder.save_session()
            self.lbl_samples_breakdown.configure(text=f"✅ Saved to: {saved_file.name}")
            self.recorder.clear_buffer()
            self._refresh_dataset_view()
        except Exception as ex:
            self.lbl_samples_breakdown.configure(text=f"❌ Save Error: {ex}")

    def _clear_recorded_session(self) -> None:
        self.recorder.clear_buffer()
        self.lbl_samples_breakdown.configure(text="Buffer cleared")

    def _open_dataset_folder(self) -> None:
        """Opens the target dataset directory in Windows Explorer."""
        target_dir = str(self.augmentor.target_dir)
        os.makedirs(target_dir, exist_ok=True)
        try:
            os.startfile(target_dir)
        except Exception as ex:
            messagebox.showerror("Error", f"Cannot open dataset folder: {ex}", parent=self)

    def _open_csv_file(self, fpath: str) -> None:
        """Opens the chosen CSV file in default system application (Excel/Notepad)."""
        if os.path.isfile(fpath):
            try:
                os.startfile(fpath)
            except Exception as ex:
                messagebox.showerror("Error", f"Cannot open CSV file: {ex}", parent=self)

    def _delete_single_file(self, fpath: str) -> None:
        """Prompts and deletes a single dataset CSV file."""
        fname = os.path.basename(fpath)
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete this session file?\n\n{fname}",
            parent=self,
        )
        if confirm and os.path.isfile(fpath):
            try:
                os.remove(fpath)
                self._refresh_dataset_view()
            except Exception as ex:
                messagebox.showerror("Delete Error", f"Failed to delete {fname}: {ex}", parent=self)

    def _delete_selected_files(self) -> None:
        """Mass deletes all checked CSV files."""
        to_delete = [fpath for fpath, var in self.selected_files.items() if var.get()]
        if not to_delete:
            messagebox.showinfo(
                "No Selection", "Please check at least one file to delete.", parent=self
            )
            return

        confirm = messagebox.askyesno(
            "Confirm Mass Delete",
            f"Are you sure you want to permanently delete {len(to_delete)} selected files?",
            parent=self,
        )
        if confirm:
            deleted_count = 0
            for fpath in to_delete:
                if os.path.isfile(fpath):
                    try:
                        os.remove(fpath)
                        deleted_count += 1
                    except Exception as ex:
                        logger.warning(f"Failed deleting {fpath}: {ex}")
            self._refresh_dataset_view()
            messagebox.showinfo(
                "Deleted", f"Successfully deleted {deleted_count} files.", parent=self
            )

    def _delete_all_augmented_files(self) -> None:
        """Deletes all generated augmented session files (*_aug_*.csv)."""
        pattern = str(self.augmentor.target_dir / "session_*_aug_*.csv")
        aug_files = glob.glob(pattern)
        if not aug_files:
            messagebox.showinfo("No Files", "No augmented files (*_aug_*.csv) found.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Delete Augmented",
            f"Found {len(aug_files)} augmented session files.\n\nDelete all augmented files?",
            parent=self,
        )
        if confirm:
            count = 0
            for f in aug_files:
                try:
                    os.remove(f)
                    count += 1
                except Exception:
                    pass
            self._refresh_dataset_view()
            messagebox.showinfo("Done", f"Deleted {count} augmented files.", parent=self)

    def _select_all_files(self) -> None:
        """Selects or deselects all files in the current view."""
        all_checked = (
            all(var.get() for var in self.selected_files.values()) if self.selected_files else False
        )
        new_state = not all_checked
        for var in self.selected_files.values():
            var.set(new_state)

    def _refresh_dataset_view(self) -> None:
        summary = self.augmentor.get_dataset_summary()
        self.lbl_dataset_summary.configure(
            text=f"Files: {summary['total_files']} | Total Samples: {summary['total_samples']:,} | "
            f"Normal: {summary['normal_samples']:,} | Fall: {summary['fall_samples']:,} "
            f"({summary['fall_ratio'] * 100:.1f}%)"
        )

        for widget in self.file_scroll.winfo_children():
            widget.destroy()

        self.selected_files.clear()

        for item in summary["files"]:
            fpath = item["path"]
            fname = item["filename"]
            var = ctk.BooleanVar(value=False)
            self.selected_files[fpath] = var

            row_frame = ctk.CTkFrame(self.file_scroll, fg_color="#18181b")
            row_frame.pack(fill="x", padx=5, pady=3)

            # Checkbox for mass delete selection
            chk = ctk.CTkCheckBox(row_frame, text="", variable=var, width=24)
            chk.pack(side="left", padx=(8, 4))

            # File name label
            ctk.CTkLabel(
                row_frame,
                text=fname,
                font=("Segoe UI", 12, "bold"),
                anchor="w",
                width=280,
            ).pack(side="left", padx=4)

            # Samples info
            ctk.CTkLabel(
                row_frame,
                text=f"{item['total_samples']} samples (Norm: {item['normal_samples']} | Fall: {item['fall_samples']})",
                font=("Segoe UI", 11),
                text_color="#94a3b8",
            ).pack(side="left", padx=8)

            # Action Buttons: Delete (Red), Open CSV (Blue), Augment (Purple)
            btn_del = ctk.CTkButton(
                row_frame,
                text="🗑️",
                width=36,
                command=lambda p=fpath: self._delete_single_file(p),
                fg_color="#dc2626",
                hover_color="#b91c1c",
            )
            btn_del.pack(side="right", padx=(2, 6))

            btn_open = ctk.CTkButton(
                row_frame,
                text="📂 Open CSV",
                width=85,
                command=lambda p=fpath: self._open_csv_file(p),
                fg_color="#334155",
                hover_color="#475569",
            )
            btn_open.pack(side="right", padx=3)

            btn_aug = ctk.CTkButton(
                row_frame,
                text="➕ Augment",
                width=80,
                command=lambda p=fpath: self._augment_single_file(p),
                fg_color="#7c3aed",
                hover_color="#6d28d9",
            )
            btn_aug.pack(side="right", padx=3)

    def _augment_single_file(self, fpath: str) -> None:
        self.augmentor.augment_file(fpath, num_variations=2)
        self._refresh_dataset_view()

    def _auto_balance_dataset(self) -> None:
        self.augmentor.auto_balance_dataset()
        self._refresh_dataset_view()

    def _start_training(self) -> None:
        epochs = int(self.epochs_slider.get())
        batch_size = int(self.batch_combo.get())
        gru_units = self.gru_entry.get().strip() or "64,32"

        self.btn_start_train.configure(state="disabled", text="⏳ Training in Progress...")
        self.txt_logs.delete("1.0", "end")
        self.txt_logs.insert("end", f"Starting training: {epochs} epochs, batch {batch_size}...\n")

        def _on_progress(epoch, total_epochs, loss, acc, val_loss, val_acc):
            progress_frac = epoch / float(total_epochs)
            self.after(
                0,
                lambda: (
                    self.train_progress.set(progress_frac),
                    self.lbl_train_status.configure(
                        text=f"Epoch {epoch}/{total_epochs} | Loss: {loss:.4f} | Acc: {acc * 100:.1f}% | Val Loss: {val_loss:.4f} | Val Acc: {val_acc * 100:.1f}%"
                    ),
                    self.txt_logs.insert(
                        "end",
                        f"Epoch {epoch:02d}/{total_epochs:02d} - loss: {loss:.4f} - acc: {acc:.4f} - val_loss: {val_loss:.4f} - val_acc: {val_acc:.4f}\n",
                    ),
                    self.txt_logs.see("end"),
                ),
            )

        def _on_complete(results):
            self.after(
                0,
                lambda: (
                    self.btn_start_train.configure(
                        state="normal", text="🚀 Start Training & Export TFLite"
                    ),
                    self.lbl_train_status.configure(
                        text=f"✅ Done! Validation Accuracy: {results['val_accuracy'] * 100:.2f}% | Model & TFLite Saved!",
                        text_color="#10b981",
                    ),
                    self.txt_logs.insert(
                        "end",
                        f"\n=== Training Complete ===\nValidation Accuracy: {results['val_accuracy'] * 100:.2f}%\nValidation Loss: {results['val_loss']:.4f}\nSaved Keras Model: {results['keras_path']}\nSaved TFLite Model: {results['tflite_path']}\n",
                    ),
                    self.txt_logs.see("end"),
                ),
            )

        def _on_error(ex):
            self.after(
                0,
                lambda: (
                    self.btn_start_train.configure(
                        state="normal", text="🚀 Start Training & Export TFLite"
                    ),
                    self.lbl_train_status.configure(
                        text=f"❌ Training Failed: {ex}", text_color="#ef4444"
                    ),
                    self.txt_logs.insert("end", f"\nERROR: {ex}\n"),
                ),
            )

        self.trainer.start_training_async(
            epochs=epochs,
            batch_size=batch_size,
            gru_units=gru_units,
            on_progress=_on_progress,
            on_complete=_on_complete,
            on_error=_on_error,
        )

    def _on_close(self) -> None:
        self._stop_camera()
        self.destroy()
