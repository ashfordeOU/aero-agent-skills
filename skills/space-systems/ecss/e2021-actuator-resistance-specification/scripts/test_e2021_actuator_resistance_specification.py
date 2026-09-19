#!/usr/bin/env python3
"""Gate 3 contract test for e2021-actuator-resistance-specification.

Stdlib unittest only, offline, deterministic. A declared maximum landing
exactly on the computed worst case is asserted with assertAlmostEqual against
that value and on the decision the logic then takes, never with a strict
inequality whose truth would depend on the last bit of a product.
"""

import unittest

from e2021_actuator_resistance_specification_logic import (
    COLD_END,
    DEFAULT_RESISTANCE_SPEC,
    HOT_END,
    RESISTANCE_EPS,
    evaluate_actuator,
    evaluate_specification,
    looks_like_the_reference_value,
    maximum_resistance_ohm,
    operating_range,
    range_coverage_gaps,
    resistance_adders_ohm,
    resistance_at_temperature,
    resolve_spec,
    specification_status,
    tightest_actuator,
    worst_case_end,
)


def nominal_actuator():
    return {
        "name": "pyro-bridgewire-a",
        "reference_resistance_ohm": 1.0,
        "reference_temperature_c": 20.0,
        "temperature_coefficient_per_k": 0.004,
        "operating_temperature_min_c": -40.0,
        "operating_temperature_max_c": 85.0,
        "contact_resistance_ohm": 0.05,
        "lead_resistance_ohm": 0.10,
        "declared_max_resistance_ohm": 1.6,
    }


def roomy_actuator():
    actuator = nominal_actuator()
    actuator["name"] = "pyro-bridgewire-b"
    actuator["declared_max_resistance_ohm"] = 2.0
    return actuator


def nominal_config():
    return {"actuators": [nominal_actuator(), roomy_actuator()]}


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["build_tolerance_fraction"], 0.05, places=9)
        self.assertEqual(set(spec), set(DEFAULT_RESISTANCE_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"ageing_allowance_fraction": 0.10})
        self.assertAlmostEqual(spec["ageing_allowance_fraction"], 0.10, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"ageing_allowance_fraction": 0.10})
        self.assertAlmostEqual(
            DEFAULT_RESISTANCE_SPEC["ageing_allowance_fraction"], 0.02, places=9
        )

    def test_a_zero_allowance_is_admissible(self):
        self.assertAlmostEqual(
            resolve_spec({"ageing_allowance_fraction": 0.0})[
                "ageing_allowance_fraction"
            ],
            0.0,
            places=9,
        )

    def test_a_negative_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"build_tolerance_fraction": -0.01})

    def test_an_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"radiation_allowance_fraction": 0.01})

    def test_a_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("build_tolerance_fraction", 0.05)])


class TestTemperatureModel(unittest.TestCase):
    def test_the_reference_point_returns_the_reference_value(self):
        self.assertAlmostEqual(
            resistance_at_temperature(1.0, 20.0, 0.004, 20.0), 1.0, places=9
        )

    def test_a_hot_excursion_raises_a_positive_coefficient_element(self):
        self.assertAlmostEqual(
            resistance_at_temperature(1.0, 20.0, 0.004, 85.0), 1.26, places=9
        )

    def test_a_cold_excursion_lowers_a_positive_coefficient_element(self):
        self.assertAlmostEqual(
            resistance_at_temperature(1.0, 20.0, 0.004, -40.0), 0.76, places=9
        )

    def test_a_negative_coefficient_rises_at_the_cold_end(self):
        self.assertAlmostEqual(
            resistance_at_temperature(1.0, 20.0, -0.002, -40.0), 1.12, places=9
        )

    def test_a_coefficient_driving_the_element_non_positive_is_rejected(self):
        with self.assertRaises(ValueError):
            resistance_at_temperature(1.0, 20.0, 0.02, -40.0)

    def test_a_non_positive_reference_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            resistance_at_temperature(0.0, 20.0, 0.004, 85.0)

    def test_a_positive_coefficient_puts_the_worst_case_at_the_hot_end(self):
        self.assertEqual(worst_case_end(0.004), HOT_END)

    def test_a_negative_coefficient_puts_the_worst_case_at_the_cold_end(self):
        self.assertEqual(worst_case_end(-0.002), COLD_END)

    def test_a_zero_coefficient_resolves_to_the_hot_end(self):
        self.assertEqual(worst_case_end(0.0), HOT_END)


