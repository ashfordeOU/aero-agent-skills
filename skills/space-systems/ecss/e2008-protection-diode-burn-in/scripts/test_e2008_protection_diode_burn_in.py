"""Contract tests for the clause 9.6.5 protection diode burn-in logic."""

import math
import unittest

from e2008_protection_diode_burn_in_logic import (
    BURN_IN_LOADING_INADEQUATE,
    BURN_IN_LOT_REJECTED,
    BURN_IN_MONITORING_BLIND,
    BURN_IN_NOT_PLANNED,
    DEFAULT_BURN_IN_POLICY,
    EARLY_LIFE_FAILURES_SCREENED,
    arrhenius_acceleration_factor,
    assess_protection_diode_burn_in,
    dissipated_power_w,
    equivalent_operating_hours,
    junction_temperature_c,
    kelvin,
    lot_failure_fraction,
    mechanism_inventory,
    screened_fraction,
    unwatched_mechanisms,
    validate_burn_in_policy,
    watched_parameters,
)

MECHANISMS = [
    "die-attach-void-growth",
    "junction-passivation-defect",
    "bond-weld-weakness",
]

PARAMETERS = [
    "thermal-resistance-junction-to-case",
    "reverse-leakage-current",
    "forward-voltage-drop",
]


def _policy(**overrides):
    policy = dict(DEFAULT_BURN_IN_POLICY)
    policy.update(overrides)
    return policy


def _loading(**overrides):
    loading = {
        "forward_current_a": 1.0,
        "forward_voltage_v": 0.8,
        "case_temperature_c": 100.0,
        "thermal_resistance_c_per_w": 15.0,
        "use_temperature_c": 60.0,
        "activation_energy_ev": 0.7,
        "duration_h": 48.0,
        "characteristic_life_h": 12.0,
        "weibull_shape": 0.4,
    }
    loading.update(overrides)
    return loading


def _case(**overrides):
    case = {
        "early_life_mechanisms": list(MECHANISMS),
        "monitored_parameters": list(PARAMETERS),
        "loading": _loading(),
        "outcome": {"batch_size": 100, "failed_units": 2},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_burn_in_policy(DEFAULT_BURN_IN_POLICY), DEFAULT_BURN_IN_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy("burn-in")

    def test_an_acceleration_floor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy(_policy(min_acceleration_factor=0.5))

    def test_a_screening_floor_above_the_whole_population_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy(_policy(min_screened_fraction=1.2))

    def test_a_reject_limit_accepting_a_wholly_failed_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy(_policy(max_lot_failure_fraction=1.0))

    def test_a_junction_ceiling_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy(_policy(max_junction_temperature_c=-300.0))

    def test_a_zero_equivalent_hours_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_burn_in_policy(_policy(min_equivalent_operating_hours=0.0))


class ThermalTests(unittest.TestCase):
    def test_power_is_the_forward_current_times_the_forward_drop(self):
        self.assertAlmostEqual(dissipated_power_w(1.0, 0.8), 0.8, places=9)

    def test_zero_forward_current_rejected(self):
        with self.assertRaises(ValueError):
            dissipated_power_w(0.0, 0.8)

    def test_a_boolean_forward_voltage_rejected(self):
        with self.assertRaises(ValueError):
            dissipated_power_w(1.0, True)

    def test_the_junction_sits_above_the_case_by_the_thermal_drop(self):
        self.assertAlmostEqual(
            junction_temperature_c(100.0, 0.8, 15.0), 112.0, places=9
        )

    def test_a_perfect_thermal_path_leaves_the_junction_at_the_case(self):
        self.assertAlmostEqual(
            junction_temperature_c(100.0, 0.8, 0.0), 100.0, places=9
        )

    def test_a_case_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 0.8, 15.0)

    def test_kelvin_conversion_offsets_by_absolute_zero(self):
        self.assertAlmostEqual(kelvin(0.0), 273.15, places=9)


