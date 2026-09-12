"""
Offline deterministic tests for element_topology_checks_logic.
Run: python3 test_element_topology_checks.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from element_topology_checks_logic import (
    ASPECT_RATIO_FAIL,
    ASPECT_RATIO_WARN,
    WARPING_FAIL_DEG,
    WARPING_WARN_DEG,
    ConnectivityFinding,
    DistortionFinding,
    DuplicateFinding,
    Element,
    Node,
    TopologyReport,
    check_connectivity,
    check_distortions,
    check_duplicates,
    run_topology_checks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node(nid: int, x: float, y: float, z: float = 0.0) -> Node:
    return Node(nid, x, y, z)


def _nmap(*ns: Node):
    return {n.id: n for n in ns}


# ---------------------------------------------------------------------------
# Connectivity tests
# ---------------------------------------------------------------------------

class TestConnectivity(unittest.TestCase):

    def test_valid_mesh_produces_no_findings(self):
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0), _node(3, 0, 1))
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        self.assertEqual(check_connectivity(ns, elems), [])

    def test_broken_reference_is_reported(self):
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0))  # node 3 absent
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_connectivity(ns, elems)
        broken = [f for f in findings if f.finding_type == "broken_ref"]
        self.assertEqual(len(broken), 1)
        self.assertEqual(broken[0].node_id, 3)
        self.assertEqual(broken[0].element_id, 1)

    def test_orphan_node_is_reported(self):
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0), _node(3, 0, 1), _node(99, 99, 99))
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_connectivity(ns, elems)
        orphans = [f for f in findings if f.finding_type == "orphan_node"]
        self.assertEqual(len(orphans), 1)
        self.assertEqual(orphans[0].node_id, 99)
        self.assertIsNone(orphans[0].element_id)

    def test_multiple_broken_refs_in_one_element(self):
        ns = _nmap(_node(1, 0, 0))  # only node 1 present
        elems = [Element(1, "QUAD4", (1, 2, 3, 4))]
        broken = [
            f for f in check_connectivity(ns, elems) if f.finding_type == "broken_ref"
        ]
        self.assertEqual(len(broken), 3)  # nodes 2, 3, 4 missing

    def test_empty_mesh_no_findings(self):
        self.assertEqual(check_connectivity({}, []), [])


# ---------------------------------------------------------------------------
# Duplicate-element tests
# ---------------------------------------------------------------------------

class TestDuplicates(unittest.TestCase):

    def test_distinct_elements_produce_no_duplicates(self):
        elems = [Element(1, "TRIA3", (1, 2, 3)), Element(2, "TRIA3", (2, 3, 4))]
        self.assertEqual(check_duplicates(elems), [])

    def test_identical_node_set_different_order_is_duplicate(self):
        elems = [
            Element(1, "TRIA3", (1, 2, 3)),
            Element(2, "TRIA3", (3, 1, 2)),
        ]
        findings = check_duplicates(elems)
        self.assertEqual(len(findings), 1)
        self.assertIn(1, findings[0].element_ids)
        self.assertIn(2, findings[0].element_ids)

    def test_quad4_duplicate_detection_order_independent(self):
        elems = [
            Element(10, "QUAD4", (1, 2, 3, 4)),
            Element(11, "QUAD4", (4, 3, 2, 1)),
        ]
        findings = check_duplicates(elems)
        self.assertEqual(len(findings), 1)

    def test_three_elements_one_duplicate_pair(self):
        elems = [
            Element(1, "TRIA3", (1, 2, 3)),
            Element(2, "TRIA3", (2, 3, 4)),
            Element(3, "TRIA3", (1, 2, 3)),  # duplicate of element 1
        ]
        findings = check_duplicates(elems)
        self.assertEqual(len(findings), 1)
        self.assertIn(1, findings[0].element_ids)
        self.assertIn(3, findings[0].element_ids)

    def test_node_set_stored_in_finding(self):
        elems = [
            Element(5, "TRIA3", (7, 8, 9)),
            Element(6, "TRIA3", (9, 7, 8)),
        ]
        findings = check_duplicates(elems)
        self.assertEqual(findings[0].node_set, (7, 8, 9))


# ---------------------------------------------------------------------------
# Distortion tests
# ---------------------------------------------------------------------------

class TestDistortions(unittest.TestCase):

    def test_equilateral_tria3_no_findings(self):
        s3 = math.sqrt(3) / 2
        ns = _nmap(_node(1, 0.0, 0.0), _node(2, 1.0, 0.0), _node(3, 0.5, s3))
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        self.assertEqual(check_distortions(ns, elems), [])

    def test_needle_tria3_aspect_ratio_fail(self):
        # One edge of length ~0.1, opposite base 100 → AR ≈ 1000
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 100.0, 0.0),
            _node(3, 0.1, 0.001),
        )
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_distortions(ns, elems)
        fails = [f for f in findings if f.metric == "aspect_ratio" and f.severity == "FAIL"]
        self.assertTrue(len(fails) > 0)
        self.assertGreaterEqual(fails[0].value, ASPECT_RATIO_FAIL)

    def test_moderate_tria3_aspect_ratio_warn(self):
        # AR ≈ 7 (> WARN threshold of 5, < FAIL threshold of 20)
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 7.0, 0.0),
            _node(3, 0.0, 1.0),
        )
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_distortions(ns, elems)
        ar = [f for f in findings if f.metric == "aspect_ratio"]
        self.assertEqual(len(ar), 1)
        self.assertEqual(ar[0].severity, "WARN")

    def test_planar_quad4_no_warping_finding(self):
        ns = _nmap(
            _node(1, 0.0, 0.0, 0.0),
            _node(2, 1.0, 0.0, 0.0),
            _node(3, 1.0, 1.0, 0.0),
            _node(4, 0.0, 1.0, 0.0),
        )
        elems = [Element(1, "QUAD4", (1, 2, 3, 4))]
        findings = check_distortions(ns, elems)
        warping_fails = [f for f in findings if f.metric == "warping" and f.severity == "FAIL"]
        self.assertEqual(warping_fails, [])

    def test_twisted_quad4_warping_fail(self):
        # Node 3 raised to z=1 creates ~60° warping — well above FAIL threshold
        ns = _nmap(
            _node(1, 0.0, 0.0, 0.0),
            _node(2, 1.0, 0.0, 0.0),
            _node(3, 1.0, 1.0, 1.0),
            _node(4, 0.0, 1.0, 0.0),
        )
        elems = [Element(1, "QUAD4", (1, 2, 3, 4))]
        findings = check_distortions(ns, elems)
        warping = [f for f in findings if f.metric == "warping"]
        self.assertEqual(len(warping), 1)
        self.assertEqual(warping[0].severity, "FAIL")
        self.assertGreaterEqual(warping[0].value, WARPING_FAIL_DEG)

    def test_unsupported_element_type_skipped(self):
        ns = _nmap(_node(1, 0, 0, 0), _node(2, 1, 0, 0))
        elems = [Element(1, "BEAM2", (1, 2))]
        self.assertEqual(check_distortions(ns, elems), [])

    def test_element_with_broken_ref_skipped_gracefully(self):
        # Node 3 absent — distortion check must not raise
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0))
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_distortions(ns, elems)
        self.assertEqual(findings, [])

    def test_distortion_finding_fields_are_typed_correctly(self):
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 100.0, 0.0),
            _node(3, 0.1, 0.001),
        )
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        findings = check_distortions(ns, elems)
        self.assertGreater(len(findings), 0)
        f = findings[0]
        self.assertIsInstance(f.element_id, int)
        self.assertIsInstance(f.metric, str)
        self.assertIsInstance(f.value, float)
        self.assertIsInstance(f.threshold, float)
        self.assertIn(f.severity, ("WARN", "FAIL"))


# ---------------------------------------------------------------------------
# TopologyReport integration tests
# ---------------------------------------------------------------------------

class TestTopologyReport(unittest.TestCase):

    def test_clean_triangulated_mesh_passes(self):
        s3 = math.sqrt(3) / 2
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 1.0, 0.0),
            _node(3, 0.5, s3),
            _node(4, 1.5, s3),
        )
        elems = [
            Element(1, "TRIA3", (1, 2, 3)),
            Element(2, "TRIA3", (2, 4, 3)),
        ]
        report = run_topology_checks(ns, elems)
        self.assertTrue(report.passed)

    def test_mesh_with_duplicate_element_fails(self):
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0), _node(3, 0, 1))
        elems = [
            Element(1, "TRIA3", (1, 2, 3)),
            Element(2, "TRIA3", (1, 2, 3)),
        ]
        report = run_topology_checks(ns, elems)
        self.assertFalse(report.passed)
        self.assertEqual(len(report.duplicate_findings), 1)

    def test_mesh_with_orphan_node_fails(self):
        ns = _nmap(_node(1, 0, 0), _node(2, 1, 0), _node(3, 0, 1), _node(99, 50, 50))
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        report = run_topology_checks(ns, elems)
        self.assertFalse(report.passed)
        orphans = [f for f in report.connectivity_findings if f.finding_type == "orphan_node"]
        self.assertEqual(len(orphans), 1)

    def test_warn_only_distortion_still_passes(self):
        # AR ≈ 7 triggers WARN but not FAIL; report should still pass
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 7.0, 0.0),
            _node(3, 0.0, 1.0),
        )
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        report = run_topology_checks(ns, elems)
        fail_distortions = [f for f in report.distortion_findings if f.severity == "FAIL"]
        self.assertEqual(fail_distortions, [])
        self.assertTrue(report.passed)

    def test_fail_distortion_blocks_pass(self):
        ns = _nmap(
            _node(1, 0.0, 0.0),
            _node(2, 100.0, 0.0),
            _node(3, 0.1, 0.001),
        )
        elems = [Element(1, "TRIA3", (1, 2, 3))]
        report = run_topology_checks(ns, elems)
        self.assertFalse(report.passed)


if __name__ == "__main__":
    unittest.main()
