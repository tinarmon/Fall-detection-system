"""High-performance inference engine supporting TFLite and Keras backends."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np

from src.fall_detection.config import GLOBAL_CONFIG

logger = logging.getLogger(__name__)


class ModelInferenceEngine:
    """Thread-safe inference runner with automatic TFLite acceleration and Keras fallback."""

    def __init__(self, model_path: Path | None = None, tflite_path: Path | None = None):
        self.model_path = model_path or GLOBAL_CONFIG.model_path
        self.tflite_path = tflite_path or GLOBAL_CONFIG.tflite_model_path
        self.backend: str = "none"
        self._keras_model: Any = None
        self._tflite_interpreter: Any = None
        self._input_details: list[dict[str, Any]] = []
        self._output_details: list[dict[str, Any]] = []
        self._lock = threading.Lock()

        self._load_backend()

    def _load_backend(self) -> None:
        """Attempts to load TFLite for ultra-low latency; falls back to Keras."""
        # 1. Try TFLite backend if available
        if self.tflite_path.is_file():
            try:
                import tensorflow as tf

                interpreter = tf.lite.Interpreter(model_path=str(self.tflite_path))
                interpreter.allocate_tensors()
                self._tflite_interpreter = interpreter
                self._input_details = interpreter.get_input_details()
                self._output_details = interpreter.get_output_details()
                self.backend = "tflite"
                logger.info(f"Loaded accelerated TFLite model from {self.tflite_path}")
                return
            except Exception as ex:
                logger.warning(f"Failed to initialize TFLite model {self.tflite_path}: {ex}")

        # 2. Fall back to Keras model
        if self.model_path.is_file():
            try:
                import tensorflow as tf

                self._keras_model = tf.keras.models.load_model(str(self.model_path), compile=False)
                self.backend = "keras"
                logger.info(f"Loaded Keras model from {self.model_path}")
                return
            except Exception as ex:
                logger.error(f"Failed to load Keras model {self.model_path}: {ex}")

        logger.warning("No fall detection model could be loaded; predictions will return 0.0")

    def predict_sequence(self, sequence: np.ndarray) -> float:
        """Runs sequence inference on shape (time_steps, features) or (1, time_steps, features).

        Parameters:
            sequence: NumPy array of sliding window features.

        Returns:
            Probability of pre-fall / fall event in range [0.0, 1.0].
        """
        if self.backend == "none":
            return 0.0

        if sequence.ndim == 2:
            input_tensor = np.expand_dims(sequence.astype(np.float32), axis=0)
        else:
            input_tensor = sequence.astype(np.float32)

        with self._lock:
            try:
                if self.backend == "tflite" and self._tflite_interpreter is not None:
                    self._tflite_interpreter.set_tensor(
                        self._input_details[0]["index"], input_tensor
                    )
                    self._tflite_interpreter.invoke()
                    output_data = self._tflite_interpreter.get_tensor(
                        self._output_details[0]["index"]
                    )
                    return float(output_data[0][0])

                if self.backend == "keras" and self._keras_model is not None:
                    pred = self._keras_model(input_tensor, training=False)
                    return float(pred[0][0])
            except Exception as ex:
                logger.error(f"Inference execution failure ({self.backend}): {ex}")

        return 0.0

    @property
    def is_ready(self) -> bool:
        """Returns True if a valid model backend is loaded."""
        return self.backend != "none"
