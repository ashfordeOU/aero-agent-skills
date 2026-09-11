"""
Offline deterministic contract tests for e1003_el_mechanical_logic.
Run: python3 test_e1003_el_mechanical.py
Must print OK.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_mechanical_logic import (
    VALID_TEST_TYPES,
    VALID_LEVELS,
    CANONICAL_ORDER,
    categorize_test,
    check_physical_properties,
    check_modal_survey,
    check_static_load,
    check_vibration_level,
    check_acoustic_level,
    check_test_sequence,
    check_test_level,
)


class TestCategorizeTest(unittest.TestCase):

    def test_physical_properties_is_mass_properties_family(self):
        self.assertEqual(categorize_test("physical_properties"), "mass_properties")

    def test_modal_survey_is_dynamic_family(self):
        self.assertEqual(categorize_test("modal_survey"), "dynamic")

    def test_acoustic_is_dynamic_family(self):
        self.assertEqual(categorize_test("acoustic"), "dynamic")

    def test_random_vibration_is_dynamic_family(self):
        self.assertEqual(categorize_test("random_vibration"), "dynamic")

    def test_sinusoidal_vibration_is_dynamic_family(self):
        self.assertEqual(categorize_test("sinusoidal_vibration"), "dynamic")

    def test_static_load_is_structural_family(self):
        self.assertEqual(categorize_test("static_load"), "structural")

    def test_spin_is_structural_family(self):
        self.assertEqual(categorize_test("spin"), "structural")

    def test_transient_sine_burst_is_structural_family(self):
        self.assertEqual(categorize_test("transient_sine_burst"), "structural")

    def test_unknown_test_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_test("laser_interferometry")

    def test_all_eight_test_types_are_valid(self):
        expected = {
            "physical_properties", "modal_survey", "static_load", "spin",
            "transient_sine_burst", "acoustic", "random_vibration",
            "sinusoidal_vibration",
        }
        self.assertEqual(VALID_TEST_TYPES, expected)


class TestPhysicalProperties(unittest.TestCase):

    def test_all_within_budget_is_compliant(self):
        result = check_physical_properties(10.0, 12.0, 0.01, 0.05)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_mass_over_budget_is_flagged(self):
        result = check_physical_properties(13.0, 12.0, 0.01, 0.05)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Mass" in f for f in result["findings"]))

    def test_cm_offset_over_limit_is_flagged(self):
        result = check_physical_properties(10.0, 12.0, 0.06, 0.05)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("CoM" in f for f in result["findings"]))

    def test_moi_over_limit_is_flagged(self):
        result = check_physical_properties(
            10.0, 12.0, 0.01, 0.05, moi_kgm2=2.0, moi_limit_kgm2=1.5
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("MoI" in f for f in result["findings"]))

    def test_moi_within_limit_stays_compliant(self):
        result = check_physical_properties(
            10.0, 12.0, 0.01, 0.05, moi_kgm2=1.2, moi_limit_kgm2=1.5
        )
        self.assertTrue(result["compliant"])

    def test_multiple_exceedances_appear_together(self):
        result = check_physical_properties(13.0, 12.0, 0.06, 0.05)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            check_physical_properties(-1.0, 12.0, 0.01, 0.05)

    def test_negative_cm_offset_raises(self):
        with self.assertRaises(ValueError):
            check_physical_properties(10.0, 12.0, -0.01, 0.05)

    def test_moi_without_limit_raises(self):
        with self.assertRaises(ValueError):
            check_physical_properties(10.0, 12.0, 0.01, 0.05, moi_kgm2=1.0)


class TestModalSurvey(unittest.TestCase):

    def test_frequency_above_minimum_is_compliant(self):
        result = check_modal_survey(100.0, 80.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_hz"], 20.0)

    def test_frequency_below_minimum_is_flagged(self):
        result = check_modal_survey(75.0, 80.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin_hz"], -5.0)

    def test_frequency_exactly_at_minimum_is_compliant(self):
        result = check_modal_survey(80.0, 80.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_hz"], 0.0)

    def test_zero_measured_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_modal_survey(0.0, 80.0)

    def test_zero_minimum_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_modal_survey(80.0, 0.0)


class TestStaticLoad(unittest.TestCase):

    def test_load_within_allowable_is_compliant(self):
        result = check_static_load(900.0, 1000.0, safety_factor=1.25)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_n"], 350.0)

    def test_load_over_allowable_is_flagged(self):
        result = check_static_load(1300.0, 1000.0, safety_factor=1.25)
        self.assertFalse(result["compliant"])

    def test_safety_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            check_static_load(900.0, 1000.0, safety_factor=0.9)

    def test_zero_applied_load_raises(self):
        with self.assertRaises(ValueError):
            check_static_load(0.0, 1000.0)

    def test_default_safety_factor_is_unity(self):
        result = check_static_load(999.0, 1000.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_n"], 1.0)


class TestVibrationLevel(unittest.TestCase):

    def test_random_vibration_at_spec_is_compliant(self):
        result = check_vibration_level("random_vibration", 10.0, 10.0)
        self.assertTrue(result["compliant"])

    def test_random_vibration_at_upper_bound_is_compliant(self):
        result = check_vibration_level("random_vibration", 11.0, 10.0)
        self.assertTrue(result["compliant"])

    def test_random_vibration_above_upper_bound_is_flagged(self):
        result = check_vibration_level("random_vibration", 11.1, 10.0)
        self.assertFalse(result["compliant"])

    def test_sinusoidal_vibration_below_lower_bound_is_flagged(self):
        result = check_vibration_level("sinusoidal_vibration", 8.9, 10.0)
        self.assertFalse(result["compliant"])

    def test_sinusoidal_vibration_at_lower_bound_is_compliant(self):
        result = check_vibration_level("sinusoidal_vibration", 9.0, 10.0)
        self.assertTrue(result["compliant"])

    def test_invalid_test_type_raises(self):
        with self.assertRaises(ValueError):
            check_vibration_level("acoustic", 10.0, 10.0)

    def test_zero_specification_raises(self):
        with self.assertRaises(ValueError):
            check_vibration_level("random_vibration", 10.0, 0.0)


class TestAcousticLevel(unittest.TestCase):

    def test_within_3db_is_compliant(self):
        result = check_acoustic_level(141.0, 142.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["deviation_db"], 1.0)

    def test_exactly_3db_over_is_compliant(self):
        result = check_acoustic_level(145.0, 142.0)
        self.assertTrue(result["compliant"])

    def test_beyond_3db_is_flagged(self):
        result = check_acoustic_level(146.0, 142.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["deviation_db"], 4.0)

    def test_below_by_more_than_3db_is_flagged(self):
        result = check_acoustic_level(138.0, 142.0)
        self.assertFalse(result["compliant"])

    def test_zero_specification_raises(self):
        with self.assertRaises(ValueError):
            check_acoustic_level(140.0, 0.0)


class TestTestSequence(unittest.TestCase):

    def test_canonical_order_is_compliant(self):
        result = check_test_sequence(CANONICAL_ORDER, required_sequence=list(CANONICAL_ORDER))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_missing_required_test_is_flagged(self):
        seq = ["physical_properties", "modal_survey"]
        required = ["physical_properties", "modal_survey", "random_vibration"]
        result = check_test_sequence(seq, required_sequence=required)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Missing" in f for f in result["findings"]))

    def test_vibration_before_modal_survey_is_flagged(self):
        seq = ["physical_properties", "random_vibration", "modal_survey"]
        required = ["physical_properties", "modal_survey", "random_vibration"]
        result = check_test_sequence(seq, required_sequence=required)
        self.assertFalse(result["compliant"])

    def test_dynamic_before_physical_properties_is_flagged(self):
        seq = ["modal_survey", "physical_properties"]
        required = ["physical_properties", "modal_survey"]
        result = check_test_sequence(seq, required_sequence=required)
        self.assertFalse(result["compliant"])

    def test_acoustic_before_modal_survey_is_flagged(self):
        seq = ["physical_properties", "acoustic", "modal_survey"]
        required = ["physical_properties", "modal_survey", "acoustic"]
        result = check_test_sequence(seq, required_sequence=required)
        self.assertFalse(result["compliant"])

    def test_unknown_type_in_sequence_raises(self):
        with self.assertRaises(ValueError):
            check_test_sequence(["physical_properties", "laser_test"])

    def test_subset_of_canonical_order_no_required_uses_defaults(self):
        # Default required = CANONICAL_ORDER, so a partial sequence is non-compliant
        seq = ["physical_properties", "modal_survey"]
        result = check_test_sequence(seq)
        self.assertFalse(result["compliant"])


class TestCheckTestLevel(unittest.TestCase):

    def test_acceptance_level_with_duration_is_compliant(self):
        result = check_test_level("random_vibration", "acceptance", duration_s=60.0)
        self.assertTrue(result["compliant"])

    def test_qualification_level_is_valid(self):
        result = check_test_level("acoustic", "qualification", duration_s=120.0)
        self.assertTrue(result["compliant"])

    def test_protoflight_level_is_valid(self):
        result = check_test_level("sinusoidal_vibration", "protoflight", duration_s=90.0)
        self.assertTrue(result["compliant"])

    def test_missing_duration_for_timed_test_is_flagged(self):
        result = check_test_level("random_vibration", "acceptance", duration_s=None)
        self.assertFalse(result["compliant"])

    def test_non_timed_test_without_duration_is_compliant(self):
        result = check_test_level("static_load", "qualification")
        self.assertTrue(result["compliant"])

    def test_physical_properties_without_duration_is_compliant(self):
        result = check_test_level("physical_properties", "acceptance")
        self.assertTrue(result["compliant"])

    def test_invalid_level_string_raises(self):
        with self.assertRaises(ValueError):
            check_test_level("random_vibration", "flight")

    def test_invalid_test_type_raises(self):
        with self.assertRaises(ValueError):
            check_test_level("unknown_test", "acceptance")

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            check_test_level("acoustic", "acceptance", duration_s=-5.0)

    def test_all_three_valid_levels_accepted(self):
        for lvl in ("acceptance", "qualification", "protoflight"):
            result = check_test_level("modal_survey", lvl)
            self.assertTrue(result["compliant"], f"Level {lvl!r} should be valid")


if __name__ == "__main__":
    unittest.main()
