import numpy as np
import unittest
from tools.master_dialogue import attenuate_verified_pauses


class PauseCleanupTests(unittest.TestCase):
    def test_pause_cleanup_preserves_speech_samples_and_timing(self):
        source = np.full(2000, 1000, dtype=np.int16)
        result = attenuate_verified_pauses(source, 1000, [(0.5, 1.0)])
        self.assertEqual(result.shape, source.shape)
        self.assertEqual(result.dtype, source.dtype)
        np.testing.assert_array_equal(result[:500], source[:500])
        np.testing.assert_array_equal(result[1000:], source[1000:])
        self.assertEqual(result[500], source[500])
        self.assertEqual(result[999], source[999])
        self.assertLess(result[750], 150)
        np.testing.assert_array_equal(source, np.full(2000, 1000, dtype=np.int16))


    def test_pause_cleanup_rejects_overlapping_or_outside_ranges(self):
        for intervals in [[(-1, 1)], [(0.5, 2.1)], [(0.5, 1), (0.8, 1.1)]]:
            with self.assertRaises(ValueError):
                attenuate_verified_pauses(np.ones(2000), 1000, intervals)
