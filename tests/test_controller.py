"""Tests for the FallEventController."""

import unittest
from unittest.mock import MagicMock, patch

from src.fall_detection.config import AppConfig
from src.fall_detection.controller import FallEventController


class TestFallEventController(unittest.TestCase):
    def setUp(self):
        self.app_config = MagicMock(spec=AppConfig)
        self.app_config.line_cooldown_seconds = 60
        self.app_config.base_dir = "/dummy/dir"
        self.controller = FallEventController(self.app_config, "dummy_token")

    @patch("src.fall_detection.controller.send_line_fall_alert_async")
    @patch("src.fall_detection.controller.create_fall_evidence_montage")
    @patch("src.fall_detection.controller.cv2.imwrite")
    @patch("src.fall_detection.controller.time.time")
    def test_process_fall_event_cooldown(self, mock_time, mock_imwrite, mock_montage, mock_send):
        mock_time.return_value = 1000.0

        mock_stream = MagicMock()
        mock_stream.save_fall_clip.return_value = "/dummy/dir/video.mp4"
        mock_stream.get_evidence_frames.return_value = [MagicMock()] * 5
        mock_stream.last_prediction = 0.95

        cfg = {"line_user_id": "user123"}

        # First call should succeed
        self.controller.process_fall_event("cam1", mock_stream, cfg)
        self.assertEqual(mock_send.call_count, 1)

        # Second call immediately after should be suppressed
        mock_time.return_value = 1010.0  # +10 seconds (cooldown is 60)
        self.controller.process_fall_event("cam1", mock_stream, cfg)
        self.assertEqual(mock_send.call_count, 1)  # Still 1

        # Call after cooldown should succeed
        mock_time.return_value = 1061.0  # +61 seconds
        self.controller.process_fall_event("cam1", mock_stream, cfg)
        self.assertEqual(mock_send.call_count, 2)

    @patch("src.fall_detection.controller.time.time")
    def test_should_alert_audio(self, mock_time):
        mock_time.return_value = 2000.0

        # First call should return True
        self.assertTrue(self.controller.should_alert_audio("cam1", cooldown=4.0))

        # Within cooldown
        mock_time.return_value = 2002.0
        self.assertFalse(self.controller.should_alert_audio("cam1", cooldown=4.0))

        # After cooldown
        mock_time.return_value = 2005.0
        self.assertTrue(self.controller.should_alert_audio("cam1", cooldown=4.0))

    @patch("src.fall_detection.controller.send_line_fall_alert_async")
    @patch("src.fall_detection.controller.create_fall_evidence_montage")
    @patch("src.fall_detection.controller.cv2.imwrite")
    @patch("src.fall_detection.controller.time.time")
    def test_process_fall_event_uses_default_user_id(
        self, mock_time, mock_imwrite, mock_montage, mock_send
    ):
        mock_time.return_value = 3000.0
        mock_stream = MagicMock()
        mock_stream.save_fall_clip.return_value = "/dummy/dir/video.mp4"
        mock_stream.get_evidence_frames.return_value = [MagicMock()] * 5
        mock_stream.last_prediction = 0.92

        # When camera cfg has no line_user_id, default_user_id is used
        self.controller.default_user_id = "global_user_789"
        cfg = {"line_user_id": "", "line_token": ""}
        self.controller.process_fall_event("cam2", mock_stream, cfg)

        self.assertEqual(mock_send.call_count, 1)
        args, kwargs = mock_send.call_args
        self.assertEqual(kwargs.get("destination_id"), "global_user_789")


if __name__ == "__main__":
    unittest.main()