class AccelerationTests(unittest.TestCase):
    def test_a_hotter_junction_ages_faster_than_use(self):
        self.assertGreater(arrhenius_acceleration_factor(112.0, 60.0, 0.7), 20.0)

    def test_a_junction_at_the_use_temperature_accelerates_nothing(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(90.0, 90.0, 0.7), 1.0, places=9
        )

    def test_a_junction_below_the_use_temperature_slows_the_batch(self):
        self.assertLess(arrhenius_acceleration_factor(112.0, 150.0, 0.7), 0.5)

    def test_a_larger_activation_energy_raises_the_factor(self):
        self.assertGreater(
            arrhenius_acceleration_factor(112.0, 60.0, 0.9),
            arrhenius_acceleration_factor(112.0, 60.0, 0.7),
        )

    def test_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(112.0, 60.0, 0.0)

    def test_equivalent_hours_are_the_soak_times_the_factor(self):
        factor = arrhenius_acceleration_factor(112.0, 60.0, 0.7)
        self.assertAlmostEqual(
            _ratio(equivalent_operating_hours(48.0, factor), 48.0 * factor),
            1.0,
            places=12,
        )

    def test_a_zero_length_soak_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_operating_hours(0.0, 26.9)


class ScreeningTests(unittest.TestCase):
    def test_the_screened_share_follows_the_weibull_form(self):
        expected = 1.0 - math.exp(-math.pow(48.0 / 12.0, 0.4))
        self.assertAlmostEqual(
            _ratio(screened_fraction(48.0, 12.0, 0.4), expected), 1.0, places=12
        )

    def test_the_screened_share_stays_inside_the_population(self):
        removed = screened_fraction(48.0, 12.0, 0.4)
        self.assertGreater(removed, 0.0)
        self.assertLess(removed, 1.0)

    def test_a_longer_soak_removes_more_of_the_population(self):
        self.assertGreater(
            screened_fraction(96.0, 12.0, 0.4), screened_fraction(24.0, 12.0, 0.4)
        )

    def test_a_constant_hazard_population_is_refused(self):
        with self.assertRaises(ValueError):
            screened_fraction(48.0, 12.0, 1.0)

    def test_a_rising_hazard_population_is_refused(self):
        with self.assertRaises(ValueError):
            screened_fraction(48.0, 12.0, 1.6)

    def test_a_zero_characteristic_life_rejected(self):
        with self.assertRaises(ValueError):
            screened_fraction(48.0, 0.0, 0.4)


class LotTests(unittest.TestCase):
    def test_the_failure_share_is_the_failed_units_over_the_batch(self):
        self.assertAlmostEqual(lot_failure_fraction(2, 100), 0.02, places=12)

    def test_a_batch_that_lost_nothing_has_a_zero_share(self):
        self.assertAlmostEqual(lot_failure_fraction(0, 100), 0.0, places=12)

    def test_more_failures_than_units_rejected(self):
        with self.assertRaises(ValueError):
            lot_failure_fraction(101, 100)

    def test_an_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            lot_failure_fraction(0, 0)

    def test_a_fractional_failure_count_rejected(self):
        with self.assertRaises(ValueError):
            lot_failure_fraction(2.5, 100)

    def test_a_negative_failure_count_rejected(self):
        with self.assertRaises(ValueError):
            lot_failure_fraction(-1, 100)


class InventoryTests(unittest.TestCase):
    def test_a_repeated_mechanism_is_grouped_once(self):
        grouped = mechanism_inventory(
            ["die-attach-void-growth", "die-attach-void-growth"]
        )
        self.assertEqual(grouped, ("die-attach-void-growth",))

    def test_an_unknown_mechanism_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory(["coverglass-darkening"])

    def test_a_non_collection_mechanism_list_rejected(self):
        with self.assertRaises(ValueError):
            mechanism_inventory("die-attach-void-growth")

    def test_two_mechanisms_sharing_a_parameter_list_it_once(self):
        parameters = watched_parameters(
            ["bond-weld-weakness", "contact-metallisation-thinning"]
        )
        self.assertEqual(parameters, ("forward-voltage-drop",))

    def test_every_declared_mechanism_reaches_a_parameter(self):
        self.assertEqual(len(watched_parameters(MECHANISMS)), 3)

    def test_a_mechanism_with_no_parameter_watching_it_is_named(self):
        blind = unwatched_mechanisms(
            MECHANISMS, ["thermal-resistance-junction-to-case"]
        )
        self.assertEqual(
            sorted(blind), ["bond-weld-weakness", "junction-passivation-defect"]
        )

    def test_full_monitoring_leaves_no_mechanism_unwatched(self):
        self.assertEqual(unwatched_mechanisms(MECHANISMS, PARAMETERS), ())


