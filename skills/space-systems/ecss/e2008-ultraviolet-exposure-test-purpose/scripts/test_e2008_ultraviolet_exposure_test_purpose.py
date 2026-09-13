"""Contract tests for the clause 6.4.3.15.1 ultraviolet exposure purpose logic."""

import unittest

from e2008_ultraviolet_exposure_test_purpose_logic import (
    ACCELERATED_EXPOSURE_INADEQUATE,
    ACCELERATED_EXPOSURE_NOT_PLANNED,
    COMMON_OBJECTIVE,
    DEFAULT_ULTRAVIOLET_POLICY,
    HOURS_PER_YEAR,
    ULTRAVIOLET_STABILITY_CHARACTERISED,
    ULTRAVIOLET_STABILITY_NOT_REQUIRED,
    acceleration_factor,
    accumulated_equivalent_sun_hours,
    assess_ultraviolet_exposure_purpose,
    dose_coverage_ratio,
    element_inventory,
    mission_equivalent_sun_hours,
    reciprocity_holds,
    required_exposure_hours,
    stability_objectives,
    validate_ultraviolet_policy,
)

ELEMENTS = [
    "coverglass-adhesive",
    "polyimide-substrate",
]

MISSION_ESH = 5.0 * HOURS_PER_YEAR * 0.6


def _policy(**overrides):
    policy = dict(DEFAULT_ULTRAVIOLET_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "ultraviolet_sensitive_elements": list(ELEMENTS),
        "mission": {
            "mission_years": 5.0,
            "solar_distance_au": 1.0,
            "illuminated_fraction": 0.6,
        },
        "exposure": {"test_irradiance_w_m2": 590.0, "duration_h": 5259.6},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_ultraviolet_policy(DEFAULT_ULTRAVIOLET_POLICY),
            DEFAULT_ULTRAVIOLET_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy("ten suns")

    def test_zero_significance_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(significance_trigger_esh=0.0))

    def test_acceleration_ceiling_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(max_acceleration_factor=0.5))

    def test_zero_ultraviolet_sun_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(ultraviolet_sun_irradiance_w_m2=0.0))

    def test_zero_facility_duration_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(max_exposure_duration_h=0.0))


