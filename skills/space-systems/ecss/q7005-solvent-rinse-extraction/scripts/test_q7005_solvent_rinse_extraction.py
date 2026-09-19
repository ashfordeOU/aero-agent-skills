#!/usr/bin/env python3
"""Contract test for the solvent rinse extraction logic (offline)."""

import copy
import unittest

from q7005_solvent_rinse_extraction_logic import (
    DEFAULT_EXTRACTION_POLICY,
    areal_contamination_ug_cm2,
    concentration_factor,
    cumulative_recovery,
    expected_residue_mass_ug,
    extract_surface_contamination,
    passes_for_target_recovery,
    rinse_volume_check,
    validate_extraction_policy,
    volume_per_area_ml_cm2,
)

BASE_CASE = {
    "per_pass_fraction": 0.6,
    "passes": 3,
    "sampled_area_cm2": 200.0,
    "rinse_volume_ml": 20.0,
    "final_volume_ml": 2.0,
    "residue_mass_ug": 120.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_extraction_policy(DEFAULT_EXTRACTION_POLICY),
            DEFAULT_EXTRACTION_POLICY,
        )

    def test_an_inverted_volume_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXTRACTION_POLICY)
        broken["min_volume_per_area_ml_cm2"] = 1.0
        with self.assertRaises(ValueError):
            validate_extraction_policy(broken)

    def test_a_recovery_floor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXTRACTION_POLICY)
        broken["min_cumulative_recovery"] = 1.2
        with self.assertRaises(ValueError):
            validate_extraction_policy(broken)

    def test_a_concentration_ceiling_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXTRACTION_POLICY)
        broken["max_concentration_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_extraction_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_extraction_policy(None)


class RecoveryTests(unittest.TestCase):
    def test_one_pass_recovers_the_per_pass_fraction(self):
        self.assertAlmostEqual(cumulative_recovery(0.6, 1), 0.6, places=9)

    def test_two_passes_leave_the_square_of_the_remainder(self):
        self.assertAlmostEqual(cumulative_recovery(0.6, 2), 1.0 - 0.4 * 0.4, places=9)

    def test_three_passes_follow_the_same_geometric_law(self):
        self.assertAlmostEqual(
            cumulative_recovery(0.5, 3), 1.0 - 0.5 * 0.5 * 0.5, places=9
        )

    def test_a_complete_per_pass_removal_finishes_in_one_pass(self):
        self.assertAlmostEqual(cumulative_recovery(1.0, 1), 1.0, places=9)

    def test_recovery_rises_with_passes_and_never_reaches_one(self):
        previous = 0.0
        for passes in range(1, 8):
            value = cumulative_recovery(0.4, passes)
            self.assertGreater(value, previous)
            self.assertLess(value, 1.0)
            previous = value

    def test_a_zero_per_pass_fraction_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_recovery(0.0, 3)

    def test_a_fractional_pass_count_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_recovery(0.6, 2.5)

    def test_a_zero_pass_count_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_recovery(0.6, 0)


class PassPlanningTests(unittest.TestCase):
    def test_the_pass_count_reaches_the_target(self):
        count = passes_for_target_recovery(0.6, 0.95)
        self.assertGreaterEqual(cumulative_recovery(0.6, count), 0.95)

    def test_the_pass_count_is_the_smallest_one_that_does(self):
        count = passes_for_target_recovery(0.6, 0.95)
        self.assertLess(cumulative_recovery(0.6, count - 1), 0.95)

    def test_a_target_landing_exactly_on_a_pass_boundary_is_not_overshot(self):
        exact = cumulative_recovery(0.5, 3)
        self.assertEqual(passes_for_target_recovery(0.5, exact), 3)

    def test_a_weaker_per_pass_removal_needs_more_passes(self):
        self.assertGreater(
            passes_for_target_recovery(0.2, 0.9),
            passes_for_target_recovery(0.8, 0.9),
        )

    def test_a_target_of_one_is_rejected_as_unreachable(self):
        with self.assertRaises(ValueError):
            passes_for_target_recovery(0.6, 1.0)

    def test_a_target_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            passes_for_target_recovery(0.6, 0.0)


class VolumeTests(unittest.TestCase):
    def test_the_ratio_is_the_volume_over_the_area(self):
        self.assertAlmostEqual(volume_per_area_ml_cm2(20.0, 200.0), 0.1, places=9)

    def test_a_sensible_rinse_is_accepted(self):
        check = rinse_volume_check(20.0, 200.0)
        self.assertTrue(check["acceptable"])
        self.assertIsNone(check["reason"])

    def test_a_ratio_exactly_on_the_floor_is_accepted(self):
        floor = DEFAULT_EXTRACTION_POLICY["min_volume_per_area_ml_cm2"]
        self.assertTrue(rinse_volume_check(floor * 200.0, 200.0)["acceptable"])

    def test_a_ratio_exactly_on_the_ceiling_is_accepted(self):
        ceiling = DEFAULT_EXTRACTION_POLICY["max_volume_per_area_ml_cm2"]
        self.assertTrue(rinse_volume_check(ceiling * 200.0, 200.0)["acceptable"])

    def test_too_little_solvent_is_rejected_with_a_wetting_reason(self):
        check = rinse_volume_check(1.0, 200.0)
        self.assertFalse(check["acceptable"])
        self.assertIn("wetting floor", check["reason"])

    def test_too_much_solvent_is_rejected_with_a_dilution_reason(self):
        check = rinse_volume_check(400.0, 200.0)
        self.assertFalse(check["acceptable"])
        self.assertIn("diluted", check["reason"])

    def test_an_area_below_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            rinse_volume_check(2.0, 5.0)

    def test_a_zero_rinse_volume_rejected(self):
        with self.assertRaises(ValueError):
            rinse_volume_check(0.0, 200.0)


class ConcentrationTests(unittest.TestCase):
    def test_the_factor_is_the_volume_ratio(self):
        self.assertAlmostEqual(concentration_factor(20.0, 2.0), 10.0, places=9)

    def test_an_unconcentrated_extract_has_a_factor_of_one(self):
        self.assertAlmostEqual(concentration_factor(20.0, 20.0), 1.0, places=9)

    def test_a_final_volume_above_the_initial_rejected(self):
        with self.assertRaises(ValueError):
            concentration_factor(2.0, 20.0)

    def test_a_zero_final_volume_rejected(self):
        with self.assertRaises(ValueError):
            concentration_factor(20.0, 0.0)


class ArealLevelTests(unittest.TestCase):
    def test_the_level_is_the_mass_over_area_and_recovery(self):
        self.assertAlmostEqual(
            areal_contamination_ug_cm2(120.0, 200.0, 0.8),
            120.0 / (200.0 * 0.8),
            places=9,
        )

    def test_a_perfect_recovery_leaves_the_level_at_mass_over_area(self):
        self.assertAlmostEqual(
            areal_contamination_ug_cm2(120.0, 200.0, 1.0), 0.6, places=9
        )

    def test_correcting_for_recovery_raises_the_reported_level(self):
        corrected = areal_contamination_ug_cm2(120.0, 200.0, 0.5)
        uncorrected = areal_contamination_ug_cm2(120.0, 200.0, 1.0)
        self.assertAlmostEqual(corrected / uncorrected, 2.0, places=9)

    def test_the_forward_and_inverse_calculations_agree(self):
        mass = expected_residue_mass_ug(0.75, 200.0, 0.8)
        self.assertAlmostEqual(
            areal_contamination_ug_cm2(mass, 200.0, 0.8), 0.75, places=9
        )

    def test_a_zero_residue_mass_rejected(self):
        with self.assertRaises(ValueError):
            areal_contamination_ug_cm2(0.0, 200.0, 0.8)

    def test_a_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            areal_contamination_ug_cm2(120.0, 200.0, 1.3)


class ExtractionTests(unittest.TestCase):
    def test_the_base_case_extraction_is_sound(self):
        result = extract_surface_contamination(BASE_CASE)
        self.assertTrue(result["extraction_sound"])
        self.assertEqual(result["findings"], [])

    def test_the_reported_level_is_the_corrected_one(self):
        result = extract_surface_contamination(BASE_CASE)
        self.assertAlmostEqual(
            result["areal_level_ug_cm2"],
            result["uncorrected_level_ug_cm2"] / result["cumulative_recovery"],
            places=9,
        )

    def test_too_few_passes_is_a_finding(self):
        result = extract_surface_contamination(_case(BASE_CASE, passes=1))
        self.assertFalse(result["extraction_sound"])
        self.assertTrue(any("recover only" in f for f in result["findings"]))

    def test_a_badly_sized_rinse_is_a_finding(self):
        result = extract_surface_contamination(
            _case(BASE_CASE, rinse_volume_ml=1.0, final_volume_ml=0.5)
        )
        self.assertTrue(any("does not suit the area" in f for f in result["findings"]))

    def test_an_over_concentrated_extract_is_a_finding(self):
        result = extract_surface_contamination(
            _case(BASE_CASE, final_volume_ml=0.1)
        )
        self.assertTrue(any("concentration factor" in f for f in result["findings"]))

    def test_a_residue_under_the_quantitation_limit_is_a_finding(self):
        result = extract_surface_contamination(
            _case(BASE_CASE, residue_mass_ug=5.0)
        )
        self.assertTrue(any("quantitation" in f for f in result["findings"]))

    def test_a_residue_exactly_on_the_quantitation_limit_is_accepted(self):
        limit = DEFAULT_EXTRACTION_POLICY["cell_quantitation_limit_ug"]
        result = extract_surface_contamination(
            _case(BASE_CASE, residue_mass_ug=limit)
        )
        self.assertFalse(any("quantitation" in f for f in result["findings"]))

    def test_every_result_carries_the_recovery_correction_duty(self):
        result = extract_surface_contamination(BASE_CASE)
        self.assertTrue(any("corrected for the" in d for d in result["duties"]))

    def test_every_result_carries_the_technique_recording_duty(self):
        result = extract_surface_contamination(BASE_CASE)
        self.assertTrue(any("pass count" in d for d in result["duties"]))

    def test_a_case_missing_the_residue_mass_rejected(self):
        case = _case(BASE_CASE)
        del case["residue_mass_ug"]
        with self.assertRaises(ValueError):
            extract_surface_contamination(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            extract_surface_contamination("rinse and weigh")


if __name__ == "__main__":
    unittest.main()
