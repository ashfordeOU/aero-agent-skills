#!/usr/bin/env python3
"""Gate 3 contract test for e2021-actuator-interface-compatibility-conditions.

Stdlib unittest only, offline, deterministic. Every corner current that lands
exactly on a window limit is asserted with assertAlmostEqual against the limit
and on the decision the logic then takes, never with a strict inequality whose
truth would depend on the last bit of a division.
"""

import unittest

from e2021_actuator_interface_compatibility_conditions_logic import (
    CURRENT_EPS,
    DEFAULT_INTERFACE_SPEC,
    HIGH_CORNER,
    LOW_CORNER,
    admissible_drive_band,
    compatibility_status,
    corner_currents,
    evaluate_interface,
    evaluate_line,
    firing_current,
    line_headroom_a,
    loop_resistance,
    resistance_band,
    resistance_spread_is_admissible,
    resolve_spec,
    worst_line,
)


def nominal_line():
    return {
        "name": "separation-nut-primary",
        "drive_voltage_min_v": 28.0,
        "drive_voltage_max_v": 30.0,
        "actuator_resistance": {"min_ohm": 3.0, "max_ohm": 5.5},
        "harness_resistance": {"min_ohm": 0.5, "max_ohm": 0.9},
        "source_resistance": {"min_ohm": 0.5, "max_ohm": 0.6},
    }


def second_line():
    line = nominal_line()
    line["name"] = "separation-nut-redundant"
    line["drive_voltage_min_v"] = 26.0
    return line


def nominal_config():
    return {"lines": [nominal_line(), second_line()]}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["min_firing_current_a"], 3.5, places=9)
        self.assertEqual(set(spec), set(DEFAULT_INTERFACE_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"max_firing_current_a": 12.0})
        self.assertAlmostEqual(spec["max_firing_current_a"], 12.0, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"max_firing_current_a": 12.0})
        self.assertAlmostEqual(
            DEFAULT_INTERFACE_SPEC["max_firing_current_a"], 8.0, places=9
        )

    def test_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_firing_voltage_v": 3.0})

    def test_non_positive_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_firing_current_a": 0.0})

    def test_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"min_firing_current_a": 9.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("min_firing_current_a", 3.0)])


class TestResistanceInputs(unittest.TestCase):
    def test_a_band_returns_its_two_ends(self):
        self.assertEqual(
            resistance_band({"min_ohm": 1.0, "max_ohm": 2.0}, "actuator"), (1.0, 2.0)
        )

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            resistance_band({"min_ohm": 2.0, "max_ohm": 1.0}, "actuator")

    def test_a_negative_band_end_is_rejected(self):
        with self.assertRaises(ValueError):
            resistance_band({"min_ohm": -0.1, "max_ohm": 1.0}, "actuator")

    def test_a_non_mapping_band_is_rejected(self):
        with self.assertRaises(ValueError):
            resistance_band([1.0, 2.0], "actuator")

    def test_the_loop_is_the_sum_of_its_three_parts(self):
        self.assertAlmostEqual(loop_resistance(3.0, 0.5, 0.5), 4.0, places=9)

    def test_an_all_zero_loop_is_rejected(self):
        with self.assertRaises(ValueError):
            loop_resistance(0.0, 0.0, 0.0)

    def test_a_negative_harness_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            loop_resistance(3.0, -0.5, 0.5)


class TestFiringCurrent(unittest.TestCase):
    def test_ohms_law_across_the_loop(self):
        self.assertAlmostEqual(firing_current(30.0, 4.0), 7.5, places=9)

    def test_zero_drive_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            firing_current(0.0, 4.0)

    def test_zero_loop_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            firing_current(30.0, 0.0)

    def test_a_non_numeric_drive_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            firing_current("30.0", 4.0)

    def test_an_infinite_drive_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            firing_current(float("inf"), 4.0)


class TestCorners(unittest.TestCase):
    def test_the_high_corner_pairs_the_top_voltage_with_the_low_loop(self):
        corners = corner_currents(nominal_line())
        self.assertAlmostEqual(corners["loop_resistance_min_ohm"], 4.0, places=9)
        self.assertAlmostEqual(corners[HIGH_CORNER], 7.5, places=9)

    def test_the_low_corner_pairs_the_bottom_voltage_with_the_high_loop(self):
        corners = corner_currents(nominal_line())
        self.assertAlmostEqual(corners["loop_resistance_max_ohm"], 7.0, places=9)
        self.assertAlmostEqual(corners[LOW_CORNER], 4.0, places=9)

    def test_an_inverted_drive_band_is_rejected(self):
        line = nominal_line()
        line["drive_voltage_max_v"] = 20.0
        with self.assertRaises(ValueError):
            corner_currents(line)

    def test_a_non_mapping_line_is_rejected(self):
        with self.assertRaises(ValueError):
            corner_currents(["separation-nut-primary"])


