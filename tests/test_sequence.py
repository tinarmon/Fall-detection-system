import unittest

import numpy as np

from scripts.train import create_sequences_vectorized


class TestSequenceVectorization(unittest.TestCase):
    def test_create_sequences_vectorized_shapes(self):
        n_samples = 50
        n_features = 18
        time_steps = 10

        x = np.arange(n_samples * n_features, dtype=np.float32).reshape(n_samples, n_features)
        y = np.arange(n_samples, dtype=np.int32)

        xs, ys = create_sequences_vectorized(x, y, time_steps)

        expected_windows = n_samples - time_steps
        self.assertEqual(xs.shape, (expected_windows, time_steps, n_features))
        self.assertEqual(ys.shape, (expected_windows,))

        # Verify the first sequence matches x[0:10] and first label matches y[10]
        np.testing.assert_array_equal(xs[0], x[0:10])
        self.assertEqual(ys[0], y[10])

        # Verify the last sequence matches x[-11:-1] or appropriate window
        np.testing.assert_array_equal(xs[-1], x[-11:-1])
        self.assertEqual(ys[-1], y[-1])

    def test_create_sequences_insufficient_samples(self):
        x = np.zeros((5, 18))
        y = np.zeros(5)
        with self.assertRaises(ValueError):
            create_sequences_vectorized(x, y, time_steps=10)


if __name__ == "__main__":
    unittest.main()
