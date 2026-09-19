"""Contract tests for the ECSS-Q-ST-70-01C particulate measurement-method logic."""

import math
import unittest

from q7001_particulate_verification_methods_logic import (
    OBSCURATION_TOLERANCE,
    apply_recovery,
    assess_particulate_measurement,
    counts_per_square_metre,
    fallout_rate_percent_per_hour,
    largest_particle_um,
    method_is_applicable,
    obscuration_percent,
    project_fallout_percent,
    projected_area_um2,
    subtract_blank,
    total_count,
    validate_area,
    validate_bins,
)

BINS = [(5.0, 400), (15.0, 120), (25.0, 40), (50.0, 6), (100.0, 1)]
BLANK = [(5.0, 20), (15.0, 4), (25.0, 0), (50.0, 0), (100.0, 0)]


class ValidateBinsTests(unittest.TestCase):
    def test_returns_float_diameters(self):
        records = validate_bins([(5, 10), (10, 2)])
        self.assertEqual(records, [(5.0, 10), (10.0, 2)])

    def test_zero_count_bin_is_allowed(self):
        self.assertEqual(validate_bins([(5.0, 0), (10.0, 3)])[0][1], 0)

    def test_empty_distribution_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([])

    def test_non_increasing_diameters_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(10.0, 5), (10.0, 2)])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0, -1)])

    def test_fractional_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0, 2.5)])

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0, True)])

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(0.0, 5)])

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_bins([(5.0,)])

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area(0.0)

    def test_non_finite_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area(float("nan"))


class BlankAndRecoveryTests(unittest.TestCase):
    def test_blank_is_removed_bin_by_bin(self):
        corrected = subtract_blank(BINS, BLANK)
        self.assertEqual(corrected[0], (5.0, 380))
        self.assertEqual(corrected[1], (15.0, 116))

    def test_blank_leaves_untouched_bins_alone(self):
        corrected = subtract_blank(BINS, BLANK)
        self.assertEqual(corrected[-1], (100.0, 1))

    def test_blank_larger_than_the_sample_is_a_control_failure(self):
        with self.assertRaises(ValueError):
            subtract_blank([(5.0, 3)], [(5.0, 9)])

    def test_unmatched_blank_bin_rejected(self):
        with self.assertRaises(ValueError):
            subtract_blank([(5.0, 30)], [(7.0, 1)])

    def test_recovery_scales_counts_up(self):
        scaled = apply_recovery([(5.0, 80)], 0.8)
        self.assertAlmostEqual(scaled[0][1], 100.0, places=9)

    def test_full_recovery_is_the_identity(self):
        scaled = apply_recovery([(5.0, 80)], 1.0)
        self.assertAlmostEqual(scaled[0][1], 80.0, places=9)

    def test_zero_recovery_rejected(self):
        with self.assertRaises(ValueError):
            apply_recovery([(5.0, 80)], 0.0)

    def test_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            apply_recovery([(5.0, 80)], 1.2)


class ReductionTests(unittest.TestCase):
    def test_total_count_sums_the_bins(self):
        self.assertAlmostEqual(total_count(BINS), 567.0, places=9)

    def test_counts_per_square_metre_divides_by_the_area(self):
        normalised = counts_per_square_metre([(5.0, 50)], 0.5)
        self.assertAlmostEqual(normalised[0][1], 100.0, places=9)

    def test_projected_area_is_the_circle_sum(self):
        area = projected_area_um2([(10.0, 4)])
        self.assertAlmostEqual(area, 4.0 * math.pi * 25.0, places=9)

    def test_obscuration_of_a_known_distribution(self):
        # One 1000 um particle over 1e-6 m2 covers pi/4 * 1e6 um2 of 1e6 um2.
        value = obscuration_percent([(1000.0, 1)], 1.0e-6)
        self.assertAlmostEqual(value, 100.0 * math.pi / 4.0, places=9)

    def test_obscuration_scales_inversely_with_area(self):
        small = obscuration_percent(BINS, 0.01)
        large = obscuration_percent(BINS, 0.02)
        self.assertAlmostEqual(small, 2.0 * large, places=9)

    def test_largest_particle_ignores_empty_bins(self):
        self.assertAlmostEqual(largest_particle_um([(5.0, 3), (50.0, 0)]), 5.0, places=9)

    def test_largest_particle_on_an_empty_distribution_rejected(self):
        with self.assertRaises(ValueError):
            largest_particle_um([(5.0, 0), (10.0, 0)])

    def test_negative_count_in_projected_area_rejected(self):
        with self.assertRaises(ValueError):
            projected_area_um2([(5.0, -2.0)])


class FalloutTests(unittest.TestCase):
    def test_rate_is_obscuration_over_hours(self):
        self.assertAlmostEqual(fallout_rate_percent_per_hour(0.024, 48.0), 0.0005, places=12)

    def test_projection_is_linear_in_time(self):
        self.assertAlmostEqual(project_fallout_percent(0.0005, 200.0), 0.1, places=12)

    def test_zero_exposure_rejected(self):
        with self.assertRaises(ValueError):
            fallout_rate_percent_per_hour(0.024, 0.0)

    def test_negative_obscuration_rejected(self):
        with self.assertRaises(ValueError):
            fallout_rate_percent_per_hour(-0.01, 10.0)

    def test_negative_projection_span_rejected(self):
        with self.assertRaises(ValueError):
            project_fallout_percent(0.0005, -5.0)


