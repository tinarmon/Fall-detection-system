import os

# ==========================================
# 📁 PATHS & DIRECTORIES
# ==========================================
# Automatically define the base directory relative to this config file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
RAW_DATA_DIR = os.path.join(DATA_DIR, "raw")

# Files
MODEL_PATH = os.path.join(ASSETS_DIR, "fall_model.keras")
POSE_TASK_PATH = os.path.join(ASSETS_DIR, "pose_landmarker_full.task")
DATASET_PATH = os.path.join(DATA_DIR, "fall_dataset.csv")
LIVE_DATA_PATH = os.path.join(DATA_DIR, "live_collected_data.csv")

# ==========================================
# 🧠 MODEL & TRAINING HYPERPARAMETERS
# ==========================================
TIME_STEPS = 10             # Number of historical frames the AI looks at
EPOCHS = 30                 # Number of training epochs
BATCH_SIZE = 32             # Training batch size
FALL_THRESHOLD = 0.6        # Prediction probability threshold to trigger a "Fall" alert

# ==========================================
# 🧍 MEDIAPIPE POSE ESTIMATION SETTINGS
# ==========================================
# 11: L Shoulder, 12: R Shoulder, 23: L Hip, 24: R Hip, 25: L Knee, 26: R Knee
TARGET_LANDMARKS = [11, 12, 23, 24, 25, 26]
CONNECTIONS = [
    (11, 12), (11, 23), (12, 24),
    (23, 24), (23, 25), (24, 26)
]

MIN_DETECTION_CONFIDENCE = 0.5
MIN_PRESENCE_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

# ==========================================
# 📷 CAMERA & UI SETTINGS
# ==========================================
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

MAIN_WINDOW_NAME = "Fall Detection System"
COLLECT_WINDOW_NAME = "Data Collection Mode"

# Colors (BGR Format)
COLOR_NORMAL = (0, 255, 0)      # Green
COLOR_WARNING = (0, 165, 255)   # Orange
COLOR_DANGER = (0, 0, 255)      # Red
COLOR_TEXT = (255, 255, 255)    # White