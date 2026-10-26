"""Create a clean, consistently leveled dialogue master without changing timing.

The source WAV is never modified.  Processing is intentionally conservative:
handling rumble and intermittent room noise are reduced first, speech dynamics
are gently evened out, and an EBU R128 pass sets a predictable final loudness.
The output must contain exactly the same number of samples as the input so that
all animation cues remain valid.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

try:
    from .audio_pipeline import clean_narration_noise, read_wav, write_pcm16
except ImportError:  # Direct execution: python tools/master_dialogue.py
    from audio_pipeline import clean_narration_noise, read_wav, write_pcm16


LOUDNORM_JSON = re.compile(r"\{\s*\"input_i\".*?\}", re.DOTALL)


def wav_shape(path: Path) -> tuple[int, int, int]:
    with wave.open(str(path), "rb") as source:
        return source.getframerate(), source.getnchannels(), source.getnframes()


def run_ffmpeg(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr)
    return result


def soften_digital_silence_edges(
    samples: np.ndarray,
    rate: int,
    *,
    minimum_seconds: float = 0.03,
    fade_seconds: float = 0.012,
) -> tuple[np.ndarray, int]:
    """Fade into and out of exact-zero gaps left by an internal audio edit.

    A stitched source take may contain a digital-silence island whose edge
    jumps directly from room tone to zero.  The pause itself is useful and its
    duration must not change; a short raised-cosine fade on either side removes
    the click or thud while preserving the timeline exactly.
    """
    zero = samples == 0.0
    changes = np.diff(np.pad(zero.astype(np.int8), (1, 1)))
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    minimum = round(minimum_seconds * rate)
    fade = round(fade_seconds * rate)
    softened = samples.astype(np.float32, copy=True)
    count = 0
    for start, end in zip(starts, ends):
        if end - start < minimum:
            continue
        left = min(fade, start)
        right = min(fade, len(softened) - end)
        if left:
            phase = np.linspace(0.0, np.pi / 2.0, left, endpoint=True)
            softened[start - left:start] *= np.cos(phase) ** 2
        if right:
            phase = np.linspace(0.0, np.pi / 2.0, right, endpoint=True)
            softened[end:end + right] *= np.sin(phase) ** 2
        count += 1
    return softened, count


def attenuate_verified_pauses(
    samples: np.ndarray,
    rate: int,
    intervals: list[tuple[float, float]],
    *,
    reduction_db: float = 18.0,
    ramp_seconds: float = 0.04,
) -> np.ndarray:
    """Reduce handling noise only in independently verified non-speech gaps.

    Callers must exclude both detected speech and transcript word intervals.
    Raised-cosine ramps stay inside each gap; samples outside the gaps are
    bit-identical and the sample count (hence every animation cue) is unchanged.
    """
    output = samples.copy()
    floor = 10 ** (-reduction_db / 20)
    previous_end = 0
    for start_seconds, end_seconds in sorted(intervals):
        start, end = round(start_seconds * rate), round(end_seconds * rate)
        if start < previous_end or start < 0 or end > len(output) or end <= start:
            raise ValueError("Pause intervals must be disjoint and inside the audio")
        previous_end = end
        length = end - start
        ramp = min(round(ramp_seconds * rate), length // 2)
        gain = np.full(length, floor)
        if ramp:
            phase = np.linspace(0, np.pi, ramp)
            edge = floor + (1 - floor) * (1 + np.cos(phase)) / 2
            gain[:ramp] = edge
            gain[-ramp:] = edge[::-1]
        if output.ndim > 1:
            gain = gain[:, None]
        adjusted = output[start:end] * gain
        if np.issubdtype(output.dtype, np.integer):
            adjusted = np.rint(adjusted)
        output[start:end] = adjusted
    return output


def loudnorm_measurement(
    source: Path,
    speech_filter: str,
    integrated_lufs: float,
    true_peak_db: float,
    loudness_range: float,
) -> dict[str, str]:
    measure_filter = (
        f"{speech_filter},"
        f"loudnorm=I={integrated_lufs}:TP={true_peak_db}:LRA={loudness_range}:"
        "print_format=json"
    )
    result = run_ffmpeg(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(source),
            "-af",
            measure_filter,
            "-f",
            "null",
            "-",
        ]
    )
    matches = LOUDNORM_JSON.findall(result.stderr)
    if not matches:
        raise RuntimeError("FFmpeg did not return loudnorm measurements")
    return json.loads(matches[-1])


def master_dialogue(
    source: Path,
    output: Path,
    *,
    integrated_lufs: float = -18.0,
    true_peak_db: float = -1.5,
    loudness_range: float = 5.0,
    noise_reduction: float = 0.48,
    highpass_hz: float = 70.0,
    deesser_intensity: float = 0.24,
    deesser_max: float = 0.40,
    deesser_frequency: float = 0.50,
) -> dict[str, object]:
    source_audio = read_wav(source)
    if source_audio.rate != 48_000:
        raise ValueError(f"Expected 48 kHz source audio, got {source_audio.rate} Hz")

    seam_smoothed, seams_softened = soften_digital_silence_edges(
        source_audio.samples, source_audio.rate,
    )
    cleaned = clean_narration_noise(
        seam_smoothed,
        source_audio.rate,
        {
            "declick_quiet_impulses": True,
            "declick_threshold": 0.065,
            "declick_quiet_rms": 0.035,
            "declick_expand_samples": 3,
            "highpass_hz": highpass_hz,
            "prop_decrease": noise_reduction,
            "time_constant_s": 0.55,
            "freq_mask_smooth_hz": 450,
            "time_mask_smooth_ms": 80,
            "threshold_multiplier": 1.5,
            "sigmoid_slope": 8.0,
            "match_loudness": True,
        },
    )

    # A slow expansion curve evens out independently recorded phrases without
    # flattening ordinary sentence emphasis.  Noise reduction runs first so
    # quiet cloth movement is not raised along with the voice.
    # Tame sibilance before dynamics processing.  Keeping the intensity and
    # maximum reduction conservative avoids turning ordinary consonants dull
    # or lispy while preventing the later loudness pass from exaggerating S/T
    # transients.
    speech_filter = (
        f"deesser=i={deesser_intensity}:m={deesser_max}:f={deesser_frequency},"
        "speechnorm=e=2:r=0.00001:f=0.00003:l=1"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix=".algovis-dialogue-",
        dir=output.parent,
    ) as temporary:
        temporary_root = Path(temporary)
        cleaned_path = temporary_root / "cleaned.wav"
        write_pcm16(cleaned_path, cleaned, source_audio.rate)
        measured = loudnorm_measurement(
            cleaned_path,
            speech_filter,
            integrated_lufs,
            true_peak_db,
            loudness_range,
        )
        final_filter = (
            f"{speech_filter},"
            f"loudnorm=I={integrated_lufs}:TP={true_peak_db}:LRA={loudness_range}:"
            f"measured_I={measured['input_i']}:"
            f"measured_LRA={measured['input_lra']}:"
            f"measured_TP={measured['input_tp']}:"
            f"measured_thresh={measured['input_thresh']}:"
            f"offset={measured['target_offset']}:linear=true:print_format=json,"
            "aresample=48000"
        )
        render = run_ffmpeg(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-y",
                "-i",
                str(cleaned_path),
                "-af",
                final_filter,
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output),
            ]
        )
        final_matches = LOUDNORM_JSON.findall(render.stderr)
        final_stats = json.loads(final_matches[-1]) if final_matches else {}

    source_shape = wav_shape(source)
    output_shape = wav_shape(output)
    if source_shape != output_shape:
        output.unlink(missing_ok=True)
        raise RuntimeError(
            "Dialogue mastering changed the timeline: "
            f"source={source_shape}, output={output_shape}"
        )

    return {
        "source": str(source),
        "output": str(output),
        "sample_rate": output_shape[0],
        "channels": output_shape[1],
        "samples": output_shape[2],
        "duration": output_shape[2] / output_shape[0],
        "noise_reduction": noise_reduction,
        "digital_silence_seams_softened": seams_softened,
        "highpass_hz": highpass_hz,
        "deesser_intensity": deesser_intensity,
        "deesser_max": deesser_max,
        "deesser_frequency": deesser_frequency,
        "speech_filter": speech_filter,
        "target_lufs": integrated_lufs,
        "target_true_peak_db": true_peak_db,
        "target_lra": loudness_range,
        "measurement": measured,
        "final": final_stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--target-lufs", type=float, default=-18.0)
    parser.add_argument("--true-peak", type=float, default=-1.5)
    parser.add_argument("--lra", type=float, default=5.0)
    parser.add_argument("--noise-reduction", type=float, default=0.48)
    parser.add_argument("--highpass", type=float, default=70.0)
    parser.add_argument("--deesser-intensity", type=float, default=0.24)
    parser.add_argument("--deesser-max", type=float, default=0.40)
    parser.add_argument("--deesser-frequency", type=float, default=0.50)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    report = master_dialogue(
        args.source,
        args.output,
        integrated_lufs=args.target_lufs,
        true_peak_db=args.true_peak,
        loudness_range=args.lra,
        noise_reduction=args.noise_reduction,
        highpass_hz=args.highpass,
        deesser_intensity=args.deesser_intensity,
        deesser_max=args.deesser_max,
        deesser_frequency=args.deesser_frequency,
    )
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
