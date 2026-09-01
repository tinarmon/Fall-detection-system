import os
import sys
import shutil
import zipfile
import subprocess
import traceback

def get_python_exe():
    """Resolve the python.exe inside the Project virtualenv that has PyInstaller installed."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "..", "Project", "venv", "Scripts", "python.exe"),
        os.path.join(base_dir, "venv", "Scripts", "python.exe"),
        sys.executable
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return sys.executable

def zip_dir(src_dir, zip_file_path):
    print(f"Compressing relocatable workspace into '{os.path.basename(zip_file_path)}' using Windows native tar...")
    try:
        subprocess.run(
            ["tar", "-a", "-cf", zip_file_path, "-C", src_dir, "."],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print(f"Successfully zipped workspace! Output size: {os.path.getsize(zip_file_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"Error zipping directory with native tar: {e}. Falling back to standard zipfile...")
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, src_dir)
                    zipf.write(abs_path, rel_path)

def build():
    print("==================================================")
    print("--- Starting DPDF Standalone Bytecode Builder ---")
    print("==================================================")
    
    python_exe = get_python_exe()
    print(f"Using Python Runtime: {python_exe}")
    
    project_dir = os.path.dirname(os.path.abspath(__file__))
    installer_dir = os.path.join(project_dir, "InstallerFile")
    dist_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")
    
    # Excluded modules for lightweight setup/uninstall wizards
    lightweight_excludes = [
        "--exclude-module=cv2",
        "--exclude-module=numpy",
        "--exclude-module=matplotlib",
        "--exclude-module=tensorflow",
        "--exclude-module=mediapipe",
        "--exclude-module=scipy",
        "--exclude-module=PIL",
        "--exclude-module=pandas",
        "--exclude-module=torch"
    ]
    
    # 1. Clean previous builds
    for folder in [build_dir, dist_dir]:
        if os.path.exists(folder):
            print(f"Cleaning build folder: {os.path.basename(folder)}...")
            try:
                shutil.rmtree(folder)
            except Exception as e:
                print(f"Warning: Could not remove {folder}: {e}")
                
    os.makedirs(installer_dir, exist_ok=True)
    
    # 2. Compile main.py into dist/DPDF/ (onedir mode with assets)
    print("\n[STEP 1/4] Compiling main.py to bytecode using PyInstaller...")
    try:
        subprocess.run(
            [
                python_exe, "-m", "PyInstaller", "main.py", 
                "--name=DPDF", "--onedir", "--noconsole", "--clean",
                "--add-data=assets;assets", "--icon=assets/icon.ico"
            ],
            check=True,
            cwd=project_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("Successfully compiled DPDF.exe application!")
    except Exception as e:
        print(f"Error compiling DPDF: {e}")
        traceback.print_exc()
        return

    # 2.5 Compile uninstall_gui.py into dist/DPDF/uninstall.exe (lightweight, no ML libraries)
    print("\n[STEP 1.5/4] Compiling uninstall_gui.py to standalone uninstall.exe...")
    try:
        subprocess.run(
            [
                python_exe, "-m", "PyInstaller", "uninstall_gui.py", 
                "--name=uninstall", "--onefile", "--noconsole", "--clean",
                "--noupx", "--icon=assets/icon.ico",
                f"--distpath={os.path.join(dist_dir, 'DPDF')}"
            ] + lightweight_excludes,
            check=True,
            cwd=project_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print("Successfully compiled uninstall.exe application!")
    except Exception as e:
        print(f"Error compiling uninstall: {e}")
        traceback.print_exc()
        return

    # 3. Create user manual and copy to dist/DPDF/
    print("\n[STEP 2/4] Generating user manual and packaging...")
    manual_content = """========================================================================
คู่มือการใช้งาน: ระบบประเมินความเสี่ยงและตรวจจับก่อนการล้มสไตล์ 3D (Pre-Fall Detection 3D)
========================================================================

ยินดีต้อนรับสู่ระบบตรวจจับท่าทางและแจ้งเตือนภัยก่อนการล้มแบบเรียลไทม์ 
ตัวโปรแกรมนี้ถูกแพ็คในรูปแบบสำเร็จรูป สามารถติดตั้งใช้งานบนเครื่องคอมพิวเตอร์ปลายทางได้ทันที

------------------------------------------------------------------------
📂 วิธีการเปิดใช้งานโปรแกรม
------------------------------------------------------------------------
1. เข้าไปในโฟลเดอร์ที่ทำการติดตั้งโปรแกรม (เช่น C:\\Users\\<ชื่อผู้ใช้งาน>\\AppData\\Local\\Programs\\DPDF)
2. ดับเบิ้ลคลิกไฟล์ "DPDF.exe" เพื่อเริ่มต้นเปิดระบบการทำงานทันที
   (หรือดับเบิ้ลคลิกจากปุ่มลัด Shortcut 'DPDF' บนหน้าจอหลัก Desktop)

