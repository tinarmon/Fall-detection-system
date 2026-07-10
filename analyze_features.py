import pandas as pd
import numpy as np
import glob
import os
import sys
import config

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def run_analysis():
    print("=" * 50)
    print("[ANALYSIS] โหมดวิเคราะห์คุณลักษณะข้อมูล (Feature Analysis)")
    print("=" * 50)

    # เลือกใช้โฟลเดอร์ตามการตั้งค่า Clean หรือ Raw
    if config.USE_CLEAN_DATA and os.path.exists(config.CLEAN_DATA_DIR):
        raw_dir = config.CLEAN_DATA_DIR
        data_type_str = "สะอาด (Cleaned Data)"
    else:
        raw_dir = config.RAW_DATA_DIR
        data_type_str = "ดิบ (Raw Data)"

    if not os.path.exists(raw_dir):
        print(f"[ERROR] ไม่พบไดเรกทอรีเก็บข้อมูล: '{raw_dir}'")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    csv_files = glob.glob(os.path.join(raw_dir, "session_*.csv"))
    if not csv_files:
        print(f"[WARNING] ไม่พบไฟล์ข้อมูลเซสชัน (.csv) ใน '{raw_dir}'")
        print("กรุณาสะสมข้อมูลผ่านทางโหมด Data Acquisition หรือ Clean & Normalize Data ก่อน")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    print(f"พบไฟล์ข้อมูล {data_type_str} ทั้งหมด {len(csv_files)} ไฟล์ กำลังโหลดและรวมข้อมูล...")

    dataframes = []
    for f in csv_files:
        try:
            temp_df = pd.read_csv(f)
            if not temp_df.empty:
                dataframes.append(temp_df)
        except Exception as e:
            print(f"[WARNING] ไม่สามารถอ่านไฟล์ '{f}' ได้: {e}")

    if not dataframes:
        print("[ERROR] ไม่มีข้อมูลที่อ่านได้จากไฟล์ CSV เหล่านั้น")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    df = pd.concat(dataframes, ignore_index=True)
    print(f"โหลดข้อมูลและรวมไฟล์สำเร็จ! จำนวนข้อมูลรวมทั้งหมด: {len(df)} แถว")

    if 'label' not in df.columns:
        print("[ERROR] โครงสร้างข้อมูลไม่ถูกต้อง (ไม่พบคอลัมน์ 'label')")
        input("กด Enter เพื่อกลับสู่เมนูหลัก...")
        return

    # ลบคอลัมน์เมทาดาตาที่ไม่ใช่ตัวเลขเพื่อความถูกต้องในการคำนวณสถิติ
    metadata_cols = ['timestamp', 'subject_id', 'input_source']
    df_features = df.drop(columns=[col for col in metadata_cols if col in df.columns])

    try:
        unique_labels = df_features['label'].unique()
        if len(unique_labels) < 2:
            print(f"[WARNING] คำเตือน: ข้อมูลที่มีอยู่มีเพียง label เดียวเท่านั้น ({unique_labels}), สถิติบางอย่างอาจไม่ครบถ้วน")
        
        summary = pd.DataFrame({
            'Normal_Mean (0)': df_features[df_features['label'] == 0].mean() if 0 in unique_labels else np.nan,
            'Normal_Std (0)': df_features[df_features['label'] == 0].std() if 0 in unique_labels else np.nan,
            'Fall_Mean (1)': df_features[df_features['label'] == 1].mean() if 1 in unique_labels else np.nan,
            'Fall_Std (1)': df_features[df_features['label'] == 1].std() if 1 in unique_labels else np.nan
        })
        
        summary = summary.drop('label', errors='ignore')
        
        summary['Mean_Difference'] = abs(summary['Normal_Mean (0)'] - summary['Fall_Mean (1)'])
        summary = summary.sort_values(by='Mean_Difference', ascending=False)

        print("\n" + "="*70)
        print("[STATS] สรุปค่าสถิติ Mean และ Std ของแต่ละตัวแปร (เรียงตามความแตกต่างสูงสุด)")
        print("="*70)
        print(summary.round(4).to_string())
        print("="*70)

        os.makedirs(config.DATA_DIR, exist_ok=True)
        output_file = os.path.join(config.DATA_DIR, 'feature_statistics_report.csv')
        summary.to_csv(output_file)
        print(f"\n[OK] บันทึกตารางสรุปผลลงในไฟล์ '{output_file}' เรียบร้อยแล้ว!")
        
    except Exception as e:
        print(f"[ERROR] มีข้อผิดพลาดในการวิเคราะห์คุณลักษณะ: {e}")
        
    input("\nกด Enter เพื่อกลับสู่เมนูหลัก...")

if __name__ == "__main__":
    run_analysis()