#!/usr/bin/env python3
"""Contract test for on-state and off-state reverse-current withstand (offline)."""

import copy
import unittest

from e2020_reverse_current_withstand_capability_logic import (
    DEFAULT_WITHSTAND_POLICY,
    PULSE_SHAPES,
    RELATIVE_TOLERANCE,
    STATES,
    assess_reverse_current_withstand,
    assess_state,
    node_excursion_v,
    pulse_shape_factors,
    recommended_withstand_current_a,
    reverse_charge_c,
    reverse_energy_j,
    rms_reverse_current_a,
    validate_withstand_policy,
)

# A 3 A outlet feeding a small inductive load that kicks back when it is cut.
TOLERANT_OUTLET = {
    "rated_output_current_a": 3.0,
    "output_capacitance_f": 470.0e-6,
    "excursion_limit_v": 6.0,
    "clamp_voltage_v": 32.0,
    "states": {
        "on": {
            "pulse": {
                "peak_a": 2.5,
                "duration_s": 0.002,
                "shape": "triangular",
                "period_s": 1.0,
            },
            "capability": {
                "withstand_current_a": 4.0,
                "withstand_duration_s": 0.050,
                "continuous_current_a": 1.0,
            },
        },
        "off": {
            "pulse": {
                "peak_a": 1.2,
                "duration_s": 0.002,
                "shape": "exponential",
                "period_s": 2.0,
            },
            "capability": {
                "withstand_current_a": 2.0,
                "withstand_duration_s": 0.100,
                "continuous_current_a": 0.5,
            },
        },
    },
}


def _outlet(**overrides):
    case = copy.deepcopy(TOLERANT_OUTLET)
    case.update(overrides)
    return case


def _with_off(**pulse_or_capability):
    case = copy.deepcopy(TOLERANT_OUTLET)
    for key, value in pulse_or_capability.items():
        target, field = key.split("__", 1)
        case["states"]["off"][target][field] = value
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_withstand_policy(DEFAULT_WITHSTAND_POLICY), DEFAULT_WITHSTAND_POLICY
        )

    def test_both_states_are_named(self):
        self.assertEqual(set(STATES), {"on", "off"})

    def test_a_policy_missing_the_off_state_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_WITHSTAND_POLICY)
        del broken["recommended_fraction"]["off"]
        with self.assertRaises(ValueError):
            validate_withstand_policy(broken)

    def test_a_non_positive_fraction_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_WITHSTAND_POLICY)
        broken["recommended_fraction"]["on"] = 0.0
        with self.assertRaises(ValueError):
            validate_withstand_policy(broken)

    def test_the_on_state_recommendation_is_the_full_rating(self):
        self.assertAlmostEqual(recommended_withstand_current_a(3.0, "on"), 3.0, places=9)

    def test_the_off_state_recommendation_is_lower_than_the_on_state(self):
        self.assertLess(
            recommended_withstand_current_a(3.0, "off"),
            recommended_withstand_current_a(3.0, "on"),
        )

    def test_an_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            recommended_withstand_current_a(3.0, "standby")


