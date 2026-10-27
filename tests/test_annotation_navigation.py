from copy import deepcopy
import unittest

from algovis.review.annotation_navigation import normalize_review_at, review_target


class AnnotationNavigationTests(unittest.TestCase):
    cues = [{"name": "begin", "time": 0, "phrase": "our example"},
            {"name": "value", "time": 4, "phrase": "the value"}]
    manifest = {"frameRate": 15, "plays": [
        {"cue": "begin", "start": 0, "end": .6},
        {"cue": "value", "start": 3.98, "end": 4.4},
        {"cue": "value", "start": 4.8, "end": 5.2},
    ]}

    def note(self, **extra):
        return {"status": "pending_review", "cue": "value", "timestamp": 5.5, **extra}

    def resolve(self, note, manifest=None, revision="one"):
        return review_target(note, self.cues, manifest or self.manifest, 8, revision)

    def test_legacy_ready_note_starts_at_rendered_animation_not_screenshot(self):
        self.assertEqual(self.resolve(self.note())["time"], 3.98)

    def test_explicit_earlier_fix_preserves_original_evidence(self):
        note = self.note(reviewAt={"cue": "begin"})
        before = deepcopy(note)
        result = self.resolve(note)
        self.assertEqual((result["time"], result["cue"], result["source"]), (0, "begin", "fix"))
        self.assertEqual(note, before)

    def test_cue_anchor_follows_retimed_render(self):
        note = self.note(reviewAt={"cue": "value", "offset": .2})
        changed = {"plays": [{"cue": "value", "start": 5, "end": 6}]}
        self.assertAlmostEqual(self.resolve(note, changed)["time"], 5.2)

    def test_exact_time_zero_and_stale_revision(self):
        anchor = normalize_review_at({"time": 0}, self.cues, 8, "one")
        note = self.note(reviewAt=anchor)
        self.assertEqual(self.resolve(note)["time"], 0)
        self.assertEqual(self.resolve(note, revision="two")["time"], 3.98)

    def test_non_ready_notes_keep_original_navigation(self):
        for status in ("draft", "pending", "resolved"):
            self.assertIsNone(self.resolve(self.note(status=status, reviewAt={"cue": "begin"})))

    def test_missing_manifest_uses_current_cue_time(self):
        result = review_target(self.note(), self.cues, None, 8, "one")
        self.assertEqual(result["time"], 4)

    def test_review_target_stays_inside_playable_video(self):
        result = self.resolve(self.note(reviewAt={"cue": "value", "offset": 8}))
        self.assertLess(result["time"], 8)

    def test_invalid_locations_are_rejected(self):
        for anchor in ({"cue": "missing"}, {"time": -1}, {"time": float("nan")},
                       {"time": 9}, {"cue": "begin", "offset": -1}, {},
                       {"cue": "begin", "time": 1}):
            with self.assertRaises(ValueError):
                normalize_review_at(anchor, self.cues, 8, "one")
