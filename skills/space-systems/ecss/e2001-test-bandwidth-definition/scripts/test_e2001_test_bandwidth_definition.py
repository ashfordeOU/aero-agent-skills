#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-01C clause 6.4.1 bandwidth leaf."""

import math
import unittest

from e2001_test_bandwidth_definition_logic import (
    ACTIVITY_PROVISIONS,
    DEFAULT_THRESHOLD_EXPONENT,
    DEFAULT_UPPER_VALIDITY_RATIO,
    activity_provision,
    assess_band_coverage,
    covered_band,
    lower_covered_edge_hz,
    minimum_test_frequency_set,
    required_coverage_band,
    summarize_bandwidth_definition,
    threshold_scaling_factor,
    validate_operating_band,
    verified_margin_db,
)


class TestOperatingBandValidation(unittest.TestCase):
    def test_valid_band_returns_float_pair(self):
        low, high = validate_operating_band(10.7e9, 12.75e9)
        self.assertAlmostEqual(low, 10.7e9)
        self.assertAlmostEqual(high, 12.75e9)

    def test_single_point_band_is_accepted(self):
        low, high = validate_operating_band(4.0e9, 4.0e9)
        self.assertAlmostEqual(low, high)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(12.0e9, 11.0e9)

    def test_zero_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(0.0, 11.0e9)

    def test_negative_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(-1.0e9, 11.0e9)

    def test_non_numeric_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band("10.7e9", 12.0e9)

    def test_boolean_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(True, 12.0e9)

    def test_non_finite_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(float("inf"), 12.0e9)

    def test_nan_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_operating_band(float("nan"), 12.0e9)


class TestActivityProvision(unittest.TestCase):
    def test_qualification_margin_exceeds_acceptance_margin(self):
        qual = activity_provision("qualification")
        acc = activity_provision("acceptance")
        self.assertGreater(qual["required_margin_db"], acc["required_margin_db"])

    def test_activity_lookup_is_case_insensitive(self):
        self.assertEqual(activity_provision("  Acceptance ")["activity"], "acceptance")

    def test_qualification_carries_band_edge_allowance(self):
        self.assertGreater(activity_provision("qualification")["band_edge_allowance"], 0.0)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            activity_provision("screening")

    def test_non_string_activity_rejected(self):
        with self.assertRaises(ValueError):
            activity_provision(3)

    def test_returned_provision_is_a_copy(self):
        provision = activity_provision("qualification")
        provision["required_margin_db"] = 99.0
        self.assertNotAlmostEqual(
            ACTIVITY_PROVISIONS["qualification"]["required_margin_db"], 99.0
        )


class TestThresholdScaling(unittest.TestCase):
    def test_scaling_is_unity_at_the_test_point(self):
        self.assertAlmostEqual(threshold_scaling_factor(4.0e9, 4.0e9), 1.0)

    def test_threshold_grows_above_the_test_frequency(self):
        self.assertAlmostEqual(threshold_scaling_factor(8.0e9, 4.0e9), 4.0)

    def test_threshold_falls_below_the_test_frequency(self):
        self.assertAlmostEqual(threshold_scaling_factor(2.0e9, 4.0e9), 0.25)

    def test_exponent_is_configurable(self):
        self.assertAlmostEqual(
            threshold_scaling_factor(8.0e9, 4.0e9, exponent=1.0), 2.0
        )

    def test_default_exponent_is_the_parallel_plate_value(self):
        self.assertAlmostEqual(DEFAULT_THRESHOLD_EXPONENT, 2.0)

    def test_zero_exponent_rejected(self):
        with self.assertRaises(ValueError):
            threshold_scaling_factor(8.0e9, 4.0e9, exponent=0.0)

    def test_negative_exponent_rejected(self):
        with self.assertRaises(ValueError):
            threshold_scaling_factor(8.0e9, 4.0e9, exponent=-2.0)

    def test_non_numeric_exponent_rejected(self):
        with self.assertRaises(ValueError):
            threshold_scaling_factor(8.0e9, 4.0e9, exponent="two")

    def test_zero_test_frequency_rejected(self):
        with self.assertRaises(ValueError):
            threshold_scaling_factor(8.0e9, 0.0)


class TestVerifiedMargin(unittest.TestCase):
    def test_margin_at_the_test_point_is_the_power_ratio(self):
        self.assertAlmostEqual(
            verified_margin_db(4.0e9, 4.0e9, 400.0, 100.0), 6.0205999132, places=6
        )

    def test_margin_increases_above_the_test_frequency(self):
        low = verified_margin_db(4.0e9, 4.0e9, 400.0, 100.0)
        high = verified_margin_db(5.0e9, 4.0e9, 400.0, 100.0)
        self.assertGreater(high, low)

    def test_margin_decreases_below_the_test_frequency(self):
        below = verified_margin_db(3.0e9, 4.0e9, 400.0, 100.0)
        at = verified_margin_db(4.0e9, 4.0e9, 400.0, 100.0)
        self.assertLess(below, at)

    def test_margin_can_be_negative_far_below_the_test_frequency(self):
        self.assertLess(verified_margin_db(1.0e9, 4.0e9, 400.0, 100.0), 0.0)

    def test_zero_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            verified_margin_db(4.0e9, 4.0e9, 400.0, 0.0)

    def test_negative_test_power_rejected(self):
        with self.assertRaises(ValueError):
            verified_margin_db(4.0e9, 4.0e9, -400.0, 100.0)


