import os
import cv2
import time
import glob
import threading
from collections import deque

class FallRecorder:
    def __init__(self, output_dir="recorded_falls", max_frames=150):
        self.output_dir = output_dir
        self.max_frames = max_frames
        self.frame_buffer = deque(maxlen=max_frames)
        self.max_dir_size_bytes = 500 * 1024 * 1024  # 500 MB Default Limit
        self.lock = threading.Lock()
        
        # Ensure output dir exists
        os.makedirs(self.output_dir, exist_ok=True)

    def write_frame(self, frame):
        if frame is not None:
            with self.lock:
                self.frame_buffer.append(frame.copy())

    def save_recording(self, cam_name, width, height, fps=30.0):
        # Create output filename using current Unix timestamp
        timestamp = int(time.time())
        filename = f"fall_{cam_name}_{timestamp}.avi"
        filepath = os.path.join(self.output_dir, filename)
        
        # Capture current snapshot of frame buffer under lock
        with self.lock:
            frames_snapshot = list(self.frame_buffer)
            
        if not frames_snapshot:
            # Nothing to record
            # Create a mock empty file just in case or return immediately
            return filepath
            
        # Spawn thread to compile video asynchronously to prevent blocking the GUI/camera thread
        threading.Thread(
            target=self._write_video_worker, 
            args=(filepath, frames_snapshot, width, height, fps), 
            daemon=True
        ).start()
        
        return filepath

    def _write_video_worker(self, filepath, frames, width, height, fps):
        try:
            # 1. Run storage cleanup before writing new video
            self._run_cleanup_policy()
            
            # 2. Write video using XVID codec
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(filepath, fourcc, fps, (width, height))
            
            for frame in frames:
                # Double check dimension matching, resize if necessary
                h, w, _ = frame.shape
                if w != width or h != height:
                    frame = cv2.resize(frame, (width, height))
                out.write(frame)
                
            out.release()
        except Exception as e:
            print(f"Error saving fall recording: {e}")

    def _run_cleanup_policy(self):
        try:
            now = time.time()
            seven_days_seconds = 7 * 86400
            
            # Find all recorder files
            pattern = os.path.join(self.output_dir, "fall_*.*")
            files = glob.glob(pattern)
            
            # Map files to their stats: (filepath, size, modification_time)
            file_stats = []
            for f in files:
                try:
                    mtime = os.path.getmtime(f)
                    size = os.path.getsize(f)
                    
                    # Delete files older than 7 days immediately
                    if now - mtime > seven_days_seconds:
                        os.remove(f)
                        continue
                        
                    file_stats.append((f, size, mtime))
                except OSError:
                    pass
            
            # Sort files by modification time (oldest first)
            file_stats.sort(key=lambda x: x[2])
            
            # Check directory size limit
            total_size = sum(x[1] for x in file_stats)
            while total_size > self.max_dir_size_bytes and file_stats:
                oldest_file, size, _ = file_stats.pop(0)
                try:
                    os.remove(oldest_file)
                    total_size -= size
                except OSError:
                    pass
                    
        except Exception as e:
            print(f"Error running cleanup policy: {e}")
