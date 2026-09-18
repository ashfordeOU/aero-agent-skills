"""Contract tests for the clause 5.2.5.2.1 undervoltage hysteresis logic."""

import unittest

from e2020_undervoltage_protection_hysteresis_logic import (
    HYSTERESIS_TOLERANCE_V,
    LIMITER_CATEGORIES,
    assess_hysteresis,
    chatter_margin_v,
    disturbance_envelope_v,
    hysteresis_band_v,
    hysteresis_fraction,
    hysteresis_obligation,
    normalise_category,
    required_hysteresis_v,
    validate_voltage,
)

# A 28 V regulated bus with a 21.0 V drop-out point. Ripple, sensing
# uncertainty and load-step droop are chosen so the envelope lands on exactly
# 1.5 V, which lets the bound case be exercised without a float surprise.
BASE = {
    "category": "retriggerable",
    "trip_v": 21.0,
    "rearm_v": 23.0,
    "bus_nominal_v": 28.0,
    "ripple_pk_pk_v": 0.5,
    "sensing_uncertainty_v": 0.25,
    "transient_droop_v": 0.5,
}


def spec(**overrides):
    merged = dict(BASE)
    merged.update(overrides)
    return merged


class CategoryTests(unittest.TestCase):
    def test_canonical_name_passes_through(self):
        self.assertEqual(normalise_category("retriggerable"), "retriggerable")

    def test_alias_and_case_are_folded(self):
        self.assertEqual(normalise_category("  LCL "), "latching")
        self.assertEqual(normalise_category("HPC"), "high-power")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("magnetic-breaker")

    def test_non_string_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category(5)

    def test_empty_category_rejected(self):
        with self.assertRaises(ValueError):
            normalise_category("   ")

    def test_retriggerable_obligation_is_mandatory(self):
        self.assertEqual(hysteresis_obligation("retriggerable"), "mandatory")

    def test_other_categories_are_recommended(self):
        for name in ("latching", "high-power", "foldback"):
            self.assertEqual(hysteresis_obligation(name), "recommended")

    def test_every_known_category_carries_an_obligation(self):
        self.assertEqual(
            set(LIMITER_CATEGORIES.values()), {"mandatory", "recommended"}
        )


