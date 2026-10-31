"""Isolate each Manim job's writable render artifacts.

Manim's TeX cleanup removes other non-SVG intermediates in the same directory.
Independent renders must never share that writable directory, even when they
publish different movie names. A process-local lock alone cannot protect them
from a separately launched render.
"""
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import re
import uuid
import shutil


@dataclass(frozen=True)
class RenderJob:
    directory: Path
    media_dir: Path
    tex_dir: Path
    text_dir: Path
    manifest_path: Path
    handoff_dir: Path
    config_file: Path

    @classmethod
    def create(cls,workspace,section):
        workspace=Path(workspace).resolve()
        label=re.sub(r'[^a-zA-Z0-9_-]+','_',str(section)).strip('_') or 'scene'
        directory=workspace/'.review'/'render-jobs'/label/uuid.uuid4().hex
        media=directory/'media';tex=directory/'Tex';text=directory/'texts'
        handoffs=directory/'handoffs'
        for path in (media,tex,text,handoffs):path.mkdir(parents=True,exist_ok=True)
        configuration=ConfigParser(interpolation=None)
        project=workspace/'manim.cfg'
        if project.is_file():configuration.read(project,encoding='utf-8-sig')
        if not configuration.has_section('CLI'):configuration.add_section('CLI')
        configuration.set('CLI','tex_dir',tex.as_posix())
        configuration.set('CLI','text_dir',text.as_posix())
        configuration.set('CLI','media_dir',media.as_posix())
        config_file=directory/'manim.cfg'
        with config_file.open('w',encoding='utf-8') as stream:configuration.write(stream)
        return cls(directory,media,tex,text,directory/'objects.json',handoffs,config_file)

    def seed_handoffs(self,source):
        for path in Path(source).glob('*.json'):
            shutil.copy2(path,self.handoff_dir/path.name)

    def movie(self,scene_name,*,expected_name=None):
        expected=expected_name or (scene_name+'.mp4')
        movies=[path for path in self.media_dir.rglob(expected)
                if 'partial_movie_files' not in path.parts and 'sections' not in path.parts
                and not path.name.endswith('.tmp.mp4')]
        if len(movies)!=1:raise FileNotFoundError(f'Expected one completed Manim movie for {scene_name}; found {len(movies)}')
        return movies[0]
