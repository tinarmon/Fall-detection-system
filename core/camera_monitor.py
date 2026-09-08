import os
import sys
import time
import threading
import datetime
import json
import uuid
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


def create_fall_evidence_montage(frames, cam_name, time_str, prediction=0.88):
    """
    Stitches 5 fall frames (representing frames 2, 4, 6, 8, 10) + 1 telemetry badge into a 2x3 grid composite.
    """
    thumb_w, thumb_h = 320, 240
    labels = ["FRAME 2", "FRAME 4", "FRAME 6", "FRAME 8", "FRAME 10 (FALL)"]
    
    # Ensure at least 5 frames
    if not frames:
        frames = [np.zeros((thumb_h, thumb_w, 3), dtype=np.uint8)]
    padded_frames = list(frames)
    while len(padded_frames) < 5:
        padded_frames.append(padded_frames[-1])
        
    cells = []
    for i in range(5):
        frame = padded_frames[i]
        cell = cv2.resize(frame, (thumb_w, thumb_h))
        is_fall = (i == 4)
        bg_col = (0, 0, 200) if is_fall else (30, 30, 35)
        # Header tag on each frame
        cv2.rectangle(cell, (8, 8), (145, 34), bg_col, -1)
        cv2.putText(cell, labels[i], (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        cells.append(cell)
        
    # Cell 6: Telemetry info card
    card = np.full((thumb_h, thumb_w, 3), (20, 20, 25), dtype=np.uint8)
    cv2.rectangle(card, (10, 10), (thumb_w - 10, thumb_h - 10), (45, 45, 55), 1)
    cv2.putText(card, "AI EVIDENCE LOG", (20, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2, cv2.LINE_AA)
    cv2.putText(card, f"CAM: {str(cam_name).upper()}", (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(card, f"RISK: {int(prediction * 100)}%", (20, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2, cv2.LINE_AA)
    cv2.putText(card, f"TIME: {time_str}", (20, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1, cv2.LINE_AA)
    cv2.putText(card, "5-FRAME (2,4,6,8,10)", (20, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 255, 100), 1, cv2.LINE_AA)
    cells.append(card)
    
    row1 = np.hstack((cells[0], cells[1]))
    row2 = np.hstack((cells[2], cells[3]))
    row3 = np.hstack((cells[4], cells[5]))
    return np.vstack((row1, row2, row3))


def upload_evidence_image(jpeg_bytes):
    """
    Uploads evidence JPEG image to anonymous image host to generate a public HTTPS URL.
    Uses Catbox with tmpfiles.org as reliable fallback.
    """
    if not jpeg_bytes:
        return None
        
    # Attempt 1: Catbox.moe
    try:
        boundary = uuid.uuid4().hex
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'Mozilla/5.0'}
        parts = [
            f'--{boundary}'.encode(),
            b'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload',
            f'--{boundary}'.encode(),
            b'Content-Disposition: form-data; name="fileToUpload"; filename="evidence.jpg"',
            b'Content-Type: image/jpeg\r\n',
            jpeg_bytes,
            f'--{boundary}--\r\n'.encode()
        ]
        data = b'\r\n'.join(parts)
        req = urllib.request.Request('https://catbox.moe/user/api.php', data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            res = r.read().decode().strip()
            if res.startswith("http"):
                return res
    except Exception as e:
        print(f"Catbox upload failed: {e}")
        
    # Attempt 2: tmpfiles.org fallback
    try:
        boundary = uuid.uuid4().hex
        headers = {'Content-Type': f'multipart/form-data; boundary={boundary}', 'User-Agent': 'Mozilla/5.0'}
        parts = [
            f'--{boundary}'.encode(),
            b'Content-Disposition: form-data; name="file"; filename="evidence.jpg"',
            b'Content-Type: image/jpeg\r\n',
            jpeg_bytes,
            f'--{boundary}--\r\n'.encode()
        ]
        data = b'\r\n'.join(parts)
        req = urllib.request.Request('https://tmpfiles.org/api/v1/upload', data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            res = json.loads(r.read().decode())
            if res.get("status") == "success":
                url = res["data"]["url"]
                return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception as e2:
        print(f"tmpfiles upload failed: {e2}")
        
    return None


def create_fall_alert_flex(cam_name, time_str, video_filename=None, image_url=None):
    """Creates a high-contrast danger alert Flex Message payload for LINE Messaging API."""
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📷 กล้อง:", "color": "#888888", "size": "sm", "flex": 3},
                {"type": "text", "text": str(cam_name).upper(), "weight": "bold", "color": "#111111", "size": "sm", "flex": 7}
            ],
            "margin": "md"
        },
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "⏰ เวลา:", "color": "#888888", "size": "sm", "flex": 3},
                {"type": "text", "text": str(time_str), "color": "#111111", "size": "sm", "flex": 7}
            ],
            "margin": "sm"
        }
    ]
    
    if image_url:
        body_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📸 ภาพถ่าย:", "color": "#888888", "size": "sm", "flex": 3},
                {"type": "text", "text": "5 เฟรมต่อเนื่อง (แตะรูปเพื่อขยาย)", "color": "#16A34A", "size": "xs", "flex": 7, "wrap": True}
            ],
            "margin": "sm"
        })

    if video_filename:
        body_contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📂 บันทึกคลิป:", "color": "#888888", "size": "sm", "flex": 3},
                {"type": "text", "text": f"{video_filename} (ในคอมพิวเตอร์)", "color": "#4B5563", "size": "xs", "flex": 7, "wrap": True}
            ],
            "margin": "sm"
        })
        
    bubble = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🚨 ตรวจพบสภาวะการล้ม!",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg"
                },
                {
                    "type": "text",
                    "text": "AI Pre-Fall Biomechanical Alert",
                    "color": "#FEE2E2",
                    "size": "xs",
                    "margin": "xs"
                }
            ],
            "backgroundColor": "#DC2626",
            "paddingAll": "16px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "16px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "📞 โทรสายด่วน 1669",
                        "uri": "tel:1669"
                    },
                    "style": "primary",
                    "color": "#DC2626",
                    "height": "sm"
                }
            ],
            "paddingAll": "12px"
        }
    }
    
    if image_url:
        bubble["hero"] = {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "label": "View Full Evidence",
                "uri": image_url
            }
        }
        
    return bubble


