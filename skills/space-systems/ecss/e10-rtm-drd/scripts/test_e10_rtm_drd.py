#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-rtm-drd (stdlib unittest, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_rtm_drd_logic import (  # noqa: E402
    REQUIRED_FIELDS, VERIFICATION_METHODS, allocation_violations,
    downward_violations, field_violations, is_rtm_complete, method_violations,
    rtm_review, trace_cycles, upward_violations, validate_unique_rows,
    validate_verification_method,
)

NODES = ["SAT", "AOCS", "RW"]


def row(rid, parent=None, top=False, kids=False, node="AOCS", method="analysis"):
    return {"requirement_id": rid, "parent_id": parent, "is_top_level": top,
            "expects_children": kids, "allocated_to": node,
            "verification_method": method}


def matrix():
    return [row("SYS-1", top=True, kids=True, node="SAT"),
            row("AOCS-1", parent="SYS-1"),
            row("AOCS-2", parent="SYS-1", method="test", node="RW")]


class VocabularyTest(unittest.TestCase):
    def test_all_methods_validate(self):
        for m in VERIFICATION_METHODS:
            self.assertEqual(validate_verification_method(m), m)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_verification_method("demonstration")

    def test_required_fields_are_declared(self):
        self.assertIn("verification_method", REQUIRED_FIELDS)


class RowTest(unittest.TestCase):
    def test_unique_rows_return_ids_in_order(self):
        self.assertEqual(validate_unique_rows(matrix())[0], "SYS-1")

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            validate_unique_rows(matrix() + [row("SYS-1", top=True)])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            validate_unique_rows([{"parent_id": None}])

    def test_clean_row_has_no_field_findings(self):
        self.assertEqual(field_violations(row("R1", parent="SYS-1")), [])

    def test_missing_allocation_is_reported(self):
        f = field_violations(row("R1", parent="SYS-1", node=""))
        self.assertEqual(f[0]["field"], "allocated_to")

    def test_blank_parent_is_not_a_field_finding(self):
        self.assertEqual(field_violations(row("R1", top=True)), [])


class UpwardTest(unittest.TestCase):
    def test_clean_matrix_has_no_upward_findings(self):
        self.assertEqual(upward_violations(matrix()), [])

    def test_derived_requirement_without_parent_is_reported(self):
        m = matrix() + [row("ORPHAN")]
        self.assertIn("no_upward_trace", [f["issue"] for f in upward_violations(m)])

    def test_dangling_parent_is_reported(self):
        m = matrix() + [row("X", parent="NOPE")]
        self.assertIn("dangling_parent", [f["issue"] for f in upward_violations(m)])

    def test_top_level_row_naming_a_parent_is_reported(self):
        m = matrix() + [row("T2", parent="SYS-1", top=True)]
        self.assertIn("top_level_with_parent",
                      [f["issue"] for f in upward_violations(m)])


class DownwardTest(unittest.TestCase):
    def test_parent_with_children_is_clean(self):
        self.assertEqual(downward_violations(matrix()), [])

    def test_requirement_expecting_children_with_none_is_reported(self):
        m = matrix() + [row("SYS-2", top=True, kids=True, node="SAT")]
        self.assertIn("no_downward_trace",
                      [f["issue"] for f in downward_violations(m)])

    def test_leaf_not_expecting_children_is_clean(self):
        self.assertEqual(downward_violations([row("L", parent=None, top=True)]), [])


class CycleTest(unittest.TestCase):
    def test_acyclic_matrix_reports_nothing(self):
        self.assertEqual(trace_cycles(matrix()), [])

    def test_two_row_cycle_is_found(self):
        m = [row("A", parent="B"), row("B", parent="A")]
        self.assertEqual(trace_cycles(m), ["A", "B"])

    def test_self_parent_is_a_cycle(self):
        self.assertEqual(trace_cycles([row("A", parent="A")]), ["A"])


class AllocationTest(unittest.TestCase):
    def test_known_allocation_is_clean(self):
        self.assertEqual(allocation_violations(matrix(), NODES), [])

    def test_unknown_allocation_target_is_reported(self):
        m = matrix() + [row("X", parent="SYS-1", node="GHOST")]
        self.assertEqual(allocation_violations(m, NODES)[0]["issue"],
                         "unknown_allocation_target")

    def test_unknown_method_reported_once_not_twice(self):
        m = [row("A", top=True, method="demo")]
        self.assertEqual(len(method_violations(m)), 1)
        self.assertEqual(field_violations(m[0]), [])


class ReviewTest(unittest.TestCase):
    def test_clean_matrix_is_complete(self):
        r = rtm_review(matrix(), NODES)
        self.assertEqual(r["row_count"], 3)
        self.assertEqual(r["top_level"], ["SYS-1"])
        self.assertTrue(is_rtm_complete(r))

    def test_any_gap_makes_it_incomplete(self):
        m = matrix() + [row("ORPHAN")]
        self.assertFalse(is_rtm_complete(rtm_review(m, NODES)))

    def test_duplicate_row_raises_from_the_review(self):
        with self.assertRaises(ValueError):
            rtm_review(matrix() + [row("AOCS-1", parent="SYS-1")], NODES)

    def test_review_does_not_mutate_input(self):
        import copy
        m = matrix()
        before = copy.deepcopy(m)
        rtm_review(m, NODES)
        self.assertEqual(m, before)

    def test_empty_matrix_is_vacuously_complete(self):
        self.assertTrue(is_rtm_complete(rtm_review([], NODES)))


if __name__ == "__main__":
    unittest.main()
