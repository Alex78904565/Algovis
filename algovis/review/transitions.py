"""Index real Manim play intervals for frame-by-frame review."""

from __future__ import annotations

import math


def build_transition_index(manifest, cues, duration, *, frame_rate=15.0):
    """Group simultaneous leaf animations and sample real video frames.

    Before is one frame before the play starts, middle is halfway through the
    combined play, and after is the first frame following its completion. All
    samples are clamped to the playable section, including a truncated outro.
    """
    if not manifest or duration <= 0:
        return []
    fps = float(manifest.get("frameRate", frame_rate))
    if not math.isfinite(fps) or fps <= 0:
        fps = frame_rate
    last_frame = max(0, math.floor(duration * fps) - 1)
    groups = {}
    for animation in manifest.get("animations", []):
        start = float(animation.get("start", 0.0))
        end = float(animation.get("end", start))
        if not math.isfinite(start) or not math.isfinite(end) or end <= start or start >= duration:
            continue
        play = int(animation.get("play", 0))
        group = groups.setdefault(play, {
            "id": f"play-{play + 1:04d}",
            "play": play,
            "start": max(0.0, start),
            "end": min(duration, end),
            "labels": [],
            "animationIds": [],
        })
        group["start"] = min(group["start"], max(0.0, start))
        group["end"] = max(group["end"], min(duration, end))
        label = str(animation.get("label") or animation.get("kind") or "Animation")
        if label not in group["labels"]:
            group["labels"].append(label)
        group["animationIds"].append(animation.get("id"))

    ordered_cues = sorted(cues, key=lambda cue: float(cue.get("time", 0.0)))
    result = sorted(groups.values(), key=lambda group: (group["start"], group["play"]))
    for group in result:
        # A low-resolution render may begin one video frame before its cue
        # because Manim quantizes waits. Allow that single-frame tolerance.
        prior = [cue for cue in ordered_cues
                 if float(cue.get("time", 0.0)) <= group["start"] + 1 / fps]
        cue = prior[-1] if prior else {}
        group["cue"] = cue.get("name")
        group["phrase"] = cue.get("phrase", "")
        labels = group.pop("labels")
        group["label"] = " · ".join(labels[:3])
        if len(labels) > 3:
            group["label"] += f" (+{len(labels) - 3} more)"
        frames = (
            ("before", math.floor(group["start"] * fps + 1e-6) - 1),
            ("middle", math.floor((group["start"] + group["end"]) / 2 * fps)),
            ("after", math.ceil(group["end"] * fps - 1e-6)),
        )
        group["frames"] = [
            {"position": position, "time": max(0, min(last_frame, frame)) / fps}
            for position, frame in frames
        ]
    return result
