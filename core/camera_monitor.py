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

import config
from core.pose_estimator import PoseEstimator;
from core.angle_calculator import AngleCalculator;
from core.ui_manager import UIManager;

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
    def __init__(self, monitor, name, source, width=640, height=480):
        self.monitor = monitor
        self.name = name
        self.source = source
        self.width = width
        self.height = height
        self.cap = None
        self.is_running = False
        self.last_frame = None
        self.fps = 0.0
        self.last_prediction = 0.0
        self.last_status = "STANDBY"
        self.sequence_buffer = deque(maxlen=config.TIME_STEPS)
        self.thread = None
        
        # Try to resolve numeric index
        try:
            if str(source).isdigit():
                self.source = int(source)
        except Exception:
            pass

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.cap:
            self.cap.release()
            self.cap = None

    def _run_loop(self):
        global shared_model
        
        estimator = PoseEstimator()
        calculator = AngleCalculator()
        ui = UIManager()
        
        # Open video capture
        if isinstance(self.source, int):
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW if os.name == 'nt' else 0)
        else:
            self.cap = cv2.VideoCapture(self.source)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        fps_time = time.time()
        while self.is_running:
            if not self.cap or not self.cap.isOpened():
                ret, frame = False, None
            else:
                ret, frame = self.cap.read()
                
            if not ret or frame is None:
                time.sleep(0.01)
                continue
                
            curr_time = time.time()
            self.fps = 1.0 / (curr_time - fps_time) if (curr_time - fps_time) > 0 else 30.0
            fps_time = curr_time
            
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
            
            if is_valid_pose:
                features = [left_angle / 180.0, right_angle / 180.0]
                rel_features = estimator.get_relative_features(points_norm)
                features.extend(rel_features)
                
                self.sequence_buffer.append(features)
                if shared_model and len(self.sequence_buffer) == config.TIME_STEPS:
                    input_data = np.array(self.sequence_buffer).reshape(1, config.TIME_STEPS, len(features))
                    with model_lock:
                        pred_val = shared_model.predict(input_data, verbose=0)[0][0]
                    prediction = float(pred_val)
                    if prediction > self.monitor.app.fall_threshold:
                        status_text = "FALL DETECTED"
                        theme_color = (0, 0, 255)
                            
            processed_frame = ui.draw_hud(
                frame=processed_frame,
                tester_name=self.name,
                fps=self.fps,
                status_text=status_text,
                prediction=prediction,
                theme_color=theme_color,
                bbox=bbox,
            )
            if is_valid_pose:
                processed_frame = ui.draw_angles(processed_frame, points_px, left_angle, right_angle)
                
            self.last_prediction = prediction
            self.last_status = status_text
            self.last_frame = processed_frame
            
        if self.cap:
            self.cap.release()
            self.cap = None


class CameraMonitor:
    def __init__(self, app):
        self.app = app
        self.active_streams = {}
        load_trained_model()

    @staticmethod
    def detect_available_cameras():
        available = []
        # Query camera indices 0-5
        for idx in range(5):
            try:
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW if os.name == 'nt' else 0)
                if cap.isOpened():
                    available.append(idx)
                    cap.release()
            except Exception:
                pass
        return available

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
