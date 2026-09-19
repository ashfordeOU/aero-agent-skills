#!/usr/bin/env python3
"""Gate 3 contract test for e2021-actuator-voltage-withstand.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2021_actuator_voltage_withstand.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2021_actuator_voltage_withstand_logic import (  # noqa: E402
    ASYMMETRY_RATIO,
    REQUIRED_SIDES,
    actuator_current_a,
    categorize_withstand,
    dissipation_w,
    evaluate_actuator_withstand,
    parallel_resistance_ohm,
    terminal_voltage_v,
    within_limit,
    withstand_margin_ratio,
    worst_case_source_voltage_v,
)


def codes(result):
    return sorted(f["code"] for f in result["findings"])


class TestSourceEnvelope(unittest.TestCase):
    def test_nominal_bus_with_no_tolerance(self):
        self.assertAlmostEqual(worst_case_source_voltage_v(28.0), 28.0, places=12)

    def test_upper_tolerance_raises_the_envelope(self):
        self.assertAlmostEqual(
            worst_case_source_voltage_v(28.0, 0.05), 29.4, places=12
        )

    def test_transient_adds_on_top_of_tolerance(self):
        self.assertAlmostEqual(
            worst_case_source_voltage_v(100.0, 0.10, 5.0), 115.0, places=12
        )

    def test_tolerance_of_one_or_more_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_source_voltage_v(28.0, 1.0)

    def test_negative_transient_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_source_voltage_v(28.0, 0.0, -1.0)

    def test_zero_bus_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_source_voltage_v(0.0)

    def test_boolean_bus_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_source_voltage_v(True)


class TestTerminalVoltage(unittest.TestCase):
    def test_zero_line_resistance_delivers_the_whole_source(self):
        self.assertAlmostEqual(terminal_voltage_v(28.0, 0.0, 10.0), 28.0, places=12)

    def test_equal_line_and_actuator_halve_the_source(self):
        self.assertAlmostEqual(terminal_voltage_v(28.0, 10.0, 10.0), 14.0, places=12)

    def test_larger_line_drop_protects_the_actuator(self):
        self.assertLess(
            terminal_voltage_v(28.0, 4.0, 10.0), terminal_voltage_v(28.0, 1.0, 10.0)
        )

    def test_negative_line_resistance_rejected(self):
        with self.assertRaises(ValueError):
            terminal_voltage_v(28.0, -1.0, 10.0)

    def test_zero_actuator_resistance_rejected(self):
        with self.assertRaises(ValueError):
            terminal_voltage_v(28.0, 1.0, 0.0)

    def test_non_numeric_source_rejected(self):
        with self.assertRaises(ValueError):
            terminal_voltage_v("28", 1.0, 10.0)


class TestDualPath(unittest.TestCase):
    def test_two_equal_paths_halve_the_line_resistance(self):
        self.assertAlmostEqual(parallel_resistance_ohm(2.0, 2.0), 1.0, places=12)

    def test_a_zero_path_shorts_the_pair(self):
        self.assertAlmostEqual(parallel_resistance_ohm(0.0, 5.0), 0.0, places=12)

    def test_both_paths_zero_is_zero(self):
        self.assertAlmostEqual(parallel_resistance_ohm(0.0, 0.0), 0.0, places=12)

    def test_parallel_pair_raises_the_terminal_voltage(self):
        single = terminal_voltage_v(28.0, 2.0, 10.0)
        pair = terminal_voltage_v(28.0, parallel_resistance_ohm(2.0, 2.0), 10.0)
        self.assertGreater(pair, single)

    def test_negative_path_rejected(self):
        with self.assertRaises(ValueError):
            parallel_resistance_ohm(-1.0, 2.0)


class TestCurrentAndPower(unittest.TestCase):
    def test_current_follows_ohms_law(self):
        self.assertAlmostEqual(actuator_current_a(24.0, 12.0), 2.0, places=12)

    def test_dissipation_follows_i_squared_r(self):
        self.assertAlmostEqual(dissipation_w(2.0, 12.0), 48.0, places=12)

    def test_zero_terminal_voltage_draws_nothing(self):
        self.assertAlmostEqual(actuator_current_a(0.0, 12.0), 0.0, places=12)

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            dissipation_w(-1.0, 12.0)


class TestGrading(unittest.TestCase):
    def test_exactly_at_the_rating_is_at_rating(self):
        self.assertEqual(categorize_withstand(50.0, 50.0), "at-rating")

    def test_under_the_rating_is_within(self):
        self.assertEqual(categorize_withstand(40.0, 50.0), "within-rating")

    def test_over_the_rating_is_over(self):
        self.assertEqual(categorize_withstand(60.0, 50.0), "over-rating")

    def test_within_limit_accepts_representation_error(self):
        self.assertTrue(within_limit(0.1 + 0.2, 0.3))

    def test_within_limit_rejects_a_real_exceedance(self):
        self.assertFalse(within_limit(0.31, 0.3))

    def test_margin_ratio_is_one_at_the_rating(self):
        self.assertAlmostEqual(withstand_margin_ratio(50.0, 50.0), 1.0, places=12)

    def test_margin_ratio_rejects_zero_stress(self):
        with self.assertRaises(ValueError):
            withstand_margin_ratio(50.0, 0.0)


class TestEvaluateWithstand(unittest.TestCase):
    def base_spec(self):
        return {
            "bus_nominal_v": 28.0,
            "bus_upper_tolerance": 0.05,
            "actuator_resistance_ohm": 20.0,
            "sides": {
                "nominal": {"line_resistance_ohm": 0.5},
                "redundant": {"line_resistance_ohm": 0.5},
            },
            "rated_voltage_v": 40.0,
            "rated_current_a": 2.0,
            "rated_power_w": 60.0,
        }

    def test_symmetric_healthy_case_is_compliant(self):
        result = evaluate_actuator_withstand(self.base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_both_sides_are_reported(self):
        result = evaluate_actuator_withstand(self.base_spec())
        self.assertEqual(sorted(result["per_side"]), sorted(REQUIRED_SIDES))

    def test_lower_drop_side_governs(self):
        spec = self.base_spec()
        spec["sides"]["redundant"]["line_resistance_ohm"] = 4.0
        result = evaluate_actuator_withstand(spec)
        self.assertEqual(result["governing_side"], "nominal")

    def test_asymmetric_sides_raise_a_finding(self):
        spec = self.base_spec()
        spec["sides"]["redundant"]["line_resistance_ohm"] = 6.0
        result = evaluate_actuator_withstand(spec)
        self.assertIn("drive-side-asymmetry", codes(result))
        self.assertGreater(result["asymmetry_ratio"], ASYMMETRY_RATIO)

    def test_redundant_side_alone_can_break_the_rating(self):
        spec = self.base_spec()
        spec["rated_voltage_v"] = 28.5
        result = evaluate_actuator_withstand(spec)
        sides = [f["side"] for f in result["findings"] if "side" in f]
        self.assertIn("redundant", sides)
        self.assertFalse(result["compliant"])

    def test_dual_energisation_is_assessed_above_both_sides(self):
        spec = self.base_spec()
        spec["sides"]["nominal"]["line_resistance_ohm"] = 2.0
        spec["sides"]["redundant"]["line_resistance_ohm"] = 2.0
        result = evaluate_actuator_withstand(spec)
        dual = result["dual_energisation"]["terminal_voltage_v"]
        self.assertGreater(dual, result["per_side"]["nominal"]["terminal_voltage_v"])

    def test_dual_case_can_fail_where_each_side_passes(self):
        spec = self.base_spec()
        spec["actuator_resistance_ohm"] = 10.0
        spec["sides"]["nominal"]["line_resistance_ohm"] = 2.0
        spec["sides"]["redundant"]["line_resistance_ohm"] = 2.0
        spec["rated_voltage_v"] = 25.0
        spec.pop("rated_current_a")
        spec.pop("rated_power_w")
        result = evaluate_actuator_withstand(spec)
        self.assertEqual(codes(result), ["dual-side-voltage-over-rating"])

    def test_dual_check_can_be_switched_off(self):
        spec = self.base_spec()
        spec["check_dual_energisation"] = False
        result = evaluate_actuator_withstand(spec)
        self.assertIsNone(result["dual_energisation"])

    def test_current_rating_breach_is_reported(self):
        spec = self.base_spec()
        spec["rated_current_a"] = 1.0
        result = evaluate_actuator_withstand(spec)
        self.assertIn("current-over-rating", codes(result))

    def test_power_rating_breach_is_reported(self):
        spec = self.base_spec()
        spec["rated_power_w"] = 10.0
        result = evaluate_actuator_withstand(spec)
        self.assertIn("dissipation-over-rating", codes(result))

    def test_command_longer_than_the_rated_duration(self):
        spec = self.base_spec()
        spec["rated_duration_s"] = 1.0
        spec["command_duration_s"] = 5.0
        result = evaluate_actuator_withstand(spec)
        self.assertIn("command-longer-than-rated-duration", codes(result))

    def test_command_duration_without_a_rating_rejected(self):
        spec = self.base_spec()
        spec["command_duration_s"] = 5.0
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_missing_redundant_side_rejected(self):
        spec = self.base_spec()
        del spec["sides"]["redundant"]
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_unknown_side_rejected(self):
        spec = self.base_spec()
        spec["sides"]["standby"] = {"line_resistance_ohm": 1.0}
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_side_without_line_resistance_rejected(self):
        spec = self.base_spec()
        spec["sides"]["nominal"] = {}
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_unknown_spec_key_rejected(self):
        spec = self.base_spec()
        spec["harness_mass_kg"] = 1.2
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_missing_required_key_rejected(self):
        spec = self.base_spec()
        del spec["rated_voltage_v"]
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand([("bus_nominal_v", 28.0)])

    def test_non_mapping_side_rejected(self):
        spec = self.base_spec()
        spec["sides"]["nominal"] = 0.5
        with self.assertRaises(ValueError):
            evaluate_actuator_withstand(spec)


if __name__ == "__main__":
    unittest.main()
