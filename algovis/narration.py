"""Audio-first narration timing for Manim scenes.

The audio master owns time.  Named cues keep scene code readable and insulate
animations from small transcript or take-length changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import warnings


@dataclass(frozen=True)
class NarrationCue:
    name: str
    time: float
    phrase: str = ""


class NarrationTrack:
    def __init__(self, audio_path, duration, cues, *, words=None):
        self.audio_path = Path(audio_path).resolve()
        self.duration = float(duration)
        self.cues = {cue.name: cue for cue in cues}
        self.start_time = None
        self.late_arrivals = []
        self.words = list(words or [])

    @classmethod
    def from_json(cls, cue_path, project_root=None):
        cue_path = Path(cue_path).resolve()
        data = json.loads(cue_path.read_text(encoding="utf-8"))
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        audio = Path(data["audio"])
        if not audio.is_absolute():
            audio = root / audio
        cues = [
            NarrationCue(item["name"], float(item["time"]), item.get("phrase", ""))
            for item in data["cues"]
        ]
        times = [cue.time for cue in cues]
        if times != sorted(times):
            raise ValueError(f"Narration cues must be chronological: {cue_path}")
        words = None
        if data.get("transcriptWords"):
            from .review.audit import timed_words
            transcript = Path(data["transcriptWords"])
            if not transcript.is_absolute():
                transcript = root / transcript
            words = timed_words(json.loads(transcript.read_text(encoding="utf-8")))
        return cls(audio, data["duration"], cues, words=words)

    def word_anchor(self, name):
        """Resolve a strict cue against spoken words; its time only disambiguates."""
        from .review.audit import phrase_anchor
        self.cue_time(name)  # Preserve the useful unknown-cue diagnostic.
        cue = self.cues[name]
        if not cue.phrase.strip() or not self.words:
            raise ValueError(f"Word cue {name!r} requires a phrase and timestamped transcriptWords")
        anchor = phrase_anchor(cue.phrase, self.words, cue.time)
        if anchor is None or anchor["approximate"]:
            raise ValueError(f"Word cue {name!r} has no verified word alignment: {cue.phrase!r}")
        return anchor

    def wait_for_word(self, scene, name, *, edge="start"):
        """Fail on a missed word instead of silently playing an animation late."""
        anchor = self.word_anchor(name)
        if edge not in ('start','end'):
            raise ValueError('Word timing edge must be start or end')
        target = anchor[edge]
        fps = float(scene.camera.frame_rate)
        tolerance = 1 / fps + 0.015
        remaining = float(target) - self.elapsed(scene)
        if remaining < -tolerance:
            raise RuntimeError(
                f"Word cue {name!r} missed by {-remaining:.3f}s; "
                "shorten or reschedule preceding animations"
            )
        if remaining > 0:
            scene.wait(remaining)
        if abs(self.elapsed(scene) - target) > tolerance:
            raise RuntimeError(f"Word cue {name!r} did not land within one video frame")
        return anchor

    def start(self, scene, gain=None):
        if not self.audio_path.exists():
            raise FileNotFoundError(self.audio_path)
        self.start_time = float(scene.renderer.time)
        kwargs = {} if gain is None else {"gain": gain}
        scene.add_sound(str(self.audio_path), **kwargs)
        return self

    def elapsed(self, scene):
        if self.start_time is None:
            raise RuntimeError("Call NarrationTrack.start(scene) before using cues.")
        return float(scene.renderer.time) - self.start_time

    def cue_time(self, name):
        try:
            return self.cues[name].time
        except KeyError as exc:
            known = ", ".join(self.cues)
            raise KeyError(f"Unknown narration cue {name!r}. Known cues: {known}") from exc

    def wait_for(self, scene, name, offset=0.0):
        remaining = self.cue_time(name) + float(offset) - self.elapsed(scene)
        if remaining > 0:
            scene.wait(remaining)
        elif remaining < -0.05:
            late_by = -remaining
            self.late_arrivals.append((name, late_by))
            warnings.warn(
                f"Narration cue {name!r} was reached {late_by:.3f}s late.",
                RuntimeWarning,
                stacklevel=2,
            )
        return max(0.0, remaining)

    def play_until(self, scene, name, *animations, minimum=0.05, offset=0.0):
        """Play animations so they finish at a named cue."""
        remaining = self.cue_time(name) + float(offset) - self.elapsed(scene)
        if remaining < -0.05:
            late_by = -remaining
            self.late_arrivals.append((name, late_by))
            warnings.warn(
                f"Narration cue {name!r} was reached {late_by:.3f}s late.",
                RuntimeWarning,
                stacklevel=2,
            )
        scene.play(*animations, run_time=max(float(minimum), remaining))
        return remaining

    def finish(self, scene, tail=0.0):
        remaining = self.duration + float(tail) - self.elapsed(scene)
        if remaining > 0:
            scene.wait(remaining)
        if self.late_arrivals:
            details = ", ".join(
                f"{name}={late_by:.3f}s"
                for name, late_by in self.late_arrivals
            )
            warnings.warn(
                f"Narration late-arrival summary: {details}",
                RuntimeWarning,
                stacklevel=2,
            )
        return max(0.0, remaining)
