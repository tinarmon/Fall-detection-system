

# Pre-Fall Detection System using MediaPipe and GRU

ระบบตรวจจับสภาวะการเสียการทรงตัว (Pre-fall) แบบเรียลไทม์ โดยใช้การวิเคราะห์โครงร่างมนุษย์ (Skeleton-based) เพื่อระบุความเสี่ยงก่อนเกิดการล้ม แตกต่างจากระบบตรวจจับการล้มทั่วไปที่อาศัยแรงกระแทก (Impact-based) ระบบนี้ใช้โมเดลโครงข่ายประสาทเทียมแบบ **Gated Recurrent Unit (GRU)** ในการวิเคราะห์ลำดับความเคลื่อนไหวเชิงเวลา (Spatial-Temporal)

## 🏗️ สถาปัตยกรรมของระบบ (System Architecture)

ระบบถูกออกแบบภายใต้โครงสร้าง 5 ขั้นตอนหลัก:

1.  **Data Ingestion Layer:** รับภาพจากกล้องผ่าน OpenCV และประมวลผลที่ความละเอียด 640x480 (ปรับแต่งได้ใน `config.py`)
2.  **Pose Estimation (MediaPipe):** ใช้ `PoseLandmarker` ในการตรวจจับจุดสำคัญของร่างกาย 33 จุด และคัดกรองเฉพาะ 6 จุดหลัก ได้แก่ หัวไหล่ (11, 12), สะโพก (23, 24) และเข่า (25, 26)
3.  **Feature Engineering:** * **Trigonometric Calculation:** คำนวณมุมระหว่าง ไหล่-สะโพก-เข่า (Body-fold angles) ทั้งซ้ายและขวาด้วย `arctan2`
    * **Scale Invariance:** แปลงพิกัดจาก Pixel เป็น Normalized Coordinates `[0.0, 1.0]` เพื่อให้โมเดลทำงานได้แม่นยำไม่ว่าระยะห่างจากกล้องจะเปลี่ยนไป
4.  **Temporal Classification (GRU):** ใช้เทคนิค Sliding Window (10 เฟรมย้อนหลัง) ป้อนเข้าสู่โมเดล GRU 2 ชั้น เพื่อวิเคราะห์แนวโน้มการเคลื่อนไหว
5.  **UI & Telemetry:** แสดงผลผ่าน Heads-Up Display (HUD) พร้อม Risk Bar บอกระดับความเสี่ยง และระบบ Auto-logging บันทึกข้อมูลการใช้งานจริง

---

## 📂 โครงสร้างโฟลเดอร์ (Repository Structure)

```text
fall-detection-system/
├── core/                   # โมดูลหลักในการทำงาน
│   ├── pose_estimator.py   # จัดการ MediaPipe และการดึงพิกัด
│   ├── angle_calculator.py # คำนวณองศาข้อต่อด้วยตรีโกณมิติ
│   └── ui_manager.py       # จัดการ Dashboard และการแสดงผลบนจอ
├── data/                   # ชุดข้อมูลและรายงานสถิติ
│   ├── fall_dataset.csv    # ข้อมูลสำหรับ Train
│   ├── test_dataset.csv    # ข้อมูลสำหรับ Test (Unseen data)
│   └── feature_statistics_report.csv # รายงานวิเคราะห์ฟีเจอร์
├── assets/                 # ไฟล์ Weights และโมเดล
│   ├── pose_landmarker_full.task # Weights ของ MediaPipe
│   └── fall_model.keras          # Weights ของโมเดล GRU ที่เทรนแล้ว
├── config.py               # จุดรวมการตั้งค่า Hyperparameters และ Paths
├── collect_data.py         # โปรแกรมเก็บข้อมูล (Data Collection)
├── train_model.py          # โปรแกรมสร้างและฝึกสอนโมเดล GRU
├── evaluate_model.py       # โปรแกรมประเมินความแม่นยำ (Confusion Matrix)
├── main.py                 # โปรแกรมหลักสำหรับรันระบบตรวจจับ (Real-time)
└── requirements.txt        # รายการ Library ที่ต้องใช้
```

