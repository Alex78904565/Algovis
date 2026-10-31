"""Audio-first narration timing for Manim scenes.

The audio master owns time.  Named cues keep scene code readable and insulate
animations from small transcript or take-length changes.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import warnings
import hashlib


@dataclass(frozen=True)
class NarrationCue:
    name: str
    time: float
    phrase: str = ""
    occurrence: int | None = None
    context: str = ''


@dataclass(frozen=True)
class WordEvent:
    """Resolved narration input, passed unchanged through the layout tree."""
    cue: str
    phrase: str
    start: float
    end: float
    edge: str
    transcript_fingerprint: str

    @property
    def time(self):return self.start if self.edge=='start' else self.end


def file_fingerprint(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


class NarrationTrack:
    def __init__(self, audio_path, duration, cues, *, words=None):
        self.audio_path = Path(audio_path).resolve()
        self.duration = float(duration)
        self.cues = {cue.name: cue for cue in cues}
        self.start_time = None
        self.late_arrivals = []
        self.words = list(words or [])
        self.alignment_provenance = None
        self._alignment_path = None

    @classmethod
    def from_json(cls, cue_path, project_root=None):
        cue_path = Path(cue_path).resolve()
        data = json.loads(cue_path.read_text(encoding="utf-8"))
        root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        audio = Path(data["audio"])
        if not audio.is_absolute():
            audio = root / audio
        cues = [
            NarrationCue(item["name"], float(item["time"]), item.get("phrase", ""),
                         item.get('occurrence'),item.get('context',''))
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
        track=cls(audio, data["duration"], cues, words=words)
        provenance=data.get('alignmentProvenance')
        if provenance is not None:
            if not words:raise ValueError('Alignment provenance requires timestamped transcriptWords')
            actual={'audioSha256':file_fingerprint(audio),'transcriptSha256':file_fingerprint(transcript)}
            if any(provenance.get(key)!=value for key,value in actual.items()):
                raise ValueError('Recording or transcript changed after alignment; realign and rebind the cues before rendering')
            track.alignment_provenance=actual
            track._alignment_path=transcript
        return track

    def validate_provenance(self):
        """Also catch a file changed while a long section was rendering."""
        if self.alignment_provenance is not None:
            actual={'audioSha256':file_fingerprint(self.audio_path),
                    'transcriptSha256':file_fingerprint(self._alignment_path)}
            if actual!=self.alignment_provenance:
                raise ValueError('Recording or transcript changed during rendering; keep the previous preview and realign')

    def word_event(self,name,*,edge='start'):
        if edge not in ('start','end'):raise ValueError('Word timing edge must be start or end')
        anchor=self.word_anchor(name)
        fingerprint=hashlib.sha256(json.dumps(self.words,sort_keys=True).encode()).hexdigest()
        return WordEvent(name,self.cues[name].phrase,float(anchor['start']),float(anchor['end']),edge,fingerprint)

    def word_anchor(self, name):
        """Resolve a strict cue against spoken words; its time only disambiguates."""
        from .review.audit import phrase_matches
        self.cue_time(name)  # Preserve the useful unknown-cue diagnostic.
        cue = self.cues[name]
        if not cue.phrase.strip() or not self.words:
            raise ValueError(f"Word cue {name!r} requires a phrase and timestamped transcriptWords")
        matches=phrase_matches(cue.phrase,self.words)
        if cue.context:
            contexts=phrase_matches(cue.context,self.words)
            matches=[match for match in matches if any(context['start']<=match['start']
                       and match['end']<=context['end'] for context in contexts)]
        if cue.occurrence is not None:
            if isinstance(cue.occurrence,bool) or not isinstance(cue.occurrence,int) or cue.occurrence<1:
                raise ValueError('A word occurrence must be a positive one-based integer')
            anchor=matches[cue.occurrence-1] if cue.occurrence<=len(matches) else None
        else:
            ordered=sorted(matches,key=lambda match:abs(match['start']-cue.time))
            if len(ordered)>1 and abs(abs(ordered[0]['start']-cue.time)-abs(ordered[1]['start']-cue.time))<1e-8:
                raise ValueError(f'Word cue {name!r} is ambiguous; specify context or occurrence')
            anchor=ordered[0] if ordered else None
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
        self.validate_provenance()
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