class PulseConversionTests(unittest.TestCase):
    def test_every_shape_carries_both_factors(self):
        for shape in PULSE_SHAPES:
            factors = pulse_shape_factors(shape)
            self.assertIn("charge", factors)
            self.assertIn("mean_square", factors)

    def test_an_unknown_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            pulse_shape_factors("sawtooth-with-ringing")

    def test_a_rectangular_pulse_charge_is_peak_times_duration(self):
        self.assertAlmostEqual(reverse_charge_c(2.0, 0.005, "rectangular"), 0.01, places=12)

    def test_a_triangular_pulse_carries_half_the_charge(self):
        self.assertAlmostEqual(
            reverse_charge_c(2.0, 0.005, "triangular"),
            0.5 * reverse_charge_c(2.0, 0.005, "rectangular"),
            places=12,
        )

    def test_a_zero_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            reverse_charge_c(0.0, 0.005, "rectangular")

    def test_a_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            reverse_charge_c(2.0, -0.005, "rectangular")

    def test_clamp_energy_is_the_clamp_voltage_times_the_charge(self):
        self.assertAlmostEqual(
            reverse_energy_j(2.0, 0.005, "rectangular", 32.0), 0.32, places=12
        )

    def test_node_excursion_is_charge_over_capacitance(self):
        self.assertAlmostEqual(node_excursion_v(0.0047, 470.0e-6), 10.0, places=9)

    def test_a_zero_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            node_excursion_v(0.0047, 0.0)

    def test_a_rectangular_pulse_at_unity_duty_gives_the_peak_as_rms(self):
        self.assertAlmostEqual(
            rms_reverse_current_a(2.0, 1.0, 1.0, "rectangular"), 2.0, places=9
        )

    def test_a_sparse_pulse_train_has_a_small_rms(self):
        self.assertLess(rms_reverse_current_a(2.0, 0.002, 2.0, "exponential"), 0.1)

    def test_a_period_shorter_than_the_pulse_is_rejected(self):
        with self.assertRaises(ValueError):
            rms_reverse_current_a(2.0, 0.5, 0.2, "rectangular")


class SingleStateTests(unittest.TestCase):
    def test_a_covered_on_state_is_tolerated(self):
        case = TOLERANT_OUTLET["states"]["on"]
        result = assess_state(
            "on", case["pulse"], case["capability"], 3.0, 470.0e-6, 6.0, 32.0
        )
        self.assertTrue(result["tolerated"])
        self.assertEqual(result["findings"], [])

    def test_a_capability_exactly_on_the_recommended_level_passes(self):
        case = copy.deepcopy(TOLERANT_OUTLET["states"]["on"])
        case["capability"]["withstand_current_a"] = 3.0
        case["pulse"]["peak_a"] = 2.5
        result = assess_state(
            "on", case["pulse"], case["capability"], 3.0, 470.0e-6, 6.0, 32.0
        )
        coverage = [
            c for c in result["checks"] if c["name"].endswith("recommended-level-coverage")
        ][0]
        self.assertAlmostEqual(coverage["value"], coverage["limit"], places=9)
        self.assertTrue(coverage["passed"])

    def test_the_repetitive_check_is_dropped_without_a_period(self):
        case = copy.deepcopy(TOLERANT_OUTLET["states"]["on"])
        del case["pulse"]["period_s"]
        result = assess_state(
            "on", case["pulse"], case["capability"], 3.0, 470.0e-6, 6.0, 32.0
        )
        self.assertIsNone(result["repetitive_rms_current_a"])
        self.assertNotIn(
            "on-state-repetitive-rms-current", [c["name"] for c in result["checks"]]
        )

    def test_a_pulse_missing_its_shape_is_rejected(self):
        case = copy.deepcopy(TOLERANT_OUTLET["states"]["on"])
        del case["pulse"]["shape"]
        with self.assertRaises(ValueError):
            assess_state("on", case["pulse"], case["capability"], 3.0, 470.0e-6, 6.0, 32.0)

    def test_a_capability_missing_its_duration_is_rejected(self):
        case = copy.deepcopy(TOLERANT_OUTLET["states"]["on"])
        del case["capability"]["withstand_duration_s"]
        with self.assertRaises(ValueError):
            assess_state("on", case["pulse"], case["capability"], 3.0, 470.0e-6, 6.0, 32.0)

    def test_a_non_mapping_pulse_is_rejected(self):
        case = TOLERANT_OUTLET["states"]["on"]
        with self.assertRaises(ValueError):
            assess_state("on", "2.5 A for 2 ms", case["capability"], 3.0, 470.0e-6, 6.0, 32.0)


