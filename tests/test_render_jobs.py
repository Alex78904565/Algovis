from configparser import ConfigParser
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import json
import subprocess
from unittest.mock import patch
from algovis.rendering import RenderJob
from algovis.review.server import ReviewServer


class RenderJobTests(unittest.TestCase):
    def test_jobs_have_distinct_writable_tex_directories(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            a=RenderJob.create(folder,'same section');b=RenderJob.create(folder,'same section')
            self.assertNotEqual(a.tex_dir,b.tex_dir)
            self.assertNotEqual(a.text_dir,b.text_dir)
            self.assertNotEqual(a.media_dir,b.media_dir)
            self.assertTrue(a.tex_dir.is_dir());self.assertTrue(b.tex_dir.is_dir())
            self.assertTrue(a.tex_dir.is_relative_to(Path(folder).resolve()))

    def test_project_configuration_is_preserved_without_editing_its_source(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);project=root/'manim.cfg'
            original='[CLI]\nbackground_color = #123456\nframe_rate = 24\ntex_dir = shared/Tex\n'
            project.write_text(original)
            job=RenderJob.create(root,'proof')
            config=ConfigParser(interpolation=None);config.read(job.config_file)
            self.assertEqual(config['CLI']['frame_rate'],'24')
            self.assertEqual(config['CLI']['background_color'],'#123456')
            self.assertEqual(Path(config['CLI']['tex_dir']),job.tex_dir)
            self.assertEqual(Path(config['CLI']['text_dir']),job.text_dir)
            self.assertEqual(project.read_text(),original)

    def test_reviewer_passes_isolated_config_to_manim(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);source=root/'scene.py';source.write_text('')
            reviewer=ReviewServer(root,'proof','Proof',root/'movie.mp4',root/'cues.json',
                                  scene_source=source,scene_name='Proof')
            job=RenderJob.create(root,'proof')
            command=reviewer._render_command(config_file=job.config_file)
            index=command.index('--config_file')
            self.assertEqual(Path(command[index+1]),job.config_file)
            self.assertIn('--disable_caching',command)

    def test_original_launcher_catalog_uses_the_same_safe_source_path(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);source=root/'full_video_preview.py';source.write_text('')
            (root/'render_sections.ps1').write_text('')
            reviewer=ReviewServer(root,'proof','Proof',root/'movie.mp4',root/'cues.json',scene_name='Proof')
            self.assertEqual(reviewer.scene_source,source.resolve())
            job=RenderJob.create(root,'proof')
            self.assertIn('--config_file',reviewer._render_command(config_file=job.config_file))

    def test_handoff_seeds_do_not_share_writable_files(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);seed=root/'previous';seed.mkdir()
            (seed/'earlier.json').write_text('original')
            a=RenderJob.create(root,'a');b=RenderJob.create(root,'b')
            a.seed_handoffs(seed);b.seed_handoffs(seed)
            (a.handoff_dir/'earlier.json').write_text('changed')
            self.assertEqual((b.handoff_dir/'earlier.json').read_text(),'original')
            self.assertEqual((seed/'earlier.json').read_text(),'original')

    def test_only_completed_movie_is_selected(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            job=RenderJob.create(folder,'proof')
            partial=job.media_dir/'videos/partial_movie_files/Proof/Proof.mp4'
            partial.parent.mkdir(parents=True);partial.write_bytes(b'partial')
            with self.assertRaises(FileNotFoundError):job.movie('Proof')
            movie=job.media_dir/'videos/Proof.mp4';movie.write_bytes(b'complete')
            self.assertEqual(job.movie('Proof'),movie)

    def test_a_missing_new_manifest_cannot_reuse_an_old_success(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);cues=root/'cues.json';cues.write_text(json.dumps({'cues':[]}))
            reviewer=ReviewServer(root,'proof','Proof',root/'old.mp4',cues,scene_name='Proof')
            reviewer.manifest_path.parent.mkdir(parents=True,exist_ok=True)
            reviewer.manifest_path.write_text('{}')
            old_manifest=reviewer.manifest_path
            with patch.object(reviewer,'_render_command',return_value=['fake']), \
                 patch('algovis.review.server.subprocess.run',return_value=subprocess.CompletedProcess([],0,'','')), \
                 patch.object(reviewer,'_publish_render') as publish:
                reviewer._render_once()
            publish.assert_not_called()
            self.assertEqual(reviewer.manifest_path,old_manifest)
            self.assertIn('fresh object manifest',reviewer.render_status.log_tail)

    def test_published_movie_owns_an_immutable_matching_manifest(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);source=root/'scene.py';source.write_text('')
            reviewer=ReviewServer(root,'proof','Proof',root/'old.mp4',root/'cues.json',
                                  scene_source=source,scene_name='Proof')
            job=RenderJob.create(root,'proof');reviewer._active_render_job=job
            movie=job.media_dir/'videos/Proof.mp4';movie.parent.mkdir(parents=True);movie.write_bytes(b'movie')
            job.manifest_path.write_text(json.dumps({'version':'new'}))
            reviewer._publish_render()
            self.assertEqual(reviewer.manifest_path,reviewer.video_path.with_suffix('.objects.json'))
            reviewer.base_manifest_path.write_text(json.dumps({'version':'later unfinished render'}))
            self.assertEqual(json.loads(reviewer.manifest_path.read_text())['version'],'new')
