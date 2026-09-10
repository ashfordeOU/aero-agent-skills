#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C sec 5.2.3.1 next-lower-level TRS
flow-down.

Exercises scripts/e10_trs_flowdown_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a TRS is section-complete
only when it carries all required DRD sections; a TS requirement is
flowed down only when at least one TRS carries its id; a TRS in conflict
with the parent TS or a sibling TRS is reported by requirement id and
document name; flow-down is ready only when there are no missing
sections, no coverage gaps, and no parent-child or sibling conflicts.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_trs_flowdown_logic as fd  # noqa: E402


class SectionGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_present(self):
        self.assertEqual(
            fd.section_gaps(fd.REQUIRED_TRS_SECTIONS),
            [],
        )

    def test_missing_sections_listed_in_order(self):
        self.assertEqual(
            fd.section_gaps(["scope", "requirements"]),
            ["applicable and reference documents", "verification requirements"],
        )

    def test_empty_input_lists_all_sections(self):
        self.assertEqual(fd.section_gaps([]), list(fd.REQUIRED_TRS_SECTIONS))


class FlowdownCoverageTest(unittest.TestCase):
    def test_fully_covered(self):
        ts = {"TS-1": 10, "TS-2": 20}
        trs = {
            "TRS-A": {"requirements": {"TS-1": 10}},
            "TRS-B": {"requirements": {"TS-2": 20}},
        }
        self.assertEqual(fd.flowdown_coverage(ts, trs), [])

    def test_uncovered_requirement_listed(self):
        ts = {"TS-1": 10, "TS-2": 20}
        trs = {"TRS-A": {"requirements": {"TS-1": 10}}}
        self.assertEqual(fd.flowdown_coverage(ts, trs), ["TS-2"])

    def test_no_trs_documents_all_uncovered(self):
        ts = {"TS-1": 10}
        self.assertEqual(fd.flowdown_coverage(ts, {}), ["TS-1"])


class ParentChildConflictsTest(unittest.TestCase):
    def test_matching_value_no_conflict(self):
        ts = {"TS-1": 10}
        trs = {"TRS-A": {"requirements": {"TS-1": 10}}}
        self.assertEqual(fd.parent_child_conflicts(ts, trs), [])

    def test_mismatched_value_reported(self):
        ts = {"TS-1": 10}
        trs = {"TRS-A": {"requirements": {"TS-1": 12}}}
        self.assertEqual(
            fd.parent_child_conflicts(ts, trs),
            [("TRS-A", "TS-1", 10, 12)],
        )

    def test_trs_only_requirement_not_a_conflict(self):
        ts = {"TS-1": 10}
        trs = {"TRS-A": {"requirements": {"TS-1": 10, "DERIVED-1": 5}}}
        self.assertEqual(fd.parent_child_conflicts(ts, trs), [])


class SiblingConflictsTest(unittest.TestCase):
    def test_matching_shared_requirement_no_conflict(self):
        trs = {
            "TRS-A": {"requirements": {"IF-1": 5}},
            "TRS-B": {"requirements": {"IF-1": 5}},
        }
        self.assertEqual(fd.sibling_conflicts(trs), [])

    def test_mismatched_shared_requirement_reported(self):
        trs = {
            "TRS-A": {"requirements": {"IF-1": 5}},
            "TRS-B": {"requirements": {"IF-1": 7}},
        }
        self.assertEqual(
            fd.sibling_conflicts(trs),
            [("IF-1", "TRS-A", 5, "TRS-B", 7)],
        )

    def test_disjoint_requirement_sets_no_conflict(self):
        trs = {
            "TRS-A": {"requirements": {"A-1": 1}},
            "TRS-B": {"requirements": {"B-1": 2}},
        }
        self.assertEqual(fd.sibling_conflicts(trs), [])


class TrsFlowdownReadyTest(unittest.TestCase):
    def test_ready_when_clean(self):
        ts = {"TS-1": 10}
        trs = {
            "TRS-A": {
                "sections": fd.REQUIRED_TRS_SECTIONS,
                "requirements": {"TS-1": 10},
            },
        }
        ready, issues = fd.trs_flowdown_ready(ts, trs)
        self.assertTrue(ready)
        self.assertEqual(issues["missing_sections"], {})
        self.assertEqual(issues["uncovered"], [])
        self.assertEqual(issues["parent_child_conflicts"], [])
        self.assertEqual(issues["sibling_conflicts"], [])

    def test_not_ready_reports_every_issue_type(self):
        ts = {"TS-1": 10, "TS-2": 20}
        trs = {
            "TRS-A": {
                "sections": ["scope"],
                "requirements": {"TS-1": 11, "IF-1": 5},
            },
            "TRS-B": {
                "sections": fd.REQUIRED_TRS_SECTIONS,
                "requirements": {"IF-1": 6},
            },
        }
        ready, issues = fd.trs_flowdown_ready(ts, trs)
        self.assertFalse(ready)
        self.assertIn("TRS-A", issues["missing_sections"])
        self.assertEqual(issues["uncovered"], ["TS-2"])
        self.assertEqual(issues["parent_child_conflicts"], [("TRS-A", "TS-1", 10, 11)])
        self.assertEqual(issues["sibling_conflicts"], [("IF-1", "TRS-A", 5, "TRS-B", 6)])


if __name__ == "__main__":
    unittest.main(verbosity=2)
