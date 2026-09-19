"""Contract tests for the ECSS-Q-ST-70-53C cleanliness-effect evaluation."""

import unittest

from q7053_contamination_and_cleanliness_effects_logic import (
    BAND_TOLERANCE,
    DEFAULT_CLEANLINESS_BANDS,
    assess_contamination_effects,
    band_ceiling,
    band_meets_requirement,
    cleanliness_band,
    obscuration_percent,
    projected_area_um2,
    residue_increase,
    validate_area_cm2,
    validate_bands,
    validate_distribution,
)

# One 100 um particle over 1 cm^2 obscures this percentage of the area.
ONE_HUNDRED_MICRON_OVER_ONE_CM2 = 0.007853981633974483
ONE_HUNDRED_MICRON_AREA_UM2 = 7853.981633974483


class AreaAndDistributionTests(unittest.TestCase):
    def test_area_is_returned_as_float(self):
        self.assertAlmostEqual(validate_area_cm2(2), 2.0)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_cm2(0.0)

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_cm2(-1.0)

    def test_pair_form_bin_accepted(self):
        self.assertEqual(validate_distribution([(25.0, 4)]), [(25.0, 4)])

    def test_mapping_form_bin_accepted(self):
        bins = validate_distribution([{"diameter_um": 25.0, "count": 4}])
        self.assertEqual(bins, [(25.0, 4)])

    def test_empty_distribution_is_allowed(self):
        self.assertEqual(validate_distribution([]), [])

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution([(0.0, 4)])

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution([(25.0, -1)])

    def test_fractional_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution([(25.0, 2.5)])

    def test_malformed_bin_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution([(25.0,)])

    def test_mapping_bin_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_distribution([{"diameter_um": 25.0}])


class ObscurationTests(unittest.TestCase):
    def test_projected_area_of_one_particle(self):
        self.assertAlmostEqual(
            projected_area_um2([(100.0, 1)]), ONE_HUNDRED_MICRON_AREA_UM2, places=9
        )

    def test_projected_area_scales_with_count(self):
        single = projected_area_um2([(100.0, 1)])
        triple = projected_area_um2([(100.0, 3)])
        self.assertAlmostEqual(triple, 3.0 * single, places=9)

    def test_doubling_diameter_quadruples_projected_area(self):
        small = projected_area_um2([(50.0, 1)])
        large = projected_area_um2([(100.0, 1)])
        self.assertAlmostEqual(large, 4.0 * small, places=9)

    def test_obscuration_percentage_over_one_square_centimetre(self):
        self.assertAlmostEqual(
            obscuration_percent([(100.0, 1)], 1.0),
            ONE_HUNDRED_MICRON_OVER_ONE_CM2,
            places=12,
        )

    def test_larger_inspected_area_gives_a_cleaner_figure(self):
        tight = obscuration_percent([(100.0, 1)], 1.0)
        wide = obscuration_percent([(100.0, 1)], 10.0)
        self.assertAlmostEqual(wide, tight / 10.0, places=12)

    def test_empty_distribution_obscures_nothing(self):
        self.assertAlmostEqual(obscuration_percent([], 1.0), 0.0)

    def test_obscuration_needs_a_positive_area(self):
        with self.assertRaises(ValueError):
            obscuration_percent([(100.0, 1)], 0.0)


class BandTests(unittest.TestCase):
    def test_default_table_validates(self):
        self.assertEqual(len(validate_bands()), len(DEFAULT_CLEANLINESS_BANDS))

    def test_non_increasing_ceilings_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("a", 0.01), ("b", 0.01)])

    def test_single_entry_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("a", 0.01)])

    def test_unnamed_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_bands([("", 0.01), ("b", 0.02)])

    def test_band_ceiling_lookup(self):
        self.assertAlmostEqual(band_ceiling("level-300"), 0.0025)

    def test_unknown_band_lookup_rejected(self):
        with self.assertRaises(ValueError):
            band_ceiling("level-42")

    def test_tightest_band_is_selected(self):
        self.assertEqual(cleanliness_band(0.002), "level-300")

    def test_very_clean_surface_reaches_the_tightest_band(self):
        self.assertEqual(cleanliness_band(0.00005), "level-100")

    def test_figure_exactly_on_a_ceiling_stays_in_that_band(self):
        bands = [("tight", ONE_HUNDRED_MICRON_OVER_ONE_CM2), ("loose", 0.1)]
        value = obscuration_percent([(100.0, 1)], 1.0)
        self.assertEqual(cleanliness_band(value, bands), "tight")

    def test_dirtier_than_the_coarsest_band_has_no_band(self):
        self.assertIsNone(cleanliness_band(1.5))

    def test_negative_obscuration_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness_band(-0.1)

    def test_tighter_band_meets_a_looser_requirement(self):
        self.assertTrue(band_meets_requirement("level-300", "level-500"))

    def test_looser_band_does_not_meet_a_tighter_requirement(self):
        self.assertFalse(band_meets_requirement("level-750", "level-500"))

    def test_equal_band_meets_the_requirement(self):
        self.assertTrue(band_meets_requirement("level-500", "level-500"))

    def test_absent_band_never_meets_the_requirement(self):
        self.assertFalse(band_meets_requirement(None, "level-1000"))


