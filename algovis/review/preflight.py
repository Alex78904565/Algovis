"""Stable preflight identities and evidence scoped to the flagged moment.

File names, source line numbers, and unrelated section edits are not evidence
that an approved moment changed. Decode its actual video interval instead.
Unavailable media fails conservatively to a content hash of the whole asset.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

from .audit import timed_words


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def legacy_id(issue):
    return digest({key: issue.get(key) for key in
                   ('severity', 'category', 'message', 'location', 'cue', 'time')})[:20]


def finding_id(issue):
    # Counts and source line numbers are diagnostics, not the identity of a rule.
    message = issue.get('message', '')
    rule = issue.get('code')
    if not rule and re.search(r'\d+ visual changes for one phrase$', message):
        rule = 'visual_density'
    if not rule and 'active beats are only' in message:
        rule = 'rapid_beats'
    identity = {'category': issue.get('category'), 'rule': rule or message,
                'cue': issue.get('cue')}
    if not issue.get('cue'):
        identity['scope'] = re.sub(r':\d+$', '', issue.get('location', ''))
    return digest(identity)[:20]


def store_decision(reviews, identifier, decision):
    previous = reviews.get(identifier, {})
    history = list(previous.get('history', []))
    if previous and (previous.get('status'), previous.get('evidenceVersion')) != (
            decision.get('status'), decision.get('evidenceVersion')):
        history.append({key: value for key, value in previous.items() if key != 'history'})
    reviews[identifier] = {**decision, 'history': history}


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding='utf-8')) if path else default
    except (OSError, ValueError):
        return default


def file_key(path):
    try:
        stat = path.stat()
        return (str(path), stat.st_mtime_ns, stat.st_size)
    except (OSError, AttributeError):
        return None


def file_digest(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, AttributeError):
        return None


def interval_digest(path, start, end, *, audio=False):
    """Hash all decoded frames/samples of this interval, ignoring MP4 metadata."""
    if not path or not path.is_file():
        return {'mode': 'missing', 'hash': None}
    command = ['ffmpeg', '-v', 'error', '-ss', f'{start:.6f}', '-i', str(path),
               '-t', f'{end-start:.6f}', '-map', '0:a:0' if audio else '0:v:0']
    command += (['-vn', '-af', 'asetpts=PTS-STARTPTS', '-f', 's16le', '-'] if audio else
                ['-an', '-vf', 'setpts=PTS-STARTPTS', '-f', 'framemd5', '-'])
    try:
        result = subprocess.run(command, capture_output=True, timeout=30)
        if result.returncode or not result.stdout:
            raise ValueError('Media interval could not be decoded')
        if audio:
            content = result.stdout
        else:
            # Metadata comments may mention container/encoder versions. Keep
            # dimensions and every frame's relative timing, duration and pixels.
            content = b'\n'.join(line for line in result.stdout.splitlines()
                                  if not line.startswith(b'#') or line.startswith(b'#dimensions'))
            if not any(line and not line.startswith(b'#') for line in content.splitlines()):
                raise ValueError('No decoded video frames')
        return {'mode': 'decoded_audio' if audio else 'decoded_video',
                'hash': hashlib.sha256(content).hexdigest()}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        # Never retain a decision based on an empty/failed decode.
        return {'mode': 'whole_asset_fallback', 'hash': file_digest(path)}


def finding_evidence(review, issue, cache):
    """Return a stable local evidence version and its inspectable inputs."""
    category = issue.get('category')
    music = review.music_settings() if category == 'audio' and review.music_path else None
    key = (finding_id(issue), issue.get('severity'), issue.get('time'), file_key(review.video_path),
           file_key(review.cue_path), file_key(review.transcript_path),
           file_key(review.manifest_path), file_key(review.music_path) if music else None,
           json.dumps(music, sort_keys=True))
    if key in cache:
        return cache[key]
    data = read_json(review.cue_path, {})
    cues = sorted(data.get('cues', []), key=lambda cue: float(cue['time']))
    cue = next((c for c in cues if c.get('name') == issue.get('cue')), None)
    manifest = read_json(review.manifest_path, {})
    fps = float(manifest.get('frameRate', 15)) or 15
    duration = float(data.get('duration', 0))
    start = float(cue['time']) if cue else float(issue.get('time') or 0)
    next_cue = next((c for c in cues if float(c['time']) > start + 1e-6), None)
    end = float(next_cue['time']) if cue and next_cue else duration
    # Include the entire related animation, even if it runs beyond the next cue.
    ends = [float(a.get('end', start)) for a in manifest.get('animations', [])
            if a.get('cue') == issue.get('cue') and issue.get('cue')]
    end = max([end, *ends])
    scoped = cue is not None and duration > 0 and end > start
    before = max(0, round(start * fps) / fps - 1 / fps) if scoped else 0
    after = min(duration, round(end * fps) / fps) if scoped else duration
    words = timed_words(read_json(review.transcript_path, {}))
    local_words = [{'word': w['word'], 'start': round(w['start']-start, 4),
                    'end': round(w['end']-start, 4)} for w in words
                   if scoped and w['end'] >= before and w['start'] < after]
    content = {'schema': 1, 'rule': finding_id(issue), 'severity': issue.get('severity'),
               'phrase': cue.get('phrase') if cue else None, 'words': local_words,
               'duration': round(after-before, 6),
               'video': interval_digest(review.video_path, before, after) if scoped else
                        {'mode': 'whole_asset', 'hash': file_digest(review.video_path)}}
    if category in {'timing', 'audio'}:
        content['speech'] = interval_digest(review.video_path, before, after, audio=True) if scoped else file_digest(review.video_path)
    if category == 'audio':
        # Soundtrack balance can affect the whole listening context. Visual-only
        # checks deliberately do not depend on music or its mix settings.
        content['music'] = {'hash': file_digest(review.music_path), 'mix': music}
    result = {'version': digest(content), 'scope': 'moment' if scoped else 'section',
              'start': before, 'end': after, 'inputs': content}
    cache[key] = result
    return result
