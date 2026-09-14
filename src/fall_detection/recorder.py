"""Video buffering and persistence for fall detection evidence clips."""

from __future__ import annotations

import glob
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

from src.fall_detection.config import GLOBAL_CONFIG

logger = logging.getLogger(__name__)


class FallRecorder:
    """Buffers recent camera frames in memory and asynchronously saves video clips upon trigger."""

    def __init__(self, output_dir: str | Path = "recorded_falls", max_frames: int = 150):
        self.output_dir = str(output_dir)
        self.max_frames = max_frames
        self.frame_buffer: deque[np.ndarray] = deque(maxlen=max_frames)
        self.max_dir_size_bytes: int = GLOBAL_CONFIG.cleanup_max_size_mb * 1024 * 1024
        self.max_age_seconds: int = GLOBAL_CONFIG.cleanup_max_age_days * 86400
        self.lock = threading.Lock()
        self._cleanup_lock = threading.Lock()

        os.makedirs(self.output_dir, exist_ok=True)

    def write_frame(self, frame: np.ndarray | None, max_w: int = 640) -> None:
        """Appends a frame into the circular buffer, downscaling if width exceeds max_w."""
        if frame is None or frame.size == 0:
            return

        h, w = frame.shape[:2]
        if w > max_w:
            scale = max_w / float(w)
            new_h = int(h * scale)
            frame_to_store = cv2.resize(frame, (max_w, new_h), interpolation=cv2.INTER_NEAREST)
        else:
            frame_to_store = frame.copy()

        with self.lock:
            self.frame_buffer.append(frame_to_store)

    def save_recording(self, cam_name: str, width: int, height: int, fps: float = 30.0) -> str:
        """Asynchronously writes current buffer frames to an AVI file."""
        timestamp = int(time.time())
        filename = f"fall_{cam_name}_{timestamp}.avi"
        filepath = os.path.join(self.output_dir, filename)

        with self.lock:
            frames_snapshot = list(self.frame_buffer)

        if not frames_snapshot:
            return filepath

        threading.Thread(
            target=self._write_video_worker,
            args=(filepath, frames_snapshot, width, height, fps),
            daemon=True,
        ).start()

        return filepath

    def _write_video_worker(
        self, filepath: str, frames: list[np.ndarray], width: int, height: int, fps: float
    ) -> None:
        self._run_cleanup_policy()

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.error(f"VideoWriter failed to open: {filepath}")
            return

        try:
            for frame in frames:
                h, w = frame.shape[:2]
                if w != width or h != height:
                    frame = cv2.resize(frame, (width, height))
                out.write(frame)
        finally:
            out.release()

    def _run_cleanup_policy(self) -> None:
        """Enforces retention limit: drops old files and trims size to configured limit."""
        # Prevent concurrent cleanup from multiple save threads
        if not self._cleanup_lock.acquire(blocking=False):
            return
        try:
            now = time.time()
            pattern = os.path.join(self.output_dir, "fall_*.*")
            files = glob.glob(pattern)

            file_stats: list[tuple[str, int, float]] = []
            for f in files:
                try:
                    mtime = os.path.getmtime(f)
                    size = os.path.getsize(f)
                    if now - mtime > self.max_age_seconds:
                        os.remove(f)
                        continue
                    file_stats.append((f, size, mtime))
                except OSError:
                    continue

            file_stats.sort(key=lambda item: item[2])
            total_size = sum(item[1] for item in file_stats)

            while total_size > self.max_dir_size_bytes and file_stats:
                oldest_file, size, _ = file_stats.pop(0)
                try:
                    os.remove(oldest_file)
                    total_size -= size
                except OSError:
                    continue
        finally:
            self._cleanup_lock.release()