class ApplicabilityTests(unittest.TestCase):
    def test_tape_lift_on_a_robust_surface_is_applicable(self):
        ok, _ = method_is_applicable("tape-lift", {"area_m2": 0.01})
        self.assertTrue(ok)

    def test_tape_lift_on_a_delicate_surface_is_refused(self):
        ok, reason = method_is_applicable(
            "tape-lift", {"area_m2": 0.01, "adhesive_safe": False}
        )
        self.assertFalse(ok)
        self.assertIn("adhesive", reason)

    def test_vacuum_sampling_needs_a_large_enough_area(self):
        ok, reason = method_is_applicable("vacuum-sampling", {"area_m2": 0.02})
        self.assertFalse(ok)
        self.assertIn("minimum", reason)

    def test_closed_out_surface_leaves_only_the_witness_plate(self):
        blocked, _ = method_is_applicable(
            "particle-counting", {"area_m2": 1.0, "accessible": False}
        )
        allowed, _ = method_is_applicable(
            "fallout-plate", {"area_m2": 1.0, "accessible": False}
        )
        self.assertFalse(blocked)
        self.assertTrue(allowed)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            method_is_applicable("wipe-sampling", {"area_m2": 1.0})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "method": "tape-lift",
            "bins": BINS,
            "area_m2": 0.01,
            "recovery_fraction": 0.8,
            "allowed_obscuration_percent": 0.05,
        }
        spec.update(overrides)
        return spec

    def test_compliant_reading_reports_no_finding(self):
        result = assess_particulate_measurement(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_recovery_raises_the_reported_obscuration(self):
        corrected = assess_particulate_measurement(self._spec())
        uncorrected = assess_particulate_measurement(
            self._spec(method="particle-counting", recovery_fraction=None)
        )
        self.assertAlmostEqual(
            corrected["obscuration_percent"],
            uncorrected["obscuration_percent"] / 0.8,
            places=12,
        )

    def test_exceedance_is_flagged(self):
        result = assess_particulate_measurement(
            self._spec(allowed_obscuration_percent=0.0001)
        )
        self.assertFalse(result["compliant"])
        self.assertIn("exceeds", result["findings"][0])

    def test_reading_exactly_at_the_allowed_value_is_compliant(self):
        base = assess_particulate_measurement(self._spec())
        result = assess_particulate_measurement(
            self._spec(allowed_obscuration_percent=base["obscuration_percent"])
        )
        self.assertTrue(result["compliant"])
        self.assertLessEqual(
            abs(result["obscuration_percent"] - result["allowed_obscuration_percent"]),
            OBSCURATION_TOLERANCE * result["allowed_obscuration_percent"],
        )

    def test_lifting_method_without_recovery_is_refused(self):
        spec = self._spec()
        del spec["recovery_fraction"]
        with self.assertRaises(ValueError):
            assess_particulate_measurement(spec)

    def test_recovery_on_a_non_removing_method_is_flagged_not_applied(self):
        result = assess_particulate_measurement(
            self._spec(method="particle-counting", recovery_fraction=0.8)
        )
        self.assertTrue(any("not applied" in item for item in result["findings"]))

    def test_blank_subtraction_lowers_the_obscuration(self):
        plain = assess_particulate_measurement(self._spec())
        blanked = assess_particulate_measurement(self._spec(blank_bins=BLANK))
        self.assertLess(blanked["obscuration_percent"], plain["obscuration_percent"])

    def test_fallout_plate_reports_a_rate(self):
        result = assess_particulate_measurement(
            self._spec(
                method="fallout-plate",
                recovery_fraction=None,
                exposure_hours=48.0,
                allowed_obscuration_percent=1.0,
            )
        )
        self.assertAlmostEqual(
            result["fallout_rate_percent_per_hour"],
            result["obscuration_percent"] / 48.0,
            places=12,
        )

    def test_fallout_plate_projects_over_a_future_exposure(self):
        result = assess_particulate_measurement(
            self._spec(
                method="fallout-plate",
                recovery_fraction=None,
                exposure_hours=48.0,
                projection_hours=480.0,
                allowed_obscuration_percent=1.0,
            )
        )
        self.assertAlmostEqual(
            result["projected_obscuration_percent"],
            10.0 * result["obscuration_percent"],
            places=9,
        )

    def test_fallout_plate_without_exposure_hours_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_measurement(
                self._spec(method="fallout-plate", recovery_fraction=None)
            )

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_measurement(self._spec(method="swab"))

    def test_missing_allowed_value_rejected(self):
        spec = self._spec()
        del spec["allowed_obscuration_percent"]
        with self.assertRaises(ValueError):
            assess_particulate_measurement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_particulate_measurement(["method"])

    def test_counts_are_reported_per_square_metre(self):
        result = assess_particulate_measurement(self._spec(method="particle-counting",
                                                           recovery_fraction=None))
        self.assertAlmostEqual(
            result["counts_per_square_metre"][0][1], 400.0 / 0.01, places=6
        )


if __name__ == "__main__":
    unittest.main()
