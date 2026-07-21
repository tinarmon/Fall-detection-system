import os
import sys
import glob
import pandas as pd
import numpy as np
import config
from core.angle_calculator import AngleCalculator

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def detect_outliers(df, jump_threshold=config.JUMP_THRESHOLD, distance_threshold=config.OUTLIER_DISTANCE_THRESHOLD):
    """
    ตรวจหาเฟรมที่เป็น Outlier (เช่น MediaPipe จับสลับไปโดนคนข้างหลัง)
    โดยใช้ความแตกต่างและการกระโดดของพิกัดสะโพกในแกนแนวนอน (X)
    """
    n = len(df)
    if n == 0:
        return np.zeros(0, dtype=bool)
    
    # คำนวณ Centroid แนวดิ่งและแนวราบของสะโพก
    cx = (df['x23'] + df['x24']) / 2.0
    
    # ค่ามัธยฐานระดับสายตา (Global Median) ของสะโพกแนวนอน
    median_x = cx.median()
    
    is_outlier = np.zeros(n, dtype=bool)
    
    # 1. เฟรมที่พิกัดสะโพกห่างจากมัธยฐานรวมมากเกินไป ให้ถือเป็น Outlier ทันที
    is_outlier[np.abs(cx - median_x) > distance_threshold] = True
    
    # 2. ตรวจสอบการกระโดดแนวนอนที่รวดเร็ว (Sudden Swap)
    i = 1
    while i < n:
        jump_x = np.abs(cx.iloc[i] - cx.iloc[i-1])
        if jump_x > jump_threshold:
            # ตรวจพบการกระโดด: จุดใหม่ห่างจากตำแหน่งปกติ (Median) มากขึ้นหรือไม่
            if np.abs(cx.iloc[i] - median_x) > np.abs(cx.iloc[i-1] - median_x) and np.abs(cx.iloc[i] - median_x) > 0.05:
                # เริ่มต้นนับเป็น Outlier Segment
                run_start = i
                run_end = n
                # มองหาจุดที่กระโดดกลับ (Jump Back)
                for j in range(i + 1, n):
                    j_jump_x = np.abs(cx.iloc[j] - cx.iloc[j-1])
                    if j_jump_x > jump_threshold:
                        # กระโดดกลับมาใกล้เคียงกับตำแหน่งปกติเดิม
                        if np.abs(cx.iloc[j] - median_x) < np.abs(cx.iloc[j-1] - median_x) and np.abs(cx.iloc[j] - median_x) < distance_threshold:
                            run_end = j
                            break
                # มาร์คเฟรมในช่วงดังกล่าวว่าเป็น Outlier
                is_outlier[run_start:run_end] = True
                i = run_end
                continue
        i += 1
        
    return is_outlier

def recalculate_angles(df):
    """
    คำนวณมุมซ้ายและขวาใหม่จากพิกัดที่มีการปรับเรียบแล้ว ในแบบ 3 มิติ
    """
    w = config.CAMERA_WIDTH
    h = config.CAMERA_HEIGHT
    calculator = AngleCalculator()
    
    for idx, row in df.iterrows():
        # มุมฝั่งซ้าย (ไหล่ 11, สะโพก 23, เข่า 25)
        p11 = (row['x11'] * w, row['y11'] * h, row['z11'] * w)
        p23 = (row['x23'] * w, row['y23'] * h, row['z23'] * w)
        p25 = (row['x25'] * w, row['y25'] * h, row['z25'] * w)
        df.at[idx, 'left_angle'] = calculator.calculate_angle_3d(p11, p23, p25) / 180.0
        
        # มุมฝั่งขวา (ไหล่ 12, สะโพก 24, เข่า 26)
        p12 = (row['x12'] * w, row['y12'] * h, row['z12'] * w)
        p24 = (row['x24'] * w, row['y24'] * h, row['z24'] * w)
        p26 = (row['x26'] * w, row['y26'] * h, row['z26'] * w)
        df.at[idx, 'right_angle'] = calculator.calculate_angle_3d(p12, p24, p26) / 180.0