---

## 🚀 ขั้นตอนการใช้งาน (Pipeline & Usage)

เพื่อให้ระบบทำงานได้อย่างมีประสิทธิภาพ ควรทำตามขั้นตอนดังนี้:


### 1. การเตรียมสภาพแวดล้อม & เวอร์ชันที่ต้องการ (Setup & Versions)

ระบบนี้พัฒนาและทดสอบด้วยเวอร์ชันดังต่อไปนี้:
* **Python**: แนะนำเป็น **Python 3.13.x**
* **Library หลัก & เวอร์ชัน**:
  * `tensorflow==2.21.0` (สมองกลโมเดล GRU)
  * `mediapipe==0.10.33` (ระบบตรวจจับท่าทางร่างกาย)
  * `opencv-python==4.13.0.92` (การจัดการกล้องและการแสดงผล HUD)
  * `keras==3.12.1` (การโหลดและรันโมเดล)
  * `numpy==2.2.6` (การจัดการอาร์เรย์และคำนวณ)
  * `pandas==2.3.3` (การสร้างและบันทึกชุดข้อมูล CSV)
  * `scikit-learn==1.7.2` (การประเมินผลประสิทธิภาพโมเดล)
  * `scipy==1.15.3` (การวิเคราะห์ทางสถิติและการคำนวณทางคณิตศาสตร์)

#### ขั้นตอนการติดตั้ง:

1. **โคลนโปรเจ็คและเข้าใช้งานโฟลเดอร์**:
   ```powershell
   git clone https://github.com/tinarmon/fall-detection-system.git
   cd fall-detection-system
   ```

2. **สร้างสภาพแวดล้อมจำลอง (Virtual Environment)**:
   * สำหรับ Windows (แนะนำ CPython 3.13):
     ```powershell
     py -3.13 -m venv venv
     ```
   * การเปิดใช้งาน Virtual Environment (Activate):
     * **Windows (PowerShell)**:
       ```powershell
       .\venv\Scripts\Activate.ps1
       ```
     * **Windows (Command Prompt)**:
       ```cmd
       .\venv\Scripts\activate.bat
       ```
     * **Linux / macOS**:
       ```bash
       source venv/bin/activate
       ```

3. **ติดตั้งไลบรารี่และแพ็คเกจทั้งหมด**:
   * ตรวจสอบให้แน่ใจว่าไฟล์ `requirements.txt` อยู่ในรูปแบบ UTF-8 จากนั้นรันคำสั่ง:
     ```powershell
     pip install -r requirements.txt
     ```
   * *หมายเหตุสำหรับ Windows*: หากเกิดข้อผิดพลาดในการติดตั้งเกี่ยวกับสิทธิ์การเข้าถึงไฟล์ (เช่น `WinError 32` เนื่องจากโปรแกรมสแกนไวรัสหรือระบบ Index ไฟล์ล็อกโฟลเดอร์ชั่วคราว) ให้ปิดโปรแกรมอื่นทั้งหมดแล้วรันคำสั่งดังกล่าวใหม่อีกครั้ง หรือใช้คำสั่งเพื่อบังคับติดตั้งใหม่:
     ```powershell
     pip install --upgrade --force-reinstall -r requirements.txt
     ```

#### ⚠️ คำแนะนำและข้อควรระวังพิเศษ:
* **ข้อจำกัดเรื่องพาร์ทโฟลเดอร์ภาษาไทย (Unicode/Thai Path Limit)**: บนระบบปฏิบัติการ Windows หากพาร์ทที่ตั้งโปรเจ็คมีอักษรภาษาไทยหรืออักษรพิเศษ (เช่น `D:\ของอิ่ม\Project`) ตัวระบบตรวจจับ MediaPipe C++ Core จะไม่สามารถเปิดไฟล์โมเดล `.task` ได้โดยตรงผ่าน String Path และจะเกิดข้อผิดพลาด `FileNotFoundError` 
  * *วิธีแก้ไข*: ตัวโปรเจ็คได้ถูกแก้ไขที่ไฟล์ `core/pose_estimator.py` ให้ทำการอ่านไฟล์แบบ Binary Bytes ก่อนส่งเข้าไปยัง MediaPipe ผ่าน `model_asset_buffer` แทนการใช้พาร์ทตรง เพื่อป้องกันปัญหานี้เรียบร้อยแล้ว
