#!/usr/bin/env python3
"""Contract test for the multijunction capacitance adaptation leaf (offline)."""

import copy
import math
import unittest

from e2008_multijunction_cell_capacitance_measurement_logic import (
    ADAPTATION_ADEQUATE,
    ADAPTATION_NOT_ADEQUATE,
    BIAS_PARTITION,
    CORNER_FREQUENCY_MARGIN,
    DOMINANT_SUBCELL_IDENTIFICATION,
    MAX_DOMINANT_SHARE,
    MAX_FREQUENCY_FRACTION_OF_CORNER,
    MIN_SUBCELLS_FOR_ADAPTATION,
    REQUIRED_ADAPTATIONS,
    SERIES_SUMMATION,
    adaptation_required,
    assess_multijunction_adaptation,
    dominant_subcell,
    forward_bias_exceedances,
    frequency_margin,
    missing_adaptations,
    reciprocal_shares,
    series_capacitance_f,
    single_junction_bias_error_fraction,
    subcell_bias_partition,
    tunnel_corner_frequency_hz,
    validate_subcells,
)

TRIPLE_STACK = [
    {"name": "top-ingap", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.4},
    {"name": "middle-ingaas", "capacitance_f": 4.5e-8, "built_in_voltage_v": 1.0},
    {"name": "bottom-germanium", "capacitance_f": 1.2e-7, "built_in_voltage_v": 0.3},
]

