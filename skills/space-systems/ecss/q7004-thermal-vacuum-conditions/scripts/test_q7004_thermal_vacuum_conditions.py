#!/usr/bin/env python3
"""Contract test for the thermal vacuum test conditions (offline)."""

import copy
import math
import unittest

from q7004_thermal_vacuum_conditions_logic import (
    BOLTZMANN_J_PER_K,
    DEFAULT_VACUUM_POLICY,
    achievable_cold_limit_k,
    assess_test_pressure,
    convection_is_negligible,
    define_vacuum_conditions,
    knudsen_number,
    mean_free_path_m,
    pump_down_sequence,
    repressurization_temperature_k,
    vacuum_dwell_time_s,
    validate_vacuum_policy,
)

GOOD_CASE = {
    "test_min_k": 223.15,
    "test_max_k": 373.15,
    "chamber_base_pressure_pa": 1.0e-4,
    "characteristic_length_m": 0.3,
    "shroud_temperature_k": 100.0,
    "time_constant_s": 1800.0,
    "stabilization_tolerance_k": 1.0,
    "hot_outgassing_soak_s": 7200.0,
    "cold_outgassing_soak_s": 3600.0,
    "dew_point_k": 283.15,
    "repressurization_item_temperature_k": 293.15,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_vacuum_policy(DEFAULT_VACUUM_POLICY), DEFAULT_VACUUM_POLICY
        )

    def test_a_policy_pressure_above_one_pascal_rejected(self):
        broken = copy.deepcopy(DEFAULT_VACUUM_POLICY)
        broken["max_test_pressure_pa"] = 10.0
        with self.assertRaises(ValueError):
            validate_vacuum_policy(broken)

    def test_a_zero_molecule_diameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_VACUUM_POLICY)
        broken["molecule_diameter_m"] = 0.0
        with self.assertRaises(ValueError):
            validate_vacuum_policy(broken)

    def test_a_negative_dew_point_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_VACUUM_POLICY)
        broken["dew_point_margin_k"] = -1.0
        with self.assertRaises(ValueError):
            validate_vacuum_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_vacuum_policy("hard vacuum")


class MeanFreePathTests(unittest.TestCase):
    def test_mean_free_path_matches_the_kinetic_theory_expression(self):
        diameter = DEFAULT_VACUUM_POLICY["molecule_diameter_m"]
        expected = BOLTZMANN_J_PER_K * 300.0 / (
            math.sqrt(2.0) * math.pi * diameter * diameter * 1.0e-4
        )
        self.assertAlmostEqual(
            mean_free_path_m(1.0e-4, 300.0) / expected, 1.0, places=9
        )

    def test_halving_the_pressure_doubles_the_mean_free_path(self):
        low = mean_free_path_m(5.0e-5, 300.0)
        high = mean_free_path_m(1.0e-4, 300.0)
        self.assertAlmostEqual(low / high, 2.0, places=9)

    def test_mean_free_path_scales_with_temperature(self):
        cold = mean_free_path_m(1.0e-4, 150.0)
        hot = mean_free_path_m(1.0e-4, 300.0)
        self.assertAlmostEqual(hot / cold, 2.0, places=9)

    def test_a_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            mean_free_path_m(0.0, 300.0)

    def test_a_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            mean_free_path_m(1.0e-4, "room temperature")


class KnudsenTests(unittest.TestCase):
    def test_knudsen_is_the_path_over_the_length(self):
        path = mean_free_path_m(1.0e-4, 300.0)
        self.assertAlmostEqual(
            knudsen_number(1.0e-4, 300.0, 0.3), path / 0.3, places=9
        )

    def test_a_hard_vacuum_is_free_molecular_across_a_small_item(self):
        self.assertTrue(
            convection_is_negligible(knudsen_number(1.0e-4, 300.0, 0.3))
        )

    def test_a_soft_vacuum_still_carries_heat(self):
        self.assertFalse(convection_is_negligible(knudsen_number(1.0, 300.0, 0.3)))

    def test_a_larger_item_lowers_the_knudsen_number(self):
        small = knudsen_number(1.0e-4, 300.0, 0.3)
        large = knudsen_number(1.0e-4, 300.0, 3.0)
        self.assertAlmostEqual(small / large, 10.0, places=9)

    def test_a_zero_characteristic_length_rejected(self):
        with self.assertRaises(ValueError):
            knudsen_number(1.0e-4, 300.0, 0.0)

    def test_a_knudsen_exactly_on_the_threshold_counts_as_free_molecular(self):
        threshold = DEFAULT_VACUUM_POLICY["free_molecular_knudsen"]
        self.assertTrue(convection_is_negligible(threshold))