class ResidueTests(unittest.TestCase):
    def test_increase_is_the_difference(self):
        self.assertAlmostEqual(residue_increase(0.5, 1.25), 0.75)

    def test_a_cleaner_surface_adds_nothing(self):
        self.assertAlmostEqual(residue_increase(1.5, 0.75), 0.0)

    def test_negative_pre_value_rejected(self):
        with self.assertRaises(ValueError):
            residue_increase(-0.1, 1.0)

    def test_negative_post_value_rejected(self):
        with self.assertRaises(ValueError):
            residue_increase(0.1, -1.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "inspected_area_cm2": 1.0,
            "pre_distribution": [(50.0, 1)],
            "post_distribution": [(100.0, 1)],
            "required_level": "level-500",
            "pre_nvr_mg_m2": 0.5,
            "post_nvr_mg_m2": 1.0,
            "nvr_allocation_mg_m2": 1.0,
            "nvr_requirement_mg_m2": 2.0,
        }
        spec.update(overrides)
        return spec

    def test_compliant_case_has_no_findings(self):
        result = assess_contamination_effects(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_bands_are_reported_for_both_states(self):
        result = assess_contamination_effects(self._spec())
        self.assertEqual(result["pre_band"], "level-300")
        self.assertEqual(result["post_band"], "level-500")

    def test_obscuration_increase_is_reported(self):
        result = assess_contamination_effects(self._spec())
        self.assertGreater(result["obscuration_increase_percent"], 0.0)

    def test_required_level_not_met_is_a_finding(self):
        result = assess_contamination_effects(self._spec(required_level="level-300"))
        self.assertFalse(result["level_met"])
        self.assertEqual(len(result["findings"]), 1)

    def test_surface_with_no_band_is_a_finding(self):
        result = assess_contamination_effects(
            self._spec(post_distribution=[(1000.0, 20)])
        )
        self.assertIsNone(result["post_band"])
        self.assertFalse(result["acceptable"])

    def test_allocation_breach_is_a_finding(self):
        result = assess_contamination_effects(
            self._spec(pre_nvr_mg_m2=0.1, post_nvr_mg_m2=1.8, nvr_allocation_mg_m2=1.0)
        )
        self.assertFalse(result["within_allocation"])
        self.assertTrue(result["within_requirement"])

    def test_total_requirement_breach_is_independent_of_the_allocation(self):
        result = assess_contamination_effects(
            self._spec(pre_nvr_mg_m2=1.9, post_nvr_mg_m2=2.4,
                       nvr_allocation_mg_m2=1.0, nvr_requirement_mg_m2=2.0)
        )
        self.assertTrue(result["within_allocation"])
        self.assertFalse(result["within_requirement"])

    def test_added_residue_floors_at_zero(self):
        result = assess_contamination_effects(
            self._spec(pre_nvr_mg_m2=1.5, post_nvr_mg_m2=1.0)
        )
        self.assertAlmostEqual(result["residue_added_mg_m2"], 0.0)

    def test_allocation_exactly_met_is_within(self):
        result = assess_contamination_effects(
            self._spec(pre_nvr_mg_m2=0.5, post_nvr_mg_m2=1.5, nvr_allocation_mg_m2=1.0,
                       nvr_requirement_mg_m2=2.0)
        )
        self.assertAlmostEqual(result["residue_added_mg_m2"], 1.0, places=9)
        self.assertTrue(result["within_allocation"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["required_level"]
        with self.assertRaises(ValueError):
            assess_contamination_effects(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_contamination_effects(["inspected_area_cm2"])

    def test_unknown_required_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_contamination_effects(self._spec(required_level="level-42"))

    def test_non_positive_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_contamination_effects(self._spec(nvr_requirement_mg_m2=0.0))

    def test_band_tolerance_is_small_and_positive(self):
        self.assertGreater(BAND_TOLERANCE, 0.0)
        self.assertLess(BAND_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
