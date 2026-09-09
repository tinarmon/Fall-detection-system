"""Backwards-compatibility configuration facade delegating to src.fall_detection.config."""

from __future__ import annotations

import os
from src.fall_detection.config import GLOBAL_CONFIG

BASE_DIR = str(GLOBAL_CONFIG.base_dir)
ASSETS_DIR = str(GLOBAL_CONFIG.assets_dir)
EXE_DIR = BASE_DIR
DATA_DIR = str(GLOBAL_CONFIG.data_dir)
RAW_DATA_DIR = str(GLOBAL_CONFIG.raw_data_dir)
CLEAN_DATA_DIR = str(GLOBAL_CONFIG.clean_data_dir)
USE_CLEAN_DATA = GLOBAL_CONFIG.use_clean_data

MODEL_PATH = str(GLOBAL_CONFIG.model_path)
POSE_TASK_PATH = str(GLOBAL_CONFIG.pose_task_path)
DATASET_PATH = str(GLOBAL_CONFIG.dataset_path)
LIVE_DATA_PATH = str(GLOBAL_CONFIG.live_data_path)

TIME_STEPS = GLOBAL_CONFIG.time_steps
EPOCHS = GLOBAL_CONFIG.epochs
BATCH_SIZE = GLOBAL_CONFIG.batch_size
FALL_THRESHOLD = GLOBAL_CONFIG.fall_threshold
LINE_COOLDOWN_SECONDS = GLOBAL_CONFIG.line_cooldown_seconds
APP_VERSION = GLOBAL_CONFIG.app_version
DEFAULT_LINE_CHANNEL_TOKEN = GLOBAL_CONFIG.line_channel_token

TARGET_LANDMARKS = GLOBAL_CONFIG.target_landmarks
CONNECTIONS = GLOBAL_CONFIG.connections

MIN_DETECTION_CONFIDENCE = GLOBAL_CONFIG.min_detection_confidence
MIN_PRESENCE_CONFIDENCE = GLOBAL_CONFIG.min_presence_confidence
MIN_TRACKING_CONFIDENCE = GLOBAL_CONFIG.min_tracking_confidence

CAMERA_INDEX = GLOBAL_CONFIG.camera_index
CAMERA_WIDTH = GLOBAL_CONFIG.camera_width
CAMERA_HEIGHT = GLOBAL_CONFIG.camera_height

WINDOW_WIDTH = GLOBAL_CONFIG.window_width
WINDOW_HEIGHT = GLOBAL_CONFIG.window_height

MAIN_WINDOW_NAME = GLOBAL_CONFIG.window_name
COLLECT_WINDOW_NAME = "Data Collection Mode"

COLOR_NORMAL = (0, 255, 0)
COLOR_WARNING = (0, 165, 255)
COLOR_DANGER = (0, 0, 255)
COLOR_TEXT = (255, 255, 255)

JUMP_THRESHOLD = GLOBAL_CONFIG.jump_threshold
OUTLIER_DISTANCE_THRESHOLD = GLOBAL_CONFIG.outlier_distance_threshold
MIN_OUTLIER_RUN = GLOBAL_CONFIG.min_outlier_run

JITTER_SIGMA = GLOBAL_CONFIG.jitter_sigma
TRANSLATION_RANGE = GLOBAL_CONFIG.translation_range
SCALE_RANGE = GLOBAL_CONFIG.scale_range