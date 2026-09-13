"""Contract tests for the clause 6.4.3.15.4 mission ultraviolet testing logic."""

import math
import unittest

from e2008_mission_specific_ultraviolet_tests_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_ULTRAVIOLET_POLICY,
    EXPOSURE_DEMONSTRATED,
    EXTRA_TESTING_NOT_REQUIRED,
    TEST_INADEQUATE,
    TEST_NOT_PLANNED,
    absorptance_increase,
    acceleration_factor,
    accelerated_test_duration_h,
    assess_mission_specific_ultraviolet_tests,
    extra_testing_required,
    extra_testing_threshold_esh,
    mission_equivalent_sun_hours,
    mission_illuminated_hours,
    mission_mean_intensity_suns,
    phase_equivalent_sun_hours,
    planned_equivalent_sun_hours,
    profile_inventory,
    solar_intensity_suns,
    ultraviolet_objectives,
    validate_ultraviolet_policy,
)

PROFILES = [
    "near-sun-science-flyby",
    "inner-planetary-cruise",
]

PHASES = [
    {"heliocentric_distance_au": 0.5, "duration_h": 4000.0,
     "illuminated_fraction": 1.0},
    {"heliocentric_distance_au": 1.0, "duration_h": 8000.0,
     "illuminated_fraction": 0.75},
]


def _policy(**overrides):
    policy = dict(DEFAULT_ULTRAVIOLET_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "mission_profiles": list(PROFILES),
        "mission": {
            "phases": [dict(phase) for phase in PHASES],
            "operating_temperature_c": 120.0,
            "saturation_absorptance_increase": 0.06,
            "characteristic_esh": 5000.0,
        },
        "test": {
            "intensity_suns": 5.0,
            "duration_h": 4400.0,
            "sample_temperature_c": 125.0,
        },
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
            validate_ultraviolet_policy("standard-exposure")

    def test_margin_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(extra_test_margin=0.5))

    def test_acceleration_bound_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(max_acceleration_factor=0.9))

    def test_zero_standard_exposure_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(_policy(standard_qualification_esh=0.0))

    def test_negative_temperature_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_ultraviolet_policy(
                _policy(max_sample_temperature_offset_c=-1.0)
            )


class IntensityTests(unittest.TestCase):
    def test_one_astronomical_unit_is_one_sun(self):
        self.assertAlmostEqual(solar_intensity_suns(1.0), 1.0, places=12)

    def test_half_an_astronomical_unit_is_four_suns(self):
        self.assertAlmostEqual(solar_intensity_suns(0.5), 4.0, places=12)

    def test_intensity_falls_with_the_square_of_the_distance(self):
        near = solar_intensity_suns(0.25)
        far = solar_intensity_suns(0.5)
        self.assertAlmostEqual(_ratio(near, 4.0 * far), 1.0, places=12)

    def test_zero_distance_rejected(self):
        with self.assertRaises(ValueError):
            solar_intensity_suns(0.0)

    def test_boolean_distance_rejected(self):
        with self.assertRaises(ValueError):
            solar_intensity_suns(True)


