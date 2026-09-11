"""
Offline deterministic tests for e1003_el_mission_logic.py.
Covers: required-test derivation, coverage validation, test-group
assignment, result evaluation, and compliance aggregation.

Run: python3 test_e1003_el_mission.py
"""

import sys
import os
import unittest

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_mission_logic import (
    ELEMENT_TYPES,
    MISSION_ORBITS,
    compute_mission_test_compliance,
    categorize_test,
    determine_required_tests,
    evaluate_test_result,
    validate_test_plan,
)


class TestDetermineRequiredTests(unittest.TestCase):

    def test_leo_avionics_includes_orbit_and_element_tests(self):
        result = determine_required_tests("avionics", "LEO")
        # Orbit: functional, thermal_vacuum, atomic_oxygen, radiation, vibration, acoustic
        # Element: functional, emc, emi, radiation
        self.assertIn("atomic_oxygen", result)
        self.assertIn("emc", result)
        self.assertIn("emi", result)
        self.assertIn("thermal_vacuum", result)
        self.assertIn("radiation", result)
        self.assertIn("vibration", result)

    def test_geo_propulsion_includes_leak_and_proof_pressure(self):
        result = determine_required_tests("propulsion", "GEO")
        self.assertIn("leak", result)
        self.assertIn("proof_pressure", result)
        self.assertIn("shock", result)
        self.assertNotIn("atomic_oxygen", result)

    def test_interplanetary_structure_includes_sterilization(self):
        result = determine_required_tests("structure", "INTERPLANETARY")
        self.assertIn("sterilization", result)
        self.assertIn("static_load", result)
        self.assertIn("vibration", result)

    def test_heo_payload_excludes_atomic_oxygen(self):
        result = determine_required_tests("payload", "HEO")
        self.assertNotIn("atomic_oxygen", result)
        self.assertIn("calibration", result)
        self.assertIn("performance", result)

    def test_meo_power_excludes_acoustic(self):
        result = determine_required_tests("power", "MEO")
        self.assertNotIn("acoustic", result)
        self.assertIn("emi", result)

    def test_invalid_element_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            determine_required_tests("sensor", "LEO")
        self.assertIn("sensor", str(ctx.exception))

    def test_invalid_orbit_raises(self):
        with self.assertRaises(ValueError) as ctx:
            determine_required_tests("avionics", "LUNAR")
        self.assertIn("LUNAR", str(ctx.exception))

    def test_result_is_superset_of_orbit_categories(self):
        # Every orbit-driven category must appear in the union result
        result = determine_required_tests("payload", "GEO")
        for cat in ("functional", "thermal_vacuum", "radiation", "vibration", "acoustic", "shock"):
            self.assertIn(cat, result)


class TestValidateTestPlan(unittest.TestCase):

    def test_complete_coverage_yields_empty_missing(self):
        required = frozenset({"functional", "thermal_vacuum", "vibration"})
        planned = {"functional", "thermal_vacuum", "vibration"}
        result = validate_test_plan(required, planned)
        self.assertEqual(result["missing"], frozenset())
        self.assertEqual(result["covered"], required)

    def test_missing_test_detected(self):
        required = frozenset({"functional", "thermal_vacuum", "radiation"})
        planned = {"functional", "thermal_vacuum"}
        result = validate_test_plan(required, planned)
        self.assertIn("radiation", result["missing"])

    def test_extra_test_flagged(self):
        required = frozenset({"functional", "vibration"})
        planned = {"functional", "vibration", "static_load"}
        result = validate_test_plan(required, planned)
        self.assertIn("static_load", result["extra"])

    def test_empty_plan_all_required_missing(self):
        required = frozenset({"functional", "thermal_vacuum"})
        result = validate_test_plan(required, set())
        self.assertEqual(result["missing"], required)
        self.assertEqual(result["covered"], frozenset())


