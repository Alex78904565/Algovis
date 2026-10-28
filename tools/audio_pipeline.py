"""Assemble narration takes and create timestamped Whisper transcripts.

Raw recordings are never modified.  The assembled section WAV is the timing
authority; transcript corrections and animation cues live beside it as JSON.
"""

from __future__ import annotations

import argparse
import copy
import difflib
import hashlib
import json
import math
import re
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.signal import butter, medfilt, resample_poly, sosfiltfilt


ROOT = Path(__file__).resolve().parents[1]
AUDIO_ROOT = ROOT / "assets" / "audio" / "dp"
NATURAL_TAILS_PATH = (
    AUDIO_ROOT / "natural_tails" / "NATURAL_TAIL_CANDIDATES.json"
)
TAKE_PATTERN = re.compile(r"^(?P<chunk>\d{3})_take_(?P<take>\d{2})(?:.*)\.wav$", re.I)


@dataclass(frozen=True)
class AudioData:
    rate: int
    samples: np.ndarray


def read_wav(path: Path) -> AudioData:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())

    if width == 1:
        raw = np.frombuffer(frames, dtype=np.uint8).astype(np.float64)
        samples = (raw - 128.0) / 128.0
    elif width == 2:
        samples = np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0
    elif width == 3:
        packed = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        values = (
            packed[:, 0].astype(np.int32)
            | (packed[:, 1].astype(np.int32) << 8)
            | (packed[:, 2].astype(np.int32) << 16)
        )
        values = np.where(values & 0x800000, values - 0x1000000, values)
        samples = values.astype(np.float64) / 8388608.0
    elif width == 4:
        samples = np.frombuffer(frames, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width ({width} bytes): {path}")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return AudioData(rate=rate, samples=samples.astype(np.float32))


def resample(audio: AudioData, target_rate: int) -> np.ndarray:
    if audio.rate == target_rate:
        return audio.samples
    divisor = math.gcd(audio.rate, target_rate)
    return resample_poly(
        audio.samples,
        target_rate // divisor,
        audio.rate // divisor,
    ).astype(np.float32)


def trim_silence(
    samples: np.ndarray,
    rate: int,
    threshold_db: float = -48.0,
    frame_ms: float = 20.0,
    headroom_before: float = 0.16,
    headroom_after: float = 0.24,
) -> tuple[np.ndarray, int, int]:
    """Trim outer digital silence while preserving consonants and edit room."""
    frame = max(1, round(rate * frame_ms / 1000.0))
    frame_count = math.ceil(len(samples) / frame)
    padded = np.pad(samples, (0, frame_count * frame - len(samples)))
    rms = np.sqrt(np.mean(padded.reshape(frame_count, frame) ** 2, axis=1))
    active = np.flatnonzero(rms >= 10 ** (threshold_db / 20.0))
    if len(active) == 0:
        return samples, 0, len(samples)

    start = max(0, int(active[0] * frame - headroom_before * rate))
    end = min(len(samples), int((active[-1] + 1) * frame + headroom_after * rate))
    return samples[start:end], start, end


def fade_clip_edges(
    samples: np.ndarray,
    rate: int,
    fade_seconds: float = 0.015,
) -> np.ndarray:
    """De-click a trimmed take without changing its length or timing.

    The section assembler places digital silence between independently
    recorded takes.  Even a tiny non-zero sample at either edge therefore
    creates a discontinuity that sounds like a click.  A short raised-cosine
    ramp reaches an exact zero at both boundaries while leaving the spoken
    portion of the take untouched.
    """
    fade_samples = min(round(rate * fade_seconds), len(samples) // 2)
    if fade_samples <= 0:
        return samples

    smoothed = samples.copy()
    phase = np.linspace(0.0, math.pi / 2.0, fade_samples, endpoint=True)
    fade_in = np.sin(phase) ** 2
    fade_out = fade_in[::-1]
    smoothed[:fade_samples] *= fade_in
    smoothed[-fade_samples:] *= fade_out
    return smoothed


def mute_clip_head(
    samples: np.ndarray,
    rate: int,
    mute_seconds: float,
) -> np.ndarray:
    """Remove a known capture transient while preserving clip duration.

    Some recorders emit a short static burst as recording starts.  Section
    manifests may mute a verified pre-roll interval; replacing it with silence
    keeps every downstream cue at exactly the same time.
    """
    mute_samples = min(round(rate * mute_seconds), len(samples))
    if mute_samples <= 0:
        return samples
    cleaned = samples.copy()
    cleaned[:mute_samples] = 0.0
    return cleaned


def insert_verified_master_pauses(samples, rate, pauses):
    """Insert pauses at reviewed quiet seams, never at detected speech.

    Times refer to the unedited master. Only a four-millisecond quiet edge
    fade changes existing samples; callers must translate later timing data.
    The peak check rejects a stale edit if the recording has changed.
    """
    if samples.dtype != np.int16 or samples.ndim != 1:
        raise ValueError("Pause edits require mono PCM16")
    output=samples.copy();inserted=0;records=[];last=-1
    for pause in sorted(pauses,key=lambda item:float(item['at'])):
        at,seconds=float(pause['at']),float(pause['seconds'])
        if not math.isfinite(at) or not math.isfinite(seconds) or at<=last or seconds<=0:
            raise ValueError("Pause points must be distinct and durations positive")
        point=round(at*rate);window=max(1,round(.01*rate));fade=max(1,round(.004*rate))
        if point-window<0 or point+window>len(samples):
            raise ValueError("Pause point needs a complete quiet window")
        peak=float(np.max(np.abs(samples[point-window:point+window].astype(np.int32))))/32768
        if peak>float(pause.get('maximum_quiet_peak',.004)):
            raise ValueError(f"Pause at {at:.3f}s intersects speech or non-quiet audio")
        position=point+inserted;length=round(seconds*rate)
        if length<1:raise ValueError("Pause must contain at least one sample")
        output[position-fade:position]=np.rint(output[position-fade:position]*np.linspace(1,0,fade)).astype(np.int16)
        output[position:position+fade]=np.rint(output[position:position+fade]*np.linspace(0,1,fade)).astype(np.int16)
        output=np.concatenate((output[:position],np.zeros(length,dtype=np.int16),output[position:]))
        records.append({'at':at,'seconds':length/rate,'inserted_samples':length,'quiet_peak':peak})
        inserted+=length;last=at
    return output,records


def mute_internal_artifacts(
    samples: np.ndarray,
    rate: int,
    ranges: list[dict[str, object]],
    padding_seconds: float = 0.012,
    fade_seconds: float = 0.012,
) -> np.ndarray:
    """Silence verified non-speech artifacts without changing clip timing.

    Ranges are relative to the final selected chunk, after any approved tempo
    processing.  Short fades reach exact zero on each side, preventing the
    repair itself from creating a new click.  The source recording is never
    modified.
    """
    if not ranges:
        return samples
    repaired = samples.astype(np.float32, copy=True)
    for item in ranges:
        start_seconds = float(item["start"])
        end_seconds = float(item["end"])
        if not 0.0 <= start_seconds < end_seconds <= len(repaired) / rate:
            raise ValueError(
                f"Invalid internal silence repair {start_seconds:.4f} to "
                f"{end_seconds:.4f} for a {len(repaired) / rate:.4f}s clip"
            )
        start = max(0, round((start_seconds - padding_seconds) * rate))
        end = min(len(repaired), round((end_seconds + padding_seconds) * rate))
        fade = min(round(fade_seconds * rate), start, len(repaired) - end)
        if fade > 0:
            phase = np.linspace(0.0, math.pi / 2.0, fade, endpoint=True)
            ramp = np.sin(phase) ** 2
            repaired[start - fade:start] *= ramp[::-1]
            repaired[end:end + fade] *= ramp
        repaired[start:end] = 0.0
    return repaired


def gain_internal_ranges(
    samples: np.ndarray,
    rate: int,
    ranges: list[dict[str, object]],
    default_fade_seconds: float = 0.06,
) -> np.ndarray:
    """Raise or lower a verified phrase without changing clip timing.

    The edit is blended in and out with a raised-cosine envelope so a local
    level correction cannot introduce a click at either boundary.  These
    ranges use the same post-trim, post-tempo coordinate system as internal
    silence repairs.
    """
    if not ranges:
        return samples
    adjusted = samples.astype(np.float32, copy=True)
    for item in ranges:
        start_seconds = float(item["start"])
        end_seconds = float(item["end"])
        gain_db = float(item["gain_db"])
        fade_seconds = float(item.get("fade_seconds", default_fade_seconds))
        if not 0.0 <= start_seconds < end_seconds <= len(adjusted) / rate:
            raise ValueError(
                f"Invalid internal gain range {start_seconds:.4f} to "
                f"{end_seconds:.4f} for a {len(adjusted) / rate:.4f}s clip"
            )
        start = round(start_seconds * rate)
        end = round(end_seconds * rate)
        fade = min(round(fade_seconds * rate), start, len(adjusted) - end)
        gain = 10.0 ** (gain_db / 20.0)
        envelope = np.ones(len(adjusted), dtype=np.float32)
        envelope[start:end] = gain
        if fade > 0:
            phase = np.linspace(0.0, math.pi / 2.0, fade, endpoint=True)
            ramp = np.sin(phase) ** 2
            envelope[start - fade:start] = 1.0 + (gain - 1.0) * ramp
            envelope[end:end + fade] = gain + (1.0 - gain) * ramp
        adjusted *= envelope
    return np.clip(adjusted, -0.999, 0.999)


def clean_narration_noise(
    samples: np.ndarray,
    rate: int,
    settings: dict[str, object],
) -> np.ndarray:
    """Apply conservative cleanup to selected narration takes.

    This is intentionally opt-in per section/chunk.  A gentle high-pass removes
    handling rumble, while non-stationary spectral gating reduces intermittent
    cloth or desk noise without treating the voice like a stationary noise
    profile.  Raw recordings remain untouched.
    """
    cleaned = samples.astype(np.float32, copy=True)
    reference_rms = float(np.sqrt(np.mean(cleaned ** 2)))

    # Independently edited takes can contain a one- or two-sample splice click
    # inside an otherwise quiet pause.  Repair only impulses whose surrounding
    # short-term level is quiet, so ordinary consonants and vocal attacks are
    # left alone.  This preserves the clip's exact duration and therefore all
    # narration cue times.
    if bool(settings.get("declick_quiet_impulses", False)) and len(cleaned) > 32:
        kernel_size = int(settings.get("declick_kernel_samples", 7))
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = max(3, kernel_size)
        baseline = medfilt(cleaned, kernel_size=kernel_size).astype(np.float32)
        residual = np.abs(cleaned - baseline)
        envelope_window = max(
            1, round(rate * float(settings.get("declick_envelope_seconds", 0.01)))
        )
        envelope = np.sqrt(
            np.convolve(
                cleaned.astype(np.float64) ** 2,
                np.ones(envelope_window, dtype=np.float64) / envelope_window,
                mode="same",
            )
        )
        impulse_mask = (
            residual > float(settings.get("declick_threshold", 0.07))
        ) & (
            envelope < float(settings.get("declick_quiet_rms", 0.03))
        )
        expand = max(0, int(settings.get("declick_expand_samples", 3)))
        if expand and np.any(impulse_mask):
            impulse_mask = np.convolve(
                impulse_mask.astype(np.uint8),
                np.ones(2 * expand + 1, dtype=np.uint8),
                mode="same",
            ) > 0
        cleaned[impulse_mask] = baseline[impulse_mask]

    highpass_hz = float(settings.get("highpass_hz", 0.0))
    if highpass_hz > 0.0 and len(cleaned) > 32:
        sos = butter(2, highpass_hz, btype="highpass", fs=rate, output="sos")
        cleaned = sosfiltfilt(sos, cleaned).astype(np.float32)

    prop_decrease = float(settings.get("prop_decrease", 0.0))
    if prop_decrease > 0.0:
        try:
            import noisereduce as nr
        except ImportError as exc:
            raise RuntimeError(
                "Noise cleanup was requested, but noisereduce is not installed. "
                "Run: python -m pip install noisereduce"
            ) from exc
        cleaned = nr.reduce_noise(
            y=cleaned,
            sr=rate,
            stationary=False,
            prop_decrease=prop_decrease,
            time_constant_s=float(settings.get("time_constant_s", 0.5)),
            freq_mask_smooth_hz=int(settings.get("freq_mask_smooth_hz", 400)),
            time_mask_smooth_ms=int(settings.get("time_mask_smooth_ms", 70)),
            thresh_n_mult_nonstationary=float(
                settings.get("threshold_multiplier", 1.5)
            ),
            sigmoid_slope_nonstationary=float(
                settings.get("sigmoid_slope", 8.0)
            ),
            use_tqdm=False,
            n_jobs=1,
        ).astype(np.float32)

    # Spectral gating can lower the whole take even when it mostly removed
    # background sound.  Match the original take's level so cleaned clips do
    # not suddenly sound quieter than neighboring narration.
    if bool(settings.get("match_loudness", True)) and reference_rms > 0.0:
        cleaned_rms = float(np.sqrt(np.mean(cleaned ** 2)))
        if cleaned_rms > 0.0:
            gain = reference_rms / cleaned_rms
            peak = float(np.max(np.abs(cleaned)))
            if peak > 0.0:
                gain = min(gain, 0.95 / peak)
            cleaned *= gain
    return cleaned


def load_edit_manifest(section: str) -> dict[str, object]:
    """Load optional, non-destructive assembly choices for one section."""
    path = AUDIO_ROOT / "edits" / f"{section}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_natural_tail_candidates(
    section: str,
) -> dict[int, dict[str, object]]:
    """Load screened low-level post-take tails for one section.

    The candidate file is measurement data, not an automatic quality verdict.
    Assembly uses only entries explicitly marked conservative candidates and
    only when the section edit manifest opts in.
    """
    if not NATURAL_TAILS_PATH.exists():
        raise FileNotFoundError(
            f"Natural-tail restoration requested, but missing {NATURAL_TAILS_PATH}"
        )
    candidates = json.loads(NATURAL_TAILS_PATH.read_text(encoding="utf-8"))
    return {
        int(candidate["chunk"]): candidate
        for candidate in candidates
        if candidate["section"] == section
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_derived_clip_manifest(
    manifest_reference: str | None,
    section: str,
) -> dict[int, dict[str, object]]:
    """Load authoritative tempo-rendered clips without reprocessing them.

    The external QC workflow renders and validates each clip once.  Assembly
    verifies the declared hash and monotone old-local -> new-local anchors, then
    inserts that PCM directly.  No tempo engine is run inside this pipeline.
    """
    if not manifest_reference:
        return {}
    manifest_path = ROOT / manifest_reference
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing derived-clip manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("clips", manifest)
    if not isinstance(entries, list):
        raise ValueError("Derived-clip manifest must contain a clips array")
    selected: dict[int, dict[str, object]] = {}
    for entry in entries:
        if entry.get("section") != section:
            continue
        chunk = int(entry["chunk"])
        if chunk in selected:
            raise ValueError(f"Duplicate derived clip for {section} chunk {chunk}")
        selected[chunk] = entry
    return selected


def validate_time_anchors(
    anchors: list[dict[str, object]],
    old_duration: float,
    new_duration: float,
    tolerance: float = 0.025,
) -> list[dict[str, float]]:
    if len(anchors) < 2:
        raise ValueError("A derived clip needs at least two local time anchors")
    normalized = [
        {"old": float(anchor["old"]), "new": float(anchor["new"])}
        for anchor in anchors
    ]
    if any(
        normalized[index]["old"] >= normalized[index + 1]["old"]
        or normalized[index]["new"] >= normalized[index + 1]["new"]
        for index in range(len(normalized) - 1)
    ):
        raise ValueError("Derived-clip time anchors must be strictly monotone")
    if (
        abs(normalized[0]["old"]) > tolerance
        or abs(normalized[0]["new"]) > tolerance
        or abs(normalized[-1]["old"] - old_duration) > tolerance
        or abs(normalized[-1]["new"] - new_duration) > tolerance
    ):
        raise ValueError(
            "Derived-clip anchors must cover both complete clip endpoints: "
            f"old 0..{old_duration:.6f}, new 0..{new_duration:.6f}"
        )
    # Pin tiny feature-matching endpoint error to the authoritative PCM bounds.
    normalized[0] = {"old": 0.0, "new": 0.0}
    normalized[-1] = {"old": old_duration, "new": new_duration}
    return normalized


def choose_takes(
    section_dir: Path,
    *,
    omit_chunks: set[int] | None = None,
    selected_takes: dict[int, int] | None = None,
    insert_after_chunks: dict[int, int] | None = None,
) -> list[tuple[int, Path]]:
    omit_chunks = omit_chunks or set()
    selected_takes = selected_takes or {}
    insert_after_chunks = insert_after_chunks or {}
    grouped: dict[int, list[tuple[int, Path]]] = {}
    for path in section_dir.glob("*.wav"):
        match = TAKE_PATTERN.match(path.name)
        if match:
            grouped.setdefault(int(match["chunk"]), []).append((int(match["take"]), path))
    if not grouped:
        raise FileNotFoundError(f"No numbered narration takes found in {section_dir}")

    choices: list[tuple[int, Path]] = []
    for chunk in sorted(grouped):
        if chunk in omit_chunks:
            continue
        takes = grouped[chunk]
        if chunk in selected_takes:
            take_number = selected_takes[chunk]
            matches = [path for take, path in takes if take == take_number]
            if not matches:
                raise ValueError(
                    f"Requested take {take_number:02} for chunk {chunk:03}, "
                    f"but it does not exist in {section_dir}"
                )
            source = matches[0]
        else:
            # The highest numbered take is the deliberate default. Every raw
            # source remains untouched.
            source = max(takes, key=lambda item: item[0])[1]
        choices.append((chunk, source))
    if not choices:
        raise ValueError(f"Every narration chunk was omitted for {section_dir.name}")

    # Pickup recordings often receive new, high chunk numbers so the existing
    # raw files and their source-time references never have to be renamed.
    # Reposition those pickups only at assembly time. A configured pickup may
    # be absent while it is still awaiting recording; once present, its anchor
    # must exist in the selected source list.
    for inserted_chunk, anchor_chunk in insert_after_chunks.items():
        if inserted_chunk == anchor_chunk:
            raise ValueError(
                f"Chunk {inserted_chunk:03} cannot be inserted after itself"
            )
        inserted_matches = [
            pair for pair in choices if pair[0] == inserted_chunk
        ]
        if not inserted_matches:
            continue
        anchor_indices = [
            index for index, pair in enumerate(choices) if pair[0] == anchor_chunk
        ]
        if not anchor_indices:
            raise ValueError(
                f"Cannot insert chunk {inserted_chunk:03} after unavailable "
                f"chunk {anchor_chunk:03} in {section_dir}"
            )
        inserted = inserted_matches[0]
        choices.remove(inserted)
        anchor_index = next(
            index for index, pair in enumerate(choices) if pair[0] == anchor_chunk
        )
        choices.insert(anchor_index + 1, inserted)
    return choices


def write_pcm16(path: Path, samples: np.ndarray, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = pcm16_samples(samples)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def pcm16_samples(samples: np.ndarray) -> np.ndarray:
    # Authoritative derived clips already are PCM16.  Returning those samples
    # byte-for-byte avoids a float decode/re-encode cycle that can move samples
    # by one least-significant bit (especially negative samples).
    if samples.dtype == np.dtype("<i2") or samples.dtype == np.dtype("int16"):
        return samples.astype("<i2", copy=False)
    return np.round(np.clip(samples, -1.0, 1.0) * 32767.0).astype("<i2")


def pcm16_sha256(samples: np.ndarray) -> str:
    return hashlib.sha256(pcm16_samples(samples).tobytes()).hexdigest()


def assemble(
    section: str,
    target_rate: int = 48_000,
    gap_seconds: float = 0.30,
    edge_fade_seconds: float = 0.015,
) -> Path:
    section_dir = AUDIO_ROOT / "raw" / section
    edits = load_edit_manifest(section)
    edge_fade_seconds = float(
        edits.get("edge_fade_seconds", edge_fade_seconds)
    )
    omit_chunks = {int(chunk) for chunk in edits.get("omit_chunks", [])}
    selected_takes = {
        int(chunk): int(take)
        for chunk, take in edits.get("selected_takes", {}).items()
    }
    insert_after_chunks = {
        int(chunk): int(anchor)
        for chunk, anchor in edits.get("insert_after_chunks", {}).items()
    }
    chunk_trims = {
        int(chunk): bounds
        for chunk, bounds in edits.get("chunk_trims", {}).items()
    }
    chunk_gain_db = {
        int(chunk): float(gain_db)
        for chunk, gain_db in edits.get("chunk_gain_db", {}).items()
    }
    gaps_after_chunks = {
        int(chunk): float(seconds)
        for chunk, seconds in edits.get("gaps_after_chunks", {}).items()
    }
    use_natural_tails = bool(edits.get("use_natural_tail_candidates", False))
    natural_tail_fade_seconds = float(
        edits.get("natural_tail_fade_seconds", 0.015)
    )
    natural_tail_candidates = (
        load_natural_tail_candidates(section) if use_natural_tails else {}
    )
    derived_clips = load_derived_clip_manifest(
        edits.get("derived_clip_manifest"), section
    )
    default_head_mute = float(edits.get("head_mute_seconds", 0.0))
    chunk_head_mutes = {
        int(chunk): float(seconds)
        for chunk, seconds in edits.get("chunk_head_mutes", {}).items()
    }
    noise_cleanup = edits.get("noise_cleanup", {})
    if noise_cleanup and not isinstance(noise_cleanup, dict):
        raise ValueError("noise_cleanup must be an object")
    cleanup_chunks = {
        int(chunk) for chunk in noise_cleanup.get("chunks", [])
    } if noise_cleanup else set()
    raw_internal_repairs = edits.get("internal_silence_repairs", {})
    if raw_internal_repairs and not isinstance(raw_internal_repairs, dict):
        raise ValueError("internal_silence_repairs must be an object")
    internal_repairs = {
        int(chunk): list(ranges)
        for chunk, ranges in raw_internal_repairs.items()
    }
    raw_internal_gains = edits.get("internal_gain_ranges", {})
    if raw_internal_gains and not isinstance(raw_internal_gains, dict):
        raise ValueError("internal_gain_ranges must be an object")
    internal_gains = {
        int(chunk): list(ranges)
        for chunk, ranges in raw_internal_gains.items()
    }
    internal_repair_padding = float(
        edits.get("internal_repair_padding_seconds", 0.012)
    )
    internal_repair_fade = float(
        edits.get("internal_repair_fade_seconds", 0.012)
    )
    sources = choose_takes(
        section_dir,
        omit_chunks=omit_chunks,
        selected_takes=selected_takes,
        insert_after_chunks=insert_after_chunks,
    )
    # Store assembled parts as final PCM16.  This lets approved derived clips
    # pass into the master byte-for-byte while unchanged baseline chunks still
    # use the exact quantization path that produced the frozen v2 masters.
    parts: list[np.ndarray] = []
    assembly: list[dict[str, object]] = []
    cursor = 0

    for index, (chunk, source) in enumerate(sources):
        audio = read_wav(source)
        converted = resample(audio, target_rate)
        trimmed, trim_start, trim_end = trim_silence(converted, target_rate)
        manual_trim = chunk_trims.get(chunk, {})
        if manual_trim:
            if not isinstance(manual_trim, dict):
                raise ValueError(f"chunk_trims[{chunk}] must be an object")
            trim_start = round(float(manual_trim.get("start", trim_start / target_rate)) * target_rate)
            trim_end = round(float(manual_trim.get("end", trim_end / target_rate)) * target_rate)
            if not 0 <= trim_start < trim_end <= len(converted):
                raise ValueError(
                    f"Invalid source-relative trim for chunk {chunk}: "
                    f"{trim_start / target_rate:.3f}s to {trim_end / target_rate:.3f}s"
                )
            trimmed = converted[trim_start:trim_end]
        derived = derived_clips.get(chunk)
        gain_db = chunk_gain_db.get(chunk, 0.0)
        # A validated tempo-adjusted clip is hashed against the untouched
        # trimmed take.  Apply new repair/level edits after loading that
        # authoritative clip; otherwise changing a gain would invalidate the
        # source hash and, worse, the edit would be silently discarded when
        # the derived PCM replaced the baseline below.
        if derived is None:
            if chunk in cleanup_chunks:
                trimmed = clean_narration_noise(trimmed, target_rate, noise_cleanup)
            if gain_db:
                gain = 10.0 ** (gain_db / 20.0)
                peak = float(np.max(np.abs(trimmed))) if len(trimmed) else 0.0
                if peak * gain > 1.0:
                    raise ValueError(
                        f"chunk_gain_db[{chunk}]={gain_db} would clip {section}; "
                        "choose a smaller gain"
                    )
                trimmed *= gain
        # Keep a copy of the trimmed take before boundary treatment.  Older
        # approved tempo clips were generated after the section's existing
        # noise cleanup, whereas newer tempo clips are intentionally hashed
        # against the untouched trim and cleaned after tempo adjustment.
        # Supporting both histories preserves the integrity check without
        # cleaning an older approved tempo clip twice.
        pre_boundary_trimmed = trimmed.copy()
        head_mute_seconds = chunk_head_mutes.get(chunk, default_head_mute)
        trimmed = mute_clip_head(trimmed, target_rate, head_mute_seconds)
        trimmed = fade_clip_edges(trimmed, target_rate, edge_fade_seconds)
        baseline_clip_duration = len(trimmed) / target_rate
        baseline_pcm = pcm16_samples(trimmed)
        assembled_pcm = baseline_pcm
        tempo_record: dict[str, object] | None = None
        if derived is not None:
            if not bool(derived.get("ready_for_assembly", False)):
                raise ValueError(
                    f"Derived clip {section} chunk {chunk} is not marked "
                    "ready_for_assembly"
                )
            derived_path = ROOT / str(derived["audio"])
            if not derived_path.exists():
                raise FileNotFoundError(f"Missing derived clip: {derived_path}")
            expected_source_hash = derived.get(
                "source_take_sha256", derived.get("source_sha256")
            )
            if expected_source_hash and sha256_file(source) != expected_source_hash:
                raise ValueError(
                    f"Source hash mismatch for {section} chunk {chunk}"
                )
            expected_baseline_pcm_hash = derived.get("baseline_pcm_sha256")
            actual_baseline_pcm_hash = pcm16_sha256(trimmed)
            baseline_hash_basis = "untouched_trim"
            derived_already_cleaned = False
            if (
                expected_baseline_pcm_hash
                and actual_baseline_pcm_hash != expected_baseline_pcm_hash
            ):
                legacy_baseline_hash = None
                if chunk in cleanup_chunks:
                    legacy_baseline = clean_narration_noise(
                        pre_boundary_trimmed.copy(), target_rate, noise_cleanup
                    )
                    legacy_baseline = mute_clip_head(
                        legacy_baseline, target_rate, head_mute_seconds
                    )
                    legacy_baseline = fade_clip_edges(
                        legacy_baseline, target_rate, edge_fade_seconds
                    )
                    legacy_baseline_hash = pcm16_sha256(legacy_baseline)
                if legacy_baseline_hash == expected_baseline_pcm_hash:
                    actual_baseline_pcm_hash = legacy_baseline_hash
                    baseline_hash_basis = "legacy_pre_tempo_noise_cleanup"
                    derived_already_cleaned = True
                else:
                    raise ValueError(
                        f"Baseline PCM hash mismatch for {section} chunk {chunk}"
                    )
            expected_derived_hash = derived.get("derived_sha256")
            actual_derived_hash = sha256_file(derived_path)
            if expected_derived_hash and actual_derived_hash != expected_derived_hash:
                raise ValueError(
                    f"Derived hash mismatch for {section} chunk {chunk}"
                )
            with wave.open(str(derived_path), "rb") as derived_wav:
                if (
                    derived_wav.getnchannels() != 1
                    or derived_wav.getsampwidth() != 2
                    or derived_wav.getframerate() != target_rate
                ):
                    raise ValueError(
                        "Authoritative derived clips must be mono PCM16 at "
                        f"{target_rate} Hz: {derived_path}"
                    )
            with wave.open(str(derived_path), "rb") as derived_wav:
                derived_pcm = np.frombuffer(
                    derived_wav.readframes(derived_wav.getnframes()),
                    dtype="<i2",
                ).copy()
            derived_duration = len(derived_pcm) / target_rate
            anchors = validate_time_anchors(
                list(derived["time_anchors"]),
                baseline_clip_duration,
                derived_duration,
            )
            # Preserve validated derived PCM byte-for-byte when it has no new
            # repair edits.  When a take needs leveling or cleanup, process the
            # already tempo-adjusted samples so its approved pacing and time
            # anchors remain intact.
            needs_cleanup = chunk in cleanup_chunks and not derived_already_cleaned
            post_processed = needs_cleanup or bool(gain_db)
            if post_processed:
                derived_samples = (
                    derived_pcm.astype(np.float32) / 32768.0
                )
                if needs_cleanup:
                    derived_samples = clean_narration_noise(
                        derived_samples, target_rate, noise_cleanup
                    )
                if gain_db:
                    gain = 10.0 ** (gain_db / 20.0)
                    peak = (
                        float(np.max(np.abs(derived_samples)))
                        if len(derived_samples) else 0.0
                    )
                    if peak * gain > 1.0:
                        raise ValueError(
                            f"chunk_gain_db[{chunk}]={gain_db} would clip {section}; "
                            "choose a smaller gain"
                        )
                    derived_samples *= gain
                derived_samples = fade_clip_edges(
                    derived_samples, target_rate, edge_fade_seconds
                )
                assembled_pcm = pcm16_samples(derived_samples)
            else:
                assembled_pcm = derived_pcm
            tempo_record = {
                "audio": derived_path.relative_to(ROOT).as_posix(),
                "derived_sha256": actual_derived_hash,
                "source_take_sha256": sha256_file(source),
                "baseline_pcm_sha256": actual_baseline_pcm_hash,
                "baseline_hash_basis": baseline_hash_basis,
                "engine": derived.get("engine"),
                "factor": derived.get("factor"),
                "old_duration": round(baseline_clip_duration, 6),
                "new_duration": round(derived_duration, 6),
                "time_anchors": anchors,
                "authoritative_pcm": not post_processed,
                "post_processed": post_processed,
                "post_tempo_noise_cleanup": needs_cleanup,
            }
        chunk_repairs = internal_repairs.get(chunk, [])
        if chunk_repairs:
            repaired_samples = assembled_pcm.astype(np.float32) / 32768.0
            repaired_samples = mute_internal_artifacts(
                repaired_samples,
                target_rate,
                chunk_repairs,
                padding_seconds=internal_repair_padding,
                fade_seconds=internal_repair_fade,
            )
            assembled_pcm = pcm16_samples(repaired_samples)
            if tempo_record is not None:
                tempo_record["authoritative_pcm"] = False
                tempo_record["post_processed"] = True
                tempo_record["internal_silence_repairs"] = len(chunk_repairs)
        chunk_gain_ranges = internal_gains.get(chunk, [])
        if chunk_gain_ranges:
            gained_samples = assembled_pcm.astype(np.float32) / 32768.0
            gained_samples = gain_internal_ranges(
                gained_samples, target_rate, chunk_gain_ranges,
            )
            assembled_pcm = pcm16_samples(gained_samples)
            if tempo_record is not None:
                tempo_record["authoritative_pcm"] = False
                tempo_record["post_processed"] = True
                tempo_record["internal_gain_ranges"] = len(chunk_gain_ranges)
        start = cursor / target_rate
        parts.append(assembled_pcm)
        cursor += len(assembled_pcm)
        end = cursor / target_rate
        is_last_chunk = index == len(sources) - 1
        # Ordinary sections receive the default gap only between takes.  An
        # explicitly configured gap after the final take is intentional tail
        # room for an on-screen reading beat and must not be discarded.
        chunk_gap_seconds = gaps_after_chunks.get(
            chunk, 0.0 if is_last_chunk else gap_seconds
        )
        entry: dict[str, object] = {
            "chunk": chunk,
            "source": source.relative_to(ROOT).as_posix(),
            "source_duration": round(len(converted) / target_rate, 6),
            "trim_start": round(trim_start / target_rate, 6),
            "trim_end": round(trim_end / target_rate, 6),
            "head_mute_seconds": head_mute_seconds,
            "gain_db": gain_db,
            "noise_cleanup": chunk in cleanup_chunks,
            "internal_silence_repairs": chunk_repairs,
            "tempo": tempo_record,
            "master_start": round(start, 6),
            "master_end": round(end, 6),
            "gap_after_seconds": chunk_gap_seconds,
        }
        if chunk_gap_seconds > 0.0:
            gap = np.zeros(
                round(target_rate * chunk_gap_seconds), dtype=np.float32
            )
            candidate = natural_tail_candidates.get(chunk)
            natural_tail_record: dict[str, object] | None = None
            if (
                candidate
                and bool(candidate.get("conservative_low_level_candidate"))
                and float(candidate.get("proposed_tail_seconds", 0.0)) > 0.0
            ):
                candidate_source = str(candidate["source"])
                selected_source = source.relative_to(ROOT).as_posix()
                if candidate_source != selected_source:
                    raise ValueError(
                        f"Natural-tail source mismatch for {section} chunk {chunk}: "
                        f"{candidate_source} != {selected_source}"
                    )
                source_tail_start = float(candidate["source_tail_start"])
                new_space = max(0.0, chunk_gap_seconds - gap_seconds)
                requested_tail = min(
                    float(candidate["proposed_tail_seconds"]), new_space
                )
                source_tail = resample(read_wav(source), target_rate)
                tail_start_sample = round(source_tail_start * target_rate)
                tail_sample_count = min(
                    round(requested_tail * target_rate),
                    len(source_tail) - tail_start_sample,
                    len(gap),
                )
                if tail_sample_count > 0:
                    tail = source_tail[
                        tail_start_sample : tail_start_sample + tail_sample_count
                    ].copy()
                    tail = fade_clip_edges(
                        tail, target_rate, natural_tail_fade_seconds
                    )
                    gap[:tail_sample_count] = tail
                    natural_tail_record = {
                        "used": True,
                        "source": candidate_source,
                        "source_start": round(source_tail_start, 6),
                        "source_end": round(
                            source_tail_start + tail_sample_count / target_rate, 6
                        ),
                        "duration": round(tail_sample_count / target_rate, 6),
                        "placement": "start of added inter-chunk gap",
                        "fade_seconds": natural_tail_fade_seconds,
                        "screened_rms_dbfs": candidate.get("tail_rms_dbfs"),
                        "screened_peak_dbfs": candidate.get("tail_peak_dbfs"),
                    }
            entry["natural_tail"] = natural_tail_record or {
                "used": False,
                "reason": (
                    "No conservative candidate with at least 0.1 seconds of "
                    "new boundary space; the gap remains silence."
                ),
            }
            parts.append(pcm16_samples(gap))
            cursor += len(gap)
        assembly.append(entry)

    unused_derived = sorted(set(derived_clips) - {chunk for chunk, _ in sources})
    if unused_derived:
        raise ValueError(
            f"Derived clips target omitted or unavailable chunks in {section}: "
            f"{unused_derived}"
        )

    master = np.concatenate(parts)
    master_gain_db = float(edits.get("master_gain_db", 0.0))
    if master_gain_db:
        gain = 10.0 ** (master_gain_db / 20.0)
        peak = int(np.max(np.abs(master.astype(np.int32)))) if len(master) else 0
        if peak * gain > np.iinfo(np.int16).max:
            raise ValueError(
                f"master_gain_db={master_gain_db} would clip {section}; "
                "choose a smaller gain"
            )
        master = np.rint(master.astype(np.float64) * gain).astype(np.int16)
    master,pause_records=insert_verified_master_pauses(master,target_rate,edits.get('master_pause_insertions',[]))
    if pause_records:
        for chunk in assembly:
            start,end=chunk['master_start'],chunk['master_end']
            chunk['master_start']=round(start+sum(p['seconds'] for p in pause_records if p['at']<=start),6)
            chunk['master_end']=round(end+sum(p['seconds'] for p in pause_records if p['at']<=end),6)
            inside=[p for p in pause_records if start<p['at']<end]
            if inside:chunk['master_pause_insertions']=inside
    master_path = AUDIO_ROOT / "masters" / f"{section}.wav"
    write_pcm16(master_path, master, target_rate)

    alignment_dir = AUDIO_ROOT / "alignment"
    alignment_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "section": section,
        "audio": master_path.relative_to(ROOT).as_posix(),
        "sample_rate": target_rate,
        "gap_seconds": gap_seconds,
        "edge_fade_seconds": edge_fade_seconds,
        "master_gain_db": master_gain_db,
        "edits": edits,
        "duration": round(len(master) / target_rate, 6),
        "master_pause_insertions": pause_records,
        "chunks": assembly,
    }
    (alignment_dir / f"{section}.assembly.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return master_path


def build_time_mapper(
    previous_manifest: dict[str, object],
    current_manifest: dict[str, object],
):
    """Map a point to its nearest spoken chunk without stretching a gap.

    This scalar helper is useful for approximate navigation. Metadata retiming
    uses ``build_span_mapper`` so a word or subtitle span keeps its complete
    duration and its original offset from one actual source chunk.
    """
    map_span = build_span_mapper(previous_manifest, current_manifest)

    def map_time(timestamp: float) -> float:
        start, _end, _anchor = map_span(timestamp, timestamp)
        return start

    return map_time


def build_span_mapper(
    previous_manifest: dict[str, object],
    current_manifest: dict[str, object],
):
    """Map an intact timing span by one source-chunk translation.

    A span that overlaps speech is assigned to the chunk with maximum overlap.
    A span entirely inside an inter-chunk gap is assigned to the nearest spoken
    chunk, preferring the incoming chunk on an exact tie.  Start and end receive
    the same translation, so word duration and cue lead are never stretched with
    a widened gap.
    """
    previous_chunks = {
        int(chunk["chunk"]): chunk for chunk in previous_manifest["chunks"]
    }
    current_chunks = {
        int(chunk["chunk"]): chunk for chunk in current_manifest["chunks"]
    }
    if previous_chunks.keys() != current_chunks.keys():
        raise ValueError(
            "Chunk sets differ. Retime is safe only when the selected spoken "
            "chunks are unchanged."
        )

    ordered = [
        (previous_chunks[key], current_chunks[key]) for key in previous_chunks
    ]

    def map_with_chunk(
        timestamp: float,
        old_chunk: dict[str, object],
        new_chunk: dict[str, object],
    ) -> float:
        old_start = float(old_chunk["master_start"])
        old_end = float(old_chunk["master_end"])
        new_start = float(new_chunk["master_start"])
        new_end = float(new_chunk["master_end"])
        tempo = new_chunk.get("tempo")
        if not tempo:
            return timestamp + (new_start - old_start)

        old_local = timestamp - old_start
        old_duration = old_end - old_start
        new_duration = new_end - new_start
        if old_local < 0.0:
            # A cue in the preceding gap keeps its absolute lead to this chunk.
            return new_start + old_local
        if old_local > old_duration:
            # Likewise preserve an explicit lag into the following gap.
            return new_end + (old_local - old_duration)

        anchors = list(tempo["time_anchors"])
        for left, right in zip(anchors, anchors[1:]):
            old_left, old_right = float(left["old"]), float(right["old"])
            if old_left - 1e-9 <= old_local <= old_right + 1e-9:
                fraction = (
                    0.0
                    if old_right == old_left
                    else (old_local - old_left) / (old_right - old_left)
                )
                new_local = float(left["new"]) + fraction * (
                    float(right["new"]) - float(left["new"])
                )
                return new_start + new_local
        if abs(old_local - old_duration) <= 1e-6:
            return new_start + new_duration
        raise ValueError(
            f"No tempo anchor covers local time {old_local:.6f} in chunk "
            f"{old_chunk['chunk']}"
        )

    def map_span(
        start: float,
        end: float,
        preferred_chunk: int | None = None,
    ) -> tuple[float, float, dict[str, object]]:
        if end < start:
            raise ValueError(f"Invalid timing span {start:.6f}-{end:.6f}")

        if preferred_chunk is not None:
            candidates = [
                pair for pair in ordered if int(pair[0]["chunk"]) == preferred_chunk
            ]
            if not candidates:
                raise ValueError(f"Unknown preferred chunk {preferred_chunk}")
            old_chunk, new_chunk = candidates[0]
            strategy = "explicit-anchor"
        else:
            overlaps: list[tuple[float, int, dict[str, object], dict[str, object]]] = []
            for old_chunk, new_chunk in ordered:
                old_start = float(old_chunk["master_start"])
                old_end = float(old_chunk["master_end"])
                overlap = max(0.0, min(end, old_end) - max(start, old_start))
                if start == end and old_start - 1e-9 <= start <= old_end + 1e-9:
                    overlap = 1e-9
                overlaps.append(
                    (overlap, int(old_chunk["chunk"]), old_chunk, new_chunk)
                )
            best_overlap = max(item[0] for item in overlaps)
            if best_overlap > 0.0:
                best = max(
                    (item for item in overlaps if item[0] == best_overlap),
                    key=lambda item: item[1],
                )
                _overlap, _chunk_id, old_chunk, new_chunk = best
                strategy = "maximum-overlap"
            else:
                center = (start + end) / 2.0
                distances = []
                for old_chunk, new_chunk in ordered:
                    old_start = float(old_chunk["master_start"])
                    old_end = float(old_chunk["master_end"])
                    distance = (
                        old_start - center
                        if center < old_start
                        else center - old_end
                        if center > old_end
                        else 0.0
                    )
                    distances.append(
                        (distance, -old_start, old_chunk, new_chunk)
                    )
                _distance, _incoming_tiebreak, old_chunk, new_chunk = min(distances)
                strategy = "nearest-chunk"

        mapped_start = map_with_chunk(start, old_chunk, new_chunk)
        mapped_end = map_with_chunk(end, old_chunk, new_chunk)
        start_shift = mapped_start - start
        end_shift = mapped_end - end
        return mapped_start, mapped_end, {
            "chunk": int(old_chunk["chunk"]),
            "strategy": strategy,
            "mapping": (
                "piecewise-local-time-anchors"
                if new_chunk.get("tempo")
                else "uniform-chunk-translation"
            ),
            "start_shift_seconds": round(start_shift, 6),
            "end_shift_seconds": round(end_shift, 6),
            "old_chunk_range": [
                old_chunk["master_start"], old_chunk["master_end"]
            ],
            "new_chunk_range": [
                new_chunk["master_start"], new_chunk["master_end"]
            ],
        }

    return map_span


def normalized_tokens(text: str) -> list[str]:
    text = re.sub(r"(?<=[a-z0-9])-(?=[a-z0-9])", "", text.lower())
    text = re.sub(r"(?<=[a-z0-9])['’](?=[a-z0-9])", "", text)
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if token
    ]


def find_phrase_word_span(
    phrase: str,
    words: list[dict[str, object]],
    cue_time: float,
) -> tuple[float, float] | None:
    """Find the occurrence of a cue phrase nearest its original cue time."""
    phrase_tokens = normalized_tokens(phrase)
    word_tokens = [
        normalized_tokens(str(word["word"]))[0]
        if normalized_tokens(str(word["word"]))
        else ""
        for word in words
    ]
    if not phrase_tokens:
        return None

    matches: list[tuple[float, int, int]] = []
    width = len(phrase_tokens)
    for index in range(0, len(word_tokens) - width + 1):
        if word_tokens[index : index + width] == phrase_tokens:
            distance = abs(float(words[index]["start"]) - cue_time)
            matches.append((distance, index, index + width - 1))
    if not matches:
        # A short cue phrase can survive a minor transcript correction better
        # by anchoring its first two words than by falling back to gap geometry.
        prefix = phrase_tokens[: min(2, len(phrase_tokens))]
        width = len(prefix)
        for index in range(0, len(word_tokens) - width + 1):
            if word_tokens[index : index + width] == prefix:
                distance = abs(float(words[index]["start"]) - cue_time)
                matches.append((distance, index, index + width - 1))
    if not matches:
        return None
    _distance, first, last = min(matches)
    return float(words[first]["start"]), float(words[last]["end"])


def write_srt(path: Path, segments: list[dict[str, object]]) -> None:
    blocks = [
        f"{index}\n{srt_timestamp(float(segment['start']))} --> "
        f"{srt_timestamp(float(segment['end']))}\n{segment['text']}"
        for index, segment in enumerate(segments, start=1)
    ]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


def retime_for_pacing(section: str, previous_assembly: Path) -> None:
    """Rebuild timing from frozen pre-pacing metadata and source chunks."""
    alignment_dir = AUDIO_ROOT / "alignment"
    current_assembly = alignment_dir / f"{section}.assembly.json"
    previous = json.loads(previous_assembly.read_text(encoding="utf-8"))
    current = json.loads(current_assembly.read_text(encoding="utf-8"))
    map_span = build_span_mapper(previous, current)
    source_alignment_dir = previous_assembly.parent
    audit: dict[str, object] = {
        "section": section,
        "source_assembly": previous_assembly.as_posix(),
        "current_assembly": current_assembly.relative_to(ROOT).as_posix(),
        "policy": (
            "Each word or subtitle span moves intact with the source chunk that "
            "has maximum overlap; a gap-only span uses the nearest chunk. Cue "
            "phrases use their matched spoken words as an explicit anchor."
        ),
        "gap_or_boundary_spans": [],
        "cues": [],
    }

    def retime_span(
        start: float,
        end: float,
        *,
        kind: str,
        identifier: str,
        preferred_chunk: int | None = None,
    ) -> tuple[float, float, dict[str, object]]:
        mapped_start, mapped_end, anchor = map_span(
            start, end, preferred_chunk=preferred_chunk
        )
        old_start, old_end = anchor["old_chunk_range"]
        boundary_span = start < float(old_start) - 1e-6 or end > float(old_end) + 1e-6
        if boundary_span or anchor["strategy"] == "nearest-chunk":
            audit["gap_or_boundary_spans"].append(
                {
                    "kind": kind,
                    "id": identifier,
                    "old_range": [round(start, 3), round(end, 3)],
                    "new_range": [round(mapped_start, 3), round(mapped_end, 3)],
                    "anchor": anchor,
                }
            )
        return mapped_start, mapped_end, anchor

    def retime_container_span(
        start: float,
        end: float,
        source_words: list[dict[str, object]],
        *,
        kind: str,
        identifier: str,
    ) -> tuple[float, float, dict[str, object]]:
        """Expand a multi-word container across newly inserted pauses.

        The first endpoint keeps its offset from the first overlapping spoken
        word, and the last endpoint keeps its offset from the last overlapping
        word.  Unlike a word, the container is therefore allowed to grow when
        it crosses one or more widened chunk boundaries.
        """
        associated = [
            word
            for word in source_words
            if float(word["end"]) >= start - 1e-6
            and float(word["start"]) <= end + 1e-6
        ]
        if not associated:
            return retime_span(
                start, end, kind=kind, identifier=identifier
            )

        first = associated[0]
        last = associated[-1]
        mapped_first_start, _mapped_first_end, first_anchor = map_span(
            float(first["start"]), float(first["end"])
        )
        _mapped_last_start, mapped_last_end, last_anchor = map_span(
            float(last["start"]), float(last["end"])
        )
        lead = max(0.0, float(first["start"]) - start)
        tail = max(0.0, end - float(last["end"]))
        mapped_start = max(0.0, mapped_first_start - lead)
        mapped_end = min(float(current["duration"]), mapped_last_end + tail)
        anchor = {
            "strategy": "first-and-last-spoken-word",
            "first_chunk": first_anchor["chunk"],
            "last_chunk": last_anchor["chunk"],
            "first_word_range": [first["start"], first["end"]],
            "last_word_range": [last["start"], last["end"]],
            "preserved_lead_seconds": round(lead, 6),
            "preserved_tail_seconds": round(tail, 6),
        }
        if first_anchor["chunk"] != last_anchor["chunk"]:
            audit["gap_or_boundary_spans"].append(
                {
                    "kind": kind,
                    "id": identifier,
                    "old_range": [round(start, 3), round(end, 3)],
                    "new_range": [round(mapped_start, 3), round(mapped_end, 3)],
                    "anchor": anchor,
                }
            )
        return mapped_start, mapped_end, anchor

    for suffix in ("words.json", "words.raw.json"):
        source_path = source_alignment_dir / f"{section}.{suffix}"
        path = alignment_dir / f"{section}.{suffix}"
        if not source_path.exists():
            continue
        document = json.loads(source_path.read_text(encoding="utf-8"))
        source_document_words = [dict(word) for word in document.get("words", [])]
        for index, word in enumerate(document.get("words", [])):
            start, end, _anchor = retime_span(
                float(word["start"]), float(word["end"]),
                kind=suffix, identifier=f"word-{index}",
            )
            word["start"], word["end"] = round(start, 3), round(end, 3)
        for segment_index, segment in enumerate(document.get("segments", [])):
            start, end, _anchor = retime_container_span(
                float(segment["start"]), float(segment["end"]),
                source_document_words,
                kind=suffix, identifier=f"segment-{segment_index}",
            )
            segment["start"], segment["end"] = round(start, 3), round(end, 3)
            for word_index, word in enumerate(segment.get("words", [])):
                start, end, _anchor = retime_span(
                    float(word["start"]), float(word["end"]),
                    kind=f"{suffix}-segment-word",
                    identifier=f"segment-{segment_index}-word-{word_index}",
                )
                word["start"], word["end"] = round(start, 3), round(end, 3)
        path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")

    for suffix in ("srt", "raw.srt"):
        source_path = source_alignment_dir / f"{section}.{suffix}"
        path = alignment_dir / f"{section}.{suffix}"
        if not source_path.exists():
            continue
        segments = parse_srt(source_path)
        source_words_suffix = "words.raw.json" if suffix == "raw.srt" else "words.json"
        source_words_path_for_srt = source_alignment_dir / f"{section}.{source_words_suffix}"
        source_words_for_srt = (
            json.loads(source_words_path_for_srt.read_text(encoding="utf-8")).get(
                "words", []
            )
            if source_words_path_for_srt.exists()
            else []
        )
        for index, segment in enumerate(segments):
            start, end, _anchor = retime_container_span(
                float(segment["start"]), float(segment["end"]),
                source_words_for_srt,
                kind=suffix, identifier=f"caption-{index}",
            )
            segment["start"], segment["end"] = round(start, 3), round(end, 3)
        write_srt(path, segments)

    source_review_path = source_alignment_dir / f"{section}.review.json"
    review_path = alignment_dir / f"{section}.review.json"
    if source_review_path.exists():
        review = json.loads(source_review_path.read_text(encoding="utf-8"))
        source_review_words = (
            json.loads(
                (source_alignment_dir / f"{section}.words.raw.json").read_text(
                    encoding="utf-8"
                )
            ).get("words", [])
            if (source_alignment_dir / f"{section}.words.raw.json").exists()
            else []
        )
        for index, span in enumerate(review.get("word_spans", [])):
            start, end, _anchor = retime_container_span(
                float(span["start"]), float(span["end"]),
                source_review_words,
                kind="review-span", identifier=f"review-span-{index}",
            )
            span["start"], span["end"] = round(start, 3), round(end, 3)
        review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

    source_cues_path = previous_assembly.parent.parent / "cues" / f"{section}.cues.json"
    cues_path = AUDIO_ROOT / "cues" / f"{section}.cues.json"
    cues = json.loads(source_cues_path.read_text(encoding="utf-8"))
    source_words_path = source_alignment_dir / f"{section}.words.json"
    source_words = (
        json.loads(source_words_path.read_text(encoding="utf-8")).get("words", [])
        if source_words_path.exists()
        else []
    )
    cues["duration"] = round(float(current["duration"]), 6)
    for cue in cues.get("cues", []):
        old_time = float(cue["time"])
        if cue["name"] == "section_start":
            new_time = 0.0
            anchor = {"strategy": "section-start"}
        elif cue["name"] == "section_end":
            new_time = float(current["duration"])
            anchor = {"strategy": "section-end"}
        else:
            phrase_span = find_phrase_word_span(
                str(cue.get("phrase", "")), source_words, old_time
            )
            preferred_chunk = None
            if phrase_span is not None:
                _phrase_start, _phrase_end, phrase_anchor = map_span(*phrase_span)
                preferred_chunk = int(phrase_anchor["chunk"])
            new_time, _unused, anchor = map_span(
                old_time, old_time, preferred_chunk=preferred_chunk
            )
            if phrase_span is not None:
                anchor = dict(anchor)
                anchor["strategy"] = "matched-phrase-explicit-anchor"
                anchor["matched_phrase_range"] = [
                    round(phrase_span[0], 3), round(phrase_span[1], 3)
                ]
        cue["time"] = round(
            min(float(current["duration"]), max(0.0, new_time)), 3
        )
        audit["cues"].append(
            {
                "name": cue["name"],
                "phrase": cue.get("phrase"),
                "old_time": old_time,
                "new_time": cue["time"],
                "anchor": anchor,
            }
        )
    cues_path.write_text(json.dumps(cues, indent=2) + "\n", encoding="utf-8")
    (alignment_dir / f"{section}.retime.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )


def srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def parse_srt(path: Path) -> list[dict[str, object]]:
    """Read a simple SRT into the segment shape used by Whisper output."""
    timestamp_pattern = re.compile(
        r"(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}),(?P<ms>\d{3})"
    )

    def seconds(value: str) -> float:
        match = timestamp_pattern.fullmatch(value)
        if not match:
            raise ValueError(f"Invalid SRT timestamp: {value}")
        return (
            int(match["h"]) * 3600
            + int(match["m"]) * 60
            + int(match["s"])
            + int(match["ms"]) / 1000
        )

    segments: list[dict[str, object]] = []
    for block in re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8").strip()):
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        start_text, end_text = lines[1].split(" --> ")
        segments.append(
            {
                "id": len(segments),
                "start": seconds(start_text),
                "end": seconds(end_text),
                "text": " ".join(lines[2:]).strip(),
                "words": [],
            }
        )
    return segments


def retime_reviewed_words(
    raw_words: list[dict[str, object]], reviewed_text: str
) -> list[dict[str, object]]:
    """Transfer raw ASR timing onto a human-reviewed transcript.

    Exact token matches retain their measured word times.  Human corrections
    are interpolated only across the raw span they replace and are explicitly
    marked approximate.
    """
    reviewed_tokens = reviewed_text.split()

    def normalized(token: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", token.lower())

    raw_tokens = [normalized(str(word["word"])) for word in raw_words]
    target_tokens = [normalized(token) for token in reviewed_tokens]
    matcher = difflib.SequenceMatcher(a=raw_tokens, b=target_tokens, autojunk=False)
    result: list[dict[str, object]] = []

    def allocate(tokens: list[str], start: float, end: float) -> list[dict[str, object]]:
        if not tokens:
            return []
        span = max(0.001, end - start)
        weights = [max(1, len(normalized(token))) for token in tokens]
        total = sum(weights)
        cursor = start
        allocated: list[dict[str, object]] = []
        for index, (token, weight) in enumerate(zip(tokens, weights)):
            token_end = end if index == len(tokens) - 1 else cursor + span * weight / total
            allocated.append(
                {
                    "word": ("" if not result and index == 0 else " ") + token,
                    "start": round(cursor, 3),
                    "end": round(token_end, 3),
                    "probability": None,
                    "reviewed_timing": "approximate",
                }
            )
            cursor = token_end
            span = max(0.001, end - cursor)
            total -= weight
        return allocated

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for raw_word, token in zip(raw_words[i1:i2], reviewed_tokens[j1:j2]):
                preserved = dict(raw_word)
                preserved["word"] = ("" if not result else " ") + token
                result.append(preserved)
            continue
        if tag == "delete":
            continue
        if i1 < i2:
            start = float(raw_words[i1]["start"])
            end = float(raw_words[i2 - 1]["end"])
        else:
            start = float(raw_words[i1 - 1]["end"]) if i1 else 0.0
            end = float(raw_words[i1]["start"]) if i1 < len(raw_words) else start + 0.001
        result.extend(allocate(reviewed_tokens[j1:j2], start, end))
    return result


def transcribe(section: str, model_name: str = "base.en") -> Path:
    import torch
    import whisper

    master_path = AUDIO_ROOT / "masters" / f"{section}.wav"
    if not master_path.exists():
        raise FileNotFoundError(f"Assemble the section first: {master_path}")

    model = whisper.load_model(model_name)
    result = model.transcribe(
        str(master_path),
        language="en",
        word_timestamps=True,
        fp16=torch.cuda.is_available(),
        condition_on_previous_text=True,
        initial_prompt=(
            "Dynamic programming lesson. Fibonacci numbers, recursive function f of n, "
            "recursion tree, child calls, and base cases."
        ),
    )

    segments: list[dict[str, object]] = []
    all_words: list[dict[str, object]] = []
    for segment in result.get("segments", []):
        words = [
            {
                "word": word["word"],
                "start": round(float(word["start"]), 3),
                "end": round(float(word["end"]), 3),
                "probability": round(float(word.get("probability", 0.0)), 4),
            }
            for word in segment.get("words", [])
        ]
        all_words.extend(words)
        segments.append(
            {
                "id": int(segment["id"]),
                "start": round(float(segment["start"]), 3),
                "end": round(float(segment["end"]), 3),
                "text": segment["text"].strip(),
                "words": words,
            }
        )

    document = {
        "section": section,
        "audio": master_path.relative_to(ROOT).as_posix(),
        "model": model_name,
        "language": result.get("language", "en"),
        "text": result.get("text", "").strip(),
        "segments": segments,
        "words": all_words,
    }
    alignment_dir = AUDIO_ROOT / "alignment"
    raw_json_path = alignment_dir / f"{section}.words.raw.json"
    raw_json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    json_path = alignment_dir / f"{section}.words.json"
    # Keep human corrections stable when transcription is rerun.  The raw
    # file above always records the latest model output for comparison.
    create_review_copy = not json_path.exists()
    if create_review_copy:
        json_path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    (alignment_dir / f"{section}.raw.txt").write_text(document["text"] + "\n", encoding="utf-8")

    srt_blocks = [
        f"{index}\n{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}\n"
        f"{segment['text']}"
        for index, segment in enumerate(segments, start=1)
    ]
    (alignment_dir / f"{section}.raw.srt").write_text(
        "\n\n".join(srt_blocks) + "\n", encoding="utf-8"
    )
    if create_review_copy:
        (alignment_dir / f"{section}.txt").write_text(
            document["text"] + "\n", encoding="utf-8"
        )
        (alignment_dir / f"{section}.srt").write_text(
            "\n\n".join(srt_blocks) + "\n", encoding="utf-8"
        )
    return json_path


def review_transcript(section: str) -> Path:
    """Promote the latest raw alignment with small, reproducible corrections.

    Whisper output remains untouched.  A compact review manifest can correct
    caption text and replace a mistranscribed word span while retaining the
    surrounding timing data.  Replacement word timings are approximate inside
    their declared span, which is recorded in the reviewed document.
    """
    alignment_dir = AUDIO_ROOT / "alignment"
    raw_path = alignment_dir / f"{section}.words.raw.json"
    review_path = alignment_dir / f"{section}.review.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Transcribe the section first: {raw_path}")
    if not review_path.exists():
        raise FileNotFoundError(f"Create a review manifest first: {review_path}")

    document = json.loads(raw_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    mode = review.get("mode")
    if mode is not None:
        if mode != "preserved_prefix_asr_extension_v1":
            raise ValueError(f"Unsupported transcript review mode: {mode}")
        from preserved_prefix_review import regenerate
        return regenerate(section, ROOT, raw_path, review_path, review)

    reviewed = copy.deepcopy(document)

    reviewed_txt_path = alignment_dir / f"{section}.txt"
    reviewed_srt_path = alignment_dir / f"{section}.srt"
    preserved_text = (
        reviewed_txt_path.read_text(encoding="utf-8").strip()
        if review.get("use_existing_reviewed_text") and reviewed_txt_path.exists()
        else None
    )
    preserved_segments = (
        parse_srt(reviewed_srt_path)
        if review.get("use_existing_reviewed_srt") and reviewed_srt_path.exists()
        else None
    )

    segment_text = {
        int(segment_id): text
        for segment_id, text in review.get("segment_text", {}).items()
    }
    for segment in reviewed["segments"]:
        if int(segment["id"]) in segment_text:
            segment["text"] = segment_text[int(segment["id"])]

    words = reviewed["words"]
    for replacement in sorted(
        review.get("word_spans", []), key=lambda item: float(item["start"]), reverse=True
    ):
        start = float(replacement["start"])
        end = float(replacement["end"])
        first = next(
            (index for index, word in enumerate(words) if float(word["start"]) >= start - 1e-6),
            None,
        )
        last = next(
            (
                index
                for index in range(len(words) - 1, -1, -1)
                if float(words[index]["end"]) <= end + 1e-6
            ),
            None,
        )
        if first is None or last is None or last < first:
            raise ValueError(f"No words found in reviewed span {start:.3f}-{end:.3f}")

        replacement_words = list(replacement["words"])
        weights = [max(1, len(word.strip(" .,!?"))) for word in replacement_words]
        total_weight = sum(weights)
        cursor = start
        corrected_words: list[dict[str, object]] = []
        for index, (word, weight) in enumerate(zip(replacement_words, weights)):
            word_end = end if index == len(replacement_words) - 1 else (
                cursor + (end - start) * weight / total_weight
            )
            corrected_words.append(
                {
                    "word": word,
                    "start": round(cursor, 3),
                    "end": round(word_end, 3),
                    "probability": None,
                    "reviewed_timing": "approximate",
                }
            )
            cursor = word_end
            total_weight -= weight
            start = cursor
        words[first : last + 1] = corrected_words

    if preserved_text is not None and review.get("retime_words_to_reviewed_text"):
        words = retime_reviewed_words(words, preserved_text)
        reviewed["words"] = words

    if preserved_segments is not None:
        reviewed["segments"] = preserved_segments

    # Reattach the corrected word stream to each original Whisper segment.
    for segment in reviewed["segments"]:
        segment["words"] = [
            word
            for word in words
            if float(word["start"]) >= float(segment["start"]) - 1e-6
            and float(word["end"]) <= float(segment["end"]) + 1e-6
        ]

    reviewed["text"] = preserved_text or " ".join(
        segment["text"].strip() for segment in reviewed["segments"]
    )
    reviewed["reviewed"] = True
    reviewed["review_source"] = review_path.relative_to(ROOT).as_posix()
    reviewed["review_notes"] = review.get("notes", [])

    reviewed_json_path = alignment_dir / f"{section}.words.json"
    reviewed_json_path.write_text(
        json.dumps(reviewed, indent=2) + "\n", encoding="utf-8"
    )
    (alignment_dir / f"{section}.txt").write_text(
        reviewed["text"] + "\n", encoding="utf-8"
    )
    srt_blocks = [
        f"{index}\n{srt_timestamp(segment['start'])} --> {srt_timestamp(segment['end'])}\n"
        f"{segment['text']}"
        for index, segment in enumerate(reviewed["segments"], start=1)
    ]
    (alignment_dir / f"{section}.srt").write_text(
        "\n\n".join(srt_blocks) + "\n", encoding="utf-8"
    )
    return reviewed_json_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("assemble", "transcribe", "review", "retime", "all")
    )
    parser.add_argument("section")
    parser.add_argument("--model", default="base.en")
    parser.add_argument(
        "--previous-assembly",
        type=Path,
        help="Assembly JSON from before a pause-only pacing change.",
    )
    args = parser.parse_args()

    if args.action in {"assemble", "all"}:
        master = assemble(args.section)
        print(f"assembled: {master}")
    if args.action in {"transcribe", "all"}:
        transcript = transcribe(args.section, args.model)
        print(f"transcribed: {transcript}")
    if args.action == "review":
        transcript = review_transcript(args.section)
        print(f"reviewed: {transcript}")
    if args.action == "retime":
        if args.previous_assembly is None:
            parser.error("retime requires --previous-assembly")
        retime_for_pacing(args.section, args.previous_assembly)
        print(f"retimed: {args.section}")


if __name__ == "__main__":
    main()
