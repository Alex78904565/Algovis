from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch
import subprocess
import sys

from algovis.review.server import ReviewCatalog, ReviewHTTPServer, ReviewServer


class ReviewServerTests(unittest.TestCase):
    def test_render_audit_records_words_and_does_not_approve_viewer_checks(self):
        self.review.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.review.manifest_path.write_text(json.dumps({
            "frameRate": 15, "animations": [{
                "id": "effect", "play": 0, "kind": "Pulse", "label": "the value",
                "start": 1.5, "end": 2, "cue": "change",
            }], "plays": [{"start": 1.5, "end": 2, "before": [], "after": []}],
        }), encoding="utf-8")
        self.review._refresh_word_ledger()
        report = json.loads((self.review.review_dir / "agent-audit.json").read_text())
        self.assertEqual(report["status"], "requires_agent_review")
        self.assertIn("attention_without_declared_trigger", report["events"][0]["findings"])
        self.assertIn("words.json", report["inputs"])
        self.assertTrue((self.review.review_dir / "agent-audit.md").exists())
        self.assertFalse(self.review.finding_reviews_path.exists())

    def test_explicit_scene_source_renders_without_a_project_powershell_script(self):
        source = self.workspace / "lesson scenes.py"
        source.write_text("# scene source", encoding="utf-8")
        self.review.scene_source = source
        self.review.scene_name = "Lesson"
        command = self.review._render_command()
        self.assertEqual(command[:4], [sys.executable, "-m", "manim", "-ql"])
        self.assertEqual(command[-2:], [str(source), "Lesson"])
        self.assertIn(str(self.workspace / "media"), command)

    def test_existing_project_render_launcher_remains_supported(self):
        launcher = self.workspace / "render_sections.ps1"
        launcher.write_text("# production render setup", encoding="utf-8")
        self.assertIn(str(launcher), self.review._render_command())

    def test_missing_scene_source_has_a_useful_error(self):
        with self.assertRaisesRegex(ValueError, "Set --source"):
            self.review._render_command()

    def test_restart_does_not_select_an_unfinished_video_publication(self):
        unfinished = self.review.published_dir / "sample.new.tmp.mp4"
        unfinished.write_bytes(b"unfinished video")
        restarted = ReviewServer(workspace=self.workspace, section_id="sample", section_title="Sample",
                                 video_path=self.workspace / "render.mp4",
                                 cue_path=self.workspace / "cues.json")
        self.assertEqual(restarted.video_path, self.workspace / "render.mp4")

    def test_scene_source_cannot_escape_the_review_workspace(self):
        with self.assertRaisesRegex(ValueError, "leaves the review workspace"):
            ReviewServer(workspace=self.workspace, section_id="outside", section_title="Outside",
                         video_path=self.workspace / "render.mp4",
                         cue_path=self.workspace / "cues.json",
                         scene_source=self.workspace.parent / "other.py")

    def test_windows_port_binding_is_exclusive(self):
        server = object.__new__(ReviewHTTPServer)
        server.socket = Mock()
        with patch("algovis.review.server.socket.SO_EXCLUSIVEADDRUSE", -5, create=True), \
             patch("http.server.ThreadingHTTPServer.server_bind") as bind:
            server.server_bind()
        self.assertFalse(server.allow_reuse_address)
        server.socket.setsockopt.assert_called_once()
        bind.assert_called_once()

    def setUp(self) -> None:
        qa_root = Path(".qa").resolve()
        qa_root.mkdir(exist_ok=True)
        self.workspace = Path(tempfile.mkdtemp(prefix="review-test-", dir=qa_root))
        (self.workspace / "render.mp4").write_bytes(b"fake video")
        (self.workspace / "music.ogg").write_bytes(b"fake music")
        (self.workspace / "cues.json").write_text(
            json.dumps({
                "duration": 3.0,
                "cues": [
                    {"name": "start", "time": 0.0, "phrase": "start here"},
                    {"name": "change", "time": 1.5, "phrase": "change this"},
                ],
            }),
            encoding="utf-8",
        )
        (self.workspace / "words.json").write_text(
            json.dumps({
                "text": "start here and change this",
                "segments": [{
                    "words": [
                        {"word": "start", "start": 0.0, "end": .2},
                        {"word": " here", "start": .2, "end": .4},
                        {"word": " and", "start": .7, "end": .9},
                        {"word": " change", "start": 1.5, "end": 1.7},
                        {"word": " this", "start": 1.7, "end": 1.9},
                    ],
                }],
            }),
            encoding="utf-8",
        )
        self.review = ReviewServer(
            workspace=self.workspace,
            section_id="sample",
            section_title="Sample",
            video_path=self.workspace / "render.mp4",
            cue_path=self.workspace / "cues.json",
            transcript_path=self.workspace / "words.json",
            music_path=self.workspace / "music.ogg",
            music_title="Test score",
            music_gain_db=-9.0,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.workspace)

    def test_annotation_preserves_cue_time_region_and_frame(self) -> None:
        pixel = base64.b64encode(b"not really a jpeg").decode("ascii")
        annotation = self.review.save_annotation({
            "cue": "change",
            "phrase": "change this",
            "timestamp": 1.6,
            "region": {"x": .1, "y": .2, "width": .3, "height": .25},
            "comment": "Move this label farther left.",
            "screenshot": f"data:image/jpeg;base64,{pixel}",
        })

        self.assertEqual(annotation["cue"], "change")
        self.assertEqual(annotation["region"]["width"], .3)
        self.assertTrue(
            (self.review.assets_dir / annotation["screenshot"]).exists()
        )

    def test_overlapping_transcript_segments_do_not_duplicate_timed_words(self):
        path = self.workspace / "words.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        # Simulate a correction segment placed before the original segment.
        data["segments"].insert(0, {"words": [
            {"word": " change", "start": 1.5, "end": 1.7},
            {"word": " this", "start": 1.7, "end": 1.9},
        ]})
        path.write_text(json.dumps(data), encoding="utf-8")
        payload = self.review.transcript_payload(self.review.cues)
        self.assertEqual(len(payload["words"]), 5)
        self.assertEqual([word["start"] for word in payload["words"]], [0, .2, .7, 1.5, 1.7])

    def test_project_exposes_separate_adjustable_music_layer(self) -> None:
        music = self.review.project_payload()["music"]

        self.assertEqual(music["title"], "Test score")
        self.assertEqual(music["gainDb"], -9.0)
        self.assertIn("/music?token=", music["url"])
        self.assertEqual(music["duck"]["ratio"], 3.5)

    def test_project_exposes_generated_section_preflight(self) -> None:
        audit_path = self.workspace / ".review" / "audit.json"
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(json.dumps({
            "sections": {
                "sample": {
                    "id": "sample",
                    "title": "Sample",
                    "status": "needs_review",
                    "issues": [{
                        "severity": "warning",
                        "category": "timing",
                        "message": "Check this cue.",
                        "location": "scene.py:12",
                    }],
                },
            },
        }), encoding="utf-8")

        audit = self.review.project_payload()["audit"]

        self.assertEqual(audit["status"], "needs_review")
        self.assertEqual(audit["issues"][0]["category"], "timing")

    def test_missing_preflight_is_nonfatal(self) -> None:
        self.assertIsNone(self.review.audit_payload())

    def _write_preflight(self, issues):
        path = self.workspace / ".review" / "audit.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"sections": {"sample": {
            "id": "sample", "title": "Sample", "issues": issues,
        }}}), encoding="utf-8")

    def test_preflight_checks_persist_but_reopen_after_video_changes(self):
        self._write_preflight([{
            "severity": "warning", "category": "timing", "message": "Check timing.",
            "cue": "start", "time": 0.0,
        }])
        audit = self.review.audit_payload()
        identifier = audit["issues"][0]["id"]
        result = self.review.review_finding(identifier, {
            "status": "checked", "version": audit["reviewVersion"],
        })
        self.assertEqual(result["audit"]["progress"]["checked"], 1)
        self.assertEqual(self.review.audit_payload()["status"], "ready")
        # Re-reading a regenerated report preserves the identity and decision.
        self._write_preflight([{
            "severity": "warning", "category": "timing", "message": "Check timing.",
            "cue": "start", "time": 0.0,
        }])
        self.assertEqual(self.review.audit_payload()["issues"][0]["reviewStatus"], "checked")
        (self.workspace / "render.mp4").write_bytes(b"updated video")
        self.assertEqual(self.review.audit_payload()["issues"][0]["reviewStatus"], "pending")
        with self.assertRaisesRegex(ValueError, "preview changed"):
            self.review.review_finding(identifier, {
                "status": "checked", "version": audit["reviewVersion"],
            })

    def test_preflight_change_request_reuses_its_note_without_resetting_other_checks(self):
        self._write_preflight([
            {"severity": "warning", "category": "timing", "message": "First flag.", "cue": "start", "time": 0.0},
            {"severity": "warning", "category": "color", "message": "Second flag.", "cue": "change", "time": 1.5},
        ])
        audit = self.review.audit_payload()
        first, second = audit["issues"]
        self.review.review_finding(first["id"], {"status": "checked", "version": audit["reviewVersion"]})
        for _attempt in range(2):
            result = self.review.review_finding(second["id"], {
                "status": "needs_change", "version": audit["reviewVersion"],
                "note": "Please make this highlight consistent.",
            })
        self.assertEqual(result["audit"]["progress"]["checked"], 1)
        self.assertEqual(result["audit"]["progress"]["needs_change"], 1)
        self.assertEqual(len(result["annotations"]), 1)
        self.assertEqual(result["annotations"][0]["status"], "pending")
        self.assertIn("Please make", result["annotations"][0]["comment"])
        self.assertFalse(result["approval"]["canApprove"])
        self.review.set_annotation_status(result["annotations"][0]["id"], "pending_review")
        result = self.review.review_finding(second["id"], {
            "status": "checked", "version": audit["reviewVersion"],
        })
        self.assertEqual(result["annotations"][0]["status"], "resolved")
        self.assertTrue(result["approval"]["canApprove"])

    def test_skipping_preflight_does_not_clear_technical_errors(self):
        self._write_preflight([{
            "severity": "error", "category": "source", "message": "Unknown cue.",
        }])
        audit = self.review.audit_payload()
        identifier = audit["issues"][0]["id"]
        with self.assertRaisesRegex(ValueError, "technical error"):
            self.review.review_finding(identifier, {
                "status": "checked", "version": audit["reviewVersion"],
            })
        result = self.review.review_finding(identifier, {
            "status": "deferred", "version": audit["reviewVersion"],
        })
        self.assertEqual(result["audit"]["progress"]["deferred"], 1)
        self.assertEqual(result["audit"]["status"], "blocked")

    def test_section_approval_persists_and_rejects_an_older_render(self):
        current = self.review.approval_payload()
        approved = self.review.set_approval({"approved": True, "version": current["version"]})
        self.assertEqual(approved["status"], "approved")

        restored = ReviewServer(
            workspace=self.workspace, section_id="sample", section_title="Sample",
            video_path=self.workspace / "render.mp4", cue_path=self.workspace / "cues.json",
            transcript_path=self.workspace / "words.json",
            music_path=self.workspace / "music.ogg", music_title="Test score", music_gain_db=-9.0,
        )
        self.assertEqual(restored.approval_payload()["status"], "approved")
        (self.workspace / "render.mp4").write_bytes(b"a new video revision")
        self.assertEqual(restored.approval_payload()["status"], "needs_review")
        with self.assertRaisesRegex(ValueError, "section changed"):
            restored.set_approval({"approved": True, "version": approved["version"]})

    def test_open_notes_must_be_resolved_before_section_approval(self):
        annotation = self.review.save_annotation({
            "cue": "start", "phrase": "start here", "timestamp": .2,
            "region": {"x": .1, "y": .1, "width": .2, "height": .2},
            "comment": "Fix this first.",
        })
        self.review.set_annotation_status(annotation["id"], "pending_review")
        current = self.review.approval_payload()
        self.assertFalse(current["canApprove"])
        with self.assertRaisesRegex(ValueError, "Resolve 1 open note"):
            self.review.set_approval({"approved": True, "version": current["version"]})
        self.review.set_annotation_status(annotation["id"], "resolved")
        current = self.review.approval_payload()
        self.assertEqual(self.review.set_approval({
            "approved": True, "version": current["version"],
        })["status"], "approved")

    def test_approval_reopens_when_soundtrack_changes_or_viewer_reopens_it(self):
        current = self.review.approval_payload()
        self.review.set_approval({"approved": True, "version": current["version"]})
        self.review.update_music_settings({"enabled": True, "gainDb": -13.0, "offsetSeconds": 1.0})
        self.assertEqual(self.review.approval_payload()["status"], "needs_review")
        current = self.review.approval_payload()
        self.review.set_approval({"approved": True, "version": current["version"]})
        self.assertEqual(self.review.set_approval({"approved": False})["status"], "needs_review")

    def test_catalog_reports_approval_without_treating_preflight_as_viewer_approval(self):
        self.assertEqual(self.review.approval_payload()["status"], "not_reviewed")
        current = self.review.approval_payload()
        self.review.set_approval({"approved": True, "version": current["version"]})
        catalog = ReviewCatalog({"sample": self.review}, "sample", "test-token")
        self.assertEqual(catalog.summaries()[0]["reviewStatus"], "approved")

    def test_transition_frames_are_cached_and_cannot_select_arbitrary_files(self):
        self.review.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.review.manifest_path.write_text(json.dumps({
            "animations": [{
                "id": "a", "play": 0, "start": 1.0, "end": 2.0,
                "label": "equation",
            }],
        }), encoding="utf-8")
        revision = self.review._video_revision()
        frames = self.review.project_payload()["transitions"][0]["frames"]
        self.assertIn(f"revision={revision}", frames[0]["url"])
        with patch("algovis.review.server.subprocess.run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, b"jpeg bytes", b"")
            first = self.review.transition_frame("play-0001", "middle", revision)
            second = self.review.transition_frame("play-0001", "middle", revision)
        self.assertEqual(first, second)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(first.read_bytes(), b"jpeg bytes")
        with self.assertRaisesRegex(ValueError, "Unknown animation"):
            self.review.transition_frame("../../outside", "middle", revision)
        with self.assertRaisesRegex(ValueError, "render changed"):
            self.review.transition_frame("play-0001", "middle", revision + 1)

    def test_full_transcript_maps_trigger_phrases_to_words(self) -> None:
        transcript = self.review.project_payload()["transcript"]

        self.assertEqual(len(transcript["words"]), 5)
        self.assertEqual(transcript["triggers"][0]["startWord"], 0)
        self.assertEqual(transcript["triggers"][0]["endWord"], 2)
        self.assertEqual(transcript["triggers"][0]["anchorWord"], 0)
        self.assertEqual(transcript["triggers"][1]["time"], 1.5)
        self.assertEqual(transcript["triggers"][1]["startWord"], 3)

    def test_catalog_exposes_and_selects_multiple_sections(self) -> None:
        second = ReviewServer(
            workspace=self.workspace,
            section_id="second",
            section_title="Second",
            video_path=self.workspace / "render.mp4",
            cue_path=self.workspace / "cues.json",
            transcript_path=self.workspace / "words.json",
        )
        catalog = ReviewCatalog(
            {"sample": self.review, "second": second},
            default_section="sample",
            token="shared-token",
        )

        self.assertEqual(len(catalog.summaries()), 2)
        self.assertEqual(catalog.review("second").section_title, "Second")
        self.assertEqual(second.token, "shared-token")

    def test_music_level_and_timing_are_persisted(self) -> None:
        saved = self.review.update_music_settings({
            "enabled": True,
            "gainDb": -11.5,
            "offsetSeconds": 1.7,
        })

        music = self.review.project_payload()["music"]
        self.assertEqual(saved["gainDb"], -11.5)
        self.assertEqual(music["offsetSeconds"], 1.7)

    def test_queue_writes_human_readable_pending_file(self) -> None:
        annotation = self.review.save_annotation({
            "cue": "start",
            "phrase": "start here",
            "timestamp": .2,
            "region": {"x": .2, "y": .2, "width": .1, "height": .1},
            "comment": "Highlight only the base case.",
        })

        result = self.review.submit_annotations()
        pending = self.review.pending_path.read_text(encoding="utf-8")

        self.assertEqual(result["queued"], 1)
        self.assertIn(annotation["id"], pending)
        self.assertIn("Highlight only the base case.", pending)
        self.assertEqual(self.review.annotations()[0]["status"], "pending")

    def test_annotation_can_be_edited_and_returns_to_draft(self) -> None:
        annotation = self.review.save_annotation({
            "cue": "start",
            "phrase": "start here",
            "timestamp": .2,
            "region": {"x": .2, "y": .2, "width": .1, "height": .1},
            "comment": "Original note.",
            "target": {"id": "object-0012", "label": "f(5)"},
        })
        self.review.submit_annotations()

        updated = self.review.update_annotation(annotation["id"], {
            "cue": "change",
            "phrase": "change this",
            "timestamp": 1.5,
            "region": {"x": .3, "y": .3, "width": .2, "height": .2},
            "comment": "Revised note.",
        })

        self.assertEqual(updated["comment"], "Revised note.")
        self.assertEqual(updated["status"], "draft")
        self.assertIn("updatedAt", updated)

    def test_fixed_note_waits_for_user_review_outside_codex_queue(self) -> None:
        annotation = self.review.save_annotation({
            "cue": "start",
            "phrase": "start here",
            "timestamp": .2,
            "region": {"x": .2, "y": .2, "width": .1, "height": .1},
            "comment": "Move this label.",
        })
        self.review.submit_annotations()

        review_ready = self.review.set_annotation_status(
            annotation["id"], "pending_review",
        )
        pending = self.review.pending_path.read_text(encoding="utf-8")

        self.assertEqual(review_ready["status"], "pending_review")
        self.assertNotIn(annotation["id"], pending)

        resolved = self.review.set_annotation_status(
            annotation["id"], "resolved",
        )
        self.assertEqual(resolved["status"], "resolved")

    def test_annotation_discussion_hands_work_between_codex_and_viewer(self) -> None:
        annotation = self.review.save_annotation({
            "cue": "start",
            "phrase": "start here",
            "timestamp": .2,
            "region": {"x": .2, "y": .2, "width": .1, "height": .1},
            "comment": "Is this explanation too advanced?",
        })
        self.review.submit_annotations()

        answered = self.review.add_annotation_response(annotation["id"], {
            "author": "codex",
            "body": "I simplified the notation and kept the visual argument.",
        })
        self.assertEqual(answered["status"], "pending_review")
        self.assertEqual(answered["responses"][0]["author"], "codex")
        self.assertNotIn(
            annotation["id"],
            self.review.pending_path.read_text(encoding="utf-8"),
        )

        followed_up = self.review.add_annotation_response(annotation["id"], {
            "author": "user",
            "body": "Could the labels remain on screen a little longer?",
        })
        pending = self.review.pending_path.read_text(encoding="utf-8")
        self.assertEqual(followed_up["status"], "pending")
        self.assertIn("Could the labels remain", pending)
        self.assertIn("Codex: I simplified the notation", pending)

    def test_unknown_cue_and_out_of_frame_region_are_rejected(self) -> None:
        common = {
            "phrase": "nope",
            "timestamp": 0,
            "comment": "Nope",
            "region": {"x": 0, "y": 0, "width": .2, "height": .2},
        }
        with self.assertRaisesRegex(ValueError, "Unknown narration cue"):
            self.review.save_annotation({**common, "cue": "missing"})
        with self.assertRaisesRegex(ValueError, "beyond the frame"):
            self.review.save_annotation({
                **common,
                "cue": "start",
                "region": {"x": .9, "y": 0, "width": .2, "height": .2},
            })


if __name__ == "__main__":
    unittest.main()