class AssessmentTests(unittest.TestCase):
    def test_an_adequate_run_screens_the_early_life_failures(self):
        result = assess_protection_diode_burn_in(_case())
        self.assertEqual(result["verdict"], EARLY_LIFE_FAILURES_SCREENED)
        self.assertEqual(result["findings"], [])

    def test_the_equivalent_hours_are_reported_for_the_run(self):
        result = assess_protection_diode_burn_in(_case())
        factor = arrhenius_acceleration_factor(112.0, 60.0, 0.7)
        self.assertAlmostEqual(
            _ratio(result["equivalent_operating_hours"], 48.0 * factor),
            1.0,
            places=12,
        )

    def test_the_junction_temperature_is_derived_not_taken_from_the_case(self):
        result = assess_protection_diode_burn_in(_case())
        self.assertAlmostEqual(result["junction_temperature_c"], 112.0, places=9)

    def test_an_unplanned_burn_in_is_its_own_verdict(self):
        case = _case()
        del case["loading"]
        result = assess_protection_diode_burn_in(case)
        self.assertEqual(result["verdict"], BURN_IN_NOT_PLANNED)
        self.assertIsNone(result["junction_temperature_c"])

    def test_a_junction_beyond_the_ceiling_makes_the_loading_inadequate(self):
        result = assess_protection_diode_burn_in(
            _case(loading=_loading(case_temperature_c=170.0))
        )
        self.assertEqual(result["verdict"], BURN_IN_LOADING_INADEQUATE)
        self.assertFalse(result["loading_adequate"])

    def test_a_short_soak_falls_under_the_equivalent_hours_floor(self):
        result = assess_protection_diode_burn_in(
            _case(loading=_loading(duration_h=1.0))
        )
        self.assertEqual(result["verdict"], BURN_IN_LOADING_INADEQUATE)
        self.assertLess(result["equivalent_operating_hours"], 1000.0)

    def test_an_oven_cooler_than_the_mission_accelerates_nothing(self):
        result = assess_protection_diode_burn_in(
            _case(loading=_loading(use_temperature_c=150.0, duration_h=4000.0))
        )
        self.assertEqual(result["verdict"], BURN_IN_LOADING_INADEQUATE)
        self.assertLess(result["acceleration_factor"], 1.0)

    def test_a_run_too_short_to_remove_the_population_is_inadequate(self):
        result = assess_protection_diode_burn_in(
            _case(loading=_loading(characteristic_life_h=4000.0, duration_h=100.0))
        )
        self.assertEqual(result["verdict"], BURN_IN_LOADING_INADEQUATE)
        self.assertLess(result["screened_fraction"], 0.8)

    def test_an_unwatched_mechanism_makes_the_run_blind(self):
        result = assess_protection_diode_burn_in(
            _case(monitored_parameters=["thermal-resistance-junction-to-case"])
        )
        self.assertEqual(result["verdict"], BURN_IN_MONITORING_BLIND)
        self.assertEqual(len(result["unwatched_mechanisms"]), 2)

    def test_a_batch_shedding_too_many_units_condemns_the_lot(self):
        result = assess_protection_diode_burn_in(
            _case(outcome={"batch_size": 100, "failed_units": 12})
        )
        self.assertEqual(result["verdict"], BURN_IN_LOT_REJECTED)
        self.assertFalse(result["lot_accepted"])

    def test_a_failure_share_exactly_on_the_reject_limit_is_accepted(self):
        result = assess_protection_diode_burn_in(
            _case(outcome={"batch_size": 100, "failed_units": 5})
        )
        self.assertEqual(result["verdict"], EARLY_LIFE_FAILURES_SCREENED)
        self.assertTrue(result["lot_accepted"])

    def test_every_inadequacy_is_reported_not_only_the_first(self):
        result = assess_protection_diode_burn_in(
            _case(
                loading=_loading(case_temperature_c=170.0, duration_h=1.0),
                monitored_parameters=[],
                outcome={"batch_size": 100, "failed_units": 40},
            )
        )
        self.assertEqual(result["verdict"], BURN_IN_LOADING_INADEQUATE)
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_an_absent_mechanism_inventory_rejected(self):
        case = _case()
        del case["early_life_mechanisms"]
        with self.assertRaises(ValueError):
            assess_protection_diode_burn_in(case)

    def test_a_missing_outcome_block_rejected(self):
        case = _case()
        del case["outcome"]
        with self.assertRaises(ValueError):
            assess_protection_diode_burn_in(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_burn_in(["loading"])

    def test_a_non_mapping_loading_rejected(self):
        with self.assertRaises(ValueError):
            assess_protection_diode_burn_in(_case(loading=[48.0]))


if __name__ == "__main__":
    unittest.main()
