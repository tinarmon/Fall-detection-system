"""TrainStudio package for dataset recording, augmentation, and model training."""

from src.fall_detection.studio.augmentation import DatasetAugmentor
from src.fall_detection.studio.recorder import StudioSessionRecorder
from src.fall_detection.studio.trainer import ModelTrainer

__all__ = ["StudioSessionRecorder", "DatasetAugmentor", "ModelTrainer"]
