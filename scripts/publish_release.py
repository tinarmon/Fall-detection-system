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
    tag = "v1.4.0"
    target_branch = "ConnectionImprov"
    release_name = "v1.4.0 - Remote Camera & LINE QR Scan Release"
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

    body_text = """## 🌟 ภาพรวมการอัปเดตเวอร์ชัน v1.4.0 (What's New in v1.4.0)

เวอร์ชัน **v1.4.0** มุ่งเน้นการแก้ปัญหาการใช้งานจริง 2 เรื่องใหญ่: **การเชื่อมต่อกล้องระยะไกลข้ามเครือข่าย** และ **การเชื่อมต่อ LINE แจ้งเตือนแบบไม่ต้องพิมพ์รหัสยาว 33 ตัว** ให้สะดวก ง่าย และรวดเร็วที่สุดสำหรับทุกคน

---

### 1. 📷 สแกน QR Code เชื่อมต่อ LINE ใน 1 วินาที (Scan-to-Connect)
* **ไม่ต้องพิมพ์รหัส 33 ตัวอีกต่อไป**: จากเดิมที่ผู้ใช้ต้องคัดลอกรหัส User ID / Group ID ยาวๆ เช่น `U4af4980629...` มาใส่ ตอนนี้เพียงกดปุ่ม **"📷 สแกน QR"** แล้วนำหน้าจอมือถือที่มีภาพ QR Code มาจ่อหน้ากล้องคอมพิวเตอร์ ระบบจะสแกนและบันทึกรหัสให้อัตโนมัติใน 1 วินาที!
* **ปุ่ม Smart Paste (📋 วางรหัส)**: กรองเอาเฉพาะรหัส LINE ID ที่ถูกต้องจากคลิปบอร์ดให้อัตโนมัติ แม้ผู้ใช้จะก๊อปปี้ติดข้อความทักทายภาษาไทยมาทั้งประโยค
* **อัปเดตบอท LINE**: โค้ด Webhook ใหม่จะตอบกลับทั้งภาพ QR Code ชัดระดับ HD และรหัสข้อความพร้อมกัน

---

### 2. 🌐 เชื่อมต่อกล้องไร้สายระยะไกลได้ง่ายขึ้น (Remote Camera Ready)
* **ปุ่มแม่แบบกล้องในคลิกเดียว (Presets Toolbar)**:
  * `[🏠 Tapo LAN]`: สำหรับกล้อง TP-Link Tapo ที่อยู่ในบ้านเดียวกัน
  * `[🌐 Tailscale (กล้องระยะไกล)]`: สำหรับดูกล้องข้ามบ้านหรือคนละเครือข่าย
  * `[⚡ ใช้ /stream2]`: สลับไปใช้ Sub-stream ความเร็วสูง ประหยัดเน็ตบ้านและภาพไม่ค้าง
* **ระบบกู้คืนสัญญาณอัตโนมัติ (Exponential Reconnect Backoff)**: หากเน็ตบ้านหรือสัญญาณ WiFi หลุดชั่วคราว ระบบจะหน่วงเวลากู้สัญญาณอย่างชาญฉลาด (1s ➔ 2s ➔ 4s ➔ 10s) ป้องกันโปรแกรมค้าง และจะกลับมาทำงานลื่นไหลทันทีที่สัญญาณกลับมา

---

### 3. 📖 คู่มือการใช้งานฉบับเข้าใจง่าย (User-Friendly README & In-App Guide)
* ปรับปรุงหน้าต่างช่วยเหลือในโปรแกรม (กด F1) เพิ่มแท็บแนะนำขั้นตอนการตั้งค่ากล้อง Tapo C200 และ Tailscale
* ปรับปรุงหน้า README.md เน้นอธิบายความสามารถของระบบและวิธีเริ่มต้นใช้งาน 3 ขั้นตอนแบบไม่เน้นศัพท์เทคนิคเชิงลึก

---

### 📥 ขั้นตอนการติดตั้ง (Installation Instructions)
1. ดาวน์โหลดไฟล์ `DPDF_Setup.exe` ด้านล่าง
2. ดับเบิลคลิกเปิดไฟล์ตัวติดตั้ง และกด **Install**
3. เริ่มต้นใช้งานผ่านไอคอนบนหน้าจอ Desktop ได้ทันที
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
            for asset in existing.get("assets", []):
                if asset["name"] == "DPDF_Setup.exe":
                    print(f"Deleting existing asset ID {asset['id']} to upload new build...")
                    del_req = urllib.request.Request(
                        f"https://api.github.com/repos/{repo}/releases/assets/{asset['id']}",
                        headers=headers,
                        method="DELETE",
                    )
                    try:
                        with urllib.request.urlopen(del_req):
                            print("Deleted old asset successfully.")
                    except Exception as ex:
                        print(f"Failed deleting old asset: {ex}")
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

    print(f"\nRelease {tag} is live at: https://github.com/{repo}/releases/tag/{tag}")


if __name__ == "__main__":
    main()
