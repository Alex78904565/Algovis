"""Keep a fix's review location separate from the original annotation evidence."""

from __future__ import annotations

import math


def normalize_review_at(value, cues, duration, revision):
    """Accept a rendered cue (preferred) or a time in the current video."""
    if not isinstance(value, dict):
        raise ValueError("reviewAt must specify a cue or a time")
    if "cue" in value and "time" in value:
        raise ValueError("Use a review cue with an optional offset, or an exact time")
    if "cue" in value:
        cue = str(value["cue"])
        if cue not in {item["name"] for item in cues}:
            raise ValueError(f"Unknown review cue: {cue!r}")
        offset = float(value.get("offset", 0))
        if not math.isfinite(offset) or not 0 <= offset <= duration:
            raise ValueError("Review offset must be finite and inside the section")
        return {"cue": cue, "offset": offset}
    if "time" not in value:
        raise ValueError("reviewAt needs a cue or a time")
    moment = float(value["time"])
    if not math.isfinite(moment) or not 0 <= moment <= duration:
        raise ValueError("Review time must be finite and inside the section")
    return {"time": moment, "videoRevision": str(revision)}


def review_target(annotation, cues, manifest, duration, revision):
    """Resolve the beginning of the repair, leaving the evidence time untouched.

    Legacy notes use their animation cue rather than a later screenshot time.
    Explicit cues survive retiming; exact numeric anchors belong to one video.
    """
    if annotation.get("status") != "pending_review":
        return None
    by_name = {item["name"]: item for item in cues}
    anchor = annotation.get("reviewAt") or {}
    moment = None
    cue_name = annotation.get("cue")
    source = "animation"
    if "cue" in anchor and anchor["cue"] in by_name:
        cue_name = anchor["cue"]
        source = "fix"
    elif "time" in anchor and anchor.get("videoRevision") == str(revision):
        moment = float(anchor["time"])
        source = "fix"
        prior = [cue for cue in cues if float(cue.get("time", 0)) <= moment]
        cue_name = max(prior, key=lambda cue: float(cue.get("time", 0)))["name"] if prior else None
    if moment is None:
        plays = [float(play["start"]) for play in (manifest or {}).get("plays", [])
                 if play.get("cue") == cue_name and math.isfinite(float(play.get("start", 0)))]
        if plays:
            moment = min(plays)
        elif cue_name in by_name:
            moment = float(by_name[cue_name].get("time", 0))
        else:
            moment = float(annotation.get("timestamp", 0))
            source = "original"
        if source == "fix":
            moment += float(anchor.get("offset", 0))
    if not math.isfinite(moment):
        moment = 0
    # duration itself is past the final playable frame in a video element.
    fps = float((manifest or {}).get("frameRate", 15))
    fps = fps if math.isfinite(fps) and fps > 0 else 15
    moment = min(max(0, moment), max(0, duration - 1 / fps))
    return {"time": moment, "cue": cue_name,
            "phrase": by_name.get(cue_name, {}).get("phrase", ""), "source": source}
