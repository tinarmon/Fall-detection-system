import unittest

from src.fall_detection.pose import PoseEstimator


class TestPoseEstimatorFeatures(unittest.TestCase):
    def test_get_relative_features_missing_key(self):
        partial_points = {11: (0.1, 0.2, 0.3)}
        features = PoseEstimator.get_relative_features(partial_points)
        self.assertEqual(len(features), 18)
        self.assertEqual(features, [0.0] * 18)

    def test_get_relative_features_valid_points(self):
        # Create a synthetic set of 6 landmarks
        points = {
            11: (0.4, 0.2, 0.0),  # L Shoulder
            12: (0.6, 0.2, 0.0),  # R Shoulder
            23: (0.45, 0.6, 0.0),  # L Hip
            24: (0.55, 0.6, 0.0),  # R Hip
            25: (0.45, 0.9, 0.0),  # L Knee
            26: (0.55, 0.9, 0.0),  # R Knee
        }
        features = PoseEstimator.get_relative_features(points)
        self.assertEqual(len(features), 18)
        # Verify hip center is centered around (0, 0, 0)
        hip_x = (features[6] + features[9]) / 2.0
        hip_y = (features[7] + features[10]) / 2.0
        hip_z = (features[8] + features[11]) / 2.0
        self.assertAlmostEqual(hip_x, 0.0, places=5)
        self.assertAlmostEqual(hip_y, 0.0, places=5)
        self.assertAlmostEqual(hip_z, 0.0, places=5)


if __name__ == "__main__":
    unittest.main()
