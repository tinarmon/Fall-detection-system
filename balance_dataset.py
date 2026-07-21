import os
import sys
import glob
import random
import pandas as pd
import numpy as np
import config
from core.angle_calculator import AngleCalculator

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def jitter_coordinates(df, sigma=config.JITTER_SIGMA):
    """
    เพิ่มสัญญาณรบกวนสุ่ม (Gaussian Noise) ลงในพิกัดเพื่อจำลองความไม่เที่ยงตรงของเซนเซอร์
    """
    df_aug = df.copy()
    landmark_cols = []
    for target in config.TARGET_LANDMARKS:
        landmark_cols.extend([f'x{target}', f'y{target}', f'z{target}'])
        
    noise = np.random.normal(0, sigma, size=(len(df_aug), len(landmark_cols)))
    df_aug[landmark_cols] = df_aug[landmark_cols] + noise
    
    # สำหรับพิกัด Relative ที่มีค่าติดลบได้ เราไม่สามารถใช้ .clip(0.0, 1.0) ได้
    # จึงทำการเอาการ Clip ออกเพื่อให้ข้อมูลโครงร่าง 3D อยู่ในสภาพปกติ
    return df_aug

def translate_coordinates(df, max_translation=config.TRANSLATION_RANGE):
    """
    สำหรับ Relative Coordinates จุดสะโพกจะถูกฟิกซ์ที่จุดกำเนิด (0,0,0) ตลอดเวลา
    ดังนั้นการเลื่อนตำแหน่งภาพ (Translation) จะไม่มีผลใดๆ ต่อข้อมูลสัมพัทธ์
    จึงข้ามการเลื่อนตำแหน่งเพื่อคงความสมบูรณ์ของจุดศูนย์กลางสะโพกไว้
    """
    return df.copy()

def scale_coordinates(df, max_scale=config.SCALE_RANGE):
    """
    ย่อ/ขยาย พิกัดโครงร่างของร่างกายสัมพันธ์กับจุดศูนย์กลางสะโพก (Centroid Scaling)
    เพื่อจำลองส่วนสูงหรือระยะห่างกล้องที่ต่างกัน
    """
    df_aug = df.copy()
    scale = random.uniform(1.0 - max_scale, 1.0 + max_scale)
    
    # คำนวณจุดกึ่งกลางสะโพกต่อเฟรม (ซึ่งปกติเป็น 0.0 สำหรับ Relative Coordinates)
    cx = (df['x23'] + df['x24']) / 2.0
    cy = (df['y23'] + df['y24']) / 2.0
    cz = (df['z23'] + df['z24']) / 2.0
    
    for target in config.TARGET_LANDMARKS:
        df_aug[f'x{target}'] = cx + scale * (df_aug[f'x{target}'] - cx)
        df_aug[f'y{target}'] = cy + scale * (df_aug[f'y{target}'] - cy)
        df_aug[f'z{target}'] = cz + scale * (df_aug[f'z{target}'] - cz)
        
    return df_aug

def recalculate_angles(df):
    """
    คำนวณมุมองศา left_angle และ right_angle ใหม่จากพิกัดที่มีการแปรรูปแล้ว ในแบบ 3 มิติ
    """
    w = config.CAMERA_WIDTH
    h = config.CAMERA_HEIGHT
    calculator = AngleCalculator()
    
    for idx, row in df.iterrows():
        # ไหล่ 11, สะโพก 23, เข่า 25
        p11 = (row['x11'] * w, row['y11'] * h, row['z11'] * w)
        p23 = (row['x23'] * w, row['y23'] * h, row['z23'] * w)
        p25 = (row['x25'] * w, row['y25'] * h, row['z25'] * w)
        df.at[idx, 'left_angle'] = calculator.calculate_angle_3d(p11, p23, p25) / 180.0
        
        # ไหล่ 12, สะโพก 24, เข่า 26
        p12 = (row['x12'] * w, row['y12'] * h, row['z12'] * w)
        p24 = (row['x24'] * w, row['y24'] * h, row['z24'] * w)
        p26 = (row['x26'] * w, row['y26'] * h, row['z26'] * w)
        df.at[idx, 'right_angle'] = calculator.calculate_angle_3d(p12, p24, p26) / 180.0

