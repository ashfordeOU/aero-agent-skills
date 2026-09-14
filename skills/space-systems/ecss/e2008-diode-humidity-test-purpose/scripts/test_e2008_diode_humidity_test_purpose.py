"""Contract tests for the clause 9.6.6.1.1 diode damp storage purpose logic."""

import math
import unittest

from e2008_diode_humidity_test_purpose_logic import (
    COMMON_OBJECTIVE,
    DAMP_STORAGE_CONDITIONS_UNSOUND,
    DAMP_STORAGE_MONITORING_BLIND,
    DAMP_STORAGE_NOT_PLANNED,
    DAMP_STORAGE_NOT_REQUIRED,
    DAMP_STORAGE_PURPOSE_SERVED,
    DEFAULT_DAMP_STORAGE_POLICY,
    HOURS_PER_MONTH,
    STORAGE_LIFE_SHORTFALL,
    assess_diode_humidity_purpose,
    damp_storage_acceleration_factor,
    equivalent_storage_months,
    exposed_families,
    exposure_objectives,
    kelvin,
    mechanism_inventory,
    unwatched_mechanisms,
    validate_damp_storage_policy,
    watched_parameters,
)

MECHANISMS = [
    "junction-passivation-permeation",
    "contact-metallisation-corrosion",
    "protective-coating-crazing",
]

PARAMETERS = [
    "reverse-leakage-current",
    "forward-voltage-drop",
    "coating-visual-integrity",
]


def _policy(**overrides):
    policy = dict(DEFAULT_DAMP_STORAGE_POLICY)
    policy.update(overrides)
    return policy


def _exposure(**overrides):
    exposure = {
        "temperature_c": 85.0,
        "humidity_pct": 85.0,
        "humidity_exponent": 2.7,
        "activation_energy_ev": 0.6,
        "duration_h": 168.0,
    }
    exposure.update(overrides)
    return exposure


def _storage(**overrides):
    storage = {"temperature_c": 30.0, "humidity_pct": 50.0}
    storage.update(overrides)
    return storage


def _case(**overrides):
    case = {
        "moisture_mechanisms": list(MECHANISMS),
        "monitored_parameters": list(PARAMETERS),
        "exposure": _exposure(),
        "storage": _storage(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_damp_storage_policy(DEFAULT_DAMP_STORAGE_POLICY),
            DEFAULT_DAMP_STORAGE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy("damp")

    def test_an_acceleration_floor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(min_acceleration_factor=0.5))

    def test_a_fitted_ceiling_below_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(
                _policy(min_acceleration_factor=50.0, max_fitted_acceleration_factor=10.0)
            )

    def test_a_zero_required_storage_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(required_storage_months=0.0))

    def test_a_saturated_humidity_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_damp_storage_policy(_policy(max_chamber_humidity_pct=100.0))


class AccelerationTests(unittest.TestCase):
    def test_identical_conditions_accelerate_nothing(self):
        self.assertAlmostEqual(
            damp_storage_acceleration_factor(50.0, 50.0, 30.0, 30.0, 2.7, 0.6),
            1.0,
            places=9,
        )

    def test_the_factor_is_the_humidity_term_times_the_thermal_term(self):
        humidity = math.pow(85.0 / 50.0, 2.7)
        thermal = math.exp(
            (0.6 / 8.617333262e-5) * (1.0 / kelvin(30.0) - 1.0 / kelvin(85.0))
        )
        self.assertAlmostEqual(
            _ratio(
                damp_storage_acceleration_factor(85.0, 50.0, 85.0, 30.0, 2.7, 0.6),
                humidity * thermal,
            ),
            1.0,
            places=12,
        )

    def test_a_wetter_chamber_accelerates_more(self):
        self.assertGreater(
            damp_storage_acceleration_factor(90.0, 50.0, 85.0, 30.0, 2.7, 0.6),
            damp_storage_acceleration_factor(70.0, 50.0, 85.0, 30.0, 2.7, 0.6),
        )

    def test_a_hotter_chamber_accelerates_more(self):
        self.assertGreater(
            damp_storage_acceleration_factor(85.0, 50.0, 85.0, 30.0, 2.7, 0.6),
            damp_storage_acceleration_factor(85.0, 50.0, 55.0, 30.0, 2.7, 0.6),
        )

    def test_a_chamber_milder_than_the_store_slows_the_mechanism(self):
        self.assertLess(
            damp_storage_acceleration_factor(40.0, 50.0, 20.0, 30.0, 2.7, 0.6), 0.9
        )

    def test_a_saturated_chamber_humidity_rejected(self):
        with self.assertRaises(ValueError):
            damp_storage_acceleration_factor(100.0, 50.0, 85.0, 30.0, 2.7, 0.6)

    def test_a_zero_humidity_exponent_rejected(self):
        with self.assertRaises(ValueError):
            damp_storage_acceleration_factor(85.0, 50.0, 85.0, 30.0, 0.0, 0.6)

    def test_a_storage_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            damp_storage_acceleration_factor(85.0, 50.0, 85.0, -300.0, 2.7, 0.6)


