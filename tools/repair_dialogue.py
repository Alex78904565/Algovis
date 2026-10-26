"""Apply reproducible click and verified-pause repairs without moving narration.

The manifest names an immutable input copy and its hash. Never recursively
process an already repaired output, change raw takes, or infer silence solely
from a transcript. All pause ranges require independent speech protection.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

try:
    from .master_dialogue import attenuate_verified_pauses
except ImportError:
    from master_dialogue import attenuate_verified_pauses

ROOT = Path(__file__).resolve().parents[1]


def repair_isolated_impulses(samples: np.ndarray, rate: int, times: list[float]) -> np.ndarray:
    """Interpolate single-sample outliers without silencing nearby word tails."""
    from scipy.signal import medfilt
    output = samples.copy()
    radius = round(.003 * rate)
    for time in times:
        center = round(time * rate)
        lo,hi = max(0,center-radius),min(len(output),center+radius)
        if hi-lo < 9:
            continue
        segment=output[lo:hi]
        baseline=medfilt(segment,7)
        mask=np.abs(segment-baseline)>.003
        mask[:3]=False
        mask[-3:]=False
        segment[mask]=baseline[mask]
    return output


def repair(entry: dict, destination: Path) -> dict:
    source = ROOT / entry['source']
    if hashlib.sha256(source.read_bytes()).hexdigest() != entry['sourceHash']:
        raise ValueError(f"Repair input has changed: {source}")
    rate, original = wavfile.read(source)
    if rate != 48000 or original.ndim != 1 or original.dtype != np.int16:
        raise ValueError('Expected the existing mono 48 kHz PCM16 dialogue master')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.repair-') as directory:
        filtered = Path(directory) / 'declicked.wav'
        command = ['ffmpeg', '-hide_banner', '-nostats', '-y', '-i', str(source),
                   '-af', 'adeclick=w=30:o=75:t=8:b=2', '-c:a', 'pcm_f32le', str(filtered)]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        out_rate, samples = wavfile.read(filtered)
        if out_rate != rate or samples.shape != original.shape:
            raise RuntimeError('Click repair changed the narration timeline')
        intervals = [(float(gap['start']), float(gap['end'])) for gap in entry['pauses']]
        protected = entry.get('protectedSpeech', [])
        if any(max(a, p) < min(b, q) for a,b in intervals for p,q in protected):
            raise ValueError('A pause repair intersects protected speech')
        samples = attenuate_verified_pauses(
            samples, rate, intervals, reduction_db=24, ramp_seconds=.010,
        )
        samples = repair_isolated_impulses(samples, rate, entry.get('impulses', []))
        if not np.isfinite(samples).all() or np.max(np.abs(samples)) >= 1:
            raise RuntimeError('Repair produced invalid or overloaded audio')
        before = original.astype(np.float32)/32768
        difference = samples-before
        # This check detects a delay accidentally introduced by a filter or a
        # conversion. Impulse repairs may change individual samples, but never
        # shift the intact speech in three representative windows.
        from scipy.signal import correlate
        for fraction in (.1, .5, .85):
            start = int(len(before)*fraction)
            x,y = before[start:start+24000], samples[start:start+24000]
            correlation = correlate(y,x,method='fft')
            lag = int(np.argmax(correlation)-(len(x)-1))
            if abs(lag) > 1:
                raise RuntimeError(f'Unexpected narration shift: {lag} samples')
        pcm = np.rint(samples*32768).astype(np.int16)
        temporary = Path(directory)/'repaired.wav'
        wavfile.write(temporary, rate, pcm)
        os.replace(temporary, destination)
    return {'section':entry['section'], 'sourceHash':entry['sourceHash'],
            'outputHash':hashlib.sha256(destination.read_bytes()).hexdigest(),
            'samples':len(pcm),'rate':rate,'timingShiftSamples':0,
            'pauseRepairs':len(intervals),
            'isolatedImpulseLocations':entry.get('impulses', []),
            'changedSamplesAbove0002':int(np.count_nonzero(np.abs(difference)>.002)),
            'totalSamples':len(pcm),
            'filterReport':[line for line in result.stderr.splitlines() if 'Detected clicks' in line]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
    def create(entry):
        return repair(entry,args.output_dir/(entry['section']+'_dialogue.wav'))
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(create,manifest['sections']))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(results,indent=2),encoding='utf-8')
    for result in results:
        print(result['section'],result['pauseRepairs'],'pause repairs;',
              '; '.join(result['filterReport']),flush=True)


if __name__=='__main__':
    main()
