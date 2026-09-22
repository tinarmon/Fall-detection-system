"""Tests for the configuration module."""

import tempfile
from pathlib import Path

from src.fall_detection.config import load_config


def test_load_config_valid_toml():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config_dir = tmp_path / "configs"
        config_dir.mkdir(parents=True, exist_ok=True)

        toml_content = """
        [app]
        version = "1.4.0"
        window_width = 800

        [camera]
        network_timeout_seconds = 12.0
        reconnect_max_backoff_seconds = 20.0
        rtsp_transport = "udp"

        [model]
        time_steps = 15
        fall_threshold = 0.75
        """
        with open(config_dir / "config.toml", "w") as f:
            f.write(toml_content)

        config = load_config(tmp_path)

        assert config.app_version == "1.4.0"
        assert config.window_width == 800
        assert config.network_timeout_seconds == 12.0
        assert config.reconnect_max_backoff_seconds == 20.0
        assert config.rtsp_transport == "udp"
        assert config.time_steps == 15
        assert config.fall_threshold == 0.75


def test_load_config_missing_toml():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        config = load_config(tmp_path)

        assert config.app_version == "1.4.0"
        assert config.window_width == 1280
        assert config.time_steps == 10
        assert config.fall_threshold == 0.6
        assert config.network_timeout_seconds == 8.0
        assert config.reconnect_max_backoff_seconds == 10.0
        assert config.rtsp_transport == "tcp"


def test_app_config_fields():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = load_config(tmp_path)

        assert hasattr(config, "fall_threshold")
        assert hasattr(config, "time_steps")
        assert hasattr(config, "app_version")
        assert hasattr(config, "network_timeout_seconds")
        assert hasattr(config, "reconnect_max_backoff_seconds")
        assert hasattr(config, "rtsp_transport")


def test_post_init_derived_paths():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = load_config(tmp_path)

        assert config.model_path == config.assets_dir / "fall_model.keras"
        assert config.pose_task_path == config.assets_dir / "pose_landmarker_full.task"
        assert config.dataset_path == config.data_dir / "fall_dataset.csv"
        assert config.live_data_path == config.data_dir / "live_collected_data.csv"
