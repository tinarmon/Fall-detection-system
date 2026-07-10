import pandas as pd
import numpy as np
import tensorflow as tf
import config
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import GRU, Dense, Dropout
import os
import sys
import glob

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

TIME_STEPS = config.TIME_STEPS
EPOCHS = config.EPOCHS
BATCH_SIZE = config.BATCH_SIZE

def load_and_preprocess_data():
    # เลือกใช้โฟลเดอร์ตามการตั้งค่า Clean หรือ Raw
    if config.USE_CLEAN_DATA and os.path.exists(config.CLEAN_DATA_DIR):
        raw_dir = config.CLEAN_DATA_DIR
        data_type_str = "สะอาด (Cleaned Data)"
    else:
        raw_dir = config.RAW_DATA_DIR
        data_type_str = "ดิบ (Raw Data)"

    if not os.path.exists(raw_dir):
        print(f"[ERROR] ไม่พบไดเรกทอรีเก็บข้อมูล: '{raw_dir}'")
        return None, None

    csv_files = glob.glob(os.path.join(raw_dir, "session_*.csv"))
    if not csv_files:
        print(f"[WARNING] ไม่พบไฟล์ข้อมูลเซสชัน (.csv) ใน '{raw_dir}'")
        return None, None

    print(f"พบไฟล์ข้อมูล {data_type_str} ทั้งหมด {len(csv_files)} ไฟล์ กำลังโหลดและรวมข้อมูลเพื่อใช้ฝึกสอน...")

    dataframes = []
    for f in csv_files:
        try:
            temp_df = pd.read_csv(f)
            if not temp_df.empty:
                dataframes.append(temp_df)
        except Exception as e:
            print(f"[WARNING] ไม่สามารถอ่านไฟล์ '{f}' ได้: {e}")

    if not dataframes:
        return None, None

    df = pd.concat(dataframes, ignore_index=True)
    print(f"โหลดข้อมูลและรวมไฟล์สำเร็จ! จำนวนข้อมูลรวมทั้งหมด: {len(df)} แถว")

    if 'label' not in df.columns:
        print("[ERROR] โครงสร้างข้อมูลไม่ถูกต้อง (ไม่พบคอลัมน์ 'label')")
        return None, None

    metadata_cols = ['timestamp', 'subject_id', 'input_source']
    df_features = df.drop(columns=[col for col in metadata_cols if col in df.columns])

    X = df_features.drop("label", axis=1).values
    y = df_features["label"].values

    return X, y

def create_sequences(X, y, time_steps):
    """
    แปลงข้อมูลรายเฟรม ให้เป็นข้อมูลแบบลำดับเวลา (Sequence) สำหรับโมเดล GRU
    """
    Xs, ys = [], []
    for i in range(len(X) - time_steps):
        Xs.append(X[i : (i + time_steps)])
        ys.append(y[i + time_steps])
    return np.array(Xs), np.array(ys)

def run_training():
    print("=" * 50)
    print("[TRAINING] เริ่มต้นการฝึกสอนโมเดล AI (Model Training Mode)")
    print("=" * 50)

    X_raw, y_raw = load_and_preprocess_data()
    if X_raw is None or y_raw is None:
        print("[ERROR] ไม่พบข้อมูลสำหรับฝึกสอน กรุณาสะสมข้อมูลก่อนเริ่มฝึกสอนโมเดล")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    if len(X_raw) <= TIME_STEPS:
        print(f"[ERROR] จำนวนข้อมูลดิบ ({len(X_raw)} เฟรม) มีไม่เพียงพอสำหรับสร้าง sequence ขนาด {TIME_STEPS} เฟรม")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    X_seq, y_seq = create_sequences(X_raw, y_raw, TIME_STEPS)
    print(f"จัดกลุ่มเป็น Sequence ละ {TIME_STEPS} เฟรม ได้ทั้งหมด: {len(X_seq)} ชุด")

    X_train, X_test, y_train, y_test = train_test_split(
        X_seq, y_seq, test_size=0.2, random_state=42, shuffle=False
    )

    print("\n--- กำลังสร้างโมเดล GRU ---")
    model = Sequential(
        [
            GRU(64, return_sequences=True, input_shape=(TIME_STEPS, X_train.shape[2])),
            Dropout(0.2),
            GRU(32),
            Dropout(0.2),
            Dense(16, activation="relu"),
            Dense(1, activation="sigmoid"),
        ]
    )

    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.summary()

    print("\n--- เริ่มฝึกสอน (Training) ---")
    try:
        model.fit(
            X_train,
            y_train,
            epochs=EPOCHS,
            batch_size=BATCH_SIZE,
            validation_split=0.2,
        )
    except Exception as e:
        print(f"[ERROR] เกิดข้อผิดพลาดขณะเทรนโมเดล: {e}")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    print("\n--- ประเมินผลกับชุดข้อมูลทดสอบ (Test Set) ---")
    try:
        loss, accuracy = model.evaluate(X_test, y_test)
        print(f"ความแม่นยำของ AI (Test Accuracy): {accuracy * 100:.2f}%\n")
    except Exception as e:
        print(f"[WARNING] ไม่สามารถประเมินโมเดลได้: {e}")

    os.makedirs(config.ASSETS_DIR, exist_ok=True)
    model_filename = config.MODEL_PATH
    try:
        model.save(model_filename)
        print(f"[OK] บันทึกโมเดลสำเร็จ! ไฟล์สมอง AI ชื่อ: '{model_filename}'")
    except Exception as e:
        print(f"[ERROR] ไม่สามารถบันทึกไฟล์โมเดลได้: {e}")

    input("\nกด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_training()
