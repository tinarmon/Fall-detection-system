"""Runtime configuration persistence for camera settings and user preferences."""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def load_runtime_config(path: str | Path) -> dict:
    """Loads runtime configuration from a JSON file."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.error("Corrupt configuration file %s: %s", path, e)
        return {}
    except OSError as e:
        logger.error("Failed to read configuration file %s: %s", path, e)
        return {}


def save_runtime_config(path: str | Path, data: dict) -> None:
    """Saves runtime configuration to a JSON file atomically."""
    path_obj = Path(path)
    tmp_path = path_obj.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        os.replace(tmp_path, path_obj)
    except OSError as e:
        logger.error("Failed to save configuration file %s: %s", path_obj, e)
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
