"""Tests for QR code scanner and LINE ID extraction module."""

from unittest.mock import MagicMock, patch

import numpy as np

from src.fall_detection.qr_scanner import (
    decode_qr_from_frame,
    decode_qr_from_image_path,
    extract_line_id,
)


def test_extract_line_id_valid_user():
    uid = "U4af4980629bc48074da88439df67d8f3"
    assert extract_line_id(uid) == uid


def test_extract_line_id_valid_group():
    gid = "C1234567890abcdef1234567890abcdef"
    assert extract_line_id(gid) == gid


def test_extract_line_id_valid_room():
    rid = "Rabcdef1234567890abcdef1234567890"
    assert extract_line_id(rid) == rid


def test_extract_line_id_dirty_thai_text():
    raw = "🛡️ [ระบบแจ้งเตือนภัยล้ม AI Alert]\n\nUser ID ของคุณคือ:\nU4af4980629bc48074da88439df67d8f3\n\n👉 คัดลอกรหัสไปใช้งานได้เลย"
    assert extract_line_id(raw) == "U4af4980629bc48074da88439df67d8f3"


def test_extract_line_id_in_url():
    url = "https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=U4af4980629bc48074da88439df67d8f3"
    assert extract_line_id(url) == "U4af4980629bc48074da88439df67d8f3"


def test_extract_line_id_invalid_strings():
    assert extract_line_id("") is None
    assert extract_line_id(None) is None
    assert extract_line_id("hello world") is None
    # Too short
    assert extract_line_id("U123456789") is None
    # Invalid prefix
    assert extract_line_id("X4af4980629bc48074da88439df67d8f3") is None
    # Invalid hex characters (z, y)
    assert extract_line_id("U4af4980629bc48074da88439df67d8zz") is None


def test_decode_qr_from_empty_frame():
    assert decode_qr_from_frame(None) == (None, None)
    assert decode_qr_from_frame(np.array([])) == (None, None)


def test_decode_qr_from_frame_with_mock():
    mock_detector = MagicMock()
    points = np.array([[[10, 10], [100, 10], [100, 100], [10, 100]]])
    mock_detector.detectAndDecode.return_value = (
        "U4af4980629bc48074da88439df67d8f3",
        points,
        None,
    )

    dummy_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    line_id, returned_points = decode_qr_from_frame(dummy_frame, detector=mock_detector)

    assert line_id == "U4af4980629bc48074da88439df67d8f3"
    assert returned_points is not None


def test_decode_qr_from_frame_unrelated_content():
    mock_detector = MagicMock()
    mock_detector.detectAndDecode.return_value = ("https://google.com", None, None)

    dummy_frame = np.zeros((200, 200, 3), dtype=np.uint8)
    line_id, returned_points = decode_qr_from_frame(dummy_frame, detector=mock_detector)

    assert line_id is None


def test_decode_qr_from_image_path_missing_file():
    assert decode_qr_from_image_path("non_existent_image_path_12345.png") is None


def test_decode_qr_from_image_path_valid():
    mock_img = np.zeros((200, 200, 3), dtype=np.uint8)
    mock_detector = MagicMock()
    mock_detector.detectAndDecode.return_value = (
        "U4af4980629bc48074da88439df67d8f3",
        None,
        None,
    )

    with (
        patch("pathlib.Path.is_file", return_value=True),
        patch("cv2.imread", return_value=mock_img),
    ):
        result = decode_qr_from_image_path("test.png", detector=mock_detector)
        assert result == "U4af4980629bc48074da88439df67d8f3"
