import os
import sys
import time
import threading
import datetime
import urllib.request
import urllib.parse
from collections import deque
import cv2
import numpy as np
import tensorflow as tf

# Force OpenCV FFmpeg backend to use TCP transport for RTSP streams
os.environ["OPENCV_FFMPEG_RTSP_TRANSPORT"] = "tcp"

import config
from core.pose_estimator import PoseEstimator
from core.angle_calculator import AngleCalculator
from core.ui_manager import UIManager
from core.fall_recorder import FallRecorder

# Global Lock and Shared Model
model_lock = threading.Lock()
shared_model = None


def send_line_notify(message, token):
    if not token or not token.strip():
        return False
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = urllib.parse.urlencode({"message": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except Exception as e:
        print(f"Error sending Line Notify: {e}")
        return False


def send_line_notify_async(message, token, callback=None):
    def worker():
        success = send_line_notify(message, token)
        if callback:
            callback(success)
    threading.Thread(target=worker, daemon=True).start()


def load_trained_model():
    global shared_model
    if os.path.isfile(config.MODEL_PATH):
        try:
            with model_lock:
                shared_model = tf.keras.models.load_model(config.MODEL_PATH)
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
    return False


class CameraStream:
    """
    High-reliability Camera Stream Handler.
    Supports both DirectShow Wired USB Cameras and TCP-based RTSP IP Network Cameras.
    Includes zero-lag buffer management, telemetry tracking, and auto-reconnection.
    """
    def __init__(self, monitor, name, source, width=640, height=480):
        self.monitor = monitor
        self.name = name
        self.source = source
        self.width = width
        self.height = height
        self.cap = None
        self.is_running = False
        
        # State tracking
        self.connection_status = "CONNECTING"  # "CONNECTING", "ONLINE", "RECONNECTING", "OFFLINE"
        self.status_detail = "Initializing stream connection..."
        self.is_online = False
        self.retry_count = 0
        self.last_frame_time = 0.0
        
        # Output telemetry
        self.last_frame = None
        self.fps = 0.0
        self.last_prediction = 0.0
        self.last_status = "CONNECTING"
        self.sequence_buffer = deque(maxlen=config.TIME_STEPS)
        
        self._raw_frame = None
        self._raw_frame_lock = threading.Lock()
        self._new_frame_event = threading.Event()
        self._reader_thread = None
        self._worker_thread = None
        self.fall_recorder = FallRecorder()
        
        # Resolve numeric source index for USB webcams
        try:
            if str(source).isdigit():
                self.source = int(source)
        except Exception:
            pass

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.connection_status = "CONNECTING"
            self.status_detail = "Connecting to video source..."
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True, name=f"{self.name}-Reader")
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name=f"{self.name}-Worker")
            self._reader_thread.start()
            self._worker_thread.start()

    def stop(self):
        self.is_running = False
        self.connection_status = "OFFLINE"
        self.is_online = False
        self._new_frame_event.set()
        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
            self._reader_thread = None
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None
        self._release_cap()

    def _release_cap(self):
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

    def _open_capture(self):
        """Open OpenCV VideoCapture with optimal backend and timeout settings."""
        self._release_cap()
        
        if isinstance(self.source, int):
            # Local Wired / USB Camera (DirectShow backend on Windows)
            backend = cv2.CAP_DSHOW if os.name == 'nt' else 0
            cap = cv2.VideoCapture(self.source, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return cap
        else:
            # IP Network Camera (RTSP Stream via FFmpeg backend over TCP)
            source_str = str(self.source).strip()
            cap = cv2.VideoCapture(source_str, cv2.CAP_FFMPEG)
            if hasattr(cv2, 'CAP_PROP_OPEN_TIMEOUT_MSEC'):
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            if hasattr(cv2, 'CAP_PROP_READ_TIMEOUT_MSEC'):
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)
            if hasattr(cv2, 'CAP_PROP_BUFFERSIZE'):
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap
            
        return None

    def _reader_loop(self):
        """
        Dedicated zero-lag frame reader thread.
        Continuously pulls frames from cap.read() at camera frame rate without any AI/processing delay,
        instantly draining FFmpeg's TCP buffer to eliminate lag accumulation and prevent deadlocks.
        """
        last_reconnect_attempt = 0.0
        
        while self.is_running:
            # 1. Connection / Reconnection Management
            if self.cap is None or not self.cap.isOpened():
                now = time.time()
                if now - last_reconnect_attempt > 2.0:
                    last_reconnect_attempt = now
                    self.retry_count += 1
                    self.connection_status = "CONNECTING" if self.retry_count <= 1 else "RECONNECTING"
                    self.status_detail = f"Attempting connection #{self.retry_count}..."
                    self.cap = self._open_capture()
                    if not self.cap or not self.cap.isOpened():
                        self.is_online = False
                        time.sleep(0.5)
                        continue
                else:
                    time.sleep(0.05)
                    continue

            # 2. Read frame immediately
            try:
                ret, frame = self.cap.read()
            except Exception as ex:
                print(f"[{self.name}] Exception reading frame: {ex}")
                ret, frame = False, None

            if ret and frame is not None and frame.size > 0:
                self.last_frame_time = time.time()
                self.is_online = True
                self.connection_status = "ONLINE"
                self.retry_count = 0
                
                with self._raw_frame_lock:
                    self._raw_frame = frame
                self._new_frame_event.set()
            else:
                # Frame drop or network blip
                now = time.time()
                if self.is_online and (now - self.last_frame_time > 3.5):
                    self.is_online = False
                    self.connection_status = "RECONNECTING"
                    self.status_detail = "Frame reception timed out. Reconnecting..."
                    self._release_cap()
                time.sleep(0.005)

        self._release_cap()

    def _worker_loop(self):
        """
        Dedicated AI inference & Cyberpunk HUD Rendering Thread.
        Pulls latest raw frame, runs downsampled Pose Estimation, 3D angle geometry,
        GRU fall classification inference, and telemetry overlays.
        """
        global shared_model
        
        estimator = PoseEstimator()
        calculator = AngleCalculator()
        ui = UIManager()
        
        frame_counter = 0
        fps_time = time.time()
        
        while self.is_running:
            has_new = self._new_frame_event.wait(timeout=0.1)
            if not self.is_running:
                break

            if not self.is_online or self._raw_frame is None:
                # Telemetry placeholder when connecting or offline
                self.last_frame = ui.generate_no_signal_frame(
                    self.width, self.height, self.name,
                    f"{self.connection_status} (#{self.retry_count})",
                    detail=str(self.source)
                )
                time.sleep(0.05)
                continue

            frame = None
            if has_new:
                self._new_frame_event.clear()
                with self._raw_frame_lock:
                    if self._raw_frame is not None:
                        frame = self._raw_frame.copy()
            else:
                time.sleep(0.01)
                continue

            if frame is None or frame.size == 0:
                continue

            curr_time = time.time()
            dt = curr_time - fps_time
            self.fps = 1.0 / dt if dt > 0 else 30.0
            fps_time = curr_time

            # 1. AI Pose Estimation
            processed_frame, points_px, points_norm, points_world = estimator.process_frame(frame)
            if processed_frame is None or processed_frame.size == 0:
                processed_frame = frame.copy()

            is_valid_pose = False
            left_angle, right_angle = 0.0, 0.0
            bbox = None

            if points_px:
                xs = [p[0] for p in points_px.values()]
                ys = [p[1] for p in points_px.values()]
                h, w, _ = processed_frame.shape
                min_x, max_x = max(0, min(xs) - 50), min(w, max(xs) + 50)
                min_y, max_y = max(0, min(ys) - 100), min(h, max(ys) + 50)
                bbox = (min_x, min_y, max_x, max_y)

                if all(k in points_px for k in config.TARGET_LANDMARKS) and all(k in points_world for k in config.TARGET_LANDMARKS):
                    is_valid_pose = True
                    left_angle = calculator.calculate_angle_3d(points_world[11], points_world[23], points_world[25])
                    right_angle = calculator.calculate_angle_3d(points_world[12], points_world[24], points_world[26])

            prediction = 0.0
            status_text = "NORMAL"
            theme_color = (0, 255, 0)

            # 2. Fall Prediction Model Inference
            if is_valid_pose:
                features = [left_angle / 180.0, right_angle / 180.0]
                rel_features = estimator.get_relative_features(points_norm)
                features.extend(rel_features)

                self.sequence_buffer.append(features)
                if shared_model and len(self.sequence_buffer) == config.TIME_STEPS:
                    if frame_counter % 3 == 0:
                        input_data = np.array(self.sequence_buffer).reshape(1, config.TIME_STEPS, len(features))
                        with model_lock:
                            pred_val = shared_model.predict(input_data, verbose=0)[0][0]
                        prediction = float(pred_val)
                    else:
                        prediction = self.last_prediction
                else:
                    prediction = 0.0

                frame_counter += 1

                if prediction > self.monitor.app.fall_threshold:
                    status_text = "FALL DETECTED"
                    theme_color = (0, 0, 255)

            # 3. Render HUD & Angles
            processed_frame = ui.draw_hud(
                frame=processed_frame,
                tester_name=self.name,
                fps=self.fps,
                status_text=status_text,
                prediction=prediction,
                theme_color=theme_color,
                bbox=bbox,
                source_label=f"{self.source}" if isinstance(self.source, int) else "RTSP IP STREAM"
            )
            if is_valid_pose:
                processed_frame = ui.draw_angles(processed_frame, points_px, left_angle, right_angle)

            self.last_prediction = prediction
            self.last_status = status_text
            self.last_frame = processed_frame
            self.fall_recorder.write_frame(processed_frame)

    def save_fall_clip(self):
        fps_val = self.fps if self.fps > 0 else 30.0
        return self.fall_recorder.save_recording(self.name, self.width, self.height, fps=fps_val)


