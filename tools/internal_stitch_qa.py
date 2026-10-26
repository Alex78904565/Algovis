"""Audit silence inside selected narration takes for hidden edit seams.

The ordinary assembly QA checks the joins between numbered clips.  This pass
looks *inside* each selected clip on the current mastered timeline, where a
speaker may already have stitched multiple recordings together before saving
the WAV.  It reports quiet clicks, brief thuds, noise-floor changes, and large
speech-level changes across internal pauses without modifying raw recordings.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.signal import medfilt

try:
    from .audio_pipeline import AUDIO_ROOT, ROOT, read_wav
except ImportError:
    from audio_pipeline import AUDIO_ROOT, ROOT, read_wav


ASSEMBLY_DIR = AUDIO_ROOT / "alignment"


def transcript_intervals(document: dict) -> list[tuple[float, float]]:
    """Protect words in either the flat or Whisper segment-based format."""
    words = document.get("words") or [
        word for segment in document.get("segments", [])
        for word in segment.get("words", [])
    ]
    return sorted((float(word["start"]), float(word["end"])) for word in words)


def db(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def frame_rms(samples: np.ndarray, frame: int) -> np.ndarray:
    count = math.ceil(len(samples) / frame)
    padded = np.pad(samples.astype(np.float64), (0, count * frame - len(samples)))
    return np.sqrt(np.mean(padded.reshape(count, frame) ** 2, axis=1))


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.pad(mask.astype(np.int8), (1, 1))
    changes = np.flatnonzero(np.diff(padded))
    return [(int(start), int(end)) for start, end in changes.reshape(-1, 2)]


def nearest_active_level(
    levels_db: np.ndarray,
    quiet: np.ndarray,
    boundary: int,
    direction: int,
    count: int = 100,
) -> float | None:
    if direction < 0:
        indices = np.flatnonzero(~quiet[:boundary])[-count:]
    else:
        indices = np.flatnonzero(~quiet[boundary:])[:count] + boundary
    if len(indices) < 3:
        return None
    return float(np.median(levels_db[indices]))


def inspect_chunk(
    samples: np.ndarray,
    rate: int,
    section: str,
    chunk: dict[str, object],
    speech_intervals: list[tuple[float, float]],
) -> list[dict[str, object]]:
    start = round(float(chunk["master_start"]) * rate)
    end = round(float(chunk["master_end"]) * rate)
    audio = samples[start:end]
    if len(audio) < rate:
        return []

    frame = max(1, round(rate * 0.01))
    rms = frame_rms(audio, frame)
    levels_db = 20.0 * np.log10(np.maximum(rms, 1e-12))
    quiet = levels_db < -42.0
    quiet_runs = [
        (left, right)
        for left, right in runs(quiet)
        if (right - left) >= 12 and left >= 8 and right <= len(quiet) - 8
    ]

    events: list[dict[str, object]] = []
    for left, right in quiet_runs:
        pause_start = left * frame / rate
        pause_end = min(len(audio), right * frame) / rate
        before = nearest_active_level(levels_db, quiet, left, -1)
        after = nearest_active_level(levels_db, quiet, right, 1)
        level_delta = abs(after - before) if before is not None and after is not None else 0.0

        quarter = max(1, (right - left) // 4)
        head_floor = max(-100.0, float(np.median(levels_db[left:left + quarter])))
        tail_floor = max(-100.0, float(np.median(levels_db[right - quarter:right])))
        floor_delta = abs(tail_floor - head_floor)

        edge = max(1, round(rate * 0.004))
        sample_left = max(1, left * frame - edge)
        sample_right = min(len(audio) - 1, right * frame + edge)
        edge_jump = float(np.max(np.abs(np.diff(audio[sample_left:sample_right]))))

        reasons: list[str] = []
        if level_delta >= 5.0:
            reasons.append("speech_level_change")
        if floor_delta >= 15.0 and max(head_floor, tail_floor) > -65.0:
            reasons.append("noise_floor_change")
        if edge_jump >= 0.06:
            reasons.append("boundary_click_candidate")
        if reasons:
            events.append(
                {
                    "section": section,
                    "chunk": int(chunk["chunk"]),
                    "source": str(chunk["source"]),
                    "kind": "internal_pause",
                    "clip_time": round(pause_start, 4),
                    "master_time": round(float(chunk["master_start"]) + pause_start, 4),
                    "pause_seconds": round(pause_end - pause_start, 4),
                    "speech_before_dbfs": round(before, 2) if before is not None else None,
                    "speech_after_dbfs": round(after, 2) if after is not None else None,
                    "speech_level_change_db": round(level_delta, 2),
                    "noise_floor_change_db": round(floor_delta, 2),
                    "edge_jump": round(edge_jump, 5),
                    "reasons": reasons,
                }
            )

    # Find isolated impulses only when their surrounding 10 ms is quiet.  This
    # deliberately mirrors the conservative de-clicker used by the assembler.
    if len(audio) > 32:
        baseline = medfilt(audio, kernel_size=7).astype(np.float32)
        residual = np.abs(audio - baseline)
        envelope_frame = max(1, round(rate * 0.01))
        envelope = np.sqrt(
            np.convolve(
                audio.astype(np.float64) ** 2,
                np.ones(envelope_frame) / envelope_frame,
                mode="same",
            )
        )
        candidates = np.flatnonzero((residual > 0.035) & (envelope < 0.008))
        if len(candidates):
            groups = np.split(candidates, np.flatnonzero(np.diff(candidates) > rate * 0.02) + 1)
            for group in groups:
                location = int(group[np.argmax(residual[group])])
                if location < rate * 0.08 or location > len(audio) - rate * 0.08:
                    continue
                master_time = float(chunk["master_start"]) + location / rate
                if any(
                    word_start - 0.08 <= master_time <= word_end + 0.08
                    for word_start, word_end in speech_intervals
                ):
                    continue
                events.append(
                    {
                        "section": section,
                        "chunk": int(chunk["chunk"]),
                        "source": str(chunk["source"]),
                        "kind": "quiet_impulse",
                        "clip_time": round(location / rate, 4),
                        "master_time": round(master_time, 4),
                        "residual": round(float(residual[location]), 5),
                        "surrounding_rms_dbfs": round(db(float(envelope[location])), 2),
                        "reasons": ["quiet_click_or_edit_impulse"],
                    }
                )

    # A short active island bracketed by silence is more likely to be a thud,
    # chair movement, or handling noise than speech.  It remains a review item,
    # never an automatic deletion.
    active_runs = runs(~quiet)
    for left, right in active_runs:
        duration = (right - left) * frame / rate
        if not (0.02 <= duration <= 0.18 and left >= 12 and right <= len(quiet) - 12):
            continue
        if not (np.all(quiet[left - 12:left]) and np.all(quiet[right:right + 12])):
            continue
        island = audio[left * frame:min(len(audio), right * frame)]
        if not len(island):
            continue
        peak = float(np.max(np.abs(island)))
        if peak < 0.018:
            continue
        island_start = float(chunk["master_start"]) + left * frame / rate
        island_end = float(chunk["master_start"]) + right * frame / rate
        if any(
            word_end >= island_start - 0.1 and word_start <= island_end + 0.1
            for word_start, word_end in speech_intervals
        ):
            continue
        events.append(
            {
                "section": section,
                "chunk": int(chunk["chunk"]),
                "source": str(chunk["source"]),
                "kind": "quiet_island",
                "clip_time": round(left * frame / rate, 4),
                "master_time": round(float(chunk["master_start"]) + left * frame / rate, 4),
                "duration": round(duration, 4),
                "peak_dbfs": round(db(peak), 2),
                "reasons": ["possible_thud_or_handling_noise"],
            }
        )
    return events


def inspect_source_zero_seams(
    section: str,
    chunk: dict[str, object],
) -> list[dict[str, object]]:
    """Find exact digital-silence runs inserted inside a selected source take."""
    source = ROOT / str(chunk["source"])
    audio = read_wav(source)
    trim_start = float(chunk["trim_start"])
    trim_end = float(chunk["trim_end"])
    left_limit = round(trim_start * audio.rate)
    right_limit = min(len(audio.samples), round(trim_end * audio.rate))
    selected = audio.samples[left_limit:right_limit]
    if len(selected) < audio.rate:
        return []
    zero = np.abs(selected) <= 1e-8
    events: list[dict[str, object]] = []
    for left, right in runs(zero):
        duration = (right - left) / audio.rate
        if duration < 0.008 or left < audio.rate * 0.08 or right > len(selected) - audio.rate * 0.08:
            continue
        jump_in = abs(float(selected[left - 1])) if left else 0.0
        jump_out = abs(float(selected[right])) if right < len(selected) else 0.0
        source_time = trim_start + left / audio.rate
        span = max(1e-9, trim_end - trim_start)
        fraction = (source_time - trim_start) / span
        master_time = float(chunk["master_start"]) + fraction * (
            float(chunk["master_end"]) - float(chunk["master_start"])
        )
        events.append(
            {
                "section": section,
                "chunk": int(chunk["chunk"]),
                "source": str(chunk["source"]),
                "kind": "digital_silence_seam",
                "source_time": round(source_time, 4),
                "master_time": round(master_time, 4),
                "duration": round(duration, 4),
                "jump_in": round(jump_in, 6),
                "jump_out": round(jump_out, 6),
                "reasons": ["exact_zero_gap_inside_selected_take"],
            }
        )
    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audio-stage", choices=("processed", "master"), default="processed",
                        help="Inspect the published dialogue by default, or the assembly master")
    args = parser.parse_args()

    events: list[dict[str, object]] = []
    sections: list[dict[str, object]] = []
    for assembly_path in sorted(ASSEMBLY_DIR.glob("*.assembly.json")):
        assembly = json.loads(assembly_path.read_text(encoding="utf-8"))
        master = (AUDIO_ROOT / "processed" / f"{assembly['section']}_dialogue.wav"
                  if args.audio_stage == "processed" else ROOT / str(assembly["audio"]))
        audio = read_wav(master)
        words_path = ASSEMBLY_DIR / f"{assembly['section']}.words.json"
        words_document = json.loads(words_path.read_text(encoding="utf-8"))
        speech_intervals = transcript_intervals(words_document)
        section_events: list[dict[str, object]] = []
        for chunk in assembly["chunks"]:
            section_events.extend(
                inspect_chunk(
                    audio.samples,
                    audio.rate,
                    str(assembly["section"]),
                    chunk,
                    speech_intervals,
                )
            )
            section_events.extend(inspect_source_zero_seams(str(assembly["section"]), chunk))
        events.extend(section_events)
        sections.append(
            {
                "section": assembly["section"],
                "chunks": len(assembly["chunks"]),
                "events": len(section_events),
            }
        )

    kind_order = {
        "digital_silence_seam": 0,
        "quiet_impulse": 1,
        "quiet_island": 2,
        "internal_pause": 3,
    }
    events.sort(key=lambda item: (kind_order.get(str(item["kind"]), 9), item["section"], item["master_time"]))
    report = {
        "scope": "Every selected chunk on the current mastered timeline; raw recordings unchanged.",
        "sections": sections,
        "event_count": len(events),
        "events": events,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    print(f"{sum(item['chunks'] for item in sections)} selected clips; {len(events)} review events")
    for item in events[:80]:
        print(
            f"{item['section']} chunk {item['chunk']:>3} "
            f"at {item['master_time']:>8.3f}s  {item['kind']}  "
            f"{','.join(item['reasons'])}"
        )


if __name__ == "__main__":
    main()
