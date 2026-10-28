"""Inspect real last/first video frames across independently rendered sections.

Run after rendering and before assembly. This complements, rather than replaces,
watching the surrounding transition and checking its narration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def compare_frames(previous, following, *, ignore_regions=(), tolerance=16):
    """Measure a cut; explicit normalized exclusions are recorded by the caller."""
    a, b = np.asarray(previous.convert('RGB')), np.asarray(following.convert('RGB'))
    if a.shape != b.shape:
        return {'status': 'fail', 'reason': 'different frame dimensions'}
    height, width = a.shape[:2]
    mask = np.ones((height, width), dtype=bool)
    for region in ignore_regions:
        x, y, w, h = (float(region[k]) for k in ('x','y','width','height'))
        if min(x,y,w,h) < 0 or x+w > 1 or y+h > 1:
            raise ValueError('Continuity exclusions must be normalized rectangles inside the frame')
        mask[int(y*height):int(np.ceil((y+h)*height)), int(x*width):int(np.ceil((x+w)*width))] = False
    if not mask.any():
        raise ValueError('Continuity audit cannot exclude the entire frame')
    raw_delta = np.abs(a.astype(float)-b.astype(float))[mask]
    # An ending P-frame and opening I-frame quantize sharp text differently,
    # even when their native Manim artwork is identical. Suppress single-pixel
    # codec ringing for this geometric cut check; retain raw metrics as evidence.
    radius = height/480
    aa = np.asarray(previous.convert('RGB').filter(ImageFilter.GaussianBlur(radius)),dtype=float)
    bb = np.asarray(following.convert('RGB').filter(ImageFilter.GaussianBlur(radius)),dtype=float)
    delta = np.abs(aa-bb)[mask]
    changed = float(np.mean(np.max(delta, axis=1) > tolerance))
    mean = float(delta.mean())
    return {'status': 'pass' if changed <= .002 and mean <= 1 else 'fail',
            'meanChannelDifference': float(raw_delta.mean()),
            'rawChangedPixelFraction': float(np.mean(np.max(raw_delta,axis=1)>tolerance)),
            'comparisonMeanDifference': mean, 'changedPixelFraction': changed,
            'blurRadiusPixels': radius,
            'pixelTolerance': tolerance, 'comparedPixels': int(mask.sum())}


def compare_video_cut(previous, following, output, *, ignore_regions=()):
    """A publication gate for one newly rendered successor; retain evidence."""
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    paths=[]
    for tag,video in [('previous',Path(previous)),('following',Path(following))]:
        stream=json.loads(subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'stream=duration,avg_frame_rate','-of','json',str(video)]))['streams'][0]
        n,d=map(float,stream['avg_frame_rate'].split('/'))
        time=max(0,float(stream['duration'])-d/n) if tag=='previous' else 0
        path=output/(tag+'.png')
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(time),'-i',str(video),
                        '-frames:v','1',str(path)],check=True)
        paths.append(path)
    result=compare_frames(Image.open(paths[0]),Image.open(paths[1]),ignore_regions=ignore_regions)
    result.update(previous=str(previous),following=str(following),ignoreRegions=ignore_regions)
    return result


def inspect_catalog(catalog_path, output, *, workspace=None):
    root = Path(workspace or Path.cwd()).resolve()
    catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    sections = catalog['sections']; captures = {}; results = []
    for section in sections:
        sid = section['id']; video = root/section['renderedVideo']
        stream = json.loads(subprocess.check_output([
            'ffprobe','-v','error','-select_streams','v:0','-show_entries',
            'stream=duration,avg_frame_rate','-of','json',str(video)]))['streams'][0]
        numerator, denominator = map(float, stream['avg_frame_rate'].split('/'))
        fps = numerator/denominator; duration = float(stream['duration'])
        frames = {}
        for tag, time in [('closing',max(0,duration-.5)), ('end',max(0,duration-1/fps)),
                          ('start',0),('early',.2),('middle',.5),('settled',1.2)]:
            path = output/f'{sid}-{tag}.png'
            subprocess.run(['ffmpeg','-v','error','-y','-ss',str(time),'-i',str(video),
                            '-frames:v','1',str(path)],check=True)
            if not path.exists():
                raise ValueError(f'No decoded frame at {time}: {video}')
            frames[tag] = {'path':str(path.resolve()),'time':time}
        captures[sid] = {'video':str(video),'videoHash':hashlib.sha256(video.read_bytes()).hexdigest(),
                         'duration':duration,'frames':frames}
    ignores = catalog.get('continuityIgnoreRegions',[])
    for index,(previous,following) in enumerate(zip(sections,sections[1:])):
        a,b = captures[previous['id']],captures[following['id']]
        comparison = compare_frames(Image.open(a['frames']['end']['path']),
                                    Image.open(b['frames']['start']['path']),ignore_regions=ignores)
        board = Image.new('RGB',(1920,800),(22,22,22)); draw = ImageDraw.Draw(board)
        tiles = [(a,'closing'),(a,'end'),(b,'start'),(b,'early'),(b,'middle'),(b,'settled')]
        for position,(clip,tag) in enumerate(tiles):
            x=(position%3)*640;y=(position//3)*400
            frame=clip['frames'][tag]
            board.paste(Image.open(frame['path']).resize((640,360)),(x,y+30))
            draw.text((x+8,y+7),f"{Path(clip['video']).stem} {tag} {frame['time']:.2f}s",fill='white')
        evidence=output/f'join-{index+1:02d}.jpg';board.save(evidence,quality=92)
        results.append({'from':previous['id'],'to':following['id'],**comparison,
                        'ignoreRegions':ignores,'evidence':str(evidence.resolve())})
    report={'sections':captures,'joins':results,'allCutsMatch':all(r['status']=='pass' for r in results),
            'scope':'Decoded last/first frame continuity, plus surrounding frame boards for visual inspection; no perceptual audio signoff.'}
    (output/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();report=inspect_catalog(args.catalog,args.output)
    for join in report['joins']:
        print(f"{join['from']} -> {join['to']}: {join['status']}")
    return 0 if report['allCutsMatch'] else 1


if __name__=='__main__':
    raise SystemExit(main())
