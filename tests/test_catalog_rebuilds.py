import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from algovis.review.server import ReviewCatalog, ReviewServer


class CatalogRebuildTests(unittest.TestCase):
    def make_catalog(self, root):
        self.requests = []
        reviews = {}
        for sid, source in [('a', 'lesson.py'), ('b', 'lesson.py'), ('c', 'other.py')]:
            reviews[sid] = SimpleNamespace(
                scene_name=sid, scene_source=root/source,
                cue_path=root/(sid+'.json'), transcript_path=None, audio_path=None,
                request_render=Mock(side_effect=lambda key=sid: self.requests.append(key)))
        catalog = ReviewCatalog(reviews, 'a', 'test')
        catalog.active_section = 'b'
        return catalog

    def test_shared_component_edit_rebuilds_every_clip_with_the_open_clip_requested_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            self.assertEqual(catalog.queue_source_changes([root/'algovis/frames.py']), ['b', 'a', 'c'])
            self.assertEqual(self.requests, ['b', 'a', 'c'])

    def test_a_scene_file_rebuilds_every_section_using_that_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            self.assertEqual(catalog.queue_source_changes([root/'lesson.py']), ['b', 'a'])
            catalog.reviews['c'].request_render.assert_not_called()

    def test_a_section_timing_edit_does_not_invalidate_unrelated_clips(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = self.make_catalog(root)
            self.assertEqual(catalog.queue_source_changes([root/'c.json']), ['c'])

    def test_editing_a_queued_scene_coalesces_but_editing_a_running_scene_requests_another_pass(self):
        review = object.__new__(ReviewServer)
        review.scene_name = 'Example'
        review._render_lock = threading.Lock()
        review.render_status = SimpleNamespace(state='rendering')
        review._render_started = False
        review._render_requested = False
        self.assertFalse(review.request_render())
        self.assertFalse(review._render_requested)
        review._render_started = True
        self.assertFalse(review.request_render())
        self.assertTrue(review._render_requested)

    def test_continuation_rebuilds_follow_the_artwork_dependency_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); catalog = self.make_catalog(root)
            catalog = ReviewCatalog(catalog.reviews, 'a', 'test', continuations={'b':'a','c':'b'})
            catalog.active_section = 'c'
            self.assertEqual(catalog.queue_source_changes([root/'a.json']), ['a','b','c'])
            self.assertIs(catalog.reviews['c']._continuation_parent, catalog.reviews['b'])
            self.assertEqual(self.requests, ['a','b','c'])

    def test_continuation_cycles_or_reversed_dependencies_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            catalog = self.make_catalog(Path(directory))
            with self.assertRaisesRegex(ValueError, 'catalog order'):
                ReviewCatalog(catalog.reviews, 'a', 'test', continuations={'a':'b'})

    def test_successor_waits_outside_manim_lock_until_predecessor_finishes(self):
        parent_entered, release_parent, child_entered = threading.Event(), threading.Event(), threading.Event()
        parent, child = object.__new__(ReviewServer), object.__new__(ReviewServer)
        for review in (parent, child):
            review._render_lock = threading.Lock()
            review.render_status = SimpleNamespace(state='rendering', message='', started_at=None)
        child._continuation_parent = parent
        def parent_work():
            parent_entered.set(); release_parent.wait(2); parent.render_status.state = 'ready'
        parent._render_once, child._render_once = parent_work, child_entered.set
        one, two = threading.Thread(target=parent._render_worker), threading.Thread(target=child._render_worker)
        two.start(); one.start()
        self.assertTrue(parent_entered.wait(2))
        try:
            self.assertFalse(child_entered.wait(.05))
        finally:
            release_parent.set(); one.join(2); two.join(2)
        self.assertTrue(child_entered.is_set())

    def test_manual_and_catalog_renders_cannot_enter_manim_at_the_same_time(self):
        first_entered, release_first, second_entered = threading.Event(), threading.Event(), threading.Event()
        first, second = object.__new__(ReviewServer), object.__new__(ReviewServer)
        for review in (first, second):
            review._render_lock = threading.Lock()
            review.render_status = SimpleNamespace(message='', started_at=None)
        def first_work():
            first_entered.set()
            release_first.wait(2)
        first._render_once, second._render_once = first_work, second_entered.set
        one, two = threading.Thread(target=first._render_worker), threading.Thread(target=second._render_worker)
        one.start()
        self.assertTrue(first_entered.wait(2))
        two.start()
        try:
            self.assertFalse(second_entered.wait(.05))
        finally:
            release_first.set()
            one.join(2);two.join(2)
        self.assertTrue(second_entered.is_set())
        self.assertFalse(one.is_alive())
        self.assertFalse(two.is_alive())


if __name__ == '__main__':
    unittest.main()