class CameraMonitor:
    def __init__(self, app):
        self.app = app
        self.active_streams = {}
        load_trained_model()

    @staticmethod
    def detect_available_cameras(max_probe=8):
        """
        Probe physical connected cameras on Windows/DirectShow.
        Returns ONLY indices that physically respond to frame capture.
        """
        available = []
        backend = cv2.CAP_DSHOW if os.name == 'nt' else 0
        for idx in range(max_probe):
            try:
                cap = cv2.VideoCapture(idx, backend)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None and frame.size > 0:
                        available.append(idx)
                    cap.release()
            except Exception:
                pass
        return available

    @staticmethod
    def test_stream_connection(source, timeout_sec=4.0):
        """
        Quick synchronous probe to test a camera source or RTSP stream.
        Returns: (success: bool, message: str, resolution: str)
        """
        try:
            if str(source).isdigit():
                src_val = int(source)
                backend = cv2.CAP_DSHOW if os.name == 'nt' else 0
                cap = cv2.VideoCapture(src_val, backend)
            else:
                src_val = str(source).strip()
                cap = cv2.VideoCapture(src_val, cv2.CAP_FFMPEG)
                if hasattr(cv2, 'CAP_PROP_OPEN_TIMEOUT_MSEC'):
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, int(timeout_sec * 1000))
                if hasattr(cv2, 'CAP_PROP_READ_TIMEOUT_MSEC'):
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, int(timeout_sec * 1000))

            if not cap.isOpened():
                return False, "ไม่สามารถเปิดสัญญาณกล้องได้ (Connection Failed)", ""

            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None and frame.size > 0:
                h, w = frame.shape[:2]
                return True, "เชื่อมต่อสัญญาณสำเร็จ (Connected Successfully)", f"{w}x{h}"
            else:
                return False, "เชื่อมต่อได้แต่ไม่ได้รับข้อมูลภาพ (No video frames received)", ""
        except Exception as e:
            return False, f"เกิดข้อผิดพลาดในการเชื่อมต่อ: {e}", ""

    def start_camera_stream(self, name, source):
        if name in self.active_streams:
            self.active_streams[name].stop()
        stream = CameraStream(self, name, source)
        self.active_streams[name] = stream
        stream.start()
        return stream

    def stop_camera_stream(self, name):
        if name in self.active_streams:
            self.active_streams[name].stop()
            del self.active_streams[name]

    def stop_all_streams(self):
        for stream in list(self.active_streams.values()):
            stream.stop()
        self.active_streams.clear()
