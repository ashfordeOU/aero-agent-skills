"""Contract tests for the clause 6.4.3.19.1 angular performance purpose logic."""

import math
import unittest

from e2008_angular_performance_test_purpose_logic import (
    ANGULAR_CHARACTERISATION_NOT_REQUIRED,
    ANGULAR_MEASUREMENT_INADEQUATE,
    ANGULAR_MEASUREMENT_NOT_PLANNED,
    ANGULAR_PERFORMANCE_CHARACTERISED,
    COMMON_OBJECTIVE,
    DEFAULT_ANGULAR_POLICY,
    OFF_POINTING_POWER_SHORTFALL,
    angular_response_factor,
    assess_angular_performance_purpose,
    characterisation_objectives,
    cosine_departure_fraction,
    cosine_projected_output,
    driver_inventory,
    envelope_covers_mission,
    output_at_incidence,
    power_margin_fraction,
    response_factor_is_physical,
    validate_angular_policy,
    worst_case_incidence_deg,
)

DRIVERS = [
    "spacecraft-slew-during-observation",
    "sun-offset-attitude-for-thermal-control",
]


def _policy(**overrides):
    policy = dict(DEFAULT_ANGULAR_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "off_pointing_drivers": list(DRIVERS),
        "mission": {
            "off_pointing_angles_deg": [0.0, 20.0, 55.0],
            "normal_output_w": 250.0,
            "required_output_w": 110.0,
            "expected_response_factor": 0.93,
        },
        "measurement": {"max_test_angle_deg": 60.0},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_angular_policy(DEFAULT_ANGULAR_POLICY), DEFAULT_ANGULAR_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_angular_policy("trigger")

    def test_ceiling_below_the_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_angular_policy(
                _policy(off_pointing_trigger_deg=70.0, max_credible_test_angle_deg=60.0)
            )

    def test_response_factor_floor_above_the_ideal_cosine_rejected(self):
        with self.assertRaises(ValueError):
            validate_angular_policy(_policy(min_response_factor=1.4))

    def test_negative_margin_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_angular_policy(_policy(required_power_margin_fraction=-0.1))

    def test_credible_ceiling_at_or_beyond_edge_on_rejected(self):
        with self.assertRaises(ValueError):
            validate_angular_policy(_policy(max_credible_test_angle_deg=90.0))


class ProjectionTests(unittest.TestCase):
    def test_normal_incidence_keeps_the_whole_output(self):
        self.assertAlmostEqual(
            _ratio(cosine_projected_output(250.0, 0.0), 250.0), 1.0, places=12
        )

    def test_sixty_degrees_halves_the_projected_output(self):
        self.assertAlmostEqual(cosine_projected_output(250.0, 60.0), 125.0, places=9)

    def test_projection_follows_the_cosine_law(self):
        expected = 250.0 * math.cos(math.radians(55.0))
        self.assertAlmostEqual(
            _ratio(cosine_projected_output(250.0, 55.0), expected), 1.0, places=12
        )

    def test_a_larger_angle_projects_less_output(self):
        self.assertLess(
            cosine_projected_output(250.0, 70.0), cosine_projected_output(250.0, 30.0)
        )

    def test_edge_on_incidence_rejected(self):
        with self.assertRaises(ValueError):
            cosine_projected_output(250.0, 90.0)

    def test_negative_incidence_angle_rejected(self):
        with self.assertRaises(ValueError):
            cosine_projected_output(250.0, -1.0)

    def test_boolean_normal_output_rejected(self):
        with self.assertRaises(ValueError):
            cosine_projected_output(True, 30.0)


class ResponseFactorTests(unittest.TestCase):
    def test_an_ideal_assembly_has_a_unit_response_factor(self):
        projected = cosine_projected_output(250.0, 55.0)
        self.assertAlmostEqual(
            angular_response_factor(projected, 250.0, 55.0), 1.0, places=12
        )

    def test_a_lossy_assembly_falls_below_the_cosine(self):
        projected = cosine_projected_output(250.0, 55.0)
        factor = angular_response_factor(0.9 * projected, 250.0, 55.0)
        self.assertAlmostEqual(factor, 0.9, places=12)

    def test_departure_is_the_complement_of_the_factor(self):
        self.assertAlmostEqual(cosine_departure_fraction(0.93), 0.07, places=12)

    def test_output_at_incidence_scales_the_projection(self):
        expected = 250.0 * math.cos(math.radians(55.0)) * 0.93
        self.assertAlmostEqual(
            _ratio(output_at_incidence(250.0, 55.0, 0.93), expected), 1.0, places=12
        )

    def test_a_factor_inside_the_band_is_physical(self):
        self.assertTrue(response_factor_is_physical(0.93, _policy()))

    def test_a_factor_exactly_at_the_ideal_cosine_is_physical(self):
        self.assertTrue(response_factor_is_physical(1.0, _policy()))

    def test_a_factor_above_the_ideal_cosine_is_not_physical(self):
        self.assertFalse(response_factor_is_physical(1.2, _policy()))

    def test_a_factor_below_the_policy_floor_is_not_physical(self):
        self.assertFalse(response_factor_is_physical(0.05, _policy()))

    def test_zero_response_factor_rejected(self):
        with self.assertRaises(ValueError):
            cosine_departure_fraction(0.0)


class EnvelopeTests(unittest.TestCase):
    def test_worst_case_is_the_largest_declared_angle(self):
        self.assertAlmostEqual(
            worst_case_incidence_deg([0.0, 20.0, 55.0]), 55.0, places=12
        )

    def test_an_empty_angle_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_incidence_deg([])

    def test_a_non_collection_angle_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_incidence_deg(55.0)

    def test_a_sweep_past_the_worst_case_covers_the_mission(self):
        self.assertTrue(envelope_covers_mission(60.0, 55.0))

    def test_a_sweep_stopping_exactly_at_the_worst_case_covers_it(self):
        self.assertTrue(envelope_covers_mission(55.0, 55.0))

    def test_a_sweep_stopping_short_does_not_cover_the_mission(self):
        self.assertFalse(envelope_covers_mission(45.0, 55.0))

    def test_margin_is_relative_to_the_requirement(self):
        self.assertAlmostEqual(power_margin_fraction(132.0, 110.0), 0.2, places=12)

    def test_a_shortfall_gives_a_negative_margin(self):
        self.assertLess(power_margin_fraction(90.0, 110.0), 0.0)

    def test_zero_required_power_rejected(self):
        with self.assertRaises(ValueError):
            power_margin_fraction(132.0, 0.0)


class ObjectiveTests(unittest.TestCase):
    def test_each_driver_contributes_an_objective(self):
        objectives = characterisation_objectives(DRIVERS)
        self.assertIn("array-power-through-the-slew", objectives)
        self.assertIn("array-power-at-the-held-offset", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = characterisation_objectives(DRIVERS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_driver_yields_no_objective(self):
        self.assertEqual(characterisation_objectives([]), ())

    def test_a_repeated_driver_is_grouped_once(self):
        grouped = driver_inventory(
            ["spacecraft-slew-during-observation", "spacecraft-slew-during-observation"]
        )
        self.assertEqual(grouped, ("spacecraft-slew-during-observation",))

    def test_unknown_driver_rejected(self):
        with self.assertRaises(ValueError):
            driver_inventory(["array-eclipse-entry"])

    def test_non_collection_driver_list_rejected(self):
        with self.assertRaises(ValueError):
            driver_inventory("spacecraft-slew-during-observation")


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_sweep_characterises_the_angular_performance(self):
        result = assess_angular_performance_purpose(_case())
        self.assertEqual(result["verdict"], ANGULAR_PERFORMANCE_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_worst_case_output_is_derived_from_the_cosine_and_the_factor(self):
        result = assess_angular_performance_purpose(_case())
        expected = 250.0 * math.cos(math.radians(55.0)) * 0.93
        self.assertAlmostEqual(
            _ratio(result["expected_output_w"], expected), 1.0, places=12
        )

    def test_the_margin_is_reported_against_the_requirement(self):
        result = assess_angular_performance_purpose(_case())
        expected = 250.0 * math.cos(math.radians(55.0)) * 0.93
        self.assertAlmostEqual(
            _ratio(result["power_margin_fraction"], (expected - 110.0) / 110.0),
            1.0,
            places=12,
        )

    def test_no_declared_driver_means_no_characterisation_required(self):
        result = assess_angular_performance_purpose(_case(off_pointing_drivers=[]))
        self.assertEqual(result["verdict"], ANGULAR_CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_sun_pointed_mission_does_not_earn_the_sweep(self):
        case = _case()
        case["mission"]["off_pointing_angles_deg"] = [0.0, 2.0, 4.0]
        result = assess_angular_performance_purpose(case)
        self.assertEqual(result["verdict"], ANGULAR_CHARACTERISATION_NOT_REQUIRED)

    def test_an_angle_exactly_at_the_trigger_earns_the_sweep(self):
        policy = _policy()
        case = _case()
        case["mission"]["off_pointing_angles_deg"] = [
            policy["off_pointing_trigger_deg"]
        ]
        result = assess_angular_performance_purpose(case, policy)
        self.assertAlmostEqual(
            result["worst_case_incidence_deg"],
            policy["off_pointing_trigger_deg"],
            places=9,
        )
        self.assertTrue(result["required"])

    def test_a_required_but_unplanned_sweep_is_its_own_verdict(self):
        case = _case()
        del case["measurement"]
        result = assess_angular_performance_purpose(case)
        self.assertEqual(result["verdict"], ANGULAR_MEASUREMENT_NOT_PLANNED)
        self.assertIsNone(result["max_test_angle_deg"])

    def test_a_sweep_stopping_short_of_the_mission_is_inadequate(self):
        result = assess_angular_performance_purpose(
            _case(measurement={"max_test_angle_deg": 45.0})
        )
        self.assertEqual(result["verdict"], ANGULAR_MEASUREMENT_INADEQUATE)
        self.assertFalse(result["envelope_covers_mission"])

    def test_a_sweep_beyond_the_credible_ceiling_is_inadequate(self):
        result = assess_angular_performance_purpose(
            _case(measurement={"max_test_angle_deg": 88.0})
        )
        self.assertEqual(result["verdict"], ANGULAR_MEASUREMENT_INADEQUATE)
        self.assertTrue(result["envelope_covers_mission"])

    def test_an_unphysical_response_factor_is_inadequate(self):
        case = _case()
        case["mission"]["expected_response_factor"] = 1.4
        result = assess_angular_performance_purpose(case)
        self.assertEqual(result["verdict"], ANGULAR_MEASUREMENT_INADEQUATE)
        self.assertFalse(result["response_factor_physical"])

    def test_both_envelope_problems_are_reported_not_only_the_first(self):
        case = _case(measurement={"max_test_angle_deg": 45.0})
        case["mission"]["expected_response_factor"] = 1.4
        result = assess_angular_performance_purpose(case)
        self.assertEqual(len(result["findings"]), 2)

    def test_an_adequate_sweep_can_still_show_a_power_shortfall(self):
        case = _case()
        case["mission"]["required_output_w"] = 200.0
        result = assess_angular_performance_purpose(case)
        self.assertEqual(result["verdict"], OFF_POINTING_POWER_SHORTFALL)
        self.assertFalse(result["power_margin_met"])

    def test_objectives_survive_an_unplanned_sweep(self):
        case = _case()
        del case["measurement"]
        result = assess_angular_performance_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_driver_key_rejected(self):
        case = _case()
        del case["off_pointing_drivers"]
        with self.assertRaises(ValueError):
            assess_angular_performance_purpose(case)

    def test_missing_mission_block_rejected(self):
        case = _case()
        del case["mission"]
        with self.assertRaises(ValueError):
            assess_angular_performance_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_angular_performance_purpose(["off_pointing_drivers"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_angular_performance_purpose(_case(measurement=[60.0]))


if __name__ == "__main__":
    unittest.main()