class TestLowerCoveredEdge(unittest.TestCase):
    def test_edge_sits_at_the_test_point_when_margins_match(self):
        edge = lower_covered_edge_hz(4.0e9, 400.0, 100.0, 6.0205999132)
        self.assertAlmostEqual(edge / 4.0e9, 1.0, places=6)

    def test_edge_sits_below_the_test_point_when_power_exceeds_the_provision(self):
        edge = lower_covered_edge_hz(4.0e9, 1600.0, 100.0, 6.0)
        self.assertLess(edge, 4.0e9)

    def test_edge_sits_above_the_test_point_when_power_is_short(self):
        edge = lower_covered_edge_hz(4.0e9, 120.0, 100.0, 6.0)
        self.assertGreater(edge, 4.0e9)

    def test_edge_recovers_the_required_margin_exactly(self):
        edge = lower_covered_edge_hz(4.0e9, 800.0, 100.0, 6.0)
        self.assertAlmostEqual(
            verified_margin_db(edge, 4.0e9, 800.0, 100.0), 6.0, places=9
        )

    def test_test_power_below_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            lower_covered_edge_hz(4.0e9, 100.0, 100.0, 6.0)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            lower_covered_edge_hz(4.0e9, 400.0, 100.0, -3.0)

    def test_non_numeric_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            lower_covered_edge_hz(4.0e9, 400.0, 100.0, "6 dB")


class TestCoveredBand(unittest.TestCase):
    def test_band_upper_edge_uses_the_validity_ratio(self):
        band = covered_band(4.0e9, 1600.0, 100.0, 6.0)
        self.assertAlmostEqual(band["upper_hz"], 4.0e9 * DEFAULT_UPPER_VALIDITY_RATIO)

    def test_band_span_is_positive_for_a_healthy_test(self):
        band = covered_band(4.0e9, 1600.0, 100.0, 6.0)
        self.assertGreater(band["span_hz"], 0.0)

    def test_band_includes_the_test_point_for_a_healthy_test(self):
        self.assertTrue(covered_band(4.0e9, 1600.0, 100.0, 6.0)["covers_test_point"])

    def test_span_collapses_to_zero_when_the_provision_is_never_met(self):
        band = covered_band(4.0e9, 110.0, 100.0, 12.0)
        self.assertAlmostEqual(band["span_hz"], 0.0)

    def test_validity_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            covered_band(4.0e9, 1600.0, 100.0, 6.0, upper_validity_ratio=0.9)

    def test_non_numeric_validity_ratio_rejected(self):
        with self.assertRaises(ValueError):
            covered_band(4.0e9, 1600.0, 100.0, 6.0, upper_validity_ratio=None)


class TestRequiredCoverageBand(unittest.TestCase):
    def test_acceptance_band_is_the_declared_band(self):
        low, high = required_coverage_band(10.0e9, 12.0e9, "acceptance")
        self.assertAlmostEqual(low, 10.0e9)
        self.assertAlmostEqual(high, 12.0e9)

    def test_qualification_band_is_widened(self):
        low, high = required_coverage_band(10.0e9, 12.0e9, "qualification")
        self.assertLess(low, 10.0e9)
        self.assertGreater(high, 12.0e9)

    def test_widening_matches_the_declared_allowance(self):
        allowance = ACTIVITY_PROVISIONS["qualification"]["band_edge_allowance"]
        low, _ = required_coverage_band(10.0e9, 12.0e9, "qualification")
        self.assertAlmostEqual(low, 10.0e9 * (1.0 - allowance))

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            required_coverage_band(10.0e9, 12.0e9, "burn-in")


