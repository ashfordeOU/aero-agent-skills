#!/usr/bin/env python3
"""Gate 3 contract test for e50-commandability-at-all-attitudes-and-rates.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_commandability_at_all_attitudes_and_rates.py
"""

import math
import unittest

from e50_commandability_at_all_attitudes_and_rates_logic import (
    ATTITUDE_AND_RATE,
    ATTITUDE_GAP,
    COMMANDABLE,
    DEFAULT_REQUIRED_MARGIN_DB,
    RATE_LIMITED,
    assess_commandability,
    attitude_coverage_fraction,
    coverage_gaps,
    direction_is_commandable,
    direction_margin_db,
    dwell_time_s,
    max_supported_rate_deg_s,
    rate_is_supported,
    receiver_time_needed_s,
    received_power_dbw,
    solid_angle_weight,
    validate_direction,
    validate_uplink_budget,
)

BUDGET = {
    "eirp_dbw": 70.0,
    "path_loss_db": 180.0,
    "other_losses_db": 2.0,
    "sensitivity_dbw": -115.0,
}


def sample(theta, phi, gain):
    return {"theta_deg": theta, "phi_deg": phi, "gain_dbi": gain}


def sphere(gain_by_theta):
    return [
        sample(theta, phi, gain)
        for theta, gain in gain_by_theta
        for phi in (0.0, 90.0, 180.0, 270.0)
    ]


class TestValidation(unittest.TestCase):
    def test_a_well_formed_sample_is_normalized(self):
        record = validate_direction(sample(30, 45, -2))
        self.assertAlmostEqual(record["theta_deg"], 30.0, places=9)
        self.assertAlmostEqual(record["gain_dbi"], -2.0, places=9)

    def test_a_polar_angle_past_180_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_direction(sample(181.0, 0.0, 0.0))

    def test_an_azimuth_of_360_is_rejected_as_a_duplicate_of_zero(self):
        with self.assertRaises(ValueError):
            validate_direction(sample(30.0, 360.0, 0.0))

    def test_a_missing_gain_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_direction({"theta_deg": 10.0, "phi_deg": 10.0})

    def test_a_negative_path_loss_is_rejected(self):
        broken = dict(BUDGET, path_loss_db=-1.0)
        with self.assertRaises(ValueError):
            validate_uplink_budget(broken)

    def test_a_boolean_eirp_is_rejected(self):
        broken = dict(BUDGET, eirp_dbw=True)
        with self.assertRaises(ValueError):
            validate_uplink_budget(broken)


class TestMargin(unittest.TestCase):
    def test_received_power_sums_the_budget_terms(self):
        self.assertAlmostEqual(received_power_dbw(-3.0, BUDGET), -115.0, places=9)

    def test_margin_is_received_power_over_sensitivity(self):
        self.assertAlmostEqual(
            direction_margin_db(sample(30.0, 0.0, 0.0), BUDGET), 3.0, places=9
        )

    def test_a_margin_landing_on_the_requirement_is_commandable(self):
        self.assertTrue(
            direction_is_commandable(sample(30.0, 0.0, 0.0), BUDGET, 3.0)
        )

    def test_a_margin_under_the_requirement_is_not_commandable(self):
        self.assertFalse(
            direction_is_commandable(sample(30.0, 0.0, -6.0), BUDGET, 3.0)
        )

    def test_the_default_requirement_is_three_decibels(self):
        self.assertAlmostEqual(DEFAULT_REQUIRED_MARGIN_DB, 3.0, places=9)


