"""Camera stream management, frame acquisition, and fall inference pipeline."""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf

from src.fall_detection.config import GLOBAL_CONFIG
from src.fall_detection.geometry import calculate_angle_3d
from src.fall_detection.pose import PoseEstimator
from src.fall_detection.recorder import FallRecorder
from src.fall_detection.ui.hud import UIManager

# Force OpenCV FFmpeg backend to use TCP transport for RTSP streams
os.environ["OPENCV_FFMPEG_RTSP_TRANSPORT"] = "tcp"

logger = logging.getLogger(__name__)

model_lock = threading.Lock()
shared_model: tf.keras.Model | None = None


def load_trained_model(model_path: str | Path | None = None) -> bool:
    """Loads trained Keras sequential model into shared singleton reference."""
    global shared_model
    path = Path(model_path or GLOBAL_CONFIG.model_path)
    if path.is_file():
        try:
            with model_lock:
                shared_model = tf.keras.models.load_model(str(path))
            return True
        except (OSError, ValueError) as ex:
            logger.error(f"Failed loading model from {path}: {ex}")
    return False


class CameraStream:
    """Decoupled dual-thread camera capture and neural inference worker."""

    def __init__(self, monitor, name: str, source: int | str, width: int = 640, height: int = 480):
        self.monitor = monitor
        self.name = name
        self.source = source
        self.width = width
        self.height = height
        self.cap: cv2.VideoCapture | None = None
        self.is_running = False

        self.connection_status = "CONNECTING"
        self.status_detail = "Initializing stream connection..."
        self.is_online = False
        self.retry_count = 0
        self.last_frame_time = 0.0

        self._state_lock = threading.Lock()
        self._last_frame: np.ndarray | None = None
        self._fps = 0.0
        self._last_prediction = 0.0
        self._last_status = "CONNECTING"

        self.sequence_buffer: deque[list[float]] = deque(maxlen=GLOBAL_CONFIG.time_steps)
        self.frame_history: deque[np.ndarray] = deque(maxlen=GLOBAL_CONFIG.time_steps)
        self.fall_event_pending = False
        self.fall_hold_until = 0.0

        self.line_override_token: str | None = None
        self.last_line_sent_time = 0.0

        self._raw_frame_lock = threading.Lock()
        self._raw_frame: np.ndarray | None = None
        self._new_frame_event = threading.Event()

        self._reader_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None

        self.fall_recorder = FallRecorder()

    # --- Thread-safe property accessors ---

    @property
    def last_frame(self) -> np.ndarray | None:
        with self._state_lock:
            return self._last_frame

    @last_frame.setter
    def last_frame(self, value: np.ndarray | None) -> None:
        with self._state_lock:
            self._last_frame = value

    @property
    def fps(self) -> float:
        with self._state_lock:
            return self._fps

    @fps.setter
    def fps(self, value: float) -> None:
        with self._state_lock:
            self._fps = value

    @property
    def last_prediction(self) -> float:
        with self._state_lock:
            return self._last_prediction

    @last_prediction.setter
    def last_prediction(self, value: float) -> None:
        with self._state_lock:
            self._last_prediction = value

    @property
    def last_status(self) -> str:
        with self._state_lock:
            return self._last_status

    @last_status.setter
    def last_status(self, value: str) -> None:
        with self._state_lock:
            self._last_status = value

    def start(self) -> None:
        """Starts asynchronous reader and inference worker threads."""
        if self.is_running:
            return
        self.is_running = True
        self.connection_status = "CONNECTING"
        self.status_detail = f"Opening device/stream: {self.source}"

        self._reader_thread = threading.Thread(
            target=self._reader_loop, name=f"{self.name}_Reader", daemon=True
        )
        self._reader_thread.start()

        self._worker_thread = threading.Thread(
            target=self._worker_loop, name=f"{self.name}_Worker", daemon=True
        )
        self._worker_thread.start()

    def stop(self) -> None:
        """Stops capture threads and releases video hardware handles."""
        self.is_running = False
        self._new_frame_event.set()

        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)

        if self.cap:
            try:
                self.cap.release()
            except cv2.error:
                pass
            self.cap = None

        self.is_online = False
        self.connection_status = "OFFLINE"
        self.status_detail = "Camera stream stopped"

    def _open_capture(self) -> cv2.VideoCapture | None:
        if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
            idx = int(self.source)
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(idx)
        else:
            cap = cv2.VideoCapture(str(self.source), cv2.CAP_FFMPEG)

        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap.release()
        return None

    def _reader_loop(self) -> None:
        reconnect_delay = GLOBAL_CONFIG.reconnect_delay_seconds
        while self.is_running:
            if self.cap is None or not self.cap.isOpened():
                self.cap = self._open_capture()
                if self.cap is None:
                    self.connection_status = "RECONNECTING"
                    self.status_detail = f"Failed opening source {self.source}. Retrying..."
                    self.is_online = False
                    time.sleep(reconnect_delay)
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None or frame.size == 0:
                self.connection_status = "RECONNECTING"
                self.status_detail = "Dropped frame or signal lost. Reconnecting..."
                self.is_online = False
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(reconnect_delay * 0.5)
                continue

            self.is_online = True
            self.connection_status = "ONLINE"
            self.status_detail = "Signal active"

            with self._raw_frame_lock:
                self._raw_frame = frame
            self._new_frame_event.set()

    def _worker_loop(self) -> None:
        pose_estimator = PoseEstimator()
        ui = UIManager()
        frame_counter = 0
        fps_start = time.time()
        inference_counter = 0
        skip_n = max(1, GLOBAL_CONFIG.inference_skip_frames)

        while self.is_running:
            got_frame = self._new_frame_event.wait(timeout=0.1)
            if not self.is_running:
                break
            if not got_frame:
                continue

            self._new_frame_event.clear()

            with self._raw_frame_lock:
                if self._raw_frame is None:
                    continue
                frame = self._raw_frame.copy()

            try:
                frame_counter += 1
                inference_counter += 1
                elapsed = time.time() - fps_start
                if elapsed >= 1.0:
                    self.fps = frame_counter / elapsed
                    frame_counter = 0
                    fps_start = time.time()

                # Run pose detection on every Nth frame to limit CPU usage
                run_inference = inference_counter >= skip_n
                if run_inference:
                    inference_counter = 0

                h, w = frame.shape[:2]
                processed_frame = frame.copy()
                is_valid_pose = False
                bbox = None
                left_angle, right_angle = 0.0, 0.0
                prediction = 0.0
                status_text = "NORMAL"
                theme_color = (0, 255, 0)

                if run_inference:
                    processed_frame, points_px, points_norm, points_world = (
                        pose_estimator.process_frame(frame)
                    )

                    is_valid_pose = len(points_norm) >= 6

                    if is_valid_pose:
                        xs = [pt[0] for pt in points_px.values()]
                        ys = [pt[1] for pt in points_px.values()]
                        pad_x, pad_y = int(w * 0.04), int(h * 0.04)
                        bbox = (
                            max(0, min(xs) - pad_x),
                            max(0, min(ys) - pad_y),
                            min(w, max(xs) + pad_x),
                            min(h, max(ys) + pad_y),
                        )

                        if all(k in points_world for k in [11, 23, 25]):
                            left_angle = calculate_angle_3d(
                                points_world[11], points_world[23], points_world[25]
                            )
                        if all(k in points_world for k in [12, 24, 26]):
                            right_angle = calculate_angle_3d(
                                points_world[12], points_world[24], points_world[26]
                            )

                        rel_features = pose_estimator.get_relative_features(points_norm)
                        if rel_features is not None:
                            features = [left_angle / 180.0, right_angle / 180.0] + rel_features
                            self.sequence_buffer.append(features)
                        else:
                            self.sequence_buffer.clear()
                    else:
                        self.sequence_buffer.clear()

                    if (
                        len(self.sequence_buffer) == GLOBAL_CONFIG.time_steps
                        and shared_model is not None
                    ):
                        seq = np.expand_dims(
                            np.array(self.sequence_buffer, dtype=np.float32), axis=0
                        )
                        try:
                            with model_lock:
                                pred_val = float(shared_model(seq, training=False)[0][0])
                            prediction = pred_val
                        except (tf.errors.OpError, ValueError, TypeError) as ex:
                            logger.error(f"Inference error: {ex}")

                        if prediction > GLOBAL_CONFIG.fall_threshold:
                            status_text = "FALL DETECTED"
                            theme_color = (0, 0, 255)
                            self.fall_hold_until = time.time() + GLOBAL_CONFIG.fall_hold_seconds
                            with self._raw_frame_lock:
                                self.fall_event_pending = True
                        elif time.time() < self.fall_hold_until:
                            status_text = "FALL DETECTED"
                            theme_color = (0, 0, 255)
                else:
                    # Non-inference frame: retain last known status during hold
                    if time.time() < self.fall_hold_until:
                        status_text = "FALL DETECTED"
                        theme_color = (0, 0, 255)

                processed_frame = ui.draw_hud(
                    frame=processed_frame,
                    tester_name=self.name,
                    fps=self.fps,
                    status_text=status_text,
                    prediction=prediction if run_inference else self.last_prediction,
                    theme_color=theme_color,
                    bbox=bbox,
                    source_label=f"{self.source}"
                    if isinstance(self.source, int)
                    else "RTSP IP STREAM",
                )
                if is_valid_pose and run_inference:
                    processed_frame = ui.draw_angles(
                        processed_frame, points_px, left_angle, right_angle
                    )

                if run_inference:
                    self.last_prediction = prediction
                self.last_status = status_text
                self.last_frame = processed_frame
                self.frame_history.append(processed_frame.copy())
                self.fall_recorder.write_frame(processed_frame)

            except (cv2.error, ValueError, RuntimeError) as loop_err:
                logger.error(f"Error in camera {self.name} worker loop: {loop_err}", exc_info=True)
                time.sleep(0.01)

    def consume_fall_event(self) -> bool:
        """Atomically checks and consumes a pending fall trigger event."""
        with self._raw_frame_lock:
            if self.fall_event_pending:
                self.fall_event_pending = False
                return True
            return False

    def get_evidence_frames(self) -> list[np.ndarray]:
        """Returns 5 snapshots representative of the fall event sequence."""
        with self._raw_frame_lock:
            frames = list(self.frame_history)
        if not frames:
            return []
        indices = GLOBAL_CONFIG.evidence_frame_indices
        if len(frames) >= 10:
            return [frames[i] for i in indices if i < len(frames)]
        elif len(frames) >= 5:
            idxs = np.linspace(0, len(frames) - 1, 5, dtype=int)
            return [frames[i] for i in idxs]
        else:
            padded = list(frames)
            while len(padded) < 5:
                padded.append(padded[-1])
            return padded[:5]

    def save_fall_clip(self) -> str:
        """Requests asynchronous AVI compilation of the buffered frames."""
        fps_val = self.fps if self.fps > 0 else 30.0
        return self.fall_recorder.save_recording(self.name, self.width, self.height, fps=fps_val)


