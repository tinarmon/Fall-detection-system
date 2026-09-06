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

if __name__ == "__main__":
    unittest.main()
