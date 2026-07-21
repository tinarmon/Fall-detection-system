import os
import sys
import glob
import pandas as pd
import config

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def check_dataset_balance():
    print("=" * 70)
    print("📊 ตรวจสอบสัดส่วนความสมดุลของชุดข้อมูล (Dataset Balance Checker)")
    print("=" * 70)
    
    clean_dir = config.CLEAN_DATA_DIR
    if not os.path.exists(clean_dir):
        print(f"[ERROR] ไม่พบโฟลเดอร์ข้อมูลสะอาด: '{clean_dir}'")
        return
        
    csv_files = glob.glob(os.path.join(clean_dir, "session_*.csv"))
    if not csv_files:
        print(f"[WARNING] ไม่พบไฟล์ข้อมูล (.csv) ในโฟลเดอร์ '{clean_dir}'")
        return
        
    print(f"กำลังวิเคราะห์ไฟล์ทั้งหมด {len(csv_files)} ไฟล์...\n")
    
    file_reports = []
    total_normal = 0
    total_fall = 0
    
    for f in sorted(csv_files):
        filename = os.path.basename(f)
        try:
            df = pd.read_csv(f)
            if 'label' not in df.columns or df.empty:
                continue
                
            n_norm = (df['label'] == 0).sum()
            n_fall = (df['label'] == 1).sum()
            total = len(df)
            
            total_normal += n_norm
            total_fall += n_fall
            
            # ย่อชื่อไฟล์ให้สั้นเพื่อการแสดงผลตารางที่สวยงาม
            short_name = filename if len(filename) <= 40 else filename[:37] + "..."
            file_reports.append({
                'File Name': short_name,
                'Normal (0)': n_norm,
                'Fall (1)': n_fall,
                'Total': total
            })
        except Exception as e:
            print(f"[WARNING] ไม่สามารถอ่านไฟล์ '{filename}': {e}")
            
    if not file_reports:
        print("[WARNING] ไม่มีข้อมูลที่วิเคราะห์ได้")
        return
        
    # แสดงตารางรายงานรายไฟล์
    print(f"{'ชื่อไฟล์ (File Name)':<42} | {'ปกติ (Normal 0)':^15} | {'ล้ม (Fall 1)':^12} | {'รวม (Total)':^10}")
    print("-" * 88)
    for r in file_reports:
        print(f"{r['File Name']:<42} | {r['Normal (0)']:^15} | {r['Fall (1)']:^12} | {r['Total']:^10}")
    print("-" * 88)
    
    # คำนวณเปอร์เซ็นต์และสัดส่วน
    grand_total = total_normal + total_fall
    if grand_total > 0:
        p_norm = (total_normal / grand_total) * 100
        p_fall = (total_fall / grand_total) * 100
    else:
        p_norm = p_fall = 0
        
    print(f"{'สรุปรวมทั้งหมด (Grand Total)':<42} | {total_normal:^15} | {total_fall:^12} | {grand_total:^10}")
    print(f"{'สัดส่วนคิดเป็นร้อยละ (Percentage)':<42} | {p_norm:^13.2f}% | {p_fall:^10.2f}% | {'100.00%':^10}")
    print("=" * 70)
    
    # ตรวจสอบและให้ข้อเสนอแนะ
    if total_normal == 0 or total_fall == 0:
        print("🚨 สถานะ: ข้อมูลไม่สมดุลอย่างรุนแรง (ขาดคลาสใดคลาสหนึ่งไปโดยสิ้นเชิง)")
        print("💡 แนะนำ: กรุณาบันทึกข้อมูลคลาสที่ขาดหายไป หรือรันสคริปต์ปรับสมดุล")
    else:
        ratio = min(total_normal, total_fall) / max(total_normal, total_fall)
        if ratio >= 0.85:
            print("✅ สถานะ: ชุดข้อมูลมีความสมดุลดีแล้ว (สัดส่วนความต่างน้อยกว่า 15%)")
        else:
            diff_class = "ล้ม (Fall - Label 1)" if total_normal > total_fall else "ปกติ (Normal - Label 0)"
            print(f"⚠️ สถานะ: ชุดข้อมูลยังไม่สมดุล (คลาสที่ต้องการการเพิ่มข้อมูลคือ: {diff_class})")
            print("💡 แนะนำ: สามารถใช้เมนูตัวเลือก [7] เพื่อสร้างข้อมูลจำลองปรับสมดุลได้")
            
    print("=" * 70)

if __name__ == "__main__":
    check_dataset_balance()
