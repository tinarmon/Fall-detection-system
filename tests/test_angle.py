import unittest

from src.fall_detection.geometry import calculate_angle_2d, calculate_angle_3d


class TestGeometry(unittest.TestCase):
    def test_calculate_angle_2d_right_angle(self):
        a = [0.0, 1.0]
        b = [0.0, 0.0]
        c = [1.0, 0.0]
        self.assertAlmostEqual(calculate_angle_2d(a, b, c), 90.0, places=4)

    def test_calculate_angle_2d_straight_line(self):
        a = [0.0, 1.0]
        b = [0.0, 0.0]
        c = [0.0, -1.0]
        self.assertAlmostEqual(calculate_angle_2d(a, b, c), 180.0, places=4)

    def test_calculate_angle_3d_acute(self):
        a = [1.0, 1.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [1.0, 0.0, 0.0]
        angle = calculate_angle_3d(a, b, c)
        self.assertAlmostEqual(angle, 45.0, places=4)

    def test_calculate_angle_3d_obtuse(self):
        a = [-1.0, 1.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [1.0, 0.0, 0.0]
        angle = calculate_angle_3d(a, b, c)
        self.assertAlmostEqual(angle, 135.0, places=4)

    def test_calculate_angle_3d_near_zero(self):
        a = [0.0, 0.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [1.0, 0.0, 0.0]
        angle = calculate_angle_3d(a, b, c)
        self.assertEqual(angle, 180.0)

    def test_calculate_angle_3d_orthogonal(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]
        angle = calculate_angle_3d(a, b, c)
        self.assertAlmostEqual(angle, 90.0, places=4)

    def test_calculate_angle_3d_degenerate(self):
        a = [0.0, 0.0, 0.0]
        b = [0.0, 0.0, 0.0]
        c = [0.0, 1.0, 0.0]
        angle = calculate_angle_3d(a, b, c)
        self.assertEqual(angle, 180.0)


if __name__ == "__main__":
    unittest.main()
