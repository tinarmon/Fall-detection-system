"""Tests for the notification module."""

from unittest.mock import MagicMock, patch

import numpy as np

from src.fall_detection.notification import (
    create_fall_alert_flex,
    create_fall_evidence_montage,
    send_line_push_message,
)


def test_create_fall_evidence_montage():
    frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
    montage = create_fall_evidence_montage(frames, "cam-1", "12:00:00")

    assert montage.shape == (720, 640, 3)


def test_create_fall_alert_flex():
    flex = create_fall_alert_flex("cam-1", "12:00:00")

    # We test that the dict returned represents a flex message bubble
    assert "type" in flex
    assert flex["type"] == "bubble"

    assert "body" in flex
    assert "header" in flex

    # Verify the wrapper adds required keys type, altText, contents
    # This structure is created inside send_line_push_message
    wrapper = {
        "type": "flex",
        "altText": "🚨 แจ้งเตือนสภาวะเสี่ยงล้ม (AI Fall Alert)",
        "contents": flex,
    }
    assert wrapper["type"] == "flex"
    assert "altText" in wrapper
    assert wrapper["contents"] == flex


@patch("urllib.request.urlopen")
def test_send_line_push_message_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    success = send_line_push_message("token", "user1", "alert")
    assert success is True


@patch("urllib.request.urlopen")
def test_send_line_push_message_error(mock_urlopen):
    import urllib.error

    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="http://test.com", code=500, msg="Error", hdrs={}, fp=None
    )

    success = send_line_push_message("token", "user1", "alert")
    assert success is False
