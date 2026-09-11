#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §4.2 development test planning
and evaluation.

Exercises scripts/e1003_dev_tests_logic.py (stdlib unittest, offline).
Contract: an objective dict missing any required field is flagged and
an empty objective returns all three missing fields; a non-dict
objective raises TypeError; a recognized test type returns its category
string and an unrecognized type raises ValueError; a condition within
the fractional tolerance band passes, one outside fails, and a negative
or over-one tolerance raises; a missing actual measurement for a
specified condition raises KeyError; a measurement within the min/max
bounds produces a pass outcome, one outside produces a fail, a missing
measurement is a failure, and a requirement without min or max raises;
a complete report has no missing fields and a report missing any field
is flagged; a plan with valid objectives and conditions has no errors
and is valid, while plans missing objectives, conditions, or containing
incomplete objectives are invalid; plan assembly does not mutate inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_dev_tests_logic as dt  # noqa: E402


class ValidateTestObjectiveTest(unittest.TestCase):
    def test_complete_objective_returns_no_missing_fields(self):
        obj = {
            "objective_id": "OBJ-001",
            "description": "Verify structural margin at proto-flight load level",
            "success_criterion": "No permanent deformation observed post-test",
        }
        self.assertEqual(dt.validate_test_objective(obj), [])

    def test_missing_success_criterion_is_flagged(self):
        obj = {"objective_id": "OBJ-002", "description": "Check thermal gradient"}
        missing = dt.validate_test_objective(obj)
        self.assertIn("success_criterion", missing)

    def test_missing_description_is_flagged(self):
        obj = {"objective_id": "OBJ-003", "success_criterion": "Pass"}
        missing = dt.validate_test_objective(obj)
        self.assertIn("description", missing)

    def test_empty_dict_returns_all_three_fields(self):
        missing = dt.validate_test_objective({})
        self.assertEqual(len(missing), 3)

    def test_non_dict_objective_raises_type_error(self):
        with self.assertRaises(TypeError):
            dt.validate_test_objective("not a dict")

    def test_non_dict_int_raises_type_error(self):
        with self.assertRaises(TypeError):
            dt.validate_test_objective(42)


class CategorizeTestTest(unittest.TestCase):
    def test_functional_is_recognized(self):
        self.assertEqual(dt.categorize_test("functional"), "functional")

    def test_environmental_is_recognized(self):
        self.assertEqual(dt.categorize_test("environmental"), "environmental")

    def test_thermal_is_recognized(self):
        self.assertEqual(dt.categorize_test("thermal"), "thermal")

    def test_structural_is_recognized(self):
        self.assertEqual(dt.categorize_test("structural"), "structural")

    def test_unrecognized_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.categorize_test("acoustic_magic")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.categorize_test("")


class CheckConditionWithinToleranceTest(unittest.TestCase):
    def test_exact_nominal_passes(self):
        self.assertTrue(dt.check_condition_within_tolerance(100.0, 100.0, 0.05))

    def test_within_tolerance_upper_edge_passes(self):
        self.assertTrue(dt.check_condition_within_tolerance(100.0, 105.0, 0.05))

    def test_outside_tolerance_fails(self):
        self.assertFalse(dt.check_condition_within_tolerance(100.0, 106.0, 0.05))

    def test_below_tolerance_lower_edge_fails(self):
        self.assertFalse(dt.check_condition_within_tolerance(100.0, 94.9, 0.05))

    def test_negative_tolerance_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.check_condition_within_tolerance(100.0, 100.0, -0.01)

    def test_tolerance_above_one_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.check_condition_within_tolerance(100.0, 100.0, 1.5)

    def test_zero_nominal_zero_actual_passes(self):
        self.assertTrue(dt.check_condition_within_tolerance(0.0, 0.0, 0.05))

    def test_zero_nominal_nonzero_actual_fails(self):
        self.assertFalse(dt.check_condition_within_tolerance(0.0, 0.1, 0.05))


class EvaluateTestConditionsTest(unittest.TestCase):
    def test_all_conditions_within_tolerance_pass(self):
        specified = {"temperature_K": 300.0, "pressure_Pa": 1.0e5}
        actual = {"temperature_K": 302.0, "pressure_Pa": 1.01e5}
        results = dt.evaluate_test_conditions(specified, actual, 0.05)
        self.assertTrue(results["temperature_K"]["within_tolerance"])
        self.assertTrue(results["pressure_Pa"]["within_tolerance"])

    def test_out_of_tolerance_condition_flagged(self):
        specified = {"temperature_K": 300.0}
        actual = {"temperature_K": 340.0}
        results = dt.evaluate_test_conditions(specified, actual, 0.05)
        self.assertFalse(results["temperature_K"]["within_tolerance"])

    def test_missing_actual_raises_key_error(self):
        with self.assertRaises(KeyError):
            dt.evaluate_test_conditions({"temperature_K": 300.0}, {}, 0.05)

    def test_result_carries_nominal_and_actual(self):
        specified = {"voltage_V": 5.0}
        actual = {"voltage_V": 5.1}
        results = dt.evaluate_test_conditions(specified, actual, 0.05)
        self.assertEqual(results["voltage_V"]["nominal"], 5.0)
        self.assertEqual(results["voltage_V"]["actual"], 5.1)


