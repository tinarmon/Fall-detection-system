import cv2
import numpy as np
import config

class UIManager:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.tick_counter = 0

    def draw_hud(
        self, frame, tester_name, fps, status_text, prediction, theme_color, bbox
    ):
        """
        วาดระบบ Telemetry HUD สไตล์ Sci-Fi คุณภาพสูง ลงบนเฟรมวิดีโอ
        """
        h, w, _ = frame.shape
        self.tick_counter += 1

        # ----------------------------------------------------
        # 1. วาดระบบเป้าหมายอัจฉริยะ (High-Tech Targeting corners)
        # ----------------------------------------------------
        if bbox:
            x1, y1, x2, y2 = bbox
            # วาดกรอบเป้าหมายกึ่งโปร่งใสบางๆ
            overlay = frame.copy()
            cv2.rectangle(overlay, (x1, y1), (x2, y2), theme_color, 1)
            cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, dst=frame)

            # วาดมุมกล้องเหล็กหนาๆ (Targeting Brackets)
            len_line = min(20, int((x2 - x1) * 0.15))
            thickness = 3
            
            # Top-Left
            cv2.line(frame, (x1, y1), (x1 + len_line, y1), theme_color, thickness)
            cv2.line(frame, (x1, y1), (x1, y1 + len_line), theme_color, thickness)
            # Top-Right
            cv2.line(frame, (x2, y1), (x2 - len_line, y1), theme_color, thickness)
            cv2.line(frame, (x2, y1), (x2, y1 + len_line), theme_color, thickness)
            # Bottom-Left
            cv2.line(frame, (x1, y2), (x1 + len_line, y2), theme_color, thickness)
            cv2.line(frame, (x1, y2), (x1, y2 - len_line), theme_color, thickness)
            # Bottom-Right
            cv2.line(frame, (x2, y2), (x2 - len_line, y2), theme_color, thickness)
            cv2.line(frame, (x2, y2), (x2, y2 - len_line), theme_color, thickness)

            # วาดขีดเป้าเล็งศูนย์กลางเป้าหมายขนาดเล็ก
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            cv2.line(frame, (cx - 5, cy), (cx + 5, cy), theme_color, 1)
            cv2.line(frame, (cx, cy - 5), (cx, cy + 5), theme_color, 1)

        # ----------------------------------------------------
        # 2. แผงควบคุมระบบ (Glassmorphic Telemetry Panel)
        # ----------------------------------------------------
        panel_x1, panel_y1, panel_x2, panel_y2 = 20, 20, 280, 190
        
        # คัดลอก ROI มาทำเบลอและกึ่งโปร่งใส
        roi = frame[panel_y1:panel_y2, panel_x1:panel_x2].copy()
        black_box = roi.copy()
        black_box[:] = (15, 15, 20)  # โทนน้ำเงินเข้มจัดๆ
        
        # ผสมสีให้โปร่งแสง 60%
        blended = cv2.addWeighted(black_box, 0.65, roi, 0.35, 0)
        frame[panel_y1:panel_y2, panel_x1:panel_x2] = blended

        # วาดกรอบพาเนลด้วยเทคโนโลยีเส้นคู่สไตล์ HUD
        cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (80, 80, 90), 1, cv2.LINE_AA)
        cv2.rectangle(frame, (panel_x1 + 3, panel_y1 + 3), (panel_x2 - 3, panel_y2 - 3), (40, 40, 45), 1, cv2.LINE_AA)
        
        # จุดยึดสี่มุมตกแต่งเพื่อความพรีเมียม
        dot_color = (120, 120, 130)
        cv2.circle(frame, (panel_x1 + 6, panel_y1 + 6), 2, dot_color, -1)
        cv2.circle(frame, (panel_x2 - 6, panel_y1 + 6), 2, dot_color, -1)
        cv2.circle(frame, (panel_x1 + 6, panel_y2 - 6), 2, dot_color, -1)
        cv2.circle(frame, (panel_x2 - 6, panel_y2 - 6), 2, dot_color, -1)

        # ----------------------------------------------------
        # 3. ข้อมูลภายในแผงควบคุม (Telemetry Metadata & HUD Text)
        # ----------------------------------------------------
        # หัวข้อระบบและการแสดงสถานะไฟกระพริบ (Blinking LED)
        system_title = "[ SENSOR TELEMETRY ]"
        cv2.putText(frame, system_title, (panel_x1 + 15, panel_y1 + 25), self.font, 0.45, (180, 180, 200), 1, cv2.LINE_AA)
        
        # วาดจุดไฟกระพริบ LED สีเขียว/แดง ตามสถานะของโมเดล
        led_color = theme_color
        # ให้ไฟกะพริบทุกๆ 15 เฟรมในโหมดปกติ
        if status_text == "NORMAL" and (self.tick_counter // 15) % 2 == 0:
            led_color = (40, 40, 40)
        cv2.circle(frame, (panel_x2 - 20, panel_y1 + 21), 5, led_color, -1, cv2.LINE_AA)
        cv2.circle(frame, (panel_x2 - 20, panel_y1 + 21), 7, led_color, 1, cv2.LINE_AA)

        # รายละเอียดข้อความบนหน้าจอหลัก
        cv2.putText(frame, f"TESTER : {tester_name}", (panel_x1 + 15, panel_y1 + 55), self.font, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, f"SYS FPS: {int(fps)}", (panel_x1 + 15, panel_y1 + 80), self.font, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        
        # ปรับขนาดฟอนต์สถานะให้เด่นชัด
        cv2.putText(frame, f"STATUS :", (panel_x1 + 15, panel_y1 + 110), self.font, 0.55, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(frame, status_text, (panel_x1 + 95, panel_y1 + 112), self.font, 0.65, theme_color, 2, cv2.LINE_AA)

        # ----------------------------------------------------
        # 4. หลอดวัดความเสี่ยงการล้มสไตล์ HUD (Segmented Risk Meter)
        # ----------------------------------------------------
        meter_x, meter_y = panel_x1 + 15, panel_y1 + 130
        meter_w, meter_h = 180, 14
        
        # วาดพื้นหลังหลอดวัด
        cv2.rectangle(frame, (meter_x, meter_y), (meter_x + meter_w, meter_y + meter_h), (35, 35, 40), -1, cv2.LINE_AA)
        cv2.rectangle(frame, (meter_x, meter_y), (meter_x + meter_w, meter_y + meter_h), (80, 80, 90), 1, cv2.LINE_AA)

        # วาดแบบแบ่งช่อง (Segmented blocks - 10 ช่อง)
        num_segments = 10
        seg_w = (meter_w - (num_segments - 1) * 2) // num_segments
        filled_segments = int(float(prediction) * num_segments)
        
        for i in range(num_segments):
            seg_x1 = meter_x + i * (seg_w + 2)
            seg_x2 = seg_x1 + seg_w
            
            # ถ้าเป็นช่องที่ต้องเติมสี
            if i < filled_segments:
                # ไล่ระดับสี: ช่องแรกๆ สีเขียว, ช่องกลางสีส้ม, ช่องท้ายสีแดง
                if i < 5:
                    seg_color = (0, 255, 100)      # Neon Green
                elif i < 8:
                    seg_color = (0, 165, 255)     # Neon Orange
                else:
                    seg_color = (0, 0, 255)       # Neon Red
                
                cv2.rectangle(frame, (seg_x1, meter_y + 2), (seg_x2, meter_y + meter_h - 2), seg_color, -1, cv2.LINE_AA)
            else:
                # วาดช่องเปล่าโปร่งๆ
                cv2.rectangle(frame, (seg_x1, meter_y + 2), (seg_x2, meter_y + meter_h - 2), (50, 50, 55), -1, cv2.LINE_AA)

        # แสดงเปอร์เซ็นต์ความเสี่ยงการล้มด้านขวา
        percent_str = f"{float(prediction) * 100:.0f}%"
        cv2.putText(frame, percent_str, (meter_x + meter_w + 10, meter_y + 12), self.font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(frame, "RISK", (meter_x + meter_w + 10, meter_y - 2), self.font, 0.35, (180, 180, 200), 1, cv2.LINE_AA)

        # ----------------------------------------------------
        # 5. ระบบแจ้งเตือนขอบจอสีแดงกระพริบภัยคุกคาม (Emergency Warning Vignette)
        # ----------------------------------------------------
        if float(prediction) > config.FALL_THRESHOLD:
            # ทำให้ขอบจอกระพริบตามความถี่เวลาสั้นๆ
            if (self.tick_counter // 5) % 2 == 0:
                cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 8, cv2.LINE_AA)
                # เพิ่มข้อความเตือนภัยสีแดงขนาดใหญ่ด้านบนจอ
                warning_banner = "!!! WARNING: PRE-FALL EVENT DETECTED !!!"
                text_sz = cv2.getTextSize(warning_banner, self.font, 0.8, 2)[0]
                text_x = (w - text_sz[0]) // 2
                
                # แถบพื้นหลังข้อความเตือนภัยกึ่งโปร่งใส
                banner_y1, banner_y2 = 25, 65
                banner_roi = frame[banner_y1:banner_y2, text_x - 20:text_x + text_sz[0] + 20].copy()
                banner_bg = banner_roi.copy()
                banner_bg[:] = (0, 0, 50)
                banner_blended = cv2.addWeighted(banner_bg, 0.8, banner_roi, 0.2, 0)
                frame[banner_y1:banner_y2, text_x - 20:text_x + text_sz[0] + 20] = banner_blended
                
                cv2.rectangle(frame, (text_x - 20, banner_y1), (text_x + text_sz[0] + 20, banner_y2), (0, 0, 255), 1, cv2.LINE_AA)
                cv2.putText(frame, warning_banner, (text_x, 52), self.font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)

        return frame

    def draw_angles(self, frame, points_px, left_angle, right_angle):
        """
        วาดพิกัดองศาข้อต่อพร้อมสายเชื่อมโยงตัวชี้ข้อมูลสไตล์ล้ำสมัย (HUD Angle Callouts)
        """
        # สะโพกซ้าย (Index 23)
        if 23 in points_px:
            hip_l = points_px[23]
            # สายนำชี้ข้อมูล (Leader line)
            cv2.line(frame, hip_l, (hip_l[0] - 60, hip_l[1] - 40), (255, 255, 0), 1, cv2.LINE_AA)
            cv2.line(frame, (hip_l[0] - 60, hip_l[1] - 40), (hip_l[0] - 110, hip_l[1] - 40), (255, 255, 0), 1, cv2.LINE_AA)
            
            # แสดงค่าองศา
            cv2.putText(
                frame,
                f"L-JOINT: {int(left_angle)}*",
                (hip_l[0] - 105, hip_l[1] - 46),
                self.font,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.circle(frame, hip_l, 4, (255, 255, 0), -1, cv2.LINE_AA)

        # สะโพกขวา (Index 24)
        if 24 in points_px:
            hip_r = points_px[24]
            # สายนำชี้ข้อมูล (Leader line)
            cv2.line(frame, hip_r, (hip_r[0] + 60, hip_r[1] - 40), (255, 255, 0), 1, cv2.LINE_AA)
            cv2.line(frame, (hip_r[0] + 60, hip_r[1] - 40), (hip_r[0] + 110, hip_r[1] - 40), (255, 255, 0), 1, cv2.LINE_AA)
            
            # แสดงค่าองศา
            cv2.putText(
                frame,
                f"R-JOINT: {int(right_angle)}*",
                (hip_r[0] + 15, hip_r[1] - 46),
                self.font,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            cv2.circle(frame, hip_r, 4, (255, 255, 0), -1, cv2.LINE_AA)

        return frame
