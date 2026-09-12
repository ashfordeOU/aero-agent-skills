"""
Contract tests for model_geometry_checks_logic — ECSS-E-ST-32C §5.2
Run: python3 test_model_geometry_checks.py
Expected: OK (15 tests)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from model_geometry_checks_logic import (
    check_node_id_uniqueness,
    check_duplicate_coordinates,
    check_free_nodes,
    check_element_connectivity,
    check_interface_node_matching,
    check_surface_normal_consistency,
    run_geometry_checks,
)


def _node(nid, x=0.0, y=0.0, z=0.0):
    return {"id": nid, "x": x, "y": y, "z": z}


def _elem(eid, node_ids):
    return {"id": eid, "nodes": node_ids}


class TestNodeIdUniqueness(unittest.TestCase):

    def test_unique_ids_produces_no_findings(self):
        nodes = [_node(1), _node(2), _node(3)]
        self.assertEqual(check_node_id_uniqueness(nodes), [])

    def test_duplicate_id_is_detected(self):
        nodes = [_node(1), _node(2), _node(1)]
        findings = check_node_id_uniqueness(nodes)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["node_id"], 1)
        self.assertEqual(findings[0]["issue"], "duplicate_node_id")

    def test_empty_node_list_produces_no_findings(self):
        self.assertEqual(check_node_id_uniqueness([]), [])


class TestDuplicateCoordinates(unittest.TestCase):

    def test_well_separated_nodes_produce_no_findings(self):
        nodes = [_node(1, 0, 0, 0), _node(2, 1, 0, 0), _node(3, 2, 0, 0)]
        self.assertEqual(check_duplicate_coordinates(nodes, 1e-6), [])

    def test_coincident_nodes_within_tolerance_detected(self):
        nodes = [_node(1, 0.0, 0.0, 0.0), _node(2, 0.0, 0.0, 5e-7)]
        findings = check_duplicate_coordinates(nodes, 1e-6)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "coincident_nodes")
        self.assertIn(findings[0]["node_a"], {1, 2})
        self.assertIn(findings[0]["node_b"], {1, 2})

    def test_nodes_exactly_at_tolerance_boundary_not_flagged(self):
        # Distance == tolerance → strictly less than fails → no finding
        nodes = [_node(1, 0.0, 0.0, 0.0), _node(2, 1e-6, 0.0, 0.0)]
        findings = check_duplicate_coordinates(nodes, 1e-6)
        self.assertEqual(findings, [])

    def test_distance_stored_in_finding(self):
        nodes = [_node(1, 0.0, 0.0, 0.0), _node(2, 0.0, 0.0, 3e-7)]
        findings = check_duplicate_coordinates(nodes, 1e-6)
        self.assertAlmostEqual(findings[0]["distance"], 3e-7, places=15)


class TestFreeNodes(unittest.TestCase):

    def test_all_nodes_referenced_produces_no_findings(self):
        nodes = [_node(1), _node(2), _node(3)]
        elements = [_elem(10, [1, 2, 3])]
        self.assertEqual(check_free_nodes(nodes, elements), [])

    def test_unreferenced_node_is_detected(self):
        nodes = [_node(1), _node(2), _node(3), _node(99)]
        elements = [_elem(10, [1, 2, 3])]
        findings = check_free_nodes(nodes, elements)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["node_id"], 99)
        self.assertEqual(findings[0]["issue"], "free_node")

    def test_multiple_free_nodes_all_detected(self):
        nodes = [_node(1), _node(2), _node(3), _node(7), _node(8)]
        elements = [_elem(10, [1, 2, 3])]
        findings = check_free_nodes(nodes, elements)
        free_ids = {f["node_id"] for f in findings}
        self.assertEqual(free_ids, {7, 8})


class TestElementConnectivity(unittest.TestCase):

    def test_valid_connectivity_produces_no_findings(self):
        nodes = [_node(1), _node(2), _node(3)]
        elements = [_elem(10, [1, 2, 3])]
        self.assertEqual(check_element_connectivity(nodes, elements), [])

    def test_missing_node_reference_detected(self):
        nodes = [_node(1), _node(2)]
        elements = [_elem(10, [1, 2, 99])]
        findings = check_element_connectivity(nodes, elements)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["element_id"], 10)
        self.assertEqual(findings[0]["missing_node"], 99)
        self.assertEqual(findings[0]["issue"], "missing_node_reference")

    def test_empty_model_produces_no_findings(self):
        self.assertEqual(check_element_connectivity([], []), [])


class TestInterfaceNodeMatching(unittest.TestCase):

    def test_perfectly_matched_interfaces_produce_no_findings(self):
        side_a = [_node(1, 1.0, 0.0, 0.0), _node(2, 2.0, 0.0, 0.0)]
        side_b = [_node(11, 1.0, 0.0, 0.0), _node(12, 2.0, 0.0, 0.0)]
        self.assertEqual(check_interface_node_matching(side_a, side_b, 1e-4), [])

    def test_node_outside_tolerance_on_side_a_detected(self):
        side_a = [_node(1, 0.0, 0.0, 0.0), _node(2, 1.0, 0.0, 0.5)]
        side_b = [_node(11, 0.0, 0.0, 0.0)]
        findings = check_interface_node_matching(side_a, side_b, 1e-4)
        issues = [f for f in findings if f["side"] == "A"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["node_id"], 2)
        self.assertEqual(issues[0]["issue"], "unmatched_interface_node")

    def test_extra_node_on_side_b_detected(self):
        side_a = [_node(1, 0.0, 0.0, 0.0)]
        side_b = [_node(11, 0.0, 0.0, 0.0), _node(12, 5.0, 5.0, 5.0)]
        findings = check_interface_node_matching(side_a, side_b, 1e-4)
        issues = [f for f in findings if f["side"] == "B"]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["node_id"], 12)

    def test_nodes_within_interface_tolerance_match(self):
        # 5e-5 < 1e-4 tolerance → should match
        side_a = [_node(1, 0.0, 0.0, 0.0)]
        side_b = [_node(11, 5e-5, 0.0, 0.0)]
        self.assertEqual(check_interface_node_matching(side_a, side_b, 1e-4), [])


class TestSurfaceNormalConsistency(unittest.TestCase):

    def test_single_triangle_produces_no_findings(self):
        elems = [_elem(1, [1, 2, 3])]
        self.assertEqual(check_surface_normal_consistency(elems), [])

    def test_two_consistently_wound_triangles_produce_no_findings(self):
        # T1: 1→2→3→1, edges: (1,2),(2,3),(3,1)
        # T2: 2→4→3→2, edges: (2,4),(4,3),(3,2)
        # Shared edge between T1 and T2: T1 has (3,2) reversed, T2 has (3,2).
        # Wait, T1 has edge (2,3) and T2 has edge (3,2) — opposite → consistent
        elems = [
            _elem(1, [1, 2, 3]),
            _elem(2, [3, 2, 4]),  # traverses (2,3) as (3,2) → consistent with T1's (2,3)? No.
            # T1 edge (2,3): a=2, b=3
            # T2 edge: nodes[0]=3,nodes[1]=2,nodes[2]=4 → edges (3,2),(2,4),(4,3)
            # T2 has (3,2) which is reverse of T1's (2,3) → consistent ✓
        ]
        self.assertEqual(check_surface_normal_consistency(elems), [])

    def test_two_inconsistently_wound_triangles_detected(self):
        # T1: 1→2→3→1, has edge (1,2)
        # T2: 1→2→4→1, also has edge (1,2) → same direction → inconsistent
        elems = [
            _elem(1, [1, 2, 3]),
            _elem(2, [1, 2, 4]),
        ]
        findings = check_surface_normal_consistency(elems)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["element_id"], 2)
        self.assertEqual(findings[0]["conflicting_element"], 1)
        self.assertEqual(findings[0]["edge"], (1, 2))
        self.assertEqual(findings[0]["issue"], "inconsistent_normal_orientation")

    def test_quad_elements_winding_check_works(self):
        # Two quads sharing edge 2→3 vs 3→2
        elems = [
            _elem(1, [1, 2, 3, 4]),   # edges (1,2),(2,3),(3,4),(4,1)
            _elem(2, [5, 3, 2, 6]),   # edges (5,3),(3,2),(2,6),(6,5)
            # T1 has (2,3); T2 has (3,2) — opposite → consistent ✓
        ]
        self.assertEqual(check_surface_normal_consistency(elems), [])


class TestRunGeometryChecks(unittest.TestCase):

    def _clean_model(self):
        return {
            "nodes": [
                _node(1, 0.0, 0.0, 0.0),
                _node(2, 1.0, 0.0, 0.0),
                _node(3, 0.0, 1.0, 0.0),
            ],
            "elements": [_elem(10, [1, 2, 3])],
            "surface_elements": [_elem(10, [1, 2, 3])],
            "interfaces": {
                "iface1": {
                    "A": [_node(100, 1.0, 0.0, 0.0)],
                    "B": [_node(200, 1.0, 0.0, 0.0)],
                }
            },
            "coord_tolerance": 1e-6,
            "iface_tolerance": 1e-4,
        }

    def test_clean_model_passes(self):
        result = run_geometry_checks(self._clean_model())
        self.assertTrue(result["pass"])
        for key in ("duplicate_node_ids", "coincident_nodes", "free_nodes",
                    "broken_connectivity", "surface_normal_issues",
                    "interface_mismatches"):
            self.assertEqual(result[key], [], msg=f"{key} should be empty")

    def test_model_with_free_node_fails(self):
        model = self._clean_model()
        model["nodes"].append(_node(99, 9.0, 9.0, 9.0))
        result = run_geometry_checks(model)
        self.assertFalse(result["pass"])
        self.assertEqual(len(result["free_nodes"]), 1)
        self.assertEqual(result["free_nodes"][0]["node_id"], 99)

    def test_model_with_broken_connectivity_fails(self):
        model = self._clean_model()
        model["elements"].append(_elem(20, [1, 2, 999]))
        result = run_geometry_checks(model)
        self.assertFalse(result["pass"])
        self.assertTrue(
            any(f["missing_node"] == 999 for f in result["broken_connectivity"])
        )

    def test_model_with_interface_mismatch_fails(self):
        model = self._clean_model()
        model["interfaces"]["iface1"]["B"] = [_node(200, 50.0, 50.0, 50.0)]
        result = run_geometry_checks(model)
        self.assertFalse(result["pass"])
        self.assertGreater(len(result["interface_mismatches"]), 0)
        self.assertEqual(result["interface_mismatches"][0]["interface"], "iface1")


if __name__ == "__main__":
    unittest.main()