class TestRangeAndAdders(unittest.TestCase):
    def test_the_operating_range_returns_its_two_ends(self):
        self.assertEqual(operating_range(nominal_actuator()), (-40.0, 85.0))

    def test_an_inverted_operating_range_is_rejected(self):
        actuator = nominal_actuator()
        actuator["operating_temperature_max_c"] = -80.0
        with self.assertRaises(ValueError):
            operating_range(actuator)

    def test_an_absent_declared_range_defaults_to_the_operating_range(self):
        self.assertEqual(range_coverage_gaps(nominal_actuator()), [])

    def test_a_declared_range_short_at_the_cold_end_is_a_gap(self):
        actuator = nominal_actuator()
        actuator["declared_temperature_min_c"] = -20.0
        self.assertEqual(range_coverage_gaps(actuator), [COLD_END])

    def test_a_declared_range_short_at_both_ends_reports_both(self):
        actuator = nominal_actuator()
        actuator["declared_temperature_min_c"] = -20.0
        actuator["declared_temperature_max_c"] = 60.0
        self.assertEqual(range_coverage_gaps(actuator), [COLD_END, HOT_END])

    def test_an_inverted_declared_range_is_rejected(self):
        actuator = nominal_actuator()
        actuator["declared_temperature_min_c"] = 60.0
        actuator["declared_temperature_max_c"] = -20.0
        with self.assertRaises(ValueError):
            range_coverage_gaps(actuator)

    def test_the_adders_are_summed(self):
        self.assertAlmostEqual(
            resistance_adders_ohm(nominal_actuator()), 0.15, places=9
        )

    def test_absent_adders_contribute_nothing(self):
        self.assertAlmostEqual(resistance_adders_ohm({"name": "bare"}), 0.0, places=9)

    def test_a_negative_adder_is_rejected(self):
        actuator = nominal_actuator()
        actuator["lead_resistance_ohm"] = -0.1
        with self.assertRaises(ValueError):
            resistance_adders_ohm(actuator)


class TestMaximumResistance(unittest.TestCase):
    def test_the_stack_sits_on_the_worst_case_temperature(self):
        computed = maximum_resistance_ohm(nominal_actuator())
        self.assertEqual(computed["worst_case_end"], HOT_END)
        self.assertAlmostEqual(computed["worst_case_temperature_c"], 85.0, places=9)
        self.assertAlmostEqual(
            computed["resistance_at_worst_case_ohm"], 1.26, places=9
        )

    def test_the_proportional_allowances_multiply_the_element(self):
        computed = maximum_resistance_ohm(nominal_actuator())
        self.assertAlmostEqual(computed["stacked_resistance_ohm"], 1.34946, places=9)

    def test_the_absolute_adders_land_on_top(self):
        computed = maximum_resistance_ohm(nominal_actuator())
        self.assertAlmostEqual(
            computed["maximum_resistance_ohm"], 1.49946, places=9
        )

    def test_a_negative_coefficient_moves_the_worst_case_to_the_cold_end(self):
        actuator = nominal_actuator()
        actuator["temperature_coefficient_per_k"] = -0.002
        computed = maximum_resistance_ohm(actuator)
        self.assertEqual(computed["worst_case_end"], COLD_END)
        self.assertAlmostEqual(computed["worst_case_temperature_c"], -40.0, places=9)

    def test_zero_allowances_leave_the_element_untouched(self):
        actuator = nominal_actuator()
        actuator["temperature_coefficient_per_k"] = 0.0
        actuator["contact_resistance_ohm"] = 0.0
        actuator["lead_resistance_ohm"] = 0.0
        computed = maximum_resistance_ohm(
            actuator,
            {"build_tolerance_fraction": 0.0, "ageing_allowance_fraction": 0.0},
        )
        self.assertAlmostEqual(computed["maximum_resistance_ohm"], 1.0, places=9)


class TestNominalOnlyDeclaration(unittest.TestCase):
    def test_a_declaration_repeating_the_reference_is_recognized(self):
        self.assertTrue(looks_like_the_reference_value(1.0, 1.0))

    def test_a_stacked_declaration_is_not_the_reference(self):
        self.assertFalse(looks_like_the_reference_value(1.6, 1.0))

    def test_a_non_numeric_declaration_is_rejected(self):
        with self.assertRaises(ValueError):
            looks_like_the_reference_value("1.0", 1.0)


