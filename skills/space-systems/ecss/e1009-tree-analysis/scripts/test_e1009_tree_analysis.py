"""
Gate-3 contract tests for e1009_tree_analysis_logic.py.

Run:  python3 test_e1009_tree_analysis.py
Expected output: OK
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1009_tree_analysis_logic import (
    TransformationTree,
    FrameNode,
    identity_4x4,
    mat_mul_4x4,
    build_transform,
    invert_homogeneous,
    _invert_homogeneous,
)

_EPS = 1e-9


def _close(a: float, b: float, eps: float = _EPS) -> bool:
    return abs(a - b) < eps


def _mat_close(A, B, eps: float = _EPS) -> bool:
    return all(_close(a, b, eps) for a, b in zip(A, B))


# ---------------------------------------------------------------------------
# Identity matrix tests
# ---------------------------------------------------------------------------

class TestIdentityMatrix(unittest.TestCase):
    def test_diagonal_entries_are_one(self):
        I = identity_4x4()
        for i in range(4):
            self.assertAlmostEqual(I[i * 4 + i], 1.0)

    def test_off_diagonal_entries_are_zero(self):
        I = identity_4x4()
        for i in range(4):
            for j in range(4):
                if i != j:
                    self.assertAlmostEqual(I[i * 4 + j], 0.0)

    def test_length_is_sixteen(self):
        self.assertEqual(len(identity_4x4()), 16)


# ---------------------------------------------------------------------------
# Matrix multiplication tests
# ---------------------------------------------------------------------------

class TestMatMul4x4(unittest.TestCase):
    def test_identity_times_identity_is_identity(self):
        I = identity_4x4()
        self.assertTrue(_mat_close(mat_mul_4x4(I, I), I))

    def test_wrong_size_A_raises(self):
        with self.assertRaises(ValueError):
            mat_mul_4x4([1.0] * 9, identity_4x4())

    def test_wrong_size_B_raises(self):
        with self.assertRaises(ValueError):
            mat_mul_4x4(identity_4x4(), [1.0] * 4)

    def test_known_product(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        A = build_transform(R, [1.0, 0.0, 0.0])
        B = build_transform(R, [0.0, 2.0, 0.0])
        C = mat_mul_4x4(A, B)
        expected = build_transform(R, [1.0, 2.0, 0.0])
        self.assertTrue(_mat_close(C, expected))


# ---------------------------------------------------------------------------
# build_transform tests
# ---------------------------------------------------------------------------

class TestBuildTransform(unittest.TestCase):
    def test_pure_translation_stored_correctly(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        T = build_transform(R, [3.0, 4.0, 5.0])
        self.assertAlmostEqual(T[3], 3.0)
        self.assertAlmostEqual(T[7], 4.0)
        self.assertAlmostEqual(T[11], 5.0)
        self.assertAlmostEqual(T[15], 1.0)

    def test_bad_rotation_shape_raises(self):
        with self.assertRaises(ValueError):
            build_transform([[1, 0], [0, 1]], [0.0, 0.0, 0.0])

    def test_bad_translation_length_raises(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        with self.assertRaises(ValueError):
            build_transform(R, [0.0, 0.0])


# ---------------------------------------------------------------------------
# Homogeneous-transform inverse tests
# ---------------------------------------------------------------------------

class TestInvertHomogeneous(unittest.TestCase):
    def test_invert_identity_gives_identity(self):
        I = identity_4x4()
        self.assertTrue(_mat_close(invert_homogeneous(I), I))

    def test_T_times_inv_T_is_identity(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        T = build_transform(R, [1.0, 2.0, 3.0])
        composed = mat_mul_4x4(T, invert_homogeneous(T))
        self.assertTrue(_mat_close(composed, identity_4x4()))

    def test_inv_T_times_T_is_identity(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        T = build_transform(R, [7.0, -3.0, 0.5])
        composed = mat_mul_4x4(invert_homogeneous(T), T)
        self.assertTrue(_mat_close(composed, identity_4x4()))

    def test_private_alias_is_same_function(self):
        I = identity_4x4()
        self.assertTrue(_mat_close(_invert_homogeneous(I), I))


# ---------------------------------------------------------------------------
# FrameNode tests
# ---------------------------------------------------------------------------

class TestFrameNode(unittest.TestCase):
    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            FrameNode("")

    def test_default_transform_is_identity(self):
        n = FrameNode("SC")
        self.assertTrue(_mat_close(n.transform_to_parent, identity_4x4()))

    def test_custom_transform_stored(self):
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        T = build_transform(R, [1.0, 2.0, 3.0])
        n = FrameNode("Panel", parent="SC", transform_to_parent=T)
        self.assertTrue(_mat_close(n.transform_to_parent, T))


# ---------------------------------------------------------------------------
# TransformationTree structural tests
# ---------------------------------------------------------------------------

class TestTransformationTreeStructure(unittest.TestCase):

    def _simple_tree(self) -> TransformationTree:
        """Root → A → B, all identity transforms."""
        tree = TransformationTree()
        tree.add_node("Root")
        tree.add_node("A", parent="Root")
        tree.add_node("B", parent="A")
        return tree

    def test_root_is_detected(self):
        self.assertEqual(self._simple_tree().root(), "Root")

    def test_children_of_root(self):
        self.assertEqual(self._simple_tree().children_of("Root"), ["A"])

    def test_children_of_leaf_is_empty(self):
        self.assertEqual(self._simple_tree().children_of("B"), [])

    def test_validate_valid_tree_returns_empty(self):
        self.assertEqual(self._simple_tree().validate(), [])

    def test_validate_empty_tree_returns_error(self):
        errors = TransformationTree().validate()
        self.assertGreater(len(errors), 0)

    def test_duplicate_node_raises(self):
        tree = TransformationTree()
        tree.add_node("Root")
        with self.assertRaises(ValueError):
            tree.add_node("Root")

    def test_missing_parent_raises(self):
        tree = TransformationTree()
        with self.assertRaises(ValueError):
            tree.add_node("Child", parent="Ghost")

    def test_multiple_roots_flagged(self):
        tree = TransformationTree()
        tree.add_node("Root1")
        tree.add_node("Root2")
        errors = tree.validate()
        self.assertTrue(any("Multiple root" in e for e in errors))

    def test_unknown_node_children_raises(self):
        tree = self._simple_tree()
        with self.assertRaises(KeyError):
            tree.children_of("Z")


# ---------------------------------------------------------------------------
# Chain resolution tests
# ---------------------------------------------------------------------------

class TestFindChain(unittest.TestCase):

    def _branching_tree(self) -> TransformationTree:
        """
        Root
        ├── A
        │   └── C
        └── B
        """
        tree = TransformationTree()
        tree.add_node("Root")
        tree.add_node("A", parent="Root")
        tree.add_node("B", parent="Root")
        tree.add_node("C", parent="A")
        return tree

    def test_same_node_returns_singleton(self):
        tree = self._branching_tree()
        self.assertEqual(tree.find_chain("Root", "Root"), ["Root"])

    def test_parent_to_child_chain(self):
        tree = self._branching_tree()
        self.assertEqual(tree.find_chain("Root", "C"), ["Root", "A", "C"])

    def test_child_to_parent_chain(self):
        tree = self._branching_tree()
        self.assertEqual(tree.find_chain("C", "Root"), ["C", "A", "Root"])

    def test_cross_branch_chain(self):
        tree = self._branching_tree()
        chain = tree.find_chain("C", "B")
        self.assertEqual(chain, ["C", "A", "Root", "B"])

    def test_missing_source_raises(self):
        tree = self._branching_tree()
        with self.assertRaises(KeyError):
            tree.find_chain("Z", "Root")

    def test_missing_target_raises(self):
        tree = self._branching_tree()
        with self.assertRaises(KeyError):
            tree.find_chain("Root", "Z")


# ---------------------------------------------------------------------------
# Transform composition tests
# ---------------------------------------------------------------------------

class TestComposeChain(unittest.TestCase):

    def test_single_node_chain_is_identity(self):
        tree = TransformationTree()
        tree.add_node("Root")
        self.assertTrue(_mat_close(tree.compose_chain(["Root"]), identity_4x4()))

    def test_identity_tree_root_to_leaf_is_identity(self):
        tree = TransformationTree()
        tree.add_node("Root")
        tree.add_node("A", parent="Root")
        tree.add_node("B", parent="A")
        chain = tree.find_chain("Root", "B")
        self.assertTrue(_mat_close(tree.compose_chain(chain), identity_4x4()))

    def test_round_trip_is_identity(self):
        """Root→B composed with B→Root should give identity."""
        tree = TransformationTree()
        R = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        tree.add_node("Root")
        tree.add_node("A", parent="Root", transform_to_parent=build_transform(R, [1.0, 0.0, 0.0]))
        tree.add_node("B", parent="A",    transform_to_parent=build_transform(R, [0.0, 1.0, 0.0]))
        fwd = tree.compose_chain(tree.find_chain("Root", "B"))
        bwd = tree.compose_chain(tree.find_chain("B", "Root"))
        combined = mat_mul_4x4(fwd, bwd)
        self.assertTrue(_mat_close(combined, identity_4x4(), eps=1e-9))

    def test_empty_chain_raises(self):
        tree = TransformationTree()
        tree.add_node("Root")
        with self.assertRaises(ValueError):
            tree.compose_chain([])

    def test_compose_returns_sixteen_elements(self):
        tree = TransformationTree()
        tree.add_node("Root")
        tree.add_node("A", parent="Root")
        result = tree.compose_chain(["Root", "A"])
        self.assertEqual(len(result), 16)


# ---------------------------------------------------------------------------
# Franck diagram tests
# ---------------------------------------------------------------------------

class TestFranckEdges(unittest.TestCase):

    def test_edge_list_correct(self):
        tree = TransformationTree()
        tree.add_node("Root")
        tree.add_node("A", parent="Root")
        tree.add_node("B", parent="Root")
        edges = tree.franck_edges()
        self.assertIn(("Root", "A"), edges)
        self.assertIn(("Root", "B"), edges)
        self.assertEqual(len(edges), 2)

    def test_root_only_has_no_edges(self):
        tree = TransformationTree()
        tree.add_node("Root")
        self.assertEqual(tree.franck_edges(), [])


if __name__ == "__main__":
    unittest.main()
