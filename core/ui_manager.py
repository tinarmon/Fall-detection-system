import cv2
import numpy as np
import config

class UIManager:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.neon_white = (255, 255, 255)

    def draw_hud(self, frame, tester_name, fps, status_text, prediction, theme_color, bbox):
        """
        วาดระบบ Telemetry HUD สไตล์ Cyberpunk/Sci-Fi ไฮเทค เรียบหรู
        """
        h, w, _ = frame.shape

        # 1. วาดเส้นกริดสแกนบางๆ แบบ Sci-Fi (Faint grid overlay)
        grid_color = (30, 30, 35)
        for i in range(1, 4):
            x_line = int(w * i / 4)
            y_line = int(h * i / 4)
            cv2.line(frame, (x_line, 0), (x_line, h), grid_color, 1, cv2.LINE_AA)
            cv2.line(frame, (0, y_line), (w, y_line), grid_color, 1, cv2.LINE_AA)

        # 2. กรอบเป้าหมายแบบ Sci-Fi Corner Brackets (แทนกล่องสี่เหลี่ยมธรรมดา)
        if bbox:
            x1, y1, x2, y2 = bbox
            length = min(30, int((x2 - x1) * 0.2))
            thickness = 2
            
            # วาดกรอบสแกนเนอร์ที่มุมทั้ง 4 ด้าน
            # บน-ซ้าย
            cv2.line(frame, (x1, y1), (x1 + length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y1), (x1, y1 + length), theme_color, thickness, cv2.LINE_AA)
            # บน-ขวา
            cv2.line(frame, (x2, y1), (x2 - length, y1), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y1), (x2, y1 + length), theme_color, thickness, cv2.LINE_AA)
            # ล่าง-ซ้าย
            cv2.line(frame, (x1, y2), (x1 + length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x1, y2), (x1, y2 - length), theme_color, thickness, cv2.LINE_AA)
            # ล่าง-ขวา
            cv2.line(frame, (x2, y2), (x2 - length, y2), theme_color, thickness, cv2.LINE_AA)
            cv2.line(frame, (x2, y2), (x2, y2 - length), theme_color, thickness, cv2.LINE_AA)

            # วาดเป้าเล็งตรงกลางตัว (Crosshair centroid)
            cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
            cv2.drawMarker(frame, (cx, cy), theme_color, cv2.MARKER_CROSS, 12, 1, cv2.LINE_AA)

        # 3. พาเนลแก้วสไตล์ Cyberpunk (Glassmorphic Panel UI)
        panel_x1, panel_y1, panel_x2, panel_y2 = 25, 25, 300, 165
        
        # มิกซ์สีพื้นหลังพาเนลแบบโปร่งแสง (Translucent overlay)
        roi = frame[panel_y1:panel_y2, panel_x1:panel_x2]
        black_box = np.zeros_like(roi)
        black_box[:] = (12, 12, 16) # มิลเลนเนียมแบล็ค
        blended = cv2.addWeighted(black_box, 0.65, roi, 0.35, 0)
        frame[panel_y1:panel_y2, panel_x1:panel_x2] = blended

        # วาดขอบพาเนลและมุมพาเนล (High-tech borders)
        cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (75, 75, 80), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 - 3, panel_y1 - 3), (panel_x1 + 10, panel_y1 + 10), theme_color, -1) # จุดมุมซ้ายบน
        
        # 4. แสดงข้อความสถานะและระดับความปลอดภัย (HUD Telemetry Text)
        text_color_main = (245, 245, 250)
        text_color_sub = (140, 140, 145)

        # ข้อมูลผู้ใช้งานระบบ
        cv2.putText(frame, f"SYSTEM CORE v2.0", (panel_x1 + 15, panel_y1 + 22), self.font, 0.35, theme_color, 1, cv2.LINE_AA)
        cv2.putText(frame, f"TARGET: {tester_name.upper()}", (panel_x1 + 15, panel_y1 + 45), self.font, 0.45, text_color_main, 1, cv2.LINE_AA)
        cv2.putText(frame, f"FPS: {int(fps)} Hz // LATENCY: {int(1000/fps if fps > 0 else 0)} ms", (panel_x1 + 15, panel_y1 + 65), self.font, 0.35, text_color_sub, 1, cv2.LINE_AA)
        
        # แยกสีเตือนภัยตามความปลอดภัย
        cv2.putText(frame, "STATUS:", (panel_x1 + 15, panel_y1 + 92), self.font, 0.4, text_color_sub, 1, cv2.LINE_AA)
        
        # วาดป้ายสัญญาณเตือนภัยขนาดเล็ก (LED Status tag)
        cv2.rectangle(frame, (panel_x1 + 75, panel_y1 + 80), (panel_x2 - 15, panel_y1 + 98), (20, 20, 25), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 + 75, panel_y1 + 80), (panel_x2 - 15, panel_y1 + 98), theme_color, 1, cv2.LINE_AA)
        cv2.putText(frame, status_text.upper(), (panel_x1 + 85, panel_y1 + 93), self.font, 0.4, theme_color, 1, cv2.LINE_AA)

        # 5. หลอดความเสี่ยงการล้มพร้อมสเกลวัด (Sci-Fi Fall Threat Indicator)
        bar_x, bar_y = panel_x1 + 15, panel_y1 + 120
        bar_w, bar_h = 200, 6
        
        # ช่องสเกลเปล่าด้านหลัง
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (35, 35, 40), -1, cv2.LINE_AA)
        
        # ปรับสเกลระดับ
        fill_w = int(bar_w * float(prediction))
        if fill_w > 0:
            # วาดแถบระดับความเสี่ยง
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), theme_color, -1, cv2.LINE_AA)
            # เพิ่มเอฟเฟกต์แสงจ้าที่ส่วนท้ายของหลอด (Neon glow tip)
            cv2.circle(frame, (bar_x + fill_w, bar_y + int(bar_h/2)), 4, self.neon_white, -1, cv2.LINE_AA)

        # ค่าเปอร์เซ็นต์แบบดิจิทัล
        risk_pct = float(prediction) * 100
        percent_str = f"FALL RISK: {risk_pct:.0f}%"
        cv2.putText(frame, percent_str, (bar_x, bar_y + 22), self.font, 0.4, text_color_main, 1, cv2.LINE_AA)

        # 6. ไฟกะพริบแจ้งเตือนระดับวิกฤต (Critical flashing alert overlay)
        if float(prediction) > config.FALL_THRESHOLD:
            # ปรับกรอบกะพริบรอบหน้าจอความหนา 4 พิกเซล
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 4, cv2.LINE_AA)
            
            # แถบคำเตือนสีแดงกะพริบวิกฤตด้านบนจอภาพ
            alert_bar_h = 35
            alert_roi = frame[0:alert_bar_h, 0:w]
            alert_red = np.zeros_like(alert_roi)
            alert_red[:] = (0, 0, 220)
            frame[0:alert_bar_h, 0:w] = cv2.addWeighted(alert_red, 0.4, alert_roi, 0.6, 0)
            
            # ข้อความสัญญาณอันตรายกะพริบเตือนตรงกลางจอ
            alert_msg = "WARNING! PRE-FALL EVENT DETECTED"
            msg_size = cv2.getTextSize(alert_msg, self.font, 0.55, 1)[0]
            msg_x = int((w - msg_size[0]) / 2)
            cv2.putText(frame, alert_msg, (msg_x, 22), self.font, 0.55, self.neon_white, 1, cv2.LINE_AA)

        return frame

    def draw_angles(self, frame, points_px, left_angle, right_angle):
        """
        วาดมุมข้อต่อแบบมีเส้นชี้ Telemetry และค่าสีสันตามสไตล์ Cyberpunk
        """
        # มุมฝั่งซ้าย (ไหล่ -> สะโพก -> เข่า)
        if 23 in points_px:
            hip_l = points_px[23]
            # เส้นชี้บ่งบอกพิกัด
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

        # มุมฝั่งขวา (ไหล่ -> สะโพก -> เข่า)
        if 24 in points_px:
            hip_r = points_px[24]
            # เส้นชี้บ่งบอกพิกัด
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
