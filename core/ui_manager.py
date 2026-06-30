import cv2
import config

class UIManager:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX

    def draw_hud(
        self, frame, tester_name, fps, status_text, prediction, theme_color, bbox
    ):
        """
        ฟังก์ชันสำหรับวาด UI ทั้งหมดลงบนเฟรมวิดีโอ
        """
        h, w, _ = frame.shape

        # 1. วาด Bounding Box รอบตัวบุคคล
        if bbox:
            cv2.rectangle(frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), theme_color, 2)

        # 2. แถบ Dashboard กึ่งโปร่งใส มุมซ้ายบน
        # ✅ แก้: blend เฉพาะ ROI แทนการ blend ทั้งจอ → หน้าจอไม่ลายอีกต่อไป
        roi = frame[15:165, 15:260].copy()
        black_box = roi.copy()
        black_box[:] = (0, 0, 0)
        blended = cv2.addWeighted(black_box, 0.55, roi, 0.45, 0)
        frame[15:165, 15:260] = blended

        # 3. ใส่ข้อความลงใน Dashboard
        cv2.putText(
            frame,
            f"TESTER : {tester_name}",
            (30, 45),
            self.font,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"FPS    : {int(fps)}",
            (30, 75),
            self.font,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"STATUS : {status_text}",
            (30, 108),
            self.font,
            0.7,
            theme_color,
            2,
            cv2.LINE_AA,
        )

        # 4. Risk Bar (หลอดความเสี่ยง)
        bar_x, bar_y, bar_w, bar_h = 30, 125, 170, 12
        cv2.rectangle(
            frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1
        )
        fill_w = int(bar_w * float(prediction))
        if fill_w > 0:
            cv2.rectangle(
                frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), theme_color, -1
            )
        cv2.putText(
            frame,
            f"{float(prediction) * 100:.0f}%",
            (bar_x + bar_w + 8, bar_y + 10),
            self.font,
            0.5,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # 5. วาดขอบจอสีแดงเตือนภัยเมื่อมีความเสี่ยงสูง
        if float(prediction) > config.FALL_THRESHOLD:
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), theme_color, 6)

        return frame  # ✅ return อยู่ท้ายสุด ถูกต้อง

    def draw_angles(self, frame, points_px, left_angle, right_angle):
        """วาดองศาข้อต่อบนหน้าจอ"""
        if 23 in points_px:  # สะโพกซ้าย
            cv2.putText(
                frame,
                f"L: {int(left_angle)} deg",
                (points_px[23][0] - 50, points_px[23][1]),
                self.font,
                0.5,
                (255, 255, 0),
                1,
                cv2.LINE_AA,
            )
        if 24 in points_px:  # สะโพกขวา
            cv2.putText(
                frame,
                f"R: {int(right_angle)} deg",
                (points_px[24][0] + 10, points_px[24][1]),
                self.font,
                0.5,
                (255, 255, 0),
                1,
                cv2.LINE_AA,
            )
        return frame
