"""Contract tests for the witness-plate surface deposition monitoring logic."""

import unittest

from q7050_surface_deposition_monitoring_logic import (
    COVERAGE_TOLERANCE_REL,
    MIN_EXPOSURE_HOURS,
    MIN_PLATE_AREA_CM2,
    assess_fallout,
    categorize_coverage,
    deposition_rate_per_hour,
    net_coverage,
    obscured_area_um2,
    particle_area_um2,
    percent_area_coverage,
    project_coverage,
    validate_bands,
    validate_exposure_hours,
    validate_orientation,
    validate_plate_area_cm2,
)


class ValidationTests(unittest.TestCase):
    def test_plate_area_is_returned_as_a_float(self):
        self.assertAlmostEqual(validate_plate_area_cm2(100), 100.0, places=12)

    def test_zero_plate_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_plate_area_cm2(0.0)

    def test_boolean_plate_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_plate_area_cm2(True)

    def test_zero_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_hours(0.0)

    def test_orientation_is_normalised(self):
        self.assertEqual(validate_orientation(" Upward "), "upward")

    def test_unknown_orientation_rejected(self):
        with self.assertRaises(ValueError):
            validate_orientation("sideways")

    def test_bands_are_returned_as_floats(self):
        self.assertEqual(validate_bands([(5, 3)]), [(5.0, 3.0)])

    def test_unordered_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(15.0, 3.0), (5.0, 2.0)])

    def test_duplicate_band_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(5.0, 3.0), (5.0, 2.0)])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(5.0, -1.0)])

    def test_zero_count_is_a_real_band(self):
        self.assertEqual(validate_bands([(5.0, 0.0)]), [(5.0, 0.0)])

    def test_empty_band_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([])


class GeometryTests(unittest.TestCase):
    def test_particle_area_is_the_projected_disc(self):
        self.assertAlmostEqual(particle_area_um2(100.0), 7853.981633974483, places=9)

    def test_doubling_the_size_quadruples_the_area(self):
        self.assertAlmostEqual(
            particle_area_um2(200.0), particle_area_um2(100.0) * 4.0, places=6
        )

    def test_zero_size_rejected(self):
        with self.assertRaises(ValueError):
            particle_area_um2(0.0)

    def test_obscured_area_sums_the_bands(self):
        total = obscured_area_um2([(100.0, 2.0), (200.0, 1.0)])
        self.assertAlmostEqual(total, 2.0 * 7853.981633974483 + 31415.926535897932, places=6)

    def test_coverage_of_one_large_particle(self):
        self.assertAlmostEqual(
            percent_area_coverage([(1000.0, 1.0)], 100.0), 0.007853981633974483, places=12
        )

    def test_coverage_scales_inversely_with_plate_area(self):
        small = percent_area_coverage([(1000.0, 1.0)], 50.0)
        large = percent_area_coverage([(1000.0, 1.0)], 100.0)
        self.assertAlmostEqual(small, large * 2.0, places=12)


class ControlSubtractionTests(unittest.TestCase):
    def test_control_is_removed_from_the_sample(self):
        self.assertAlmostEqual(net_coverage(0.05, 0.01), 0.04, places=12)

    def test_no_control_leaves_the_sample_unchanged(self):
        self.assertAlmostEqual(net_coverage(0.05), 0.05, places=12)

    def test_equal_control_and_sample_give_zero(self):
        self.assertAlmostEqual(net_coverage(0.05, 0.05), 0.0, places=12)

    def test_control_above_the_sample_is_refused(self):
        with self.assertRaises(ValueError):
            net_coverage(0.01, 0.05)

    def test_negative_control_rejected(self):
        with self.assertRaises(ValueError):
            net_coverage(0.05, -0.01)


class RateAndProjectionTests(unittest.TestCase):
    def test_rate_is_coverage_over_exposure(self):
        self.assertAlmostEqual(deposition_rate_per_hour(0.048, 24.0), 0.002, places=12)

    def test_projection_is_linear_in_time(self):
        self.assertAlmostEqual(project_coverage(0.002, 100.0), 0.2, places=12)

    def test_initial_coverage_is_carried_forward(self):
        self.assertAlmostEqual(project_coverage(0.002, 100.0, 0.05), 0.25, places=12)

    def test_zero_rate_leaves_the_initial_coverage(self):
        self.assertAlmostEqual(project_coverage(0.0, 100.0, 0.05), 0.05, places=12)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            project_coverage(-0.002, 100.0)

    def test_zero_exposure_rejected_in_the_rate(self):
        with self.assertRaises(ValueError):
            deposition_rate_per_hour(0.048, 0.0)