* **การใช้งาน Python Interpreter**: โปรดรันโปรเจ็คด้วย CPython มาตรฐาน (`python`) เท่านั้น **ห้ามใช้ PyPy** เนื่องจากไลบรารี่การคำนวณระดับล่าง (TensorFlow, MediaPipe, OpenCV) มีการใช้ C-Extensions ที่ออกแบบมาสำหรับ CPython เท่านั้น


### 2. การเก็บข้อมูล (Data Collection)
รันไฟล์ `collect_data.py` เพื่อสร้างชุดข้อมูลสอน AI
* กด **'n'**: เริ่มบันทึกท่าทางปกติ (Label: 0)
* กด **'f'**: เริ่มบันทึกท่าทางเสียการทรงตัว (Label: 1)
* กด **'p'** หรือ **Spacebar**: หยุดบันทึกชั่วคราว
* ข้อมูลจะถูกบันทึกเป็นพิกัดที่ผ่านการทำ Normalization แล้วลงใน `data/fall_dataset.csv`

### 3. การวิเคราะห์ข้อมูล (Feature Analysis)
รัน `analyze_features.py` เพื่อดูว่าตัวแปรใด (เช่น มุมสะโพก หรือตำแหน่งไหล่) ที่มีความแตกต่างระหว่างท่าปกติและท่าล้มมากที่สุด ผลลัพธ์จะช่วยในการเขียนรายงานเชิงสถิติในเล่มโครงงาน

### 4. การฝึกสอนโมเดล (Training)
รัน `train_model.py` เพื่อสร้างสมอง AI
* โมเดลจะใช้ข้อมูลแบบ Sequence (10 เฟรมต่อ 1 การทำนาย)
* มีการใช้ **Dropout (0.2)** เพื่อป้องกัน Overfitting
* เมื่อเทรนเสร็จจะบันทึกไฟล์ไว้ที่ `assets/fall_model.keras`

### 5. การประเมินผล (Evaluation)
รัน `evaluate_model.py` เพื่อวัดประสิทธิภาพกับข้อมูลที่ไม่เคยเห็น
* สรุปผลเป็น **Accuracy**, **Precision**, **Recall** และ **Confusion Matrix** เพื่อดูจำนวนครั้งที่เกิด False Alarm หรือ Missed Detection

### 6. การใช้งานจริง (Real-time Inference)
รัน `main.py` เพื่อเปิดระบบตรวจจับ
* ระบบจะถามชื่อผู้ทดสอบผ่าน GUI Popup
* หากค่าความน่าจะเป็นสูงกว่าที่ตั้งไว้ใน `config.py` (Default: 60%) ระบบจะแสดงกรอบสีแดงแจ้งเตือนทันที

---

## ⚙️ การปรับแต่ง (Configuration)
คุณสามารถปรับแต่งค่าต่างๆ ได้ที่ไฟล์ `config.py` เช่น:
* `TIME_STEPS`: จำนวนเฟรมย้อนหลังที่ AI ใช้จำเหตุการณ์
* `FALL_THRESHOLD`: ค่าความอ่อนไหวในการแจ้งเตือน (0.0 - 1.0)
* `TARGET_LANDMARKS`: จุดที่ต้องการให้ AI โฟกัส

---
**ผู้พัฒนา:** [ทินกฤต อมรบุตร/tinarmon]
**เทคโนโลยีที่ใช้:** Python, TensorFlow, MediaPipe, OpenCV, Scikit-learn