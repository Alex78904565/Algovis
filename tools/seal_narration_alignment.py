"""Bind already verified timestamped words to their exact recording bytes.

This does not align or certify speech. Use --seal only after alignment review;
a later edit to either file requires realignment/review and another explicit seal.
Without --seal, print the current fingerprints without modifying the cue file.
"""
import argparse
import json
from pathlib import Path

from algovis.narration import NarrationTrack,file_fingerprint


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cues',nargs='+',type=Path)
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--seal',action='store_true')
    parser.add_argument('--manifest-dir',type=Path,
                        help='Validate the cue declarations in previously checked render manifests')
    args=parser.parse_args()
    for path in args.cues:
        data=json.loads(path.read_text(encoding='utf-8'))
        audio=args.root/data['audio'];words=args.root/data['transcriptWords']
        # Rebinding deliberately clears a stale seal, but exact cue selection
        # still must succeed. No guessed/approximate anchors are accepted.
        unsealed={key:value for key,value in data.items() if key!='alignmentProvenance'}
        from algovis.review.audit import timed_words
        from algovis.narration import NarrationCue
        track=NarrationTrack(audio,data['duration'],[
            NarrationCue(c['name'],c['time'],c.get('phrase',''),c.get('occurrence'),c.get('context',''))
            for c in unsealed['cues']],words=timed_words(json.loads(words.read_text(encoding='utf-8'))))
        if args.manifest_dir:
            section=data.get('section',path.name.removesuffix('.cues.json'))
            manifest=json.loads((args.manifest_dir/(section+'.objects.json')).read_text(encoding='utf-8'))
            declared={event['cue'] for event in manifest.get('plays',[]) if event.get('cue') and
                      (event.get('wordTiming') or event.get('wordSequence'))}
            declared.update(event['cue'] for event in manifest.get('viewInfrastructure',{}).get('steps',[])
                            if event.get('cue') and event.get('completed'))
            for cue in declared:track.word_event(cue)
        provenance={'audioSha256':file_fingerprint(audio),'transcriptSha256':file_fingerprint(words)}
        print(path,provenance)
        if args.seal:
            data['alignmentProvenance']=provenance
            path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