class TestLineVerdict(unittest.TestCase):
    def test_a_nominal_line_is_compatible(self):
        result = evaluate_line(nominal_line())
        self.assertTrue(result["compatible"])
        self.assertEqual(result["violated_corners"], [])

    def test_a_high_corner_exactly_on_the_ceiling_is_compatible(self):
        line = nominal_line()
        line["drive_voltage_max_v"] = 32.0
        result = evaluate_line(line)
        self.assertAlmostEqual(result[HIGH_CORNER], 8.0, places=9)
        self.assertAlmostEqual(result["max_firing_current_a"], 8.0, places=9)
        self.assertTrue(result["compatible"])
        self.assertAlmostEqual(result["ceiling_excess_a"], 0.0, places=9)

    def test_a_low_corner_exactly_on_the_floor_is_compatible(self):
        line = nominal_line()
        line["drive_voltage_min_v"] = 24.5
        result = evaluate_line(line)
        self.assertAlmostEqual(result[LOW_CORNER], 3.5, places=9)
        self.assertAlmostEqual(result["min_firing_current_a"], 3.5, places=9)
        self.assertTrue(result["compatible"])
        self.assertAlmostEqual(result["floor_shortfall_a"], 0.0, places=9)

    def test_a_low_corner_under_the_floor_is_a_violation(self):
        line = nominal_line()
        line["drive_voltage_min_v"] = 21.0
        result = evaluate_line(line)
        self.assertEqual(result["violated_corners"], [LOW_CORNER])
        self.assertAlmostEqual(result["floor_shortfall_a"], 0.5, places=9)

    def test_a_high_corner_over_the_ceiling_is_a_violation(self):
        line = nominal_line()
        line["drive_voltage_max_v"] = 40.0
        result = evaluate_line(line)
        self.assertEqual(result["violated_corners"], [HIGH_CORNER])
        self.assertAlmostEqual(result["ceiling_excess_a"], 2.0, places=9)

    def test_the_nominal_sum_can_pass_while_a_corner_fails(self):
        line = nominal_line()
        line["drive_voltage_max_v"] = 40.0
        nominal_current = firing_current(
            (line["drive_voltage_min_v"] + line["drive_voltage_max_v"]) / 2.0,
            (4.0 + 7.0) / 2.0,
        )
        self.assertAlmostEqual(nominal_current, 34.0 / 5.5, places=9)
        self.assertFalse(evaluate_line(line)["compatible"])

    def test_a_line_without_a_name_is_rejected(self):
        line = nominal_line()
        line["name"] = "   "
        with self.assertRaises(ValueError):
            evaluate_line(line)


class TestAdmissibleDriveBand(unittest.TestCase):
    def test_the_band_ends_come_from_the_two_loop_extremes(self):
        band = admissible_drive_band(corner_currents(nominal_line()))
        self.assertAlmostEqual(band["lowest_admissible_drive_v"], 24.5, places=9)
        self.assertAlmostEqual(band["highest_admissible_drive_v"], 32.0, places=9)
        self.assertTrue(band["feasible"])

    def test_a_spread_too_wide_for_the_window_is_infeasible(self):
        line = nominal_line()
        line["actuator_resistance"] = {"min_ohm": 3.0, "max_ohm": 18.5}
        self.assertFalse(resistance_spread_is_admissible(line))

    def test_a_band_whose_ends_coincide_is_still_feasible(self):
        line = nominal_line()
        line["actuator_resistance"] = {"min_ohm": 3.0, "max_ohm": 7.1428571428571}
        band = admissible_drive_band(corner_currents(line))
        self.assertTrue(
            band["lowest_admissible_drive_v"]
            <= band["highest_admissible_drive_v"] + CURRENT_EPS
        )

    def test_incomplete_corners_are_rejected(self):
        with self.assertRaises(ValueError):
            admissible_drive_band({"loop_resistance_min_ohm": 4.0})

    def test_non_mapping_corners_are_rejected(self):
        with self.assertRaises(ValueError):
            admissible_drive_band([4.0, 7.0])


class TestHeadroomAndWorstLine(unittest.TestCase):
    def test_headroom_is_the_nearer_of_the_two_distances(self):
        result = evaluate_line(nominal_line())
        self.assertAlmostEqual(line_headroom_a(result), 0.5, places=9)

    def test_the_worst_line_is_the_least_headroom(self):
        results = [evaluate_line(line) for line in nominal_config()["lines"]]
        self.assertEqual(worst_line(results)["name"], "separation-nut-redundant")

    def test_worst_line_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_line([])

    def test_headroom_rejects_an_incomplete_record(self):
        with self.assertRaises(ValueError):
            line_headroom_a({LOW_CORNER: 4.0})


class TestEndToEnd(unittest.TestCase):
    def test_a_compatible_set_reports_no_findings(self):
        report = evaluate_interface(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "interface-compatible")
        self.assertTrue(report["compatible"])

    def test_one_short_line_holds_the_assessment(self):
        config = nominal_config()
        config["lines"][1]["drive_voltage_min_v"] = 21.0
        report = evaluate_interface(config)
        self.assertFalse(report["compatible"])
        self.assertEqual(report["status"], "hold-interface-compatibility")
        self.assertTrue(
            any("separation-nut-redundant" in f for f in report["findings"])
        )

    def test_an_infeasible_spread_is_reported_as_its_own_finding(self):
        config = nominal_config()
        config["lines"][0]["actuator_resistance"] = {"min_ohm": 3.0, "max_ohm": 18.5}
        report = evaluate_interface(config)
        self.assertTrue(
            any("no drive voltage can satisfy" in f for f in report["findings"])
        )

    def test_a_widened_window_can_requalify_a_set(self):
        config = nominal_config()
        config["lines"][1]["drive_voltage_min_v"] = 21.0
        self.assertFalse(evaluate_interface(config)["compatible"])
        config["spec"] = {"min_firing_current_a": 2.5}
        self.assertTrue(evaluate_interface(config)["compatible"])

    def test_duplicate_line_names_are_rejected(self):
        config = nominal_config()
        config["lines"][1]["name"] = config["lines"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_interface(config)

    def test_an_empty_line_set_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_interface({"lines": []})

    def test_a_missing_line_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_interface({"spec": {}})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_interface([("lines", [])])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            compatibility_status("hold")

    def test_the_named_tolerance_is_far_below_any_current_limit(self):
        self.assertLess(CURRENT_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
