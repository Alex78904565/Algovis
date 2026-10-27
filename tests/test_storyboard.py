import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from algovis.storyboard import Storyboard, StoryboardSyntaxError, parse_storyboard


EXAMPLE = '''
storyboard 2
section example "Example section"
audio "voice.wav"

animation comparison "Compare retained and repeated work":
  goal "Keep the semantic distinction stable while the narration compares both calls."
  component start say "begin":
    show title role=neutral style=fade
  component compare +0.2 say "same input":
    together:
      focus kept role=retained style=tint
      together:
        focus duplicate role=repeated style=tint
        caption duplicate "requested again"
    merge duplicate -> kept order=bottom_up
'''


class StoryboardTests(unittest.TestCase):
    def test_round_trip(self):
        board = parse_storyboard(EXAMPLE)
        reparsed = parse_storyboard(board.to_source())
        self.assertEqual(board.section, reparsed.section)
        self.assertEqual(board.beats, reparsed.beats)

    def test_validates_against_cues(self):
        scratch = Path.cwd() / ".qa" / "tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=scratch) as directory:
            cue_path = Path(directory) / "cues.json"
            cue_path.write_text(json.dumps({"cues": [
                {"name": "start", "time": 0.0},
                {"name": "compare", "time": 1.0},
            ]}), encoding="utf-8")
            parse_storyboard(EXAMPLE).validate(
                cue_path, require_all_cues=True,
            )

    def test_rejects_raw_color_role(self):
        bad = EXAMPLE.replace("role=retained", "role=green")
        with self.assertRaises(StoryboardSyntaxError):
            parse_storyboard(bad).validate()

    def test_reports_visual_density(self):
        board = parse_storyboard(EXAMPLE)
        warnings = board.density_warnings(max_changes_per_phrase=1)
        self.assertTrue(any("visual changes" in warning for warning in warnings))

    def test_cleanup_and_a_coordinated_build_are_not_many_new_ideas(self):
        board = parse_storyboard('''
storyboard 2
section example "Example"
audio "voice.wav"
animation notation "Change notation":
  component start say "brackets":
    together:
      hide old_heading
      hide old_left
      hide old_right
    together:
      show left_bracket
      show right_bracket
      show new_heading
''')
        self.assertEqual(board.density_warnings(), [])

    def test_independent_additions_still_raise_a_density_warning(self):
        board = parse_storyboard(EXAMPLE.replace('    merge duplicate -> kept order=bottom_up',
            '\n'.join('    show item'+str(i) for i in range(5))))
        self.assertTrue(any('visual changes' in w for w in board.density_warnings()))


if __name__ == "__main__":
    unittest.main()