class PressureAssessmentTests(unittest.TestCase):
    def test_a_good_chamber_pressure_is_acceptable(self):
        result = assess_test_pressure(1.0e-4, 373.15, 0.3)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_a_pressure_above_the_policy_is_reported(self):
        result = assess_test_pressure(1.0e-2, 373.15, 0.3)
        self.assertFalse(result["within_policy"])
        self.assertTrue(any("above the declared" in f for f in result["findings"]))

    def test_a_pressure_exactly_on_the_policy_limit_is_within_policy(self):
        result = assess_test_pressure(
            DEFAULT_VACUUM_POLICY["max_test_pressure_pa"], 373.15, 0.3
        )
        self.assertTrue(result["within_policy"])

    def test_a_large_item_at_a_soft_vacuum_is_not_free_molecular(self):
        result = assess_test_pressure(1.0, 300.0, 2.0)
        self.assertFalse(result["free_molecular"])
        self.assertTrue(any("Knudsen" in f for f in result["findings"]))

    def test_the_assessment_reports_the_mean_free_path_it_used(self):
        result = assess_test_pressure(1.0e-4, 300.0, 0.3)
        self.assertAlmostEqual(
            result["mean_free_path_m"], mean_free_path_m(1.0e-4, 300.0), places=12
        )


class ColdLimitTests(unittest.TestCase):
    def test_a_limit_above_the_shroud_is_reachable(self):
        result = achievable_cold_limit_k(100.0, 223.15)
        self.assertTrue(result["reachable"])
        self.assertAlmostEqual(result["achievable_min_k"], 223.15, places=9)

    def test_a_limit_below_the_shroud_is_not_reachable(self):
        result = achievable_cold_limit_k(180.0, 150.0)
        self.assertFalse(result["reachable"])
        self.assertAlmostEqual(result["achievable_min_k"], 180.0, places=9)

    def test_a_limit_exactly_on_the_shroud_is_reachable(self):
        result = achievable_cold_limit_k(180.0, 180.0)
        self.assertTrue(result["reachable"])

    def test_a_negative_shroud_temperature_rejected(self):
        with self.assertRaises(ValueError):
            achievable_cold_limit_k(-10.0, 150.0)


class RepressurizationTests(unittest.TestCase):
    def test_a_warm_item_is_safe_to_repressurize(self):
        result = repressurization_temperature_k(293.15, 283.15)
        self.assertTrue(result["safe"])
        self.assertAlmostEqual(result["required_k"], 293.15, places=9)

    def test_a_cold_item_is_held_to_the_guard(self):
        result = repressurization_temperature_k(273.15, 283.15)
        self.assertFalse(result["safe"])
        self.assertAlmostEqual(
            result["required_k"],
            283.15 + DEFAULT_VACUUM_POLICY["dew_point_margin_k"],
            places=9,
        )

    def test_an_item_exactly_on_the_guard_is_safe(self):
        guard = 283.15 + DEFAULT_VACUUM_POLICY["dew_point_margin_k"]
        self.assertTrue(repressurization_temperature_k(guard, 283.15)["safe"])

    def test_a_non_numeric_dew_point_rejected(self):
        with self.assertRaises(ValueError):
            repressurization_temperature_k(293.15, "ten celsius")


