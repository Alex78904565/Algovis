import unittest
import numpy as np

from tools.audio_pipeline import insert_verified_master_pauses


class MasterPauseInsertionTests(unittest.TestCase):
    def test_quiet_pause_preserves_speech_and_translates_following_audio(self):
        samples=np.zeros(1000,dtype=np.int16)
        samples[:300]=7000;samples[700:]=-6000
        output,records=insert_verified_master_pauses(samples,1000,[{'at':.5,'seconds':.2}])
        np.testing.assert_array_equal(output[:300],samples[:300])
        np.testing.assert_array_equal(output[900:],samples[700:])
        self.assertEqual(len(output),1200)
        self.assertEqual(records[0]['inserted_samples'],200)
        self.assertFalse(output[500:700].any())

    def test_stale_pause_cannot_cut_through_speech(self):
        with self.assertRaisesRegex(ValueError,'intersects speech'):
            insert_verified_master_pauses(np.full(1000,7000,dtype=np.int16),1000,
                                          [{'at':.5,'seconds':.2}])

    def test_multiple_points_refer_to_the_original_master(self):
        samples=np.zeros(1000,dtype=np.int16);samples[500]=10000
        output,_=insert_verified_master_pauses(samples,1000,
            [{'at':.3,'seconds':.1},{'at':.7,'seconds':.2}])
        self.assertEqual(len(output),1300)
        self.assertEqual(np.flatnonzero(output).tolist(),[600])
