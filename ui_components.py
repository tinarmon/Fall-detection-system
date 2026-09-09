"""Backwards-compatibility facade delegating to src.fall_detection.ui.components."""

from __future__ import annotations

from src.fall_detection.ui.components import (
    AppFonts,
    BaseModalDialog,
    CardFrame,
    DangerButton,
    EmptyCameraSlot,
    IconButton,
    PrimaryButton,
    SecondaryButton,
    StyledButton,
    ToastBanner,
    Tooltip,
    convert_cv2_to_tk_image,
)

__all__ = [
    "convert_cv2_to_tk_image",
    "Tooltip",
    "StyledButton",
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "IconButton",
    "CardFrame",
    "BaseModalDialog",
    "EmptyCameraSlot",
    "ToastBanner",
    "AppFonts",
]
