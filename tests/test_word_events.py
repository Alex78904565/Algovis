import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from algovis import NarrationCue,NarrationTrack,WordEvent
from algovis.narration import file_fingerprint


class WordEventTests(unittest.TestCase):
    words=[{'word':'one','start':1.,'end':1.2},
           {'word':'then','start':2.,'end':2.2},
           {'word':'one','start':3.,'end':3.2}]

    def track(self,cue):return NarrationTrack('unused.wav',5,[cue],words=self.words)

    def test_occurrence_selects_the_second_utterance(self):
        event=self.track(NarrationCue('second',1.,'one',occurrence=2)).word_event('second')
        self.assertIsInstance(event,WordEvent)
        self.assertEqual(event.time,3.)

    def test_missing_occurrence_fails_without_falling_back(self):
        with self.assertRaisesRegex(ValueError,'no verified word alignment'):
            self.track(NarrationCue('missing',1.,'one',occurrence=3)).word_event('missing')

    def test_context_disambiguates_repeated_values(self):
        event=self.track(NarrationCue('second',1.,'one',context='then one')).word_event('second')
        self.assertEqual(event.start,3.)

    def test_equal_distance_is_ambiguous(self):
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            self.track(NarrationCue('which',2.,'one')).word_event('which')

    def test_end_edge_is_explicit(self):
        event=self.track(NarrationCue('second',3.,'one')).word_event('second',edge='end')
        self.assertEqual(event.time,3.2)

    def test_changed_transcript_has_a_different_event_fingerprint(self):
        track=self.track(NarrationCue('second',3.,'one'))
        event=track.word_event('second')
        track.words=[*track.words,{'word':'new','start':4.,'end':4.2}]
        self.assertNotEqual(event.transcript_fingerprint,track.word_event('second').transcript_fingerprint)

    def test_rerecorded_audio_cannot_use_sealed_old_alignment(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);audio=root/'voice.wav';transcript=root/'words.json';cues=root/'cues.json'
            audio.write_bytes(b'original recording')
            transcript.write_text(json.dumps({'words':self.words}))
            data={'audio':str(audio),'duration':5,'cues':[{'name':'first','time':1,'phrase':'one'}],
                  'transcriptWords':str(transcript),'alignmentProvenance':{
                      'audioSha256':file_fingerprint(audio),'transcriptSha256':file_fingerprint(transcript)}}
            cues.write_text(json.dumps(data))
            self.assertTrue(NarrationTrack.from_json(cues).alignment_provenance)
            audio.write_bytes(b'rerecorded voice')
            with self.assertRaisesRegex(ValueError,'changed after alignment'):
                NarrationTrack.from_json(cues)

    def test_changed_alignment_must_be_rebound_too(self):
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);audio=root/'voice.wav';transcript=root/'words.json';cues=root/'cues.json'
            audio.write_bytes(b'recording');transcript.write_text(json.dumps({'words':self.words}))
            data={'audio':str(audio),'duration':5,'cues':[{'name':'first','time':1,'phrase':'one'}],
                  'transcriptWords':str(transcript),'alignmentProvenance':{
                      'audioSha256':file_fingerprint(audio),'transcriptSha256':file_fingerprint(transcript)}}
            cues.write_text(json.dumps(data));transcript.write_text(json.dumps({'words':self.words[:-1]}))
            with self.assertRaisesRegex(ValueError,'changed after alignment'):
                NarrationTrack.from_json(cues)

    def test_publication_rechecks_a_recording_changed_after_the_render(self):
        from algovis.review.server import ReviewServer
        with TemporaryDirectory(dir=Path.cwd()/'.qa') as folder:
            root=Path(folder);audio=root/'voice.wav';transcript=root/'words.json';cues=root/'cues.json'
            audio.write_bytes(b'recording');transcript.write_text(json.dumps({'words':self.words}))
            cues.write_text(json.dumps({'audio':str(audio),'duration':5,
                'cues':[{'name':'first','time':1,'phrase':'one'}],'transcriptWords':str(transcript),
                'alignmentProvenance':{'audioSha256':file_fingerprint(audio),
                                       'transcriptSha256':file_fingerprint(transcript)}}))
            reviewer=ReviewServer(root,'test','test',root/'video.mp4',cues)
            audio.write_bytes(b'new voice')
            with self.assertRaisesRegex(ValueError,'changed after alignment'):
                reviewer._validate_render_timing()


if __name__=='__main__':unittest.main()
