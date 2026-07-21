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
        landmark_cols.extend([f'x{target}', f'y{target}'])
        
    noise = np.random.normal(0, sigma, size=(len(df_aug), len(landmark_cols)))
    df_aug[landmark_cols] = df_aug[landmark_cols] + noise
    
    # Clip พิกัดให้อยู่ในช่วง 0.0 - 1.0 เสมอ
    df_aug[landmark_cols] = df_aug[landmark_cols].clip(0.0, 1.0)
    return df_aug

def translate_coordinates(df, max_translation=config.TRANSLATION_RANGE):
    """
    เลื่อนพิกัดของร่างกายทั้งหมดในระนาบระนาบ/แนวดิ่ง (Translation)
    เพื่อจำลองตำแหน่งตัวแบบที่ต่างกันในกล้อง
    """
    df_aug = df.copy()
    dx = random.uniform(-max_translation, max_translation)
    dy = random.uniform(-max_translation, max_translation)
    
    for target in config.TARGET_LANDMARKS:
        df_aug[f'x{target}'] = (df_aug[f'x{target}'] + dx).clip(0.0, 1.0)
        df_aug[f'y{target}'] = (df_aug[f'y{target}'] + dy).clip(0.0, 1.0)
        
    return df_aug

def scale_coordinates(df, max_scale=config.SCALE_RANGE):
    """
    ย่อ/ขยาย พิกัดโครงร่างของร่างกายสัมพันธ์กับจุดศูนย์กลางสะโพก (Centroid Scaling)
    เพื่อจำลองส่วนสูงหรือระยะห่างกล้องที่ต่างกัน
    """
    df_aug = df.copy()
    scale = random.uniform(1.0 - max_scale, 1.0 + max_scale)
    
    # คำนวณจุดกึ่งกลางสะโพกต่อเฟรม
    cx = (df['x23'] + df['x24']) / 2.0
    cy = (df['y23'] + df['y24']) / 2.0
    
    for target in config.TARGET_LANDMARKS:
        df_aug[f'x{target}'] = (cx + scale * (df_aug[f'x{target}'] - cx)).clip(0.0, 1.0)
        df_aug[f'y{target}'] = (cy + scale * (df_aug[f'y{target}'] - cy)).clip(0.0, 1.0)
        
    return df_aug

def recalculate_angles(df):
    """
    คำนวณมุมองศา left_angle และ right_angle ใหม่จากพิกัดที่มีการแปรรูปแล้ว
    """
    w = config.CAMERA_WIDTH
    h = config.CAMERA_HEIGHT
    calculator = AngleCalculator()
    
    for idx, row in df.iterrows():
        # ไหล่ 11, สะโพก 23, เข่า 25
        p11 = (row['x11'] * w, row['y11'] * h)
        p23 = (row['x23'] * w, row['y23'] * h)
        p25 = (row['x25'] * w, row['y25'] * h)
        df.at[idx, 'left_angle'] = calculator.calculate_angle(p11, p23, p25) / 180.0
        
        # ไหล่ 12, สะโพก 24, เข่า 26
        p12 = (row['x12'] * w, row['y12'] * h)
        p24 = (row['x24'] * w, row['y24'] * h)
        p26 = (row['x26'] * w, row['y26'] * h)
        df.at[idx, 'right_angle'] = calculator.calculate_angle(p12, p24, p26) / 180.0

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
            
            if n_fall > 0:
                fall_sessions.append((f, df))
        except Exception as e:
            pass
            
    print(f"📊 สัดส่วนข้อมูลปัจจุบัน:")
    print(f"   - เฟรมปกติ (Normal - Label 0): {normal_frames} เฟรม")
    print(f"   - เฟรมล้ม (Fall - Label 1)   : {fall_frames} เฟรม")
    
    if normal_frames == 0:
        print("[ERROR] ไม่มีข้อมูลปกติ (Label 0) เลยในระบบ ไม่สามารถสร้างความสมดุลได้")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    ratio = fall_frames / normal_frames
    print(f"   - อัตราส่วนความล้มเหลว (Ratio) : {ratio * 100:.2f}% ของข้อมูลทั้งหมด")
    
    if ratio >= 0.85:
        print("[OK] ชุดข้อมูลสมดุลดีอยู่แล้ว (มีข้อมูลล้มอย่างน้อย 85% ของข้อมูลปกติ) ไม่จำเป็นต้องสร้าง mockup เพิ่ม")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    if not fall_sessions:
        print("[WARNING] ❌ ไม่พบเซสชันการล้ม (Label 1) ใดๆ ในระบบ ไม่สามารถทำ Augmentation ได้")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return
        
    # คำนวณจำนวนข้อมูลที่ต้องเพิ่มขึ้น
    target_fall_frames = int(normal_frames * 0.90)  # ตั้งเป้าให้ได้ความสมดุล 90%
    needed_fall_frames = target_fall_frames - fall_frames
    
    print(f"\n📢 กำลังเริ่มกระบวนการสุ่มจำลองข้อมูลการล้ม (Augmenting Falls)...")
    print(f"   - เป้าหมายสร้างเฟรมล้มจำลองเพิ่ม: ~{needed_fall_frames} เฟรม")
    
    generated_files = 0
    generated_frames = 0
    
    # สุ่มดึงเซสชันการล้มและนำมาผ่านกระบวนการแปรรูปจนกว่าความสมดุลจะครบถ้วน
    while generated_frames < needed_fall_frames:
        # สุ่มหยิบไฟล์เซสชันการล้มที่มีอยู่
        fpath, df_orig = random.choice(fall_sessions)
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
        
        n_fall_added = (df_aug['label'] == 1).sum()
        generated_frames += n_fall_added
        
    print("\n" + "=" * 50)
    print("🎉 ปรับสมดุลชุดข้อมูลฝึกสอนเสร็จสิ้น!")
    print(f"   - สร้างไฟล์จำลองล้มใหม่: {generated_files} ไฟล์")
    print(f"   - เพิ่มเฟรมล้มจำลอง (Oversampled) : {generated_frames} เฟรม")
    print(f"   - สัดส่วนรวมของเฟรมล้มหลังทำเสร็จ: {fall_frames + generated_frames} เฟรม (สมดุลกับปกติ {normal_frames} เฟรม)")
    print("=" * 50)
    
    input("กด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_dataset_balancing()
