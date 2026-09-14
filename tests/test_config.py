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
        version = "1.3.0"
        window_width = 800

        [model]
        time_steps = 15
        fall_threshold = 0.75
        """
        with open(config_dir / "config.toml", "w") as f:
            f.write(toml_content)

        config = load_config(tmp_path)

        assert config.app_version == "1.3.0"
        assert config.window_width == 800
        assert config.time_steps == 15
        assert config.fall_threshold == 0.75


def test_load_config_missing_toml():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        config = load_config(tmp_path)

        assert config.app_version == "1.3.0"
        assert config.window_width == 1280
        assert config.time_steps == 10
        assert config.fall_threshold == 0.6


def test_app_config_fields():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = load_config(tmp_path)

        assert hasattr(config, "fall_threshold")
        assert hasattr(config, "time_steps")
        assert hasattr(config, "app_version")


def test_post_init_derived_paths():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = load_config(tmp_path)

        assert config.model_path == config.assets_dir / "fall_model.keras"
        assert config.pose_task_path == config.assets_dir / "pose_landmarker_full.task"
        assert config.dataset_path == config.data_dir / "fall_dataset.csv"
        assert config.live_data_path == config.data_dir / "live_collected_data.csv"
