import numpy as np

class AngleCalculator:
    @staticmethod
    def calculate_angle(a, b, c):
        """
        คำนวณมุมระหว่าง 3 จุด (a, b, c) ในแบบ 2D (สำหรับโครงร่างเดิม)
        """
        a = np.array(a) # ไหล่
        b = np.array(b) # สะโพก
        c = np.array(c) # เข่า
        
        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)
        
        if angle > 180.0:
            angle = 360 - angle
            
        return angle

    @staticmethod
    def calculate_angle_3d(a, b, c):
        """
        คำนวณมุม 3 มิติระหว่าง 3 จุด (a, b, c) ในหน่วยองศา (สำหรับความมั่นคงเชิงมุมไม่ว่ากล้องหันมุมไหน)
        a = ไหล่, b = สะโพก (จุดยอดมุม), c = เข่า
        """
        a = np.array(a)
        b = np.array(b)
        c = np.array(c)
        
        u = a - b
        v = c - b
        
        dot_product = np.dot(u, v)
        norm_u = np.linalg.norm(u)
        norm_v = np.linalg.norm(v)
        
        if norm_u == 0 or norm_v == 0:
            return 180.0
            
        cosine_angle = dot_product / (norm_u * norm_v)
        cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
        
        angle = np.arccos(cosine_angle)
        return np.degrees(angle)