def send_line_fall_alert_async(channel_token, destination_id, cam_name, time_str, montage_img=None, video_filename=None, callback=None):
    """
    Uploads evidence montage on a background worker thread and delivers rich Flex Message.
    Non-blocking to the main application and camera stream.
    """
    def worker():
        image_url = None
        if montage_img is not None:
            try:
                _, buf = cv2.imencode('.jpg', montage_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
                image_url = upload_evidence_image(buf.tobytes())
                if image_url:
                    print(f"📸 [LINE] Evidence montage uploaded successfully: {image_url}")
            except Exception as ex:
                print(f"Failed to encode/upload montage: {ex}")
                
        flex = create_fall_alert_flex(cam_name, time_str, video_filename=video_filename, image_url=image_url)
        alt_msg = f"\n🚨 แจ้งเตือนตรวจพบการล้ม!\n📷 กล้อง: {str(cam_name).upper()}\n⏰ เวลา: {time_str}\n📸 มีภาพหลักฐาน 5 เฟรมแนบ"
        success = send_line_push_message(channel_token, destination_id, message_text=alt_msg, flex_container=flex)
        if callback:
            callback(success)
            
    threading.Thread(target=worker, daemon=True).start()


def send_line_push_message(channel_token, destination_id, message_text=None, flex_container=None):
    """
    Sends a push message to a LINE user or group via LINE Messaging API.
    Supports text, Flex Message cards, and auto-fallback.
    """
    if not channel_token or not str(channel_token).strip() or not destination_id or not str(destination_id).strip():
        return False
        
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {channel_token.strip()}",
        "Content-Type": "application/json"
    }
    
    messages = []
    if flex_container:
        messages.append({
            "type": "flex",
            "altText": message_text or "🚨 แจ้งเตือนสภาวะเสี่ยงล้ม (AI Fall Alert)",
            "contents": flex_container
        })
    elif message_text:
        messages.append({
            "type": "text",
            "text": message_text
        })
    else:
        return False
        
    payload = {
        "to": str(destination_id).strip(),
        "messages": messages
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=8) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        print(f"HTTPError sending LINE Push Message ({e.code}): {error_body}")
        if flex_container and message_text:
            try:
                fallback_payload = {
                    "to": str(destination_id).strip(),
                    "messages": [{"type": "text", "text": message_text}]
                }
                fallback_data = json.dumps(fallback_payload).encode("utf-8")
                req = urllib.request.Request(url, data=fallback_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=5) as fallback_resp:
                    return fallback_resp.status == 200
            except Exception as ex2:
                print(f"Fallback plain text failed: {ex2}")
        return False
    except Exception as e:
        print(f"Error sending LINE Push Message: {e}")
        return False


def send_line_push_async(channel_token, destination_id, message_text=None, flex_container=None, callback=None):
    def worker():
        success = send_line_push_message(channel_token, destination_id, message_text, flex_container)
        if callback:
            callback(success)
    threading.Thread(target=worker, daemon=True).start()


