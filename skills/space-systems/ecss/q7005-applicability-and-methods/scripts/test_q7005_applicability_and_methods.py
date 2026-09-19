#!/usr/bin/env python3
"""Contract test for the IR contamination applicability logic (offline)."""

import copy
import unittest

from q7005_applicability_and_methods_logic import (
    DEFAULT_APPLICABILITY_POLICY,
    DIRECT_FAMILY,
    FLIGHT_SURFACE,
    INDIRECT_FAMILY,
    METHOD_FAMILIES,
    WITNESS_PLATE,
    admissible_method_families,
    assess_applicability,
    band_within_instrument_range,
    direct_method_detection_limit,
    indirect_method_detection_limit,
    screen_contaminant,
    validate_applicability_policy,
    witness_plate_representativeness,
)

CONTAMINANT = {"organic": True, "diagnostic_band_cm_1": 1730.0}

BASE_CASE = {
    "contaminant": CONTAMINANT,
    "sampling_object": FLIGHT_SURFACE,
    "required_level_ug_cm2": 1.0,
    "specific_absorbance_per_ug_cm2": 0.01,
    "reflection_passes": 1,
    "sampled_area_cm2": 100.0,
    "recovery_fraction": 0.8,
}

WITNESS_CASE = dict(
    BASE_CASE,
    sampling_object=WITNESS_PLATE,
    exposure_ratio=1.0,
    view_factor_ratio=0.8,
    accommodation_ratio=1.0,
)


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_applicability_policy(DEFAULT_APPLICABILITY_POLICY),
            DEFAULT_APPLICABILITY_POLICY,
        )

    def test_an_inverted_instrument_range_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["instrument_low_cm_1"] = 5000.0
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_a_represented_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["min_represented_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_a_zero_absorbance_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_APPLICABILITY_POLICY)
        broken["absorbance_detection_limit"] = 0.0
        with self.assertRaises(ValueError):
            validate_applicability_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicability_policy(["default"])


class BandTests(unittest.TestCase):
    def test_a_carbonyl_band_sits_inside_the_range(self):
        self.assertTrue(band_within_instrument_range(1730.0))

    def test_a_band_exactly_on_the_low_edge_is_inside(self):
        self.assertTrue(
            band_within_instrument_range(
                DEFAULT_APPLICABILITY_POLICY["instrument_low_cm_1"]
            )
        )

    def test_a_band_exactly_on_the_high_edge_is_inside(self):
        self.assertTrue(
            band_within_instrument_range(
                DEFAULT_APPLICABILITY_POLICY["instrument_high_cm_1"]
            )
        )

    def test_a_far_infrared_band_falls_outside(self):
        self.assertFalse(band_within_instrument_range(150.0))

    def test_a_zero_band_rejected(self):
        with self.assertRaises(ValueError):
            band_within_instrument_range(0.0)


class ScreeningTests(unittest.TestCase):
    def test_an_organic_in_band_contaminant_is_in_scope(self):
        result = screen_contaminant(CONTAMINANT)
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["reasons"], [])

    def test_an_inorganic_contaminant_is_out_of_scope(self):
        result = screen_contaminant(dict(CONTAMINANT, organic=False))
        self.assertFalse(result["in_scope"])
        self.assertTrue(any("not organic" in r for r in result["reasons"]))

    def test_an_out_of_range_band_is_out_of_scope(self):
        result = screen_contaminant(
            dict(CONTAMINANT, diagnostic_band_cm_1=120.0)
        )
        self.assertFalse(result["in_scope"])
        self.assertTrue(any("outside the instrument" in r for r in result["reasons"]))

    def test_both_failures_are_reported_together(self):
        result = screen_contaminant(
            {"organic": False, "diagnostic_band_cm_1": 120.0}
        )
        self.assertEqual(len(result["reasons"]), 2)

    def test_an_unstated_organic_flag_is_refused_not_defaulted(self):
        with self.assertRaises(ValueError):
            screen_contaminant({"diagnostic_band_cm_1": 1730.0})

    def test_a_non_boolean_organic_flag_rejected(self):
        with self.assertRaises(ValueError):
            screen_contaminant({"organic": "yes", "diagnostic_band_cm_1": 1730.0})

    def test_a_missing_band_rejected(self):
        with self.assertRaises(ValueError):
            screen_contaminant({"organic": True})


