"""Backwards-compatibility facade for CameraStream, CameraMonitor, and alert helpers."""

from __future__ import annotations

from src.fall_detection.camera import (
    CameraMonitor,
    CameraStream,
    load_trained_model,
    model_lock,
    shared_model,
)
from src.fall_detection.notification import (
    create_fall_alert_flex,
    create_fall_evidence_montage,
    send_line_fall_alert_async,
    send_line_notify,
    send_line_notify_async,
    send_line_push_async,
    send_line_push_message,
    upload_evidence_image,
)

__all__ = [
    "CameraStream",
    "CameraMonitor",
    "load_trained_model",
    "model_lock",
    "shared_model",
    "create_fall_evidence_montage",
    "upload_evidence_image",
    "create_fall_alert_flex",
    "send_line_fall_alert_async",
    "send_line_push_message",
    "send_line_push_async",
    "send_line_notify",
    "send_line_notify_async",
]
