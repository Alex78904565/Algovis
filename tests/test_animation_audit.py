import unittest

from algovis.review.audit import audit_section, content_change, phrase_anchor, timed_words, tokens


class WordLevelAuditTests(unittest.TestCase):
    def test_declared_peer_size_regression_is_included_once(self):
        snapshot={'time':2,'objects':[
            {'id':'a','label':'general','typographyGroup':'runtime','typeRole':'equation','fontSize':34},
            {'id':'b','label':'example','typographyGroup':'runtime','typeRole':'equation','fontSize':28}]}
        manifest={'animations':[],'plays':[{'start':0,'end':1,'before':[],'after':[]}],
                  'snapshots':[snapshot,{**snapshot,'time':3}]}
        findings=audit_section(manifest,{'cues':[]},{'words':[]})['findings']
        self.assertEqual([f['kind'] for f in findings],['peer_font_size_mismatch'])

    def manifest(self, start, trigger=None):
        return {"frameRate":15,"animations":[{
            "id":"pulse-1","play":0,"kind":"Pulse","start":start,"end":start+.6,
            "cue":"broad_phrase","label":"f(5)","attention":{"trigger":trigger},
        }],"plays":[{"start":start,"end":start+.6,"before":[],"after":[]}]}

    def audit(self,start,trigger=None):
        return audit_section(self.manifest(start,trigger),
                             {"cues":[{"name":"broad_phrase","phrase":"already","time":1}]},
                             {"segments":[{"words":[
                                 {"word":"already","start":1,"end":1.5},
                                 {"word":"f(5)","start":3,"end":3.6},
                             ]}]})

    def test_inherited_cue_does_not_approve_an_unjustified_pulse(self):
        report=self.audit(1)
        self.assertIn("attention_without_declared_trigger",report['events'][0]['findings'])

    def test_pulse_must_follow_the_referenced_word_not_a_broad_phrase(self):
        self.assertIn('attention_before_word',self.audit(1,'f of five')['events'][0]['findings'])
        self.assertEqual(self.audit(3,'f of five')['events'][0]['findings'],[])
        self.assertIn('attention_after_word',self.audit(4,'f of five')['events'][0]['findings'])

    def test_approximate_math_alignment_is_not_certified_as_exact(self):
        words=[{'word':'f(5)','start':3,'end':4,'reviewed_timing':'approximate'}]
        self.assertTrue(phrase_anchor('f of five',words,3)['approximate'])

    def test_removing_and_recreating_text_is_distinct_from_moving_it(self):
        before=[{'id':'same','label':'retained equation'}]
        kept=content_change(before,[{'id':'same','label':'retained equation'}])
        replaced=content_change(before,[{'id':'new','label':'retained equation'}])
        self.assertEqual(kept['retainedFraction'],1)
        self.assertEqual(replaced['retainedFraction'],0)

    def test_repeated_asr_context_does_not_duplicate_words(self):
        word={'word':'answer','start':1,'end':2}
        self.assertEqual(len(timed_words({'segments':[{'words':[word]},{'words':[word]}]})),1)

    def test_pre_and_post_snapshots_from_earlier_instrumentation_are_supported(self):
        manifest = self.manifest(3, 'f of five')
        for side in ('before', 'after'):
            manifest['plays'][0][side] = {'objects': []}
        report = audit_section(manifest, {'cues': []}, {'words': []})
        self.assertEqual(report['changes'][0]['retainedFraction'], 1)

    def test_math_subscript_spelling_matches_spoken_letters(self):
        words = [{'word':'vi', 'start':2, 'end':2.5}]
        self.assertEqual(phrase_anchor('v i', words, 2)['start'], 2)

    def test_hyphenated_asr_continuations_keep_their_word_onset(self):
        for first, second in [('long', '-term'), ('top', '-down'), ('bottom', '-up')]:
            with self.subTest(first=first):
                words = [{'word':first, 'start':2, 'end':2.2},
                         {'word':second, 'start':2.2, 'end':2.5}]
                anchor = phrase_anchor(first+second, words, 2)
                self.assertEqual((anchor['start'],anchor['end']), (2,2.5))
        self.assertEqual(tokens('-2'), ['minus','two'])
        self.assertEqual(tokens('n-1'), ['n','minus','one'])

    def test_content_reveal_is_checked_independently_of_a_correct_later_pulse(self):
        manifest = self.manifest(3, 'f of five')
        manifest['animations'].append({'id':'reveal','play':1,'kind':'FadeIn',
                                       'start':1,'end':1.5,'label':'value'})
        manifest['plays'].append({'start':1,'end':1.5,'before':[],'after':[],
                                 'wordTiming':{'trigger':'f of five','time':3}})
        report = audit_section(manifest, {'cues':[]},
                               {'words':[{'word':'f(5)','start':3,'end':3.6}]})
        self.assertEqual(report['events'][0]['findings'], [])
        self.assertIn('content_before_word', report['changes'][1]['findings'])

    def test_declared_content_trigger_is_reported_with_its_narration_offset(self):
        timing={'trigger':'answer', 'time':2, 'narrationStart':5}
        manifest={'frameRate':15,
                  'animations':[{'id':'reveal','play':0,'kind':'FadeIn',
                                 'start':7,'end':7.5,'label':'value','wordTiming':timing}],
                  'plays':[{'start':7,'end':7.5,'before':[],'after':[],'wordTiming':timing}]}
        report=audit_section(manifest, {'cues':[]},
                             {'words':[{'word':'answer','start':2,'end':2.3}]})
        self.assertEqual(report['events'][0]['triggerPhrase'],'answer')
        self.assertEqual(report['events'][0]['anchor']['start'],7)
        self.assertEqual(report['findings'],[])


if __name__=='__main__':
    unittest.main()
