"""Contract tests for the post-cleaning verification logic."""

import math
import unittest

from q7001_cleaning_verification_after_cleaning_logic import (
    LEVEL_TOLERANCE,
    MIN_SAMPLE_SITES,
    MOLECULAR_LEVELS_MG_PER_M2,
    PARTICULATE_LEVELS,
    band_upper_micron,
    largest_populated_band,
    level_meets,
    net_residue_mg,
    obscuration_ppm,
    particulate_level_reached,
    residue_is_bounded,
    residue_level_reached,
    residue_mg_per_m2,
    sampling_adequacy,
    validate_counts,
    verify_after_cleaning,
)

CLEAN_COUNTS = {"5-15": 40, "15-25": 12, "25-50": 3}
DIRTY_COUNTS = {"5-15": 400, "100-250": 6, "250-500": 1}


def _measurement(**overrides):
    measurement = {
        "counts": dict(CLEAN_COUNTS),
        "sampled_area_m2": 0.05,
        "surface_area_m2": 1.0,
        "site_count": 4,
        "sample_mg": 0.38,
        "blank_mg": 0.30,
        "balance_resolution_mg": 0.05,
        "required_particulate_level": "PCL-100",
        "required_residue_level": "NVR-B",
    }
    measurement.update(overrides)
    return measurement


class BandTests(unittest.TestCase):
    def test_band_upper_bound_is_returned(self):
        self.assertAlmostEqual(band_upper_micron("25-50"), 50.0)

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            band_upper_micron("1000-2000")

    def test_non_string_band_rejected(self):
        with self.assertRaises(ValueError):
            band_upper_micron(50)

    def test_counts_validate(self):
        self.assertEqual(validate_counts(CLEAN_COUNTS), CLEAN_COUNTS)

    def test_empty_counts_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({})

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"5-15": -2})

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"5-15": 2.5})

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_counts({"5-15": True})


class ObscurationTests(unittest.TestCase):
    def test_single_particle_obscuration_matches_closed_form(self):
        value = obscuration_ppm({"5-15": 1}, 1.0)
        expected = 1.0e6 * math.pi * (0.5 * 15.0e-6) ** 2
        self.assertAlmostEqual(value, expected, places=12)

    def test_obscuration_scales_inversely_with_area(self):
        wide = obscuration_ppm(CLEAN_COUNTS, 0.10)
        narrow = obscuration_ppm(CLEAN_COUNTS, 0.05)
        self.assertAlmostEqual(narrow, 2.0 * wide, places=12)

    def test_larger_band_dominates_the_obscuration(self):
        small = obscuration_ppm({"5-15": 100}, 1.0)
        large = obscuration_ppm({"250-500": 1}, 1.0)
        self.assertGreater(large, small)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            obscuration_ppm(CLEAN_COUNTS, 0.0)


class ParticulateLadderTests(unittest.TestCase):
    def test_largest_populated_band_is_found(self):
        self.assertEqual(largest_populated_band(DIRTY_COUNTS), "250-500")

    def test_empty_bands_are_ignored(self):
        self.assertEqual(largest_populated_band({"5-15": 7, "250-500": 0}), "5-15")

    def test_all_zero_counts_have_no_populated_band(self):
        self.assertIsNone(largest_populated_band({"5-15": 0}))

    def test_all_zero_counts_reach_the_cleanest_level(self):
        self.assertEqual(particulate_level_reached({"5-15": 0}), PARTICULATE_LEVELS[0][0])

    def test_band_landing_exactly_on_a_bound_stays_on_that_level(self):
        self.assertEqual(particulate_level_reached({"25-50": 1}), "PCL-50")

    def test_dirty_surface_lands_further_down_the_ladder(self):
        self.assertEqual(particulate_level_reached(DIRTY_COUNTS), "PCL-500")


class ResidueTests(unittest.TestCase):
    def test_blank_is_subtracted(self):
        self.assertAlmostEqual(net_residue_mg(0.80, 0.30), 0.50, places=12)

    def test_blank_above_the_sample_is_an_invalid_run(self):
        with self.assertRaises(ValueError):
            net_residue_mg(0.20, 0.30)

    def test_negative_sample_rejected(self):
        with self.assertRaises(ValueError):
            net_residue_mg(-0.10, 0.0)

    def test_net_under_the_balance_floor_is_a_bound(self):
        self.assertTrue(residue_is_bounded(0.02, 0.05))

    def test_net_exactly_at_the_balance_floor_is_a_bound(self):
        self.assertTrue(residue_is_bounded(0.05, 0.05))

    def test_net_above_the_balance_floor_is_a_value(self):
        self.assertFalse(residue_is_bounded(0.50, 0.05))

    def test_zero_balance_resolution_rejected(self):
        with self.assertRaises(ValueError):
            residue_is_bounded(0.50, 0.0)

    def test_loading_is_mass_over_area(self):
        self.assertAlmostEqual(residue_mg_per_m2(0.50, 0.05), 10.0, places=12)

    def test_loading_on_a_bound_level_is_that_level(self):
        self.assertEqual(residue_level_reached(1.0), "NVR-A")

    def test_cleaner_loading_reaches_a_cleaner_level(self):
        self.assertEqual(residue_level_reached(0.05), "NVR-A/10")

    def test_loading_off_the_ladder_has_no_level(self):
        self.assertIsNone(residue_level_reached(9.0))

    def test_negative_loading_rejected(self):
        with self.assertRaises(ValueError):
            residue_level_reached(-0.1)


