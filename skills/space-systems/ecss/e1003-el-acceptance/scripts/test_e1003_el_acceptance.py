"""
Acceptance test contract for e1003_el_acceptance_logic.
stdlib unittest only — deterministic, offline, no network.
Run: python3 test_e1003_el_acceptance.py
"""
import math
import sys
import os
import unittest

# Allow import when run directly from the scripts/ directory or from repo root.
sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_acceptance_logic import (
    THERMAL_ACCEPTANCE_MARGIN_C,
    VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR,
    VIB_SINE_ACCEPTANCE_G_FACTOR,
    EMC,
    FUNCTIONAL,
    THERMAL_CYCLING,
    THERMAL_VACUUM,
    VIB_RANDOM,
    VIB_SINE,
    VISUAL,
    TestPlanEntry,
    check_test_baseline,
    check_test_duration,
    derive_thermal_acceptance_range,
    derive_vibration_random_acceptance_grms,
    derive_vibration_sine_acceptance_g,
    validate_acceptance_plan,
)


class TestVibrationRandomAcceptanceLevel(unittest.TestCase):

    def test_factor_is_minus_3db_in_psd(self):
        expected = math.sqrt(10.0 ** (-3.0 / 10.0))
        self.assertAlmostEqual(VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR, expected, places=10)

    def test_acceptance_grms_below_qualification(self):
        qual = 10.0
        acc = derive_vibration_random_acceptance_grms(qual)
        self.assertLess(acc, qual)
        self.assertAlmostEqual(acc, qual * VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR, places=10)

    def test_acceptance_grms_at_unity_qual(self):
        acc = derive_vibration_random_acceptance_grms(1.0)
        self.assertAlmostEqual(acc, VIB_RANDOM_ACCEPTANCE_GRMS_FACTOR, places=10)

    def test_negative_qual_grms_raises(self):
        with self.assertRaises(ValueError):
            derive_vibration_random_acceptance_grms(-1.0)

    def test_zero_qual_grms_raises(self):
        with self.assertRaises(ValueError):
            derive_vibration_random_acceptance_grms(0.0)


class TestVibrationSineAcceptanceLevel(unittest.TestCase):

    def test_factor_is_minus_3db_in_amplitude(self):
        expected = 10.0 ** (-3.0 / 20.0)
        self.assertAlmostEqual(VIB_SINE_ACCEPTANCE_G_FACTOR, expected, places=10)

    def test_acceptance_g_below_qualification(self):
        qual = 20.0
        acc = derive_vibration_sine_acceptance_g(qual)
        self.assertLess(acc, qual)
        self.assertAlmostEqual(acc, qual * VIB_SINE_ACCEPTANCE_G_FACTOR, places=10)

    def test_negative_qual_g_raises(self):
        with self.assertRaises(ValueError):
            derive_vibration_sine_acceptance_g(-5.0)


class TestThermalAcceptanceRange(unittest.TestCase):

    def test_nominal_range_narrowed_correctly(self):
        acc_high, acc_low = derive_thermal_acceptance_range(80.0, -30.0)
        self.assertAlmostEqual(acc_high, 80.0 - THERMAL_ACCEPTANCE_MARGIN_C)
        self.assertAlmostEqual(acc_low, -30.0 + THERMAL_ACCEPTANCE_MARGIN_C)

    def test_acceptance_range_is_narrower_than_qualification(self):
        acc_high, acc_low = derive_thermal_acceptance_range(100.0, -50.0)
        self.assertGreater(100.0 - (-50.0), acc_high - acc_low)

    def test_inverted_qualification_range_raises(self):
        with self.assertRaises(ValueError):
            derive_thermal_acceptance_range(-10.0, 20.0)

    def test_equal_high_low_raises(self):
        with self.assertRaises(ValueError):
            derive_thermal_acceptance_range(50.0, 50.0)

    def test_too_narrow_range_raises(self):
        # Range of 8 °C cannot accommodate 5 °C margin at each side (would need 10 °C).
        with self.assertRaises(ValueError):
            derive_thermal_acceptance_range(4.0, -4.0)


