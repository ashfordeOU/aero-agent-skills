"""Contract tests for the tape-lift surface sampling logic."""

import unittest

from q7050_tape_lift_sampling_logic import (
    COUNT_TOLERANCE_REL,
    MAX_EFFICIENCY,
    MIN_EFFICIENCY,
    MIN_LIFT_AREA_CM2,
    REFERENCE_AREA_CM2,
    assess_tape_lift,
    correct_for_efficiency,
    cumulative_counts,
    grade_bands,
    scale_to_reference_area,
    subtract_blank,
    validate_bands,
    validate_efficiency,
    validate_lift_area_cm2,
)

BANDS = [(5.0, 120.0), (15.0, 40.0), (25.0, 12.0), (50.0, 3.0)]
BLANK = [(5.0, 10.0), (15.0, 2.0), (25.0, 0.0), (50.0, 0.0)]
ALLOWANCES = [(5.0, 5000.0), (15.0, 2000.0), (25.0, 600.0), (50.0, 120.0)]


class ValidationTests(unittest.TestCase):
    def test_lift_area_is_returned_as_a_float(self):
        self.assertAlmostEqual(validate_lift_area_cm2(50), 50.0, places=12)

    def test_zero_lift_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_lift_area_cm2(0.0)

    def test_boolean_lift_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_lift_area_cm2(True)

    def test_full_recovery_is_allowed(self):
        self.assertAlmostEqual(validate_efficiency(MAX_EFFICIENCY), 1.0, places=12)

    def test_efficiency_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_efficiency(1.2)

    def test_efficiency_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_efficiency(MIN_EFFICIENCY / 2.0)

    def test_bands_are_returned_as_floats(self):
        self.assertEqual(validate_bands([(5, 3)]), [(5.0, 3.0)])

    def test_unordered_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(25.0, 3.0), (5.0, 2.0)])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([(5.0, -2.0)])

    def test_empty_bands_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([])


class BlankSubtractionTests(unittest.TestCase):
    def test_blank_counts_are_removed_band_by_band(self):
        net = subtract_blank(BANDS, BLANK)
        self.assertAlmostEqual(net[0][1], 110.0, places=12)
        self.assertAlmostEqual(net[1][1], 38.0, places=12)

    def test_a_blank_above_the_sample_floors_at_zero(self):
        net = subtract_blank([(5.0, 4.0)], [(5.0, 9.0)])
        self.assertAlmostEqual(net[0][1], 0.0, places=12)

    def test_untouched_bands_are_unchanged(self):
        net = subtract_blank(BANDS, BLANK)
        self.assertAlmostEqual(net[3][1], 3.0, places=12)

    def test_a_blank_band_with_no_sample_band_is_refused(self):
        with self.assertRaises(ValueError):
            subtract_blank([(5.0, 10.0)], [(7.0, 1.0)])

    def test_malformed_blank_rejected(self):
        with self.assertRaises(ValueError):
            subtract_blank(BANDS, [])


class EfficiencyCorrectionTests(unittest.TestCase):
    def test_partial_recovery_raises_the_count(self):
        corrected = correct_for_efficiency([(5.0, 80.0)], 0.8)
        self.assertAlmostEqual(corrected[0][1], 100.0, places=12)

    def test_full_recovery_leaves_the_count(self):
        corrected = correct_for_efficiency([(5.0, 80.0)], 1.0)
        self.assertAlmostEqual(corrected[0][1], 80.0, places=12)

    def test_halving_the_efficiency_doubles_the_count(self):
        low = correct_for_efficiency([(5.0, 80.0)], 0.2)
        high = correct_for_efficiency([(5.0, 80.0)], 0.4)
        self.assertAlmostEqual(low[0][1], high[0][1] * 2.0, places=9)

    def test_sizes_are_preserved(self):
        corrected = correct_for_efficiency(BANDS, 0.8)
        self.assertEqual([s for s, _ in corrected], [s for s, _ in BANDS])

    def test_out_of_range_efficiency_rejected(self):
        with self.assertRaises(ValueError):
            correct_for_efficiency(BANDS, 0.0)


class CumulativeTests(unittest.TestCase):
    def test_largest_band_is_unchanged(self):
        cumulative = cumulative_counts(BANDS)
        self.assertAlmostEqual(cumulative[-1][1], 3.0, places=12)

    def test_smallest_band_carries_the_whole_population(self):
        cumulative = cumulative_counts(BANDS)
        self.assertAlmostEqual(cumulative[0][1], 175.0, places=12)

    def test_the_distribution_never_rises_with_size(self):
        cumulative = cumulative_counts(BANDS)
        for i in range(1, len(cumulative)):
            self.assertLessEqual(cumulative[i][1], cumulative[i - 1][1])

    def test_a_single_band_is_its_own_cumulative(self):
        self.assertEqual(cumulative_counts([(5.0, 7.0)]), [(5.0, 7.0)])


