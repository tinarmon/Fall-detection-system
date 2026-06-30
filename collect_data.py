import cv2
import csv
import os
import re
import sys
import time
import datetime
from core.pose_estimator import PoseEstimator
from core.angle_calculator import AngleCalculator
import config

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def get_valid_subject_id():
    while True:
        subject_id = input("กรุณากรอก Subject ID หรือ ชื่อผู้ทดสอบ (ภาษาอังกฤษ/ตัวเลข): ").strip()
        if not subject_id:
            print("Subject ID ห้ามว่างเปล่า กรุณากรอกใหม่อีกครั้ง")
            continue
        if not re.match(r"^[a-zA-Z0-9_-]+$", subject_id):
            print("Subject ID มีตัวอักษรที่ไม่ได้รับอนุญาต ให้ใช้เฉพาะภาษาอังกฤษ ตัวเลข ขีดล่าง (_) และขีดกลาง (-) เท่านั้น")
            continue
        return subject_id

def run_collection():
    print("=" * 50)
    print("[DATA] โหมดเก็บข้อมูลการเคลื่อนไหว (Data Ingestion Mode)")
    print("=" * 50)

    subject_id = get_valid_subject_id()
    
    print("\nกรุณาเลือกแหล่งข้อมูลป้อนเข้า:")
    print("[1] กล้อง Webcam (Real-time Webcam Stream)")
    print("[2] ไฟล์วิดีโอในเครื่อง (Local Video File)")
    
    while True:
        choice = input("กรอกตัวเลือก (1 หรือ 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("ตัวเลือกไม่ถูกต้อง กรุณากรอก 1 หรือ 2")

    is_webcam = (choice == "1")
    global_label = None

    if is_webcam:
        input_source = "webcam"
        print("\nระบบกำลังเชื่อมต่อกล้อง...")
        cap = cv2.VideoCapture(config.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        time.sleep(1)
    else:
        while True:
            video_path = input("\nลากไฟล์วิดีโอมาวางที่นี่ หรือกรอกที่อยู่ไฟล์: ").strip()
            # ตัดเครื่องหมายคำพูดหากมีจากการลากวางไฟล์
            video_path = video_path.strip("'\"")
            
            if os.path.isfile(video_path):
                input_source = os.path.basename(video_path)
                cap = cv2.VideoCapture(video_path)
                break
            print(f"ไม่พบไฟล์: '{video_path}' กรุณาตรวจสอบและกรอกใหม่อีกครั้ง")
        
        while True:
            label_input = input("ระบุป้ายกำกับ (Label) สำหรับวิดีโอนี้ (0 = ท่าปกติ, 1 = ท่าล้ม/เสียการทรงตัว): ").strip()
            if label_input in ["0", "1"]:
                global_label = int(label_input)
                break
            print("กรุณากรอกเฉพาะ 0 หรือ 1 เท่านั้น")

    if not cap.isOpened():
        print("[ERROR] ไม่สามารถเชื่อมต่อกล้องหรือเปิดไฟล์วิดีโอได้")
        input("กด Enter เพื่อกลับเมนูหลัก...")
        return

    estimator = PoseEstimator(config.POSE_TASK_PATH)
    calculator = AngleCalculator()

    window_name = config.COLLECT_WINDOW_NAME
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)

    # สร้างชื่อไฟล์เก็บข้อมูลและเตรียม header
    timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{subject_id}_{timestamp_str}.csv"
    os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
    filepath = os.path.join(config.RAW_DATA_DIR, filename)

    header = ['timestamp', 'subject_id', 'input_source', 'label', 'left_angle', 'right_angle']
    for target in config.TARGET_LANDMARKS:
        header.extend([f'x{target}', f'y{target}'])

    # Atomic Buffer ในแรม
    frame_buffer = []

    print("\n--- เริ่มขั้นตอนการสกัดเฟรมข้อมูล ---")
    if is_webcam:
        print("- กด 'n' = บันทึกท่าปกติ (NORMAL | Label: 0)")
        print("- กด 'f' = บันทึกท่าเสียการทรงตัว (FALL | Label: 1)")
        print("- กด 'p' หรือ 'Spacebar' = หยุดบันทึกชั่วคราว (PAUSE)")
        print("- กด 'q' หรือ 'ESC' = บันทึกข้อมูลลงดิสก์และกลับสู่เมนูหลัก\n")
        current_mode = "PAUSED"
    else:
        print("- วิดีโอจะทำการบันทึกพิกัดและมุมอัตโนมัติด้วย Label:", global_label)
        print("- กด 'p' หรือ 'Spacebar' = หยุดเล่นวิดีโอชั่วคราว (PAUSE)")
        print("- กด 'q' หรือ 'ESC' = บันทึกข้อมูลเท่าที่ได้และกลับสู่เมนูหลัก\n")
        current_mode = "RECORDING"

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) if not is_webcam else -1
    frame_idx = 0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_idx += 1
            processed_frame, points_px, points_norm = estimator.process_frame(frame)
            
            left_angle, right_angle = 0.0, 0.0
            is_valid_pose = False

            if points_px:
                if all(k in points_px for k in config.TARGET_LANDMARKS):
                    is_valid_pose = True
                    left_angle = calculator.calculate_angle(points_px[11], points_px[23], points_px[25])
                    right_angle = calculator.calculate_angle(points_px[12], points_px[24], points_px[26])
                    
                    cv2.putText(processed_frame, f"L:{int(left_angle)}", (points_px[23][0]+20, points_px[23][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(processed_frame, f"R:{int(right_angle)}", (points_px[24][0]-80, points_px[24][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

            key = cv2.waitKey(10)
            
            if is_webcam:
                if key == ord('n') or key == ord('ช'):
                    current_mode = "NORMAL"
                elif key == ord('f') or key == ord('ด'):
                    current_mode = "FALL"
                elif key == ord('p') or key == ord('ย') or key == 32:
                    current_mode = "PAUSED"
                elif key == ord('q') or key == ord('ๆ') or (key & 0xFF == ord('q')) or key == 27:
                    break

                status_text = "PAUSED (Press N or F to Start)"
                color = (0, 0, 255)

                if current_mode == "NORMAL":
                    status_text = f"Recording: NORMAL (0) | Subject: {subject_id}"
                    color = (0, 255, 0)
                    if is_valid_pose:
                        row_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        row_data = [row_timestamp, subject_id, input_source, 0, left_angle / 180.0, right_angle / 180.0]
                        for target in config.TARGET_LANDMARKS:
                            row_data.extend([points_norm[target][0], points_norm[target][1]])
                        frame_buffer.append(row_data)

                elif current_mode == "FALL":
                    status_text = f"Recording: FALL (1) | Subject: {subject_id}"
                    color = (0, 165, 255)
                    if is_valid_pose:
                        row_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        row_data = [row_timestamp, subject_id, input_source, 1, left_angle / 180.0, right_angle / 180.0]
                        for target in config.TARGET_LANDMARKS:
                            row_data.extend([points_norm[target][0], points_norm[target][1]])
                        frame_buffer.append(row_data)
            else:
                if key == ord('p') or key == ord('ย') or key == 32:
                    if current_mode == "RECORDING":
                        current_mode = "PAUSED"
                    else:
                        current_mode = "RECORDING"
                elif key == ord('q') or key == ord('ๆ') or (key & 0xFF == ord('q')) or key == 27:
                    break

                if current_mode == "RECORDING":
                    status_text = f"Video: {frame_idx}/{total_frames} | Auto-Label: {global_label}"
                    color = (0, 255, 0)
                    if is_valid_pose:
                        row_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                        row_data = [row_timestamp, subject_id, input_source, global_label, left_angle / 180.0, right_angle / 180.0]
                        for target in config.TARGET_LANDMARKS:
                            row_data.extend([points_norm[target][0], points_norm[target][1]])
                        frame_buffer.append(row_data)
                else:
                    status_text = f"PAUSED Playback: {frame_idx}/{total_frames}"
                    color = (0, 0, 255)
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx - 1)
                    frame_idx -= 1
                    time.sleep(0.05)

            cv2.putText(processed_frame, status_text, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.imshow(window_name, processed_frame)

    finally:
        cap.release()
        cv2.destroyAllWindows()

        if frame_buffer:
            print(f"\nกำลังบันทึก {len(frame_buffer)} เฟรมข้อมูลลงดิสก์...")
            try:
                with open(filepath, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(frame_buffer)
                print(f"[OK] บันทึกข้อมูลเซสชันสำเร็จ: '{filepath}'")
            except Exception as e:
                print(f"[ERROR] มีข้อผิดพลาดในการเขียนไฟล์: {e}")
        else:
            print("\n[WARNING] ไม่มีข้อมูลการเคลื่อนไหวที่ถูกบันทึกในเซสชันนี้")
        
        input("\nกด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_collection()