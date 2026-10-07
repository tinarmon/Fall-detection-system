"""Live biomechanical data recorder and session extractor for TrainStudio."""

from __future__ import annotations

import datetime
import logging
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pandas as pd

from src.fall_detection.config import GLOBAL_CONFIG
from src.fall_detection.geometry import calculate_angle_3d
from src.fall_detection.pose import PoseEstimator

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "timestamp",
    "subject_id",
    "input_source",
    "label",
    "left_angle",
    "right_angle",
    "x11",
    "y11",
    "z11",
    "x12",
    "y12",
    "z12",
    "x23",
    "y23",
    "z23",
    "x24",
    "y24",
    "z24",
    "x25",
    "y25",
    "z25",
    "x26",
    "y26",
    "z26",
]


class StudioSessionRecorder:
    """Extracts 3D pose landmarks and records labeled biomechanical time-series data."""

    def __init__(self, subject_id: str = "Subject_01", input_source: str = "webcam_0"):
        self.subject_id = subject_id
        self.input_source = input_source
        self.pose_estimator = PoseEstimator()
        self.is_recording = False
        self.current_label = 0  # 0: Normal / ADL, 1: Fall / Pre-fall
        self.recorded_rows: list[list[Any]] = []
        self.total_frames_processed = 0

        # Live telemetry metrics
        self.recording_start_time: float = 0.0
        self.last_angle_time: float = 0.0
        self.last_left_angle: float = 180.0
        self.last_right_angle: float = 180.0
        self.angular_velocity: float = 0.0
        self._fps_window: list[float] = []

    def process_frame(
        self, frame: np.ndarray, active_label: int | None = None
    ) -> tuple[np.ndarray, bool, dict[str, Any]]:
        """Processes a single frame, extracts features, and records if recording is active."""
        now = time.time()
        self.total_frames_processed += 1
        label_to_record = self.current_label if active_label is None else active_label

        annotated_frame, points_px, points_norm, points_world = self.pose_estimator.process_frame(
            frame, draw=True
        )

        required_landmarks = [11, 12, 23, 24, 25, 26]
        joint_health = {k: (k in points_norm) for k in required_landmarks}
        has_all_required = all(joint_health.values())

        left_angle = 180.0
        right_angle = 180.0
        ang_vel = 0.0

        if has_all_required:
            if all(k in points_world for k in [11, 23, 25]):
                left_angle = calculate_angle_3d(
                    points_world[11], points_world[23], points_world[25]
                )
            if all(k in points_world for k in [12, 24, 26]):
                right_angle = calculate_angle_3d(
                    points_world[12], points_world[24], points_world[26]
                )

            # Compute real-time angular velocity (deg/sec)
            dt = now - self.last_angle_time
            if 0.005 < dt < 0.5:
                delta_l = abs(left_angle - self.last_left_angle)
                delta_r = abs(right_angle - self.last_right_angle)
                ang_vel = max(delta_l, delta_r) / dt
                self.angular_velocity = float(0.7 * self.angular_velocity + 0.3 * ang_vel)

            self.last_left_angle = left_angle
            self.last_right_angle = right_angle
            self.last_angle_time = now

            rel_features = self.pose_estimator.get_relative_features(points_norm)

            if self.is_recording and rel_features is not None and len(rel_features) == 18:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                left_angle_rad = float(np.radians(left_angle))
                right_angle_rad = float(np.radians(right_angle))

                row = [
                    now_str,
                    self.subject_id,
                    self.input_source,
                    int(label_to_record),
                    left_angle_rad,
                    right_angle_rad,
                ] + [float(val) for val in rel_features]

                self.recorded_rows.append(row)

        # Elapsed time & samples per second
        elapsed_sec = (now - self.recording_start_time) if self.is_recording else 0.0
        recorded_total = len(self.recorded_rows)
        smp_per_sec = (
            (recorded_total / elapsed_sec) if (self.is_recording and elapsed_sec > 0.5) else 0.0
        )

        normal_count = sum(1 for r in self.recorded_rows if r[3] == 0)
        fall_count = sum(1 for r in self.recorded_rows if r[3] == 1)

        telemetry = {
            "valid_pose": has_all_required,
            "joint_health": joint_health,
            "left_angle": left_angle,
            "right_angle": right_angle,
            "angular_velocity": self.angular_velocity,
            "label": label_to_record,
            "is_recording": self.is_recording,
            "elapsed_seconds": elapsed_sec,
            "samples_per_second": smp_per_sec,
            "recorded_count": recorded_total,
            "normal_count": normal_count,
            "fall_count": fall_count,
        }

        # Draw interactive TrainStudio HUD overlay on frame
        self._render_studio_hud(annotated_frame, telemetry)

        return annotated_frame, has_all_required, telemetry

    def start_recording(self, label: int = 0) -> None:
        """Starts capturing frames into session buffer."""
        self.current_label = label
        self.is_recording = True
        self.recording_start_time = time.time()
        logger.info(f"TrainStudio: Started recording with default label {label}")

    def stop_recording(self) -> int:
        """Stops capturing frames and returns number of recorded samples."""
        self.is_recording = False
        logger.info(f"TrainStudio: Stopped recording. Total samples: {len(self.recorded_rows)}")
        return len(self.recorded_rows)

    def clear_buffer(self) -> None:
        """Clears in-memory session rows."""
        self.recorded_rows.clear()
        self.recording_start_time = 0.0

    def save_session(self, output_dir: Path | None = None, session_name: str | None = None) -> Path:
        """Persists recorded rows to session CSV file in standard schema."""
        if not self.recorded_rows:
            raise ValueError("No recorded data to save in this session")

        target_dir = output_dir or GLOBAL_CONFIG.clean_data_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if session_name:
            filename = f"session_{session_name}_{timestamp_str}.csv"
        else:
            filename = f"session_{self.subject_id}_{timestamp_str}.csv"

        filepath = target_dir / filename
        df = pd.DataFrame(self.recorded_rows, columns=FEATURE_COLUMNS)
        df.to_csv(filepath, index=False)
        logger.info(f"TrainStudio: Saved {len(df)} samples to {filepath}")
        return filepath

    def _render_studio_hud(self, frame: np.ndarray, telemetry: dict[str, Any]) -> None:
        """Renders TrainStudio status indicators and angle telemetry on OpenCV frame."""
        h, w = frame.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX

        # Top status bar
        if self.is_recording:
            bar_color = (0, 0, 180) if telemetry["label"] == 1 else (0, 140, 0)
            elapsed_m, elapsed_s = divmod(int(telemetry["elapsed_seconds"]), 60)
            elapsed_ms = int(
                (telemetry["elapsed_seconds"] - int(telemetry["elapsed_seconds"])) * 10
            )
            rec_status = (
                f"● REC [{'FALL (1)' if telemetry['label'] == 1 else 'NORMAL (0)'}] "
                f"⏱ {elapsed_m:02d}:{elapsed_s:02d}.{elapsed_ms} | {telemetry['samples_per_second']:.1f} smp/s"
            )
        else:
            bar_color = (25, 25, 30)
            rec_status = "○ READY — Press [Space] or click Record"

        cv2.rectangle(frame, (0, 0), (w, 36), bar_color, -1)
        cv2.putText(frame, rec_status, (15, 24), font, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

        # Pose validity indicator
        val_text = "POSE: OK" if telemetry["valid_pose"] else "POSE: ADJUST BODY"
        val_color = (0, 255, 0) if telemetry["valid_pose"] else (0, 165, 255)
        cv2.putText(frame, val_text, (w - 180, 24), font, 0.5, val_color, 2, cv2.LINE_AA)

        # Bottom telemetry box
        panel_w, panel_h = 320, 85
        px, py = 15, h - panel_h - 15
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, py), (px + panel_w, py + panel_h), (15, 15, 20), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
        cv2.rectangle(frame, (px, py), (px + panel_w, py + panel_h), (80, 80, 85), 1)

        cv2.putText(
            frame,
            f"L-Ang: {telemetry['left_angle']:.1f}° | R-Ang: {telemetry['right_angle']:.1f}° | Vel: {telemetry['angular_velocity']:.0f}°/s",
            (px + 10, py + 24),
            font,
            0.42,
            (240, 240, 245),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Samples: {telemetry['recorded_count']} (Norm: {telemetry['normal_count']} | Fall: {telemetry['fall_count']})",
            (px + 10, py + 52),
            font,
            0.42,
            (0, 255, 200),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Speed: {telemetry['samples_per_second']:.1f} samples/sec (20 vars)",
            (px + 10, py + 74),
            font,
            0.38,
            (160, 160, 170),
            1,
            cv2.LINE_AA,
        )