------------------------------------------------------------------------
📹 วิธีการเชื่อมต่อกล้อง (USB Webcam และ RTSP IP Camera)
------------------------------------------------------------------------
โปรแกรมนี้รองรับการใช้งานกล้องพร้อมกันหลายตัวในหน้าจอเดียว (สูงสุด 4 ตัว):
1. เมื่อเปิดหน้าแรก (Live Tracking) หากยังไม่มีการเชื่อมต่อ ให้กดปุ่ม "+ Add Camera Stream"
2. กรอกการตั้งค่ากล้อง:
   - Camera Name: ตั้งชื่อกล้องตามต้องการ (เช่น หน้าห้องน้ำ, ทางเดิน)
   - Camera Source:
     * หากเป็นกล้อง USB เสียบสาย: ให้เลือก Local Camera หรือใส่ตัวเลขลำดับกล้อง
     * หากเป็นกล้องเน็ตเวิร์ก IP Camera: ให้กรอกลิงก์ RTSP (เช่น "rtsp://admin:password@192.168.1.100:554/stream1")
3. กดปุ่ม "Save Settings"
4. สัญญาณภาพสดพร้อมเส้นโครงกระดูกสแกนแบบ Cyberpunk จะปรากฏขึ้นทันที!

------------------------------------------------------------------------
🛠️ วิธีการควบคุมสตรีมกล้องบนหน้าจอ Grid
------------------------------------------------------------------------
สังเกตบริเวณมุมขวาบนของภาพแต่ละกล้อง จะมีปุ่มควบคุม:
- ปุ่มฟันเฟือง (⚙): คลิกเพื่อแก้ไขชื่อกล้อง หรือย้ายที่อยู่ IP/RTSP ของกล้องนั้นๆ
- ปุ่มกากบาท (✕): คลิกเพื่อปิดสัญญาณกล้องตัวนั้นและลบออกจากการตั้งค่า
* ข้อมูลกล้องทั้งหมดจะบันทึกในไฟล์ "client_config.json" อัตโนมัติ (เปิดรอบถัดไปกล้องจะขึ้นเลย ไม่ต้องตั้งค่าใหม่)

------------------------------------------------------------------------
🚨 ระบบเตือนภัยล้ม (Fall Threat Warning) และ LINE Notify
------------------------------------------------------------------------
- เมื่อบุคคลตรวจจับสูญเสียการทรงตัวหรือกำลังจะล้ม ตัวโมเดล AI จะคิดค่าความเสี่ยงเป็นเปอร์เซ็นต์
- หากความเสี่ยงเกินเกณฑ์ที่ปลอดภัย แผงเตือนภัยด้านล่างสุดจะกะพริบเป็นแถบสีแดง 
  พร้อมส่งข้อความแจ้งเตือนเข้าสู่กลุ่ม LINE ทันทีตามรหัส Token ที่ตั้งไว้!

------------------------------------------------------------------------
❌ วิธีถอนการติดตั้งโปรแกรม (Uninstallation)
------------------------------------------------------------------------
1. เข้าไปยังโฟลเดอร์ติดตั้งของโปรแกรม
2. ดับเบิ้ลคลิกไฟล์ "uninstall.exe" เพื่อทำการลบโปรแกรม ทางลัดบนเดสก์ท็อป และข้อมูลระบบทั้งหมดอย่างปลอดภัย
"""
    manual_path = os.path.join(dist_dir, "DPDF", "คู่มือการใช้งาน.txt")
    with open(manual_path, "w", encoding="utf-8") as f:
        f.write(manual_content)
        
    # Compress dist/DPDF workspace into payload.zip
    zip_path = os.path.join(project_dir, "payload.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    zip_dir(os.path.join(dist_dir, "DPDF"), zip_path)
    
    # 4. Compile setup_gui.py into single installer DPDF_Setup.exe (lightweight, noupx)
    print("\n[STEP 3/4] Compiling DPDF_Setup.exe Installer Wizard...")
    try:
        subprocess.run(
            [
                python_exe, "-m", "PyInstaller", "setup_gui.py", 
                "--name=DPDF_Setup", "--onefile", "--noconsole", 
                f"--add-data={zip_path};.", 
                "--clean", "--noupx", "--icon=assets/icon.ico",
                f"--distpath={installer_dir}"
            ] + lightweight_excludes,
            check=True,
            cwd=project_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        print(f"Successfully compiled DPDF_Setup.exe installer into '{installer_dir}'!")
            
    except Exception as e:
        print(f"Error compiling DPDF_Setup.exe: {e}")
        traceback.print_exc()
        return
        
    # 5. Final Cleanups (only payload.zip, keep build clean)
    print("\n[STEP 4/4] Performing final cleanups...")
    if os.path.exists(zip_path):
        try:
            os.remove(zip_path)
        except Exception:
            pass
            
    print("\n==================================================")
    print("Standalone bytecode installer compiled successfully!")
    print(f"Output Setup Installer: '{installer_dir}\\DPDF_Setup.exe'")
    print("==================================================\n")

if __name__ == "__main__":
    build()