class TestActuatorVerdict(unittest.TestCase):
    def test_a_bounding_declaration_is_specified(self):
        result = evaluate_actuator(nominal_actuator())
        self.assertTrue(result["specified"])
        self.assertAlmostEqual(result["margin_ohm"], 0.10054, places=9)

    def test_a_declaration_exactly_on_the_worst_case_bounds_it(self):
        actuator = nominal_actuator()
        actuator["temperature_coefficient_per_k"] = 0.0
        actuator["contact_resistance_ohm"] = 0.0
        actuator["lead_resistance_ohm"] = 0.0
        actuator["declared_max_resistance_ohm"] = 1.0
        result = evaluate_actuator(
            actuator,
            {"build_tolerance_fraction": 0.0, "ageing_allowance_fraction": 0.0},
        )
        self.assertAlmostEqual(result["maximum_resistance_ohm"], 1.0, places=9)
        self.assertAlmostEqual(result["declared_max_resistance_ohm"], 1.0, places=9)
        self.assertTrue(result["bounds_worst_case"])
        self.assertAlmostEqual(result["shortfall_ohm"], 0.0, places=9)

    def test_a_declaration_under_the_worst_case_reports_its_shortfall(self):
        actuator = nominal_actuator()
        actuator["declared_max_resistance_ohm"] = 1.4
        result = evaluate_actuator(actuator)
        self.assertFalse(result["bounds_worst_case"])
        self.assertAlmostEqual(result["shortfall_ohm"], 0.09946, places=9)

    def test_a_declaration_repeating_the_reference_is_flagged(self):
        actuator = nominal_actuator()
        actuator["declared_max_resistance_ohm"] = 1.0
        result = evaluate_actuator(actuator)
        self.assertTrue(result["stated_at_nominal_only"])
        self.assertFalse(result["specified"])

    def test_an_absent_declaration_adopts_the_computed_worst_case(self):
        actuator = nominal_actuator()
        del actuator["declared_max_resistance_ohm"]
        result = evaluate_actuator(actuator)
        self.assertTrue(result["bounds_worst_case"])
        self.assertAlmostEqual(result["margin_ohm"], 0.0, places=9)

    def test_a_short_declared_range_holds_the_specification(self):
        actuator = nominal_actuator()
        actuator["declared_temperature_max_c"] = 60.0
        self.assertFalse(evaluate_actuator(actuator)["specified"])

    def test_a_non_positive_declaration_is_rejected(self):
        actuator = nominal_actuator()
        actuator["declared_max_resistance_ohm"] = 0.0
        with self.assertRaises(ValueError):
            evaluate_actuator(actuator)

    def test_an_actuator_without_a_name_is_rejected(self):
        actuator = nominal_actuator()
        actuator["name"] = " "
        with self.assertRaises(ValueError):
            evaluate_actuator(actuator)

    def test_a_non_mapping_actuator_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_actuator(["pyro-bridgewire-a"])


class TestEndToEnd(unittest.TestCase):
    def test_a_specified_set_reports_no_findings(self):
        report = evaluate_specification(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "resistance-specified")
        self.assertTrue(report["specified"])

    def test_the_tightest_declaration_is_named(self):
        report = evaluate_specification(nominal_config())
        self.assertEqual(report["tightest_actuator"]["name"], "pyro-bridgewire-a")

    def test_one_short_declaration_holds_the_specification(self):
        config = nominal_config()
        config["actuators"][1]["declared_max_resistance_ohm"] = 1.4
        report = evaluate_specification(config)
        self.assertFalse(report["specified"])
        self.assertEqual(report["status"], "hold-resistance-specification")
        self.assertTrue(any("pyro-bridgewire-b" in f for f in report["findings"]))

    def test_a_range_gap_is_reported_per_end(self):
        config = nominal_config()
        config["actuators"][0]["declared_temperature_min_c"] = -20.0
        config["actuators"][0]["declared_temperature_max_c"] = 60.0
        report = evaluate_specification(config)
        self.assertEqual(len(report["findings"]), 2)

    def test_a_larger_ageing_allowance_can_hold_a_passing_set(self):
        config = nominal_config()
        self.assertTrue(evaluate_specification(config)["specified"])
        config["spec"] = {"ageing_allowance_fraction": 0.30}
        self.assertFalse(evaluate_specification(config)["specified"])

    def test_duplicate_actuator_names_are_rejected(self):
        config = nominal_config()
        config["actuators"][1]["name"] = config["actuators"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_specification(config)

    def test_an_empty_actuator_set_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specification({"actuators": []})

    def test_a_missing_actuator_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specification({"spec": {}})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_specification([("actuators", [])])

    def test_the_tightest_helper_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            tightest_actuator([])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            specification_status("hold")

    def test_the_named_tolerance_is_far_below_any_declared_resistance(self):
        self.assertLess(RESISTANCE_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
