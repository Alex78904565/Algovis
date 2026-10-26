from __future__ import annotations

import ast
import unittest

from algovis.qa import SectionAudit, audit_source_method, phrase_anchor_offset


class AnimationAuditTests(unittest.TestCase):
    def test_phrase_existence_does_not_hide_a_premature_trigger(self):
        words = [("now", 0), ("the", 0.2), ("base", 3), ("case", 3.3)]
        self.assertEqual(phrase_anchor_offset(words, "base case", 0), 3)
        self.assertEqual(phrase_anchor_offset(words, "base case", 3), 0)

    def test_repeated_phrase_uses_the_nearest_spoken_occurrence(self):
        words = [("answer", 2), ("answer", 40)]
        self.assertAlmostEqual(phrase_anchor_offset(words, "answer", 39.9), .1)
        self.assertIsNone(phrase_anchor_offset(words, "another phrase", 0))

    def test_pending_notes_block_section_gate(self) -> None:
        report = SectionAudit(
            "sample", "Sample", annotation_counts={"pending": 1},
        )
        self.assertEqual(report.status, "blocked")

    def test_pending_review_waits_for_viewer_without_blocking_work_queue(self) -> None:
        report = SectionAudit(
            "sample", "Sample", annotation_counts={"pending_review": 1},
        )
        self.assertEqual(report.status, "needs_review")

    def test_source_audit_ignores_legacy_code_after_top_level_return(self) -> None:
        tree = ast.parse("""
def scene(self):
    self.wait_for_cue('start')
    self.play(Write(title))
    return
    self.wait_for_cue('missing')
    self.wait(10)
""")
        issues = audit_source_method(tree, "scene", {"start"}, "scene.py")
        self.assertEqual(issues, [])

    def test_source_audit_flags_large_offsets_and_hard_waits(self) -> None:
        tree = ast.parse("""
def scene(self):
    self.wait_for_cue('start', offset=1.25)
    self.wait(0.5)
""")
        issues = audit_source_method(tree, "scene", {"start"}, "scene.py")
        messages = [issue.message for issue in issues]
        self.assertTrue(any("Hard-coded wait" in message for message in messages))
        self.assertTrue(any("word-level cue" in message for message in messages))

    def test_source_findings_keep_their_cue_and_effective_time(self) -> None:
        tree = ast.parse("""
def scene(self):
    self.wait_for_cue('explain', offset=1.25)
    self.play(Indicate(value, color=self.theme.success))
""")
        issues = audit_source_method(
            tree, "scene", {"explain"}, "scene.py", {"explain": 10.0},
        )
        self.assertEqual(len(issues), 2)
        self.assertTrue(all(issue.cue == "explain" for issue in issues))
        self.assertTrue(all(issue.time == 11.25 for issue in issues))


if __name__ == "__main__":
    unittest.main()
