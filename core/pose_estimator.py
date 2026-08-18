import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config


class PoseEstimator:
    def __init__(self, model_path=config.POSE_TASK_PATH, min_detection_confidence=None, min_presence_confidence=None, min_tracking_confidence=None):
        base_options = python.BaseOptions(model_asset_path=model_path)
        
        det_conf = min_detection_confidence if min_detection_confidence is not None else config.MIN_DETECTION_CONFIDENCE
        pres_conf = min_presence_confidence if min_presence_confidence is not None else config.MIN_PRESENCE_CONFIDENCE
        track_conf = min_tracking_confidence if min_tracking_confidence is not None else config.MIN_TRACKING_CONFIDENCE
        
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=det_conf,
            min_pose_presence_confidence=pres_conf,
            min_tracking_confidence=track_conf
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.TARGET_LANDMARKS = config.TARGET_LANDMARKS
        self.CONNECTIONS = config.CONNECTIONS

    def process_frame(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = self.detector.detect(mp_image)
        
        points_px = {}
        points_norm = {}   # Normalized 3D coordinates (x, y, z)
        points_world = {}  # World metric 3D coordinates (x, y, z) in meters
        
        if detection_result.pose_landmarks:
            landmarks = detection_result.pose_landmarks[0]
            world_landmarks = (
                detection_result.pose_world_landmarks[0]
                if detection_result.pose_world_landmarks
                else None
            )
            
            h, w, _ = frame.shape
            
            for idx in self.TARGET_LANDMARKS:
                lm = landmarks[idx]
                if lm.visibility > 0.5:
                    # 1. พิกัด Pixel (สำหรับวาดจอและแสดงผล HUD)
                    px, py = int(lm.x * w), int(lm.y * h)
                    points_px[idx] = (px, py)
                    
                    # 2. พิกัด Normalized 3D (x, y, z) สำหรับป้อน AI
                    points_norm[idx] = (lm.x, lm.y, lm.z)
                    
                    # 3. พิกัด World 3D (x, y, z) สำหรับคำนวณมุม 3 มิติที่เป็นกลางทางทิศทาง
                    if world_landmarks:
                        w_lm = world_landmarks[idx]
                        points_world[idx] = (w_lm.x, w_lm.y, w_lm.z)
                    else:
                        points_world[idx] = (lm.x, lm.y, lm.z)
                    
                    cv2.circle(frame, (px, py), 8, (0, 255, 0), -1)

            for p1, p2 in self.CONNECTIONS:
                if p1 in points_px and p2 in points_px:
                    cv2.line(frame, points_px[p1], points_px[p2], (255, 200, 0), 3)
                    
        # ส่งค่ากลับ 4 ตัว (ภาพ, พิกัดพิกเซล, พิกัด AI, พิกัด 3D โลกจริง)
        return frame, points_px, points_norm, points_world

    @staticmethod
    def get_relative_features(points_norm):
        """
        แปลงพิกัด 3D Normalized ให้สัมพันธ์กับศูนย์กลางสะโพก และปรับสเกลด้วยความสูงลำตัว (Torso)
        ส่งกลับเป็น list ขนาด 18 ค่า (x, y, z สำหรับจุดหลัก 6 จุด)
        """
        import numpy as np
        required = [11, 12, 23, 24, 25, 26]
        if not all(k in points_norm for k in required):
            return [0.0] * 18
            
        # 1. คำนวณจุดศูนย์กลางสะโพก (Hip center)
        hc_x = (points_norm[23][0] + points_norm[24][0]) / 2.0
        hc_y = (points_norm[23][1] + points_norm[24][1]) / 2.0
        hc_z = (points_norm[23][2] + points_norm[24][2]) / 2.0
        
        # 2. คำนวณจุดศูนย์กลางไหล่ (Shoulder center)
        sc_x = (points_norm[11][0] + points_norm[12][0]) / 2.0
        sc_y = (points_norm[11][1] + points_norm[12][1]) / 2.0
        sc_z = (points_norm[11][2] + points_norm[12][2]) / 2.0
        
        # 3. คำนวณความสูงลำตัว (Torso distance) เพื่อปรับสเกลขนาดร่างกาย
        torso = np.sqrt((sc_x - hc_x)**2 + (sc_y - hc_y)**2 + (sc_z - hc_z)**2)
        if torso == 0:
            torso = 1.0
            
        features = []
        for idx in required:
            x, y, z = points_norm[idx]
            features.extend([
                (x - hc_x) / torso,
                (y - hc_y) / torso,
                (z - hc_z) / torso
            ])
            
        return features