class ScalingTests(unittest.TestCase):
    def test_counts_scale_with_the_area_ratio(self):
        scaled = scale_to_reference_area([(5.0, 100.0)], 50.0)
        self.assertAlmostEqual(scaled[0][1], 2000.0, places=9)

    def test_lifting_the_whole_reference_area_changes_nothing(self):
        scaled = scale_to_reference_area([(5.0, 100.0)], REFERENCE_AREA_CM2)
        self.assertAlmostEqual(scaled[0][1], 100.0, places=9)

    def test_a_smaller_lift_extrapolates_further(self):
        small = scale_to_reference_area([(5.0, 100.0)], 25.0)
        large = scale_to_reference_area([(5.0, 100.0)], 50.0)
        self.assertAlmostEqual(small[0][1], large[0][1] * 2.0, places=9)

    def test_zero_lift_area_rejected(self):
        with self.assertRaises(ValueError):
            scale_to_reference_area([(5.0, 100.0)], 0.0)


class GradingTests(unittest.TestCase):
    def test_a_band_under_its_allowance_is_compliant(self):
        graded = grade_bands([(5.0, 100.0)], [(5.0, 200.0)])
        self.assertTrue(graded[0]["compliant"])
        self.assertAlmostEqual(graded[0]["utilisation"], 0.5, places=12)

    def test_a_band_exactly_on_its_allowance_is_compliant(self):
        graded = grade_bands([(5.0, 200.0)], [(5.0, 200.0)])
        self.assertTrue(graded[0]["compliant"])
        self.assertAlmostEqual(graded[0]["utilisation"], 1.0, places=12)

    def test_a_band_over_its_allowance_fails(self):
        graded = grade_bands([(5.0, 201.0)], [(5.0, 200.0)])
        self.assertFalse(graded[0]["compliant"])

    def test_a_band_with_no_allowance_is_refused(self):
        with self.assertRaises(ValueError):
            grade_bands([(5.0, 100.0), (9.0, 10.0)], [(5.0, 200.0)])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "lift_area_cm2": 50.0,
            "efficiency": 0.8,
            "bands": list(BANDS),
            "blank_bands": list(BLANK),
            "allowances": list(ALLOWANCES),
        }
        spec.update(overrides)
        return spec

    def test_a_sound_lift_is_compliant_and_clean(self):
        result = assess_tape_lift(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_the_scaled_cumulative_count_is_reported(self):
        result = assess_tape_lift(self._spec())
        self.assertAlmostEqual(result["cumulative_per_reference_area"][0][1], 4075.0, places=6)

    def test_the_governing_band_is_the_highest_utilisation(self):
        result = assess_tape_lift(self._spec())
        self.assertAlmostEqual(result["governing_band"]["size_um"], 5.0, places=12)

    def test_a_missing_blank_is_flagged(self):
        spec = self._spec()
        del spec["blank_bands"]
        result = assess_tape_lift(spec)
        self.assertTrue(any("no blank lift" in f for f in result["findings"]))

    def test_a_missing_blank_leaves_a_higher_count(self):
        spec = self._spec()
        with_blank = assess_tape_lift(spec)
        del spec["blank_bands"]
        without_blank = assess_tape_lift(spec)
        self.assertGreater(
            without_blank["cumulative_per_reference_area"][0][1],
            with_blank["cumulative_per_reference_area"][0][1],
        )

    def test_a_tiny_lift_area_is_flagged(self):
        result = assess_tape_lift(self._spec(lift_area_cm2=MIN_LIFT_AREA_CM2 / 5.0))
        self.assertTrue(any("below the" in f and "cm2 minimum" in f for f in result["findings"]))

    def test_multiple_lifts_raise_the_sampled_area(self):
        single = assess_tape_lift(self._spec())
        doubled = assess_tape_lift(self._spec(lift_count=2))
        self.assertAlmostEqual(doubled["total_area_cm2"], single["total_area_cm2"] * 2.0, places=9)
        self.assertAlmostEqual(
            doubled["cumulative_per_reference_area"][0][1],
            single["cumulative_per_reference_area"][0][1] / 2.0,
            places=6,
        )

    def test_a_poor_recovery_is_flagged(self):
        result = assess_tape_lift(self._spec(efficiency=0.2))
        self.assertTrue(any("recovery efficiency" in f for f in result["findings"]))

    def test_a_dirty_surface_fails_its_level(self):
        dirty = [(5.0, 1200.0), (15.0, 400.0), (25.0, 120.0), (50.0, 30.0)]
        result = assess_tape_lift(self._spec(bands=dirty))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("over the stated level" in f for f in result["findings"]))

    def test_zero_lift_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_tape_lift(self._spec(lift_count=0))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["allowances"]
        with self.assertRaises(ValueError):
            assess_tape_lift(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tape_lift(["bands"])

    def test_tolerance_is_relative_and_tiny(self):
        self.assertLess(COUNT_TOLERANCE_REL, 1e-6)


if __name__ == "__main__":
    unittest.main()