class EvaluateMeasurementsTest(unittest.TestCase):
    def test_measurement_within_bounds_is_pass(self):
        result = dt.evaluate_measurements(
            {"voltage_V": 3.3},
            {"voltage_V": {"min": 3.0, "max": 3.6}},
        )
        self.assertEqual(result["outcome"], "pass")
        self.assertEqual(result["failures"], [])

    def test_measurement_above_max_is_fail(self):
        result = dt.evaluate_measurements(
            {"voltage_V": 3.8},
            {"voltage_V": {"min": 3.0, "max": 3.6}},
        )
        self.assertEqual(result["outcome"], "fail")
        self.assertIn("voltage_V", result["failures"])

    def test_measurement_below_min_is_fail(self):
        result = dt.evaluate_measurements(
            {"voltage_V": 2.5},
            {"voltage_V": {"min": 3.0, "max": 3.6}},
        )
        self.assertEqual(result["outcome"], "fail")
        self.assertIn("voltage_V", result["failures"])

    def test_missing_measurement_is_a_failure(self):
        result = dt.evaluate_measurements(
            {},
            {"current_A": {"min": 0.1, "max": 0.5}},
        )
        self.assertEqual(result["outcome"], "fail")
        self.assertIn("current_A", result["failures"])

    def test_requirement_without_min_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.evaluate_measurements({"x": 1.0}, {"x": {"max": 2.0}})

    def test_requirement_without_max_raises_value_error(self):
        with self.assertRaises(ValueError):
            dt.evaluate_measurements({"x": 1.0}, {"x": {"min": 0.0}})

    def test_multiple_parameters_all_pass(self):
        result = dt.evaluate_measurements(
            {"temp_K": 295.0, "voltage_V": 3.3},
            {
                "temp_K": {"min": 280.0, "max": 320.0},
                "voltage_V": {"min": 3.0, "max": 3.6},
            },
        )
        self.assertEqual(result["outcome"], "pass")


class CheckReportCompletenessTest(unittest.TestCase):
    def _complete_report(self):
        return {
            "test_id": "DT-001",
            "objective_ids": ["OBJ-001"],
            "actual_conditions": {"temperature_K": 301.0},
            "measurements": {"voltage_V": 3.3},
            "outcome": "pass",
            "anomalies": [],
        }

    def test_complete_report_has_no_missing_fields(self):
        self.assertEqual(dt.check_report_completeness(self._complete_report()), [])

    def test_missing_outcome_is_flagged(self):
        report = self._complete_report()
        del report["outcome"]
        missing = dt.check_report_completeness(report)
        self.assertIn("outcome", missing)

    def test_missing_anomalies_is_flagged(self):
        report = self._complete_report()
        del report["anomalies"]
        missing = dt.check_report_completeness(report)
        self.assertIn("anomalies", missing)

    def test_non_dict_report_raises_type_error(self):
        with self.assertRaises(TypeError):
            dt.check_report_completeness(42)


class BuildDevelopmentTestPlanTest(unittest.TestCase):
    def _good_objective(self, oid="OBJ-001"):
        return {
            "objective_id": oid,
            "description": "Verify function under nominal conditions",
            "success_criterion": "Output within specification bounds",
        }

    def test_valid_plan_has_no_errors(self):
        plan = dt.build_development_test_plan(
            "DT-001",
            [self._good_objective()],
            {"temperature_K": 293.0},
        )
        self.assertEqual(plan["validation_errors"], [])
        self.assertTrue(dt.is_plan_valid(plan))

    def test_empty_objectives_makes_plan_invalid(self):
        plan = dt.build_development_test_plan("DT-002", [], {"temperature_K": 293.0})
        self.assertFalse(dt.is_plan_valid(plan))

    def test_empty_conditions_makes_plan_invalid(self):
        plan = dt.build_development_test_plan("DT-003", [self._good_objective()], {})
        self.assertFalse(dt.is_plan_valid(plan))

    def test_incomplete_objective_makes_plan_invalid(self):
        bad_obj = {"objective_id": "OBJ-X"}
        plan = dt.build_development_test_plan("DT-004", [bad_obj], {"temperature_K": 300.0})
        self.assertFalse(dt.is_plan_valid(plan))
        self.assertTrue(any("missing fields" in e for e in plan["validation_errors"]))

    def test_multiple_valid_objectives_all_accepted(self):
        objectives = [self._good_objective("OBJ-%d" % i) for i in range(3)]
        plan = dt.build_development_test_plan("DT-005", objectives, {"temperature_K": 300.0})
        self.assertTrue(dt.is_plan_valid(plan))
        self.assertEqual(len(plan["objectives"]), 3)

    def test_plan_assembly_does_not_mutate_inputs(self):
        objectives = [self._good_objective()]
        conditions = {"temperature_K": 300.0}
        dt.build_development_test_plan("DT-006", objectives, conditions)
        self.assertEqual(len(objectives), 1)
        self.assertEqual(len(conditions), 1)

    def test_plan_output_contains_test_id(self):
        plan = dt.build_development_test_plan(
            "DT-007", [self._good_objective()], {"pressure_Pa": 1.0e5}
        )
        self.assertEqual(plan["test_id"], "DT-007")


if __name__ == "__main__":
    unittest.main()