class CameraMonitor:
    """Oversees multiple active CameraStream instances and manages model inference lifecycle."""

    def __init__(self, app):
        self.app = app
        self.active_streams: dict[str, CameraStream] = {}
        load_trained_model()

    @staticmethod
    def detect_available_cameras(max_probe: int = 8) -> list[int]:
        """Probes DirectShow video hardware indices and returns verified available cameras."""
        available: list[int] = []
        for idx in range(max_probe):
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available.append(idx)
                cap.release()
        return available

    @staticmethod
    def test_stream_connection(
        source: int | str, timeout_sec: float = 6.0
    ) -> tuple[bool, str, str]:
        """Probes a camera index or RTSP URL to verify responsiveness and resolution."""
        try:
            if str(source).isdigit():
                backend = cv2.CAP_DSHOW if os.name == "nt" else 0
                cap = cv2.VideoCapture(int(source), backend)
            else:
                os.environ["OPENCV_FFMPEG_RTSP_TRANSPORT"] = "tcp"
                cap = cv2.VideoCapture(str(source).strip(), cv2.CAP_FFMPEG)
                if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout_sec * 1000))
                if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout_sec * 1000))

            if not cap.isOpened():
                return False, "Failed to connect to camera source", ""

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None and frame.size > 0:
                h, w = frame.shape[:2]
                return True, "Connected successfully", f"{w}x{h}"
            return False, "No video frames received from source", ""
        except cv2.error as ex:
            return False, f"Connection error: {ex}", ""

    def start_camera_stream(
        self, name: str, source: int | str, width: int = 640, height: int = 480
    ) -> CameraStream:
        """Starts and registers an active CameraStream."""
        if name in self.active_streams:
            self.stop_camera_stream(name)

        stream = CameraStream(self, name, source, width, height)
        self.active_streams[name] = stream
        stream.start()
        return stream

    def stop_camera_stream(self, name: str) -> None:
        """Stops and unregisters an existing CameraStream."""
        if name in self.active_streams:
            stream = self.active_streams.pop(name)
            stream.stop()

    def add_stream(
        self, name: str, source: int | str, width: int = 640, height: int = 480
    ) -> CameraStream:
        return self.start_camera_stream(name, source, width, height)

    def remove_stream(self, name: str) -> None:
        self.stop_camera_stream(name)

    def stop_all_streams(self) -> None:
        """Stops all active camera streams."""
        for name in list(self.active_streams.keys()):
            self.stop_camera_stream(name)
