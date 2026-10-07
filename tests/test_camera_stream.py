import unittest
import time
import numpy as np
import threading
from core.camera_monitor import CameraStream, CameraMonitor

class MockApp:
    def __init__(self):
        self.fall_threshold = 0.5
        self.available_cameras = []

class TestCameraStreamDecoupled(unittest.TestCase):
    def setUp(self):
        self.app = MockApp()
        self.monitor = CameraMonitor(self.app)

    def tearDown(self):
        self.monitor.stop_all_streams()

    def test_camera_stream_initialization(self):
        stream = CameraStream(self.monitor, "TestCam", 0, width=640, height=480)
        self.assertEqual(stream.name, "TestCam")
        self.assertEqual(stream.source, 0)
        self.assertFalse(stream.is_running)
        self.assertIsNone(stream._reader_thread)
        self.assertIsNone(stream._worker_thread)

    def test_camera_stream_start_and_stop_lifecycle(self):
        stream = CameraStream(self.monitor, "TestCam", "invalid_source_123", width=640, height=480)
        stream.start()
        self.assertTrue(stream.is_running)
        self.assertIsNotNone(stream._reader_thread)
        self.assertIsNotNone(stream._worker_thread)
        self.assertTrue(stream._reader_thread.is_alive())
        self.assertTrue(stream._worker_thread.is_alive())

        # Let it run briefly to ensure no immediate crash
        time.sleep(0.3)

        # Stop stream
        stream.stop()
        self.assertFalse(stream.is_running)
        self.assertFalse(stream._reader_thread.is_alive() if stream._reader_thread else False)
        self.assertFalse(stream._worker_thread.is_alive() if stream._worker_thread else False)

    def test_camera_stream_frame_exchange_thread_safety(self):
        stream = CameraStream(self.monitor, "TestCam", "invalid_source_123", width=640, height=480)

        # Simulate feeding raw frames into the decoupled pipeline
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        with stream._raw_frame_lock:
            stream._raw_frame = dummy_frame
        stream._new_frame_event.set()

        self.assertTrue(stream._new_frame_event.is_set())
        with stream._raw_frame_lock:
            self.assertIsNotNone(stream._raw_frame)
            self.assertEqual(stream._raw_frame.shape, (480, 640, 3))


class TestCameraDiscoveryAndWatcher(unittest.TestCase):
    def test_detect_available_cameras_contract(self):
        from src.fall_detection.camera import CameraMonitor

        cams = CameraMonitor.detect_available_cameras(max_probe=2)
        self.assertIsInstance(cams, list)
        for c in cams:
            self.assertIsInstance(c, int)

    def test_detect_available_cameras_info_contract(self):
        from src.fall_detection.camera import CameraMonitor

        info = CameraMonitor.detect_available_cameras_info(max_probe=2)
        self.assertIsInstance(info, list)
        for item in info:
            self.assertIn("index", item)
            self.assertIn("name", item)
            self.assertIn("resolution", item)
            self.assertIn("display_label", item)

    def test_camera_watcher_lifecycle_and_callbacks(self):
        from src.fall_detection.camera import CameraWatcher

        watcher = CameraWatcher(interval_seconds=10.0, max_probe=2)
        received_events = []

        def callback(cams, info):
            received_events.append((cams, info))

        watcher.add_listener(callback)
        self.assertEqual(len(watcher._listeners), 1)

        # Immediate trigger scan
        cams, info = watcher.trigger_scan()
        self.assertIsInstance(cams, list)
        self.assertIsInstance(info, list)
        self.assertGreaterEqual(len(received_events), 1)
        self.assertEqual(received_events[-1][0], cams)

        # Listener removal
        watcher.remove_listener(callback)
        self.assertEqual(len(watcher._listeners), 0)

        # Test start & stop
        watcher.start()
        self.assertTrue(watcher._is_running)
        watcher.stop()
        self.assertFalse(watcher._is_running)


if __name__ == "__main__":
    unittest.main()
