"""Configuration module for the Fall Detection System."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppConfig:
    """Immutable application and ML configuration."""

    base_dir: Path
    assets_dir: Path
    data_dir: Path
    raw_data_dir: Path
    clean_data_dir: Path
    use_clean_data: bool = True

    model_path: Path = field(init=False)
    pose_task_path: Path = field(init=False)
    dataset_path: Path = field(init=False)
    live_data_path: Path = field(init=False)

    app_version: str = "1.3.0"
    window_name: str = "Fall Detection System"
    window_width: int = 1280
    window_height: int = 720
    line_cooldown_seconds: int = 60

    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480

    time_steps: int = 10
    epochs: int = 30
    batch_size: int = 32
    fall_threshold: float = 0.6

    target_landmarks: list[int] = field(default_factory=lambda: [11, 12, 23, 24, 25, 26])
    connections: list[tuple[int, int]] = field(
        default_factory=lambda: [(11, 12), (11, 23), (12, 24), (23, 24), (23, 25), (24, 26)]
    )

    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    jump_threshold: float = 0.15
    outlier_distance_threshold: float = 0.20
    min_outlier_run: int = 3

    jitter_sigma: float = 0.005
    translation_range: float = 0.05
    scale_range: float = 0.05

    line_channel_token: str = ""

    # Inference pipeline settings (were hardcoded in camera.py)
    fall_hold_seconds: float = 2.0
    reconnect_delay_seconds: float = 1.0
    inference_skip_frames: int = 1
    evidence_frame_indices: list[int] = field(default_factory=lambda: [1, 3, 5, 7, 9])

    # Recording cleanup (were hardcoded in recorder.py)
    cleanup_max_size_mb: int = 500
    cleanup_max_age_days: int = 7

    # Pose detection (was hardcoded in pose.py)
    detection_resize_width: int = 640

    # GUI refresh rate (was hardcoded in main.py)
    gui_refresh_ms: int = 33

    # Upload endpoints (were hardcoded in notification.py)
    upload_primary_url: str = "https://catbox.moe/user/api.php"
    upload_fallback_url: str = "https://tmpfiles.org/api/v1/upload"

    def __post_init__(self):
        object.__setattr__(self, "model_path", self.assets_dir / "fall_model.keras")
        object.__setattr__(self, "pose_task_path", self.assets_dir / "pose_landmarker_full.task")
        object.__setattr__(self, "dataset_path", self.data_dir / "fall_dataset.csv")
        object.__setattr__(self, "live_data_path", self.data_dir / "live_collected_data.csv")


def load_config(root_path: Path | None = None) -> AppConfig:
    """Loads application configuration from TOML with environment variable fallbacks."""
    if root_path is None:
        if getattr(sys, "frozen", False):
            root_path = Path(sys.executable).resolve().parent
        else:
            root_path = Path(__file__).resolve().parents[2]

    toml_path = root_path / "configs" / "config.toml"
    if not toml_path.is_file() and getattr(sys, "frozen", False):
        alt_toml = Path(getattr(sys, "_MEIPASS", root_path)) / "configs" / "config.toml"
        if alt_toml.is_file():
            toml_path = alt_toml

    raw: dict = {}
    if toml_path.is_file():
        with open(toml_path, "rb") as f:
            raw = tomllib.load(f)

    app_sec = raw.get("app", {})
    cam_sec = raw.get("camera", {})
    model_sec = raw.get("model", {})
    pose_sec = raw.get("pose", {})
    prep_sec = raw.get("preprocessing", {})
    aug_sec = raw.get("augmentation", {})
    notif_sec = raw.get("notifications", {})
    infer_sec = raw.get("inference", {})
    rec_sec = raw.get("recording", {})
    upload_sec = raw.get("upload", {})

    token = os.environ.get("LINE_CHANNEL_TOKEN", str(notif_sec.get("line_channel_token", "")))

    raw_connections = pose_sec.get(
        "connections",
        [[11, 12], [11, 23], [12, 24], [23, 24], [23, 25], [24, 26]],
    )
    connections = [(int(p[0]), int(p[1])) for p in raw_connections]

    assets_dir = root_path / "assets"
    if not assets_dir.is_dir() and getattr(sys, "frozen", False):
        alt_assets = Path(getattr(sys, "_MEIPASS", root_path)) / "assets"
        if alt_assets.is_dir():
            assets_dir = alt_assets

    data_dir = root_path / "data"

    # Evidence frame indices from TOML arrive as list[int]
    raw_evidence = infer_sec.get("evidence_frame_indices", [1, 3, 5, 7, 9])
    evidence_indices = [int(x) for x in raw_evidence]

    return AppConfig(
        base_dir=root_path,
        assets_dir=assets_dir,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        clean_data_dir=data_dir / "clean",
        app_version=str(app_sec.get("version", "1.3.0")),
        window_name=str(app_sec.get("window_name", "Fall Detection System")),
        window_width=int(app_sec.get("window_width", 1280)),
        window_height=int(app_sec.get("window_height", 720)),
        line_cooldown_seconds=int(app_sec.get("line_cooldown_seconds", 60)),
        camera_index=int(cam_sec.get("default_index", 0)),
        camera_width=int(cam_sec.get("width", 640)),
        camera_height=int(cam_sec.get("height", 480)),
        time_steps=int(model_sec.get("time_steps", 10)),
        epochs=int(model_sec.get("epochs", 30)),
        batch_size=int(model_sec.get("batch_size", 32)),
        fall_threshold=float(model_sec.get("fall_threshold", 0.6)),
        target_landmarks=[
            int(x) for x in pose_sec.get("target_landmarks", [11, 12, 23, 24, 25, 26])
        ],
        connections=connections,
        min_detection_confidence=float(pose_sec.get("min_detection_confidence", 0.5)),
        min_presence_confidence=float(pose_sec.get("min_presence_confidence", 0.5)),
        min_tracking_confidence=float(pose_sec.get("min_tracking_confidence", 0.5)),
        jump_threshold=float(prep_sec.get("jump_threshold", 0.15)),
        outlier_distance_threshold=float(prep_sec.get("outlier_distance_threshold", 0.20)),
        min_outlier_run=int(prep_sec.get("min_outlier_run", 3)),
        jitter_sigma=float(aug_sec.get("jitter_sigma", 0.005)),
        translation_range=float(aug_sec.get("translation_range", 0.05)),
        scale_range=float(aug_sec.get("scale_range", 0.05)),
        line_channel_token=token,
        fall_hold_seconds=float(infer_sec.get("fall_hold_seconds", 2.0)),
        reconnect_delay_seconds=float(infer_sec.get("reconnect_delay_seconds", 1.0)),
        inference_skip_frames=int(infer_sec.get("skip_frames", 1)),
        evidence_frame_indices=evidence_indices,
        cleanup_max_size_mb=int(rec_sec.get("cleanup_max_size_mb", 500)),
        cleanup_max_age_days=int(rec_sec.get("cleanup_max_age_days", 7)),
        detection_resize_width=int(pose_sec.get("detection_resize_width", 640)),
        gui_refresh_ms=int(app_sec.get("gui_refresh_ms", 33)),
        upload_primary_url=str(upload_sec.get("primary_url", "https://catbox.moe/user/api.php")),
        upload_fallback_url=str(
            upload_sec.get("fallback_url", "https://tmpfiles.org/api/v1/upload")
        ),
    )


try:
    GLOBAL_CONFIG = load_config()
except Exception:
    logger.warning("Failed to load config.toml, using defaults", exc_info=True)
    # Provide sensible defaults when TOML is missing or malformed
    _fallback_root = Path(__file__).resolve().parents[2]
    GLOBAL_CONFIG = AppConfig(
        base_dir=_fallback_root,
        assets_dir=_fallback_root / "assets",
        data_dir=_fallback_root / "data",
        raw_data_dir=_fallback_root / "data" / "raw",
        clean_data_dir=_fallback_root / "data" / "clean",
    )
