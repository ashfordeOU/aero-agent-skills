"""Contract tests for the cleanliness limit and level application logic."""

import unittest

from q7050_cleanliness_limit_application_logic import (
    DEFAULT_REFERENCE_AREA_M2,
    airborne_limit_per_m3,
    allowable_count_for_area,
    allowable_count_per_reference_area,
    assess_limit_application,
    envelope_level,
    grade_distribution,
    grade_facility_class,
    grade_point,
    required_level_for_point,
    validate_level,
    validate_size_um,
)

# A plausible cumulative surface distribution: many small particles, few large.
DISTRIBUTION = [(5.0, 900), (15.0, 120), (25.0, 30), (50.0, 4), (100.0, 1)]


class ValidationTests(unittest.TestCase):
    def test_level_returned_as_float(self):
        self.assertAlmostEqual(validate_level(500), 500.0, places=12)

    def test_level_at_one_micron_rejected(self):
        with self.assertRaises(ValueError):
            validate_level(1.0)

    def test_negative_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level(-500.0)

    def test_boolean_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level(True)

    def test_zero_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_um(0.0)

    def test_non_finite_size_rejected(self):
        with self.assertRaises(ValueError):
            validate_size_um(float("inf"))


class CurveTests(unittest.TestCase):
    def test_one_particle_is_allowed_at_the_level_label(self):
        self.assertAlmostEqual(
            allowable_count_per_reference_area(500.0, 500.0), 1.0, places=9
        )

    def test_nothing_is_allowed_above_the_level_label(self):
        self.assertAlmostEqual(
            allowable_count_per_reference_area(500.0, 501.0), 0.0, places=12
        )

    def test_allowance_falls_as_size_rises(self):
        small = allowable_count_per_reference_area(500.0, 25.0)
        large = allowable_count_per_reference_area(500.0, 100.0)
        self.assertGreater(small, large * 2.0)

    def test_a_higher_level_allows_more_at_the_same_size(self):
        tight = allowable_count_per_reference_area(300.0, 25.0)
        loose = allowable_count_per_reference_area(750.0, 25.0)
        self.assertGreater(loose, tight * 2.0)

    def test_allowance_scales_with_the_inspected_area(self):
        reference = allowable_count_per_reference_area(500.0, 25.0)
        doubled = allowable_count_for_area(
            500.0, 25.0, DEFAULT_REFERENCE_AREA_M2 * 2.0
        )
        self.assertAlmostEqual(doubled, reference * 2.0, places=6)

    def test_steeper_slope_tightens_the_allowance(self):
        shallow = allowable_count_per_reference_area(500.0, 25.0, 0.5)
        steep = allowable_count_per_reference_area(500.0, 25.0, 1.2)
        self.assertGreater(steep, shallow * 2.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            allowable_count_for_area(500.0, 25.0, 0.0)

    def test_negative_slope_rejected(self):
        with self.assertRaises(ValueError):
            allowable_count_per_reference_area(500.0, 25.0, -0.9)


class RequiredLevelTests(unittest.TestCase):
    def test_single_particle_at_a_size_requires_that_size_as_the_level(self):
        self.assertAlmostEqual(
            required_level_for_point(1, 500.0, DEFAULT_REFERENCE_AREA_M2),
            500.0,
            places=6,
        )

    def test_zero_counted_still_floors_the_level_at_the_size(self):
        self.assertAlmostEqual(
            required_level_for_point(0, 250.0, DEFAULT_REFERENCE_AREA_M2),
            250.0,
            places=9,
        )

    def test_more_particles_demand_a_higher_level(self):
        one = required_level_for_point(1, 500.0, DEFAULT_REFERENCE_AREA_M2)
        many = required_level_for_point(50, 500.0, DEFAULT_REFERENCE_AREA_M2)
        self.assertGreater(many, one * 1.1)

    def test_the_same_count_over_a_larger_area_demands_less(self):
        small_area = required_level_for_point(50, 500.0, 0.1)
        large_area = required_level_for_point(50, 500.0, 1.0)
        self.assertGreater(small_area, large_area * 1.01)

    def test_a_count_far_under_the_curve_is_floored_by_the_size(self):
        self.assertAlmostEqual(
            required_level_for_point(1, 5.0, 100.0), 5.0, places=9
        )

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            required_level_for_point(-3, 500.0, 0.1)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            required_level_for_point(3.5, 500.0, 0.1)


class EnvelopeTests(unittest.TestCase):
    def test_envelope_names_the_driving_channel(self):
        result = envelope_level(DISTRIBUTION, 0.1)
        self.assertIn(result["driving_size_um"], [p[0] for p in DISTRIBUTION])

    def test_envelope_level_admits_every_point(self):
        result = envelope_level(DISTRIBUTION, 0.1)
        graded = grade_distribution(DISTRIBUTION, result["required_level_um"], 0.1)
        self.assertTrue(graded["conforming"])

    def test_a_level_just_under_the_envelope_fails_somewhere(self):
        result = envelope_level(DISTRIBUTION, 0.1)
        graded = grade_distribution(
            DISTRIBUTION, result["required_level_um"] * 0.8, 0.1
        )
        self.assertFalse(graded["conforming"])

    def test_unsorted_observations_are_ordered_before_grading(self):
        shuffled = list(reversed(DISTRIBUTION))
        self.assertAlmostEqual(
            envelope_level(shuffled, 0.1)["required_level_um"],
            envelope_level(DISTRIBUTION, 0.1)["required_level_um"],
            places=9,
        )

    def test_rising_cumulative_counts_rejected(self):
        with self.assertRaises(ValueError):
            envelope_level([(5.0, 10), (25.0, 40)], 0.1)

    def test_repeated_size_channel_rejected(self):
        with self.assertRaises(ValueError):
            envelope_level([(5.0, 10), (5.0, 8)], 0.1)

    def test_empty_observations_rejected(self):
        with self.assertRaises(ValueError):
            envelope_level([], 0.1)

    def test_malformed_observation_rejected(self):
        with self.assertRaises(ValueError):
            envelope_level([(5.0,)], 0.1)


class GradingTests(unittest.TestCase):
    def test_count_equal_to_the_allowance_conforms(self):
        graded = grade_point(1, 500.0, 500.0, DEFAULT_REFERENCE_AREA_M2)
        self.assertTrue(graded["conforming"])
        self.assertAlmostEqual(graded["utilisation"], 1.0, places=9)

    def test_count_above_the_allowance_fails(self):
        graded = grade_point(5, 500.0, 500.0, DEFAULT_REFERENCE_AREA_M2)
        self.assertFalse(graded["conforming"])

    def test_no_particle_is_allowed_above_the_level_label(self):
        graded = grade_point(1, 600.0, 500.0, DEFAULT_REFERENCE_AREA_M2)
        self.assertFalse(graded["conforming"])
        self.assertIsNone(graded["utilisation"])

    def test_zero_count_above_the_level_label_still_conforms(self):
        graded = grade_point(0, 600.0, 500.0, DEFAULT_REFERENCE_AREA_M2)
        self.assertTrue(graded["conforming"])

    def test_distribution_reports_every_failing_channel(self):
        graded = grade_distribution(DISTRIBUTION, 50.0, 0.1)
        self.assertFalse(graded["conforming"])
        self.assertGreaterEqual(len(graded["failing_sizes_um"]), 1)

    def test_distribution_driving_point_is_the_worst_utilisation(self):
        graded = grade_distribution(DISTRIBUTION, 750.0, 0.1)
        worst = graded["driving_point"]
        for entry in graded["points"]:
            if entry["utilisation"] is not None and worst["utilisation"] is not None:
                self.assertLessEqual(
                    entry["utilisation"], worst["utilisation"] + 1e-12
                )

    def test_negative_count_rejected_in_grading(self):
        with self.assertRaises(ValueError):
            grade_point(-1, 25.0, 500.0, 0.1)


class FacilityTests(unittest.TestCase):
    def test_limit_at_the_reference_size_is_the_class_decade(self):
        self.assertAlmostEqual(
            airborne_limit_per_m3(5.0, 0.1) / 1.0e5, 1.0, places=9
        )

    def test_one_class_up_is_a_decade_looser(self):
        ratio = airborne_limit_per_m3(6.0, 0.5) / airborne_limit_per_m3(5.0, 0.5)
        self.assertAlmostEqual(ratio, 10.0, places=6)

    def test_limit_falls_with_particle_size(self):
        self.assertGreater(
            airborne_limit_per_m3(5.0, 0.3), airborne_limit_per_m3(5.0, 5.0) * 2.0
        )

    def test_conforming_room_passes(self):
        result = grade_facility_class([(0.5, 1000.0), (5.0, 20.0)], 7.0)
        self.assertTrue(result["conforming"])

    def test_over_concentration_fails(self):
        result = grade_facility_class([(0.5, 1.0e9)], 5.0)
        self.assertFalse(result["conforming"])

    def test_negative_concentration_rejected(self):
        with self.assertRaises(ValueError):
            grade_facility_class([(0.5, -1.0)], 5.0)

    def test_malformed_measurement_rejected(self):
        with self.assertRaises(ValueError):
            grade_facility_class([(0.5,)], 5.0)

    def test_empty_measurements_rejected(self):
        with self.assertRaises(ValueError):
            grade_facility_class([], 5.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "observations": DISTRIBUTION,
            "area_m2": 0.1,
            "assigned_level_um": 750.0,
        }
        spec.update(overrides)
        return spec

    def test_generous_level_is_compliant(self):
        result = assess_limit_application(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_tight_level_reports_a_finding(self):
        result = assess_limit_application(self._spec(assigned_level_um=50.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("assigned level" in f for f in result["findings"]))

    def test_envelope_is_reported_even_without_an_assigned_level(self):
        spec = self._spec()
        del spec["assigned_level_um"]
        result = assess_limit_application(spec)
        self.assertIsNone(result["surface"])
        self.assertIsNotNone(result["envelope"]["required_level_um"])

    def test_facility_failure_is_reported(self):
        result = assess_limit_application(self._spec(facility={
            "measurements": [(0.5, 1.0e9)],
            "iso_class": 5.0,
        }))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("class" in f for f in result["findings"]))

    def test_facility_pass_keeps_the_assessment_compliant(self):
        result = assess_limit_application(self._spec(facility={
            "measurements": [(0.5, 100.0)],
            "iso_class": 7.0,
        }))
        self.assertTrue(result["compliant"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["area_m2"]
        with self.assertRaises(ValueError):
            assess_limit_application(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_limit_application(["observations"])

    def test_malformed_facility_rejected(self):
        with self.assertRaises(ValueError):
            assess_limit_application(self._spec(facility={"iso_class": 5.0}))


if __name__ == "__main__":
    unittest.main()
