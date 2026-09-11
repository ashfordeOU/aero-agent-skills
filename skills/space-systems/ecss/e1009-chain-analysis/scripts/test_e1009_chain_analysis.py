#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.2.3 coordinate system chain analysis.

Exercises scripts/e1009_chain_analysis_logic.py (stdlib unittest, offline).
Contract: every coordinate system has a type from the known set and a
handedness of right or left; a duplicate registration raises; a
self-loop or unknown-system transformation raises; find_chain returns the
shortest path via breadth-first search and raises when no path exists;
verify_completeness flags every user frame that cannot reach the root;
detect_cycles returns directed cycles and an empty list when none exist;
check_handedness_consistency flags frames whose handedness differs from the
chain root; analyze_all_chains is compliant only when all three conditions
hold simultaneously.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1009_chain_analysis_logic as ca


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analyzer_triangle():
    """Return a ChainAnalyzer with three right-handed CS connected root-body-sensor."""
    az = ca.ChainAnalyzer()
    az.add_system(ca.CoordinateSystem("root", "inertial", "right"))
    az.add_system(ca.CoordinateSystem("body", "body", "right"))
    az.add_system(ca.CoordinateSystem("sensor", "sensor", "right"))
    az.add_transformation(ca.Transformation("root", "body", "rigid_body"))
    az.add_transformation(ca.Transformation("body", "sensor", "rotation"))
    return az


# ---------------------------------------------------------------------------
# CoordinateSystem construction
# ---------------------------------------------------------------------------