class MissionDoseTests(unittest.TestCase):
    def test_dose_is_illuminated_hours_at_one_astronomical_unit(self):
        self.assertAlmostEqual(
            _ratio(mission_equivalent_sun_hours(5.0, 1.0, 0.6), MISSION_ESH),
            1.0,
            places=12,
        )

    def test_a_fully_illuminated_mission_sees_every_hour(self):
        self.assertAlmostEqual(
            _ratio(mission_equivalent_sun_hours(1.0, 1.0, 1.0), HOURS_PER_YEAR),
            1.0,
            places=12,
        )

    def test_dose_falls_with_the_square_of_the_solar_distance(self):
        near = mission_equivalent_sun_hours(5.0, 1.0, 1.0)
        far = mission_equivalent_sun_hours(5.0, 2.0, 1.0)
        self.assertAlmostEqual(_ratio(near, 4.0 * far), 1.0, places=12)

    def test_the_illuminated_fraction_scales_the_dose_linearly(self):
        full = mission_equivalent_sun_hours(5.0, 1.0, 1.0)
        half = mission_equivalent_sun_hours(5.0, 1.0, 0.5)
        self.assertAlmostEqual(_ratio(full, 2.0 * half), 1.0, places=12)

    def test_zero_mission_years_rejected(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours(0.0, 1.0, 1.0)

    def test_illuminated_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours(5.0, 1.0, 1.4)

    def test_negative_solar_distance_rejected(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours(5.0, -1.0, 1.0)

    def test_boolean_mission_years_rejected(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours(True, 1.0, 1.0)


class AccelerationTests(unittest.TestCase):
    def test_acceleration_is_the_irradiance_in_ultraviolet_suns(self):
        self.assertAlmostEqual(
            _ratio(acceleration_factor(590.0, None, _policy()), 5.0), 1.0, places=12
        )

    def test_an_explicit_one_sun_value_overrides_the_policy(self):
        self.assertAlmostEqual(
            _ratio(acceleration_factor(590.0, 59.0, _policy()), 10.0), 1.0, places=12
        )

    def test_required_hours_is_the_target_dose_over_the_acceleration(self):
        self.assertAlmostEqual(
            _ratio(required_exposure_hours(26298.0, 5.0), 5259.6), 1.0, places=12
        )

    def test_accumulated_dose_is_irradiance_times_hours_in_suns(self):
        self.assertAlmostEqual(
            _ratio(
                accumulated_equivalent_sun_hours(590.0, 1000.0, _policy()), 5000.0
            ),
            1.0,
            places=12,
        )

    def test_coverage_ratio_compares_the_run_with_the_mission(self):
        self.assertAlmostEqual(
            _ratio(dose_coverage_ratio(13149.0, 26298.0), 0.5), 1.0, places=12
        )

    def test_a_factor_exactly_at_the_ceiling_still_holds_reciprocity(self):
        policy = _policy(max_acceleration_factor=5.0)
        factor = acceleration_factor(590.0, None, policy)
        self.assertAlmostEqual(factor, policy["max_acceleration_factor"], places=9)
        self.assertTrue(reciprocity_holds(factor, policy))

    def test_a_factor_above_the_ceiling_breaks_reciprocity(self):
        self.assertFalse(reciprocity_holds(20.0, _policy()))

    def test_zero_exposure_duration_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_equivalent_sun_hours(590.0, 0.0, _policy())

    def test_zero_acceleration_rejected_by_required_hours(self):
        with self.assertRaises(ValueError):
            required_exposure_hours(26298.0, 0.0)


class InventoryTests(unittest.TestCase):
    def test_each_element_contributes_an_objective(self):
        objectives = stability_objectives(ELEMENTS)
        self.assertIn("adhesive-transmission-darkening", objectives)
        self.assertIn("polyimide-embrittlement-and-darkening", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = stability_objectives(ELEMENTS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_element_yields_no_objective(self):
        self.assertEqual(stability_objectives([]), ())

    def test_a_repeated_element_is_grouped_once(self):
        grouped = element_inventory(["coverglass-adhesive", "coverglass-adhesive"])
        self.assertEqual(grouped, ("coverglass-adhesive",))

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            element_inventory(["aluminium-honeycomb-core"])

    def test_non_collection_element_list_rejected(self):
        with self.assertRaises(ValueError):
            element_inventory("coverglass-adhesive")


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_exposure_characterises_the_stability(self):
        result = assess_ultraviolet_exposure_purpose(_case())
        self.assertEqual(result["verdict"], ULTRAVIOLET_STABILITY_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_mission_dose_is_reported(self):
        result = assess_ultraviolet_exposure_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["mission_equivalent_sun_hours"], MISSION_ESH),
            1.0,
            places=12,
        )

    def test_the_planned_run_covers_the_mission_dose(self):
        result = assess_ultraviolet_exposure_purpose(_case())
        self.assertAlmostEqual(result["dose_coverage_ratio"], 1.0, places=9)

    def test_the_acceleration_factor_is_reported(self):
        result = assess_ultraviolet_exposure_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["acceleration_factor"], 5.0), 1.0, places=12
        )

    def test_no_declared_element_means_no_exposure_required(self):
        result = assess_ultraviolet_exposure_purpose(
            _case(ultraviolet_sensitive_elements=[])
        )
        self.assertEqual(result["verdict"], ULTRAVIOLET_STABILITY_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_negligible_mission_dose_does_not_earn_the_exposure(self):
        case = _case()
        case["mission"]["mission_years"] = 0.001
        result = assess_ultraviolet_exposure_purpose(case)
        self.assertEqual(result["verdict"], ULTRAVIOLET_STABILITY_NOT_REQUIRED)

    def test_a_dose_exactly_at_the_trigger_earns_the_exposure(self):
        policy = _policy(significance_trigger_esh=MISSION_ESH)
        result = assess_ultraviolet_exposure_purpose(_case(), policy)
        self.assertAlmostEqual(
            _ratio(
                result["mission_equivalent_sun_hours"],
                policy["significance_trigger_esh"],
            ),
            1.0,
            places=12,
        )
        self.assertTrue(result["required"])

    def test_a_required_but_unplanned_exposure_is_its_own_verdict(self):
        case = _case()
        del case["exposure"]
        result = assess_ultraviolet_exposure_purpose(case)
        self.assertEqual(result["verdict"], ACCELERATED_EXPOSURE_NOT_PLANNED)
        self.assertIsNone(result["acceleration_factor"])

    def test_an_over_accelerated_run_is_inadequate(self):
        result = assess_ultraviolet_exposure_purpose(
            _case(exposure={"test_irradiance_w_m2": 2360.0, "duration_h": 1314.9})
        )
        self.assertEqual(result["verdict"], ACCELERATED_EXPOSURE_INADEQUATE)
        self.assertFalse(result["reciprocity_holds"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_run_short_of_the_mission_dose_is_inadequate(self):
        result = assess_ultraviolet_exposure_purpose(
            _case(exposure={"test_irradiance_w_m2": 590.0, "duration_h": 1000.0})
        )
        self.assertEqual(result["verdict"], ACCELERATED_EXPOSURE_INADEQUATE)
        self.assertTrue(result["reciprocity_holds"])
        self.assertEqual(len(result["findings"]), 1)

    def test_both_inadequacies_are_reported_not_only_the_first(self):
        result = assess_ultraviolet_exposure_purpose(
            _case(exposure={"test_irradiance_w_m2": 2360.0, "duration_h": 100.0})
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_a_run_past_the_facility_duration_limit_is_inadequate(self):
        result = assess_ultraviolet_exposure_purpose(
            _case(exposure={"test_irradiance_w_m2": 354.0, "duration_h": 10000.0})
        )
        self.assertEqual(result["verdict"], ACCELERATED_EXPOSURE_INADEQUATE)
        self.assertTrue(result["reciprocity_holds"])
        self.assertEqual(len(result["findings"]), 1)

    def test_objectives_survive_an_unplanned_exposure(self):
        case = _case()
        del case["exposure"]
        result = assess_ultraviolet_exposure_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_element_key_rejected(self):
        case = _case()
        del case["ultraviolet_sensitive_elements"]
        with self.assertRaises(ValueError):
            assess_ultraviolet_exposure_purpose(case)

    def test_missing_mission_block_rejected(self):
        case = _case()
        del case["mission"]
        with self.assertRaises(ValueError):
            assess_ultraviolet_exposure_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_ultraviolet_exposure_purpose(["coverglass-adhesive"])

    def test_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            assess_ultraviolet_exposure_purpose(_case(exposure=[590.0, 5259.6]))


if __name__ == "__main__":
    unittest.main()