class TestCheckTestDuration(unittest.TestCase):

    def test_duration_meets_minimum_passes(self):
        result = check_test_duration(FUNCTIONAL, 30.0)
        self.assertTrue(result.passes)
        self.assertEqual(result.shortfall_min, 0.0)

    def test_duration_exceeds_minimum_passes(self):
        result = check_test_duration(THERMAL_VACUUM, 2000.0)
        self.assertTrue(result.passes)
        self.assertEqual(result.shortfall_min, 0.0)

    def test_duration_below_minimum_fails(self):
        result = check_test_duration(THERMAL_CYCLING, 60.0)  # min is 480
        self.assertFalse(result.passes)
        self.assertAlmostEqual(result.shortfall_min, 420.0)

    def test_duration_at_minimum_boundary_passes(self):
        result = check_test_duration(VISUAL, 15.0)
        self.assertTrue(result.passes)

    def test_unknown_test_type_raises(self):
        with self.assertRaises(ValueError):
            check_test_duration("shock", 10.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            check_test_duration(FUNCTIONAL, -1.0)


class TestCheckTestBaseline(unittest.TestCase):

    def test_simple_category_complete(self):
        result = check_test_baseline("simple", {VISUAL, FUNCTIONAL})
        self.assertTrue(result.baseline_complete)
        self.assertEqual(result.missing_tests, frozenset())

    def test_simple_category_missing_functional(self):
        result = check_test_baseline("simple", {VISUAL})
        self.assertFalse(result.baseline_complete)
        self.assertIn(FUNCTIONAL, result.missing_tests)

    def test_standard_category_complete(self):
        result = check_test_baseline(
            "standard", {VISUAL, FUNCTIONAL, VIB_RANDOM, THERMAL_CYCLING}
        )
        self.assertTrue(result.baseline_complete)

    def test_standard_category_missing_vibration(self):
        result = check_test_baseline("standard", {VISUAL, FUNCTIONAL, THERMAL_CYCLING})
        self.assertFalse(result.baseline_complete)
        self.assertIn(VIB_RANDOM, result.missing_tests)

    def test_critical_category_complete(self):
        result = check_test_baseline(
            "critical",
            {VISUAL, FUNCTIONAL, VIB_SINE, VIB_RANDOM, THERMAL_CYCLING, THERMAL_VACUUM, EMC},
        )
        self.assertTrue(result.baseline_complete)
        self.assertEqual(result.missing_tests, frozenset())

    def test_critical_category_missing_emc(self):
        result = check_test_baseline(
            "critical",
            {VISUAL, FUNCTIONAL, VIB_SINE, VIB_RANDOM, THERMAL_CYCLING, THERMAL_VACUUM},
        )
        self.assertFalse(result.baseline_complete)
        self.assertIn(EMC, result.missing_tests)

    def test_extra_tests_do_not_compensate_for_missing(self):
        # EMC is extra for standard; still missing VIB_RANDOM.
        result = check_test_baseline("standard", {VISUAL, FUNCTIONAL, THERMAL_CYCLING, EMC})
        self.assertFalse(result.baseline_complete)
        self.assertIn(VIB_RANDOM, result.missing_tests)
        self.assertIn(EMC, result.extra_tests)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            check_test_baseline("heritage", {VISUAL, FUNCTIONAL})

    def test_unknown_test_type_in_proposed_set_raises(self):
        with self.assertRaises(ValueError):
            check_test_baseline("simple", {VISUAL, FUNCTIONAL, "acoustic"})


class TestValidateAcceptancePlan(unittest.TestCase):

    def _make_standard_passing_plan(self):
        return [
            TestPlanEntry(VISUAL, 20.0),
            TestPlanEntry(FUNCTIONAL, 45.0),
            TestPlanEntry(VIB_RANDOM, 3.0),
            TestPlanEntry(THERMAL_CYCLING, 500.0),
        ]

    def test_plan_accepted_when_complete_and_durations_pass(self):
        result = validate_acceptance_plan("standard", self._make_standard_passing_plan())
        self.assertTrue(result.plan_accepted)
        self.assertTrue(result.baseline_complete)
        self.assertTrue(result.all_durations_pass)
        self.assertEqual(result.missing_tests, frozenset())
        self.assertEqual(result.duration_failures, [])

    def test_plan_rejected_when_mandatory_test_missing(self):
        entries = [
            TestPlanEntry(VISUAL, 20.0),
            TestPlanEntry(FUNCTIONAL, 45.0),
            TestPlanEntry(THERMAL_CYCLING, 500.0),
            # VIB_RANDOM omitted
        ]
        result = validate_acceptance_plan("standard", entries)
        self.assertFalse(result.plan_accepted)
        self.assertFalse(result.baseline_complete)
        self.assertIn(VIB_RANDOM, result.missing_tests)

    def test_plan_rejected_when_duration_too_short(self):
        entries = [
            TestPlanEntry(VISUAL, 20.0),
            TestPlanEntry(FUNCTIONAL, 45.0),
            TestPlanEntry(VIB_RANDOM, 1.0),   # min is 2.0
            TestPlanEntry(THERMAL_CYCLING, 500.0),
        ]
        result = validate_acceptance_plan("standard", entries)
        self.assertFalse(result.plan_accepted)
        self.assertFalse(result.all_durations_pass)
        self.assertEqual(len(result.duration_failures), 1)
        self.assertEqual(result.duration_failures[0].test_type, VIB_RANDOM)
        self.assertAlmostEqual(result.duration_failures[0].shortfall_min, 1.0)

    def test_simple_plan_accepted(self):
        entries = [
            TestPlanEntry(VISUAL, 15.0),
            TestPlanEntry(FUNCTIONAL, 30.0),
        ]
        result = validate_acceptance_plan("simple", entries)
        self.assertTrue(result.plan_accepted)

    def test_critical_plan_accepted(self):
        entries = [
            TestPlanEntry(VISUAL, 15.0),
            TestPlanEntry(FUNCTIONAL, 30.0),
            TestPlanEntry(VIB_SINE, 5.0),
            TestPlanEntry(VIB_RANDOM, 2.0),
            TestPlanEntry(THERMAL_CYCLING, 480.0),
            TestPlanEntry(THERMAL_VACUUM, 1440.0),
            TestPlanEntry(EMC, 60.0),
        ]
        result = validate_acceptance_plan("critical", entries)
        self.assertTrue(result.plan_accepted)

    def test_test_plan_entry_rejects_invalid_type(self):
        with self.assertRaises(ValueError):
            TestPlanEntry("acoustic_noise", 60.0)

    def test_test_plan_entry_rejects_negative_duration(self):
        with self.assertRaises(ValueError):
            TestPlanEntry(FUNCTIONAL, -5.0)


if __name__ == "__main__":
    unittest.main()