class TestCoverage(unittest.TestCase):
    def test_a_uniform_sphere_has_no_gap(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0), (135.0, 2.0)])
        self.assertEqual(coverage_gaps(samples, BUDGET), ())

    def test_a_null_direction_is_reported_as_a_gap(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0)]) + [sample(170.0, 10.0, -20.0)]
        gaps = coverage_gaps(samples, BUDGET)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["theta_deg"], 170.0, places=9)

    def test_full_coverage_is_a_fraction_of_one(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0), (135.0, 2.0)])
        self.assertAlmostEqual(
            attitude_coverage_fraction(samples, BUDGET), 1.0, places=9
        )

    def test_coverage_is_weighted_by_solid_angle(self):
        samples = [sample(90.0, 0.0, 2.0), sample(90.0, 180.0, -20.0)]
        self.assertAlmostEqual(
            attitude_coverage_fraction(samples, BUDGET), 0.5, places=9
        )

    def test_a_pole_only_sample_set_cannot_be_weighted(self):
        with self.assertRaises(ValueError):
            attitude_coverage_fraction([sample(0.0, 0.0, 2.0)], BUDGET)

    def test_an_empty_sample_set_is_rejected(self):
        with self.assertRaises(ValueError):
            coverage_gaps([], BUDGET)

    def test_the_equator_carries_the_most_solid_angle(self):
        self.assertAlmostEqual(solid_angle_weight(90.0), 1.0, places=9)
        self.assertAlmostEqual(solid_angle_weight(0.0), 0.0, places=9)


class TestRates(unittest.TestCase):
    def test_dwell_is_the_beam_width_over_the_rate(self):
        self.assertAlmostEqual(dwell_time_s(30.0, 6.0), 10.0, places=9)

    def test_a_stationary_body_never_leaves_the_beam(self):
        self.assertTrue(math.isinf(dwell_time_s(30.0, 0.0)))

    def test_a_negative_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(30.0, -1.0)

    def test_a_zero_beam_width_is_rejected(self):
        with self.assertRaises(ValueError):
            dwell_time_s(0.0, 1.0)

    def test_receiver_time_is_acquisition_plus_one_frame(self):
        self.assertAlmostEqual(receiver_time_needed_s(6.0, 4.0), 10.0, places=9)

    def test_a_dwell_landing_on_the_need_is_supported(self):
        self.assertTrue(rate_is_supported(30.0, 6.0, 6.0, 4.0))

    def test_a_dwell_under_the_need_is_not_supported(self):
        self.assertFalse(rate_is_supported(30.0, 12.0, 6.0, 4.0))

    def test_the_rate_ceiling_inverts_the_dwell_calculation(self):
        self.assertAlmostEqual(max_supported_rate_deg_s(30.0, 6.0, 4.0), 6.0, places=9)


class TestAssessment(unittest.TestCase):
    def test_a_clean_design_is_commandable(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0), (135.0, 2.0)])
        report = assess_commandability(samples, BUDGET, 30.0, 4.0, 6.0, 4.0)
        self.assertEqual(report["verdict"], COMMANDABLE)
        self.assertTrue(report["commandable"])
        self.assertEqual(report["findings"], [])

    def test_a_null_in_the_pattern_is_an_attitude_gap(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0)]) + [sample(160.0, 0.0, -30.0)]
        report = assess_commandability(samples, BUDGET, 30.0, 4.0, 6.0, 4.0)
        self.assertEqual(report["verdict"], ATTITUDE_GAP)

    def test_a_fast_tumble_is_rate_limited(self):
        samples = sphere([(45.0, 2.0), (90.0, 2.0), (135.0, 2.0)])
        report = assess_commandability(samples, BUDGET, 30.0, 20.0, 6.0, 4.0)
        self.assertEqual(report["verdict"], RATE_LIMITED)
        self.assertFalse(report["rate_supported"])

    def test_both_failures_are_reported_together(self):
        samples = sphere([(45.0, 2.0)]) + [sample(160.0, 0.0, -30.0)]
        report = assess_commandability(samples, BUDGET, 30.0, 20.0, 6.0, 4.0)
        self.assertEqual(report["verdict"], ATTITUDE_AND_RATE)
        self.assertEqual(len(report["findings"]), 2)

    def test_the_report_carries_the_rate_ceiling(self):
        samples = sphere([(90.0, 2.0)])
        report = assess_commandability(samples, BUDGET, 30.0, 4.0, 6.0, 4.0)
        self.assertAlmostEqual(report["max_supported_rate_deg_s"], 6.0, places=9)

    def test_a_rate_exactly_at_the_ceiling_is_still_commandable(self):
        samples = sphere([(90.0, 2.0)])
        report = assess_commandability(samples, BUDGET, 30.0, 6.0, 6.0, 4.0)
        self.assertEqual(report["verdict"], COMMANDABLE)


if __name__ == "__main__":
    unittest.main()
