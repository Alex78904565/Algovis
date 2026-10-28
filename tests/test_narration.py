from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from algovis import NarrationCue, NarrationTrack, SlideScene
from types import SimpleNamespace


class NarrationTrackTests(unittest.TestCase):
    def strict_track(self, time=1):
        track = NarrationTrack("unused.wav", 5,
                               [NarrationCue("answer", 1, "six")],
                               words=[{"word":"six", "start":2, "end":2.3}])
        track.start_time = 0
        scene = SimpleNamespace(renderer=SimpleNamespace(time=time),
                                camera=SimpleNamespace(frame_rate=15))
        scene.wait = lambda seconds: setattr(scene.renderer, "time", scene.renderer.time+seconds)
        return track, scene

    def test_word_timing_uses_recording_not_outdated_numeric_hint(self):
        track, scene = self.strict_track()
        anchor = track.wait_for_word(scene, "answer")
        self.assertEqual(anchor["start"], 2)
        self.assertEqual(scene.renderer.time, 2)

    def test_missed_word_fails_instead_of_silently_playing_late(self):
        track, scene = self.strict_track(2.4)
        with self.assertRaisesRegex(RuntimeError, "shorten or reschedule"):
            track.wait_for_word(scene, "answer")

    def test_phrase_end_waits_until_the_words_are_finished(self):
        track, scene = self.strict_track()
        track.wait_for_word(scene, "answer", edge="end")
        self.assertEqual(scene.renderer.time, 2.3)
        track, scene = self.strict_track(2.5)
        with self.assertRaises(RuntimeError):
            track.wait_for_word(scene, "answer", edge="end")
        with self.assertRaises(ValueError):
            track.wait_for_word(scene, "answer", edge="middle")

    def test_strict_word_event_rejects_missing_or_approximate_alignment(self):
        track, scene = self.strict_track()
        track.words[0]["reviewed_timing"] = "approximate"
        with self.assertRaisesRegex(ValueError, "verified word"):
            track.wait_for_word(scene, "answer")
        track.words = []
        with self.assertRaisesRegex(ValueError, "timestamped"):
            track.wait_for_word(scene, "answer")

    def test_atomic_play_records_content_trigger_and_cannot_leak_to_next_play(self):
        track, state = self.strict_track()
        scene = object.__new__(SlideScene)
        scene.narration, scene.renderer = track, state.renderer
        scene.renderer.camera = state.camera
        scene.wait = state.wait
        captured = []
        scene.play = lambda *animations, **kwargs: captured.append(dict(scene._review_active_cue))
        scene.play_on_cue("answer", object(), run_time=.5, reason="Reveal the stated total")
        self.assertEqual(captured[0]["wordTiming"]["time"], 2)
        self.assertNotIn("wordTiming", scene._review_active_cue)

    def test_atomic_phrase_end_records_the_end_rather_than_the_start(self):
        track, state = self.strict_track()
        scene = object.__new__(SlideScene)
        scene.narration, scene.renderer = track, state.renderer
        scene.renderer.camera = state.camera
        scene.wait = state.wait
        captured = []
        scene.play = lambda *args, **kwargs: captured.append(dict(scene._review_active_cue))
        scene.play_on_cue('answer', object(), run_time=.5, reason='Wait for the phrase to finish', edge='end')
        self.assertEqual(captured[0]['wordTiming']['time'], 2.3)
        self.assertEqual(captured[0]['wordTiming']['edge'], 'end')

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
