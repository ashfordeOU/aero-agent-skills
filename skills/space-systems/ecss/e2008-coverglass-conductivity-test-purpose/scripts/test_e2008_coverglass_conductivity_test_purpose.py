"""Contract tests for the clause 6.4.3.13.1 coverglass conductivity purpose."""

import math
import unittest

from e2008_coverglass_conductivity_test_purpose_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_UNIFORMITY_POLICY,
    SURFACE_UNIFORMITY_CHARACTERISED,
    SURVEY_INADEQUATE,
    SURVEY_NOT_PLANNED,
    UNIFORMITY_NOT_REQUIRED,
    assess_coverglass_conductivity_purpose,
    behaviour_inventory,
    charge_bleed_time_constant_s,
    differential_potential_v,
    sheet_resistance_ohm_per_square,
    site_coverage_fraction,
    site_pitch_m,
    survey_objectives,
    validate_uniformity_policy,
)

BEHAVIOURS = [
    "array-differential-surface-charging",
    "array-electrostatic-discharge-initiation",
]


def _policy(**overrides):
    policy = dict(DEFAULT_UNIFORMITY_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "surface_behaviours": list(BEHAVIOURS),
        "coverglass": {
            "surface_conductivity_s_per_square": 1.0e-9,
            "area_m2": 0.0016,
            "bleed_path_length_m": 0.5,
            "area_capacitance_f_per_m2": 4.0e-7,
            "plasma_current_density_a_per_m2": 1.0e-5,
        },
        "survey": {"site_count": 9, "site_area_m2": 4.0e-6},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_uniformity_policy(DEFAULT_UNIFORMITY_POLICY),
            DEFAULT_UNIFORMITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy("uniform")

    def test_coverage_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(min_site_coverage_fraction=1.5))

    def test_zero_significant_potential_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(significant_potential_v=0.0))

    def test_fractional_minimum_site_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(min_probe_sites=4.5))


class CoatingQuantityTests(unittest.TestCase):
    def test_sheet_resistance_is_the_reciprocal_conductivity(self):
        self.assertAlmostEqual(
            _ratio(sheet_resistance_ohm_per_square(1.0e-9), 1.0e9), 1.0, places=12
        )

    def test_a_better_coating_has_a_lower_sheet_resistance(self):
        good = sheet_resistance_ohm_per_square(1.0e-7)
        poor = sheet_resistance_ohm_per_square(1.0e-9)
        self.assertLess(good, poor)

    def test_zero_conductivity_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_ohm_per_square(0.0)

    def test_boolean_conductivity_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_ohm_per_square(True)

    def test_bleed_time_constant_follows_the_sheet_rc_model(self):
        self.assertAlmostEqual(
            _ratio(charge_bleed_time_constant_s(1.0e9, 4.0e-7, 0.5), 25.0),
            1.0,
            places=12,
        )

    def test_a_longer_bleed_path_slows_the_decay_by_the_square(self):
        short_path = charge_bleed_time_constant_s(1.0e9, 4.0e-7, 0.5)
        long_path = charge_bleed_time_constant_s(1.0e9, 4.0e-7, 1.0)
        self.assertAlmostEqual(_ratio(long_path, 4.0 * short_path), 1.0, places=12)

    def test_differential_potential_follows_the_declared_model(self):
        self.assertAlmostEqual(
            _ratio(differential_potential_v(1.0e-5, 1.0e9, 0.5), 312.5),
            1.0,
            places=12,
        )

    def test_no_plasma_current_floats_no_potential(self):
        self.assertAlmostEqual(
            differential_potential_v(0.0, 1.0e9, 0.5), 0.0, places=12
        )

    def test_negative_plasma_current_density_rejected(self):
        with self.assertRaises(ValueError):
            differential_potential_v(-1.0e-5, 1.0e9, 0.5)

    def test_non_finite_area_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            charge_bleed_time_constant_s(1.0e9, float("inf"), 0.5)


class SurveyGeometryTests(unittest.TestCase):
    def test_coverage_is_the_touched_share_of_the_face(self):
        self.assertAlmostEqual(
            _ratio(site_coverage_fraction(9, 4.0e-6, 0.0016), 0.0225),
            1.0,
            places=12,
        )

    def test_more_sites_touch_more_of_the_face(self):
        few = site_coverage_fraction(9, 4.0e-6, 0.0016)
        many = site_coverage_fraction(25, 4.0e-6, 0.0016)
        self.assertLess(few, many)

    def test_sites_touching_more_than_the_face_rejected(self):
        with self.assertRaises(ValueError):
            site_coverage_fraction(9, 1.0e-3, 0.0016)

    def test_site_pitch_is_the_even_grid_spacing(self):
        self.assertAlmostEqual(
            _ratio(site_pitch_m(0.0016, 9), 0.04 / 3.0), 1.0, places=12
        )

    def test_more_sites_tighten_the_pitch(self):
        coarse = site_pitch_m(0.0016, 4)
        fine = site_pitch_m(0.0016, 36)
        self.assertLess(fine, coarse)

    def test_zero_site_count_rejected(self):
        with self.assertRaises(ValueError):
            site_pitch_m(0.0016, 0)