class VacuumDwellTests(unittest.TestCase):
    def test_dwell_is_stabilization_plus_the_outgassing_soak(self):
        dwell = vacuum_dwell_time_s(1800.0, 150.0, 1.0, 7200.0)
        expected = 1800.0 * math.log(150.0) + 7200.0
        self.assertAlmostEqual(dwell["dwell_s"] / expected, 1.0, places=9)
        self.assertEqual(dwell["set_by"], "stabilization-and-soak")

    def test_the_policy_floor_takes_over_for_a_fast_item_with_no_soak(self):
        dwell = vacuum_dwell_time_s(1.0, 150.0, 1.0, 0.0)
        self.assertAlmostEqual(
            dwell["dwell_s"], DEFAULT_VACUUM_POLICY["minimum_dwell_s"], places=9
        )
        self.assertEqual(dwell["set_by"], "policy-floor")

    def test_an_item_already_inside_tolerance_needs_no_stabilization(self):
        dwell = vacuum_dwell_time_s(1800.0, 0.5, 1.0, 7200.0)
        self.assertAlmostEqual(dwell["stabilization_s"], 0.0, places=9)

    def test_a_negative_outgassing_soak_rejected(self):
        with self.assertRaises(ValueError):
            vacuum_dwell_time_s(1800.0, 150.0, 1.0, -60.0)

    def test_a_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            vacuum_dwell_time_s(1800.0, 150.0, 0.0, 7200.0)


class SequenceTests(unittest.TestCase):
    def test_the_chamber_is_pumped_before_the_first_transition(self):
        steps = pump_down_sequence(GOOD_CASE)
        self.assertLess(
            next(i for i, s in enumerate(steps) if "pump down" in s),
            next(i for i, s in enumerate(steps) if "first temperature transition" in s),
        )

    def test_the_item_is_warmed_before_gas_is_admitted(self):
        steps = pump_down_sequence(GOOD_CASE)
        self.assertLess(
            next(i for i, s in enumerate(steps) if "dew-point guard" in s),
            next(i for i, s in enumerate(steps) if "admit dry gas" in s),
        )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            pump_down_sequence("pump then cool")


class DefinitionTests(unittest.TestCase):
    def test_the_good_case_is_an_acceptable_condition_set(self):
        result = define_vacuum_conditions(GOOD_CASE)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_a_soft_chamber_pressure_makes_the_condition_unacceptable(self):
        result = define_vacuum_conditions(
            _case(GOOD_CASE, chamber_base_pressure_pa=5.0e-2)
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("above the declared" in f for f in result["findings"]))

    def test_a_cold_limit_below_the_shroud_is_reported(self):
        result = define_vacuum_conditions(
            _case(GOOD_CASE, test_min_k=90.0, shroud_temperature_k=100.0)
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("below the shroud" in f for f in result["findings"]))

    def test_a_cold_repressurization_is_reported(self):
        result = define_vacuum_conditions(
            _case(GOOD_CASE, repressurization_item_temperature_k=273.15)
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("condense" in f for f in result["findings"]))

    def test_the_hot_dwell_is_longer_than_the_cold_one_here(self):
        result = define_vacuum_conditions(GOOD_CASE)
        self.assertGreater(
            result["hot_dwell"]["dwell_s"], result["cold_dwell"]["dwell_s"]
        )

    def test_every_condition_set_carries_the_hold_pressure_duty(self):
        result = define_vacuum_conditions(GOOD_CASE)
        self.assertTrue(any("whole run" in duty for duty in result["duties"]))

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            define_vacuum_conditions(_case(GOOD_CASE, test_min_k=400.0))

    def test_a_case_without_a_characteristic_length_rejected(self):
        case = _case(GOOD_CASE)
        del case["characteristic_length_m"]
        with self.assertRaises(ValueError):
            define_vacuum_conditions(case)

    def test_a_case_without_a_dew_point_rejected(self):
        case = _case(GOOD_CASE)
        del case["dew_point_k"]
        with self.assertRaises(ValueError):
            define_vacuum_conditions(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            define_vacuum_conditions("hard vacuum, hot and cold")


if __name__ == "__main__":
    unittest.main()
