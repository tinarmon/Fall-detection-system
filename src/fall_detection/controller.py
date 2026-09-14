"""Fall event lifecycle controller for notification dispatch and cooldown management."""

import datetime
import logging
import os
import time

import cv2

from src.fall_detection.config import AppConfig
from src.fall_detection.notification import (
    create_fall_evidence_montage,
    send_line_fall_alert_async,
)

logger = logging.getLogger(__name__)


class FallEventController:
    """Controls fall event dispatch and notification cooldowns."""

    def __init__(
        self,
        app_config: AppConfig,
        line_channel_token: str = "",
        default_user_id: str = "",
    ):
        self.app_config = app_config
        self.line_channel_token = line_channel_token
        self.default_user_id = default_user_id
        self.last_line_notify_time: dict[str, float] = {}
        self.last_audio_alert_time: float = 0.0

    def process_fall_event(self, cam_name: str, stream, cfg: dict) -> None:
        """Processes a single fall event, handling cooldown and evidence upload."""
        curr_time = time.time()
        last_sent = self.last_line_notify_time.get(cam_name, 0.0)

        if curr_time - last_sent > self.app_config.line_cooldown_seconds:
            self.last_line_notify_time[cam_name] = curr_time

            video_path = stream.save_fall_clip()
            video_filename = os.path.basename(video_path)

            time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            evidence_frames = stream.get_evidence_frames()
            montage_img = None
            if evidence_frames:
                montage_img = create_fall_evidence_montage(
                    evidence_frames, cam_name, time_str, stream.last_prediction
                )
                evidence_filename = f"evidence_{cam_name}_{int(curr_time)}.jpg"
                evidence_path = os.path.join(
                    str(self.app_config.base_dir), "recorded_falls", evidence_filename
                )
                try:
                    cv2.imwrite(evidence_path, montage_img)
                except Exception as e:
                    logger.warning("Failed to save evidence image: %s", e)

            target_user = (
                cfg.get("line_user_id", "").strip()
                or cfg.get("line_token", "").strip()
                or self.default_user_id.strip()
                or getattr(self, "global_line_user_id", "").strip()
            )
            channel_token = (
                self.line_channel_token or self.app_config.line_channel_token
            ).strip()

            logger.info(
                "🚨 [FALL EVENT TRIGGERED] Camera: %s | User: %s | Video: %s",
                cam_name,
                target_user or "(NO USER ID)",
                video_filename,
            )

            if channel_token and target_user:
                send_line_fall_alert_async(
                    channel_token=channel_token,
                    destination_id=target_user,
                    cam_name=cam_name,
                    time_str=time_str,
                    montage_img=montage_img,
                    video_filename=video_filename,
                )
            elif not target_user:
                logger.warning(
                    "⚠️ [FALL EVENT] No LINE User ID or Group ID provided. Alert could not be sent to LINE."
                )

    def should_alert_audio(self, cam_name: str, cooldown: float = 4.0) -> bool:
        """Determines if audio alert should sound based on cooldown."""
        curr_t = time.time()
        if curr_t - self.last_audio_alert_time > cooldown:
            self.last_audio_alert_time = curr_t
            return True
        return False