class OutletTests(unittest.TestCase):
    def test_the_tolerant_outlet_passes_in_both_states(self):
        result = assess_reverse_current_withstand(TOLERANT_OUTLET)
        self.assertEqual(result["verdict"], "reverse-current-tolerated")
        self.assertTrue(result["tolerated"])
        self.assertEqual(result["findings"], [])
        self.assertFalse(result["blocking_element_recommended"])

    def test_both_states_are_reported_separately(self):
        result = assess_reverse_current_withstand(TOLERANT_OUTLET)
        self.assertEqual(set(result["states"]), {"on", "off"})
        self.assertNotEqual(
            result["states"]["on"]["recommended_withstand_current_a"],
            result["states"]["off"]["recommended_withstand_current_a"],
        )

    def test_an_off_state_peak_above_the_capability_calls_for_a_blocking_element(self):
        result = assess_reverse_current_withstand(_with_off(pulse__peak_a=3.5))
        self.assertFalse(result["tolerated"])
        self.assertTrue(result["blocking_element_recommended"])
        self.assertTrue(any("blocking or bypass element" in f for f in result["findings"]))

    def test_an_off_state_capability_below_the_recommendation_is_named(self):
        result = assess_reverse_current_withstand(_with_off(capability__withstand_current_a=1.0))
        self.assertFalse(result["tolerated"])
        self.assertTrue(
            any("below the recommended level" in f for f in result["findings"])
        )

    def test_a_passing_on_state_does_not_rescue_a_failing_off_state(self):
        result = assess_reverse_current_withstand(_with_off(pulse__peak_a=3.5))
        self.assertTrue(result["states"]["on"]["tolerated"])
        self.assertFalse(result["states"]["off"]["tolerated"])
        self.assertFalse(result["tolerated"])

    def test_a_long_pulse_breaks_the_node_excursion_limit(self):
        result = assess_reverse_current_withstand(_with_off(pulse__duration_s=0.02))
        excursion = [
            c
            for c in result["states"]["off"]["checks"]
            if c["name"] == "off-state-output-node-excursion"
        ][0]
        self.assertFalse(excursion["passed"])
        self.assertFalse(result["tolerated"])

    def test_a_pulse_longer_than_the_declared_withstand_time_fails(self):
        result = assess_reverse_current_withstand(_with_off(pulse__duration_s=0.5))
        failed = [c["name"] for c in result["states"]["off"]["checks"] if not c["passed"]]
        self.assertIn("off-state-applied-duration", failed)

    def test_a_larger_holdup_capacitance_lowers_the_excursion(self):
        small = assess_reverse_current_withstand(TOLERANT_OUTLET)
        large = assess_reverse_current_withstand(_outlet(output_capacitance_f=4700.0e-6))
        self.assertLess(
            large["states"]["off"]["output_node_excursion_v"],
            small["states"]["off"]["output_node_excursion_v"],
        )

    def test_an_outlet_declaring_only_the_on_state_is_rejected(self):
        case = copy.deepcopy(TOLERANT_OUTLET)
        del case["states"]["off"]
        with self.assertRaises(ValueError):
            assess_reverse_current_withstand(case)

    def test_a_state_without_a_capability_is_rejected(self):
        case = copy.deepcopy(TOLERANT_OUTLET)
        del case["states"]["off"]["capability"]
        with self.assertRaises(ValueError):
            assess_reverse_current_withstand(case)

    def test_a_missing_top_level_key_is_rejected(self):
        case = copy.deepcopy(TOLERANT_OUTLET)
        del case["clamp_voltage_v"]
        with self.assertRaises(ValueError):
            assess_reverse_current_withstand(case)

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_reverse_current_withstand("a 3 A outlet")

    def test_the_clamp_energy_is_reported_for_both_states(self):
        result = assess_reverse_current_withstand(TOLERANT_OUTLET)
        for state in STATES:
            self.assertGreater(result["states"][state]["clamp_energy_j"], 0.0)

    def test_the_relative_tolerance_stays_small_and_positive(self):
        self.assertGreater(RELATIVE_TOLERANCE, 0.0)
        self.assertLess(RELATIVE_TOLERANCE, 1e-9)


if __name__ == "__main__":
    unittest.main()
