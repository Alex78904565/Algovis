import unittest
from algovis.review.typography_source import Source, audit_source, require_scene_typography
from pathlib import Path
from tempfile import TemporaryDirectory


class TypographySourceTests(unittest.TestCase):
    def test_unregistered_operator_scale_is_detected(self):
        report=audit_source('''
from manim import MathTex
class Lesson:
 def construct(self):
  times = MathTex(r"\\times").scale(.86)
''', scene='Lesson')
        self.assertEqual(report['counts'], {'manual_text_scale': 1})
        self.assertEqual(report['findings'][0]['disposition'], 'migration_required')

    def test_all_parent_methods_and_called_helpers_are_in_scope(self):
        source='''
def caption():
 return Text("caption",font_size=18)
class Lesson:
 def first(self):
  caption()
  MathTex("f(n)").scale(.7)
 def unused_legacy(self):
  Text("old",font_size=9)
class Clip(Lesson):
 def construct(self): self.first()
'''
        report=audit_source(source,scene='Clip')
        self.assertEqual(report['counts'], {'absolute_font_size':1, 'manual_text_scale':1})
        self.assertNotIn('Lesson.unused_legacy', report['reachableFunctions'])

    def test_aliases_and_assigned_text_are_detected(self):
        report=audit_source('''
from manim import MathTex as Formula
class Lesson:
 def construct(self):
  call=Formula("f(i)")
  call.scale(.8)
''',scene='Lesson')
        self.assertEqual(report['findings'][0]['subject'],'text')

    def test_grouped_text_cannot_hide_a_scale(self):
        report=audit_source('''
class Lesson:
 def construct(self):
  a=MathTex("a")
  b=MathTex("b")
  row=VGroup(a,b)
  row.scale(.7)
''',scene='Lesson')
        self.assertEqual(report['findings'][0]['category'],'manual_text_scale')

    def test_property_setters_cannot_hide_text_sizing(self):
        report=audit_source('''
class Lesson:
 def construct(self):
  call=MathTex("f(i)")
  call.font_size=42
  call.width=8
''',scene='Lesson')
        self.assertEqual(report['counts'],{'absolute_font_size':1,'manual_text_scale':1})

    def test_unknown_and_diagram_geometry_require_separate_review(self):
        report=audit_source('''
class Lesson:
 def construct(self):
  tree=RecursiveTree(factory)
  tree.scale_to_fit_width(8)
  unknown.scale(.7)
''',scene='Lesson')
        self.assertEqual([r['disposition'] for r in report['findings']],
                         ['component_geometry_review','classification_required'])

    def test_scene_defaults_and_relative_overrides_are_distinguished(self):
        report=audit_source('''
class Lesson:
 def construct(self):
  view=ColumnSlide()
  view.add("equation", MathRow({"f":"f(i)"}))
  view.add("note", "Supporting note",font_scale=.85)
''',scene='Lesson')
        self.assertEqual(report['counts'],{'relative_font_override':1})
        self.assertEqual(report['findings'][0]['disposition'],'relative_override_review')

    def test_size_check_does_not_depend_on_watch_registration(self):
        qa=Path.cwd()/'.qa'
        qa.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=qa) as folder:
            path=Path(folder)/'lesson.py'
            path.write_text('class Lesson:\n def construct(self):\n  MathTex("x").scale(.86)\n')
            with self.assertRaisesRegex(ValueError,'Scene typography migration required'):
                require_scene_typography(path,'Lesson')

    def test_missing_scene_is_incomplete_instead_of_silently_passing(self):
        with self.assertRaisesRegex(ValueError,'Cannot locate'):
            audit_source('class Lesson: pass',scene='Lesson')

    def test_parked_code_after_return_does_not_pollute_active_inventory(self):
        report=audit_source('''
class Lesson:
 def construct(self):
  view=ColumnSlide()
  view.add("text", "An explanation")
  return
  MathTex("old").scale(.2)
''',scene='Lesson')
        self.assertEqual(report['findings'],[])


if __name__=='__main__': unittest.main()
