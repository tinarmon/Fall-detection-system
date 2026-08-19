import os
import shutil
import unittest
import numpy as np
import time
from core.fall_recorder import FallRecorder

class TestFallRecorder(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_recorded_falls")
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_buffer_recording_and_saving(self):
        # Initialize recorder with a small max size of 30 frames (1 second at 30 fps)
        recorder = FallRecorder(output_dir=self.test_dir, max_frames=30)
        
        # Buffer 40 frames of dummy images (should keep only the last 30)
        for i in range(40):
            frame = np.zeros((240, 320, 3), dtype=np.uint8)
            # draw a simple counter to make them distinct
            import cv2
            cv2.putText(frame, str(i), (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            recorder.write_frame(frame)
            
        self.assertEqual(len(recorder.frame_buffer), 30)
        
        # Trigger async save
        filepath = recorder.save_recording(cam_name="test_cam", width=320, height=240, fps=30)
        
        # Wait up to 3 seconds for the async thread to finish writing
        for _ in range(30):
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                break
            time.sleep(0.1)
            
        self.assertTrue(os.path.exists(filepath), f"File {filepath} was not created")
        self.assertTrue(os.path.getsize(filepath) > 0, f"File {filepath} is empty")

    def test_auto_cleanup_policy(self):
        # Initialize recorder with a custom small size limit of 100 KB
        recorder = FallRecorder(output_dir=self.test_dir)
        recorder.max_dir_size_bytes = 100 * 1024 # 100 KB
        
        # Create a mock file inside output_dir that is 80 KB
        file1 = os.path.join(self.test_dir, "fall_cam1_1787000000.avi")
        with open(file1, "wb") as f:
            f.write(b"\0" * (80 * 1024))
            
        # Modify time to make file1 older
        os.utime(file1, (time.time() - 3600, time.time() - 3600))
        
        # Run cleanup. Total size is 80KB (under 100KB), so file1 should stay
        recorder._run_cleanup_policy()
        self.assertTrue(os.path.exists(file1))
        
        # Create another file of 40 KB (total size becomes 120KB, exceeding 100KB limit)
        file2 = os.path.join(self.test_dir, "fall_cam1_1787000010.avi")
        with open(file2, "wb") as f:
            f.write(b"\0" * (40 * 1024))
            
        # Run cleanup. Total is 120KB, so the oldest file (file1) should be deleted!
        recorder._run_cleanup_policy()
        self.assertFalse(os.path.exists(file1), "Old file was not cleaned up")
        self.assertTrue(os.path.exists(file2), "New file was deleted incorrectly")

if __name__ == "__main__":
    unittest.main()
