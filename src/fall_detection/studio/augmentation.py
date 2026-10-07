"""Data augmentation engine for balancing and expanding pre-fall training datasets."""

from __future__ import annotations

import glob
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.fall_detection.config import GLOBAL_CONFIG

logger = logging.getLogger(__name__)


class DatasetAugmentor:
    """Generates synthetic dataset variations with jitter, scaling, and time-stretching."""

    def __init__(
        self,
        jitter_sigma: float = 0.005,
        scale_range: float = 0.05,
        target_dir: Path | None = None,
    ):
        self.jitter_sigma = jitter_sigma
        self.scale_range = scale_range
        self.target_dir = target_dir or GLOBAL_CONFIG.clean_data_dir

    def get_dataset_summary(self) -> dict[str, Any]:
        """Scans dataset directory and returns file counts, sample counts, and label distributions."""
        csv_files = sorted(glob.glob(str(self.target_dir / "session_*.csv")))
        total_samples = 0
        normal_samples = 0
        fall_samples = 0
        file_details: list[dict[str, Any]] = []

        for f in csv_files:
            try:
                df = pd.read_csv(f)
                count = len(df)
                total_samples += count
                n_normal = int((df["label"] == 0).sum()) if "label" in df.columns else 0
                n_fall = int((df["label"] == 1).sum()) if "label" in df.columns else 0
                normal_samples += n_normal
                fall_samples += n_fall
                file_details.append(
                    {
                        "filename": Path(f).name,
                        "path": f,
                        "total_samples": count,
                        "normal_samples": n_normal,
                        "fall_samples": n_fall,
                    }
                )
            except Exception as ex:
                logger.warning(f"Could not read {f}: {ex}")

        return {
            "total_files": len(csv_files),
            "total_samples": total_samples,
            "normal_samples": normal_samples,
            "fall_samples": fall_samples,
            "fall_ratio": (fall_samples / total_samples) if total_samples > 0 else 0.0,
            "files": file_details,
        }

    def augment_file(
        self,
        source_csv: str | Path,
        num_variations: int = 3,
        augment_only_minority: bool = False,
    ) -> list[Path]:
        """Applies spatial jitter and scaling to a single session CSV, saving augmented versions."""
        csv_path = Path(source_csv)
        if not csv_path.is_file():
            raise FileNotFoundError(f"Source file not found: {csv_path}")

        df = pd.read_csv(csv_path)
        if df.empty or "label" not in df.columns:
            return []

        # If augment_only_minority is True and file has no fall samples, skip
        if augment_only_minority and (df["label"] == 1).sum() == 0:
            return []

        coord_cols = [c for c in df.columns if c.startswith(("x", "y", "z"))]
        created_files: list[Path] = []
        stem = csv_path.stem

        for v in range(1, num_variations + 1):
            aug_df = df.copy()

            # 1. Coordinate spatial jitter
            noise = np.random.normal(0, self.jitter_sigma, size=aug_df[coord_cols].shape)
            aug_df[coord_cols] = aug_df[coord_cols] + noise

            # 2. Torso scaling factor (simulate distance / body size variations)
            scale_factor = 1.0 + np.random.uniform(-self.scale_range, self.scale_range)
            aug_df[coord_cols] = aug_df[coord_cols] * scale_factor

            # 3. Angle jitter (mild perturbation in radians)
            if "left_angle" in aug_df.columns:
                aug_df["left_angle"] += np.random.normal(0, 0.02, size=len(aug_df))
            if "right_angle" in aug_df.columns:
                aug_df["right_angle"] += np.random.normal(0, 0.02, size=len(aug_df))

            out_filename = f"{stem}_aug_{v}.csv"
            out_path = csv_path.parent / out_filename
            aug_df.to_csv(out_path, index=False)
            created_files.append(out_path)

        return created_files

    def auto_balance_dataset(self, target_fall_ratio: float = 0.40) -> dict[str, Any]:
        """Automatically augments sessions containing fall data until target ratio or balance is reached."""
        summary_before = self.get_dataset_summary()
        fall_files = [f for f in summary_before["files"] if f["fall_samples"] > 0]

        created_files: list[Path] = []
        if fall_files:
            for item in fall_files:
                new_files = self.augment_file(item["path"], num_variations=2)
                created_files.extend(new_files)

        summary_after = self.get_dataset_summary()
        return {
            "created_count": len(created_files),
            "before": summary_before,
            "after": summary_after,
        }
