from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from algovis import NarrationTrack


class NarrationTrackTests(unittest.TestCase):
    def write_cues(self, directory: Path, cues: list[dict[str, object]]) -> Path:
        path = directory / "cues.json"
        path.write_text(
            json.dumps({
                "audio": "audio/lesson.wav",
                "duration": 4.5,
                "cues": cues,
            }),
            encoding="utf-8",
        )
        return path

    def test_relative_audio_path_uses_project_root(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            path = self.write_cues(root, [{"name": "reveal", "time": 1.25}])
            track = NarrationTrack.from_json(path, project_root=root)

            self.assertEqual(track.audio_path, (root / "audio/lesson.wav").resolve())
            self.assertEqual(track.cue_time("reveal"), 1.25)
            self.assertEqual(track.duration, 4.5)

    def test_nonchronological_cues_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            root = Path(temporary)
            path = self.write_cues(root, [
                {"name": "later", "time": 2.0},
                {"name": "earlier", "time": 1.0},
            ])

            with self.assertRaisesRegex(ValueError, "chronological"):
                NarrationTrack.from_json(path, project_root=root)


if __name__ == "__main__":
    unittest.main()