def send_line_notify(message, token):
    """Legacy LINE Notify compatibility function."""
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
    """Legacy LINE Notify async compatibility function."""
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
        self.frame_history = deque(maxlen=config.TIME_STEPS)
        self.fall_event_pending = False
        self.fall_hold_until = 0.0
        
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
        ui = UIManager()
        estimator = None
        try:
            import logging
            logging.info(f"[{self.name}] Initializing PoseEstimator (task_path={config.POSE_TASK_PATH}, exists={os.path.exists(config.POSE_TASK_PATH)})")
            estimator = PoseEstimator()
            logging.info(f"[{self.name}] PoseEstimator initialized successfully!")
        except Exception as ex:
            import logging
            logging.error(f"[{self.name}] Failed to initialize PoseEstimator: {ex}", exc_info=True)
            print(f"[{self.name}] Warning: Failed to initialize PoseEstimator: {ex}")
            
        calculator = AngleCalculator()
        
        frame_counter = 0
        fps_time = time.time()
        
        while self.is_running:
            try:
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
                if estimator is not None:
                    try:
                        processed_frame, points_px, points_norm, points_world = estimator.process_frame(frame)
                        if frame_counter % 60 == 0:
                            import logging
                            logging.info(f"[{self.name}] Frame {frame_counter}: landmarks detected={len(points_px)}")
                    except Exception as ex:
                        import logging
                        logging.error(f"[{self.name}] Error in process_frame: {ex}", exc_info=True)
                        print(f"[{self.name}] Error in process_frame: {ex}")
                        processed_frame = frame.copy()
                        points_px, points_norm, points_world = {}, {}, {}
                else:
                    if frame_counter % 60 == 0:
                        import logging
                        logging.warning(f"[{self.name}] Frame {frame_counter}: estimator is None, attempting re-initialization...")
                        try:
                            estimator = PoseEstimator()
                            logging.info(f"[{self.name}] PoseEstimator successfully re-initialized!")
                        except Exception as ex:
                            logging.error(f"[{self.name}] PoseEstimator re-initialization failed: {ex}")
                    processed_frame = frame.copy()
                    points_px, points_norm, points_world = {}, {}, {}

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
                    # Dynamic feature dimension adaptation matching the loaded GRU model (14 or 20)
                    expected_dim = shared_model.input_shape[-1] if (shared_model is not None and hasattr(shared_model, 'input_shape') and shared_model.input_shape) else 14

                    if expected_dim == 14:
                        features = [left_angle / 180.0, right_angle / 180.0]
                        for target in config.TARGET_LANDMARKS:
                            features.extend([points_norm[target][0], points_norm[target][1]])
                    elif expected_dim == 20:
                        features = [left_angle / 180.0, right_angle / 180.0]
                        rel_features = estimator.get_relative_features(points_norm)
                        features.extend(rel_features)
                    else:
                        features = [left_angle / 180.0, right_angle / 180.0]
                        for target in config.TARGET_LANDMARKS:
                            features.extend([points_norm[target][0], points_norm[target][1]])
                        if len(features) < expected_dim:
                            features.extend([0.0] * (expected_dim - len(features)))
                        elif len(features) > expected_dim:
                            features = features[:expected_dim]

                    self.sequence_buffer.append(features)
                    if shared_model and len(self.sequence_buffer) == config.TIME_STEPS:
                        if frame_counter % 3 == 0:
                            try:
                                input_data = np.array(self.sequence_buffer, dtype=np.float32).reshape(1, config.TIME_STEPS, expected_dim)
                                with model_lock:
                                    pred_val = shared_model(input_data, training=False).numpy()[0][0]
                                prediction = float(pred_val)
                            except Exception as pred_err:
                                import logging
                                logging.error(f"[{self.name}] Error during model inference: {pred_err}", exc_info=True)
                                prediction = self.last_prediction
                        else:
                            prediction = self.last_prediction
                    else:
                        prediction = 0.0

                    frame_counter += 1

                    if prediction > self.monitor.app.fall_threshold:
                        status_text = "FALL DETECTED"
                        theme_color = (0, 0, 255)
                        with self._raw_frame_lock:
                            self.fall_event_pending = True
                        self.fall_hold_until = time.time() + 1.5
                    elif time.time() < self.fall_hold_until:
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
                self.frame_history.append(processed_frame.copy())
                self.fall_recorder.write_frame(processed_frame)

            except Exception as loop_err:
                import logging
                logging.error(f"[{self.name}] Unexpected error in worker loop: {loop_err}", exc_info=True)
                time.sleep(0.01)

    def consume_fall_event(self):
        with self._raw_frame_lock:
            if self.fall_event_pending:
                self.fall_event_pending = False
                return True
            return False

    def get_evidence_frames(self):
        with self._raw_frame_lock:
            frames = list(self.frame_history)
        if not frames:
            return []
        if len(frames) >= 10:
            # Frames 2, 4, 6, 8, 10 (1-indexed) -> [1, 3, 5, 7, 9] (0-indexed)
            return [frames[1], frames[3], frames[5], frames[7], frames[9]]
        elif len(frames) >= 5:
            idxs = np.linspace(0, len(frames) - 1, 5, dtype=int)
            return [frames[i] for i in idxs]
        else:
            padded = list(frames)
            while len(padded) < 5:
                padded.append(padded[-1])
            return padded[:5]

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
    def test_stream_connection(source, timeout_sec=6.0):
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
                os.environ["OPENCV_FFMPEG_RTSP_TRANSPORT"] = "tcp"
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