class VoltageValidationTests(unittest.TestCase):
    def test_positive_value_returned_as_float(self):
        self.assertEqual(validate_voltage(21, "trip_v"), 21.0)

    def test_zero_rejected_unless_allowed(self):
        with self.assertRaises(ValueError):
            validate_voltage(0.0, "trip_v")
        self.assertEqual(validate_voltage(0.0, "ripple", allow_zero=True), 0.0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(-1.0, "trip_v")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(True, "trip_v")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage(float("inf"), "trip_v")

    def test_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_voltage("21", "trip_v")


class BandTests(unittest.TestCase):
    def test_band_is_the_threshold_difference(self):
        self.assertAlmostEqual(hysteresis_band_v(21.0, 23.0), 2.0, places=9)

    def test_equal_thresholds_give_a_zero_band(self):
        self.assertAlmostEqual(hysteresis_band_v(21.0, 21.0), 0.0, places=9)

    def test_rearm_below_trip_rejected(self):
        with self.assertRaises(ValueError):
            hysteresis_band_v(21.0, 20.0)

    def test_fraction_is_band_over_trip(self):
        self.assertAlmostEqual(hysteresis_fraction(20.0, 21.0), 0.05, places=9)

    def test_fraction_of_a_zero_band_is_zero(self):
        self.assertAlmostEqual(hysteresis_fraction(20.0, 20.0), 0.0, places=9)


class EnvelopeTests(unittest.TestCase):
    def test_sensing_uncertainty_is_counted_at_both_thresholds(self):
        self.assertAlmostEqual(
            disturbance_envelope_v(0.5, 0.25, 0.5), 1.5, places=9
        )

    def test_envelope_of_a_quiet_bus_is_zero(self):
        self.assertAlmostEqual(disturbance_envelope_v(0.0, 0.0, 0.0), 0.0, places=9)

    def test_negative_ripple_rejected(self):
        with self.assertRaises(ValueError):
            disturbance_envelope_v(-0.1, 0.25, 0.5)

    def test_margin_factor_scales_the_requirement(self):
        self.assertAlmostEqual(required_hysteresis_v(1.5, 2.0), 3.0, places=9)

    def test_unity_margin_factor_is_the_envelope(self):
        self.assertAlmostEqual(required_hysteresis_v(1.5), 1.5, places=9)

    def test_margin_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_hysteresis_v(1.5, 0.8)

    def test_chatter_margin_is_band_minus_requirement(self):
        self.assertAlmostEqual(chatter_margin_v(2.0, 1.5), 0.5, places=9)


class AssessmentTests(unittest.TestCase):
    def test_sufficient_band_on_a_retriggerable_limiter_is_compliant(self):
        result = assess_hysteresis(spec())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["hysteresis_present"])

    def test_band_exactly_on_the_envelope_is_accepted(self):
        result = assess_hysteresis(spec(rearm_v=22.5))
        self.assertAlmostEqual(result["chatter_margin_v"], 0.0, places=9)
        self.assertTrue(result["hysteresis_sufficient"])
        self.assertEqual(result["verdict"], "compliant")

    def test_short_band_on_a_retriggerable_limiter_fails(self):
        result = assess_hysteresis(spec(rearm_v=21.5))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertAlmostEqual(result["chatter_margin_v"], -1.0, places=9)

    def test_same_short_band_on_a_latching_limiter_is_advisory(self):
        result = assess_hysteresis(spec(category="latching", rearm_v=21.5))
        self.assertEqual(result["verdict"], "advisory")
        self.assertEqual(len(result["findings"]), 1)

    def test_absent_band_on_a_retriggerable_limiter_fails(self):
        result = assess_hysteresis(spec(rearm_v=21.0))
        self.assertFalse(result["hysteresis_present"])
        self.assertEqual(result["verdict"], "non-compliant")

    def test_absent_band_on_a_high_power_limiter_is_advisory(self):
        result = assess_hysteresis(spec(category="high-power", rearm_v=21.0))
        self.assertEqual(result["verdict"], "advisory")

    def test_trip_point_at_the_nominal_bus_fails_every_category(self):
        result = assess_hysteresis(
            spec(category="latching", trip_v=28.0, rearm_v=30.0, bus_nominal_v=28.0)
        )
        self.assertEqual(result["verdict"], "non-compliant")

    def test_rearm_above_nominal_is_reported_as_unreachable(self):
        result = assess_hysteresis(spec(category="latching", rearm_v=29.0))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertTrue(any("never be reached" in f for f in result["findings"]))

    def test_margin_factor_can_turn_a_pass_into_a_shortfall(self):
        self.assertEqual(assess_hysteresis(spec())["verdict"], "compliant")
        tightened = assess_hysteresis(spec(margin_factor=2.0))
        self.assertEqual(tightened["verdict"], "non-compliant")

    def test_band_fraction_is_reported(self):
        result = assess_hysteresis(spec(trip_v=20.0, rearm_v=21.0))
        self.assertAlmostEqual(result["band_fraction"], 0.05, places=9)

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["bus_nominal_v"]
        with self.assertRaises(ValueError):
            assess_hysteresis(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_hysteresis(["retriggerable", 21.0])

    def test_obligation_is_echoed_with_the_verdict(self):
        self.assertEqual(assess_hysteresis(spec())["obligation"], "mandatory")
        self.assertEqual(
            assess_hysteresis(spec(category="foldback"))["obligation"], "recommended"
        )

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(HYSTERESIS_TOLERANCE_V, 1e-6)


if __name__ == "__main__":
    unittest.main()
