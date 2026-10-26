"""Measure narration consistency without modifying source or mastered audio.

The report is chunk-aware: it uses the assembly manifests to compare active
speech levels with the surrounding takes, flag clipping, and find unusually
large sample discontinuities at edit points.  It is intentionally diagnostic;
approved corrections remain explicit in each section's edits JSON.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT = ROOT / "assets" / "audio" / "dp" / "alignment"


def dbfs(value: float) -> float:
    return 20.0 * math.log10(max(value, 1e-12))


def mono_float(path: Path) -> tuple[int, np.ndarray]:
    rate, samples = wavfile.read(path)
    if samples.ndim > 1:
        samples = samples.astype(np.float64).mean(axis=1)
    if np.issubdtype(samples.dtype, np.integer):
        scale = max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max)
        samples = samples.astype(np.float64) / float(scale)
    else:
        samples = samples.astype(np.float64)
    return int(rate), samples


def active_level(samples: np.ndarray, rate: int) -> tuple[float, float, float]:
    """Return median active-frame RMS, peak, and active-frame percentage."""
    if len(samples) == 0:
        return -120.0, -120.0, 0.0
    frame = max(1, round(rate * 0.04))
    usable = len(samples) // frame * frame
    if usable == 0:
        rms = float(np.sqrt(np.mean(samples * samples)))
        return dbfs(rms), dbfs(float(np.max(np.abs(samples)))), 100.0
    framed = samples[:usable].reshape(-1, frame)
    frame_rms = np.sqrt(np.mean(framed * framed, axis=1))
    active = frame_rms[frame_rms >= 10 ** (-42.0 / 20.0)]
    if len(active) == 0:
        active = frame_rms[frame_rms > 0]
    level = float(np.median(active)) if len(active) else 0.0
    active_pct = 100.0 * len(active) / max(1, len(frame_rms))
    return dbfs(level), dbfs(float(np.max(np.abs(samples)))), active_pct


def boundary_jump(samples: np.ndarray, index: int, rate: int) -> float:
    radius = max(2, round(rate * 0.004))
    lo = max(1, index - radius)
    hi = min(len(samples), index + radius)
    if hi <= lo:
        return -120.0
    return dbfs(float(np.max(np.abs(np.diff(samples[lo:hi])))))


def analyze(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    audio_path = ROOT / str(manifest["audio"])
    rate, samples = mono_float(audio_path)
    words_path = manifest_path.with_name(
        manifest_path.name.replace(".assembly.json", ".words.json")
    )
    timed_words: list[dict[str, object]] = []
    if words_path.exists():
        words_data = json.loads(words_path.read_text(encoding="utf-8"))
        for segment in words_data.get("segments", []):
            timed_words.extend(segment.get("words", []))
    chunks: list[dict[str, object]] = []
    for entry in manifest["chunks"]:
        start = int(round(float(entry["master_start"]) * rate))
        end = int(round(float(entry["master_end"]) * rate))
        level, peak, active_pct = active_level(samples[start:end], rate)
        chunks.append(
            {
                "chunk": int(entry["chunk"]),
                "start": float(entry["master_start"]),
                "end": float(entry["master_end"]),
                "active_dbfs": round(level, 2),
                "peak_dbfs": round(peak, 2),
                "active_percent": round(active_pct, 1),
                "boundary_jump_dbfs": round(boundary_jump(samples, start, rate), 2),
                "text": "".join(
                    str(word.get("word", ""))
                    for word in timed_words
                    if float(word.get("end", 0.0)) > float(entry["master_start"])
                    and float(word.get("start", 0.0)) < float(entry["master_end"])
                ).strip(),
            }
        )

    levels = np.array([float(chunk["active_dbfs"]) for chunk in chunks])
    section_median = float(np.median(levels)) if len(levels) else -120.0
    for index, chunk in enumerate(chunks):
        lo = max(0, index - 2)
        hi = min(len(chunks), index + 3)
        neighborhood = np.delete(levels[lo:hi], index - lo)
        local_median = float(np.median(neighborhood)) if len(neighborhood) else section_median
        chunk["vs_section_db"] = round(float(chunk["active_dbfs"]) - section_median, 2)
        chunk["vs_neighbors_db"] = round(float(chunk["active_dbfs"]) - local_median, 2)
        chunk["flag"] = (
            abs(float(chunk["vs_neighbors_db"])) >= 2.4
            or float(chunk["peak_dbfs"]) >= -0.5
            or float(chunk["boundary_jump_dbfs"]) >= -8.0
        )

    return {
        "section": manifest["section"],
        "audio": manifest["audio"],
        "duration": manifest["duration"],
        "active_median_dbfs": round(section_median, 2),
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", help="Analyze one section name instead of all sections")
    parser.add_argument("--json", type=Path, help="Write the full machine-readable report")
    args = parser.parse_args()

    paths = sorted(ALIGNMENT.glob("*.assembly.json"))
    if args.section:
        paths = [ALIGNMENT / f"{args.section}.assembly.json"]
    report = [analyze(path) for path in paths]

    for section in report:
        print(f"\n{section['section']}  median {section['active_median_dbfs']:.2f} dBFS")
        for chunk in section["chunks"]:
            if chunk["flag"]:
                print(
                    f"  chunk {chunk['chunk']:>3}: {chunk['active_dbfs']:>6.2f} dBFS  "
                    f"neighbors {chunk['vs_neighbors_db']:+.2f} dB  "
                    f"peak {chunk['peak_dbfs']:.2f}  join {chunk['boundary_jump_dbfs']:.2f}\n"
                    f"             {chunk['text'][:180]}"
                )

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
