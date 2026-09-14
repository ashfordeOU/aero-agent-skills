"""Contract tests for the clause 7.5.7.1.1 damp storage purpose logic."""

import math
import unittest

from e2008_solar_cell_humidity_test_purpose_logic import (
    BOLTZMANN_EV_PER_K,
    COMMON_OBJECTIVE,
    DAMP_STABILITY_EVIDENCED,
    DEFAULT_DAMP_POLICY,
    EXPOSURE_INSUFFICIENT,
    MONITORING_INADEQUATE,
    MONITORING_NOT_PLANNED,
    STORAGE_NOT_PLANNED,
    STORAGE_NOT_REQUIRED,
    acceleration_factor,
    assess_damp_storage_purpose,
    coverage_ratio,
    equivalent_ambient_hours,
    humidity_acceleration,
    mechanism_inventory,
    monitoring_objectives,
    thermal_acceleration,
    unwatched_mechanisms,
    validate_damp_policy,
)

MECHANISMS = [
    "cell-contact-adhesion-loss",
    "integrated-bypass-diode-leakage",
]

PARAMETERS = [
    "contact-peel-strength-drift",
    "diode-reverse-leakage-drift",
]


def _policy(**overrides):
    policy = dict(DEFAULT_DAMP_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "degradation_mechanisms": list(MECHANISMS),
        "ambient_condition": {
            "relative_humidity_pct": 50.0,
            "temperature_k": 298.15,
            "required_ambient_hours": 8760.0,
        },
        "storage": {
            "relative_humidity_pct": 85.0,
            "temperature_k": 358.15,
            "soak_duration_h": 1000.0,
        },
        "monitored_parameters": list(PARAMETERS),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_damp_policy(DEFAULT_DAMP_POLICY), DEFAULT_DAMP_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_policy("peck")

    def test_zero_humidity_exponent_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_policy(_policy(humidity_exponent=0.0))

    def test_negative_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_policy(_policy(activation_energy_ev=-0.7))

    def test_zero_coverage_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_policy(_policy(min_coverage_ratio=0.0))


class MechanismTests(unittest.TestCase):
    def test_each_mechanism_maps_to_a_watched_parameter(self):
        objectives = monitoring_objectives(MECHANISMS)
        self.assertIn("contact-peel-strength-drift", objectives)
        self.assertIn("diode-reverse-leakage-drift", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = monitoring_objectives(MECHANISMS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_mechanism_yields_no_objective(self):
        self.assertEqual(monitoring_objectives([]), ())

    def test_a_repeated_mechanism_is_grouped_once(self):
        grouped = mechanism_inventory(
            ["cell-contact-adhesion-loss", "cell-contact-adhesion-loss"]
        )
        self.assertEqual(grouped, ("cell-contact-adhesion-loss",))

    def test_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory(["cell-radiation-displacement-damage"])

    def test_non_collection_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory("cell-contact-adhesion-loss")

    def test_an_unwatched_mechanism_is_named(self):
        self.assertEqual(
            unwatched_mechanisms(MECHANISMS, ["contact-peel-strength-drift"]),
            ("integrated-bypass-diode-leakage",),
        )

    def test_fully_watched_mechanisms_leave_nothing_unwatched(self):
        self.assertEqual(unwatched_mechanisms(MECHANISMS, PARAMETERS), ())

    def test_non_collection_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            unwatched_mechanisms(MECHANISMS, "contact-peel-strength-drift")


class AccelerationTests(unittest.TestCase):
    def test_humidity_term_follows_the_power_law(self):
        expected = (85.0 / 50.0) ** 2.66
        self.assertAlmostEqual(
            _ratio(humidity_acceleration(85.0, 50.0, 2.66), expected), 1.0, places=12
        )

    def test_equal_humidity_gives_unity_acceleration(self):
        self.assertAlmostEqual(humidity_acceleration(50.0, 50.0, 2.66), 1.0, places=9)

    def test_thermal_term_follows_the_arrhenius_form(self):
        expected = math.exp(
            (0.70 / BOLTZMANN_EV_PER_K) * ((1.0 / 298.15) - (1.0 / 358.15))
        )
        self.assertAlmostEqual(
            _ratio(thermal_acceleration(358.15, 298.15, 0.70), expected),
            1.0,
            places=12,
        )

    def test_equal_temperature_gives_unity_acceleration(self):
        self.assertAlmostEqual(
            thermal_acceleration(298.15, 298.15, 0.70), 1.0, places=9
        )

    def test_a_colder_chamber_decelerates(self):
        self.assertLess(thermal_acceleration(273.15, 298.15, 0.70), 1.0)

    def test_combined_factor_is_the_product_of_both_terms(self):
        case = _case()
        expected = humidity_acceleration(85.0, 50.0, 2.66) * thermal_acceleration(
            358.15, 298.15, 0.70
        )
        self.assertAlmostEqual(
            _ratio(
                acceleration_factor(
                    case["storage"], case["ambient_condition"], _policy()
                ),
                expected,
            ),
            1.0,
            places=12,
        )

    def test_humidity_above_one_hundred_per_cent_rejected(self):
        with self.assertRaises(ValueError):
            humidity_acceleration(140.0, 50.0, 2.66)

    def test_zero_ambient_humidity_rejected(self):
        with self.assertRaises(ValueError):
            humidity_acceleration(85.0, 0.0, 2.66)

    def test_negative_absolute_temperature_rejected(self):
        with self.assertRaises(ValueError):
            thermal_acceleration(-358.15, 298.15, 0.70)

    def test_non_mapping_storage_condition_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor([85.0, 358.15], _case()["ambient_condition"])


class EquivalenceTests(unittest.TestCase):
    def test_equivalent_hours_scale_with_the_factor(self):
        self.assertAlmostEqual(
            _ratio(equivalent_ambient_hours(12.0, 1000.0), 12000.0), 1.0, places=12
        )

    def test_coverage_is_equivalent_over_required(self):
        self.assertAlmostEqual(
            _ratio(coverage_ratio(12000.0, 8760.0), 12000.0 / 8760.0), 1.0, places=12
        )

    def test_zero_soak_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_ambient_hours(12.0, 0.0)

    def test_zero_required_exposure_rejected(self):
        with self.assertRaises(ValueError):
            coverage_ratio(12000.0, 0.0)


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_complete_case_evidences_damp_stability(self):
        result = assess_damp_storage_purpose(_case())
        self.assertEqual(result["verdict"], DAMP_STABILITY_EVIDENCED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_acceleration_and_equivalent_exposure_are_reported(self):
        result = assess_damp_storage_purpose(_case())
        expected = humidity_acceleration(85.0, 50.0, 2.66) * thermal_acceleration(
            358.15, 298.15, 0.70
        )
        self.assertAlmostEqual(
            _ratio(result["acceleration_factor"], expected), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["equivalent_ambient_hours"], expected * 1000.0),
            1.0,
            places=12,
        )

    def test_no_declared_mechanism_means_no_storage_required(self):
        result = assess_damp_storage_purpose(_case(degradation_mechanisms=[]))
        self.assertEqual(result["verdict"], STORAGE_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_required_but_unplanned_storage_is_its_own_verdict(self):
        case = _case()
        del case["storage"]
        result = assess_damp_storage_purpose(case)
        self.assertEqual(result["verdict"], STORAGE_NOT_PLANNED)
        self.assertIsNone(result["acceleration_factor"])

    def test_a_short_soak_leaves_the_exposure_insufficient(self):
        case = _case()
        case["storage"]["soak_duration_h"] = 1.0
        result = assess_damp_storage_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_INSUFFICIENT)
        self.assertLess(result["coverage_ratio"], 1.0)

    def test_a_coverage_exactly_at_the_floor_still_evidences_stability(self):
        case = _case()
        factor = acceleration_factor(
            case["storage"], case["ambient_condition"], _policy()
        )
        case["ambient_condition"]["required_ambient_hours"] = factor * 1000.0
        result = assess_damp_storage_purpose(case)
        self.assertAlmostEqual(
            result["coverage_ratio"], _policy()["min_coverage_ratio"], places=9
        )
        self.assertEqual(result["verdict"], DAMP_STABILITY_EVIDENCED)

    def test_a_chamber_at_ambient_conditions_accelerates_nothing(self):
        case = _case()
        case["storage"]["relative_humidity_pct"] = 50.0
        case["storage"]["temperature_k"] = 298.15
        case["storage"]["soak_duration_h"] = 20000.0
        result = assess_damp_storage_purpose(case, _policy(min_acceleration_factor=2.0))
        self.assertEqual(result["verdict"], EXPOSURE_INSUFFICIENT)

    def test_absent_monitoring_is_its_own_verdict(self):
        case = _case()
        del case["monitored_parameters"]
        result = assess_damp_storage_purpose(case)
        self.assertEqual(result["verdict"], MONITORING_NOT_PLANNED)

    def test_a_partly_watched_inventory_is_inadequate(self):
        result = assess_damp_storage_purpose(
            _case(monitored_parameters=["contact-peel-strength-drift"])
        )
        self.assertEqual(result["verdict"], MONITORING_INADEQUATE)
        self.assertEqual(
            result["unwatched_mechanisms"], ("integrated-bypass-diode-leakage",)
        )

    def test_both_a_short_soak_and_a_gap_in_monitoring_are_reported(self):
        case = _case(monitored_parameters=["contact-peel-strength-drift"])
        case["storage"]["soak_duration_h"] = 1.0
        result = assess_damp_storage_purpose(case)
        self.assertEqual(len(result["findings"]), 2)

    def test_objectives_survive_an_unplanned_storage(self):
        case = _case()
        del case["storage"]
        result = assess_damp_storage_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_mechanism_key_rejected(self):
        case = _case()
        del case["degradation_mechanisms"]
        with self.assertRaises(ValueError):
            assess_damp_storage_purpose(case)

    def test_missing_ambient_condition_rejected(self):
        case = _case()
        del case["ambient_condition"]
        with self.assertRaises(ValueError):
            assess_damp_storage_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_damp_storage_purpose(["degradation_mechanisms"])

    def test_non_mapping_storage_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_damp_storage_purpose(_case(storage=[85.0, 358.15]))


if __name__ == "__main__":
    unittest.main()