class SamplingTests(unittest.TestCase):
    def test_adequate_sample_has_no_findings(self):
        self.assertEqual(sampling_adequacy(0.05, 1.0, 4), [])

    def test_sampled_fraction_exactly_at_the_minimum_is_adequate(self):
        self.assertEqual(sampling_adequacy(0.01, 1.0, 3), [])

    def test_thin_sample_is_a_finding(self):
        findings = sampling_adequacy(0.001, 1.0, 3)
        self.assertEqual(len(findings), 1)
        self.assertIn("sampled fraction", findings[0])

    def test_single_site_is_a_finding(self):
        findings = sampling_adequacy(0.5, 1.0, 1)
        self.assertEqual(len(findings), 1)
        self.assertIn("sample site", findings[0])

    def test_minimum_site_count_is_adequate(self):
        self.assertEqual(sampling_adequacy(0.5, 1.0, MIN_SAMPLE_SITES), [])

    def test_sample_larger_than_the_surface_rejected(self):
        with self.assertRaises(ValueError):
            sampling_adequacy(2.0, 1.0, 3)

    def test_zero_site_count_rejected(self):
        with self.assertRaises(ValueError):
            sampling_adequacy(0.5, 1.0, 0)


class LevelComparisonTests(unittest.TestCase):
    def test_cleaner_meets_the_requirement(self):
        self.assertTrue(level_meets("PCL-50", "PCL-200", PARTICULATE_LEVELS))

    def test_equal_meets_the_requirement(self):
        self.assertTrue(level_meets("NVR-A", "NVR-A", MOLECULAR_LEVELS_MG_PER_M2))

    def test_dirtier_fails_the_requirement(self):
        self.assertFalse(level_meets("PCL-500", "PCL-100", PARTICULATE_LEVELS))

    def test_off_ladder_result_fails(self):
        self.assertFalse(level_meets(None, "NVR-C", MOLECULAR_LEVELS_MG_PER_M2))

    def test_unknown_required_level_rejected(self):
        with self.assertRaises(ValueError):
            level_meets("PCL-50", "PCL-42", PARTICULATE_LEVELS)


class VerificationTests(unittest.TestCase):
    def test_clean_surface_is_accepted(self):
        result = verify_after_cleaning(_measurement())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])

    def test_accepted_result_reports_both_levels(self):
        result = verify_after_cleaning(_measurement())
        self.assertEqual(result["particulate_level_reached"], "PCL-50")
        self.assertEqual(result["residue_level_reached"], "NVR-B")

    def test_large_particles_force_a_re_clean(self):
        result = verify_after_cleaning(_measurement(counts=dict(DIRTY_COUNTS)))
        self.assertEqual(result["verdict"], "re-clean")
        self.assertFalse(result["particulate_meets_requirement"])

    def test_residue_shortfall_forces_a_re_clean(self):
        result = verify_after_cleaning(
            _measurement(sample_mg=1.00, blank_mg=0.30, required_residue_level="NVR-A/2")
        )
        self.assertEqual(result["verdict"], "re-clean")
        self.assertFalse(result["residue_meets_requirement"])

    def test_thin_sample_forces_a_re_sample_before_any_verdict(self):
        result = verify_after_cleaning(
            _measurement(sampled_area_m2=0.001, counts=dict(DIRTY_COUNTS))
        )
        self.assertEqual(result["verdict"], "re-sample")

    def test_below_floor_residue_is_reported_as_a_bound(self):
        result = verify_after_cleaning(_measurement(sample_mg=0.32, blank_mg=0.30))
        self.assertTrue(result["residue_is_bound"])
        self.assertTrue(any("bound, not a value" in note for note in result["findings"]))

    def test_obscuration_is_reported(self):
        result = verify_after_cleaning(_measurement())
        expected = obscuration_ppm(CLEAN_COUNTS, 0.05)
        self.assertAlmostEqual(result["obscuration_ppm"], expected, places=12)

    def test_loading_on_a_level_bound_still_meets_it(self):
        result = verify_after_cleaning(
            _measurement(
                sample_mg=0.40,
                blank_mg=0.30,
                sampled_area_m2=0.05,
                required_residue_level="NVR-B",
            )
        )
        self.assertAlmostEqual(result["residue_loading_mg_per_m2"], 2.0, places=9)
        self.assertLessEqual(
            abs(result["residue_loading_mg_per_m2"] - 2.0), 1e-9 + LEVEL_TOLERANCE
        )
        self.assertTrue(result["residue_meets_requirement"])

    def test_invalid_blank_run_is_refused(self):
        with self.assertRaises(ValueError):
            verify_after_cleaning(_measurement(sample_mg=0.10, blank_mg=0.30))

    def test_missing_key_rejected(self):
        broken = _measurement()
        del broken["site_count"]
        with self.assertRaises(ValueError):
            verify_after_cleaning(broken)

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            verify_after_cleaning(["counts"])


if __name__ == "__main__":
    unittest.main()
