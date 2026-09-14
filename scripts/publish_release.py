"""Script to publish v1.3.0 release and upload DPDF_Setup.exe asset to GitHub."""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request


def get_github_token() -> str:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        text=True,
        capture_output=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("Could not retrieve GitHub token from git credential helper")


def main():
    repo = "tinarmon/Fall-detection-system"
    tag = "v1.3.0"
    target_branch = "Rule1.3.0"
    release_name = "v1.3.0 - Performance & Thread Safety Release"
    installer_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "InstallerFile",
        "DPDF_Setup.exe",
    )

    if not os.path.isfile(installer_path):
        print(f"Error: Installer file not found at {installer_path}")
        sys.exit(1)

    file_size_mb = os.path.getsize(installer_path) / (1024 * 1024)
    print(f"Found installer: {installer_path} ({file_size_mb:.1f} MB)")

    token = get_github_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ReleasePublisher/1.0",
    }

    body_text = """## 🚀 Highlights in v1.3.0

เวอร์ชัน v1.3.0 อัปเกรดประสิทธิภาพการประมวลผล AI การจัดการเธรด และโครงสร้างสถาปัตยกรรมภายใน เพื่อความเสถียรและรวดเร็วสูงสุด

### ⚡ Performance & Inference Optimization (ประสิทธิภาพความเร็ว)
* **MediaPipe Video Mode:** สลับไปใช้ `RunningMode.VIDEO` พร้อมระบบ Monotonic Frame Timestamps ทำให้โมเดลแชร์การตรวจจับระหว่างเฟรมต่อเนื่อง ลดภาระการทำงานของ CPU ลง 30–40%
* **Inference Frame Skipping:** รองรับการตั้งค่าข้ามการประมวลผล Pose Detection ทุก ๆ N เฟรม (ค่าเริ่มต้นแสดงผล 30-60 FPS ลื่นไหล แต่รัน AI ตามรอบที่กำหนด)
* **Decoupled Pose Drawing:** แยกขั้นตอนการวาดโครงกระดูกออกจาก Logic การตรวจจับ (Single Responsibility)

### 🔒 Thread Safety & Resilience (ความปลอดภัยของเธรดและข้อผิดพลาด)
* **State Locking:** ป้องกัน Data Race ระหว่าง Worker Thread กับ GUI Main Thread ด้วย Lock-protected property accessors สำหรับ `last_frame`, `fps`, `last_prediction`, `last_status`
* **Bounded Notifications:** เปลี่ยนการสร้าง Thread อิสระมาใช้ `ThreadPoolExecutor(max_workers=3)` พร้อมระบบ Single-retry อัตโนมัติ ป้องกันปัญหาค้างหรือ Thread ทะลัก
* **Video Writer & Cleanup Protection:** เพิ่มการตรวจสอบ `VideoWriter.isOpened()` และเพิ่ม Concurrency Lock ป้องกัน TOCTOU Race Condition ขณะบันทึกคลิปหลักฐานการล้มพร้อมกัน

### 📦 Centralized Configuration (การตั้งค่ารวมศูนย์)
* ย้ายค่าคงที่กว่า 10 ตัวจากโค้ดเข้ามาอยู่ใน `configs/config.toml` (`[inference]`, `[recording]`, `[upload]`, `gui_refresh_ms`)
* รองรับการปรับแต่ง URL โฮสต์สำรองภาพหลักฐาน (`catbox.moe` และ `tmpfiles.org`)

### 🧩 Controller & Architecture Decomposition
* แยก Controller ตรวจจับและส่งการแจ้งเตือนออกมาเป็นโมดูล `src/fall_detection/controller.py`
* เพิ่มโมดูลจัดเก็บค่าการทำงานแบบ Atomic `src/fall_detection/persistence.py`
* เพิ่มชุด Automated Test Suite ใหม่ ครอบคลุมเป็น **26 การทดสอบ** (ผ่าน 100%)

---
### 📥 Installation Instructions (ขั้นตอนการติดตั้ง)
1. ดาวน์โหลดไฟล์ `DPDF_Setup.exe` ด้านล่าง
2. ดับเบิลคลิกไฟล์เพื่อเปิดตัวติดตั้ง Wizard
3. เลือกไดเรกทอรีที่ต้องการและกด Install
4. เปิดใช้งานผ่าน Shortcut หน้า Desktop หรือโฟลเดอร์ที่ติดตั้ง
"""

    release_payload = {
        "tag_name": tag,
        "target_commitish": target_branch,
        "name": release_name,
        "body": body_text,
        "draft": False,
        "prerelease": False,
    }

    # Check if release already exists
    req_check = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
        headers=headers,
    )
    release_id = None
    upload_url_template = None
    try:
        with urllib.request.urlopen(req_check) as resp:
            existing = json.loads(resp.read().decode())
            release_id = existing["id"]
            upload_url_template = existing["upload_url"]
            print(f"Release {tag} already exists (ID: {release_id})")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass
        else:
            raise

    if not release_id:
        print(f"Creating release {tag} on GitHub...")
        req_create = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/releases",
            data=json.dumps(release_payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_create) as resp:
            rel_data = json.loads(resp.read().decode())
            release_id = rel_data["id"]
            upload_url_template = rel_data["upload_url"]
            print(f"Created release {tag} (ID: {release_id})")

    # Upload asset
    upload_base = upload_url_template.split("{")[0]
    upload_url = f"{upload_base}?name=DPDF_Setup.exe"

    print(f"Uploading {installer_path} to {upload_url}...")
    with open(installer_path, "rb") as f:
        file_bytes = f.read()

    upload_headers = {
        **headers,
        "Content-Type": "application/octet-stream",
    }
    req_upload = urllib.request.Request(
        upload_url,
        data=file_bytes,
        headers=upload_headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req_upload) as resp:
            asset_data = json.loads(resp.read().decode())
            print(f"Successfully uploaded asset: {asset_data.get('browser_download_url')}")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        if "already_exists" in err_body:
            print("Asset already exists on release.")
        else:
            print(f"Upload failed: {e.code} - {err_body}")
            sys.exit(1)

    print(f"\nRelease v1.3.0 is live at: https://github.com/{repo}/releases/tag/{tag}")


if __name__ == "__main__":
    main()