class CoordinateSystemConstructionTest(unittest.TestCase):
    def test_valid_system_right_handed(self):
        cs = ca.CoordinateSystem("inertial_j2000", "inertial", "right")
        self.assertEqual(cs.name, "inertial_j2000")
        self.assertEqual(cs.cs_type, "inertial")
        self.assertEqual(cs.handedness, "right")

    def test_valid_system_left_handed(self):
        cs = ca.CoordinateSystem("image_sensor", "sensor", "left")
        self.assertEqual(cs.handedness, "left")

    def test_default_handedness_is_right(self):
        cs = ca.CoordinateSystem("sc_body", "body")
        self.assertEqual(cs.handedness, "right")

    def test_invalid_cs_type_raises(self):
        with self.assertRaises(ca.ChainError):
            ca.CoordinateSystem("bad", "galactic")

    def test_invalid_handedness_raises(self):
        with self.assertRaises(ca.ChainError):
            ca.CoordinateSystem("bad", "body", "ambidextrous")

    def test_empty_name_raises(self):
        with self.assertRaises(ca.ChainError):
            ca.CoordinateSystem("", "body")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegistrationTest(unittest.TestCase):
    def test_duplicate_system_raises(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        with self.assertRaises(ca.ChainError):
            az.add_system(ca.CoordinateSystem("root", "body"))

    def test_transform_with_unregistered_source_raises(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        with self.assertRaises(ca.ChainError):
            az.add_transformation(ca.Transformation("ghost", "root", "rotation"))

    def test_transform_with_unregistered_target_raises(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        with self.assertRaises(ca.ChainError):
            az.add_transformation(ca.Transformation("root", "ghost", "rotation"))

    def test_self_loop_transform_raises(self):
        with self.assertRaises(ca.ChainError):
            ca.Transformation("root", "root", "rotation")

    def test_invalid_xform_type_raises(self):
        with self.assertRaises(ca.ChainError):
            ca.Transformation("a", "b", "teleportation")


# ---------------------------------------------------------------------------
# Chain finding
# ---------------------------------------------------------------------------

class ChainFindingTest(unittest.TestCase):
    def test_direct_one_hop_chain(self):
        az = _make_analyzer_triangle()
        chain = az.find_chain("body", "root")
        self.assertEqual(chain, ["body", "root"])

    def test_multi_hop_chain(self):
        az = _make_analyzer_triangle()
        chain = az.find_chain("sensor", "root")
        self.assertEqual(chain, ["sensor", "body", "root"])

    def test_same_source_and_target_returns_singleton(self):
        az = _make_analyzer_triangle()
        chain = az.find_chain("root", "root")
        self.assertEqual(chain, ["root"])

    def test_missing_link_raises(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("orphan", "sensor"))
        with self.assertRaises(ca.ChainError):
            az.find_chain("orphan", "root")

    def test_unregistered_source_raises(self):
        az = _make_analyzer_triangle()
        with self.assertRaises(ca.ChainError):
            az.find_chain("unknown_frame", "root")

    def test_unidirectional_link_not_reversed(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("sensor", "sensor"))
        az.add_transformation(ca.Transformation("root", "sensor", "rotation", bidirectional=False))
        with self.assertRaises(ca.ChainError):
            az.find_chain("sensor", "root")

    def test_bidirectional_link_traversed_both_ways(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("sensor", "sensor"))
        az.add_transformation(ca.Transformation("root", "sensor", "rotation", bidirectional=True))
        chain = az.find_chain("sensor", "root")
        self.assertEqual(chain, ["sensor", "root"])


# ---------------------------------------------------------------------------
# Completeness verification
# ---------------------------------------------------------------------------

class CompletenessTest(unittest.TestCase):
    def test_all_users_reachable(self):
        az = _make_analyzer_triangle()
        result = az.verify_completeness(["body", "sensor"], "root")
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])
        self.assertIsNotNone(result["chains"]["body"])
        self.assertIsNotNone(result["chains"]["sensor"])

    def test_missing_user_flagged(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("orphan", "sensor"))
        result = az.verify_completeness(["orphan"], "root")
        self.assertFalse(result["complete"])
        self.assertIn("orphan", result["missing"])
        self.assertIsNone(result["chains"]["orphan"])

    def test_unregistered_root_raises(self):
        az = _make_analyzer_triangle()
        with self.assertRaises(ca.ChainError):
            az.verify_completeness(["body"], "nonexistent_root")

    def test_unregistered_user_raises(self):
        az = _make_analyzer_triangle()
        with self.assertRaises(ca.ChainError):
            az.verify_completeness(["phantom_frame"], "root")


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

class CycleDetectionTest(unittest.TestCase):
    def test_no_cycles_in_acyclic_graph(self):
        az = _make_analyzer_triangle()
        cycles = az.detect_cycles()
        self.assertEqual(cycles, [])

    def test_directed_cycle_detected(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("a", "body"))
        az.add_system(ca.CoordinateSystem("b", "structural"))
        az.add_transformation(ca.Transformation("root", "a", "rotation", bidirectional=False))
        az.add_transformation(ca.Transformation("a", "b", "rotation", bidirectional=False))
        az.add_transformation(ca.Transformation("b", "a", "rotation", bidirectional=False))
        cycles = az.detect_cycles()
        self.assertTrue(len(cycles) > 0)
        found = any("a" in c and "b" in c for c in cycles)
        self.assertTrue(found, f"Expected a/b cycle in {cycles}")

    def test_isolated_node_has_no_cycle(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("lone", "ground"))
        cycles = az.detect_cycles()
        self.assertEqual(cycles, [])


# ---------------------------------------------------------------------------
# Handedness consistency
# ---------------------------------------------------------------------------

class HandednessTest(unittest.TestCase):
    def test_all_right_handed_is_consistent(self):
        az = _make_analyzer_triangle()
        result = az.check_handedness_consistency(["root", "body", "sensor"])
        self.assertTrue(result["consistent"])
        self.assertEqual(result["mismatches"], [])

    def test_mixed_handedness_flagged(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial", "right"))
        az.add_system(ca.CoordinateSystem("cam", "sensor", "left"))
        result = az.check_handedness_consistency(["root", "cam"])
        self.assertFalse(result["consistent"])
        mismatch_names = [m[0] for m in result["mismatches"]]
        self.assertIn("cam", mismatch_names)

    def test_empty_chain_is_consistent(self):
        az = _make_analyzer_triangle()
        result = az.check_handedness_consistency([])
        self.assertTrue(result["consistent"])
        self.assertEqual(result["mismatches"], [])

    def test_unregistered_name_in_chain_raises(self):
        az = _make_analyzer_triangle()
        with self.assertRaises(ca.ChainError):
            az.check_handedness_consistency(["root", "ghost_frame"])


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------

class FullAnalysisTest(unittest.TestCase):
    def test_fully_compliant_project(self):
        az = _make_analyzer_triangle()
        report = az.analyze_all_chains(["body", "sensor"], "root")
        self.assertTrue(report["complete"])
        self.assertEqual(report["missing_users"], [])
        self.assertEqual(report["cycles"], [])
        self.assertTrue(report["handedness"]["body"]["consistent"])
        self.assertTrue(report["handedness"]["sensor"]["consistent"])
        self.assertTrue(report["compliant"])

    def test_missing_user_makes_noncompliant(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("orphan", "sensor"))
        report = az.analyze_all_chains(["orphan"], "root")
        self.assertFalse(report["complete"])
        self.assertIn("orphan", report["missing_users"])
        self.assertFalse(report["compliant"])

    def test_cycle_makes_noncompliant(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial"))
        az.add_system(ca.CoordinateSystem("a", "body"))
        az.add_system(ca.CoordinateSystem("b", "structural"))
        az.add_transformation(ca.Transformation("root", "a", "rigid_body", bidirectional=False))
        az.add_transformation(ca.Transformation("a", "b", "rotation", bidirectional=False))
        az.add_transformation(ca.Transformation("b", "a", "rotation", bidirectional=False))
        az.add_transformation(ca.Transformation("a", "root", "rigid_body", bidirectional=False))
        report = az.analyze_all_chains(["a", "b"], "root")
        self.assertTrue(len(report["cycles"]) > 0)
        self.assertFalse(report["compliant"])

    def test_handedness_mismatch_makes_noncompliant(self):
        az = ca.ChainAnalyzer()
        az.add_system(ca.CoordinateSystem("root", "inertial", "right"))
        az.add_system(ca.CoordinateSystem("cam", "sensor", "left"))
        az.add_transformation(ca.Transformation("root", "cam", "rotation"))
        report = az.analyze_all_chains(["cam"], "root")
        self.assertTrue(report["complete"])
        self.assertFalse(report["handedness"]["cam"]["consistent"])
        self.assertFalse(report["compliant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
