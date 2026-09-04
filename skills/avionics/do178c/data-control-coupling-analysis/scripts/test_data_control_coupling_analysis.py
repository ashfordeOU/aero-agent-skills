"""Offline contract test for data-control-coupling-analysis.

Covers the wave-32 spec contract: the four-component worked example
(components A/B/C/D with X/Y variables and call edges (A,B), (B,C)),
declared synchronization suppression, symmetric-pairwise data coupling,
control coupling only along declared call edges, tuple sorting, coupling
coverage ratio bounds, PASS/FAIL verdict logic, empty-list PASS, ValueError
rejection of unknown components and foreign evidence keys, exact
analyze_coupling dict keys, and run-to-run determinism.

Run offline: python3 scripts/test_data_control_coupling_analysis.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_control_coupling_analysis_logic as dcc  # noqa: E402

COMPONENTS = {
    "A": {"writes": {"X"}, "reads": set()},
    "B": {"writes": {"Y"}, "reads": {"X"}},
    "C": {"writes": set(), "reads": {"X", "Y"}},
    "D": {"writes": {"Y"}, "reads": set()},
}
EDGES = [("A", "B"), ("B", "C")]

DATA_ALL = [("A", "B", "X"), ("A", "C", "X"), ("B", "C", "Y"), ("D", "C", "Y")]
DATA_SYNC = [("A", "B", "X"), ("B", "C", "Y"), ("D", "C", "Y")]
CONTROL_ALL = [("A", "B", "X"), ("B", "C", "Y")]
EVIDENCE_ALL = {("A", "B", "X"), ("A", "C", "X"), ("B", "C", "Y"), ("D", "C", "Y")}
EVIDENCE_MISSING_ACX = {("A", "B", "X"), ("B", "C", "Y"), ("D", "C", "Y")}


class TestDataCouplingItems(unittest.TestCase):
    def test_worked_example_four_items(self):
        # Spec magnitude bound: exactly 4 data items for the example.
        self.assertEqual(dcc.data_coupling_items(COMPONENTS), DATA_ALL)
        self.assertEqual(len(dcc.data_coupling_items(COMPONENTS)), 4)

    def test_sorted_by_tuple_order(self):
        items = dcc.data_coupling_items(COMPONENTS)
        self.assertEqual(items, sorted(items))

    def test_writer_reader_pair_direction(self):
        # A writes X and B reads X so (A,B,X) exists; B does not write X,
        # so the reversed pair (B,A,X) must not exist.
        items = dcc.data_coupling_items(COMPONENTS)
        self.assertIn(("A", "B", "X"), items)
        self.assertNotIn(("B", "A", "X"), items)

    def test_pairwise_over_all_components(self):
        # D writes Y and C reads Y, so (D,C,Y) exists even though D has no
        # call edge to C: the data-coupling model is pairwise.
        items = dcc.data_coupling_items(COMPONENTS)
        self.assertIn(("D", "C", "Y"), items)

    def test_no_self_pair(self):
        items = dcc.data_coupling_items(COMPONENTS)
        for a, b, _var in items:
            self.assertNotEqual(a, b)

    def test_sync_suppresses_only_that_item(self):
        items = dcc.data_coupling_items(COMPONENTS, {("A", "C", "X")})
        self.assertEqual(items, DATA_SYNC)
        self.assertNotIn(("A", "C", "X"), items)
        self.assertEqual(len(items), 3)

    def test_unsuppressed_sibling_survives(self):
        # Suppressing the A-C handshake must not remove the A-B or D-C
        # items that share the variables X/Y.
        items = dcc.data_coupling_items(COMPONENTS, {("A", "C", "X")})
        self.assertIn(("A", "B", "X"), items)
        self.assertIn(("D", "C", "Y"), items)

    def test_sync_unknown_component_raises(self):
        for bad in ({("A", "Z", "X")}, {("Z", "A", "X")}):
            with self.assertRaises(ValueError):
                dcc.data_coupling_items(COMPONENTS, bad)

    def test_empty_components_empty_items(self):
        self.assertEqual(dcc.data_coupling_items({}), [])


class TestControlCouplingItems(unittest.TestCase):
    def test_worked_example_two_items(self):
        # Spec magnitude bound: exactly 2 control items for the example.
        items = dcc.control_coupling_items(COMPONENTS, EDGES)
        self.assertEqual(items, CONTROL_ALL)
        self.assertEqual(len(items), 2)

    def test_only_along_declared_edges(self):
        # No A->C or D->C edge exists, so no (A,C,X) or (D,C,Y) control
        # item even though those data items exist.
        items = dcc.control_coupling_items(COMPONENTS, EDGES)
        self.assertNotIn(("A", "C", "X"), items)
        self.assertNotIn(("D", "C", "Y"), items)

    def test_edge_direction_matters(self):
        # Reversing an edge changes the items: with (C,B), C writes nothing
        # that B reads, so no item results.
        items = dcc.control_coupling_items(COMPONENTS, [("C", "B")])
        self.assertEqual(items, [])

    def test_sorted_by_tuple_order(self):
        items = dcc.control_coupling_items(COMPONENTS, EDGES)
        self.assertEqual(items, sorted(items))

    def test_callee_reads_writer_var(self):
        # On edge (A,B) the item variable is X: A writes it and B reads it.
        items = dcc.control_coupling_items(COMPONENTS, [("A", "B")])
        self.assertEqual(items, [("A", "B", "X")])

    def test_edge_unknown_component_raises(self):
        for bad in ([("Z", "B")], [("A", "Z")]):
            with self.assertRaises(ValueError):
                dcc.control_coupling_items(COMPONENTS, bad)

    def test_no_edges_no_items(self):
        self.assertEqual(dcc.control_coupling_items(COMPONENTS, []), [])


class TestCoverage(unittest.TestCase):
    def _combined(self):
        return dcc.data_coupling_items(COMPONENTS) + \
            dcc.control_coupling_items(COMPONENTS, EDGES)

    def test_ratio_one_when_all_covered(self):
        combined = self._combined()
        self.assertEqual(dcc.coupling_coverage_ratio(combined, EVIDENCE_ALL),
                         1.0)
        # Ratio bound: any ratio stays in [0, 1].
        self.assertGreaterEqual(
            dcc.coupling_coverage_ratio(combined, EVIDENCE_MISSING_ACX), 0.0)
        self.assertLessEqual(
            dcc.coupling_coverage_ratio(combined, EVIDENCE_MISSING_ACX), 1.0)

    def test_ratio_five_sixths_when_acx_missing(self):
        ratio = dcc.coupling_coverage_ratio(self._combined(),
                                            EVIDENCE_MISSING_ACX)
        self.assertAlmostEqual(ratio, 5.0 / 6.0, places=12)
        self.assertLess(ratio, 1.0)

    def test_evidence_for_nonexistent_item_raises(self):
        with self.assertRaises(ValueError):
            dcc.coupling_coverage_ratio(self._combined(),
                                        {("A", "B", "NOPE")})

    def test_verdict_pass_at_full_evidence(self):
        v = dcc.coverage_verdict(self._combined(), EVIDENCE_ALL)
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["ratio"], 1.0)
        self.assertEqual(v["covered"], 6)
        self.assertEqual(v["total"], 6)
        self.assertEqual(v["uncovered"], [])

    def test_verdict_fail_lists_uncovered_sorted(self):
        v = dcc.coverage_verdict(self._combined(), EVIDENCE_MISSING_ACX)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertEqual(v["uncovered"], [("A", "C", "X")])
        self.assertEqual(v["covered"], 5)
        self.assertEqual(v["total"], 6)

    def test_verdict_empty_list_is_pass(self):
        # Empty item list: ratio 0.0, verdict PASS, nothing uncovered.
        v = dcc.coverage_verdict([], set())
        self.assertEqual(v["verdict"], "PASS")
        self.assertEqual(v["ratio"], 0.0)
        self.assertEqual(v["total"], 0)
        self.assertEqual(v["uncovered"], [])
        self.assertEqual(dcc.coupling_coverage_ratio([], set()), 0.0)

    def test_verdict_foreign_evidence_raises(self):
        with self.assertRaises(ValueError):
            dcc.coverage_verdict([], {("Q", "R", "S")})

    def test_verdict_dict_keys(self):
        v = dcc.coverage_verdict(self._combined(), EVIDENCE_ALL)
        self.assertEqual(set(v), {"ratio", "covered", "total", "verdict",
                                  "uncovered"})


class TestAnalyzeCoupling(unittest.TestCase):
    def test_analyze_fail_case(self):
        r = dcc.analyze_coupling(COMPONENTS, EDGES, EVIDENCE_MISSING_ACX)
        self.assertEqual(r["data_items"], DATA_ALL)
        self.assertEqual(r["control_items"], CONTROL_ALL)
        self.assertEqual(r["total_items"], 6)
        self.assertEqual(r["covered"], 5)
        self.assertAlmostEqual(r["ratio"], 5.0 / 6.0, places=12)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertEqual(r["uncovered_items"], [("A", "C", "X")])
        self.assertEqual(r["component_count"], 4)

    def test_analyze_pass_case(self):
        r = dcc.analyze_coupling(COMPONENTS, EDGES, EVIDENCE_ALL)
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual(r["ratio"], 1.0)
        self.assertEqual(r["uncovered_items"], [])

    def test_analyze_with_sync_declarations(self):
        # Sync suppression removes the A-C data item; with the control items
        # unchanged, total drops to 5 and full evidence passes.
        ev = {("A", "B", "X"), ("B", "C", "Y"), ("D", "C", "Y")}
        r = dcc.analyze_coupling(COMPONENTS, EDGES, ev, {("A", "C", "X")})
        self.assertEqual(r["data_items"], DATA_SYNC)
        self.assertEqual(r["total_items"], 5)
        self.assertEqual(r["verdict"], "PASS")

    def test_analyze_exact_keys(self):
        r = dcc.analyze_coupling(COMPONENTS, EDGES, EVIDENCE_ALL)
        self.assertEqual(
            set(r),
            {"data_items", "control_items", "total_items", "covered",
             "ratio", "verdict", "uncovered_items", "component_count"})

    def test_analyze_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            dcc.analyze_coupling(COMPONENTS, [("A", "Z")], EVIDENCE_ALL)

    def test_analyze_no_edges_no_control(self):
        r = dcc.analyze_coupling(COMPONENTS, [], EVIDENCE_ALL)
        self.assertEqual(r["control_items"], [])
        self.assertEqual(r["total_items"], 4)


class TestDeterminism(unittest.TestCase):
    def test_repeat_calls_identical(self):
        for _ in range(3):
            self.assertEqual(dcc.data_coupling_items(COMPONENTS), DATA_ALL)
            self.assertEqual(dcc.control_coupling_items(COMPONENTS, EDGES),
                             CONTROL_ALL)

    def test_input_order_does_not_matter(self):
        shuffled = {"C": COMPONENTS["C"], "A": COMPONENTS["A"],
                    "D": COMPONENTS["D"], "B": COMPONENTS["B"]}
        self.assertEqual(dcc.data_coupling_items(shuffled), DATA_ALL)
        self.assertEqual(dcc.control_coupling_items(shuffled, EDGES),
                         CONTROL_ALL)

    def test_set_vs_list_evidence_equivalent(self):
        combined = DATA_ALL + CONTROL_ALL
        v_set = dcc.coverage_verdict(combined, EVIDENCE_ALL)
        v_list = dcc.coverage_verdict(combined, list(EVIDENCE_ALL))
        self.assertEqual(v_set, v_list)

    def test_lists_accepted_as_write_read_sets(self):
        comps = {"A": {"writes": ["X"], "reads": []},
                 "B": {"writes": ["Y"], "reads": ["X"]}}
        self.assertEqual(dcc.data_coupling_items(comps), [("A", "B", "X")])


if __name__ == "__main__":
    unittest.main()
