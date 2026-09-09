"""HUD and telemetry overlay rendering on video frames."""

from __future__ import annotations

import cv2
import numpy as np

from src.fall_detection.config import GLOBAL_CONFIG


class UIManager:
    """Renders telemetry HUD overlays, bounding brackets, and joint angles on OpenCV video frames."""

    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.neon_white = (255, 255, 255)

    def draw_hud(
        self,
        frame: np.ndarray,
        tester_name: str,
        fps: float,
        status_text: str,
        prediction: float,
        theme_color: tuple[int, int, int],
        bbox: tuple[int, int, int, int] | None,
        source_label: str = "LOCAL",
    ) -> np.ndarray:
        """Renders telemetry panel, grid lines, and tracking brackets."""
        h, w = frame.shape[:2]

        grid_color = (30, 30, 35)
        for i in range(1, 4):
            x_line = int(w * i / 4)
            y_line = int(h * i / 4)
            cv2.line(frame, (x_line, 0), (x_line, h), grid_color, 1, cv2.LINE_AA)
            cv2.line(frame, (0, y_line), (w, y_line), grid_color, 1, cv2.LINE_AA)

        if bbox:
            x1, y1, x2, y2 = bbox
            length = min(30, int((x2 - x1) * 0.2))
            thickness = 2

            cv2.line(frame, (x1, y1), (x1 + length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y1), (x1, y1 + length), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y1), (x2 - length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y1), (x2, y1 + length), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y2), (x1 + length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y2), (x1, y2 - length), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y2), (x2 - length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y2), (x2, y2 - length), theme_color, thickness, cv2.LINE_AA)

            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            cv2.drawMarker(frame, (cx, cy), theme_color, cv2.MARKER_CROSS, 12, 1, cv2.LINE_AA)

        panel_x1, panel_y1, panel_x2, panel_y2 = 20, 20, 310, 175
        roi = frame[panel_y1:panel_y2, panel_x1:panel_x2]
        black_box = np.zeros_like(roi)
        black_box[:] = (12, 12, 16)
        frame[panel_y1:panel_y2, panel_x1:panel_x2] = cv2.addWeighted(black_box, 0.70, roi, 0.30, 0)

        # High-tech borders & corner accent
        cv2.rectangle(
            frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (75, 75, 80), 1, cv2.LINE_AA
        )
        cv2.line(
            frame, (panel_x1, panel_y1), (panel_x1 + 30, panel_y1), theme_color, 2, cv2.LINE_AA
        )
        cv2.line(
            frame, (panel_x1, panel_y1), (panel_x1, panel_y1 + 30), theme_color, 2, cv2.LINE_AA
        )

        text_main = (245, 245, 250)
        text_sub = (140, 140, 145)

        cv2.putText(
            frame,
            f"DPDF SYSTEM v{GLOBAL_CONFIG.app_version} // {source_label}",
            (panel_x1 + 15, panel_y1 + 22),
            self.font,
            0.35,
            theme_color,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"CAM: {tester_name.upper()}",
            (panel_x1 + 15, panel_y1 + 45),
            self.font,
            0.45,
            text_main,
            1,
            cv2.LINE_AA,
        )
        latency = int(1000 / fps if fps > 0 else 0)
        cv2.putText(
            frame,
            f"FPS: {int(fps)} Hz // LATENCY: {latency} ms",
            (panel_x1 + 15, panel_y1 + 65),
            self.font,
            0.35,
            text_sub,
            1,
            cv2.LINE_AA,
        )

        cv2.putText(
            frame,
            "STATUS:",
            (panel_x1 + 15, panel_y1 + 92),
            self.font,
            0.4,
            text_sub,
            1,
            cv2.LINE_AA,
        )
        status_upper = status_text.upper()
        (text_w, _), _ = cv2.getTextSize(status_upper, self.font, 0.38, 1)
        badge_x1 = panel_x1 + 75
        badge_x2 = badge_x1 + text_w + 16
        cv2.rectangle(
            frame,
            (badge_x1, panel_y1 + 80),
            (badge_x2, panel_y1 + 98),
            (20, 20, 25),
            -1,
            cv2.LINE_AA,
        )
        cv2.rectangle(
            frame,
            (badge_x1, panel_y1 + 80),
            (badge_x2, panel_y1 + 98),
            theme_color,
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            status_upper,
            (badge_x1 + 8, panel_y1 + 93),
            self.font,
            0.38,
            theme_color,
            1,
            cv2.LINE_AA,
        )

        bar_x, bar_y = panel_x1 + 15, panel_y1 + 120
        bar_w, bar_h = 200, 6
        cv2.rectangle(
            frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (35, 35, 40), -1, cv2.LINE_AA
        )

        fill_w = int(bar_w * float(prediction))
        if fill_w > 0:
            cv2.rectangle(
                frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), theme_color, -1, cv2.LINE_AA
            )
            cv2.circle(
                frame,
                (bar_x + fill_w, bar_y + int(bar_h / 2)),
                4,
                self.neon_white,
                -1,
                cv2.LINE_AA,
            )

        risk_pct = float(prediction) * 100
        cv2.putText(
            frame,
            f"PRE-FALL RISK: {risk_pct:.0f}%",
            (bar_x, bar_y + 22),
            self.font,
            0.4,
            text_main,
            1,
            cv2.LINE_AA,
        )

        if float(prediction) > GLOBAL_CONFIG.fall_threshold:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 4, cv2.LINE_AA)
            alert_bar_h = 35
            alert_roi = frame[0:alert_bar_h, 0:w]
            alert_red = np.zeros_like(alert_roi)
            alert_red[:] = (0, 0, 220)
            frame[0:alert_bar_h, 0:w] = cv2.addWeighted(alert_red, 0.4, alert_roi, 0.6, 0)
            cv2.putText(
                frame,
                "CRITICAL WARNING: HIGH FALL RISK DETECTED",
                (int(w / 2) - 200, 24),
                self.font,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        return frame

    def draw_angles(
        self,
        frame: np.ndarray,
        points_px: dict[int, tuple[int, int]],
        left_angle: float,
        right_angle: float,
    ) -> np.ndarray:
        """Overlays hip and knee angle telemetry tags on landmark positions."""
        badge_bg = (20, 20, 25)
        badge_border = (60, 60, 65)

        if 23 in points_px and left_angle > 0:
            lx, ly = points_px[23]
            cv2.rectangle(frame, (lx - 65, ly - 25), (lx + 65, ly + 5), badge_bg, -1, cv2.LINE_AA)
            cv2.rectangle(
                frame, (lx - 65, ly - 25), (lx + 65, ly + 5), badge_border, 1, cv2.LINE_AA
            )
            cv2.putText(
                frame,
                f"L-HIP: {int(left_angle)} deg",
                (lx - 55, ly - 10),
                self.font,
                0.35,
                (100, 255, 255),
                1,
                cv2.LINE_AA,
            )

        if 24 in points_px and right_angle > 0:
            rx, ry = points_px[24]
            cv2.rectangle(frame, (rx - 65, ry - 25), (rx + 65, ry + 5), badge_bg, -1, cv2.LINE_AA)
            cv2.rectangle(
                frame, (rx - 65, ry - 25), (rx + 65, ry + 5), badge_border, 1, cv2.LINE_AA
            )
            cv2.putText(
                frame,
                f"R-HIP: {int(right_angle)} deg",
                (rx - 55, ry - 10),
                self.font,
                0.35,
                (100, 255, 255),
                1,
                cv2.LINE_AA,
            )

        return frame
