"""Notification and evidence delivery module via LINE Messaging API."""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from src.fall_detection.config import GLOBAL_CONFIG

logger = logging.getLogger(__name__)

# Bounded thread pool executor for background notification tasks
_notification_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="NotificationWorker")


def create_fall_evidence_montage(
    frames: list[np.ndarray],
    cam_name: str,
    time_str: str,
    prediction: float = 0.88,
) -> np.ndarray:
    """Stitches up to 5 evidence frames and a telemetry badge into a 2x3 composite image.

    Parameters:
        frames: List of BGR video frames.
        cam_name: Camera identifier label.
        time_str: Formatted timestamp string.
        prediction: Risk probability score between 0.0 and 1.0.

    Returns:
        Composed BGR image of dimensions (720, 640, 3).
    """
    thumb_w, thumb_h = 320, 240
    labels = ["FRAME 2", "FRAME 4", "FRAME 6", "FRAME 8", "FRAME 10 (FALL)"]

    if not frames:
        frames = [np.zeros((thumb_h, thumb_w, 3), dtype=np.uint8)]
    padded_frames = list(frames)
    while len(padded_frames) < 5:
        padded_frames.append(padded_frames[-1])

    cells = []
    for i in range(5):
        frame = padded_frames[i]
        cell = cv2.resize(frame, (thumb_w, thumb_h))
        is_fall = i == 4
        bg_col = (0, 0, 200) if is_fall else (30, 30, 35)

        cv2.rectangle(cell, (8, 8), (145, 34), bg_col, -1)
        cv2.putText(
            cell,
            labels[i],
            (14, 26),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cells.append(cell)

    card = np.full((thumb_h, thumb_w, 3), (20, 20, 25), dtype=np.uint8)
    cv2.rectangle(card, (10, 10), (thumb_w - 10, thumb_h - 10), (45, 45, 55), 1)
    cv2.putText(
        card,
        "AI EVIDENCE LOG",
        (20, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 165, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        card,
        f"CAM: {str(cam_name).upper()}",
        (20, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.42,
        (255, 255, 255),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        card,
        f"RISK: {int(prediction * 100)}%",
        (20, 125),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (0, 0, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        card,
        f"TIME: {time_str}",
        (20, 165),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.35,
        (200, 200, 200),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        card,
        "5-FRAME (2,4,6,8,10)",
        (20, 205),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.35,
        (100, 255, 100),
        1,
        cv2.LINE_AA,
    )
    cells.append(card)

    row1 = np.hstack((cells[0], cells[1]))
    row2 = np.hstack((cells[2], cells[3]))
    row3 = np.hstack((cells[4], cells[5]))
    return np.vstack((row1, row2, row3))


def upload_evidence_image(
    jpeg_bytes: bytes, retries: int = 1, retry_delay: float = 1.0
) -> str | None:
    """Uploads JPEG evidence bytes to temporary image host with fallback.

    Returns:
        Public HTTPS URL of uploaded image, or None if upload failed.
    """
    if not jpeg_bytes:
        return None

    boundary = uuid.uuid4().hex
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "Mozilla/5.0",
    }
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="reqtype"\r\n\r\nfileupload',
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="fileToUpload"; filename="evidence.jpg"',
        b"Content-Type: image/jpeg\r\n",
        jpeg_bytes,
        f"--{boundary}--\r\n".encode(),
    ]
    data = b"\r\n".join(parts)
    primary_url = getattr(GLOBAL_CONFIG, "upload_primary_url", "https://catbox.moe/user/api.php")
    req = urllib.request.Request(primary_url, data=data, headers=headers)

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=6) as response:
                res = response.read().decode().strip()
                if res.startswith("http"):
                    return res
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as ex:
            logger.warning(f"Primary evidence upload attempt {attempt + 1} failed: {ex}")
            if attempt < retries and retry_delay > 0:
                time.sleep(retry_delay)

    parts_fallback = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="evidence.jpg"',
        b"Content-Type: image/jpeg\r\n",
        jpeg_bytes,
        f"--{boundary}--\r\n".encode(),
    ]
    data_fb = b"\r\n".join(parts_fallback)
    fallback_url = getattr(
        GLOBAL_CONFIG, "upload_fallback_url", "https://tmpfiles.org/api/v1/upload"
    )
    req_fb = urllib.request.Request(fallback_url, data=data_fb, headers=headers)

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req_fb, timeout=6) as response:
                res_dict = json.loads(response.read().decode())
                if res_dict.get("status") == "success":
                    url: str = res_dict["data"]["url"]
                    return url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            json.JSONDecodeError,
        ) as ex:
            logger.warning(f"Fallback evidence upload attempt {attempt + 1} failed: {ex}")
            if attempt < retries and retry_delay > 0:
                time.sleep(retry_delay)

    return None


