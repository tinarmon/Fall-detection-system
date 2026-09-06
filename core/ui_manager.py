import cv2
import numpy as np
import config


class UIManager:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.neon_white = (255, 255, 255)

    def draw_hud(self, frame, tester_name, fps, status_text, prediction, theme_color, bbox, source_label="LOCAL"):
        """
        Render Cyberpunk / Sci-Fi Telemetry HUD overlay.
        """
        h, w, _ = frame.shape

        # 1. Sci-Fi Faint Grid Overlay
        grid_color = (30, 30, 35)
        for i in range(1, 4):
            x_line = int(w * i / 4)
            y_line = int(h * i / 4)
            cv2.line(frame, (x_line, 0), (x_line, h), grid_color, 1, cv2.LINE_AA)
            cv2.line(frame, (0, y_line), (w, y_line), grid_color, 1, cv2.LINE_AA)

        # 2. Sci-Fi Corner Brackets & Centroid Crosshair
        if bbox:
            x1, y1, x2, y2 = bbox
            length = min(30, int((x2 - x1) * 0.2))
            thickness = 2
            
            # Top-Left
            cv2.line(frame, (x1, y1), (x1 + length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y1), (x1, y1 + length), theme_color, thickness, cv2.LINE_AA)
            # Top-Right
            cv2.line(frame, (x2, y1), (x2 - length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y1), (x2, y1 + length), theme_color, thickness, cv2.LINE_AA)
            # Bottom-Left
            cv2.line(frame, (x1, y2), (x1 + length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y2), (x1, y2 - length), theme_color, thickness, cv2.LINE_AA)
            # Bottom-Right
            cv2.line(frame, (x2, y2), (x2 - length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y2), (x2, y2 - length), theme_color, thickness, cv2.LINE_AA)

            # Centroid crosshair
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            cv2.drawMarker(frame, (cx, cy), theme_color, cv2.MARKER_CROSS, 12, 1, cv2.LINE_AA)

        # 3. Glassmorphic Telemetry Panel UI
        panel_x1, panel_y1, panel_x2, panel_y2 = 20, 20, 310, 175
        
        # Translucent overlay
        roi = frame[panel_y1:panel_y2, panel_x1:panel_x2]
        black_box = np.zeros_like(roi)
        black_box[:] = (12, 12, 16)
        blended = cv2.addWeighted(black_box, 0.70, roi, 0.30, 0)
        frame[panel_y1:panel_y2, panel_x1:panel_x2] = blended

        # High-tech borders
        cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (75, 75, 80), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 - 2, panel_y1 - 2), (panel_x1 + 10, panel_y1 + 10), theme_color, -1)
        
        # 4. Telemetry Text
        text_color_main = (245, 245, 250)
        text_color_sub = (140, 140, 145)

        cv2.putText(frame, f"DPDF SYSTEM v2.0 // {source_label}", (panel_x1 + 15, panel_y1 + 22), self.font, 0.35, theme_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"CAM: {tester_name.upper()}", (panel_x1 + 15, panel_y1 + 45), self.font, 0.45, text_color_main, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {int(fps)} Hz // LATENCY: {int(1000/fps if fps > 0 else 0)} ms", (panel_x1 + 15, panel_y1 + 65), self.font, 0.35, text_color_sub, 1, cv2.LINE_AA)
        
        # Status Tag
        cv2.putText(frame, "STATUS:", (panel_x1 + 15, panel_y1 + 92), self.font, 0.4, text_color_sub, 1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 + 75, panel_y1 + 80), (panel_x2 - 15, panel_y1 + 98), (20, 20, 25), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 + 75, panel_y1 + 80), (panel_x2 - 15, panel_y1 + 98), theme_color, 1, cv2.LINE_AA)
        cv2.putText(frame, status_text.upper(), (panel_x1 + 85, panel_y1 + 93), self.font, 0.38, theme_color, 1, cv2.LINE_AA)

        # 5. Sci-Fi Fall Risk Indicator Bar
        bar_x, bar_y = panel_x1 + 15, panel_y1 + 120
        bar_w, bar_h = 200, 6
        
        # Track background
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (35, 35, 40), -1, cv2.LINE_AA)
        
        fill_w = int(bar_w * float(prediction))
        if fill_w > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), theme_color, -1, cv2.LINE_AA)
            cv2.circle(frame, (bar_x + fill_w, bar_y + int(bar_h/2)), 4, self.neon_white, -1, cv2.LINE_AA)

        risk_pct = float(prediction) * 100
        percent_str = f"PRE-FALL RISK: {risk_pct:.0f}%"
        cv2.putText(frame, percent_str, (bar_x, bar_y + 22), self.font, 0.4, text_color_main, 1, cv2.LINE_AA)

        # 6. Critical Flashing Danger Overlay
        if float(prediction) > config.FALL_THRESHOLD:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 4, cv2.LINE_AA)
            
            alert_bar_h = 35
            alert_roi = frame[0:alert_bar_h, 0:w]
            alert_red = np.zeros_like(alert_roi)
            alert_red[:] = (0, 0, 220)
            frame[0:alert_bar_h, 0:w] = cv2.addWeighted(alert_red, 0.4, alert_roi, 0.6, 0)
            
            alert_msg = "WARNING! PRE-FALL EVENT DETECTED"
            msg_size = cv2.getTextSize(alert_msg, self.font, 0.55, 1)[0]
            msg_x = int((w - msg_size[0]) / 2)
            cv2.putText(frame, alert_msg, (msg_x, 22), self.font, 0.55, self.neon_white, 1, cv2.LINE_AA)

        return frame

    def draw_angles(self, frame, points_px, left_angle, right_angle):
        """
        Draw angle telemetry on skeleton joint points.
        """
        if 23 in points_px:
            hip_l = points_px[23]
            cv2.line(frame, (hip_l[0] - 8, hip_l[1]), (hip_l[0] - 25, hip_l[1]), (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(
                frame,
                f"L_ANG: {int(left_angle)}*",
                (hip_l[0] - 90, hip_l[1] + 4),
                self.font,
                0.35,
                (0, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.circle(frame, hip_l, 4, (0, 255, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, hip_l, 2, self.neon_white, -1, cv2.LINE_AA)

        if 24 in points_px:
            hip_r = points_px[24]
            cv2.line(frame, (hip_r[0] + 8, hip_r[1]), (hip_r[0] + 25, hip_r[1]), (0, 165, 255), 1, cv2.LINE_AA)
            cv2.putText(
                frame,
                f"R_ANG: {int(right_angle)}*",
                (hip_r[0] + 32, hip_r[1] + 4),
                self.font,
                0.35,
                (0, 165, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.circle(frame, hip_r, 4, (0, 165, 255), -1, cv2.LINE_AA)
            cv2.circle(frame, hip_r, 2, self.neon_white, -1, cv2.LINE_AA)

        return frame

    def generate_no_signal_frame(self, w=640, h=480, camera_name="Camera", status="CONNECTING...", detail=""):
        """
        Generate a Cyberpunk-styled 'No Signal / Reconnecting' placeholder frame.
        """
        w = max(320, int(w))
        h = max(240, int(h))
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (12, 12, 16)  # Dark millennium background

        # Grid lines
        grid_color = (25, 25, 30)
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), grid_color, 1)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), grid_color, 1)

        # Sci-Fi Corner Brackets
        corner_len = min(40, int(w * 0.1))
        accent_color = (0, 140, 255) if "RECONNECT" in status.upper() else ((0, 215, 255) if "CONNECT" in status.upper() else (60, 60, 220))
        
        cv2.line(frame, (20, 20), (20 + corner_len, 20), accent_color, 2, cv2.LINE_AA)
        cv2.line(frame, (20, 20), (20, 20 + corner_len), accent_color, 2, cv2.LINE_AA)
        
        cv2.line(frame, (w - 20, 20), (w - 20 - corner_len, 20), accent_color, 2, cv2.LINE_AA)
        cv2.line(frame, (w - 20, 20), (w - 20, 20 + corner_len), accent_color, 2, cv2.LINE_AA)
        
        cv2.line(frame, (20, h - 20), (20 + corner_len, h - 20), accent_color, 2, cv2.LINE_AA)
        cv2.line(frame, (20, h - 20), (20, h - 20 - corner_len), accent_color, 2, cv2.LINE_AA)
        
        cv2.line(frame, (w - 20, h - 20), (w - 20 - corner_len, h - 20), accent_color, 2, cv2.LINE_AA)
        cv2.line(frame, (w - 20, h - 20), (w - 20, h - 20 - corner_len), accent_color, 2, cv2.LINE_AA)

        # Center Telemetry Box
        cx, cy = int(w / 2), int(h / 2)
        cv2.drawMarker(frame, (cx, cy), (45, 45, 50), cv2.MARKER_CROSS, 30, 1, cv2.LINE_AA)
        
        # Status Text
        title_text = f"TARGET: {camera_name.upper()}"
        t_size = cv2.getTextSize(title_text, self.font, 0.55, 1)[0]
        cv2.putText(frame, title_text, (cx - int(t_size[0] / 2), cy - 30), self.font, 0.55, (230, 230, 235), 1, cv2.LINE_AA)

        s_size = cv2.getTextSize(status.upper(), self.font, 0.5, 1)[0]
        cv2.putText(frame, status.upper(), (cx - int(s_size[0] / 2), cy), self.font, 0.5, accent_color, 1, cv2.LINE_AA)

        if detail:
            d_text = f"SOURCE: {detail}"
            if len(d_text) > 45:
                d_text = d_text[:42] + "..."
            d_size = cv2.getTextSize(d_text, self.font, 0.35, 1)[0]
            cv2.putText(frame, d_text, (cx - int(d_size[0] / 2), cy + 28), self.font, 0.35, (120, 120, 125), 1, cv2.LINE_AA)

        cv2.putText(frame, "AUTOMATIC RECOVERY ENGINE ACTIVE", (cx - 120, cy + 55), self.font, 0.32, (80, 80, 85), 1, cv2.LINE_AA)

        return frame
