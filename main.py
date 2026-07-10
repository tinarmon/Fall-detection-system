import os
import sys
import time

# Reconfigure stdout/stderr to use UTF-8 to prevent encoding errors on Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

try:
    import config
    from collect_data import run_collection
    from analyze_features import run_analysis
    from train_model import run_training
    from live_inference import run_inference
    from normalize_data import run_normalization
except ImportError as e:
    print(f"[ERROR] Error importing core modules: {e}")
    sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def check_diagnostics():
    print("=" * 50)
    print("[DIAGNOSTICS] ระบบตรวจสอบสถานะและทรัพยากร (Metadata Diagnostics)")
    print("=" * 50)
    
    model_exists = os.path.isfile(config.MODEL_PATH)
    pose_task_exists = os.path.isfile(config.POSE_TASK_PATH)
    
    print(f"1. AI Model Path: '{config.MODEL_PATH}'")
    if model_exists:
        size_kb = os.path.getsize(config.MODEL_PATH) / 1024
        print(f"   [OK] ไฟล์โมเดลมีอยู่จริง (ขนาด: {size_kb:.2f} KB)")
    else:
        print("   [MISSING] [ERROR] ไม่พบไฟล์โมเดลกรุณาเทรนโมเดลเพื่อสร้างไฟล์ก่อน")
        
    print(f"2. MediaPipe Pose Task Path: '{config.POSE_TASK_PATH}'")
    if pose_task_exists:
        size_mb = os.path.getsize(config.POSE_TASK_PATH) / (1024 * 1024)
        print(f"   [OK] ไฟล์โมเดลมีอยู่จริง (ขนาด: {size_mb:.2f} MB)")
    else:
        print("   [MISSING] [ERROR] ไม่พบไฟล์ MediaPipe Pose Task กรุณาดาวน์โหลดหรือวางไว้ที่โฟลเดอร์ assets/")
        
    raw_data_dir = config.RAW_DATA_DIR
    raw_data_exists = os.path.exists(raw_data_dir)
    print(f"3. Raw Data Directory: '{raw_data_dir}'")
    if raw_data_exists:
        import glob
        session_files = glob.glob(os.path.join(raw_data_dir, "session_*.csv"))
        print(f"   [OK] โฟลเดอร์มีอยู่จริง (พบไฟล์เซสชันดิบ: {len(session_files)} ไฟล์)")
    else:
        print("   [INFO] ยังไม่มีการสร้างโฟลเดอร์เก็บข้อมูลดิบ (จะถูกสร้างเมื่อเริ่มบันทึกข้อมูล)")

    clean_data_dir = config.CLEAN_DATA_DIR
    clean_data_exists = os.path.exists(clean_data_dir)
    print(f"4. Clean Data Directory: '{clean_data_dir}'")
    if clean_data_exists:
        import glob
        clean_session_files = glob.glob(os.path.join(clean_data_dir, "session_*.csv"))
        print(f"   [OK] โฟลเดอร์มีอยู่จริง (พบไฟล์เซสชันสะอาด: {len(clean_session_files)} ไฟล์)")
    else:
        print("   [INFO] ยังไม่มีการทำความสะอาดข้อมูลดิบ (สามารถเลือกเมนู 6 เพื่อทำความสะอาดได้)")

    input("\nกด Enter เพื่อกลับสู่เมนูหลัก...")

def main():
    while True:
        clear_screen()
        print("==================================================")
        print("Pre-Fall Detection System using MediaPipe & GRU")
        print("==================================================")
        print("กรุณาเลือกโหมดการทำงาน:")
        print("[1] เก็บข้อมูลการเคลื่อนไหว (Data Acquisition)")
        print("[2] วิเคราะห์ข้อมูลสถิติฟีเจอร์ (Feature Engineering)")
        print("[3] ฝึกสอนโมเดลสมองเทียม AI (Model Training)")
        print("[4] ตรวจจับความเสี่ยงแบบเรียลไทม์ (Real-time Tracking)")
        print("[5] ตรวจสอบสถานะระบบ (Metadata Diagnostics)")
        print("[6] ทำความสะอาดและปรับปรุงข้อมูลดิบ (Clean & Normalize Data)")
        print("[0] ออกจากโปรแกรม (Exit)")
        print("==================================================")
        
        choice = input("ป้อนตัวเลือกของคุณ (0-6): ").strip()
        
        if choice == "1":
            clear_screen()
            try:
                run_collection()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในโหมดเก็บข้อมูล: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "2":
            clear_screen()
            try:
                run_analysis()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในโหมดวิเคราะห์คุณลักษณะ: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "3":
            clear_screen()
            try:
                run_training()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในโหมดฝึกสอนโมเดล: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "4":
            clear_screen()
            try:
                run_inference()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในโหมดตรวจจับเรียลไทม์: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "5":
            clear_screen()
            try:
                check_diagnostics()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในการรันการตรวจสอบระบบ: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "6":
            clear_screen()
            try:
                run_normalization()
            except Exception as e:
                print(f"\n[ERROR] เกิดข้อผิดพลาดในการรันการทำความสะอาดข้อมูล: {e}")
                input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        elif choice == "0":
            clear_screen()
            print("ขอบคุณที่ใช้งานระบบตรวจจับก่อนการล้ม สวัสดีครับ")
            break
        else:
            print("\n[WARNING] ตัวเลือกไม่ถูกต้อง กรุณากรอกตัวเลขระหว่าง 0 ถึง 6")
            input("กด Enter เพื่อเลือกใหม่...")

if __name__ == "__main__":
    main()
