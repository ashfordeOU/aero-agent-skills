"""Contract tests for the post-repair cleanliness verification logic."""

import unittest

from q7028_cleanliness_after_repair_logic import (
    CLEANLINESS_LIMITS_UG_NACL_PER_CM2,
    DEFAULT_CLEANLINESS_CATEGORY,
    MAX_VERIFICATION_DELAY_HOURS,
    MIN_DRYING_MINUTES,
    MIN_EXTRACT_VOLUME_ML_PER_CM2,
    assess_cleanliness_after_repair,
    cleaning_agent_findings,
    cleanliness_limit,
    cleanliness_utilisation,
    extract_area_cm2,
    extract_volume_findings,
    nacl_equivalent_ug_per_cm2,
    timing_findings,
    visual_findings,
)


def base_record(**overrides):
    """A 100 x 100 mm double-sided board, rosin flux, cleaned in isopropanol.

    Area is 200 cm2, the extract is 400 mL, and a net 1.0 uS/cm reading gives
    1.0 x 400 x 0.5 / 200 = 1.0 ug NaCl-eq/cm2 -- exactly on the default limit.
    """
    record = {
        "board_dimensions_mm": (100.0, 100.0),
        "sides": 2,
        "flux_category": "rosin",
        "cleaning_agent": "isopropanol",
        "extract_volume_ml": 400.0,
        "extract_conductivity_us_cm": 2.5,
        "blank_conductivity_us_cm": 2.0,
        "visual_observations": (),
        "drying_minutes": 45.0,
        "verification_delay_hours": 2.0,
    }
    record.update(overrides)
    return record


class AreaTests(unittest.TestCase):
    def test_double_sided_area_counts_both_faces(self):
        self.assertAlmostEqual(extract_area_cm2((100.0, 100.0), 2), 200.0, places=9)

    def test_single_sided_area_counts_one_face(self):
        self.assertAlmostEqual(extract_area_cm2((100.0, 100.0), 1), 100.0, places=9)

    def test_extra_area_is_added(self):
        self.assertAlmostEqual(extract_area_cm2((100.0, 100.0), 1, 12.5), 112.5, places=9)

    def test_three_sided_board_rejected(self):
        with self.assertRaises(ValueError):
            extract_area_cm2((100.0, 100.0), 3)

    def test_zero_dimension_rejected(self):
        with self.assertRaises(ValueError):
            extract_area_cm2((100.0, 0.0), 2)

    def test_negative_extra_area_rejected(self):
        with self.assertRaises(ValueError):
            extract_area_cm2((100.0, 100.0), 2, -1.0)


class ExtractTests(unittest.TestCase):
    def test_blank_is_subtracted_from_the_reading(self):
        value = nacl_equivalent_ug_per_cm2(2.5, 2.0, 400.0, 200.0)
        self.assertAlmostEqual(value, 0.5, places=9)

    def test_a_reading_equal_to_the_blank_gives_zero(self):
        self.assertAlmostEqual(nacl_equivalent_ug_per_cm2(2.0, 2.0, 400.0, 200.0), 0.0, places=9)

    def test_reading_below_the_blank_rejected(self):
        with self.assertRaises(ValueError):
            nacl_equivalent_ug_per_cm2(1.0, 2.0, 400.0, 200.0)

    def test_density_scales_with_volume_over_area(self):
        small = nacl_equivalent_ug_per_cm2(3.0, 2.0, 400.0, 200.0)
        large = nacl_equivalent_ug_per_cm2(3.0, 2.0, 800.0, 200.0)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_adequate_extract_volume_is_clean(self):
        self.assertEqual(extract_volume_findings(400.0, 200.0), [])

    def test_volume_exactly_on_the_minimum_ratio_is_clean(self):
        area = 200.0
        self.assertEqual(
            extract_volume_findings(MIN_EXTRACT_VOLUME_ML_PER_CM2 * area, area), []
        )

    def test_starved_extract_is_flagged(self):
        findings = extract_volume_findings(100.0, 200.0)
        self.assertTrue(any("below the" in f for f in findings))

    def test_zero_extract_volume_rejected(self):
        with self.assertRaises(ValueError):
            extract_volume_findings(0.0, 200.0)


class LimitTests(unittest.TestCase):
    def test_default_category_has_a_limit(self):
        self.assertAlmostEqual(
            cleanliness_limit(DEFAULT_CLEANLINESS_CATEGORY),
            CLEANLINESS_LIMITS_UG_NACL_PER_CM2[DEFAULT_CLEANLINESS_CATEGORY],
            places=9,
        )

    def test_crewed_compartment_is_the_tightest_category(self):
        self.assertLess(
            cleanliness_limit("crewed-compartment"), cleanliness_limit("standard")
        )

    def test_category_lookup_ignores_case_and_padding(self):
        self.assertAlmostEqual(
            cleanliness_limit("  High-Reliability "),
            cleanliness_limit("high-reliability"),
            places=9,
        )

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness_limit("pristine")

    def test_utilisation_of_a_value_on_the_limit_is_one(self):
        limit = cleanliness_limit("high-reliability")
        self.assertAlmostEqual(cleanliness_utilisation(limit, "high-reliability"), 1.0, places=9)

    def test_negative_density_rejected(self):
        with self.assertRaises(ValueError):
            cleanliness_utilisation(-0.1)


