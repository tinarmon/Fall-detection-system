import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import os
import sys
import glob
import config

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

TIME_STEPS = config.TIME_STEPS

def create_sequences(X, y, time_steps):
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i:(i + time_steps)])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)

def run_evaluation():
    print("=" * 50)
    print("[EVAL] โหมดประเมินประสิทธิภาพโมเดล AI (Evaluation Mode)")
    print("=" * 50)

    test_file = None
    raw_dir = config.RAW_DATA_DIR
    
    old_test_path = os.path.join(config.DATA_DIR, 'test_dataset.csv')
    if os.path.isfile(old_test_path):
        test_file = old_test_path
    else:
        if os.path.exists(raw_dir):
            test_files = glob.glob(os.path.join(raw_dir, "*test*.csv"))
            if not test_files:
                test_files = glob.glob(os.path.join(raw_dir, "session_*.csv"))
            
            if test_files:
                if len(test_files) == 1:
                    test_file = test_files[0]
                else:
                    print("\nพบไฟล์ข้อมูลเซสชันหลายไฟล์สำหรับนำมาทดสอบ:")
                    for idx, f in enumerate(test_files):
                        print(f"[{idx + 1}] {os.path.basename(f)}")
                    print("[0] ป้อนที่อยู่ไฟล์เอง (Enter manual file path)")
                    
                    while True:
                        choice = input("เลือกไฟล์ (กรอกตัวเลข): ").strip()
                        if choice == "0":
                            break
                        if choice.isdigit() and 1 <= int(choice) <= len(test_files):
                            test_file = test_files[int(choice) - 1]
                            break
                        print("ตัวเลือกไม่ถูกต้อง")
                        
    if test_file is None:
        test_file_input = input("\nกรุณากรอกที่อยู่ไฟล์ชุดข้อมูลสำหรับทดสอบ (CSV): ").strip()
        test_file_input = test_file_input.strip("'\"")
        if os.path.isfile(test_file_input):
            test_file = test_file_input
        else:
            print("[ERROR] ไม่พบไฟล์ดังกล่าว")
            input("กด Enter เพื่อกลับสู่เมนูหลัก...")
            return

    print(f"\nกำลังโหลดชุดข้อมูลทดสอบจาก: '{test_file}'")
    try:
        df = pd.read_csv(test_file)
        if df.empty:
            print("[ERROR] ไฟล์ข้อมูลว่างเปล่า")
            input("กด Enter เพื่อกลับสู่เมนูหลัก...")
            return
            
        if 'label' not in df.columns:
            print("[ERROR] โครงสร้างข้อมูลไม่ถูกต้อง (ไม่พบคอลัมน์ 'label')")
            input("กด Enter เพื่อกลับสู่เมนูหลัก...")
            return

        metadata_cols = ['timestamp', 'subject_id', 'input_source']
        df_features = df.drop(columns=[col for col in metadata_cols if col in df.columns])

        X_raw = df_features.drop('label', axis=1).values 
        y_raw = df_features['label'].values
        
        if len(X_raw) <= TIME_STEPS:
            print(f"[ERROR] จำนวนข้อมูลดิบมีไม่เพียงพอสำหรับสร้าง sequence ขนาด {TIME_STEPS}")
            input("กด Enter เพื่อกลับสู่เมนูหลัก...")
            return

        X_test, y_true = create_sequences(X_raw, y_raw, TIME_STEPS)
        print(f"โหลดข้อมูลทดสอบสำเร็จ! จำนวน: {len(X_test)} ลำดับเหตุการณ์")
    except Exception as e:
        print(f"[ERROR] เกิดข้อผิดพลาดในการโหลดไฟล์ทดสอบ: {e}")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    try:
        model = tf.keras.models.load_model(config.MODEL_PATH)
        print("โหลดสมอง AI 'fall_model.keras' สำเร็จ!\n")
    except Exception as e:
        print(f"[ERROR] ไม่พบไฟล์โมเดลที่ '{config.MODEL_PATH}' หรือไม่สามารถโหลดได้ กรุณาฝึกสอนโมเดลก่อน")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    print("กำลังให้ AI ทำนายผลข้อมูลใหม่...")
    try:
        y_pred_prob = model.predict(X_test, verbose=0)
        y_pred = (y_pred_prob > config.FALL_THRESHOLD).astype(int).flatten()
    except Exception as e:
        print(f"[ERROR] เกิดข้อผิดพลาดในการทำนายผล: {e}")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    accuracy = accuracy_score(y_true, y_pred)
    conf_matrix = confusion_matrix(y_true, y_pred)
    
    print("\n" + "="*50)
    print(f"[OK] ความแม่นยำรวม (Overall Accuracy): {accuracy * 100:.2f}%")
    print("="*50)
    print("\n[CONFUSION MATRIX] ตาราง Confusion Matrix:")
    
    tn = conf_matrix[0][0] if conf_matrix.shape == (2, 2) else (conf_matrix[0][0] if y_true[0] == 0 else 0)
    fp = conf_matrix[0][1] if conf_matrix.shape == (2, 2) else 0
    fn = conf_matrix[1][0] if conf_matrix.shape == (2, 2) else 0
    tp = conf_matrix[1][1] if conf_matrix.shape == (2, 2) else (conf_matrix[0][0] if y_true[0] == 1 else 0)

    print(f"ทายว่า ปกติ(0) และเป็น ปกติ(0) จริงๆ : {tn} ครั้ง")
    print(f"ทายว่า ล้ม(1) แต่จริงๆคือ ปกติ(0)   : {fp} ครั้ง (False Alarm)")
    print(f"ทายว่า ปกติ(0) แต่จริงๆคือ ล้ม(1)    : {fn} ครั้ง (Missed)")
    print(f"ทายว่า ล้ม(1) และเป็น ล้ม(1) จริงๆ   : {tp} ครั้ง")
    print("-" * 50)
    print("\n[REPORT] รายงาน Classification Report:")
    
    unique_classes = np.unique(y_true)
    target_names = []
    if 0 in unique_classes:
        target_names.append('Normal (0)')
    if 1 in unique_classes:
        target_names.append('Fall (1)')
        
    print(classification_report(y_true, y_pred, target_names=target_names if len(target_names) > 0 else None))

    input("\nกด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_evaluation()