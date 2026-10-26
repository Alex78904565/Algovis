import unittest

import numpy as np

from tools.repair_dialogue import repair_isolated_impulses


class ImpulseRepairTests(unittest.TestCase):
    def test_repairs_an_impulse_without_muting_a_pause_or_moving_speech(self):
        signal = np.full(48000,.002,dtype=np.float32)
        signal[24000] = .12
        signal[30000:33000] = .1*np.sin(np.arange(3000)*.1)
        before=signal.copy()
        repaired=repair_isolated_impulses(signal,48000,[.5])
        self.assertEqual(repaired.shape,signal.shape)
        self.assertLess(abs(repaired[24000]),.003)
        np.testing.assert_array_equal(repaired[:23856],before[:23856])
        np.testing.assert_array_equal(repaired[24144:],before[24144:])
        np.testing.assert_array_equal(signal,before)


if __name__=='__main__':
    unittest.main()
