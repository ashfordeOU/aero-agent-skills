#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C requirement analysis (5.2.1).

Exercises scripts/e10_req_analysis_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - every requirement record
needs id/level/parent/text/rationale/origin/control_status, with origin
in derived|generated and control_status in draft|released|baselined;
a requirement is an orphan when its parent is neither a customer
requirement id nor another requirement id in the set; a requirement
counts as controlled only at released or baselined; level coverage
counts requirements per level.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_analysis_logic as ra  # noqa: E402


def make_req(id, level, parent, origin="derived", control_status="draft", text=None, rationale=None):
    return {
        "id": id,
        "level": level,
        "parent": parent,
        "text": text if text is not None else ("requirement text for %s" % id),
        "rationale": rationale if rationale is not None else ("rationale for %s" % id),
        "origin": origin,
        "control_status": control_status,
    }


class ValidateRequirementTest(unittest.TestCase):
    def test_valid_requirement_has_no_problems(self):
        req = make_req("SYS-001", "system", None)
        self.assertEqual(ra.validate_requirement(req), [])

    def test_missing_field_reported(self):
        req = make_req("SYS-001", "system", None)
        del req["rationale"]
        problems = ra.validate_requirement(req)
        self.assertIn("missing field: rationale", problems)

    def test_empty_text_reported(self):
        req = make_req("SYS-001", "system", None, text="")
        problems = ra.validate_requirement(req)
        self.assertIn("empty field: text", problems)

    def test_invalid_origin_reported(self):
        req = make_req("SYS-001", "system", None, origin="invented")
        problems = ra.validate_requirement(req)
        self.assertIn("invalid origin: 'invented'", problems)

    def test_invalid_control_status_reported(self):
        req = make_req("SYS-001", "system", None, control_status="approved")
        problems = ra.validate_requirement(req)
        self.assertIn("invalid control_status: 'approved'", problems)


class AnalyzeRequirementSetTest(unittest.TestCase):
    def test_clean_chain_has_no_problems(self):
        requirements = [
            make_req("SYS-001", "system", "CUST-001"),
            make_req("SUB-001", "subsystem", "SYS-001"),
        ]
        report = ra.analyze_requirement_set(["CUST-001"], requirements)
        self.assertEqual(report, {})

    def test_customer_root_with_none_parent_is_not_orphan(self):
        requirements = [make_req("SYS-001", "system", None)]
        report = ra.analyze_requirement_set(["CUST-001"], requirements)
        self.assertEqual(report, {})

    def test_orphan_parent_reported(self):
        requirements = [make_req("SUB-001", "subsystem", "SYS-999")]
        report = ra.analyze_requirement_set(["CUST-001"], requirements)
        self.assertIn("SUB-001", report)
        self.assertTrue(any("orphan" in p for p in report["SUB-001"]))

    def test_duplicate_id_reported(self):
        requirements = [
            make_req("SYS-001", "system", "CUST-001"),
            make_req("SYS-001", "system", "CUST-001"),
        ]
        report = ra.analyze_requirement_set(["CUST-001"], requirements)
        self.assertIn("SYS-001", report)

    def test_invalid_requirement_reported_by_id(self):
        req = make_req("SYS-001", "system", None)
        req["origin"] = "bogus"
        report = ra.analyze_requirement_set([], [req])
        self.assertIn("SYS-001", report)


class ControlReadinessTest(unittest.TestCase):
    def test_ready_when_all_released_or_baselined(self):
        requirements = [
            make_req("SYS-001", "system", None, control_status="released"),
            make_req("SUB-001", "subsystem", "SYS-001", control_status="baselined"),
        ]
        ready, uncontrolled = ra.control_readiness(requirements)
        self.assertTrue(ready)
        self.assertEqual(uncontrolled, [])

    def test_not_ready_lists_draft_ids_in_order(self):
        requirements = [
            make_req("SYS-001", "system", None, control_status="draft"),
            make_req("SUB-001", "subsystem", "SYS-001", control_status="released"),
            make_req("SUB-002", "subsystem", "SYS-001", control_status="draft"),
        ]
        ready, uncontrolled = ra.control_readiness(requirements)
        self.assertFalse(ready)
        self.assertEqual(uncontrolled, ["SYS-001", "SUB-002"])


class LowerLevelCoverageTest(unittest.TestCase):
    def test_counts_per_level_in_first_seen_order(self):
        requirements = [
            make_req("SYS-001", "system", None),
            make_req("SUB-001", "subsystem", "SYS-001"),
            make_req("SUB-002", "subsystem", "SYS-001"),
            make_req("EQ-001", "equipment", "SUB-001"),
        ]
        coverage = ra.lower_level_coverage(requirements)
        self.assertEqual(coverage, {"system": 1, "subsystem": 2, "equipment": 1})
        self.assertEqual(list(coverage.keys()), ["system", "subsystem", "equipment"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
