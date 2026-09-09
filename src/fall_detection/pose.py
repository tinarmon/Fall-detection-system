"""Pose landmark estimation and relative biomechanical feature extraction."""

from __future__ import annotations

from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from src.fall_detection.config import GLOBAL_CONFIG


class PoseEstimator:
    """Detects 3D pose landmarks and extracts normalized torso-relative feature vectors."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        min_detection_confidence: float | None = None,
        min_presence_confidence: float | None = None,
        min_tracking_confidence: float | None = None,
    ):
        asset_path = str(model_path or GLOBAL_CONFIG.pose_task_path)
        base_options = python.BaseOptions(model_asset_path=asset_path)

        det_conf = (
            min_detection_confidence
            if min_detection_confidence is not None
            else GLOBAL_CONFIG.min_detection_confidence
        )
        pres_conf = (
            min_presence_confidence
            if min_presence_confidence is not None
            else GLOBAL_CONFIG.min_presence_confidence
        )
        track_conf = (
            min_tracking_confidence
            if min_tracking_confidence is not None
            else GLOBAL_CONFIG.min_tracking_confidence
        )

        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=det_conf,
            min_pose_presence_confidence=pres_conf,
            min_tracking_confidence=track_conf,
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.target_landmarks = GLOBAL_CONFIG.target_landmarks
        self.connections = GLOBAL_CONFIG.connections

    def process_frame(
        self, frame: np.ndarray
    ) -> tuple[
        np.ndarray,
        dict[int, tuple[int, int]],
        dict[int, tuple[float, float, float]],
        dict[int, tuple[float, float, float]],
    ]:
        """Detects pose landmarks on a single video frame.

        Parameters:
            frame: BGR image array of shape (H, W, 3).

        Returns:
            Tuple of:
                - Annotated or original BGR frame array
                - points_px: mapping landmark_index -> (pixel_x, pixel_y)
                - points_norm: mapping landmark_index -> (norm_x, norm_y, norm_z)
                - points_world: mapping landmark_index -> (world_x, world_y, world_z) in meters
        """
        h, w = frame.shape[:2]

        if w > 640:
            scale = 640.0 / float(w)
            small_h = max(180, int(h * scale))
            detect_frame = cv2.resize(frame, (640, small_h), interpolation=cv2.INTER_LINEAR)
        else:
            detect_frame = frame

        image_rgb = cv2.cvtColor(detect_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = self.detector.detect(mp_image)

        points_px: dict[int, tuple[int, int]] = {}
        points_norm: dict[int, tuple[float, float, float]] = {}
        points_world: dict[int, tuple[float, float, float]] = {}

        if detection_result.pose_landmarks:
            landmarks = detection_result.pose_landmarks[0]
            world_landmarks = (
                detection_result.pose_world_landmarks[0]
                if detection_result.pose_world_landmarks
                else None
            )

            for idx in self.target_landmarks:
                lm = landmarks[idx]
                vis = getattr(lm, "visibility", None)
                if vis is None:
                    vis = getattr(lm, "presence", 1.0)

                if vis is None or vis > 0.5:
                    px, py = int(lm.x * w), int(lm.y * h)
                    points_px[idx] = (px, py)
                    points_norm[idx] = (float(lm.x), float(lm.y), float(lm.z))

                    if world_landmarks:
                        w_lm = world_landmarks[idx]
                        points_world[idx] = (float(w_lm.x), float(w_lm.y), float(w_lm.z))
                    else:
                        points_world[idx] = (float(lm.x), float(lm.y), float(lm.z))

                    cv2.circle(frame, (px, py), 8, (0, 255, 0), -1)

            for p1, p2 in self.connections:
                if p1 in points_px and p2 in points_px:
                    cv2.line(frame, points_px[p1], points_px[p2], (255, 200, 0), 3)

        return frame, points_px, points_norm, points_world

    @staticmethod
    def get_relative_features(points_norm: dict[int, tuple[float, float, float]]) -> list[float]:
        """Normalizes landmark coordinates relative to hip center and scales by torso length.

        Parameters:
            points_norm: Mapping of target landmark indices to normalized (x, y, z) tuples.

        Returns:
            List of 18 floating-point values representing centered and scaled (x, y, z)
            coordinates for landmarks [11, 12, 23, 24, 25, 26]. Returns zeros if any required
            landmarks are absent.
        """
        required = [11, 12, 23, 24, 25, 26]
        if not all(k in points_norm for k in required):
            return [0.0] * 18

        coords = np.array([points_norm[k] for k in required], dtype=np.float64)

        # Hip center from points 23 and 24 (indices 2 and 3)
        hip_center = (coords[2] + coords[3]) / 2.0
        # Shoulder center from points 11 and 12 (indices 0 and 1)
        shoulder_center = (coords[0] + coords[1]) / 2.0

        torso_dist = float(np.linalg.norm(shoulder_center - hip_center))
        if torso_dist == 0.0:
            torso_dist = 1.0

        relative = (coords - hip_center) / torso_dist
        return relative.flatten().tolist()