def create_fall_alert_flex(
    cam_name: str,
    time_str: str,
    video_filename: str | None = None,
    image_url: str | None = None,
) -> dict:
    """Constructs LINE Flex Message JSON payload for high-priority fall alert."""
    body_contents: list[dict] = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "📷 กล้อง:", "color": "#888888", "size": "sm", "flex": 3},
                {
                    "type": "text",
                    "text": str(cam_name).upper(),
                    "weight": "bold",
                    "color": "#111111",
                    "size": "sm",
                    "flex": 7,
                },
            ],
            "margin": "md",
        },
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {"type": "text", "text": "⏰ เวลา:", "color": "#888888", "size": "sm", "flex": 3},
                {
                    "type": "text",
                    "text": str(time_str),
                    "color": "#111111",
                    "size": "sm",
                    "flex": 7,
                },
            ],
            "margin": "sm",
        },
    ]

    if image_url:
        body_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "📸 ภาพถ่าย:",
                        "color": "#888888",
                        "size": "sm",
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": "5 เฟรมต่อเนื่อง (แตะรูปเพื่อขยาย)",
                        "color": "#16A34A",
                        "size": "xs",
                        "flex": 7,
                        "wrap": True,
                    },
                ],
                "margin": "sm",
            }
        )

    if video_filename:
        body_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {
                        "type": "text",
                        "text": "📂 บันทึกคลิป:",
                        "color": "#888888",
                        "size": "sm",
                        "flex": 3,
                    },
                    {
                        "type": "text",
                        "text": f"{video_filename} (ในคอมพิวเตอร์)",
                        "color": "#4B5563",
                        "size": "xs",
                        "flex": 7,
                        "wrap": True,
                    },
                ],
                "margin": "sm",
            }
        )

    bubble: dict = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "🚨 ตรวจพบสภาวะการล้ม!",
                    "weight": "bold",
                    "color": "#FFFFFF",
                    "size": "lg",
                },
                {
                    "type": "text",
                    "text": "AI Pre-Fall Biomechanical Alert",
                    "color": "#FEE2E2",
                    "size": "xs",
                    "margin": "xs",
                },
            ],
            "backgroundColor": "#DC2626",
            "paddingAll": "16px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": body_contents,
            "paddingAll": "16px",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "📞 โทรสายด่วน 1669",
                        "uri": "tel:1669",
                    },
                    "style": "primary",
                    "color": "#DC2626",
                    "height": "sm",
                }
            ],
            "paddingAll": "12px",
        },
    }

    if image_url:
        bubble["hero"] = {
            "type": "image",
            "url": image_url,
            "size": "full",
            "aspectRatio": "20:13",
            "aspectMode": "cover",
            "action": {
                "type": "uri",
                "label": "View Full Evidence",
                "uri": image_url,
            },
        }

    return bubble


def send_line_push_message(
    channel_token: str,
    destination_id: str,
    message_text: str | None = None,
    flex_container: dict | None = None,
    retries: int = 1,
    retry_delay: float = 1.0,
) -> bool:
    """Delivers push notification to LINE user or group."""
    if not channel_token.strip() or not destination_id.strip():
        return False

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {channel_token.strip()}",
        "Content-Type": "application/json",
    }

    messages = []
    if flex_container:
        messages.append(
            {
                "type": "flex",
                "altText": message_text or "🚨 แจ้งเตือนสภาวะเสี่ยงล้ม (AI Fall Alert)",
                "contents": flex_container,
            }
        )
    elif message_text:
        messages.append({"type": "text", "text": message_text})
    else:
        return False

    payload = {"to": destination_id.strip(), "messages": messages}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as ex:
            logger.error(f"Failed to send LINE push message (attempt {attempt + 1}): {ex}")
            if attempt < retries and retry_delay > 0:
                time.sleep(retry_delay)

    return False


def send_line_fall_alert_async(
    channel_token: str,
    destination_id: str,
    cam_name: str,
    time_str: str,
    montage_img: np.ndarray | None = None,
    video_filename: str | None = None,
    callback: Callable[[bool], None] | None = None,
) -> None:
    """Asynchronously uploads evidence montage and sends LINE Flex Alert via thread pool."""

    def worker():
        image_url = None
        if montage_img is not None:
            ok, buf = cv2.imencode(".jpg", montage_img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ok:
                image_url = upload_evidence_image(buf.tobytes())

        flex = create_fall_alert_flex(
            cam_name, time_str, video_filename=video_filename, image_url=image_url
        )
        alt_msg = f"\n🚨 แจ้งเตือนตรวจพบการล้ม!\n📷 กล้อง: {str(cam_name).upper()}\n⏰ เวลา: {time_str}\n📸 มีภาพหลักฐาน 5 เฟรมแนบ"
        success = send_line_push_message(
            channel_token, destination_id, message_text=alt_msg, flex_container=flex
        )
        if callback:
            callback(success)

    _notification_executor.submit(worker)


def send_line_push_async(
    channel_token: str,
    destination_id: str,
    message_text: str | None = None,
    flex_container: dict | None = None,
    callback: Callable[[bool], None] | None = None,
) -> None:
    def worker():
        success = send_line_push_message(
            channel_token, destination_id, message_text, flex_container
        )
        if callback:
            callback(success)

    _notification_executor.submit(worker)


def send_line_notify(message: str, token: str) -> bool:
    """Legacy LINE Notify push method."""
    if not token or not token.strip():
        return False
    url = "https://notify-api.line.me/api/notify"
    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = urllib.parse.urlencode({"message": message}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False


def send_line_notify_async(
    message: str, token: str, callback: Callable[[bool], None] | None = None
) -> None:
    def worker():
        success = send_line_notify(message, token)
        if callback:
            callback(success)

    _notification_executor.submit(worker)
