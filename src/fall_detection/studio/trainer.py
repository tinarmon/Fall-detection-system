"""Asynchronous model training runner, validation evaluator, and TFLite exporter."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from scripts.train import (
    build_gru_model,
    create_sequences_vectorized,
    load_dataset,
    set_reproducibility_seed,
)
from src.fall_detection.config import GLOBAL_CONFIG

logger = logging.getLogger(__name__)


def convert_model_to_tflite(
    model: tf.keras.Model,
    output_tflite_path: Path,
    time_steps: int = 10,
    n_features: int = 20,
) -> Path:
    """Converts a trained Keras Sequential/Functional model to an optimized TFLite model."""
    output_tflite_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        # Enable default optimizations
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        # Enable Select TF Ops if custom recurrent ops are required
        converter.target_spec.supported_ops = [
            tf.lite.OpsSet.TFLITE_BUILTINS,
            tf.lite.OpsSet.SELECT_TF_OPS,
        ]
        converter._experimental_lower_tensor_list_ops = False
        tflite_model = converter.convert()

        with open(output_tflite_path, "wb") as f:
            f.write(tflite_model)

        logger.info(
            f"Successfully converted model to TFLite: {output_tflite_path} ({len(tflite_model)} bytes)"
        )
        return output_tflite_path
    except Exception as ex:
        logger.warning(f"Standard TFLite conversion fallback: {ex}")
        # Standard fallback without select ops
        converter = tf.lite.TFLiteConverter.from_keras_model(model)
        tflite_model = converter.convert()
        with open(output_tflite_path, "wb") as f:
            f.write(tflite_model)
        return output_tflite_path


class StudioTrainingCallback(tf.keras.callbacks.Callback):
    """Bridge callback forwarding training epoch metrics to UI or logging listener."""

    def __init__(
        self,
        total_epochs: int,
        on_epoch_end_fn: Callable[[int, int, float, float, float, float], None] | None = None,
    ):
        super().__init__()
        self.total_epochs = total_epochs
        self.on_epoch_end_fn = on_epoch_end_fn

    def on_epoch_end(self, epoch: int, logs: dict[str, Any] | None = None) -> None:
        if logs and self.on_epoch_end_fn:
            loss = float(logs.get("loss", 0.0))
            acc = float(logs.get("accuracy", 0.0))
            val_loss = float(logs.get("val_loss", 0.0))
            val_acc = float(logs.get("val_accuracy", 0.0))
            self.on_epoch_end_fn(epoch + 1, self.total_epochs, loss, acc, val_loss, val_acc)


class ModelTrainer:
    """Asynchronous trainer for TrainStudio."""

    def __init__(self):
        self.is_training = False
        self._thread: threading.Thread | None = None
        self._stop_requested = False

    def start_training_async(
        self,
        epochs: int = 25,
        batch_size: int = 32,
        gru_units: str = "64,32",
        dropout: float = 0.2,
        dense_units: int = 16,
        test_size: float = 0.2,
        on_progress: Callable[[int, int, float, float, float, float], None] | None = None,
        on_complete: Callable[[dict[str, Any]], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Launches training in a background daemon thread."""
        if self.is_training:
            raise RuntimeError("Training is already in progress")

        self.is_training = True
        self._stop_requested = False

        def _worker():
            try:
                results = self.train_pipeline(
                    epochs=epochs,
                    batch_size=batch_size,
                    gru_units=gru_units,
                    dropout=dropout,
                    dense_units=dense_units,
                    test_size=test_size,
                    progress_callback=on_progress,
                )
                self.is_training = False
                if on_complete:
                    on_complete(results)
            except Exception as ex:
                self.is_training = False
                logger.error(f"Training error: {ex}", exc_info=True)
                if on_error:
                    on_error(ex)

        self._thread = threading.Thread(target=_worker, name="TrainStudio_Worker", daemon=True)
        self._thread.start()

    def train_pipeline(
        self,
        epochs: int = 25,
        batch_size: int = 32,
        gru_units: str = "64,32",
        dropout: float = 0.2,
        dense_units: int = 16,
        test_size: float = 0.2,
        seed: int = 42,
        progress_callback: Callable[[int, int, float, float, float, float], None] | None = None,
    ) -> dict[str, Any]:
        """Runs the complete training and validation pipeline."""
        set_reproducibility_seed(seed)
        data_dir = (
            GLOBAL_CONFIG.clean_data_dir
            if GLOBAL_CONFIG.use_clean_data and GLOBAL_CONFIG.clean_data_dir.is_dir()
            else GLOBAL_CONFIG.raw_data_dir
        )

        logger.info(f"TrainStudio: Loading dataset from {data_dir}")
        x_raw, y_raw = load_dataset(data_dir)
        total_raw_samples = len(x_raw)

        xs, ys = create_sequences_vectorized(x_raw, y_raw, GLOBAL_CONFIG.time_steps)
        n_features = xs.shape[2]

        x_train, x_val, y_train, y_val = train_test_split(
            xs, ys, test_size=test_size, random_state=seed, stratify=ys
        )

        classes = np.unique(y_train)
        class_weights_arr = compute_class_weight(
            class_weight="balanced", classes=classes, y=y_train
        )
        class_weight_dict = dict(zip(classes, class_weights_arr, strict=False))

        model = build_gru_model(
            GLOBAL_CONFIG.time_steps,
            n_features,
            gru_units=gru_units,
            dropout=dropout,
            dense_units=dense_units,
        )

        callbacks: list[tf.keras.callbacks.Callback] = [
            StudioTrainingCallback(total_epochs=epochs, on_epoch_end_fn=progress_callback),
            tf.keras.callbacks.EarlyStopping(
                patience=6, monitor="val_loss", restore_best_weights=True
            ),
        ]

        history = model.fit(
            x_train,
            y_train,
            validation_data=(x_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            class_weight=class_weight_dict,
            callbacks=callbacks,
            verbose=1,
        )

        val_loss, val_acc = model.evaluate(x_val, y_val, verbose=0)
        y_pred_probs = model.predict(x_val, verbose=0)
        y_pred = (y_pred_probs >= GLOBAL_CONFIG.fall_threshold).astype(int).flatten()

        cm = confusion_matrix(y_val, y_pred)
        report = classification_report(y_val, y_pred, output_dict=True, zero_division=0)

        # Save Keras model
        output_keras_path = GLOBAL_CONFIG.model_path
        output_keras_path.parent.mkdir(parents=True, exist_ok=True)
        model.save(str(output_keras_path))

        # Save TFLite model
        output_tflite_path = GLOBAL_CONFIG.tflite_model_path
        convert_model_to_tflite(model, output_tflite_path, GLOBAL_CONFIG.time_steps, n_features)

        return {
            "total_raw_samples": total_raw_samples,
            "total_sequences": len(xs),
            "val_loss": float(val_loss),
            "val_accuracy": float(val_acc),
            "confusion_matrix": cm.tolist(),
            "classification_report": report,
            "keras_path": str(output_keras_path),
            "tflite_path": str(output_tflite_path),
            "history": {
                "loss": [float(v) for v in history.history.get("loss", [])],
                "accuracy": [float(v) for v in history.history.get("accuracy", [])],
                "val_loss": [float(v) for v in history.history.get("val_loss", [])],
                "val_accuracy": [float(v) for v in history.history.get("val_accuracy", [])],
            },
        }
