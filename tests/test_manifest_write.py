import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from algovis import SlideScene


class ManifestWriteTests(unittest.TestCase):
    def standin(self, path):
        return SimpleNamespace(
            _review_manifest_path=str(path),
            _capture_review_snapshot=lambda: None,
            _review_snapshots=[], _review_animations=[], _review_plays=[],
        )

    def test_transient_reader_lock_retries_atomic_replacement(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text('{"old":true}', encoding='utf-8')
            replace = os.replace
            attempts = []

            def locked_once(source, destination):
                attempts.append(True)
                if len(attempts) == 1:
                    self.assertEqual(json.loads(path.read_text()), {'old': True})
                    raise PermissionError('reader holds the previous manifest')
                replace(source, destination)

            with patch('algovis.presentation.os.replace', side_effect=locked_once), patch('algovis.presentation.time.sleep'):
                SlideScene._write_review_manifest(self.standin(path))
            self.assertEqual(len(attempts), 2)
            self.assertEqual(json.loads(path.read_text())['plays'], [])

    def test_permanent_lock_preserves_previous_manifest_and_reports_failure(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'manifest.json'
            path.write_text('{"old":true}', encoding='utf-8')
            with patch('algovis.presentation.os.replace', side_effect=PermissionError('locked')) as replace, patch('algovis.presentation.time.sleep'):
                with self.assertRaises(PermissionError):
                    SlideScene._write_review_manifest(self.standin(path))
            self.assertEqual(replace.call_count, 4)
            self.assertEqual(json.loads(path.read_text()), {'old': True})
