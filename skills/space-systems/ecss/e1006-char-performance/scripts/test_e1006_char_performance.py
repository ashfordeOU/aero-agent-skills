#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §8.2.1 performance requirement
content check.

Exercises scripts/e1006_char_performance_logic.py (stdlib unittest,
offline). Contract: a performance requirement type is categorized as
"performance" and a non-performance type as "non_performance"; an
unrecognized type raises ValueError; a parameter is fully quantified
when it carries a numeric value, a non-empty unit string, and a
recognized operator — each missing component is a separate finding;
a performance requirement with no parameters is flagged without
inspecting individual parameters; non-performance requirements produce
no findings; the aggregate review maps each req_id to its findings
list; the set is compliant only when every findings list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_char_performance_logic as perf  # noqa: E402


class CategorizeRequirementTest(unittest.TestCase):
    def test_performance_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("performance"), "performance")

    def test_timing_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("timing"), "performance")

    def test_accuracy_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("accuracy"), "performance")

    def test_capacity_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("capacity"), "performance")

    def test_throughput_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("throughput"), "performance")

    def test_efficiency_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("efficiency"), "performance")

    def test_data_rate_type_is_performance(self):
        self.assertEqual(perf.categorize_requirement("data_rate"), "performance")

    def test_functional_type_is_non_performance(self):
        self.assertEqual(perf.categorize_requirement("functional"), "non_performance")

    def test_interface_type_is_non_performance(self):
        self.assertEqual(perf.categorize_requirement("interface"), "non_performance")

    def test_design_constraint_type_is_non_performance(self):
        self.assertEqual(perf.categorize_requirement("design_constraint"), "non_performance")

    def test_operational_type_is_non_performance(self):
        self.assertEqual(perf.categorize_requirement("operational"), "non_performance")

    def test_safety_type_is_non_performance(self):
        self.assertEqual(perf.categorize_requirement("safety"), "non_performance")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            perf.categorize_requirement("aesthetic_preference")


