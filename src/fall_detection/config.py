"""Configuration module for the Fall Detection System."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib


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

    app_version: str = "1.2.0"
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

    return AppConfig(
        base_dir=root_path,
        assets_dir=assets_dir,
        data_dir=data_dir,
        raw_data_dir=data_dir / "raw",
        clean_data_dir=data_dir / "clean",
        app_version=str(app_sec.get("version", "1.2.0")),
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
    )


GLOBAL_CONFIG = load_config()