class TestCategorizeTest(unittest.TestCase):

    def test_functional_group(self):
        self.assertEqual(categorize_test("functional"), "functional")

    def test_thermal_vacuum_is_environmental(self):
        self.assertEqual(categorize_test("thermal_vacuum"), "environmental")

    def test_radiation_is_environmental(self):
        self.assertEqual(categorize_test("radiation"), "environmental")

    def test_emc_is_environmental(self):
        self.assertEqual(categorize_test("emc"), "environmental")

    def test_leak_is_performance_verification(self):
        self.assertEqual(categorize_test("leak"), "performance_verification")

    def test_calibration_is_performance_verification(self):
        self.assertEqual(categorize_test("calibration"), "performance_verification")

    def test_unknown_test_raises(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_test("not_a_real_test")
        self.assertIn("not_a_real_test", str(ctx.exception))


class TestEvaluateTestResult(unittest.TestCase):

    def test_max_limit_pass_below(self):
        r = evaluate_test_result("vibration", 5.0, 10.0, "max")
        self.assertEqual(r["status"], "pass")

    def test_max_limit_pass_equal(self):
        r = evaluate_test_result("vibration", 10.0, 10.0, "max")
        self.assertEqual(r["status"], "pass")

    def test_max_limit_fail_above(self):
        r = evaluate_test_result("vibration", 10.1, 10.0, "max")
        self.assertEqual(r["status"], "fail")

    def test_min_limit_pass_above(self):
        r = evaluate_test_result("functional", 95.0, 90.0, "min")
        self.assertEqual(r["status"], "pass")

    def test_min_limit_pass_equal(self):
        r = evaluate_test_result("functional", 90.0, 90.0, "min")
        self.assertEqual(r["status"], "pass")

    def test_min_limit_fail_below(self):
        r = evaluate_test_result("functional", 89.9, 90.0, "min")
        self.assertEqual(r["status"], "fail")

    def test_invalid_limit_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            evaluate_test_result("vibration", 5.0, 10.0, "range")
        self.assertIn("range", str(ctx.exception))

    def test_result_dict_contains_expected_keys(self):
        r = evaluate_test_result("shock", 3.2, 5.0, "max")
        for key in ("test_name", "measured_value", "limit_value", "limit_type", "status"):
            self.assertIn(key, r)
        self.assertEqual(r["test_name"], "shock")


class TestComputeMissionTestCompliance(unittest.TestCase):

    def _geo_structure_results(self):
        # Full coverage, all pass
        return [
            {"test_name": "vibration", "measured_value": 4.5, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "acoustic",  "measured_value": 3.0, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "shock",     "measured_value": 2.0, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "functional","measured_value": 100.0,"limit_value": 90.0,"limit_type": "min"},
        ]

    def test_compliant_when_coverage_full_and_all_pass(self):
        required = determine_required_tests("structure", "GEO")
        planned = set(required)  # full coverage
        results = self._geo_structure_results()
        report = compute_mission_test_compliance("structure", "GEO", planned, results)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_not_compliant_when_coverage_gap_exists(self):
        required = determine_required_tests("structure", "GEO")
        planned = required - {"shock"}  # deliberately drop one
        results = self._geo_structure_results()
        report = compute_mission_test_compliance("structure", "GEO", planned, results)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("shock" in f for f in report["findings"]))

    def test_not_compliant_when_result_fails(self):
        required = determine_required_tests("structure", "GEO")
        planned = set(required)
        results = [
            {"test_name": "vibration", "measured_value": 9.9, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "acoustic",  "measured_value": 3.0, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "shock",     "measured_value": 2.0, "limit_value": 5.0, "limit_type": "max"},
            {"test_name": "functional","measured_value": 100.0,"limit_value": 90.0,"limit_type": "min"},
        ]
        report = compute_mission_test_compliance("structure", "GEO", planned, results)
        self.assertFalse(report["compliant"])
        self.assertTrue(any("vibration" in f for f in report["findings"]))

    def test_not_compliant_when_both_gap_and_fail(self):
        required = determine_required_tests("structure", "GEO")
        planned = required - {"acoustic"}
        results = [
            {"test_name": "vibration", "measured_value": 9.9, "limit_value": 5.0, "limit_type": "max"},
        ]
        report = compute_mission_test_compliance("structure", "GEO", planned, results)
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["findings"]), 2)

    def test_report_contains_required_tests_field(self):
        required = determine_required_tests("avionics", "LEO")
        planned = set(required)
        report = compute_mission_test_compliance("avionics", "LEO", planned, [])
        self.assertEqual(report["required_tests"], required)

    def test_empty_results_with_full_coverage_is_compliant(self):
        required = determine_required_tests("payload", "GEO")
        planned = set(required)
        report = compute_mission_test_compliance("payload", "GEO", planned, [])
        self.assertTrue(report["compliant"])


if __name__ == "__main__":
    unittest.main()
