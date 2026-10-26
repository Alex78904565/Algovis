"""Serve a real Manim render with transcript-anchored visual annotations.

The review server is intentionally local-only.  It displays an existing Manim
video, records normalized point/rectangle annotations beside the project, and
can rerender one configured scene after a source edit.
"""

from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, quote, urlparse
import uuid

from .transitions import build_transition_index


MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_COMMENT_LENGTH = 4_000


class ReviewHTTPServer(ThreadingHTTPServer):
    """One preview process owns a port, including on Windows.

    Windows SO_REUSEADDR can let two live HTTP servers bind the same port.
    Browsers then receive inconsistent revisions depending on the connection.
    """

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.allow_reuse_address = False
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        return super().server_bind()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"Path leaves the review workspace: {resolved}") from exc
    return resolved


@dataclass
class RenderStatus:
    state: str = "idle"
    message: str = "Ready"
    started_at: str | None = None
    completed_at: str | None = None
    log_tail: str = ""


@dataclass
class ReviewServer:
    workspace: Path
    section_id: str
    section_title: str
    video_path: Path
    cue_path: Path
    transcript_path: Path | None = None
    scene_name: str = ""
    scene_source: Path | None = None
    audio_path: Path | None = None
    music_path: Path | None = None
    music_title: str = ""
    music_gain_db: float = -12.0
    music_offset_seconds: float = 0.0
    duck_threshold: float = 0.018
    duck_ratio: float = 3.5
    duck_attack_ms: float = 350.0
    duck_release_ms: float = 1800.0
    rendered_video_path: Path | None = None
    manifest_path: Path | None = None
    quality: str = "l"
    watch_paths: tuple[Path, ...] = ()
    static_path: Path = field(
        default_factory=lambda: Path(__file__).with_name("static") / "index.html"
    )
    token: str = field(default_factory=lambda: secrets.token_urlsafe(18))

    def __post_init__(self) -> None:
        self.workspace = self.workspace.resolve()
        self.video_path = _inside(self.workspace, self.video_path)
        self.base_video_path = self.video_path
        self.cue_path = _inside(self.workspace, self.cue_path)
        if self.scene_source is not None:
            self.scene_source = _inside(self.workspace, self.scene_source)
        if self.transcript_path is not None:
            self.transcript_path = _inside(self.workspace, self.transcript_path)
        if self.audio_path is not None:
            self.audio_path = _inside(self.workspace, self.audio_path)
        if self.music_path is not None:
            self.music_path = _inside(self.workspace, self.music_path)
        if self.rendered_video_path is not None:
            self.rendered_video_path = _inside(
                self.workspace, self.rendered_video_path,
            )
        self.watch_paths = tuple(
            _inside(self.workspace, path) for path in self.watch_paths
        )
        self.review_dir = (
            self.workspace / ".review" / "annotations" / self.section_id
        )
        self.published_dir = (
            self.workspace / ".review" / "renders" / self.section_id
        )
        self.published_dir.mkdir(parents=True, exist_ok=True)
        published = sorted(
            (path for path in self.published_dir.glob("*.mp4")
             if not path.name.endswith(".tmp.mp4")),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        if published and (
            not self.base_video_path.exists()
            or published[0].stat().st_mtime_ns
            >= self.base_video_path.stat().st_mtime_ns
        ):
            self.video_path = published[0]
        if self.manifest_path is None:
            self.manifest_path = (
                self.workspace / ".review" / "manifests"
                / f"{self.section_id}.objects.json"
            )
        else:
            self.manifest_path = _inside(self.workspace, self.manifest_path)
        self.assets_dir = self.review_dir / "assets"
        self.annotations_path = self.review_dir / "annotations.json"
        self.pending_path = self.review_dir / "PENDING.md"
        self.music_settings_path = self.review_dir / "music.json"
        self.approval_path = self.review_dir / "approval.json"
        self.finding_reviews_path = self.review_dir / "preflight-reviews.json"
        self.review_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        if not self.annotations_path.exists():
            _atomic_json(self.annotations_path, [])
        self._lock = threading.RLock()
        self._render_lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._transition_cache_key = None
        self._transition_cache = []
        self._render_requested = False
        self.render_status = RenderStatus()
        self.revision = self._video_revision()
        self._watch_snapshot = self._watch_mtimes()

    @property
    def cues(self) -> list[dict]:
        data = json.loads(self.cue_path.read_text(encoding="utf-8"))
        return list(data.get("cues", ()))

    def _video_revision(self) -> int:
        try:
            return self.video_path.stat().st_mtime_ns
        except FileNotFoundError:
            return 0

    def _watch_mtimes(self) -> dict[str, int]:
        values = {}
        for path in self.watch_paths:
            candidates = [path]
            if path.is_dir():
                candidates = [
                    child for child in path.rglob("*.py")
                    if "__pycache__" not in child.parts
                    and "review" not in child.parts
                ]
            for candidate in candidates:
                try:
                    values[str(candidate)] = candidate.stat().st_mtime_ns
                except FileNotFoundError:
                    values[str(candidate)] = 0
        return values

    def annotations(self) -> list[dict]:
        with self._lock:
            try:
                return json.loads(
                    self.annotations_path.read_text(encoding="utf-8")
                )
            except (FileNotFoundError, json.JSONDecodeError):
                return []

    def project_payload(self) -> dict:
        duration = 0.0
        cue_data = json.loads(self.cue_path.read_text(encoding="utf-8"))
        duration = float(cue_data.get("duration", 0.0))
        with self._lock:
            status = self.render_status.__dict__.copy()
        music = None
        if self.music_path is not None:
            settings = self.music_settings()
            music = {
                "title": self.music_title or self.music_path.stem,
                "url": (
                    f"/music?token={self.token}"
                    f"&section={quote(self.section_id)}"
                    f"&revision={self.music_path.stat().st_mtime_ns}"
                ),
                **settings,
                "duck": {
                    "threshold": self.duck_threshold,
                    "ratio": self.duck_ratio,
                    "attackMs": self.duck_attack_ms,
                    "releaseMs": self.duck_release_ms,
                },
                "notice": "Private editorial audition; license before publication.",
            }
        manifest = self.object_manifest()
        return {
            "section": {
                "id": self.section_id,
                "title": self.section_title,
                "scene": self.scene_name,
                "duration": duration,
            },
            "cues": cue_data.get("cues", []),
            "transcript": self.transcript_payload(cue_data.get("cues", [])),
            "videoUrl": (
                f"/video?token={self.token}&revision={self.revision}"
                f"&section={quote(self.section_id)}"
            ),
            "revision": self.revision,
            "render": status,
            "annotations": self.annotations(),
            "music": music,
            "objects": manifest,
            "audit": self.audit_payload(),
            "transitions": self.transitions_payload(manifest),
            "approval": self.approval_payload(),
        }

    def _review_version(self, annotations: list[dict]) -> str:
        """Identify the exact video, soundtrack, and feedback being reviewed."""
        def asset(path):
            if path is None:
                return None
            try:
                stat = path.stat()
            except FileNotFoundError:
                return None
            return [str(path.relative_to(self.workspace)), str(stat.st_mtime_ns), stat.st_size]

        version = {
            "video": asset(self.video_path),
            "cues": asset(self.cue_path),
            "transcript": asset(self.transcript_path),
            "music": asset(self.music_path),
            "mix": self.music_settings() if self.music_path else None,
            "duck": [self.duck_threshold, self.duck_ratio,
                     self.duck_attack_ms, self.duck_release_ms],
            "annotations": annotations,
        }
        return hashlib.sha256(json.dumps(version, sort_keys=True).encode("utf-8")).hexdigest()

    def approval_payload(self) -> dict:
        with self._lock:
            annotations = self.annotations()
            version = self._review_version(annotations)
            try:
                saved = json.loads(self.approval_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                saved = {}
            open_notes = sum(item.get("status") != "resolved" for item in annotations)
            approved = saved.get("approved") is True and saved.get("version") == version and not open_notes
            status = "approved" if approved else "needs_review" if saved else "not_reviewed"
            if open_notes:
                message = f"Resolve {open_notes} open note{'s' if open_notes != 1 else ''} before approving."
            elif self.render_status.state == "rendering":
                message = "An updated preview is rendering. Review it before approving."
            elif approved:
                message = "You approved this version. You can still review any section."
            elif saved.get("approved"):
                message = "This section changed since approval. Review the updated version."
            elif saved:
                message = "Review reopened. Approve again when it looks and sounds good."
            else:
                message = "Review sections in any order. Approve only when you are happy with the lesson in context."
            return {
                "status": status,
                "version": version,
                "approvedAt": saved.get("approvedAt"),
                "canApprove": not open_notes and self.video_path.exists()
                and self.render_status.state != "rendering",
                "openNotes": open_notes,
                "message": message,
            }

    def set_approval(self, payload: dict) -> dict:
        approved = payload.get("approved")
        if not isinstance(approved, bool):
            raise ValueError("Choose whether to approve or reopen the section.")
        with self._lock:
            current = self.approval_payload()
            if approved:
                if payload.get("version") != current["version"]:
                    raise ValueError("This section changed. Review the latest version before approving.")
                if not current["canApprove"]:
                    raise ValueError(current["message"])
            _atomic_json(self.approval_path, {
                "approved": approved,
                "version": current["version"],
                "approvedAt": _utc_now() if approved else None,
                "updatedAt": _utc_now(),
            })
            return self.approval_payload()

    def audit_payload(self) -> dict | None:
        """Return the generated preflight findings for the active section."""
        path = self.workspace / ".review" / "audit.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        audit = data.get("sections", {}).get(self.section_id)
        if audit is None:
            return None
        try:
            reviews = json.loads(self.finding_reviews_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            reviews = {}
        # Reviewing one flag must not reset the rest when its change request
        # creates an annotation. Only changes to the audiovisual version do.
        version = self._review_version([])
        progress = {"pending": 0, "checked": 0, "needs_change": 0, "deferred": 0}
        for issue in audit.get("issues", []):
            identity = {key: issue.get(key) for key in (
                "severity", "category", "message", "location", "cue", "time",
            )}
            identifier = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:20]
            saved = reviews.get(identifier, {})
            status = saved.get("status", "pending") if saved.get("version") == version else "pending"
            if status not in progress:
                status = "pending"
            issue.update({
                "id": identifier,
                "reviewStatus": status,
                "reviewedAt": saved.get("reviewedAt") if status != "pending" else None,
                "annotationId": saved.get("annotationId"),
                "reviewQuestion": self._finding_question(issue),
            })
            progress[status] += 1
        audit.get("issues", []).sort(key=lambda issue: (
            issue.get("time") is None,
            float(issue.get("time") or 0.0),
        ))
        audit["reviewVersion"] = version
        audit["progress"] = progress
        # Notes change between source audits. Keep the review gate current
        # when the viewer resolves a fix or queues a follow-up.
        counts = {}
        for annotation in self.annotations():
            status = annotation.get("status", "draft")
            counts[status] = counts.get(status, 0) + 1
        audit["annotationCounts"] = counts
        severities = {
            issue.get("severity") for issue in audit.get("issues", [])
            if issue.get("reviewStatus") != "checked" or issue.get("severity") == "error"
        }
        if "error" in severities or counts.get("draft") or counts.get("pending"):
            audit["status"] = "blocked"
        elif "warning" in severities or counts.get("pending_review"):
            audit["status"] = "needs_review"
        else:
            audit["status"] = "ready"
        return audit

    @staticmethod
    def _finding_question(issue: dict) -> str:
        if issue.get("severity") == "error":
            return "This needs a technical check. Send it to Codex to investigate."
        category = issue.get("category")
        if category == "timing":
            return "Does the animation line up with the words you are saying?"
        if category in {"density", "storyboard"}:
            return "Is there enough time to follow each change, without too much happening at once?"
        if category == "color":
            return "Does this highlight use a color that makes sense here?"
        if category == "audio":
            return "Does this moment sound right, including the music?"
        return "Does this part look and sound right?"

    def review_finding(self, identifier: str, payload: dict) -> dict:
        status = payload.get("status")
        if status not in {"pending", "checked", "needs_change", "deferred"}:
            raise ValueError("Choose checked, request a change, or skip for now.")
        with self._lock:
            audit = self.audit_payload()
            if audit is None:
                raise ValueError("No preflight report is available for this section.")
            if payload.get("version") != audit["reviewVersion"]:
                raise ValueError("The preview changed. Review the latest version of this flag.")
            issue = next((item for item in audit["issues"] if item["id"] == identifier), None)
            if issue is None:
                raise ValueError("This flag is no longer in the current preflight report.")
            if status == "checked" and issue.get("severity") == "error":
                raise ValueError("This technical error needs a fix before it can be cleared.")
            try:
                reviews = json.loads(self.finding_reviews_path.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                reviews = {}
            annotation_id = issue.get("annotationId")
            if status == "needs_change":
                note = str(payload.get("note", "")).strip()
                if len(note) > 2_000:
                    raise ValueError("Keep the change request under 2,000 characters.")
                comment = f"Preflight review: {issue['reviewQuestion']}\n\n{issue['message']}"
                if issue.get("location"):
                    comment += f"\nSource: {issue['location']}"
                if note:
                    comment += f"\n\nRequested change: {note}"
                existing = next((item for item in self.annotations() if item["id"] == annotation_id), None)
                if existing is not None and existing.get("status") != "resolved":
                    if note:
                        self.add_annotation_response(annotation_id, {"author": "user", "body": note})
                    else:
                        self.set_annotation_status(annotation_id, "pending")
                else:
                    cues = sorted(self.cues, key=lambda cue: float(cue.get("time", 0.0)))
                    cue = next((cue for cue in cues if cue["name"] == issue.get("cue")), None)
                    moment = float(issue.get("time") or 0.0)
                    nearby = [cue for cue in cues if float(cue.get("time", 0.0)) <= moment]
                    cue = cue or (nearby[-1] if nearby else next(iter(cues), None))
                    if cue is None:
                        raise ValueError("The section has no narration cues for a change request.")
                    annotation = self.save_annotation({
                        "cue": cue["name"], "phrase": cue.get("phrase", ""),
                        "timestamp": moment,
                        "region": {"x": 0, "y": 0, "width": 0, "height": 0},
                        "comment": comment,
                    })
                    annotation_id = annotation["id"]
                    self.set_annotation_status(annotation_id, "pending")
            elif status == "checked" and annotation_id:
                # The viewer's explicit confirmation also closes the change
                # request created for this flag, avoiding duplicate review.
                linked = next((item for item in self.annotations() if item["id"] == annotation_id), None)
                if linked is not None and linked.get("status") != "resolved":
                    self.set_annotation_status(annotation_id, "resolved")
            reviews[identifier] = {
                "status": status, "version": audit["reviewVersion"],
                "reviewedAt": _utc_now(), "annotationId": annotation_id,
            }
            _atomic_json(self.finding_reviews_path, reviews)
            return {
                "audit": self.audit_payload(), "annotations": self.annotations(),
                "approval": self.approval_payload(),
            }

    def transitions_payload(self, manifest=None) -> list[dict]:
        if self.manifest_path is None or not self.manifest_path.exists():
            return []
        revision = self._video_revision()
        key = (
            revision, self.manifest_path.stat().st_mtime_ns,
            self.cue_path.stat().st_mtime_ns,
        )
        if key == self._transition_cache_key:
            return self._transition_cache
        if manifest is None:
            manifest = self.object_manifest()
        cue_data = json.loads(self.cue_path.read_text(encoding="utf-8"))
        fps = {"l": 15.0, "m": 30.0, "h": 60.0, "p": 60.0, "k": 60.0}[self.quality]
        transitions = build_transition_index(
            manifest, cue_data.get("cues", []),
            float(cue_data.get("duration", 0.0)), frame_rate=fps,
        )
        for transition in transitions:
            for frame in transition["frames"]:
                frame["url"] = (
                    f"/review-frame?token={self.token}&section={quote(self.section_id)}"
                    f"&revision={revision}&transition={transition['id']}"
                    f"&position={frame['position']}"
                )
        self._transition_cache = transitions
        self._transition_cache_key = key
        return transitions

    def transition_frame(self, identifier: str, position: str, revision: int) -> Path:
        """Extract a cached thumbnail from the same MP4 the viewer is playing."""
        video_path = self.video_path
        if revision != self._video_revision():
            raise ValueError("The render changed. Refresh the animation frames.")
        transition = next((
            item for item in self.transitions_payload() if item["id"] == identifier
        ), None)
        if transition is None:
            raise ValueError("Unknown animation interval")
        frame = next((
            item for item in transition["frames"] if item["position"] == position
        ), None)
        if frame is None:
            raise ValueError("Unknown frame position")
        directory = self.workspace / ".review" / "frames" / self.section_id / str(revision)
        path = directory / f"{identifier}-{position}.jpg"
        with self._frame_lock:
            if path.exists():
                return path
            completed = subprocess.run([
                "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                "-ss", f"{frame['time']:.6f}", "-i", str(video_path),
                "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "3",
                "-f", "image2pipe", "-vcodec", "mjpeg", "pipe:1",
            ], cwd=self.workspace, capture_output=True, timeout=30, check=False)
            if completed.returncode or not completed.stdout:
                raise RuntimeError("Could not read this frame from the rendered video.")
            directory.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_bytes(completed.stdout)
            os.replace(temporary, path)
        return path

    def object_manifest(self) -> dict | None:
        if self.manifest_path is None:
            return None
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def transcript_payload(self, cues: list[dict]) -> dict | None:
        if self.transcript_path is None:
            return None
        source = json.loads(self.transcript_path.read_text(encoding="utf-8"))
        words = []
        for segment_index, segment in enumerate(source.get("segments", [])):
            for word in segment.get("words", []):
                words.append({
                    "text": str(word.get("word", "")),
                    "start": float(word.get("start", 0.0)),
                    "end": float(word.get("end", word.get("start", 0.0))),
                    "segment": segment_index,
                })
        # Corrected alignment segments can overlap. Sort chronologically and
        # remove the same timed token repeated by those segments, without
        # deleting genuine repeated spoken words at different times.
        words.sort(key=lambda word: (word["start"], word["end"]))
        seen = set()
        unique_words = []
        for word in words:
            identity = (word["start"], word["end"], word["text"].strip().lower())
            if identity not in seen:
                seen.add(identity)
                unique_words.append(word)
        words = unique_words
        normalized_words = [self._tokens(word["text"]) for word in words]
        flat_words = [tokens[0] if tokens else "" for tokens in normalized_words]
        triggers = []
        for cue in cues:
            phrase_tokens = self._tokens(str(cue.get("phrase", "")))
            if not phrase_tokens:
                continue
            candidates = []
            length = len(phrase_tokens)
            for start in range(0, max(0, len(flat_words) - length + 1)):
                if flat_words[start:start + length] == phrase_tokens:
                    candidates.append(start)
            if candidates:
                start = min(
                    candidates,
                    key=lambda index: abs(words[index]["start"] - float(cue["time"])),
                )
            else:
                start = min(
                    range(len(words)),
                    key=lambda index: abs(words[index]["start"] - float(cue["time"])),
                    default=0,
                )
            end = min(len(words), start + length)
            anchor_candidates = range(start, max(start + 1, end))
            anchor = min(
                anchor_candidates,
                key=lambda index: abs(
                    words[index]["start"] - float(cue["time"])
                ),
                default=start,
            )
            triggers.append({
                "cue": cue["name"],
                "startWord": start,
                "endWord": end,
                "anchorWord": anchor,
                "time": float(cue["time"]),
            })
        return {
            "text": str(source.get("text", "")),
            "words": words,
            "triggers": triggers,
        }

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return re.findall(r"[a-z0-9]+", value.lower())

    def music_settings(self) -> dict:
        settings = {
            "enabled": True,
            "gainDb": self.music_gain_db,
            "offsetSeconds": self.music_offset_seconds,
        }
        try:
            saved = json.loads(self.music_settings_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            saved = {}
        for key in settings:
            if key in saved:
                settings[key] = saved[key]
        return settings

    def update_music_settings(self, payload: dict) -> dict:
        if self.music_path is None:
            raise ValueError("No music is configured for this section")
        gain = float(payload.get("gainDb", self.music_gain_db))
        offset = float(payload.get("offsetSeconds", self.music_offset_seconds))
        if not -60.0 <= gain <= 12.0:
            raise ValueError("Music level is outside the supported range")
        if not -60.0 <= offset <= 60.0:
            raise ValueError("Music timing offset is outside the supported range")
        settings = {
            "enabled": bool(payload.get("enabled", True)),
            "gainDb": gain,
            "offsetSeconds": offset,
            "updatedAt": _utc_now(),
        }
        with self._lock:
            _atomic_json(self.music_settings_path, settings)
        return settings

    def save_annotation(self, payload: dict) -> dict:
        fields = self._validated_annotation_fields(payload)
        identifier = uuid.uuid4().hex[:12]
        screenshot = self._save_screenshot(identifier, payload.get("screenshot"))
        annotation = {
            "id": identifier,
            "section": self.section_id,
            **fields,
            "target": payload.get("target"),
            "screenshot": screenshot,
            "responses": [],
            "status": "draft",
            "createdAt": _utc_now(),
        }
        with self._lock:
            annotations = self.annotations()
            annotations.append(annotation)
            _atomic_json(self.annotations_path, annotations)
        return annotation

    def _validated_annotation_fields(self, payload: dict) -> dict:
        comment = str(payload.get("comment", "")).strip()
        if not comment:
            raise ValueError("Annotation comment cannot be empty")
        if len(comment) > MAX_COMMENT_LENGTH:
            raise ValueError("Annotation comment is too long")
        cue_names = {cue["name"] for cue in self.cues}
        cue = str(payload.get("cue", ""))
        if cue not in cue_names:
            raise ValueError(f"Unknown narration cue: {cue!r}")
        timestamp = float(payload.get("timestamp", 0.0))
        region = payload.get("region") or {}
        normalized = {}
        for key in ("x", "y", "width", "height"):
            value = float(region.get(key, 0.0))
            if value < 0.0 or value > 1.0:
                raise ValueError("Annotation coordinates must be normalized")
            normalized[key] = value
        if normalized["x"] + normalized["width"] > 1.001:
            raise ValueError("Annotation extends beyond the frame")
        if normalized["y"] + normalized["height"] > 1.001:
            raise ValueError("Annotation extends beyond the frame")

        return {
            "cue": cue,
            "phrase": str(payload.get("phrase", ""))[:500],
            "timestamp": timestamp,
            "region": normalized,
            "comment": comment,
        }

    def update_annotation(self, identifier: str, payload: dict) -> dict:
        fields = self._validated_annotation_fields(payload)
        with self._lock:
            annotations = self.annotations()
            match = next(
                (item for item in annotations if item.get("id") == identifier),
                None,
            )
            if match is None:
                raise KeyError(identifier)
            old_screenshot = match.get("screenshot")
            screenshot = old_screenshot
            if payload.get("screenshot"):
                screenshot = self._save_screenshot(identifier, payload["screenshot"])
                if old_screenshot and old_screenshot != screenshot:
                    old_asset = self.assets_dir / Path(old_screenshot).name
                    if old_asset.exists():
                        old_asset.unlink()
            match.update(fields)
            match.update({
                "target": payload.get("target"),
                "screenshot": screenshot,
                "status": "draft",
                "updatedAt": _utc_now(),
            })
            _atomic_json(self.annotations_path, annotations)
            return match.copy()

    def _save_screenshot(self, identifier: str, data_url) -> str | None:
        if not data_url:
            return None
        value = str(data_url)
        prefixes = {
            "data:image/png;base64,": ".png",
            "data:image/jpeg;base64,": ".jpg",
        }
        for prefix, suffix in prefixes.items():
            if value.startswith(prefix):
                binary = base64.b64decode(value[len(prefix):], validate=True)
                if len(binary) > 6 * 1024 * 1024:
                    raise ValueError("Annotation screenshot is too large")
                name = identifier + suffix
                (self.assets_dir / name).write_bytes(binary)
                return name
        raise ValueError("Unsupported screenshot format")

    def remove_annotation(self, identifier: str) -> bool:
        with self._lock:
            annotations = self.annotations()
            kept = [item for item in annotations if item.get("id") != identifier]
            if len(kept) == len(annotations):
                return False
            removed = next(
                item for item in annotations if item.get("id") == identifier
            )
            screenshot = removed.get("screenshot")
            if screenshot:
                asset = self.assets_dir / Path(screenshot).name
                if asset.exists():
                    asset.unlink()
            _atomic_json(self.annotations_path, kept)
            return True

    def submit_annotations(self) -> dict:
        with self._lock:
            annotations = self.annotations()
            pending = []
            for annotation in annotations:
                if annotation.get("status") == "draft":
                    annotation["status"] = "pending"
                    pending.append(annotation)
            _atomic_json(self.annotations_path, annotations)
            self._write_pending_file(annotations)
        return {
            "queued": len(pending),
            "path": str(self.pending_path.relative_to(self.workspace)),
        }

    def set_annotation_status(self, identifier: str, status: str) -> dict:
        allowed = {"pending", "pending_review", "resolved"}
        if status not in allowed:
            raise ValueError(f"Unsupported annotation status: {status!r}")
        with self._lock:
            annotations = self.annotations()
            match = next(
                (item for item in annotations if item.get("id") == identifier),
                None,
            )
            if match is None:
                raise KeyError(identifier)
            match["status"] = status
            match["updatedAt"] = _utc_now()
            _atomic_json(self.annotations_path, annotations)
            self._write_pending_file(annotations)
            return match.copy()

    def add_annotation_response(self, identifier: str, payload: dict) -> dict:
        body = str(payload.get("body", "")).strip()
        if not body:
            raise ValueError("Response cannot be empty")
        if len(body) > MAX_COMMENT_LENGTH:
            raise ValueError("Response is too long")
        author = str(payload.get("author", "user")).strip().lower()
        if author not in {"user", "codex"}:
            raise ValueError("Response author must be user or codex")
        response = {
            "id": uuid.uuid4().hex[:12],
            "author": author,
            "body": body,
            "createdAt": _utc_now(),
        }
        with self._lock:
            annotations = self.annotations()
            match = next(
                (item for item in annotations if item.get("id") == identifier),
                None,
            )
            if match is None:
                raise KeyError(identifier)
            match.setdefault("responses", []).append(response)
            # A viewer follow-up returns the item to Codex's active queue.
            # A Codex explanation hands it back without pretending the user
            # has approved either the answer or the visual fix.
            match["status"] = "pending" if author == "user" else "pending_review"
            match["updatedAt"] = _utc_now()
            _atomic_json(self.annotations_path, annotations)
            self._write_pending_file(annotations)
            return match.copy()

    def _write_pending_file(self, annotations: list[dict]) -> None:
        lines = [
            f"# Pending fixes: {self.section_title}",
            "",
            "These notes still need changes from Codex. Notes already marked",
            "ready for review stay visible in the reviewer but are omitted here.",
            "",
        ]
        if self.music_path is not None:
            music = self.music_settings()
            lines.extend([
                "## Music audition settings",
                "",
                f"Track: {self.music_title or self.music_path.stem}",
                f"Enabled: {music['enabled']}",
                f"Level: {music['gainDb']:.1f} dB",
                f"Timing offset: {music['offsetSeconds']:+.1f} s",
                "Ducking follows the configured narration-sidechain preset.",
                "",
            ])
        for item in annotations:
            if item.get("status") != "pending":
                continue
            region = item["region"]
            lines.extend([
                f"## {item['id']} · {item['cue']} · {item['timestamp']:.2f}s",
                "",
                f"> {item.get('phrase', '')}",
                "",
                item["comment"],
                "",
                "Region: "
                f"x={region['x']:.4f}, y={region['y']:.4f}, "
                f"w={region['width']:.4f}, h={region['height']:.4f}",
            ])
            if item.get("screenshot"):
                lines.append(f"Screenshot: assets/{item['screenshot']}")
            if item.get("target"):
                target = item["target"]
                lines.append(
                    "Manim object: "
                    f"{target.get('label', target.get('id', 'unknown'))} "
                    f"[{target.get('id', 'unknown')}]"
                )
            for response in item.get("responses", []):
                speaker = "Viewer" if response.get("author") == "user" else "Codex"
                lines.extend([
                    "",
                    f"{speaker}: {response.get('body', '')}",
                ])
            lines.append("")
        self.pending_path.write_text("\n".join(lines), encoding="utf-8")

    def request_render(self) -> bool:
        if not self.scene_name:
            raise ValueError("No Manim scene is configured for rendering")
        with self._render_lock:
            if self.render_status.state == "rendering":
                self._render_requested = True
                return False
            self.render_status = RenderStatus(
                state="rendering", message="Rendering with Manim…",
                started_at=_utc_now(),
            )
        threading.Thread(target=self._render_worker, daemon=True).start()
        return True

    def _render_command(self) -> list[str]:
        """Render an explicit scene source using the current Python runtime."""
        if self.scene_source is not None:
            if not self.scene_source.is_file():
                raise ValueError(f"Scene source does not exist: {self.scene_source}")
            return [
                sys.executable, "-m", "manim", f"-q{self.quality}",
                "--media_dir", str(self.workspace / "media"),
                "-v", "WARNING", "--progress_bar", "none",
                str(self.scene_source), self.scene_name,
            ]
        # Existing productions may retain their own render setup. Explicit
        # sources require no launcher and work on Windows, macOS, and Linux.
        launcher = self.workspace / "render_sections.ps1"
        if launcher.is_file():
            return [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-File", str(launcher),
                "-Section", self.scene_name, "-Quality", self.quality,
            ]
        raise ValueError("Set --source (or a catalog section's source) to its Manim Python file")

    def _render_worker(self) -> None:
        try:
            command = self._render_command()
            completed = subprocess.run(
                command, cwd=self.workspace, capture_output=True, text=True,
                timeout=30 * 60, check=False,
                env={
                    **os.environ,
                    "ALGOVIS_REVIEW_MANIFEST": str(self.manifest_path),
                },
            )
            log = (completed.stdout + "\n" + completed.stderr).strip()
            (self.review_dir / "last-render.log").write_text(log + "\n", encoding="utf-8")
            if completed.returncode:
                raise RuntimeError(log or f"Render exited {completed.returncode}")
            self._validate_render_timing()
            self._publish_render()
            self._refresh_preflight()
            with self._render_lock:
                self.revision = self._video_revision()
                self.render_status = RenderStatus(
                    state="ready", message="Render updated",
                    started_at=self.render_status.started_at,
                    completed_at=_utc_now(), log_tail=log[-3_000:],
                )
        except Exception as exc:  # surfaced in the local review UI
            detail = str(exc)
            with self._render_lock:
                self.render_status = RenderStatus(
                    # Keep the toolbar usable.  The complete diagnostic still
                    # lives in log_tail; putting it in the one-line status
                    # label can expand across the entire reviewer.
                    state="error",
                    message="Render failed; the previous preview is still available",
                    started_at=self.render_status.started_at,
                    completed_at=_utc_now(), log_tail=detail[-3_000:],
                )
        finally:
            rerender = False
            with self._render_lock:
                if self._render_requested:
                    self._render_requested = False
                    rerender = True
            if rerender:
                self.request_render()

    def _validate_render_timing(self) -> None:
        """Keep a mistimed render out of the reviewer, preserving the last good video."""
        from .audit import audit_section
        paths = [self.manifest_path, self.cue_path, self.transcript_path]
        if any(path is None or not path.is_file() for path in paths):
            return
        report = audit_section(*[
            json.loads(path.read_text(encoding="utf-8")) for path in paths
        ])
        problems = [event for event in report["events"] if event["findings"]]
        content = [change for change in report["changes"] if any(
            finding.startswith("content_") and finding != "content_erased_then_recreated"
            for finding in change["findings"]
        )]
        if problems or content:
            details = [f"{item.get('cue')}: {', '.join(item['findings'])}"
                       for item in problems + content]
            raise RuntimeError("Word timing rejected before publication: " + "; ".join(details[:8]))

    def _refresh_preflight(self) -> None:
        """Regenerate storyboards and static QA after a successful render.

        Review video remains available even if preflight generation fails; the
        next manual audit will surface the diagnostic without discarding a good
        Manim render.
        """
        # The word/composition ledger belongs to every project, not just the
        # private production's source-to-storyboard adapter. It is an agent
        # worklist, and does not mark the viewer's checks approved.
        self._refresh_word_ledger()
        # These legacy adapters belong to the original lesson. Other projects
        # can provide their own audit report without requiring its private files.
        if self.scene_source is not None:
            return
        scripts = (self.workspace / "tools" / "export_storyboards.py",
                   self.workspace / "tools" / "audit_animation_setup.py")
        if not (self.workspace / "full_video_preview.py").exists() or not all(
            script.exists() for script in scripts
        ):
            return
        commands = (
            [sys.executable, str(self.workspace / "tools" / "export_storyboards.py")],
            [sys.executable, str(self.workspace / "tools" / "audit_animation_setup.py")],
        )
        for command in commands:
            completed = subprocess.run(
                command, cwd=self.workspace, capture_output=True, text=True,
                timeout=90, check=False,
            )
            if completed.returncode:
                return

    def _refresh_word_ledger(self) -> None:
        from .audit import audit_section, markdown_report
        paths = [self.manifest_path, self.cue_path, self.transcript_path]
        if any(path is None or not path.is_file() for path in paths):
            return
        try:
            report = audit_section(*[
                json.loads(path.read_text(encoding="utf-8")) for path in paths
            ])
            report["inputs"] = {
                str(path.relative_to(self.workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            }
            _atomic_json(self.review_dir / "agent-audit.json", report)
            (self.review_dir / "agent-audit.md").write_text(
                markdown_report({"title": self.section_title}, report), encoding="utf-8",
            )
        except Exception as exc:
            # Keep the good render, but leave an explicit failed audit. A stale
            # older success must never survive as the result for this version.
            _atomic_json(self.review_dir / "agent-audit.json", {
                "status": "audit_failed", "error": str(exc),
            })

    def _publish_render(self) -> None:
        source = self.rendered_video_path
        if source is None:
            quality_dir = {
                "l": "480p15", "m": "720p30", "h": "1080p60",
                "p": "1440p60", "k": "2160p60",
            }[self.quality]
            source = (
                self.workspace / "media" / "videos"
                / (self.scene_source.stem if self.scene_source else "full_video_preview")
                / quality_dir / f"{self.scene_name}.mp4"
            )
        if not source.exists():
            raise FileNotFoundError(f"Manim output was not created: {source}")
        # Browsers can keep an open MP4 locked on Windows. Publishing each
        # revision to a fresh filename lets the old preview keep playing while
        # the server atomically switches new requests to the completed render.
        revision_name = f"{self.section_id}.{time.time_ns()}"
        destination = self.published_dir / f"{revision_name}.mp4"
        temporary = self.published_dir / f"{revision_name}.tmp.mp4"
        if self.audio_path is not None and self.audio_path.exists():
            command = [
                "ffmpeg", "-loglevel", "error", "-y",
                "-i", str(source), "-i", str(self.audio_path),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-af", "apad", "-shortest",
                "-movflags", "+faststart", str(temporary),
            ]
            completed = subprocess.run(
                command, cwd=self.workspace, capture_output=True, text=True,
                timeout=10 * 60, check=False,
            )
            if completed.returncode:
                raise RuntimeError(completed.stderr.strip() or "FFmpeg failed")
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        self.video_path = destination
        published = sorted(
            (path for path in self.published_dir.glob("*.mp4")
             if not path.name.endswith(".tmp.mp4")),
            key=lambda path: path.stat().st_mtime_ns,
            reverse=True,
        )
        for stale in published[3:]:
            try:
                stale.unlink()
            except OSError:
                # A tab may still be finishing playback from this revision.
                pass

    def watch(self, stop: threading.Event) -> None:
        dirty_at = None
        while not stop.wait(0.5):
            current = self._watch_mtimes()
            if current != self._watch_snapshot:
                self._watch_snapshot = current
                dirty_at = time.monotonic()
            if dirty_at is not None and time.monotonic() - dirty_at >= 1.0:
                try:
                    self.request_render()
                except ValueError:
                    pass
                dirty_at = None


@dataclass
class ReviewCatalog:
    reviews: dict[str, ReviewServer]
    default_section: str
    token: str

    def __post_init__(self) -> None:
        if self.default_section not in self.reviews:
            raise ValueError(f"Unknown default review section: {self.default_section}")
        for review in self.reviews.values():
            review.token = self.token
        self.active_section = self.default_section
        self._lock = threading.RLock()

    def review(self, section_id: str | None = None) -> ReviewServer:
        selected = section_id or self.default_section
        try:
            review = self.reviews[selected]
        except KeyError as exc:
            raise ValueError(f"Unknown review section: {selected}") from exc
        with self._lock:
            self.active_section = selected
        return review

    def summaries(self) -> list[dict]:
        summaries = []
        for review in self.reviews.values():
            cue_data = json.loads(review.cue_path.read_text(encoding="utf-8"))
            summaries.append({
                "id": review.section_id,
                "title": review.section_title,
                "duration": float(cue_data.get("duration", 0.0)),
                "reviewStatus": review.approval_payload()["status"],
            })
        return summaries

    def watch(self, stop: threading.Event) -> None:
        reference = self.reviews[self.default_section]
        dirty_at = None
        snapshot = reference._watch_mtimes()
        while not stop.wait(0.5):
            current = reference._watch_mtimes()
            if current != snapshot:
                snapshot = current
                dirty_at = time.monotonic()
            if dirty_at is not None and time.monotonic() - dirty_at >= 1.0:
                with self._lock:
                    review = self.reviews[self.active_section]
                try:
                    review.request_render()
                except ValueError:
                    pass
                dirty_at = None


class ReviewRequestHandler(BaseHTTPRequestHandler):
    server_version = "AlgovisReview/0.1"

    @property
    def review(self) -> ReviewServer:
        _parsed, query = self._query()
        section = query.get("section", [None])[0]
        return self.server.catalog.review(section)  # type: ignore[attr-defined]

    @property
    def catalog(self) -> ReviewCatalog:
        return self.server.catalog  # type: ignore[attr-defined]

    def log_message(self, format, *args) -> None:  # noqa: A002
        return

    def _query(self):
        parsed = urlparse(self.path)
        return parsed, parse_qs(parsed.query)

    def _authorized(self, query) -> bool:
        token = query.get("token", [""])[0]
        return secrets.compare_digest(token, self.review.token)

    def _json(self, value, status=HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status, message) -> None:
        self._json({"error": str(message)}, status)

    def _payload(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_JSON_BYTES:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        parsed, query = self._query()
        if parsed.path == "/":
            location = (
                f"/app?token={self.catalog.token}"
                f"&section={quote(self.catalog.default_section)}"
            )
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", location)
            self.end_headers()
            return
        if parsed.path == "/app":
            self._send_file(self.review.static_path, "text/html; charset=utf-8")
            return
        if not self._authorized(query):
            self._error(HTTPStatus.FORBIDDEN, "Invalid review session")
            return
        if parsed.path == "/api/project":
            payload = self.review.project_payload()
            payload["sections"] = self.catalog.summaries()
            payload["activeSection"] = self.review.section_id
            self._json(payload)
            return
        if parsed.path == "/api/revision":
            self.review.revision = self.review._video_revision()
            self._json({
                "revision": self.review.revision,
                "render": self.review.render_status.__dict__,
                "annotationCount": len(self.review.annotations()),
                "audit": self.review.audit_payload(),
                "approval": self.review.approval_payload(),
                "sections": self.catalog.summaries(),
            })
            return
        if parsed.path == "/video":
            self._send_media(self.review.video_path, "video/mp4")
            return
        if parsed.path == "/review-frame":
            try:
                path = self.review.transition_frame(
                    query.get("transition", [""])[0],
                    query.get("position", [""])[0],
                    int(query.get("revision", ["0"])[0]),
                )
                self._send_file(path, "image/jpeg")
            except (ValueError, KeyError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, exc)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                self._error(HTTPStatus.SERVICE_UNAVAILABLE, str(exc))
            return
        if parsed.path == "/music" and self.review.music_path is not None:
            content_type = (
                mimetypes.guess_type(self.review.music_path.name)[0]
                or "audio/ogg"
            )
            self._send_media(self.review.music_path, content_type)
            return
        if parsed.path.startswith("/annotation-asset/"):
            name = Path(parsed.path).name
            self._send_file(self.review.assets_dir / name)
            return
        self._error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed, query = self._query()
        if not self._authorized(query):
            self._error(HTTPStatus.FORBIDDEN, "Invalid review session")
            return
        try:
            if parsed.path == "/api/annotations":
                self._json(
                    self.review.save_annotation(self._payload()),
                    HTTPStatus.CREATED,
                )
                return
            annotation_prefix = "/api/annotations/"
            if (
                parsed.path.startswith(annotation_prefix)
                and parsed.path.endswith("/responses")
            ):
                identifier = parsed.path[
                    len(annotation_prefix):-len("/responses")
                ]
                try:
                    updated = self.review.add_annotation_response(
                        identifier, self._payload(),
                    )
                except KeyError:
                    self._error(HTTPStatus.NOT_FOUND, "Annotation not found")
                    return
                self._json(updated, HTTPStatus.CREATED)
                return
            if parsed.path == "/api/submit":
                self._json(self.review.submit_annotations())
                return
            if parsed.path == "/api/render":
                started = self.review.request_render()
                self._json({"started": started})
                return
        except (ValueError, json.JSONDecodeError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, exc)
            return
        self._error(HTTPStatus.NOT_FOUND, "Not found")

    def do_DELETE(self) -> None:  # noqa: N802
        parsed, query = self._query()
        if not self._authorized(query):
            self._error(HTTPStatus.FORBIDDEN, "Invalid review session")
            return
        prefix = "/api/annotations/"
        if parsed.path.startswith(prefix):
            identifier = parsed.path[len(prefix):]
            if self.review.remove_annotation(identifier):
                self._json({"removed": identifier})
            else:
                self._error(HTTPStatus.NOT_FOUND, "Annotation not found")
            return
        self._error(HTTPStatus.NOT_FOUND, "Not found")

    def do_PATCH(self) -> None:  # noqa: N802
        parsed, query = self._query()
        if not self._authorized(query):
            self._error(HTTPStatus.FORBIDDEN, "Invalid review session")
            return
        prefix = "/api/annotations/"
        if parsed.path.startswith("/api/preflight/"):
            try:
                identifier = parsed.path[len("/api/preflight/"):]
                self._json(self.review.review_finding(identifier, self._payload()))
            except (ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, exc)
            return
        if parsed.path == "/api/approval":
            try:
                approval = self.review.set_approval(self._payload())
                self._json({"approval": approval, "sections": self.catalog.summaries()})
            except (ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, exc)
            return
        if parsed.path == "/api/music":
            try:
                self._json(
                    self.review.update_music_settings(self._payload())
                )
            except (ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, exc)
            return
        if parsed.path.startswith(prefix):
            suffix = parsed.path[len(prefix):]
            if suffix.endswith("/status"):
                identifier = suffix[:-len("/status")]
                try:
                    updated = self.review.set_annotation_status(
                        identifier, str(self._payload().get("status", "")),
                    )
                except KeyError:
                    self._error(HTTPStatus.NOT_FOUND, "Annotation not found")
                    return
                except (ValueError, json.JSONDecodeError) as exc:
                    self._error(HTTPStatus.BAD_REQUEST, exc)
                    return
                self._json(updated)
                return
            identifier = suffix
            try:
                updated = self.review.update_annotation(
                    identifier, self._payload(),
                )
            except KeyError:
                self._error(HTTPStatus.NOT_FOUND, "Annotation not found")
                return
            except (ValueError, json.JSONDecodeError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, exc)
                return
            self._json(updated)
            return
        self._error(HTTPStatus.NOT_FOUND, "Not found")

    def _send_file(self, path: Path, content_type: str | None = None) -> None:
        try:
            path = path.resolve(strict=True)
        except FileNotFoundError:
            self._error(HTTPStatus.NOT_FOUND, "File not found")
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            content_type or mimetypes.guess_type(path.name)[0]
            or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_media(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self._error(HTTPStatus.NOT_FOUND, "Rendered video not found")
            return
        size = path.stat().st_size
        start, end = 0, size - 1
        status = HTTPStatus.OK
        header = self.headers.get("Range")
        if header and header.startswith("bytes="):
            first, _, last = header[6:].partition("-")
            if first:
                start = int(first)
            if last:
                end = min(int(last), size - 1)
            status = HTTPStatus.PARTIAL_CONTENT
        length = max(0, end - start + 1)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        try:
            with path.open("rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            # Browsers routinely cancel an old byte-range request after a seek.
            return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review a real Manim section with transcript annotations.",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--section-id")
    parser.add_argument("--title")
    parser.add_argument("--video", type=Path)
    parser.add_argument("--cues", type=Path)
    parser.add_argument("--transcript-words", type=Path)
    parser.add_argument("--scene", default="")
    parser.add_argument("--source", type=Path, help="Manim Python source for section rendering")
    parser.add_argument("--audio", type=Path)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--music-title", default="")
    parser.add_argument("--music-gain-db", type=float, default=-12.0)
    parser.add_argument("--music-offset-seconds", type=float, default=0.0)
    parser.add_argument("--duck-threshold", type=float, default=0.018)
    parser.add_argument("--duck-ratio", type=float, default=3.5)
    parser.add_argument("--duck-attack-ms", type=float, default=350.0)
    parser.add_argument("--duck-release-ms", type=float, default=1800.0)
    parser.add_argument("--rendered-video", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--quality", choices=("l", "m", "h", "p", "k"), default="l")
    parser.add_argument("--watch", type=Path, action="append", default=[])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument(
        "--token",
        help="Optional fixed local session token (otherwise generated at startup).",
    )
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    workspace = args.workspace.resolve()

    def workspace_path(path: Path | None) -> Path | None:
        if path is None:
            return None
        return path if path.is_absolute() else workspace / path

    token = args.token or secrets.token_urlsafe(18)
    common_watch_paths = tuple(workspace_path(path) for path in args.watch)

    def build_review(values: dict) -> ReviewServer:
        return ReviewServer(
            workspace=workspace,
            section_id=str(values["id"]),
            section_title=str(values["title"]),
            video_path=workspace_path(Path(values["video"])),
            cue_path=workspace_path(Path(values["cues"])),
            transcript_path=workspace_path(
                Path(values["transcriptWords"])
                if values.get("transcriptWords") else None
            ),
            scene_name=str(values.get("scene", "")),
            scene_source=workspace_path(
                Path(values["source"]) if values.get("source") else args.source
            ),
            audio_path=workspace_path(
                Path(values["audio"]) if values.get("audio") else None
            ),
            music_path=workspace_path(
                Path(values["music"]) if values.get("music") else None
            ),
            music_title=str(values.get("musicTitle", "")),
            music_gain_db=float(values.get("musicGainDb", -12.0)),
            music_offset_seconds=float(values.get("musicOffsetSeconds", 0.0)),
            duck_threshold=float(values.get("duckThreshold", 0.018)),
            duck_ratio=float(values.get("duckRatio", 3.5)),
            duck_attack_ms=float(values.get("duckAttackMs", 350.0)),
            duck_release_ms=float(values.get("duckReleaseMs", 1800.0)),
            rendered_video_path=workspace_path(
                Path(values["renderedVideo"])
                if values.get("renderedVideo") else None
            ),
            manifest_path=workspace_path(
                Path(values["manifest"]) if values.get("manifest") else None
            ),
            quality=str(values.get("quality", args.quality)),
            watch_paths=common_watch_paths,
            token=token,
        )

    if args.catalog:
        catalog_path = workspace_path(args.catalog)
        catalog_data = json.loads(catalog_path.read_text(encoding="utf-8"))
        reviews = {
            str(item["id"]): build_review(item)
            for item in catalog_data["sections"]
        }
        default_section = str(
            catalog_data.get("defaultSection") or next(iter(reviews))
        )
    else:
        if not all((args.section_id, args.title, args.video, args.cues)):
            raise SystemExit(
                "Provide --catalog or all of --section-id, --title, --video, --cues"
            )
        single = {
            "id": args.section_id,
            "title": args.title,
            "video": str(args.video),
            "cues": str(args.cues),
            "transcriptWords": (
                str(args.transcript_words) if args.transcript_words else None
            ),
            "scene": args.scene,
            "source": str(args.source) if args.source else None,
            "audio": str(args.audio) if args.audio else None,
            "music": str(args.music) if args.music else None,
            "musicTitle": args.music_title,
            "musicGainDb": args.music_gain_db,
            "musicOffsetSeconds": args.music_offset_seconds,
            "duckThreshold": args.duck_threshold,
            "duckRatio": args.duck_ratio,
            "duckAttackMs": args.duck_attack_ms,
            "duckReleaseMs": args.duck_release_ms,
            "renderedVideo": (
                str(args.rendered_video) if args.rendered_video else None
            ),
            "manifest": str(args.manifest) if args.manifest else None,
            "quality": args.quality,
        }
        review = build_review(single)
        reviews = {review.section_id: review}
        default_section = review.section_id

    catalog = ReviewCatalog(reviews, default_section, token)
    server = ReviewHTTPServer((args.host, args.port), ReviewRequestHandler)
    server.catalog = catalog  # type: ignore[attr-defined]
    stop = threading.Event()
    if common_watch_paths:
        threading.Thread(target=catalog.watch, args=(stop,), daemon=True).start()
    url = (
        f"http://{args.host}:{args.port}/app?token={catalog.token}"
        f"&section={quote(catalog.default_section)}"
    )
    print(url, flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
