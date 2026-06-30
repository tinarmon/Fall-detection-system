import cv2
import config

class UIManager:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_hud(
        self, frame, tester_name, fps, status_text, prediction, theme_color, bbox
    ):
        """
        วาดระบบ Telemetry HUD สไตล์มินิมอลลิสต์ เรียบหรู (Minimalist telemetry HUD)
        """
        h, w, _ = frame.shape

        # 1. กรอบเป้าหมายแบบเรียบง่าย (Thin, Minimal Bounding Box)
        if bbox:
            x1, y1, x2, y2 = bbox
            # วาดเส้นกรอบเป้าหมายบางๆ เพียง 1 พิกเซล
            cv2.rectangle(frame, (x1, y1), (x2, y2), theme_color, 1, cv2.LINE_AA)

        # 2. พาเนลแสดงผลข้อมูลแบบเรียบง่าย (Minimal Glassmorphic Panel)
        # ขนาดพาเนลที่กระทัดรัด
        panel_x1, panel_y1, panel_x2, panel_y2 = 20, 20, 260, 140
        
        # ผสมพื้นหลังพาเนลสีดำโปร่งแสงบางๆ
        roi = frame[panel_y1:panel_y2, panel_x1:panel_x2].copy()
        black_box = roi.copy()
        black_box[:] = (10, 10, 10)  # สีออฟแบล็ค
        blended = cv2.addWeighted(black_box, 0.40, roi, 0.60, 0)
        frame[panel_y1:panel_y2, panel_x1:panel_x2] = blended

        # วาดเส้นขอบพาเนลบางๆ 1 พิกเซล สีเทาเข้ม
        cv2.rectangle(frame, (panel_x1, panel_y1), (panel_x2, panel_y2), (60, 60, 65), 1, cv2.LINE_AA)

        # 3. การแสดงผลข้อความในพาเนล (Clean HUD Text)
        # ใช้สีขาวและเทาหม่นสไตล์มินิมอล
        text_color_main = (240, 240, 240)
        text_color_sub = (160, 160, 165)

        # ผู้ทดสอบ และ FPS
        cv2.putText(frame, f"tester: {tester_name.lower()}", (panel_x1 + 15, panel_y1 + 25), self.font, 0.45, text_color_main, 1, cv2.LINE_AA)
        cv2.putText(frame, f"fps: {int(fps)}", (panel_x1 + 15, panel_y1 + 50), self.font, 0.4, text_color_sub, 1, cv2.LINE_AA)
        
        # สถานะ (ปรับสีตาม Theme แต่ใช้ระดับความเข้มที่สบายตา)
        cv2.putText(frame, "status:", (panel_x1 + 15, panel_y1 + 80), self.font, 0.45, text_color_sub, 1, cv2.LINE_AA)
        cv2.putText(frame, status_text.lower(), (panel_x1 + 75, panel_y1 + 80), self.font, 0.5, theme_color, 1, cv2.LINE_AA)

        # 4. หลอดวัดความเสี่ยงแบบเส้นตรงเรียบบาง (Thin Continuous Risk Bar)
        bar_x, bar_y = panel_x1 + 15, panel_y1 + 105
        bar_w, bar_h = 160, 3  # หลอดบางมากเพียง 3 พิกเซล
        
        # พื้นหลังหลอดวัด
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (45, 45, 48), -1, cv2.LINE_AA)
        
        # แถบสีแสดงความเสี่ยงจริง
        fill_w = int(bar_w * float(prediction))
        if fill_w > 0:
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), theme_color, -1, cv2.LINE_AA)

        # แสดงเปอร์เซ็นต์ความเสี่ยงการล้ม
        percent_str = f"{float(prediction) * 100:.0f}%"
        cv2.putText(frame, percent_str, (bar_x + bar_w + 10, bar_y + 5), self.font, 0.4, text_color_main, 1, cv2.LINE_AA)

        # 5. สัญญาณเตือนกรณีมีความเสี่ยงสูง (Minimal Threat Indication)
        # ไม่มีการกระพริบขอบจอทั้งหมดหรือแบนเนอร์ใหญ่โต ให้แสดงกรอบสีแดงบางๆ รอบจอเท่านั้น
        if float(prediction) > config.FALL_THRESHOLD:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 2, cv2.LINE_AA)

        return frame

    def draw_angles(self, frame, points_px, left_angle, right_angle):
        """
        วาดองศาข้อต่อแบบตัวหนังสือเรียบง่ายระบุพิกัดโดยตรง (Minimal Angle Texts)
        """
        text_color = (255, 255, 255)
        
        # มุมข้อต่อสะโพกซ้าย
        if 23 in points_px:
            hip_l = points_px[23]
            cv2.putText(
                frame,
                f"L: {int(left_angle)}*",
                (hip_l[0] - 55, hip_l[1]),
                self.font,
                0.4,
                text_color,
                1,
                cv2.LINE_AA,
            )
            # จุดวงกลมบอกตำแหน่งแบบเรียบง่ายขนาดเล็กที่สุด
            cv2.circle(frame, hip_l, 2, text_color, -1, cv2.LINE_AA)

        # มุมข้อต่อสะโพกขวา
        if 24 in points_px:
            hip_r = points_px[24]
            cv2.putText(
                frame,
                f"R: {int(right_angle)}*",
                (hip_r[0] + 15, hip_r[1]),
                self.font,
                0.4,
                text_color,
                1,
                cv2.LINE_AA,
            )
            cv2.circle(frame, hip_r, 2, text_color, -1, cv2.LINE_AA)

        return frame
