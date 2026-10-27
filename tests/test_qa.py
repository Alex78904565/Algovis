from __future__ import annotations

import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from algovis.qa import SectionAudit, audit_source_method, phrase_anchor_offset, audit_project


class AnimationAuditTests(unittest.TestCase):
    def test_structural_section_bounds_are_not_missing_spoken_triggers(self):
        scratch=Path.cwd()/'.qa/tests';scratch.mkdir(parents=True,exist_ok=True)
        with TemporaryDirectory(dir=scratch)as tmp:
            root=Path(tmp)
            for name in ['video.mp4','voice.wav','music.ogg']:(root/name).write_bytes(b'asset')
            (root/'cues.json').write_text(json.dumps({'duration':3,'cues':[
                {'name':'section_start','time':0,'phrase':'Structural start'},
                {'name':'content','time':1,'phrase':'Missing spoken phrase'},
                {'name':'section_end','time':3,'phrase':'Structural end'}]}))
            (root/'words.json').write_text(json.dumps({'text':'actual narration'}))
            (root/'scene.py').write_text('def scene(self): pass')
            (root/'example.story').write_text('storyboard 2\nsection sample "Sample"\naudio "voice.wav"\n'
                'animation setup "Setup":\n  goal "Hold the setup"\n'+''.join(f'  component {cue} say "context":\n    hold\n'for cue in ['section_start','content','section_end']))
            (root/'catalog.json').write_text(json.dumps({'sections':[{'id':'sample','video':'video.mp4',
                'audio':'voice.wav','music':'music.ogg','cues':'cues.json','transcriptWords':'words.json'}]}))
            report=audit_project(root,root/'catalog.json',storyboard_by_section={'sample':root/'example.story'},
                method_by_section={'sample':'scene'},source_path=root/'scene.py')
            issues=report['sections']['sample']['issues']
            self.assertEqual([i['cue']for i in issues],['content'],issues)

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
    self.play(Write(title))
""")
        issues = audit_source_method(tree, "scene", {"start"}, "scene.py")
        messages = [issue.message for issue in issues]
        self.assertTrue(any("Hard-coded wait" in message for message in messages))
        self.assertTrue(any("word-level cue" in message for message in messages))

    def test_still_hold_before_another_named_cue_is_not_a_timing_bypass(self):
        tree = ast.parse("""
def scene(self):
    self.wait_for_cue('start')
    self.wait(0.5)
    self.wait_for_cue('next')
    self.play(Write(title))
""")
        issues = audit_source_method(tree, "scene", {"start", "next"}, "scene.py")
        self.assertFalse(any('Hard-coded wait' in issue.message for issue in issues))

    def test_atomic_word_timing_is_recognized_by_the_static_source_check(self):
        tree=ast.parse('''
def scene(self):
    self.wait(0.5)
    self.play_on_cue('value', Write(value), run_time=0.5, reason='Name it')
''')
        self.assertEqual(audit_source_method(tree,'scene',{'value'},'scene.py',{'value':2}),[])
        issues=audit_source_method(tree,'scene',set(),'scene.py')
        self.assertTrue(any("unknown cue"in i.message for i in issues))

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