class EquivalenceTests(unittest.TestCase):
    def test_months_are_the_accelerated_hours_over_a_month_of_hours(self):
        self.assertAlmostEqual(
            equivalent_storage_months(HOURS_PER_MONTH, 1.0), 1.0, places=9
        )

    def test_the_factor_multiplies_the_soak(self):
        self.assertAlmostEqual(
            _ratio(
                equivalent_storage_months(168.0, 142.0), 168.0 * 142.0 / HOURS_PER_MONTH
            ),
            1.0,
            places=12,
        )

    def test_a_longer_soak_is_worth_more_store(self):
        self.assertGreater(
            equivalent_storage_months(336.0, 142.0),
            equivalent_storage_months(168.0, 142.0),
        )

    def test_a_zero_length_soak_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_storage_months(0.0, 142.0)

    def test_a_zero_acceleration_factor_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_storage_months(168.0, 0.0)


class InventoryTests(unittest.TestCase):
    def test_a_repeated_mechanism_is_grouped_once(self):
        grouped = mechanism_inventory(
            ["protective-coating-crazing", "protective-coating-crazing"]
        )
        self.assertEqual(grouped, ("protective-coating-crazing",))

    def test_an_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory(["coverglass-darkening"])

    def test_a_non_collection_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory("protective-coating-crazing")

    def test_the_three_families_are_named_by_the_mechanisms(self):
        self.assertEqual(
            exposed_families(MECHANISMS),
            ("diode-coatings", "diode-contacts", "diode-function"),
        )

    def test_two_function_mechanisms_name_the_family_once(self):
        self.assertEqual(
            exposed_families(
                ["junction-passivation-permeation", "die-attach-moisture-ingress"]
            ),
            ("diode-function",),
        )

    def test_each_mechanism_reaches_a_parameter(self):
        self.assertEqual(len(watched_parameters(MECHANISMS)), 3)

    def test_the_shared_objective_is_appended_once(self):
        objectives = exposure_objectives(MECHANISMS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_mechanism_yields_no_objective(self):
        self.assertEqual(exposure_objectives([]), ())

    def test_an_unwatched_mechanism_is_named(self):
        blind = unwatched_mechanisms(MECHANISMS, ["reverse-leakage-current"])
        self.assertEqual(
            sorted(blind),
            ["contact-metallisation-corrosion", "protective-coating-crazing"],
        )

    def test_full_monitoring_leaves_no_mechanism_unwatched(self):
        self.assertEqual(unwatched_mechanisms(MECHANISMS, PARAMETERS), ())

    def test_a_non_collection_monitoring_list_rejected(self):
        with self.assertRaises(ValueError):
            unwatched_mechanisms(MECHANISMS, "reverse-leakage-current")


class PurposeAssessmentTests(unittest.TestCase):
    def test_a_sound_exposure_serves_its_purpose(self):
        result = assess_diode_humidity_purpose(_case())
        self.assertEqual(result["verdict"], DAMP_STORAGE_PURPOSE_SERVED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_equivalent_store_is_reported_for_the_soak(self):
        result = assess_diode_humidity_purpose(_case())
        factor = damp_storage_acceleration_factor(85.0, 50.0, 85.0, 30.0, 2.7, 0.6)
        self.assertAlmostEqual(
            _ratio(
                result["equivalent_storage_months"], 168.0 * factor / HOURS_PER_MONTH
            ),
            1.0,
            places=12,
        )

    def test_the_families_the_exposure_is_for_are_reported(self):
        result = assess_diode_humidity_purpose(_case())
        self.assertIn("diode-coatings", result["exposed_families"])
        self.assertIn("diode-contacts", result["exposed_families"])
        self.assertIn("diode-function", result["exposed_families"])

    def test_no_declared_mechanism_means_no_exposure_required(self):
        result = assess_diode_humidity_purpose(_case(moisture_mechanisms=[]))
        self.assertEqual(result["verdict"], DAMP_STORAGE_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_required_but_unplanned_exposure_is_its_own_verdict(self):
        case = _case()
        del case["exposure"]
        result = assess_diode_humidity_purpose(case)
        self.assertEqual(result["verdict"], DAMP_STORAGE_NOT_PLANNED)
        self.assertIsNone(result["acceleration_factor"])

    def test_objectives_survive_an_unplanned_exposure(self):
        case = _case()
        del case["exposure"]
        result = assess_diode_humidity_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_a_chamber_barely_above_the_store_is_unsound(self):
        result = assess_diode_humidity_purpose(
            _case(exposure=_exposure(temperature_c=32.0, humidity_pct=52.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertLess(result["acceleration_factor"], 2.0)

    def test_an_acceleration_beyond_the_fitted_range_is_unsound(self):
        result = assess_diode_humidity_purpose(
            _case(
                exposure=_exposure(humidity_pct=93.0),
                storage=_storage(temperature_c=20.0, humidity_pct=40.0),
            )
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertGreater(result["acceleration_factor"], 200.0)

    def test_a_chamber_hotter_than_the_part_may_be_held_is_unsound(self):
        result = assess_diode_humidity_purpose(
            _case(exposure=_exposure(temperature_c=90.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_chamber_wet_enough_to_condense_is_unsound(self):
        result = assess_diode_humidity_purpose(
            _case(exposure=_exposure(humidity_pct=95.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertFalse(result["conditions_sound"])

    def test_an_unwatched_mechanism_makes_the_exposure_blind(self):
        result = assess_diode_humidity_purpose(
            _case(monitored_parameters=["reverse-leakage-current"])
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_MONITORING_BLIND)
        self.assertEqual(len(result["unwatched_mechanisms"]), 2)

    def test_a_sound_watched_exposure_can_still_fall_short_of_the_shelf_life(self):
        result = assess_diode_humidity_purpose(
            _case(exposure=_exposure(duration_h=48.0))
        )
        self.assertEqual(result["verdict"], STORAGE_LIFE_SHORTFALL)
        self.assertFalse(result["storage_equivalence_met"])

    def test_both_condition_problems_are_reported_not_only_the_first(self):
        result = assess_diode_humidity_purpose(
            _case(exposure=_exposure(temperature_c=95.0, humidity_pct=97.0))
        )
        self.assertEqual(result["verdict"], DAMP_STORAGE_CONDITIONS_UNSOUND)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_an_absent_mechanism_inventory_rejected(self):
        case = _case()
        del case["moisture_mechanisms"]
        with self.assertRaises(ValueError):
            assess_diode_humidity_purpose(case)

    def test_a_missing_storage_block_rejected(self):
        case = _case()
        del case["storage"]
        with self.assertRaises(ValueError):
            assess_diode_humidity_purpose(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_humidity_purpose(["exposure"])

    def test_a_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_humidity_purpose(_case(exposure=[168.0]))


if __name__ == "__main__":
    unittest.main()