class AgentTests(unittest.TestCase):
    def test_isopropanol_removes_a_rosin_residue(self):
        self.assertEqual(cleaning_agent_findings("rosin", "isopropanol"), [])

    def test_water_alone_does_not_remove_a_rosin_residue(self):
        findings = cleaning_agent_findings("rosin", "deionised-water")
        self.assertTrue(any("does not remove" in f for f in findings))

    def test_water_soluble_flux_takes_water(self):
        self.assertEqual(cleaning_agent_findings("water-soluble", "deionised-water"), [])

    def test_a_disturbed_no_clean_residue_still_needs_an_agent(self):
        self.assertEqual(cleaning_agent_findings("no-clean", "isopropanol"), [])
        self.assertTrue(cleaning_agent_findings("no-clean", "deionised-water"))

    def test_unknown_flux_category_rejected(self):
        with self.assertRaises(ValueError):
            cleaning_agent_findings("organic-acid", "isopropanol")

    def test_blank_agent_rejected(self):
        with self.assertRaises(ValueError):
            cleaning_agent_findings("rosin", "   ")


class VisualAndTimingTests(unittest.TestCase):
    def test_a_clean_repair_area_reports_nothing(self):
        self.assertEqual(visual_findings(()), [])

    def test_white_residue_is_reported(self):
        findings = visual_findings(["white-residue"])
        self.assertTrue(any("white-residue" in f for f in findings))

    def test_unknown_observation_rejected(self):
        with self.assertRaises(ValueError):
            visual_findings(["scorch"])

    def test_a_bare_string_is_not_a_sequence_of_observations(self):
        with self.assertRaises(ValueError):
            visual_findings("flux-residue")

    def test_nominal_timing_is_clean(self):
        self.assertEqual(timing_findings(MIN_DRYING_MINUTES, 1.0), [])

    def test_drying_exactly_on_the_minimum_is_clean(self):
        self.assertEqual(timing_findings(MIN_DRYING_MINUTES, 0.0), [])

    def test_short_drying_is_flagged(self):
        self.assertTrue(any("short of" in f for f in timing_findings(5.0, 1.0)))

    def test_delay_exactly_on_the_window_is_clean(self):
        self.assertEqual(timing_findings(MIN_DRYING_MINUTES, MAX_VERIFICATION_DELAY_HOURS), [])

    def test_late_verification_is_flagged(self):
        findings = timing_findings(MIN_DRYING_MINUTES, 72.0)
        self.assertTrue(any("beyond the" in f for f in findings))

    def test_negative_delay_rejected(self):
        with self.assertRaises(ValueError):
            timing_findings(MIN_DRYING_MINUTES, -1.0)


class AssessmentTests(unittest.TestCase):
    def test_nominal_record_verifies_clean(self):
        result = assess_cleanliness_after_repair(base_record())
        self.assertTrue(result["verified_clean"])
        self.assertEqual(result["findings"], [])

    def test_area_and_density_are_reported(self):
        result = assess_cleanliness_after_repair(base_record())
        self.assertAlmostEqual(result["wetted_area_cm2"], 200.0, places=9)
        self.assertAlmostEqual(result["residue_ug_per_cm2"], 0.5, places=9)

    def test_residue_exactly_on_the_limit_still_verifies(self):
        record = base_record(extract_conductivity_us_cm=3.0, blank_conductivity_us_cm=2.0)
        result = assess_cleanliness_after_repair(record)
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)
        self.assertTrue(result["verified_clean"])

    def test_residue_over_the_limit_fails_and_names_the_criterion(self):
        record = base_record(extract_conductivity_us_cm=8.0, blank_conductivity_us_cm=2.0)
        result = assess_cleanliness_after_repair(record)
        self.assertFalse(result["verified_clean"])
        self.assertEqual(result["governing_criterion"], "ionic-cleanliness-limit")

    def test_the_tighter_category_can_turn_the_same_extract_into_a_failure(self):
        record = base_record(
            extract_conductivity_us_cm=3.0,
            blank_conductivity_us_cm=2.0,
            cleanliness_category="crewed-compartment",
        )
        self.assertFalse(assess_cleanliness_after_repair(record)["verified_clean"])

    def test_a_visible_residue_blocks_a_passing_measurement(self):
        record = base_record(visual_observations=["flux-residue"])
        result = assess_cleanliness_after_repair(record)
        self.assertFalse(result["verified_clean"])
        self.assertEqual(result["governing_criterion"], "supporting-evidence")

    def test_wrong_cleaning_agent_reaches_the_findings(self):
        record = base_record(cleaning_agent="deionised-water")
        result = assess_cleanliness_after_repair(record)
        self.assertTrue(any("does not remove" in f for f in result["findings"]))

    def test_margin_is_the_limit_less_the_density(self):
        result = assess_cleanliness_after_repair(base_record())
        self.assertAlmostEqual(
            result["margin_ug_per_cm2"],
            result["limit_ug_per_cm2"] - result["residue_ug_per_cm2"],
            places=9,
        )

    def test_missing_required_key_rejected(self):
        record = base_record()
        del record["extract_volume_ml"]
        with self.assertRaises(ValueError):
            assess_cleanliness_after_repair(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanliness_after_repair(["board"])


if __name__ == "__main__":
    unittest.main()
