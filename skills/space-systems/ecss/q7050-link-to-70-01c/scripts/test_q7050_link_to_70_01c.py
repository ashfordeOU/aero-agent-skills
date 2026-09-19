"""Contract tests for the monitoring-to-cleanliness-verification handover logic."""

import math
import unittest

from q7050_link_to_70_01c_logic import (
    COVERAGE_TOLERANCE_PERCENT,
    assess_monitoring_handover,
    bin_obscured_area_m2,
    coarsest_bin_um,
    fallout_rates,
    level_for_coverage,
    percentage_area_coverage,
    project_bins,
    projection_factor,
    validate_bins,
    validate_positive,
)

# Representative witness-plate read: a fine population with a small coarse tail.
BINS = [(5.0, 400.0), (15.0, 60.0), (50.0, 4.0)]

LEVELS = [
    (0.01, "A"),
    (0.10, "B"),
    (1.00, "C"),
]


class ValidationTests(unittest.TestCase):
    def test_positive_value_returns_float(self):
        self.assertEqual(validate_positive(3, "x"), 3.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "collecting_area_m2")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "monitored_days")

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"), "exposure_days")

    def test_bins_are_sorted_by_diameter(self):
        cleaned = validate_bins([(50.0, 4.0), (5.0, 400.0)])
        self.assertAlmostEqual(cleaned[0][0], 5.0)
        self.assertAlmostEqual(cleaned[-1][0], 50.0)

    def test_empty_bin_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0, -1.0)])

    def test_zero_count_bin_is_allowed(self):
        self.assertEqual(validate_bins([(5.0, 0.0)]), [(5.0, 0.0)])

    def test_duplicate_diameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0, 10.0), (5.0, 20.0)])

    def test_malformed_bin_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0,)])


class FalloutRateTests(unittest.TestCase):
    def test_rate_is_counts_per_area_per_day(self):
        rates = fallout_rates([(5.0, 400.0)], 0.01, 4.0)
        self.assertAlmostEqual(rates[0][1], 10000.0)

    def test_rate_keeps_one_entry_per_bin(self):
        self.assertEqual(len(fallout_rates(BINS, 0.01, 2.0)), 3)

    def test_zero_monitored_days_rejected(self):
        with self.assertRaises(ValueError):
            fallout_rates(BINS, 0.01, 0.0)

    def test_projection_factor_is_the_period_ratio(self):
        self.assertAlmostEqual(projection_factor(30.0, 3.0), 10.0)


class ObscurationTests(unittest.TestCase):
    def test_single_particle_area_is_the_disc_area(self):
        area = bin_obscured_area_m2(10.0, 1.0)
        self.assertAlmostEqual(area, math.pi * 25.0 * 1e-12, places=18)

    def test_area_is_quadratic_in_diameter(self):
        small = bin_obscured_area_m2(5.0, 1.0)
        large = bin_obscured_area_m2(50.0, 1.0)
        self.assertAlmostEqual(large / small, 100.0, places=9)

    def test_zero_count_bin_obscures_nothing(self):
        self.assertAlmostEqual(bin_obscured_area_m2(50.0, 0.0), 0.0)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            bin_obscured_area_m2(50.0, -2.0)

    def test_coverage_sums_every_bin(self):
        one_bin = percentage_area_coverage([(50.0, 4.0)], 1.0)
        all_bins = percentage_area_coverage(BINS, 1.0)
        self.assertGreater(all_bins, one_bin)

    def test_coverage_scales_inversely_with_area(self):
        small = percentage_area_coverage(BINS, 1.0)
        large = percentage_area_coverage(BINS, 2.0)
        self.assertAlmostEqual(small / large, 2.0, places=9)

    def test_coarsest_bin_is_reported(self):
        self.assertAlmostEqual(coarsest_bin_um(BINS), 50.0)


