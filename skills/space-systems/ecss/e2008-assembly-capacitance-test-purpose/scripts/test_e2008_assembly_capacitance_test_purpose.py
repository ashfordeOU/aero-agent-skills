"""Contract tests for the clause 5.5.3.5.1 assembly capacitance purpose logic."""

import math
import unittest

from e2008_assembly_capacitance_test_purpose_logic import (
    CHARACTERISATION_NOT_REQUIRED,
    COMMON_OBJECTIVE,
    DEFAULT_CAPACITANCE_POLICY,
    DYNAMIC_BEHAVIOUR_CHARACTERISED,
    MEASUREMENT_INADEQUATE,
    MEASUREMENT_NOT_PLANNED,
    assembly_capacitance_f,
    assess_assembly_capacitance_purpose,
    behaviour_inventory,
    bias_matches_working_point,
    bridge_can_measure,
    bridge_impedance_ohm,
    characterisation_objectives,
    displacement_current_a,
    series_string_capacitance_f,
    stored_charge_c,
    switching_time_constant_s,
    validate_capacitance_policy,
)

BEHAVIOURS = [
    "array-regulator-loop-stability",
    "array-shunt-switching-transient",
]


def _policy(**overrides):
    policy = dict(DEFAULT_CAPACITANCE_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "dynamic_behaviours": list(BEHAVIOURS),
        "assembly": {
            "cell_capacitance_f": 2.4e-6,
            "cells_in_series": 24,
            "strings_in_parallel": 8,
            "working_point_v": 100.0,
            "source_resistance_ohm": 2.0,
            "step_rate_v_per_s": 1.0e5,
        },
        "measurement": {"frequency_hz": 1.0e3, "bias_voltage_v": 100.0},
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_capacitance_policy(DEFAULT_CAPACITANCE_POLICY),
            DEFAULT_CAPACITANCE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_policy("trigger")

    def test_inverted_meter_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_policy(
                _policy(meter_min_impedance_ohm=1.0e7, meter_max_impedance_ohm=1.0)
            )

    def test_zero_significance_trigger_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_policy(_policy(significance_trigger_f=0.0))

    def test_negative_bias_offset_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_capacitance_policy(_policy(max_bias_offset_v=-1.0))


class GeometryTests(unittest.TestCase):
    def test_series_cells_divide_the_cell_capacitance(self):
        self.assertAlmostEqual(
            _ratio(series_string_capacitance_f(2.4e-6, 24), 1.0e-7), 1.0, places=12
        )

    def test_parallel_strings_multiply_the_string_capacitance(self):
        self.assertAlmostEqual(
            _ratio(assembly_capacitance_f(2.4e-6, 24, 8), 8.0e-7), 1.0, places=12
        )

    def test_a_single_cell_string_is_the_cell_capacitance(self):
        self.assertAlmostEqual(
            _ratio(series_string_capacitance_f(2.4e-6, 1), 2.4e-6), 1.0, places=12
        )

    def test_doubling_the_series_count_halves_the_string_capacitance(self):
        long_string = series_string_capacitance_f(2.4e-6, 48)
        short_string = series_string_capacitance_f(2.4e-6, 24)
        self.assertAlmostEqual(_ratio(short_string, 2.0 * long_string), 1.0, places=12)

    def test_fractional_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            series_string_capacitance_f(2.4e-6, 24.5)

    def test_zero_string_count_rejected(self):
        with self.assertRaises(ValueError):
            assembly_capacitance_f(2.4e-6, 24, 0)

    def test_boolean_cell_capacitance_rejected(self):
        with self.assertRaises(ValueError):
            series_string_capacitance_f(True, 24)


class DynamicQuantityTests(unittest.TestCase):
    def test_displacement_current_is_capacitance_times_rate(self):
        self.assertAlmostEqual(
            _ratio(displacement_current_a(8.0e-7, 1.0e5), 0.08), 1.0, places=12
        )

    def test_a_falling_step_gives_a_negative_displacement_current(self):
        self.assertLess(displacement_current_a(8.0e-7, -1.0e5), 0.0)

    def test_stored_charge_is_capacitance_times_voltage(self):
        self.assertAlmostEqual(
            _ratio(stored_charge_c(8.0e-7, 100.0), 8.0e-5), 1.0, places=12
        )

    def test_time_constant_is_the_rc_product(self):
        self.assertAlmostEqual(
            _ratio(switching_time_constant_s(8.0e-7, 2.0), 1.6e-6), 1.0, places=12
        )

    def test_zero_source_resistance_rejected(self):
        with self.assertRaises(ValueError):
            switching_time_constant_s(8.0e-7, 0.0)

    def test_non_finite_step_rate_rejected(self):
        with self.assertRaises(ValueError):
            displacement_current_a(8.0e-7, float("nan"))


class BridgeTests(unittest.TestCase):
    def test_impedance_follows_the_reactance_formula(self):
        expected = 1.0 / (2.0 * math.pi * 1.0e3 * 8.0e-7)
        self.assertAlmostEqual(
            _ratio(bridge_impedance_ohm(8.0e-7, 1.0e3), expected), 1.0, places=12
        )

    def test_raising_the_frequency_lowers_the_impedance(self):
        low = bridge_impedance_ohm(8.0e-7, 1.0e3)
        high = bridge_impedance_ohm(8.0e-7, 1.0e5)
        self.assertLess(high, low)

    def test_an_impedance_inside_the_range_is_measurable(self):
        self.assertTrue(bridge_can_measure(1.0e3, _policy()))

    def test_an_impedance_exactly_at_the_range_ceiling_is_measurable(self):
        policy = _policy()
        self.assertTrue(
            bridge_can_measure(policy["meter_max_impedance_ohm"], policy)
        )

    def test_an_impedance_above_the_ceiling_is_not_measurable(self):
        self.assertFalse(bridge_can_measure(1.0e9, _policy()))

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            bridge_impedance_ohm(8.0e-7, 0.0)

    def test_a_bias_at_the_working_point_is_representative(self):
        self.assertTrue(bias_matches_working_point(100.0, 100.0, _policy()))

    def test_a_bias_exactly_at_the_offset_allowance_is_representative(self):
        policy = _policy(max_bias_offset_v=5.0)
        self.assertAlmostEqual(abs(105.0 - 100.0), policy["max_bias_offset_v"],
                               places=9)
        self.assertTrue(bias_matches_working_point(105.0, 100.0, policy))

    def test_a_bias_far_from_the_working_point_is_not_representative(self):
        self.assertFalse(bias_matches_working_point(0.0, 100.0, _policy()))


class ObjectiveTests(unittest.TestCase):
    def test_each_behaviour_contributes_an_objective(self):
        objectives = characterisation_objectives(BEHAVIOURS)
        self.assertIn("assembly-capacitance-load-pole", objectives)
        self.assertIn("shunt-switching-displacement-current", objectives)

    def test_the_shared_objective_is_appended_once(self):
        objectives = characterisation_objectives(BEHAVIOURS)
        self.assertEqual(objectives.count(COMMON_OBJECTIVE), 1)

    def test_no_behaviour_yields_no_objective(self):
        self.assertEqual(characterisation_objectives([]), ())

    def test_a_repeated_behaviour_is_grouped_once(self):
        grouped = behaviour_inventory(
            ["array-regulator-loop-stability", "array-regulator-loop-stability"]
        )
        self.assertEqual(grouped, ("array-regulator-loop-stability",))

    def test_unknown_behaviour_rejected(self):
        with self.assertRaises(ValueError):
            behaviour_inventory(["array-eclipse-entry"])

    def test_non_collection_behaviour_list_rejected(self):
        with self.assertRaises(ValueError):
            behaviour_inventory("array-regulator-loop-stability")


class PurposeAssessmentTests(unittest.TestCase):
    def test_an_adequate_measurement_characterises_the_behaviour(self):
        result = assess_assembly_capacitance_purpose(_case())
        self.assertEqual(result["verdict"], DYNAMIC_BEHAVIOUR_CHARACTERISED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["required"])

    def test_the_assembly_capacitance_is_reported(self):
        result = assess_assembly_capacitance_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["assembly_capacitance_f"], 8.0e-7), 1.0, places=12
        )

    def test_the_dynamic_quantities_are_derived_from_the_assembly_value(self):
        result = assess_assembly_capacitance_purpose(_case())
        self.assertAlmostEqual(
            _ratio(result["displacement_current_a"], 0.08), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["stored_charge_c"], 8.0e-5), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["switching_time_constant_s"], 1.6e-6), 1.0, places=12
        )

    def test_no_declared_behaviour_means_no_characterisation_required(self):
        result = assess_assembly_capacitance_purpose(_case(dynamic_behaviours=[]))
        self.assertEqual(result["verdict"], CHARACTERISATION_NOT_REQUIRED)
        self.assertFalse(result["required"])

    def test_a_negligible_capacitance_does_not_earn_the_measurement(self):
        case = _case()
        case["assembly"]["cell_capacitance_f"] = 2.4e-12
        result = assess_assembly_capacitance_purpose(case)
        self.assertEqual(result["verdict"], CHARACTERISATION_NOT_REQUIRED)

    def test_a_capacitance_exactly_at_the_trigger_earns_the_measurement(self):
        policy = _policy(significance_trigger_f=8.0e-7)
        result = assess_assembly_capacitance_purpose(_case(), policy)
        self.assertAlmostEqual(
            _ratio(result["assembly_capacitance_f"], policy["significance_trigger_f"]),
            1.0,
            places=12,
        )
        self.assertTrue(result["required"])

    def test_a_required_but_unplanned_measurement_is_its_own_verdict(self):
        case = _case()
        del case["measurement"]
        result = assess_assembly_capacitance_purpose(case)
        self.assertEqual(result["verdict"], MEASUREMENT_NOT_PLANNED)
        self.assertIsNone(result["bridge_impedance_ohm"])

    def test_an_out_of_range_bridge_frequency_is_inadequate(self):
        result = assess_assembly_capacitance_purpose(
            _case(measurement={"frequency_hz": 1.0e-3, "bias_voltage_v": 100.0})
        )
        self.assertEqual(result["verdict"], MEASUREMENT_INADEQUATE)
        self.assertFalse(result["bridge_in_range"])

    def test_an_unrepresentative_bias_is_inadequate(self):
        result = assess_assembly_capacitance_purpose(
            _case(measurement={"frequency_hz": 1.0e3, "bias_voltage_v": 0.0})
        )
        self.assertEqual(result["verdict"], MEASUREMENT_INADEQUATE)
        self.assertFalse(result["bias_representative"])

    def test_both_inadequacies_are_reported_not_only_the_first(self):
        result = assess_assembly_capacitance_purpose(
            _case(measurement={"frequency_hz": 1.0e-3, "bias_voltage_v": 0.0})
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_objectives_survive_an_unplanned_measurement(self):
        case = _case()
        del case["measurement"]
        result = assess_assembly_capacitance_purpose(case)
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_absent_behaviour_key_rejected(self):
        case = _case()
        del case["dynamic_behaviours"]
        with self.assertRaises(ValueError):
            assess_assembly_capacitance_purpose(case)

    def test_missing_assembly_block_rejected(self):
        case = _case()
        del case["assembly"]
        with self.assertRaises(ValueError):
            assess_assembly_capacitance_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_capacitance_purpose(["dynamic_behaviours"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_capacitance_purpose(_case(measurement=[1.0e3]))


if __name__ == "__main__":
    unittest.main()