def run_dataset_balancing():
    print("=" * 50)
    print("[BALANCING] ระบบจำลองพิกัดและปรับสมดุลชุดข้อมูลฝึกสอน")
    print("=" * 50)
    
    clean_dir = config.CLEAN_DATA_DIR
    if not os.path.exists(clean_dir):
        print(f"[ERROR] ไม่พบไดเรกทอรีข้อมูลสะอาด: '{clean_dir}' กรุณาทำความสะอาดข้อมูลดิบก่อน (เมนู 6)")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    csv_files = glob.glob(os.path.join(clean_dir, "session_*.csv"))
    if not csv_files:
        print(f"[WARNING] ไม่พบไฟล์ข้อมูลสะอาดใน '{clean_dir}'")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    # เคลียร์ไฟล์จำลองเก่า (หากมี) เพื่อไม่ให้ทำซ้ำซ้อนสะสม
    old_aug_files = glob.glob(os.path.join(clean_dir, "*_aug_*.csv"))
    if old_aug_files:
        print(f"🧹 ตรวจพบไฟล์สมดุลเก่า {len(old_aug_files)} ไฟล์ กำลังทำการเคลียร์ลบข้อมูลเก่า...")
        for f in old_aug_files:
            try:
                os.remove(f)
            except Exception as e:
                pass
        # รีโหลดรายการไฟล์ใหม่หลังลบไฟล์จำลองเก่า
        csv_files = glob.glob(os.path.join(clean_dir, "session_*.csv"))
        
    print("กำลังประเมินสัดส่วนข้อมูลใน Dataset...")
    
    normal_frames = 0
    fall_frames = 0
    normal_sessions = []
    fall_sessions = []
    
    for f in csv_files:
        try:
            df = pd.read_csv(f)
            if df.empty or 'label' not in df.columns:
                continue
            n_norm = (df['label'] == 0).sum()
            n_fall = (df['label'] == 1).sum()
            
            normal_frames += n_norm
            fall_frames += n_fall
            
            if n_norm > 0:
                normal_sessions.append((f, df))
            if n_fall > 0:
                fall_sessions.append((f, df))
        except Exception as e:
            pass
            
    print(f"📊 สัดส่วนข้อมูลปัจจุบัน:")
    print(f"   - เฟรมปกติ (Normal - Label 0): {normal_frames} เฟรม")
    print(f"   - เฟรมล้ม (Fall - Label 1)   : {fall_frames} เฟรม")
    
    if normal_frames == 0 and fall_frames == 0:
        print("[ERROR] ไม่มีข้อมูลในระบบเลย ไม่สามารถดำเนินการได้")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    # ตัดสินหาคลาสส่วนน้อย (Minority Class)
    if normal_frames > fall_frames:
        minority_class = 1
        minority_name = "ล้ม (Fall - Label 1)"
        majority_name = "ปกติ (Normal - Label 0)"
        ratio = fall_frames / normal_frames if normal_frames > 0 else 0
        needed_frames = int(normal_frames * 0.90) - fall_frames
        target_sessions = fall_sessions
    elif fall_frames > normal_frames:
        minority_class = 0
        minority_name = "ปกติ (Normal - Label 0)"
        majority_name = "ล้ม (Fall - Label 1)"
        ratio = normal_frames / fall_frames if fall_frames > 0 else 0
        needed_frames = int(fall_frames * 0.90) - normal_frames
        target_sessions = normal_sessions
    else:
        ratio = 1.0
        needed_frames = 0
        target_sessions = []
        
    print(f"   - อัตราส่วนความสมดุลปัจจุบัน : {ratio * 100:.2f}% (เทียบกับคลาสส่วนใหญ่: {majority_name})")
    
    if ratio >= 0.85:
        print("[OK] ชุดข้อมูลสมดุลดีอยู่แล้ว (คลาสทั้งสองมีสัดส่วนห่างกันไม่เกิน 15%) ไม่จำเป็นต้องสร้าง mockup เพิ่ม")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    if not target_sessions:
        print(f"[WARNING] ❌ ไม่พบเซสชันต้นแบบของคลาสที่ขาดแคลน ({minority_name}) ในระบบ ไม่สามารถทำ Augmentation ได้")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    print(f"\n📢 กำลังเริ่มกระบวนการสุ่มจำลองข้อมูลสำหรับคลาสที่ขาดแคลน ({minority_name})...")
    print(f"   - เป้าหมายสร้างเฟรมจำลองเพิ่ม: ~{needed_frames} เฟรม")
    
    generated_files = 0
    generated_frames = 0
    
    while generated_frames < needed_frames:
        fpath, df_orig = random.choice(target_sessions)
        filename = os.path.basename(fpath)
        base_name = os.path.splitext(filename)[0]
        
        # 1. แปรรูปพิกัดทีละขั้นอย่างสุ่ม
        df_aug = jitter_coordinates(df_orig)
        df_aug = translate_coordinates(df_aug)
        df_aug = scale_coordinates(df_aug)
        
        # 2. คำนวณมุมใหม่หลังเปลี่ยนแปลงพิกัด
        recalculate_angles(df_aug)
        
        # 3. บันทึกเป็นไฟล์ CSV จำลองใหม่
        generated_files += 1
        new_filename = f"{base_name}_aug_{generated_files}.csv"
        new_filepath = os.path.join(clean_dir, new_filename)
        
        df_aug.to_csv(new_filepath, index=False)
        
        n_added = (df_aug['label'] == minority_class).sum()
        generated_frames += n_added
        
    print("\n" + "=" * 50)
    print("🎉 ปรับสมดุลชุดข้อมูลฝึกสอนเสร็จสิ้น!")
    print(f"   - สร้างไฟล์จำลองสำเร็จ: {generated_files} ไฟล์")
    print(f"   - เพิ่มเฟรมของคลาส {minority_name} จำลองสำเร็จ: {generated_frames} เฟรม")
    print("=" * 50)
    
    input("กด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_dataset_balancing()
