import unittest
from algovis.review.inspection import focus_span_findings


class FocusLifetimeTests(unittest.TestCase):
    def manifest(self):
        return {'frameRate':15,'focusSpans':[{'object':'box','cue':'refer','target':'f(i+1,w)',
            'start':1,'end':5,'revealDuration':.5,'releaseDuration':.25}],
            'snapshots':[{'time':2,'objects':[{'id':'box','opacity':1}]},
                         {'time':4.8,'objects':[{'id':'box','opacity':1}]},
                         {'time':5.4,'objects':[]}]}

    def test_box_survives_the_explanation_and_retires_at_its_named_cue(self):
        self.assertEqual(focus_span_findings(self.manifest()),[])

    def test_a_brief_flash_cannot_pass_as_a_held_explanation(self):
        manifest=self.manifest()
        manifest['snapshots'][1]['objects']=[]
        self.assertEqual(focus_span_findings(manifest)[0]['kind'],'focus_removed_before_explanation_ends')

    def test_an_unexecuted_release_and_a_lingering_box_are_rejected(self):
        manifest=self.manifest()
        del manifest['focusSpans'][0]['releaseDuration']
        self.assertEqual(focus_span_findings(manifest)[0]['kind'],'focus_release_cue_not_executed')
        manifest=self.manifest()
        manifest['snapshots'][-1]['objects']=[{'id':'box','opacity':1}]
        self.assertEqual(focus_span_findings(manifest)[0]['kind'],'focus_lingers_after_release')

    def test_an_unrecorded_box_is_not_treated_as_verified(self):
        manifest=self.manifest();manifest['focusSpans'][0]['object']=None
        self.assertEqual(focus_span_findings(manifest)[0]['kind'],'focus_never_rendered')
