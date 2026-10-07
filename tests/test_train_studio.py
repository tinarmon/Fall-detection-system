"""Tests for TrainStudio recorder, augmentor, trainer, and inference engine."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.fall_detection.engine import ModelInferenceEngine
from src.fall_detection.studio.augmentation import DatasetAugmentor
from src.fall_detection.studio.recorder import FEATURE_COLUMNS, StudioSessionRecorder


def test_studio_session_recorder_lifecycle():
    recorder = StudioSessionRecorder(subject_id="TestSubject", input_source="test_cam")
    assert not recorder.is_recording
    assert recorder.current_label == 0
    assert len(recorder.recorded_rows) == 0

    recorder.start_recording(label=1)
    assert recorder.is_recording
    assert recorder.current_label == 1

    # Simulate blank frame
    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    processed_frame, valid_pose, telemetry = recorder.process_frame(blank_frame)

    assert processed_frame.shape == (480, 640, 3)
    assert "left_angle" in telemetry
    assert "right_angle" in telemetry
    assert telemetry["label"] == 1

    count = recorder.stop_recording()
    assert not recorder.is_recording
    assert count == len(recorder.recorded_rows)


def test_studio_session_recorder_save(tmp_path: Path):
    recorder = StudioSessionRecorder(subject_id="TestSub", input_source="test_cam")

    # Manually append a sample row
    sample_row = ["2026-10-07 12:00:00.000", "TestSub", "test_cam", 0, 1.57, 1.57] + [0.1] * 18
    recorder.recorded_rows.append(sample_row)

    saved_path = recorder.save_session(output_dir=tmp_path, session_name="Unit_Test")
    assert saved_path.is_file()

    df = pd.read_csv(saved_path)
    assert len(df) == 1
    assert list(df.columns) == FEATURE_COLUMNS
    assert df["label"].iloc[0] == 0


def test_dataset_augmentor(tmp_path: Path):
    # Create sample session CSV
    df = pd.DataFrame(
        {
            "timestamp": ["2026-10-07 12:00:00.000", "2026-10-07 12:00:00.033"],
            "subject_id": ["SubA", "SubA"],
            "input_source": ["cam0", "cam0"],
            "label": [1, 1],
            "left_angle": [1.2, 1.3],
            "right_angle": [1.4, 1.5],
            "x11": [0.1, 0.12],
            "y11": [0.2, 0.22],
            "z11": [0.3, 0.32],
            "x12": [0.4, 0.42],
            "y12": [0.5, 0.52],
            "z12": [0.6, 0.62],
            "x23": [0.1, 0.12],
            "y23": [0.2, 0.22],
            "z23": [0.3, 0.32],
            "x24": [0.4, 0.42],
            "y24": [0.5, 0.52],
            "z24": [0.6, 0.62],
            "x25": [0.1, 0.12],
            "y25": [0.2, 0.22],
            "z25": [0.3, 0.32],
            "x26": [0.4, 0.42],
            "y26": [0.5, 0.52],
            "z26": [0.6, 0.62],
        }
    )
    csv_file = tmp_path / "session_SubA_test.csv"
    df.to_csv(csv_file, index=False)

    augmentor = DatasetAugmentor(target_dir=tmp_path)
    summary = augmentor.get_dataset_summary()
    assert summary["total_files"] == 1
    assert summary["total_samples"] == 2
    assert summary["fall_samples"] == 2

    created = augmentor.augment_file(csv_file, num_variations=2)
    assert len(created) == 2
    for cf in created:
        assert cf.is_file()


def test_model_inference_engine_fallback():
    engine = ModelInferenceEngine(
        model_path=Path("non_existent_model.keras"),
        tflite_path=Path("non_existent_model.tflite"),
    )
    assert not engine.is_ready

    dummy_seq = np.zeros((10, 20), dtype=np.float32)
    pred = engine.predict_sequence(dummy_seq)
    assert pred == 0.0