class CheckParameterTest(unittest.TestCase):
    def _valid_param(self):
        return {"name": "pointing_accuracy", "value": 0.1, "unit": "deg", "operator": "leq"}

    def test_valid_parameter_has_no_findings(self):
        self.assertEqual(perf.check_parameter(self._valid_param()), [])

    def test_integer_value_is_valid(self):
        p = {"name": "data_rate", "value": 100, "unit": "Mbps", "operator": "geq"}
        self.assertEqual(perf.check_parameter(p), [])

    def test_missing_value_flagged(self):
        p = {"name": "efficiency", "unit": "%", "operator": "geq"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("missing_numeric_value", issues)

    def test_none_value_flagged(self):
        p = {"name": "efficiency", "value": None, "unit": "%", "operator": "geq"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("missing_numeric_value", issues)

    def test_string_value_flagged(self):
        p = {"name": "efficiency", "value": "high", "unit": "%", "operator": "geq"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("missing_numeric_value", issues)

    def test_missing_unit_flagged(self):
        p = {"name": "response_time", "value": 50.0, "operator": "leq"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("missing_unit", issues)

    def test_empty_unit_flagged(self):
        p = {"name": "response_time", "value": 50.0, "unit": "  ", "operator": "leq"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("missing_unit", issues)

    def test_invalid_operator_flagged(self):
        p = {"name": "mass", "value": 10.0, "unit": "kg", "operator": "approximately"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("invalid_or_missing_operator", issues)

    def test_missing_operator_flagged(self):
        p = {"name": "mass", "value": 10.0, "unit": "kg"}
        issues = [f["issue"] for f in perf.check_parameter(p)]
        self.assertIn("invalid_or_missing_operator", issues)

    def test_range_operator_is_valid(self):
        p = {"name": "temperature", "value": 25.0, "unit": "degC", "operator": "range"}
        self.assertEqual(perf.check_parameter(p), [])

    def test_all_three_missing_generates_three_findings(self):
        p = {"name": "capacity"}
        findings = perf.check_parameter(p)
        issues = [f["issue"] for f in findings]
        self.assertIn("missing_numeric_value", issues)
        self.assertIn("missing_unit", issues)
        self.assertIn("invalid_or_missing_operator", issues)

    def test_finding_carries_parameter_name(self):
        p = {"name": "throughput", "unit": "Mbps", "operator": "geq"}
        findings = perf.check_parameter(p)
        self.assertTrue(all(f["parameter"] == "throughput" for f in findings))


class CheckRequirementPerformanceContentTest(unittest.TestCase):
    def test_non_performance_requirement_has_no_findings(self):
        req = {
            "req_id": "SYS-FUNC-001",
            "req_type": "functional",
            "performance_parameters": [],
        }
        self.assertEqual(perf.check_requirement_performance_content(req), [])

    def test_performance_req_with_no_parameters_flagged(self):
        req = {
            "req_id": "SYS-PERF-001",
            "req_type": "performance",
            "performance_parameters": [],
        }
        findings = perf.check_requirement_performance_content(req)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "performance_requirement_has_no_parameters")
        self.assertEqual(findings[0]["req_id"], "SYS-PERF-001")

    def test_performance_req_with_valid_params_has_no_findings(self):
        req = {
            "req_id": "SYS-PERF-002",
            "req_type": "accuracy",
            "performance_parameters": [
                {"name": "pointing_error", "value": 0.05, "unit": "deg", "operator": "leq"}
            ],
        }
        self.assertEqual(perf.check_requirement_performance_content(req), [])

    def test_performance_req_with_bad_param_flagged(self):
        req = {
            "req_id": "SYS-PERF-003",
            "req_type": "timing",
            "performance_parameters": [
                {"name": "latency", "value": None, "unit": "ms", "operator": "leq"}
            ],
        }
        findings = perf.check_requirement_performance_content(req)
        self.assertTrue(any(f["issue"] == "missing_numeric_value" for f in findings))
        self.assertTrue(all(f["req_id"] == "SYS-PERF-003" for f in findings))

    def test_unknown_req_type_raises(self):
        req = {"req_id": "SYS-X-001", "req_type": "aesthetic", "performance_parameters": []}
        with self.assertRaises(ValueError):
            perf.check_requirement_performance_content(req)

    def test_multiple_params_all_checked(self):
        req = {
            "req_id": "SYS-PERF-004",
            "req_type": "performance",
            "performance_parameters": [
                {"name": "data_rate", "value": 100, "unit": "Mbps", "operator": "geq"},
                {"name": "latency", "unit": "ms", "operator": "leq"},
            ],
        }
        findings = perf.check_requirement_performance_content(req)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "missing_numeric_value")
        self.assertEqual(findings[0]["parameter"], "latency")


class PerformanceContentReviewTest(unittest.TestCase):
    def _compliant_req(self, req_id):
        return {
            "req_id": req_id,
            "req_type": "performance",
            "performance_parameters": [
                {"name": "mass", "value": 50.0, "unit": "kg", "operator": "leq"}
            ],
        }

    def test_empty_set_is_compliant(self):
        review = perf.performance_content_review([])
        self.assertTrue(perf.is_performance_compliant(review))

    def test_all_compliant_requirements_produce_empty_findings(self):
        requirements = [self._compliant_req("SYS-PERF-001"), self._compliant_req("SYS-PERF-002")]
        review = perf.performance_content_review(requirements)
        self.assertEqual(review["SYS-PERF-001"], [])
        self.assertEqual(review["SYS-PERF-002"], [])
        self.assertTrue(perf.is_performance_compliant(review))

    def test_one_violation_makes_set_non_compliant(self):
        requirements = [
            self._compliant_req("SYS-PERF-001"),
            {
                "req_id": "SYS-PERF-002",
                "req_type": "efficiency",
                "performance_parameters": [],
            },
        ]
        review = perf.performance_content_review(requirements)
        self.assertEqual(review["SYS-PERF-001"], [])
        self.assertTrue(len(review["SYS-PERF-002"]) > 0)
        self.assertFalse(perf.is_performance_compliant(review))

    def test_non_performance_reqs_produce_no_findings(self):
        requirements = [
            {"req_id": "SYS-FUNC-001", "req_type": "functional", "performance_parameters": []},
            {"req_id": "SYS-INTF-001", "req_type": "interface", "performance_parameters": []},
        ]
        review = perf.performance_content_review(requirements)
        self.assertEqual(review["SYS-FUNC-001"], [])
        self.assertEqual(review["SYS-INTF-001"], [])

    def test_mixed_set_aggregates_correctly(self):
        requirements = [
            self._compliant_req("SYS-PERF-001"),
            {"req_id": "SYS-FUNC-001", "req_type": "functional", "performance_parameters": []},
            {
                "req_id": "SYS-PERF-002",
                "req_type": "timing",
                "performance_parameters": [
                    {"name": "boot_time", "value": 30, "unit": "s", "operator": "leq"}
                ],
            },
        ]
        review = perf.performance_content_review(requirements)
        self.assertEqual(review["SYS-PERF-001"], [])
        self.assertEqual(review["SYS-FUNC-001"], [])
        self.assertEqual(review["SYS-PERF-002"], [])
        self.assertTrue(perf.is_performance_compliant(review))

    def test_unknown_type_in_set_raises(self):
        requirements = [
            {"req_id": "SYS-??-001", "req_type": "unknown_type", "performance_parameters": []}
        ]
        with self.assertRaises(ValueError):
            perf.performance_content_review(requirements)


class IsPerformanceCompliantTest(unittest.TestCase):
    def test_all_empty_findings_is_compliant(self):
        review = {"SYS-PERF-001": [], "SYS-PERF-002": []}
        self.assertTrue(perf.is_performance_compliant(review))

    def test_any_nonempty_findings_is_not_compliant(self):
        review = {
            "SYS-PERF-001": [],
            "SYS-PERF-002": [{"issue": "missing_numeric_value", "parameter": "mass", "req_id": "SYS-PERF-002"}],
        }
        self.assertFalse(perf.is_performance_compliant(review))

    def test_empty_review_is_compliant(self):
        self.assertTrue(perf.is_performance_compliant({}))


if __name__ == "__main__":
    unittest.main()
