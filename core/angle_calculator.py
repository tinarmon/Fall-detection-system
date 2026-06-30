import numpy as np

class AngleCalculator:
    @staticmethod
    def calculate_angle(a, b, c):
        """
        คำนวณมุมระหว่าง 3 จุด (a, b, c)
        a = ไหล่, b = สะโพก (จุดยอดมุม), c = เข่า
        """
        a = np.array(a) # ไหล่
        b = np.array(b) # สะโพก
        c = np.array(c) # เข่า
        
        # ใช้ arctan2 ในการหาค่ามุม (Radians) และแปลงเป็นองศา (Degrees)
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        # ปรับมุมไม่ให้เกิน 180 องศา
        if angle > 180.0:
            angle = 360 - angle
            
        return angle