class RepresentativenessTests(unittest.TestCase):
    def test_a_perfect_plate_represents_the_whole_surface(self):
        result = witness_plate_representativeness(1.0, 1.0, 1.0)
        self.assertAlmostEqual(result["represented_fraction"], 1.0, places=9)
        self.assertAlmostEqual(result["scale_to_flight_surface"], 1.0, places=9)

    def test_the_three_ratios_multiply(self):
        result = witness_plate_representativeness(0.5, 0.5, 1.0)
        self.assertAlmostEqual(result["represented_fraction"], 0.25, places=9)

    def test_the_scaling_is_the_reciprocal_of_the_fraction(self):
        result = witness_plate_representativeness(0.5, 0.5, 1.0)
        self.assertAlmostEqual(
            result["represented_fraction"] * result["scale_to_flight_surface"],
            1.0,
            places=9,
        )

    def test_a_zero_exposure_ratio_rejected(self):
        with self.assertRaises(ValueError):
            witness_plate_representativeness(0.0, 1.0, 1.0)

    def test_a_ratio_above_one_rejected(self):
        with self.assertRaises(ValueError):
            witness_plate_representativeness(1.0, 1.2, 1.0)


class DetectionLimitTests(unittest.TestCase):
    def test_the_direct_limit_is_the_absorbance_limit_over_the_absorbance(self):
        expected = DEFAULT_APPLICABILITY_POLICY["absorbance_detection_limit"] / 0.01
        self.assertAlmostEqual(
            direct_method_detection_limit(0.01), expected, places=9
        )

    def test_extra_reflection_passes_lower_the_direct_limit(self):
        single = direct_method_detection_limit(0.01, 1)
        quadruple = direct_method_detection_limit(0.01, 4)
        self.assertAlmostEqual(single / quadruple, 4.0, places=9)

    def test_a_zero_specific_absorbance_rejected(self):
        with self.assertRaises(ValueError):
            direct_method_detection_limit(0.0)

    def test_a_fractional_pass_count_rejected(self):
        with self.assertRaises(ValueError):
            direct_method_detection_limit(0.01, 2.5)

    def test_the_indirect_limit_spreads_the_cell_limit_over_the_area(self):
        expected = DEFAULT_APPLICABILITY_POLICY[
            "cell_mass_detection_limit_ug"
        ] / (100.0 * 0.8)
        self.assertAlmostEqual(
            indirect_method_detection_limit(100.0, 0.8), expected, places=9
        )

    def test_a_larger_sampled_area_lowers_the_indirect_limit(self):
        small = indirect_method_detection_limit(100.0, 0.8)
        large = indirect_method_detection_limit(400.0, 0.8)
        self.assertAlmostEqual(small / large, 4.0, places=9)

    def test_an_area_exactly_on_the_policy_floor_is_accepted(self):
        floor = DEFAULT_APPLICABILITY_POLICY["min_sampled_area_cm2"]
        self.assertGreater(indirect_method_detection_limit(floor, 1.0), 0.0)

    def test_an_area_below_the_policy_floor_rejected(self):
        with self.assertRaises(ValueError):
            indirect_method_detection_limit(1.0, 0.8)

    def test_a_recovery_above_one_rejected(self):
        with self.assertRaises(ValueError):
            indirect_method_detection_limit(100.0, 1.4)


