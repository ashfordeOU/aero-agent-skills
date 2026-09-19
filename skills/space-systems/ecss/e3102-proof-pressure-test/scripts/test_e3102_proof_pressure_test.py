"""Contract test for the proof-pressure-test leaf (stdlib unittest)."""

import unittest

from e3102_proof_pressure_test_logic import (
    DEFAULT_MINIMUM_HOLD_S,
    DEFAULT_PERMANENT_SET_ALLOWANCE,
    MIN_PROOF_FACTOR,
    PRESSURE_TOLERANCE,
    assess_applied_pressure,
    assess_hold_duration,
    assess_leakage,
    assess_permanent_set,
    assess_proof_pressure_test,
    corrected_proof_pressure_pa,
    permanent_set_fraction,
    require_non_negative,
    require_positive,
    require_real,
    required_proof_pressure_pa,
    temperature_correction_factor,
    validate_proof_factor,
)

MDP = 2.0e6
FACTOR = 1.5


def good_spec(**overrides):
    spec = {
        "mdp_pa": MDP,
        "proof_factor": FACTOR,
        "applied_pa": 3.1e6,
        "applied_hold_s": 600.0,
        "gauge_before": 1.000,
        "gauge_after": 1.0005,
        "leak_detected": False,
        "yield_pressure_pa": 4.0e6,
    }
    spec.update(overrides)
    return spec


class TestValidators(unittest.TestCase):
    def test_require_real_rejects_boolean(self):
        with self.assertRaises(ValueError):
            require_real("x", False)

    def test_require_real_rejects_nan(self):
        with self.assertRaises(ValueError):
            require_real("x", float("nan"))

    def test_require_positive_rejects_zero(self):
        with self.assertRaises(ValueError):
            require_positive("x", 0.0)

    def test_require_non_negative_accepts_zero(self):
        self.assertAlmostEqual(require_non_negative("x", 0.0), 0.0, places=9)

    def test_require_non_negative_rejects_negative(self):
        with self.assertRaises(ValueError):
            require_non_negative("x", -1.0)


class TestProofFactor(unittest.TestCase):
    def test_factor_above_unity_is_accepted(self):
        self.assertAlmostEqual(validate_proof_factor(1.5), 1.5, places=9)

    def test_factor_of_exactly_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_proof_factor(MIN_PROOF_FACTOR)

    def test_factor_below_unity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_proof_factor(0.9)

    def test_proof_pressure_is_mdp_times_factor(self):
        self.assertAlmostEqual(required_proof_pressure_pa(MDP, FACTOR), 3.0e6, places=9)

    def test_non_positive_mdp_raises(self):
        with self.assertRaises(ValueError):
            required_proof_pressure_pa(0.0, FACTOR)


class TestTemperatureCorrection(unittest.TestCase):
    def test_equal_allowables_give_unity(self):
        self.assertAlmostEqual(temperature_correction_factor(300.0e6, 300.0e6),
                               1.0, places=9)

    def test_stronger_at_test_temperature_raises_the_test_pressure(self):
        factor = temperature_correction_factor(360.0e6, 300.0e6)
        self.assertAlmostEqual(factor, 1.2, places=9)

    def test_weaker_at_test_temperature_lowers_the_test_pressure(self):
        self.assertAlmostEqual(
            temperature_correction_factor(240.0e6, 300.0e6), 0.8, places=9
        )

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            temperature_correction_factor(0.0, 300.0e6)

    def test_corrected_pressure_applies_the_ratio(self):
        value = corrected_proof_pressure_pa(MDP, FACTOR, 360.0e6, 300.0e6)
        self.assertAlmostEqual(value, 3.6e6, places=9)

    def test_uncorrected_pressure_when_no_allowables_given(self):
        self.assertAlmostEqual(corrected_proof_pressure_pa(MDP, FACTOR), 3.0e6, places=9)

    def test_one_allowable_alone_raises(self):
        with self.assertRaises(ValueError):
            corrected_proof_pressure_pa(MDP, FACTOR, 360.0e6, None)


