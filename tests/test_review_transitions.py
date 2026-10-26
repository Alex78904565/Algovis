from __future__ import annotations

import unittest

from algovis.review.transitions import build_transition_index


class ReviewTransitionTests(unittest.TestCase):
    def test_simultaneous_animations_form_one_frame_triplet(self):
        transitions = build_transition_index({
            "animations": [
                {"id": "a", "play": 1, "start": 1.0, "end": 1.5, "label": "title"},
                {"id": "b", "play": 1, "start": 1.2, "end": 2.0, "label": "equation"},
            ],
        }, [{"name": "introduce", "time": 1.01, "phrase": "our equation"}], 4, frame_rate=10)

        self.assertEqual(len(transitions), 1)
        change = transitions[0]
        self.assertEqual((change["start"], change["end"]), (1.0, 2.0))
        self.assertEqual(change["cue"], "introduce")
        self.assertEqual([frame["time"] for frame in change["frames"]], [.9, 1.5, 2.0])

    def test_frames_stay_inside_trimmed_video(self):
        transitions = build_transition_index({
            "animations": [
                {"play": 0, "start": 0, "end": .5},
                {"play": 1, "start": 2.5, "end": 4},
                {"play": 2, "start": 4, "end": 5},
            ],
        }, [], 3, frame_rate=10)

        self.assertEqual(len(transitions), 2)
        times = [frame["time"] for change in transitions for frame in change["frames"]]
        self.assertTrue(all(0 <= time <= 2.9 for time in times))
        self.assertEqual(transitions[0]["frames"][0]["time"], 0)
        self.assertEqual(transitions[-1]["frames"][-1]["time"], 2.9)


if __name__ == "__main__":
    unittest.main()