class ProjectionTests(unittest.TestCase):
    def test_projection_scales_with_exposure(self):
        rates = [(5.0, 100.0)]
        short = project_bins(rates, 2.0, 1.0, 1.0)
        long_run = project_bins(rates, 2.0, 5.0, 1.0)
        self.assertAlmostEqual(long_run[0][1] / short[0][1], 5.0, places=9)

    def test_projection_at_the_allowed_horizon_is_accepted(self):
        projected = project_bins([(5.0, 100.0)], 1.0, 10.0, 1.0, 10.0)
        self.assertAlmostEqual(projection_factor(10.0, 1.0), 10.0, places=9)
        self.assertAlmostEqual(projected[0][1], 1000.0, places=9)

    def test_projection_past_the_horizon_is_refused(self):
        with self.assertRaises(ValueError):
            project_bins([(5.0, 100.0)], 1.0, 400.0, 1.0, 10.0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            project_bins([(5.0, -1.0)], 1.0, 2.0, 1.0)

    def test_empty_rate_set_rejected(self):
        with self.assertRaises(ValueError):
            project_bins([], 1.0, 2.0, 1.0)


class LevelTableTests(unittest.TestCase):
    def test_coverage_inside_the_tightest_level(self):
        self.assertEqual(level_for_coverage(0.004, LEVELS), "A")

    def test_coverage_falls_into_the_next_level(self):
        self.assertEqual(level_for_coverage(0.05, LEVELS), "B")

    def test_boundary_coverage_meets_the_level(self):
        self.assertEqual(level_for_coverage(0.01, LEVELS), "A")

    def test_coverage_above_every_level_returns_none(self):
        self.assertIsNone(level_for_coverage(5.0, LEVELS))

    def test_empty_level_table_rejected(self):
        with self.assertRaises(ValueError):
            level_for_coverage(0.01, [])

    def test_unnamed_level_rejected(self):
        with self.assertRaises(ValueError):
            level_for_coverage(0.01, [(0.01, "")])


class HandoverTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "bins": BINS,
            "collecting_area_m2": 0.01,
            "monitored_days": 10.0,
            "exposed_area_m2": 2.0,
            "exposure_days": 30.0,
            "level_table": LEVELS,
            "declared_level": "C",
            "requirement_reference_um": 5.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_run_is_verified(self):
        result = assess_monitoring_handover(self._spec())
        self.assertTrue(result["verified"])
        self.assertEqual(result["findings"], [])

    def test_projection_factor_is_reported(self):
        result = assess_monitoring_handover(self._spec())
        self.assertAlmostEqual(result["projection_factor"], 3.0, places=9)

    def test_coverage_is_the_projected_not_the_monitored_figure(self):
        monitored = percentage_area_coverage(BINS, 0.01)
        result = assess_monitoring_handover(self._spec())
        self.assertNotAlmostEqual(result["coverage_percent"], monitored, places=6)

    def test_tight_declared_level_is_flagged(self):
        dirty = [(5.0, 400000.0), (15.0, 60000.0), (50.0, 4000.0)]
        result = assess_monitoring_handover(self._spec(bins=dirty, declared_level="A"))
        self.assertFalse(result["meets_declared_level"])
        self.assertFalse(result["verified"])
        self.assertEqual(len(result["findings"]), 1)

    def test_coarse_requirement_reference_marks_a_lower_bound(self):
        result = assess_monitoring_handover(self._spec(requirement_reference_um=100.0))
        self.assertTrue(result["lower_bound"])
        self.assertFalse(result["verified"])

    def test_boundary_coverage_is_absorbed_by_the_tolerance(self):
        ceiling = assess_monitoring_handover(self._spec())["coverage_percent"]
        tuned = self._spec(level_table=[(ceiling, "EXACT")], declared_level="EXACT")
        result = assess_monitoring_handover(tuned)
        self.assertTrue(result["meets_declared_level"])
        self.assertAlmostEqual(
            result["coverage_percent"] - result["declared_ceiling_percent"], 0.0, places=9
        )
        self.assertAlmostEqual(COVERAGE_TOLERANCE_PERCENT, 1e-9, places=12)

    def test_unknown_declared_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring_handover(self._spec(declared_level="Z"))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["exposure_days"]
        with self.assertRaises(ValueError):
            assess_monitoring_handover(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring_handover(["bins"])

    def test_over_horizon_exposure_refused_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_monitoring_handover(self._spec(exposure_days=5000.0))

    def test_longer_exposure_raises_the_coverage(self):
        short = assess_monitoring_handover(self._spec(exposure_days=20.0))
        long_run = assess_monitoring_handover(self._spec(exposure_days=40.0))
        self.assertAlmostEqual(
            long_run["coverage_percent"] / short["coverage_percent"], 2.0, places=9
        )


if __name__ == "__main__":
    unittest.main()