def clean_session_file(filepath, output_dir):
    """
    ทำความสะอาดไฟล์ CSV และบันทึกไปยังโฟลเดอร์ปลายทาง
    """
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)
    
    if df.empty:
        print(f"[WARNING] ไฟล์ว่างเปล่า: '{filename}'")
        return False, 0
    
    # ตรวจสอบโครงสร้างคอลัมน์สะโพกที่ต้องใช้หาพิกัด centroid
    required_cols = [
        'x23', 'y23', 'z23', 'x24', 'y24', 'z24',
        'x11', 'y11', 'z11', 'x12', 'y12', 'z12',
        'x25', 'y25', 'z25', 'x26', 'y26', 'z26'
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"[ERROR] โครงสร้างไฟล์ '{filename}' ไม่ถูกต้อง ขาดคอลัมน์: {missing_cols}")
        return False, 0
        
    is_outlier = detect_outliers(df)
    flagged_count = int(is_outlier.sum())
    
    if flagged_count == len(df):
        print(f"[WARNING] ❌ ไฟล์ '{filename}' พบ Outlier 100% (ตรวจจับแต่คนอื่นตลอดทั้งไฟล์) - ข้ามการทำความสะอาดไฟล์นี้")
        return False, 0
        
    if flagged_count > 0:
        # ระบุคอลัมน์พิกัดทั้งหมดที่จะแก้ไข
        landmark_cols = []
        for target in config.TARGET_LANDMARKS:
            landmark_cols.extend([f'x{target}', f'y{target}', f'z{target}'])
            
        # 1. กำหนดค่าของ Outlier ให้เป็น NaN เพื่อนำไปอินเทอร์โพเลตต่อ
        df.loc[is_outlier, landmark_cols] = np.nan
        
        # 2. ปรับค่าทางสถิติ (Linear interpolation สำหรับช่องว่าง, hold-last-good สำหรับหัวท้าย)
        df[landmark_cols] = df[landmark_cols].interpolate(method='linear', limit_direction='both')
        
        # 3. คำนวณมุมใหม่จากพิกัดใหม่เพื่อให้ข้อมูลสอดคล้องกัน
        recalculate_angles(df)
        
        print(f"[CLEANED] ✨ ไฟล์ '{filename}' ปรับปรุงพิกัดที่หลุดไป {flagged_count}/{len(df)} เฟรมสำเร็จ")
    else:
        # ไม่มี Outlier บันทึกข้อมูลคงเดิม
        pass
        
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, filename)
    df.to_csv(out_path, index=False)
    return True, flagged_count

def run_normalization():
    print("=" * 50)
    print("[CLEANING] เริ่มต้นทำความสะอาดและปรับปรุงข้อมูลดิบ")
    print("=" * 50)
    
    raw_dir = config.RAW_DATA_DIR
    clean_dir = config.CLEAN_DATA_DIR
    
    if not os.path.exists(raw_dir):
        print(f"[ERROR] ไม่พบไดเรกทอรีข้อมูลดิบ: '{raw_dir}'")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    csv_files = glob.glob(os.path.join(raw_dir, "session_*.csv"))
    if not csv_files:
        print(f"[WARNING] ไม่พบไฟล์ข้อมูลเซสชันใน '{raw_dir}'")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    print(f"พบไฟล์ข้อมูลดิบทั้งหมด {len(csv_files)} ไฟล์ กำลังเริ่มประมวลผล...")
    
    success_count = 0
    total_flagged_frames = 0
    
    for f in csv_files:
        try:
            success, flagged = clean_session_file(f, clean_dir)
            if success:
                success_count += 1
                total_flagged_frames += flagged
        except Exception as e:
            print(f"[ERROR] เกิดข้อผิดพลาดกับไฟล์ '{os.path.basename(f)}': {e}")
            
    print("\n" + "=" * 50)
    print(f"🎉 เสร็จสิ้น! ทำความสะอาดไฟล์สำเร็จ {success_count}/{len(csv_files)} ไฟล์")
    print(f"จำนวนเฟรมทั้งหมดที่ปรับปรุงสะโพกสลับ: {total_flagged_frames} เฟรม")
    print(f"บันทึกไฟล์ผลลัพธ์ไปยัง: '{clean_dir}'")
    print("=" * 50)
    
    input("กด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_normalization()
