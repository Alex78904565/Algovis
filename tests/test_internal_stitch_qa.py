import unittest

import numpy as np

from tools.internal_stitch_qa import inspect_chunk, transcript_intervals


class InternalStitchTests(unittest.TestCase):
    def test_segment_words_protect_speech_from_noise_candidate_classification(self):
        document = {"segments": [{"words": [{"start": .45, "end": .55}]}]}
        intervals = transcript_intervals(document)
        # A short consonant surrounded by silence must not become a
        # "handling noise" candidate just because words are nested in segments.
        signal = np.zeros(1500, dtype=np.float32)
        signal[450:550] = .05
        events = inspect_chunk(signal, 1000, "sample",
                               {"master_start": 0, "master_end": 1.5,
                                "chunk": 1, "source": "sample.wav"}, intervals)
        self.assertFalse(any(event["kind"] in ("quiet_island", "quiet_impulse") for event in events))

    def test_flat_and_segment_word_formats_give_the_same_intervals(self):
        words = [{"start": 2, "end": 3}, {"start": 0, "end": 1}]
        self.assertEqual(transcript_intervals({"words": words}),
                         transcript_intervals({"segments": [{"words": words}]}))


if __name__ == "__main__":
    unittest.main()
