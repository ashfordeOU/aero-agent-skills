#!/usr/bin/env python3
"""Contract test for sealed-anodize corrosion resistance (offline)."""

import copy
import unittest

from q7003_corrosion_resistance_verification_logic import (
    DEFAULT_ATTACK_LIMITS,
    DEFAULT_SEAL_LIMITS,
    OUTCOME_FAIL,
    OUTCOME_INCONCLUSIVE,
    OUTCOME_PASS,
    REFERENCE_THICKNESS_UM,
    SEAL_GRADES,
    attack_density_per_dm2,
    evaluate_attack,
    exposure_is_sufficient,
    grade_seal,
    normalised_admittance_us,
    validate_seal_limits,
    verify_corrosion_resistance,
)

GOOD_CASE = {
    "seal_admittance_us": 12.0,
    "thickness_um": 20.0,
    "exposure_hours": 336.0,
    "required_exposure_hours": 336.0,
    "site_count": 0,
    "exposed_area_mm2": 10000.0,
    "largest_site_mm": 0.0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class SealLimitTests(unittest.TestCase):
    def test_default_limits_validate(self):
        self.assertIs(validate_seal_limits(DEFAULT_SEAL_LIMITS), DEFAULT_SEAL_LIMITS)

    def test_inverted_limits_rejected(self):
        broken = dict(DEFAULT_SEAL_LIMITS, marginal_max_us=5.0)
        with self.assertRaises(ValueError):
            validate_seal_limits(broken)

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_seal_limits("default")

    def test_missing_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_seal_limits({"well_sealed_max_us": 20.0})


class NormalisationTests(unittest.TestCase):
    def test_reference_thickness_leaves_the_reading_unchanged(self):
        self.assertAlmostEqual(
            normalised_admittance_us(15.0, REFERENCE_THICKNESS_UM), 15.0, places=9
        )

    def test_a_thicker_coating_is_credited(self):
        thick = normalised_admittance_us(20.0, 40.0)
        self.assertAlmostEqual(thick, 10.0, places=9)

    def test_a_thinner_coating_is_penalised(self):
        thin = normalised_admittance_us(20.0, 10.0)
        self.assertAlmostEqual(thin, 40.0, places=9)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            normalised_admittance_us(15.0, 0.0)

    def test_negative_admittance_rejected(self):
        with self.assertRaises(ValueError):
            normalised_admittance_us(-1.0, 20.0)


class SealGradeTests(unittest.TestCase):
    def test_low_admittance_is_well_sealed(self):
        result = grade_seal(8.0, 20.0)
        self.assertEqual(result["grade"], "well-sealed")
        self.assertEqual(result["findings"], [])

    def test_admittance_exactly_on_the_sealed_limit_is_well_sealed(self):
        result = grade_seal(20.0, 20.0)
        self.assertAlmostEqual(result["normalised_admittance_us"], 20.0, places=9)
        self.assertEqual(result["grade"], "well-sealed")

    def test_mid_admittance_is_marginal(self):
        result = grade_seal(30.0, 20.0)
        self.assertEqual(result["grade"], "marginally-sealed")
        self.assertTrue(any("dwell" in f for f in result["findings"]))

    def test_high_admittance_is_unsealed(self):
        result = grade_seal(80.0, 20.0)
        self.assertEqual(result["grade"], "unsealed")
        self.assertTrue(result["findings"])

    def test_thickness_moves_the_grade(self):
        thin = grade_seal(30.0, 10.0)["grade"]
        thick = grade_seal(30.0, 40.0)["grade"]
        self.assertEqual(thin, "unsealed")
        self.assertEqual(thick, "well-sealed")

    def test_every_grade_is_reachable(self):
        grades = {
            grade_seal(5.0, 20.0)["grade"],
            grade_seal(30.0, 20.0)["grade"],
            grade_seal(90.0, 20.0)["grade"],
        }
        self.assertEqual(grades, set(SEAL_GRADES))


class AttackTests(unittest.TestCase):
    def test_density_is_per_square_decimetre(self):
        self.assertAlmostEqual(
            attack_density_per_dm2(3, 10000.0), 3.0, places=9
        )

    def test_clean_coupon_passes(self):
        result = evaluate_attack(0, 10000.0)
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertEqual(result["findings"], [])

    def test_density_exactly_on_the_allowance_passes(self):
        result = evaluate_attack(2, 10000.0, largest_site_mm=0.5)
        self.assertAlmostEqual(result["density_per_dm2"], 2.0, places=9)
        self.assertEqual(result["outcome"], OUTCOME_PASS)

    def test_too_many_sites_fail(self):
        result = evaluate_attack(9, 10000.0, largest_site_mm=0.2)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertFalse(result["density_acceptable"])

    def test_one_oversize_site_fails_an_acceptable_count(self):
        result = evaluate_attack(1, 10000.0, largest_site_mm=2.5)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertTrue(result["density_acceptable"])
        self.assertFalse(result["size_acceptable"])

    def test_site_size_without_a_site_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attack(0, 10000.0, largest_site_mm=0.4)

    def test_non_integer_site_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attack(2.5, 10000.0)

    def test_negative_site_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attack(-1, 10000.0)

    def test_zero_exposed_area_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attack(1, 0.0, largest_site_mm=0.1)

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_attack(1, 10000.0, largest_site_mm=0.1, limits=None)


class ExposureTests(unittest.TestCase):
    def test_full_duration_is_sufficient(self):
        self.assertTrue(exposure_is_sufficient(336.0, 336.0))

    def test_longer_exposure_is_sufficient(self):
        self.assertTrue(exposure_is_sufficient(400.0, 336.0))

    def test_short_exposure_is_not(self):
        self.assertFalse(exposure_is_sufficient(300.0, 336.0))

    def test_zero_required_duration_rejected(self):
        with self.assertRaises(ValueError):
            exposure_is_sufficient(336.0, 0.0)

    def test_negative_actual_duration_rejected(self):
        with self.assertRaises(ValueError):
            exposure_is_sufficient(-1.0, 336.0)


class VerifyTests(unittest.TestCase):
    def test_good_coupon_passes(self):
        result = verify_corrosion_resistance(GOOD_CASE)
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertTrue(result["exposure_sufficient"])
        self.assertEqual(result["findings"], [])

    def test_short_exposure_is_inconclusive_not_a_pass(self):
        result = verify_corrosion_resistance(_case(exposure_hours=100.0))
        self.assertEqual(result["outcome"], OUTCOME_INCONCLUSIVE)
        self.assertIsNone(result["attack"])
        self.assertTrue(any("short of" in f for f in result["findings"]))

    def test_short_exposure_is_not_reported_as_a_failure(self):
        result = verify_corrosion_resistance(_case(exposure_hours=10.0, site_count=20))
        self.assertNotEqual(result["outcome"], OUTCOME_FAIL)

    def test_attack_beyond_the_allowance_fails(self):
        result = verify_corrosion_resistance(
            _case(site_count=12, largest_site_mm=0.3)
        )
        self.assertEqual(result["outcome"], OUTCOME_FAIL)

    def test_an_unsealed_coating_fails_even_with_a_clean_coupon(self):
        result = verify_corrosion_resistance(_case(seal_admittance_us=120.0))
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertEqual(result["seal"]["grade"], "unsealed")
        self.assertTrue(any("does not carry" in f for f in result["findings"]))

    def test_a_marginal_seal_with_a_clean_coupon_still_passes_with_a_finding(self):
        result = verify_corrosion_resistance(_case(seal_admittance_us=30.0))
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertEqual(result["seal"]["grade"], "marginally-sealed")
        self.assertTrue(result["findings"])

    def test_custom_attack_limits_are_honoured(self):
        strict = dict(DEFAULT_ATTACK_LIMITS, max_sites_per_dm2=0.0)
        result = verify_corrosion_resistance(
            _case(site_count=1, largest_site_mm=0.1), attack_limits=strict
        )
        self.assertEqual(result["outcome"], OUTCOME_FAIL)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            verify_corrosion_resistance("sealed and fine")

    def test_missing_thickness_rejected(self):
        case = _case()
        del case["thickness_um"]
        with self.assertRaises(ValueError):
            verify_corrosion_resistance(case)

    def test_missing_required_duration_rejected(self):
        case = _case()
        del case["required_exposure_hours"]
        with self.assertRaises(ValueError):
            verify_corrosion_resistance(case)


if __name__ == "__main__":
    unittest.main()
