#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.6.5 software tool
qualification for verification by analysis.

Exercises scripts/e1002_sw_tools_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - domain check flags any
analysis parameter missing from or outside the tool's validated domain;
qualification status follows fixed precedence (not validated ->
not_qualified; unvalidated configuration -> pending configuration
control; out-of-domain conditions -> qualified_out_of_domain;
safety-critical without an independent check -> pending independent
check; otherwise qualified); the qualification record covers every
tool-usage id with no duplicates; only 'qualified' records are
acceptable as verification evidence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_sw_tools_logic as sw  # noqa: E402


class CheckDomainTest(unittest.TestCase):
    def test_in_domain_returns_empty(self):
        self.assertEqual(
            sw.check_domain({"temperature": (0, 100)}, {"temperature": 50}),
            [],
        )

    def test_out_of_range_is_flagged(self):
        self.assertEqual(
            sw.check_domain({"temperature": (0, 100)}, {"temperature": 150}),
            ["temperature"],
        )

    def test_missing_bounds_is_flagged(self):
        self.assertEqual(
            sw.check_domain({}, {"pressure": 10}),
            ["pressure"],
        )

    def test_multiple_parameters_sorted(self):
        self.assertEqual(
            sw.check_domain(
                {"temperature": (0, 100)},
                {"temperature": 150, "pressure": 10},
            ),
            ["pressure", "temperature"],
        )


class QualifyToolTest(unittest.TestCase):
    BASE = {
        "validated": True,
        "configuration_controlled": True,
        "validated_domain": {"load": (0, 10)},
    }

    def test_unvalidated_is_not_qualified(self):
        tool = dict(self.BASE, validated=False)
        self.assertEqual(sw.qualify_tool(tool, {"load": 5}), "not_qualified")

    def test_unvalidated_wins_over_other_deficiencies(self):
        tool = dict(self.BASE, validated=False, configuration_controlled=False)
        self.assertEqual(sw.qualify_tool(tool, {"load": 500}), "not_qualified")

    def test_uncontrolled_configuration(self):
        tool = dict(self.BASE, configuration_controlled=False)
        self.assertEqual(
            sw.qualify_tool(tool, {"load": 5}),
            "qualified_pending_configuration_control",
        )

    def test_out_of_domain(self):
        self.assertEqual(sw.qualify_tool(self.BASE, {"load": 500}), "qualified_out_of_domain")

    def test_safety_critical_without_independent_check(self):
        tool = dict(self.BASE, safety_critical=True)
        self.assertEqual(
            sw.qualify_tool(tool, {"load": 5}),
            "qualified_pending_independent_check",
        )

    def test_safety_critical_with_independent_check(self):
        tool = dict(self.BASE, safety_critical=True, independent_check=True)
        self.assertEqual(sw.qualify_tool(tool, {"load": 5}), "qualified")

    def test_non_safety_critical_fully_qualified(self):
        self.assertEqual(sw.qualify_tool(self.BASE, {"load": 5}), "qualified")


class QualifyToolUsageTest(unittest.TestCase):
    def test_full_record(self):
        usage = {
            "id": "TOOL-001",
            "validated": True,
            "configuration_controlled": True,
            "validated_domain": {"load": (0, 10)},
            "analysis_conditions": {"load": 5},
        }
        self.assertEqual(
            sw.qualify_tool_usage(usage),
            {"id": "TOOL-001", "status": "qualified", "out_of_domain_parameters": []},
        )

    def test_out_of_domain_record_lists_parameters(self):
        usage = {
            "id": "TOOL-002",
            "validated": True,
            "configuration_controlled": True,
            "validated_domain": {"load": (0, 10)},
            "analysis_conditions": {"load": 500},
        }
        self.assertEqual(
            sw.qualify_tool_usage(usage),
            {
                "id": "TOOL-002",
                "status": "qualified_out_of_domain",
                "out_of_domain_parameters": ["load"],
            },
        )

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            sw.qualify_tool_usage({
                "validated": True,
                "configuration_controlled": True,
                "validated_domain": {},
                "analysis_conditions": {},
            })


class BuildQualificationRecordTest(unittest.TestCase):
    USAGES = [
        {
            "id": "TOOL-001",
            "validated": True,
            "configuration_controlled": True,
            "validated_domain": {"load": (0, 10)},
            "analysis_conditions": {"load": 5},
        },
        {
            "id": "TOOL-002",
            "validated": False,
            "configuration_controlled": True,
            "validated_domain": {"load": (0, 10)},
            "analysis_conditions": {"load": 5},
        },
    ]

    def test_record_order_and_content(self):
        records = sw.build_qualification_record(self.USAGES)
        self.assertEqual(
            records,
            [
                {"id": "TOOL-001", "status": "qualified", "out_of_domain_parameters": []},
                {"id": "TOOL-002", "status": "not_qualified", "out_of_domain_parameters": []},
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            sw.build_qualification_record(self.USAGES + [self.USAGES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(u) for u in self.USAGES]
        sw.build_qualification_record(self.USAGES)
        self.assertEqual(self.USAGES, before)


class AcceptanceTest(unittest.TestCase):
    def test_qualified_is_acceptable(self):
        self.assertTrue(sw.acceptable_for_verification_evidence({"status": "qualified"}))

    def test_non_qualified_is_not_acceptable(self):
        self.assertFalse(
            sw.acceptable_for_verification_evidence({"status": "qualified_out_of_domain"})
        )

    def test_find_unacceptable_lists_flagged_ids_in_order(self):
        records = [
            {"id": "TOOL-001", "status": "qualified"},
            {"id": "TOOL-002", "status": "qualified_out_of_domain"},
            {"id": "TOOL-003", "status": "qualified_pending_independent_check"},
        ]
        self.assertEqual(sw.find_unacceptable(records), ["TOOL-002", "TOOL-003"])

    def test_find_unacceptable_clean_set(self):
        records = [{"id": "TOOL-001", "status": "qualified"}]
        self.assertEqual(sw.find_unacceptable(records), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
