"""
Gate-3 contract tests for e1003-el-qual logic.
Run: python3 test_e1003_el_qual.py
Offline, deterministic, stdlib unittest only.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_qual_logic import (
    VALID_ELEMENT_CATEGORIES,
    VALID_QUAL_CATEGORIES,
    VALID_TEST_TYPES,
    VALID_ENVIRONMENT_DRIVERS,
    determine_qual_category,
    determine_required_tests,
    compute_qual_level,
    compute_qual_duration,
    validate_test_plan,
)


class TestDetermineQualCategory(unittest.TestCase):

    def test_full_qual_engineering_model_with_proto(self):
        result = determine_qual_category("engineering_model", True)
        self.assertEqual(result, "full_qualification")

    def test_full_qual_flight_model_with_proto(self):
        result = determine_qual_category("flight_model", True)
        self.assertEqual(result, "full_qualification")

    def test_protoflight_model_always_protoflight(self):
        # A protoflight_model article is always protoflight regardless of flag
        result = determine_qual_category("protoflight_model", True)
        self.assertEqual(result, "protoflight")

    def test_flight_model_without_proto_is_protoflight(self):
        result = determine_qual_category("flight_model", False)
        self.assertEqual(result, "protoflight")

    def test_engineering_model_without_proto_is_protoflight(self):
        result = determine_qual_category("engineering_model", False)
        self.assertEqual(result, "protoflight")

    def test_breadboard_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            determine_qual_category("breadboard", False)
        self.assertIn("Breadboard", str(ctx.exception))

    def test_unknown_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            determine_qual_category("flight_spare", True)

    def test_non_bool_dedicated_raises_type_error(self):
        with self.assertRaises(TypeError):
            determine_qual_category("flight_model", "yes")


class TestDetermineRequiredTests(unittest.TestCase):

    def test_launch_vibration_returns_three_types(self):
        result = determine_required_tests(["launch_vibration"])
        self.assertIn("sine_vibration", result)
        self.assertIn("random_vibration", result)
        self.assertIn("quasi_static", result)
        self.assertEqual(len(result), 3)

    def test_launch_acoustic_returns_acoustic(self):
        result = determine_required_tests(["launch_acoustic"])
        self.assertEqual(result, {"acoustic"})

    def test_on_orbit_thermal_returns_thermal_types(self):
        result = determine_required_tests(["on_orbit_thermal"])
        self.assertIn("thermal_cycling", result)
        self.assertIn("thermal_vacuum", result)

    def test_multiple_drivers_union(self):
        result = determine_required_tests(["launch_vibration", "launch_acoustic"])
        self.assertIn("sine_vibration", result)
        self.assertIn("acoustic", result)

    def test_duplicate_drivers_no_duplication(self):
        result = determine_required_tests(["launch_shock", "pyrotechnic_shock"])
        self.assertEqual(result, {"shock"})

    def test_empty_drivers_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            determine_required_tests([])
        self.assertIn("least one", str(ctx.exception))

    def test_unknown_driver_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            determine_required_tests(["magnetic_torque"])
        self.assertIn("Unrecognized", str(ctx.exception))


class TestComputeQualLevel(unittest.TestCase):

    def test_sine_vibration_adds_3db(self):
        result = compute_qual_level("sine_vibration", 10.0)
        self.assertAlmostEqual(result["qual_level"], 13.0)
        self.assertEqual(result["margin_type"], "db")
        self.assertEqual(result["margin"], 3.0)

    def test_random_vibration_adds_3db(self):
        result = compute_qual_level("random_vibration", 5.5)
        self.assertAlmostEqual(result["qual_level"], 8.5)

    def test_shock_adds_3db(self):
        result = compute_qual_level("shock", 1000.0)
        self.assertAlmostEqual(result["qual_level"], 1003.0)

    def test_acoustic_adds_3db(self):
        result = compute_qual_level("acoustic", 140.0)
        self.assertAlmostEqual(result["qual_level"], 143.0)

    def test_thermal_cycling_upper_adds_10degc(self):
        result = compute_qual_level("thermal_cycling", 70.0, upper=True)
        self.assertAlmostEqual(result["qual_level"], 80.0)
        self.assertEqual(result["margin_type"], "degc")

    def test_thermal_cycling_lower_subtracts_10degc(self):
        result = compute_qual_level("thermal_cycling", -20.0, upper=False)
        self.assertAlmostEqual(result["qual_level"], -30.0)

    def test_thermal_vacuum_upper(self):
        result = compute_qual_level("thermal_vacuum", 80.0, upper=True)
        self.assertAlmostEqual(result["qual_level"], 90.0)

    def test_quasi_static_multiplies_by_1_5(self):
        result = compute_qual_level("quasi_static", 20.0)
        self.assertAlmostEqual(result["qual_level"], 30.0)
        self.assertEqual(result["margin_type"], "factor")

    def test_unknown_test_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_level("magnetic_cleanliness", 10.0)

    def test_non_numeric_level_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_level("sine_vibration", "high")

    def test_result_contains_acceptance_level(self):
        result = compute_qual_level("sine_vibration", 7.0)
        self.assertAlmostEqual(result["acceptance_level"], 7.0)
        self.assertEqual(result["test_type"], "sine_vibration")


class TestComputeQualDuration(unittest.TestCase):

    def test_full_qual_sine_vibration_doubles_duration(self):
        result = compute_qual_duration("sine_vibration", 60.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 120.0)
        self.assertAlmostEqual(result["factor"], 2.0)

    def test_full_qual_random_vibration_quadruples_duration(self):
        result = compute_qual_duration("random_vibration", 60.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 240.0)

    def test_full_qual_random_vibration_enforces_120s_floor(self):
        # 10 s × 4 = 40 s < 120 s floor
        result = compute_qual_duration("random_vibration", 10.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 120.0)
        self.assertTrue(any("120" in n for n in result["notes"]))

    def test_protoflight_random_vibration_enforces_120s_floor(self):
        # protoflight keeps acceptance duration, but floor still applies
        result = compute_qual_duration("random_vibration", 30.0, "protoflight")
        self.assertAlmostEqual(result["qual_duration"], 120.0)

    def test_protoflight_uses_acceptance_duration(self):
        result = compute_qual_duration("sine_vibration", 45.0, "protoflight")
        self.assertAlmostEqual(result["qual_duration"], 45.0)
        self.assertAlmostEqual(result["factor"], 1.0)
        self.assertTrue(any("protoflight" in n for n in result["notes"]))

    def test_full_qual_thermal_vacuum_adds_2h_soak(self):
        result = compute_qual_duration("thermal_vacuum", 6.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 8.0)
        self.assertIsNone(result["factor"])

    def test_full_qual_acoustic_doubles_duration(self):
        result = compute_qual_duration("acoustic", 30.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 60.0)

    def test_full_qual_shock_enforces_3_shot_floor(self):
        # acceptance 1 shot × 1.0 factor = 1 shot < 3 shot floor
        result = compute_qual_duration("shock", 1.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 3.0)
        self.assertTrue(any("3" in n for n in result["notes"]))

    def test_full_qual_thermal_cycling_doubles_cycles(self):
        result = compute_qual_duration("thermal_cycling", 8.0, "full_qualification")
        self.assertAlmostEqual(result["qual_duration"], 16.0)

    def test_zero_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_duration("sine_vibration", 0.0, "full_qualification")

    def test_negative_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_duration("sine_vibration", -10.0, "full_qualification")

    def test_unknown_test_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_duration("pressure_cycle", 5.0, "full_qualification")

    def test_unknown_qual_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_qual_duration("sine_vibration", 60.0, "acceptance_only")


class TestValidateTestPlan(unittest.TestCase):

    def _compliant_item(self, test_type, acc_level, acc_dur, qual_cat):
        """Build a plan item that exactly meets the qualification requirements."""
        level_r = compute_qual_level(test_type, acc_level, upper=True)
        dur_r = compute_qual_duration(test_type, acc_dur, qual_cat)
        return {
            "test_type": test_type,
            "acceptance_level": acc_level,
            "proposed_level": level_r["qual_level"],
            "acceptance_duration": acc_dur,
            "proposed_duration": dur_r["qual_duration"],
        }

    def test_compliant_plan_returns_no_findings(self):
        item = self._compliant_item("sine_vibration", 10.0, 60.0, "full_qualification")
        findings = validate_test_plan([item], "full_qualification")
        self.assertEqual(findings, [])

    def test_multiple_compliant_items_no_findings(self):
        items = [
            self._compliant_item("sine_vibration", 10.0, 60.0, "full_qualification"),
            self._compliant_item("thermal_vacuum", 6.0, 6.0, "full_qualification"),
        ]
        findings = validate_test_plan(items, "full_qualification")
        self.assertEqual(findings, [])

    def test_insufficient_level_flagged(self):
        item = {
            "test_type": "sine_vibration",
            "acceptance_level": 10.0,
            "proposed_level": 11.0,   # needs 13.0
            "acceptance_duration": 60.0,
            "proposed_duration": 120.0,
        }
        findings = validate_test_plan([item], "full_qualification")
        level_findings = [f for f in findings if f["field"] == "level"]
        self.assertEqual(len(level_findings), 1)
        self.assertEqual(level_findings[0]["status"], "INSUFFICIENT")
        self.assertAlmostEqual(level_findings[0]["required"], 13.0)

    def test_insufficient_duration_flagged(self):
        item = {
            "test_type": "random_vibration",
            "acceptance_level": 5.0,
            "proposed_level": 8.0,
            "acceptance_duration": 60.0,
            "proposed_duration": 100.0,  # needs 240.0 (4× 60)
        }
        findings = validate_test_plan([item], "full_qualification")
        dur_findings = [f for f in findings if f["field"] == "duration"]
        self.assertEqual(len(dur_findings), 1)
        self.assertEqual(dur_findings[0]["status"], "INSUFFICIENT")

    def test_invalid_test_type_flagged(self):
        item = {
            "test_type": "pressure_cycle",
            "acceptance_level": 5.0,
            "proposed_level": 8.0,
            "acceptance_duration": 10.0,
            "proposed_duration": 20.0,
        }
        findings = validate_test_plan([item], "full_qualification")
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["status"], "INVALID")

    def test_missing_level_fields_flagged(self):
        item = {
            "test_type": "acoustic",
            "proposed_level": 143.0,
            # acceptance_level missing
            "acceptance_duration": 30.0,
            "proposed_duration": 60.0,
        }
        findings = validate_test_plan([item], "full_qualification")
        level_findings = [f for f in findings if f["field"] == "level"]
        self.assertEqual(len(level_findings), 1)
        self.assertEqual(level_findings[0]["status"], "MISSING")

    def test_protoflight_plan_uses_acceptance_duration(self):
        # Protoflight: qual level, acceptance duration — both must be met
        item = {
            "test_type": "thermal_cycling",
            "acceptance_level": 70.0,
            "proposed_level": 80.0,   # 70 + 10 — exact qual level
            "acceptance_duration": 8.0,
            "proposed_duration": 8.0,  # protoflight: keep acceptance cycles
        }
        findings = validate_test_plan([item], "protoflight")
        self.assertEqual(findings, [])

    def test_empty_plan_returns_no_findings(self):
        findings = validate_test_plan([], "full_qualification")
        self.assertEqual(findings, [])

    def test_invalid_qual_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_test_plan([], "development_only")


if __name__ == "__main__":
    unittest.main()