class BandingTests(unittest.TestCase):
    def test_a_tiny_coverage_is_negligible(self):
        self.assertEqual(categorize_coverage(0.001), "negligible")

    def test_a_band_boundary_stays_in_the_lower_band(self):
        self.assertEqual(categorize_coverage(0.01), "negligible")

    def test_a_mid_coverage_is_moderate(self):
        self.assertEqual(categorize_coverage(0.5), "moderate")

    def test_a_large_coverage_is_excessive(self):
        self.assertEqual(categorize_coverage(25.0), "excessive")

    def test_negative_coverage_rejected(self):
        with self.assertRaises(ValueError):
            categorize_coverage(-1.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "plate_area_cm2": 100.0,
            "exposure_hours": 24.0,
            "orientation": "upward",
            "bands": [(10.0, 500.0), (25.0, 120.0), (50.0, 20.0)],
            "control_bands": [(10.0, 20.0)],
            "control_plate_area_cm2": 100.0,
            "hardware_exposure_hours": 200.0,
            "allowed_coverage_percent": 0.05,
        }
        spec.update(overrides)
        return spec

    def test_a_sound_plate_is_compliant_and_clean(self):
        result = assess_fallout(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_the_control_lowers_the_net_coverage(self):
        result = assess_fallout(self._spec())
        self.assertLess(result["net_coverage_percent"], result["gross_coverage_percent"])

    def test_projection_is_rate_times_hardware_exposure(self):
        result = assess_fallout(self._spec())
        self.assertAlmostEqual(
            result["projected_coverage_percent"],
            result["rate_percent_per_hour"] * 200.0,
            places=12,
        )

    def test_a_projection_over_the_allowance_is_flagged(self):
        result = assess_fallout(self._spec(allowed_coverage_percent=0.001))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the allowed" in f for f in result["findings"]))

    def test_a_projection_exactly_on_the_allowance_is_compliant(self):
        base = assess_fallout(self._spec())
        tight = assess_fallout(
            self._spec(allowed_coverage_percent=base["projected_coverage_percent"])
        )
        self.assertTrue(tight["compliant"])

    def test_an_undersized_plate_is_flagged(self):
        result = assess_fallout(self._spec(plate_area_cm2=MIN_PLATE_AREA_CM2 / 5.0))
        self.assertTrue(any("below the" in f and "cm2 minimum" in f for f in result["findings"]))

    def test_a_short_exposure_is_flagged(self):
        result = assess_fallout(self._spec(exposure_hours=MIN_EXPOSURE_HOURS / 2.0))
        self.assertTrue(any("reporting handling" in f for f in result["findings"]))

    def test_a_non_upward_plate_is_flagged(self):
        result = assess_fallout(self._spec(orientation="vertical"))
        self.assertTrue(any("gravitational fallout" in f for f in result["findings"]))

    def test_a_missing_control_plate_is_flagged(self):
        spec = self._spec()
        del spec["control_bands"]
        result = assess_fallout(spec)
        self.assertTrue(any("no control plate" in f for f in result["findings"]))
        self.assertAlmostEqual(result["control_coverage_percent"], 0.0, places=12)

    def test_a_far_projection_is_flagged_as_extrapolation(self):
        result = assess_fallout(self._spec(hardware_exposure_hours=5000.0))
        self.assertTrue(any("extrapolating far past" in f for f in result["findings"]))

    def test_the_reporting_band_is_returned(self):
        result = assess_fallout(self._spec())
        self.assertIn(result["band"], ("negligible", "low", "moderate", "high", "excessive"))

    def test_zero_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_fallout(self._spec(allowed_coverage_percent=0.0))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["bands"]
        with self.assertRaises(ValueError):
            assess_fallout(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_fallout(["bands"])

    def test_tolerance_is_relative_and_tiny(self):
        self.assertLess(COVERAGE_TOLERANCE_REL, 1e-6)


if __name__ == "__main__":
    unittest.main()