BASE_CASE = {
    "subcells": TRIPLE_STACK,
    "terminal_bias_v": -2.0,
    "test_frequency_hz": 1.0e5,
    "tunnel_junction_series_resistance_ohm": 0.5,
    "declared_adaptations": list(REQUIRED_ADAPTATIONS),
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class StackValidationTests(unittest.TestCase):
    def test_a_declared_stack_keeps_its_order_and_names(self):
        stack = validate_subcells(TRIPLE_STACK)
        self.assertEqual(
            [entry["name"] for entry in stack],
            ["top-ingap", "middle-ingaas", "bottom-germanium"],
        )

    def test_a_repeated_sub_cell_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subcells(
                [
                    {"name": "top", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.4},
                    {"name": "top", "capacitance_f": 4.5e-8, "built_in_voltage_v": 1.0},
                ]
            )

    def test_a_sub_cell_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subcells(
                [{"capacitance_f": 3.0e-8, "built_in_voltage_v": 1.4}]
            )

    def test_a_non_positive_sub_cell_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subcells(
                [{"name": "top", "capacitance_f": 0.0, "built_in_voltage_v": 1.4}]
            )

    def test_an_empty_stack_is_refused(self):
        with self.assertRaises(ValueError):
            validate_subcells([])

    def test_two_or_more_junctions_make_the_adaptation_necessary(self):
        self.assertTrue(adaptation_required(TRIPLE_STACK))
        self.assertFalse(adaptation_required(TRIPLE_STACK[:1]))
        self.assertEqual(MIN_SUBCELLS_FOR_ADAPTATION, 2)


class SeriesSummationTests(unittest.TestCase):
    def test_the_terminal_reading_is_the_reciprocal_sum(self):
        expected = 1.0 / sum(
            1.0 / entry["capacitance_f"] for entry in TRIPLE_STACK
        )
        self.assertAlmostEqual(
            series_capacitance_f(TRIPLE_STACK) / expected, 1.0, places=12
        )

    def test_two_equal_junctions_halve_the_terminal_reading(self):
        stack = [
            {"name": "a", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.0},
            {"name": "b", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.0},
        ]
        self.assertAlmostEqual(
            series_capacitance_f(stack) / 1.5e-8, 1.0, places=12
        )

    def test_the_stack_reads_below_its_smallest_junction(self):
        smallest = min(entry["capacitance_f"] for entry in TRIPLE_STACK)
        self.assertLess(series_capacitance_f(TRIPLE_STACK), smallest)

    def test_the_reciprocal_shares_sum_to_one(self):
        total = sum(entry["share"] for entry in reciprocal_shares(TRIPLE_STACK))
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_the_smallest_junction_dominates_the_reading(self):
        self.assertEqual(dominant_subcell(TRIPLE_STACK)["name"], "top-ingap")

    def test_equal_junctions_share_the_stack_equally(self):
        stack = [
            {"name": "a", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.0},
            {"name": "b", "capacitance_f": 3.0e-8, "built_in_voltage_v": 1.0},
        ]
        for entry in reciprocal_shares(stack):
            self.assertAlmostEqual(entry["share"], 0.5, places=9)


class BiasPartitionTests(unittest.TestCase):
    def test_the_bias_divides_in_proportion_to_the_shares(self):
        partition = subcell_bias_partition(TRIPLE_STACK, -2.0)
        shares = {entry["name"]: entry["share"] for entry in reciprocal_shares(TRIPLE_STACK)}
        for entry in partition:
            self.assertAlmostEqual(
                entry["bias_voltage_v"], shares[entry["name"]] * -2.0, places=12
            )

    def test_the_partition_sums_back_to_the_terminal_bias(self):
        total = sum(
            entry["bias_voltage_v"]
            for entry in subcell_bias_partition(TRIPLE_STACK, -2.0)
        )
        self.assertAlmostEqual(total, -2.0, places=9)

    def test_a_single_junction_extraction_misattributes_the_rest_of_the_bias(self):
        error = single_junction_bias_error_fraction(TRIPLE_STACK)
        dominant = dominant_subcell(TRIPLE_STACK)["share"]
        self.assertAlmostEqual(error, 1.0 - dominant, places=12)
        self.assertGreater(error, 0.4)

    def test_one_junction_alone_misattributes_nothing(self):
        self.assertAlmostEqual(
            single_junction_bias_error_fraction(TRIPLE_STACK[:1]), 0.0, places=12
        )

    def test_a_non_numeric_terminal_bias_is_refused(self):
        with self.assertRaises(ValueError):
            subcell_bias_partition(TRIPLE_STACK, "minus two volts")

    def test_a_reverse_terminal_bias_keeps_every_junction_depleted(self):
        self.assertEqual(forward_bias_exceedances(TRIPLE_STACK, -2.0), ())

    def test_a_forward_terminal_bias_pushes_junctions_past_their_ceiling(self):
        offenders = forward_bias_exceedances(TRIPLE_STACK, 2.0)
        self.assertTrue(offenders)
        self.assertIn("top-ingap", [entry["name"] for entry in offenders])


class TunnelJunctionTests(unittest.TestCase):
    def test_the_corner_follows_the_series_resistance_and_the_stack(self):
        terminal = series_capacitance_f(TRIPLE_STACK)
        self.assertAlmostEqual(
            tunnel_corner_frequency_hz(0.5, terminal)
            / (1.0 / (2.0 * math.pi * 0.5 * terminal)),
            1.0,
            places=12,
        )

    def test_a_larger_series_resistance_lowers_the_corner(self):
        terminal = series_capacitance_f(TRIPLE_STACK)
        self.assertGreater(
            tunnel_corner_frequency_hz(0.1, terminal),
            tunnel_corner_frequency_hz(5.0, terminal),
        )

    def test_a_zero_series_resistance_has_no_corner(self):
        with self.assertRaises(ValueError):
            tunnel_corner_frequency_hz(0.0, 1.5e-8)

    def test_the_margin_is_the_test_frequency_over_the_corner(self):
        self.assertAlmostEqual(frequency_margin(1.0e5, 1.0e6), 0.1, places=12)

    def test_a_zero_test_frequency_has_no_margin(self):
        with self.assertRaises(ValueError):
            frequency_margin(0.0, 1.0e6)


class AdaptationDeclarationTests(unittest.TestCase):
    def test_a_full_declaration_leaves_nothing_missing(self):
        self.assertEqual(missing_adaptations(REQUIRED_ADAPTATIONS), ())

    def test_an_undeclared_run_is_missing_every_adaptation(self):
        self.assertEqual(missing_adaptations(None), REQUIRED_ADAPTATIONS)

    def test_a_partial_declaration_names_what_is_left(self):
        absent = missing_adaptations([SERIES_SUMMATION, BIAS_PARTITION])
        self.assertIn(CORNER_FREQUENCY_MARGIN, absent)
        self.assertIn(DOMINANT_SUBCELL_IDENTIFICATION, absent)

    def test_an_invented_adaptation_is_refused(self):
        with self.assertRaises(ValueError):
            missing_adaptations(["average-the-three-junctions"])

    def test_a_declaration_that_is_not_a_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            missing_adaptations("series-stack-reciprocal-summation")


class AssessmentTests(unittest.TestCase):
    def test_a_fully_adapted_triple_junction_run_is_adequate(self):
        result = assess_multijunction_adaptation(BASE_CASE)
        self.assertEqual(result["verdict"], ADAPTATION_ADEQUATE)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["subcell_count"], 3)

    def test_the_assessment_reports_the_dominant_junction(self):
        result = assess_multijunction_adaptation(BASE_CASE)
        self.assertEqual(result["dominant_subcell"]["name"], "top-ingap")
        self.assertTrue(result["adaptation_required"])

    def test_carrying_the_single_junction_method_over_unchanged_is_a_finding(self):
        result = assess_multijunction_adaptation(_case(declared_adaptations=[]))
        self.assertEqual(result["verdict"], ADAPTATION_NOT_ADEQUATE)
        self.assertEqual(result["missing_adaptations"], REQUIRED_ADAPTATIONS)
        self.assertTrue(
            any("without" in finding for finding in result["findings"])
        )

    def test_a_stack_governed_by_one_junction_cannot_be_resolved(self):
        stack = copy.deepcopy(TRIPLE_STACK)
        stack[0]["capacitance_f"] = 1.0e-9
        result = assess_multijunction_adaptation(_case(subcells=stack))
        self.assertEqual(result["verdict"], ADAPTATION_NOT_ADEQUATE)
        self.assertGreater(result["dominant_subcell"]["share"], MAX_DOMINANT_SHARE)
        self.assertTrue(any("separable" in f for f in result["findings"]))

    def test_a_test_frequency_above_the_corner_ceiling_is_a_finding(self):
        result = assess_multijunction_adaptation(_case(test_frequency_hz=1.0e7))
        self.assertEqual(result["verdict"], ADAPTATION_NOT_ADEQUATE)
        self.assertTrue(any("rolling off" in f for f in result["findings"]))

    def test_a_frequency_landing_exactly_on_the_ceiling_is_accepted(self):
        corner = tunnel_corner_frequency_hz(0.5, series_capacitance_f(TRIPLE_STACK))
        result = assess_multijunction_adaptation(
            _case(test_frequency_hz=MAX_FREQUENCY_FRACTION_OF_CORNER * corner)
        )
        self.assertAlmostEqual(
            result["frequency_margin"], MAX_FREQUENCY_FRACTION_OF_CORNER, places=9
        )
        self.assertEqual(result["verdict"], ADAPTATION_ADEQUATE)

    def test_a_forward_terminal_bias_is_a_finding_against_the_run(self):
        result = assess_multijunction_adaptation(_case(terminal_bias_v=2.0))
        self.assertEqual(result["verdict"], ADAPTATION_NOT_ADEQUATE)
        self.assertTrue(result["forward_bias_exceedances"])
        self.assertTrue(any("forward ceiling" in f for f in result["findings"]))

    def test_a_single_junction_device_is_sent_back_to_the_unadapted_method(self):
        result = assess_multijunction_adaptation(_case(subcells=TRIPLE_STACK[:1]))
        self.assertEqual(result["verdict"], ADAPTATION_NOT_ADEQUATE)
        self.assertFalse(result["adaptation_required"])
        self.assertTrue(any("unchanged" in f for f in result["findings"]))

    def test_the_bias_error_of_a_one_junction_reading_is_carried_in_the_result(self):
        result = assess_multijunction_adaptation(BASE_CASE)
        self.assertAlmostEqual(
            result["single_junction_bias_error_fraction"],
            1.0 - result["dominant_subcell"]["share"],
            places=12,
        )

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_multijunction_adaptation("triple-junction")

    def test_a_missing_tunnel_resistance_stops_the_assessment(self):
        case = _case()
        del case["tunnel_junction_series_resistance_ohm"]
        with self.assertRaises(ValueError):
            assess_multijunction_adaptation(case)


if __name__ == "__main__":
    unittest.main()