class ExposureBudgetTests(unittest.TestCase):
    def test_a_phase_multiplies_intensity_hours_and_illuminated_fraction(self):
        self.assertAlmostEqual(
            _ratio(phase_equivalent_sun_hours(PHASES[0]), 16000.0), 1.0, places=12
        )

    def test_an_eclipsed_phase_contributes_only_its_lit_share(self):
        self.assertAlmostEqual(
            _ratio(phase_equivalent_sun_hours(PHASES[1]), 6000.0), 1.0, places=12
        )

    def test_the_mission_budget_sums_every_phase(self):
        self.assertAlmostEqual(
            _ratio(mission_equivalent_sun_hours(PHASES), 22000.0), 1.0, places=12
        )

    def test_illuminated_hours_ignore_the_intensity(self):
        self.assertAlmostEqual(
            _ratio(mission_illuminated_hours(PHASES), 10000.0), 1.0, places=12
        )

    def test_the_mean_intensity_is_dose_weighted(self):
        self.assertAlmostEqual(
            _ratio(mission_mean_intensity_suns(PHASES), 2.2), 1.0, places=12
        )

    def test_an_empty_phase_list_is_rejected_not_treated_as_zero(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours([])

    def test_an_illuminated_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            phase_equivalent_sun_hours(
                {"heliocentric_distance_au": 1.0, "duration_h": 10.0,
                 "illuminated_fraction": 1.5}
            )

    def test_a_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            mission_equivalent_sun_hours([(0.5, 4000.0, 1.0)])


class ThresholdTests(unittest.TestCase):
    def test_the_threshold_is_the_standard_exposure_times_the_margin(self):
        policy = _policy(standard_qualification_esh=1000.0, extra_test_margin=2.0)
        self.assertAlmostEqual(
            _ratio(extra_testing_threshold_esh(policy), 2000.0), 1.0, places=12
        )

    def test_an_exposure_exactly_at_the_threshold_earns_the_extra_testing(self):
        policy = _policy(standard_qualification_esh=2000.0, extra_test_margin=1.0)
        self.assertAlmostEqual(
            extra_testing_threshold_esh(policy), 2000.0, places=9
        )
        self.assertTrue(extra_testing_required(2000.0, policy))

    def test_an_exposure_below_the_threshold_does_not(self):
        self.assertFalse(extra_testing_required(10.0, _policy()))

    def test_a_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            extra_testing_required(-1.0, _policy())


class AccelerationTests(unittest.TestCase):
    def test_acceleration_is_lamp_over_mission_mean(self):
        self.assertAlmostEqual(
            _ratio(acceleration_factor(5.0, 2.5), 2.0), 1.0, places=12
        )

    def test_lamp_hours_fall_as_the_lamp_is_driven_harder(self):
        slow = accelerated_test_duration_h(22000.0, 2.0)
        fast = accelerated_test_duration_h(22000.0, 10.0)
        self.assertAlmostEqual(_ratio(slow, 5.0 * fast), 1.0, places=12)

    def test_planned_exposure_is_lamp_intensity_times_lamp_hours(self):
        self.assertAlmostEqual(
            _ratio(planned_equivalent_sun_hours(5.0, 4400.0), 22000.0),
            1.0,
            places=12,
        )

    def test_zero_mission_mean_intensity_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(5.0, 0.0)

    def test_zero_lamp_hours_rejected(self):
        with self.assertRaises(ValueError):
            planned_equivalent_sun_hours(5.0, 0.0)


class DarkeningTests(unittest.TestCase):
    def test_no_exposure_produces_no_darkening(self):
        self.assertAlmostEqual(absorptance_increase(0.0, 0.06, 5000.0), 0.0,
                               places=12)

    def test_one_characteristic_dose_reaches_the_expected_fraction(self):
        expected = 0.06 * (1.0 - math.exp(-1.0))
        self.assertAlmostEqual(
            _ratio(absorptance_increase(5000.0, 0.06, 5000.0), expected),
            1.0,
            places=12,
        )

    def test_the_darkening_saturates_rather_than_growing_without_bound(self):
        far = absorptance_increase(1.0e6, 0.06, 5000.0)
        self.assertAlmostEqual(_ratio(far, 0.06), 1.0, places=9)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            absorptance_increase(-1.0, 0.06, 5000.0)


class ProfileTests(unittest.TestCase):
    def test_each_profile_contributes_an_objective(self):
        objectives = ultraviolet_objectives(PROFILES)
        self.assertIn("solar-intensity-multiplied-ultraviolet-dose", objectives)
        self.assertIn("prolonged-high-intensity-ultraviolet-dose", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = ultraviolet_objectives(PROFILES)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_profile_yields_no_objective(self):
        self.assertEqual(ultraviolet_objectives([]), ())

    def test_a_repeated_profile_is_grouped_once(self):
        grouped = profile_inventory(
            ["near-sun-science-flyby", "near-sun-science-flyby"]
        )
        self.assertEqual(grouped, ("near-sun-science-flyby",))

    def test_unknown_profile_rejected(self):
        with self.assertRaises(ValueError):
            profile_inventory(["lunar-surface-night"])

    def test_a_bare_string_is_not_a_profile_collection(self):
        with self.assertRaises(ValueError):
            profile_inventory("near-sun-science-flyby")


class AssessmentTests(unittest.TestCase):
    def test_an_adequate_run_demonstrates_the_mission_exposure(self):
        result = assess_mission_specific_ultraviolet_tests(_case())
        self.assertEqual(result["verdict"], EXPOSURE_DEMONSTRATED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_mission_budget_is_reported(self):
        result = assess_mission_specific_ultraviolet_tests(_case())
        self.assertAlmostEqual(
            _ratio(result["mission_equivalent_sun_hours"], 22000.0), 1.0, places=12
        )

    def test_a_run_that_exactly_covers_the_budget_is_accepted(self):
        result = assess_mission_specific_ultraviolet_tests(_case())
        self.assertAlmostEqual(
            result["planned_equivalent_sun_hours"],
            result["mission_equivalent_sun_hours"],
            places=9,
        )
        self.assertTrue(result["dose_covered"])

    def test_no_declared_profile_means_no_extra_testing(self):
        result = assess_mission_specific_ultraviolet_tests(
            _case(mission_profiles=[])
        )
        self.assertEqual(result["verdict"], EXTRA_TESTING_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_near_earth_profile_below_the_threshold_earns_nothing(self):
        case = _case()
        case["mission"]["phases"] = [
            {"heliocentric_distance_au": 1.0, "duration_h": 100.0,
             "illuminated_fraction": 0.6}
        ]
        result = assess_mission_specific_ultraviolet_tests(case)
        self.assertEqual(result["verdict"], EXTRA_TESTING_NOT_REQUIRED)

    def test_an_earned_but_unplanned_run_is_its_own_verdict(self):
        case = _case()
        del case["test"]
        result = assess_mission_specific_ultraviolet_tests(case)
        self.assertEqual(result["verdict"], TEST_NOT_PLANNED)
        self.assertIsNone(result["acceleration_factor"])

    def test_a_short_run_does_not_cover_the_mission_dose(self):
        result = assess_mission_specific_ultraviolet_tests(
            _case(test={"intensity_suns": 5.0, "duration_h": 100.0,
                        "sample_temperature_c": 125.0})
        )
        self.assertEqual(result["verdict"], TEST_INADEQUATE)
        self.assertFalse(result["dose_covered"])

    def test_an_over_driven_lamp_breaks_the_acceleration_bound(self):
        policy = _policy(max_acceleration_factor=2.0)
        result = assess_mission_specific_ultraviolet_tests(
            _case(test={"intensity_suns": 9.0, "duration_h": 4000.0,
                        "sample_temperature_c": 125.0}),
            policy,
        )
        self.assertEqual(result["verdict"], TEST_INADEQUATE)
        self.assertFalse(result["acceleration_within_bound"])

    def test_an_intensity_beyond_the_facility_is_reported(self):
        policy = _policy(max_facility_intensity_suns=4.0,
                         max_acceleration_factor=50.0)
        result = assess_mission_specific_ultraviolet_tests(_case(), policy)
        self.assertFalse(result["facility_can_produce_intensity"])

    def test_a_cold_sample_is_not_representative(self):
        result = assess_mission_specific_ultraviolet_tests(
            _case(test={"intensity_suns": 5.0, "duration_h": 4400.0,
                        "sample_temperature_c": 20.0})
        )
        self.assertEqual(result["verdict"], TEST_INADEQUATE)
        self.assertFalse(result["sample_temperature_representative"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_mission_specific_ultraviolet_tests(
            _case(test={"intensity_suns": 20.0, "duration_h": 10.0,
                        "sample_temperature_c": 20.0})
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_the_predicted_darkening_travels_with_the_verdict(self):
        result = assess_mission_specific_ultraviolet_tests(_case())
        expected = absorptance_increase(22000.0, 0.06, 5000.0)
        self.assertAlmostEqual(
            _ratio(result["predicted_absorptance_increase"], expected),
            1.0,
            places=12,
        )

    def test_objectives_survive_an_unplanned_run(self):
        case = _case()
        del case["test"]
        result = assess_mission_specific_ultraviolet_tests(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_profile_key_rejected(self):
        case = _case()
        del case["mission_profiles"]
        with self.assertRaises(ValueError):
            assess_mission_specific_ultraviolet_tests(case)

    def test_missing_mission_block_rejected(self):
        case = _case()
        del case["mission"]
        with self.assertRaises(ValueError):
            assess_mission_specific_ultraviolet_tests(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_mission_specific_ultraviolet_tests(["mission_profiles"])

    def test_non_mapping_test_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_mission_specific_ultraviolet_tests(_case(test=[5.0, 4400.0]))


if __name__ == "__main__":
    unittest.main()