class AdmissibilityTests(unittest.TestCase):
    def test_both_families_reach_a_loose_requirement(self):
        result = admissible_method_families(BASE_CASE)
        self.assertEqual(set(result["admitted"]), set(METHOD_FAMILIES))
        self.assertEqual(result["excluded"], {})

    def test_a_tight_requirement_excludes_the_less_sensitive_family(self):
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=0.15)
        )
        self.assertIn(INDIRECT_FAMILY, result["admitted"])
        self.assertIn(DIRECT_FAMILY, result["excluded"])

    def test_more_reflection_passes_bring_the_direct_family_back(self):
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=0.15, reflection_passes=4)
        )
        self.assertIn(DIRECT_FAMILY, result["admitted"])

    def test_a_small_sampled_area_can_cost_the_indirect_family_its_place(self):
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=0.15, sampled_area_cm2=30.0)
        )
        self.assertIn(INDIRECT_FAMILY, result["excluded"])

    def test_a_requirement_exactly_on_a_limit_admits_that_family(self):
        limit = direct_method_detection_limit(0.01, 1)
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=limit)
        )
        self.assertIn(DIRECT_FAMILY, result["admitted"])

    def test_an_impossible_requirement_admits_nothing(self):
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=1.0e-9)
        )
        self.assertEqual(result["admitted"], ())
        self.assertEqual(len(result["excluded"]), len(METHOD_FAMILIES))

    def test_an_exclusion_carries_its_reason(self):
        result = admissible_method_families(
            _case(BASE_CASE, required_level_ug_cm2=1.0e-9)
        )
        for reason in result["excluded"].values():
            self.assertIn("does not reach", reason)

    def test_a_zero_required_level_rejected(self):
        with self.assertRaises(ValueError):
            admissible_method_families(_case(BASE_CASE, required_level_ug_cm2=0.0))


class AssessmentTests(unittest.TestCase):
    def test_the_base_case_is_applicable(self):
        result = assess_applicability(BASE_CASE)
        self.assertTrue(result["applicable"])
        self.assertEqual(result["findings"], [])

    def test_a_flight_surface_case_needs_no_representativeness(self):
        result = assess_applicability(BASE_CASE)
        self.assertIsNone(result["representativeness"])
        self.assertTrue(any("flight surface itself" in d for d in result["duties"]))

    def test_a_witness_plate_case_carries_a_scaling_duty(self):
        result = assess_applicability(WITNESS_CASE)
        self.assertIsNotNone(result["representativeness"])
        self.assertTrue(any("scale the witness-plate" in d for d in result["duties"]))

    def test_an_unrepresentative_plate_is_a_finding(self):
        result = assess_applicability(
            _case(WITNESS_CASE, exposure_ratio=0.1, view_factor_ratio=0.5)
        )
        self.assertFalse(result["findings"] == [])
        self.assertTrue(any("represents only" in f for f in result["findings"]))

    def test_a_plate_exactly_on_the_minimum_fraction_is_accepted(self):
        minimum = DEFAULT_APPLICABILITY_POLICY["min_represented_fraction"]
        result = assess_applicability(
            _case(
                WITNESS_CASE,
                exposure_ratio=minimum,
                view_factor_ratio=1.0,
                accommodation_ratio=1.0,
            )
        )
        self.assertFalse(any("represents only" in f for f in result["findings"]))

    def test_an_inorganic_contaminant_makes_the_case_inapplicable(self):
        result = assess_applicability(
            _case(BASE_CASE, contaminant=dict(CONTAMINANT, organic=False))
        )
        self.assertFalse(result["applicable"])

    def test_an_unreachable_requirement_makes_the_case_inapplicable(self):
        result = assess_applicability(
            _case(BASE_CASE, required_level_ug_cm2=1.0e-9)
        )
        self.assertFalse(result["applicable"])
        self.assertTrue(any("no method family" in f for f in result["findings"]))

    def test_every_assessment_carries_the_diagnostic_band_duty(self):
        result = assess_applicability(BASE_CASE)
        self.assertTrue(any("diagnostic band" in d for d in result["duties"]))

    def test_an_unknown_sampling_object_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability(_case(BASE_CASE, sampling_object="coupon"))

    def test_a_witness_case_without_its_ratios_rejected(self):
        case = _case(WITNESS_CASE)
        del case["view_factor_ratio"]
        with self.assertRaises(ValueError):
            assess_applicability(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_applicability("wipe it and look")


if __name__ == "__main__":
    unittest.main()
