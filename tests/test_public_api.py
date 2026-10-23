import unittest

import algovis


class PublicApiTests(unittest.TestCase):
    def test_version_is_exposed(self):
        self.assertEqual(algovis.__version__, "0.1.0")

    def test_primary_authoring_components_are_exposed(self):
        for name in (
            "SlideScene",
            "NarrationTrack",
            "RecursiveTree",
            "DPTable",
            "BellmanDerivation",
            "InductiveProof",
            "RecursionMemoComparison",
        ):
            self.assertTrue(hasattr(algovis, name), name)

    def test_recursive_tree_supports_subtree_collapse(self):
        self.assertTrue(hasattr(algovis.RecursiveTree, "collapse_to_backbone"))
        self.assertTrue(hasattr(
            algovis.RecursiveTree,
            "get_backbone_collapse_animations",
        ))
        self.assertTrue(hasattr(algovis.RecursiveTree, "set_state_colors"))


if __name__ == "__main__":
    unittest.main()