class TestAssessBandCoverage(unittest.TestCase):
    def test_generous_test_point_covers_a_narrow_band(self):
        result = assess_band_coverage(
            3.95e9, 4.05e9, 4.0e9, 4000.0, 100.0, "acceptance"
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_exact_low_edge_is_compliant_despite_representation_error(self):
        p_operating = 100.0
        margin = ACTIVITY_PROVISIONS["acceptance"]["required_margin_db"]
        f_test = 4.0e9
        p_test = 900.0
        edge = lower_covered_edge_hz(f_test, p_test, p_operating, margin)
        result = assess_band_coverage(
            edge, f_test, f_test, p_test, p_operating, "acceptance"
        )
        self.assertTrue(result["compliant"])

    def test_low_edge_shortfall_is_reported(self):
        result = assess_band_coverage(
            1.0e9, 4.05e9, 4.0e9, 400.0, 100.0, "acceptance"
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("low band edge" in f for f in result["findings"]))

    def test_high_edge_shortfall_is_reported(self):
        result = assess_band_coverage(
            3.95e9, 9.0e9, 4.0e9, 4000.0, 100.0, "acceptance"
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("high band edge" in f for f in result["findings"]))

    def test_qualification_is_stricter_than_acceptance_on_the_same_point(self):
        args = (3.90e9, 4.05e9, 4.0e9, 700.0, 100.0)
        acc = assess_band_coverage(*(args + ("acceptance",)))
        qual = assess_band_coverage(*(args + ("qualification",)))
        self.assertGreaterEqual(
            qual["covered"]["lower_hz"], acc["covered"]["lower_hz"]
        )

    def test_empty_band_finding_when_the_margin_is_never_met(self):
        result = assess_band_coverage(
            3.95e9, 4.05e9, 4.0e9, 105.0, 100.0, "qualification"
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("verifies no band" in f for f in result["findings"]))

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            assess_band_coverage(3.95e9, 4.05e9, 4.0e9, 400.0, 100.0, "flight")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_band_coverage(4.05e9, 3.95e9, 4.0e9, 400.0, 100.0, "acceptance")


class TestMinimumTestFrequencySet(unittest.TestCase):
    def test_single_frequency_is_enough_for_a_narrow_band(self):
        points = minimum_test_frequency_set(
            3.95e9, 4.05e9, 4000.0, 100.0, "acceptance"
        )
        self.assertEqual(len(points), 1)

    def test_wide_band_needs_several_frequencies(self):
        points = minimum_test_frequency_set(
            1.0e9, 18.0e9, 400.0, 100.0, "acceptance"
        )
        self.assertGreater(len(points), 1)

    def test_frequencies_are_returned_in_ascending_order(self):
        points = minimum_test_frequency_set(
            1.0e9, 18.0e9, 400.0, 100.0, "acceptance"
        )
        self.assertEqual(points, sorted(points))

    def test_the_set_actually_covers_the_whole_band(self):
        low, high = 1.0e9, 18.0e9
        points = minimum_test_frequency_set(low, high, 400.0, 100.0, "acceptance")
        required_low, required_high = required_coverage_band(low, high, "acceptance")
        margin = ACTIVITY_PROVISIONS["acceptance"]["required_margin_db"]
        edge = required_low
        for f_test in points:
            band = covered_band(f_test, 400.0, 100.0, margin)
            self.assertLessEqual(band["lower_hz"], edge * (1.0 + 1e-9))
            edge = band["upper_hz"]
        self.assertGreaterEqual(edge, required_high * (1.0 - 1e-9))

    def test_qualification_needs_at_least_as_many_points_as_acceptance(self):
        acc = minimum_test_frequency_set(1.0e9, 18.0e9, 400.0, 100.0, "acceptance")
        qual = minimum_test_frequency_set(1.0e9, 18.0e9, 400.0, 100.0, "qualification")
        self.assertGreaterEqual(len(qual), len(acc))

    def test_non_advancing_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_test_frequency_set(
                1.0e9, 18.0e9, 101.0, 100.0, "qualification"
            )

    def test_test_power_below_operating_power_rejected(self):
        with self.assertRaises(ValueError):
            minimum_test_frequency_set(1.0e9, 2.0e9, 50.0, 100.0, "acceptance")


class TestSummary(unittest.TestCase):
    def test_summary_reports_the_covered_verdict(self):
        result = assess_band_coverage(
            3.95e9, 4.05e9, 4.0e9, 4000.0, 100.0, "acceptance"
        )
        lines = summarize_bandwidth_definition(result)
        self.assertTrue(any("verdict: covered" in line for line in lines))

    def test_summary_lists_every_finding(self):
        result = assess_band_coverage(
            1.0e9, 9.0e9, 4.0e9, 400.0, 100.0, "acceptance"
        )
        lines = summarize_bandwidth_definition(result)
        emitted = [line for line in lines if line.startswith("finding: ")]
        self.assertEqual(len(emitted), len(result["findings"]))

    def test_summary_rejects_a_foreign_mapping(self):
        with self.assertRaises(ValueError):
            summarize_bandwidth_definition({"activity": "acceptance"})


class TestDeterminism(unittest.TestCase):
    def test_repeated_assessment_is_bit_identical(self):
        args = (3.95e9, 4.05e9, 4.0e9, 4000.0, 100.0, "acceptance")
        first = assess_band_coverage(*args)
        second = assess_band_coverage(*args)
        self.assertEqual(
            first["covered"]["lower_hz"], second["covered"]["lower_hz"]
        )

    def test_margin_and_edge_are_mutually_consistent(self):
        for f_test in (1.0e9, 4.0e9, 12.0e9):
            edge = lower_covered_edge_hz(f_test, 900.0, 100.0, 6.0)
            self.assertTrue(
                math.isclose(
                    verified_margin_db(edge, f_test, 900.0, 100.0), 6.0, rel_tol=1e-9
                )
            )


if __name__ == "__main__":
    unittest.main()
