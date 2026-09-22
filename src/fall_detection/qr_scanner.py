"""QR Code scanner and LINE identifier extraction module."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Regular expression for 33-character LINE Destination IDs:
# U: User ID (33 chars)
# C: Group ID (33 chars)
# R: Room ID (33 chars)
LINE_ID_PATTERN = re.compile(r"\b([UCR][0-9a-fA-F]{32})\b")


def extract_line_id(raw_text: str | None) -> str | None:
    """Extracts a valid LINE User, Group, or Room ID from raw text or URLs.

    Parameters:
        raw_text: Any raw text string, URL, or message containing a LINE ID.

    Returns:
        The 33-character LINE ID if found, otherwise None.
    """
    if not raw_text or not isinstance(raw_text, str):
        return None

    cleaned = raw_text.strip()
    match = LINE_ID_PATTERN.search(cleaned)
    if match:
        return match.group(1)

    return None


def decode_qr_from_frame(
    frame: np.ndarray,
    detector: cv2.QRCodeDetector | None = None,
) -> tuple[str | None, np.ndarray | None]:
    """Detects and decodes a QR code from an OpenCV BGR video frame.

    Parameters:
        frame: Video frame in BGR format.
        detector: Optional cached cv2.QRCodeDetector instance.

    Returns:
        Tuple of (extracted_line_id, bounding_box_points).
        If no QR code or no valid LINE ID is present, extracted_line_id will be None.
    """
    if frame is None or frame.size == 0:
        return None, None

    if detector is None:
        detector = cv2.QRCodeDetector()

    try:
        data, points, _ = detector.detectAndDecode(frame)
        if data:
            line_id = extract_line_id(data)
            return line_id, points
        return None, points if points is not None and len(points) > 0 else None
    except Exception as ex:
        logger.debug("Error during QR code decoding: %s", ex)
        return None, None


def decode_qr_from_image_path(
    path: str | Path,
    detector: cv2.QRCodeDetector | None = None,
) -> str | None:
    """Loads an image from file and decodes any embedded LINE QR code.

    Parameters:
        path: Path to the image file (PNG, JPG, etc.).
        detector: Optional cached cv2.QRCodeDetector instance.

    Returns:
        Extracted LINE ID if found, otherwise None.
    """
    path_obj = Path(path)
    if not path_obj.is_file():
        logger.warning("QR image file not found: %s", path)
        return None

    img = cv2.imread(str(path_obj))
    if img is None or img.size == 0:
        logger.warning("Failed to load image from %s", path)
        return None

    line_id, _ = decode_qr_from_frame(img, detector=detector)
    return line_id