class ObjectiveTests(unittest.TestCase):
    def test_each_behaviour_contributes_an_objective(self):
        objectives = survey_objectives(BEHAVIOURS)
        self.assertIn("coverglass-surface-potential-gradient", objectives)
        self.assertIn("surface-charge-held-at-a-dead-patch", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = survey_objectives(BEHAVIOURS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_behaviour_yields_no_objective(self):
        self.assertEqual(survey_objectives([]), ())

    def test_a_repeated_behaviour_is_grouped_once(self):
        grouped = behaviour_inventory(
            [
                "array-frame-potential-control",
                "array-frame-potential-control",
            ]
        )
        self.assertEqual(grouped, ("array-frame-potential-control",))

    def test_unknown_behaviour_rejected(self):
        with self.assertRaises(ValueError):
            behaviour_inventory(["array-coverglass-darkening"])

    def test_non_collection_behaviour_list_rejected(self):
        with self.assertRaises(ValueError):
            behaviour_inventory("array-frame-potential-control")


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_survey_characterises_the_uniformity(self):
        result = assess_coverglass_conductivity_purpose(_case())
        self.assertEqual(result["verdict"], SURFACE_UNIFORMITY_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_derived_quantities_are_reported(self):
        result = assess_coverglass_conductivity_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["sheet_resistance_ohm_per_sq"], 1.0e9), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["differential_potential_v"], 312.5), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["charge_bleed_time_constant_s"], 25.0), 1.0, places=12
        )

    def test_no_declared_behaviour_means_no_survey_required(self):
        result = assess_coverglass_conductivity_purpose(
            _case(surface_behaviours=[])
        )
        self.assertEqual(result["verdict"], UNIFORMITY_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_well_bled_coating_does_not_earn_the_survey(self):
        case = _case()
        case["coverglass"]["surface_conductivity_s_per_square"] = 1.0e-5
        result = assess_coverglass_conductivity_purpose(case)
        self.assertEqual(result["verdict"], UNIFORMITY_NOT_REQUIRED)

    def test_a_potential_exactly_at_the_trigger_earns_the_survey(self):
        policy = _policy(significant_potential_v=312.5)
        result = assess_coverglass_conductivity_purpose(_case(), policy)
        self.assertAlmostEqual(
            result["differential_potential_v"],
            policy["significant_potential_v"],
            places=9,
        )
        self.assertTrue(result["required"])

    def test_a_required_but_unplanned_survey_is_its_own_verdict(self):
        case = _case()
        del case["survey"]
        result = assess_coverglass_conductivity_purpose(case)
        self.assertEqual(result["verdict"], SURVEY_NOT_PLANNED)
        self.assertIsNone(result["site_coverage_fraction"])

    def test_objectives_survive_an_unplanned_survey(self):
        case = _case()
        del case["survey"]
        result = assess_coverglass_conductivity_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_too_little_touched_area_is_inadequate(self):
        result = assess_coverglass_conductivity_purpose(
            _case(survey={"site_count": 9, "site_area_m2": 1.0e-7})
        )
        self.assertEqual(result["verdict"], SURVEY_INADEQUATE)
        self.assertFalse(result["coverage_adequate"])

    def test_coverage_exactly_at_the_floor_is_adequate(self):
        policy = _policy(min_site_coverage_fraction=0.0225)
        result = assess_coverglass_conductivity_purpose(_case(), policy)
        self.assertAlmostEqual(
            result["site_coverage_fraction"],
            policy["min_site_coverage_fraction"],
            places=9,
        )
        self.assertTrue(result["coverage_adequate"])

    def test_too_few_sites_is_inadequate(self):
        result = assess_coverglass_conductivity_purpose(
            _case(survey={"site_count": 2, "site_area_m2": 4.0e-5})
        )
        self.assertEqual(result["verdict"], SURVEY_INADEQUATE)
        self.assertFalse(result["site_count_adequate"])

    def test_a_pitch_wide_enough_to_straddle_a_patch_is_inadequate(self):
        policy = _policy(max_site_pitch_m=0.005, min_probe_sites=5)
        result = assess_coverglass_conductivity_purpose(_case(), policy)
        self.assertEqual(result["verdict"], SURVEY_INADEQUATE)
        self.assertFalse(result["pitch_adequate"])

    def test_a_pitch_exactly_at_the_ceiling_is_adequate(self):
        pitch = site_pitch_m(0.0016, 9)
        policy = _policy(max_site_pitch_m=pitch)
        result = assess_coverglass_conductivity_purpose(_case(), policy)
        self.assertAlmostEqual(result["site_pitch_m"], pitch, places=9)
        self.assertTrue(result["pitch_adequate"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        policy = _policy(min_probe_sites=64, min_site_coverage_fraction=0.5)
        result = assess_coverglass_conductivity_purpose(_case(), policy)
        self.assertEqual(len(result["findings"]), 2)

    def test_absent_behaviour_key_rejected(self):
        case = _case()
        del case["surface_behaviours"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_purpose(case)

    def test_missing_coverglass_block_rejected(self):
        case = _case()
        del case["coverglass"]
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_purpose(["surface_behaviours"])

    def test_non_mapping_survey_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_conductivity_purpose(_case(survey=[9]))

    def test_the_grid_pitch_matches_the_face_and_site_count(self):
        result = assess_coverglass_conductivity_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["site_pitch_m"], math.sqrt(0.0016 / 9.0)),
            1.0,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