class TestAppliedPressure(unittest.TestCase):
    def test_pressure_exactly_at_the_target_is_compliant(self):
        result = assess_applied_pressure(3.0e6, 3.0e6)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["overshoot_pa"], 0.0, places=9)

    def test_pressure_short_of_the_target_fails(self):
        result = assess_applied_pressure(2.9e6, 3.0e6)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["reached_target"])

    def test_pressure_above_yield_fails_even_though_the_target_was_met(self):
        result = assess_applied_pressure(4.5e6, 3.0e6, 4.0e6)
        self.assertTrue(result["reached_target"])
        self.assertFalse(result["below_yield"])
        self.assertFalse(result["compliant"])

    def test_pressure_exactly_at_yield_is_still_accepted(self):
        result = assess_applied_pressure(4.0e6, 3.0e6, 4.0e6)
        self.assertTrue(result["compliant"])

    def test_yield_below_the_target_is_an_unproofable_article(self):
        with self.assertRaises(ValueError):
            assess_applied_pressure(3.0e6, 3.0e6, 2.5e6)

    def test_negative_applied_pressure_raises(self):
        with self.assertRaises(ValueError):
            assess_applied_pressure(-1.0, 3.0e6)


class TestHoldDuration(unittest.TestCase):
    def test_hold_longer_than_the_minimum_passes(self):
        result = assess_hold_duration(600.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["minimum_hold_s"], DEFAULT_MINIMUM_HOLD_S, places=9)

    def test_hold_exactly_at_the_minimum_passes(self):
        result = assess_hold_duration(DEFAULT_MINIMUM_HOLD_S)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_s"], 0.0, places=9)

    def test_short_hold_fails(self):
        self.assertFalse(assess_hold_duration(120.0)["compliant"])

    def test_negative_hold_raises(self):
        with self.assertRaises(ValueError):
            assess_hold_duration(-1.0)

    def test_custom_minimum_hold_is_honoured(self):
        self.assertFalse(assess_hold_duration(400.0, minimum_hold_s=900.0)["compliant"])


class TestPermanentSet(unittest.TestCase):
    def test_fraction_is_relative_to_the_original_gauge(self):
        self.assertAlmostEqual(permanent_set_fraction(1.0, 1.001), 0.001, places=9)

    def test_no_change_is_zero_set(self):
        result = assess_permanent_set(1.0, 1.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["permanent_set_fraction"], 0.0, places=9)

    def test_set_exactly_at_the_allowance_is_accepted(self):
        result = assess_permanent_set(1.0, 1.0 + DEFAULT_PERMANENT_SET_ALLOWANCE)
        self.assertTrue(result["compliant"])

    def test_set_above_the_allowance_fails(self):
        result = assess_permanent_set(1.0, 1.01)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_shrunken_gauge_is_a_measurement_finding(self):
        result = assess_permanent_set(1.0, 0.999)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("shrank" in f for f in result["findings"]))

    def test_zero_gauge_raises(self):
        with self.assertRaises(ValueError):
            assess_permanent_set(0.0, 1.0)


class TestLeakage(unittest.TestCase):
    def test_no_leak_is_compliant(self):
        self.assertTrue(assess_leakage(False)["compliant"])

    def test_leak_rejects_the_article(self):
        result = assess_leakage(True)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"])

    def test_non_boolean_observation_raises(self):
        with self.assertRaises(ValueError):
            assess_leakage("no")


class TestWholeTest(unittest.TestCase):
    def test_good_test_is_compliant(self):
        report = assess_proof_pressure_test(good_spec())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertAlmostEqual(report["target_pressure_pa"], 3.0e6, places=9)

    def test_temperature_correction_moves_the_target(self):
        report = assess_proof_pressure_test(good_spec(
            allowable_at_test_pa=360.0e6, allowable_at_design_pa=300.0e6,
            applied_pa=3.7e6, yield_pressure_pa=4.5e6,
        ))
        self.assertAlmostEqual(report["target_pressure_pa"], 3.6e6, places=9)
        self.assertTrue(report["compliant"])

    def test_leak_names_the_failed_check(self):
        report = assess_proof_pressure_test(good_spec(leak_detected=True))
        self.assertFalse(report["compliant"])
        self.assertIn("leakage", report["failed_checks"])

    def test_short_hold_names_the_failed_check(self):
        report = assess_proof_pressure_test(good_spec(applied_hold_s=10.0))
        self.assertIn("hold", report["failed_checks"])

    def test_missing_key_raises(self):
        spec = good_spec()
        del spec["applied_pa"]
        with self.assertRaises(ValueError):
            assess_proof_pressure_test(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_proof_pressure_test([MDP, FACTOR])

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertLess(PRESSURE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
