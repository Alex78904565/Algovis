import tempfile
import unittest
from pathlib import Path
from algovis.review.media import completed_render


class PreviewAssemblyTests(unittest.TestCase):
    def test_assembly_reads_an_immutable_completed_review_revision(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix=".test-preview-assembly-") as directory:
            root = Path(directory)
            revisions = root / ".review" / "renders" / "sample"
            revisions.mkdir(parents=True)
            completed = revisions / "sample.1.mp4"
            completed.write_bytes(b"completed revision")
            self.assertEqual(completed_render(root, "Scene", "sample", video_dir=root / "video"), completed)

    def test_direct_scene_render_remains_supported_without_review_revisions(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix=".test-preview-assembly-") as directory:
            root = Path(directory)
            self.assertEqual(completed_render(root, "Scene", "sample", video_dir=root / "video"),
                             root / "video" / "Scene.mp4")

    def test_unfinished_publication_is_not_used_for_assembly(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd(), prefix=".test-preview-assembly-") as directory:
            root = Path(directory)
            revisions = root / ".review" / "renders" / "sample"
            revisions.mkdir(parents=True)
            (revisions / "sample.new.tmp.mp4").write_bytes(b"unfinished")
            self.assertEqual(completed_render(root, "Scene", "sample", video_dir=root / "video"),
                             root / "video" / "Scene.mp4")
