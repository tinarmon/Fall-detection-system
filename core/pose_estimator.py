import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import config

class PoseEstimator:
    # Update default path
    def __init__(self, model_path=config.POSE_TASK_PATH):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=config.MIN_PRESENCE_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
        )
        self.detector = vision.PoseLandmarker.create_from_options(options)
        self.TARGET_LANDMARKS = config.TARGET_LANDMARKS
        self.CONNECTIONS = config.CONNECTIONS

    def process_frame(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
        detection_result = self.detector.detect(mp_image)
        
        points_px = {}
        points_norm = {} # เพิ่มพิกัดสำหรับ AI
        
        if detection_result.pose_landmarks:
            landmarks = detection_result.pose_landmarks[0]
            h, w, _ = frame.shape
            
            for idx in self.TARGET_LANDMARKS:
                lm = landmarks[idx]
                if lm.visibility > 0.5:
                    # 1. พิกัด Pixel (สำหรับวาดจอและคำนวณมุม)
                    px, py = int(lm.x * w), int(lm.y * h)
                    points_px[idx] = (px, py)
                    
                    # 2. พิกัด Normalized (0.0-1.0 สำหรับสอน AI)
                    points_norm[idx] = (lm.x, lm.y)
                    
                    cv2.circle(frame, (px, py), 8, (0, 255, 0), -1)

            for p1, p2 in self.CONNECTIONS:
                if p1 in points_px and p2 in points_px:
                    cv2.line(frame, points_px[p1], points_px[p2], (255, 200, 0), 3)
                    
        # ส่งค่ากลับ 3 ตัว (ภาพ, พิกัดวาด, พิกัดAI)
        return frame, points_px, points_norm