"""Model training pipeline for GRU-based pre-fall sequence classification."""

from __future__ import annotations

import argparse
import glob
import logging
import os
import random
import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.layers import GRU, Dense, Dropout
from tensorflow.keras.models import Sequential

from src.fall_detection.config import GLOBAL_CONFIG

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def set_reproducibility_seed(seed: int = 42) -> None:
    """Sets random seeds across Python, NumPy, and TensorFlow for reproducible training."""
    random.seed(seed)
    np.random.seed(seed)  # Needed for TF/Keras compatibility
    tf.random.set_seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)


def load_dataset(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Loads and aggregates session CSV files from target directory.

    Returns:
        Tuple of (X, y) feature and label NumPy arrays.
    """
    if not data_dir.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {data_dir}")

    csv_files = sorted(glob.glob(str(data_dir / "session_*.csv")))
    if not csv_files:
        raise FileNotFoundError(f"No session CSV files found in {data_dir}")

    dataframes = []
    for f in csv_files:
        try:
            df_part = pd.read_csv(f)
            if not df_part.empty:
                dataframes.append(df_part)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as ex:
            logger.warning(f"Skipping unreadable CSV {f}: {ex}")

    if not dataframes:
        raise ValueError("All candidate CSV files were empty or corrupted")

    combined_df = pd.concat(dataframes, ignore_index=True)
    if "label" not in combined_df.columns:
        raise ValueError("Required 'label' target column missing from dataset")

    metadata_cols = ["timestamp", "subject_id", "input_source"]
    features_df = combined_df.drop(columns=[c for c in metadata_cols if c in combined_df.columns])

    x_raw = features_df.drop("label", axis=1).values
    y_raw = features_df["label"].values

    if np.isnan(x_raw).any() or np.isinf(x_raw).any():
        raise ValueError("Dataset contains NaN or Inf feature values")

    return x_raw, y_raw


def create_sequences_vectorized(
    x: np.ndarray, y: np.ndarray, time_steps: int
) -> tuple[np.ndarray, np.ndarray]:
    """Transforms 2D tabular features into 3D sequential sliding windows using NumPy striding.

    Parameters:
        x: Feature array of shape (N, features).
        y: Label array of shape (N,).
        time_steps: Window size for GRU sequence input.

    Returns:
        Tuple of (xs, ys) with shapes (N - time_steps, time_steps, features) and (N - time_steps,).
    """
    n_samples, n_features = x.shape
    if n_samples <= time_steps:
        raise ValueError(f"Insufficient samples ({n_samples}) for time_steps ({time_steps})")

    # Vectorized sliding window generation
    num_windows = n_samples - time_steps
    shape = (num_windows, time_steps, n_features)
    strides = (x.strides[0], x.strides[0], x.strides[1])
    xs = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides).copy()
    ys = y[time_steps:].copy()

    if np.isnan(xs).any() or np.isinf(xs).any():
        raise ValueError("Dataset contains NaN or Inf feature values after sequence creation")

    return xs, ys


def build_gru_model(
    time_steps: int,
    n_features: int,
    gru_units: str = "64,32",
    dropout: float = 0.2,
    dense_units: int = 16,
) -> Sequential:
    """Builds GRU binary classification architecture."""
    units = [int(u.strip()) for u in gru_units.split(",")]

    model = Sequential()
    model.add(
        GRU(units[0], return_sequences=(len(units) > 1), input_shape=(time_steps, n_features))
    )
    model.add(Dropout(dropout))

    for i in range(1, len(units)):
        model.add(GRU(units[i], return_sequences=(i < len(units) - 1)))
        model.add(Dropout(dropout))

    model.add(Dense(dense_units, activation="relu"))
    model.add(Dense(1, activation="sigmoid"))

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    return model


def train(
    epochs: int | None = None,
    batch_size: int | None = None,
    test_size: float = 0.2,
    seed: int = 42,
    gru_units: str = "64,32",
    dropout: float = 0.2,
    dense_units: int = 16,
) -> None:
    """Executes end-to-end model training, evaluation, and checkpoint saving."""
    set_reproducibility_seed(seed)

    epochs_val = epochs or GLOBAL_CONFIG.epochs
    batch_size_val = batch_size or GLOBAL_CONFIG.batch_size
    data_dir = (
        GLOBAL_CONFIG.clean_data_dir
        if GLOBAL_CONFIG.use_clean_data and GLOBAL_CONFIG.clean_data_dir.is_dir()
        else GLOBAL_CONFIG.raw_data_dir
    )

    logger.info(f"Loading dataset from {data_dir}...")
    x_raw, y_raw = load_dataset(data_dir)
    logger.info(f"Loaded {len(x_raw)} rows of raw feature samples.")

    xs, ys = create_sequences_vectorized(x_raw, y_raw, GLOBAL_CONFIG.time_steps)
    logger.info(f"Created {len(xs)} sequences of shape ({xs.shape[1]}, {xs.shape[2]}).")

    x_train, x_val, y_train, y_val = train_test_split(
        xs, ys, test_size=test_size, random_state=seed, stratify=ys
    )

    classes = np.unique(y_train)
    class_weights_arr = compute_class_weight(class_weight="balanced", classes=classes, y=y_train)
    class_weight_dict = dict(zip(classes, class_weights_arr, strict=False))
    logger.info(
        f"Class distribution: {np.bincount(y_train.astype(int))}, Weights: {class_weight_dict}"
    )

    model = build_gru_model(
        GLOBAL_CONFIG.time_steps,
        xs.shape[2],
        gru_units=gru_units,
        dropout=dropout,
        dense_units=dense_units,
    )
    logger.info("Starting model fit...")

    Path("checkpoints").mkdir(parents=True, exist_ok=True)
    callbacks = [
        ModelCheckpoint(
            "checkpoints/best_model.keras", save_best_only=True, monitor="val_accuracy"
        ),
        EarlyStopping(patience=5, restore_best_weights=True),
    ]

    model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=epochs_val,
        batch_size=batch_size_val,
        class_weight=class_weight_dict,
        callbacks=callbacks,
        verbose=1,
    )

    loss, accuracy = model.evaluate(x_val, y_val, verbose=0)
    logger.info(f"Validation loss: {loss:.4f}, accuracy: {accuracy * 100:.2f}%")

    output_path = GLOBAL_CONFIG.model_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(output_path))
    logger.info(f"Model saved to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Fall Detection GRU Model")
    parser.add_argument("--epochs", type=int, default=None, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Batch size for training")
    parser.add_argument("--test-size", type=float, default=0.2, help="Validation split fraction")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--gru-units", type=str, default="64,32", help="Comma-separated list of GRU units"
    )
    parser.add_argument("--dropout", type=float, default=0.2, help="Dropout rate")
    parser.add_argument("--dense-units", type=int, default=16, help="Units in the dense layer")
    args = parser.parse_args()

    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        test_size=args.test_size,
        seed=args.seed,
        gru_units=args.gru_units,
        dropout=args.dropout,
        dense_units=args.dense_units,
    )


if __name__ == "__main__":
    main()
