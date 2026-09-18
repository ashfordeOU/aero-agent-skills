"""Contract tests for the clause 7.3.4 MMIC simulation-results review item."""

import copy
import unittest

from q6012_simulation_results_review_item_logic import (
    DIRECTIONS,
    MARGIN_TOLERANCE,
    corner_key,
    corner_label,
    corner_spread,
    evaluate_parameter,
    extra_corners,
    margin_fraction,
    missing_corners,
    normalise_runs,
    parameter_margin,
    parameter_samples,
    required_corner_set,
    review_simulation_results,
    worst_corner,
)

PROCESSES = ["slow", "fast"]
TEMPERATURES = [-30.0, 85.0]
SUPPLIES = [5.0]

PARAMETERS = [
    {"name": "gain_db", "direction": "min", "target": 18.0, "unit": "dB"},
    {"name": "noise_figure_db", "direction": "max", "target": 2.5, "unit": "dB"},
]

# Four corners: the cross product of two process corners, two temperature
# extremes and one supply. Gain is worst hot-and-slow, noise figure worst
# hot-and-fast, so the two parameters do not share a worst corner.
RUNS = [
    {
        "process": "slow", "temperature_c": -30.0, "supply_v": 5.0,
        "values": {"gain_db": 20.4, "noise_figure_db": 1.9},
    },
    {
        "process": "slow", "temperature_c": 85.0, "supply_v": 5.0,
        "values": {"gain_db": 18.6, "noise_figure_db": 2.2},
    },
    {
        "process": "fast", "temperature_c": -30.0, "supply_v": 5.0,
        "values": {"gain_db": 21.8, "noise_figure_db": 2.0},
    },
    {
        "process": "fast", "temperature_c": 85.0, "supply_v": 5.0,
        "values": {"gain_db": 19.5, "noise_figure_db": 2.35},
    },
]


def package(**overrides):
    """Return a clean simulation-results package with the overrides applied."""
    base = {
        "process_corners": list(PROCESSES),
        "temperatures_c": list(TEMPERATURES),
        "supplies_v": list(SUPPLIES),
        "parameters": copy.deepcopy(PARAMETERS),
        "runs": copy.deepcopy(RUNS),
    }
    base.update(copy.deepcopy(overrides))
    return base


class RequiredCornerSetTests(unittest.TestCase):
    def test_matrix_is_the_full_cross_product(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        self.assertEqual(len(matrix), 4)

    def test_matrix_grows_with_a_second_supply(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, [4.5, 5.5])
        self.assertEqual(len(matrix), 8)

    def test_matrix_is_deterministically_ordered(self):
        first = required_corner_set(["fast", "slow"], TEMPERATURES, SUPPLIES)
        second = required_corner_set(["slow", "fast"], TEMPERATURES, SUPPLIES)
        self.assertEqual(first, second)

    def test_repeated_process_corner_rejected(self):
        with self.assertRaises(ValueError):
            required_corner_set(["slow", "slow"], TEMPERATURES, SUPPLIES)

    def test_repeated_temperature_rejected(self):
        with self.assertRaises(ValueError):
            required_corner_set(PROCESSES, [25.0, 25.0], SUPPLIES)

    def test_non_positive_supply_rejected(self):
        with self.assertRaises(ValueError):
            required_corner_set(PROCESSES, TEMPERATURES, [0.0])

    def test_empty_axis_rejected(self):
        with self.assertRaises(ValueError):
            required_corner_set([], TEMPERATURES, SUPPLIES)


class CornerKeyTests(unittest.TestCase):
    def test_process_name_is_case_folded(self):
        self.assertEqual(
            corner_key({"process": "SLOW", "temperature_c": -30, "supply_v": 5}),
            ("slow", -30.0, 5.0),
        )

    def test_integer_and_float_axis_values_give_one_key(self):
        one = corner_key({"process": "slow", "temperature_c": -30, "supply_v": 5})
        two = corner_key({"process": "slow", "temperature_c": -30.0, "supply_v": 5.0})
        self.assertEqual(one, two)

    def test_label_is_readable(self):
        self.assertEqual(corner_label(("slow", -30.0, 5.0)), "slow @ -30C @ 5V")

    def test_malformed_key_rejected_by_label(self):
        with self.assertRaises(ValueError):
            corner_label(("slow", -30.0))

    def test_missing_process_rejected(self):
        with self.assertRaises(ValueError):
            corner_key({"temperature_c": -30.0, "supply_v": 5.0})


class NormaliseRunsTests(unittest.TestCase):
    def test_all_runs_are_keyed(self):
        table = normalise_runs(RUNS)
        self.assertEqual(len(table), 4)
        self.assertIn(("slow", 85.0, 5.0), table)

    def test_duplicate_corner_rejected(self):
        with self.assertRaises(ValueError):
            normalise_runs(RUNS + [copy.deepcopy(RUNS[0])])

    def test_run_without_values_rejected(self):
        runs = copy.deepcopy(RUNS)
        runs[0]["values"] = {}
        with self.assertRaises(ValueError):
            normalise_runs(runs)

    def test_non_numeric_value_rejected(self):
        runs = copy.deepcopy(RUNS)
        runs[0]["values"]["gain_db"] = "20.4"
        with self.assertRaises(ValueError):
            normalise_runs(runs)

    def test_empty_run_list_rejected(self):
        with self.assertRaises(ValueError):
            normalise_runs([])


class CoverageTests(unittest.TestCase):
    def test_full_coverage_reports_nothing_missing(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        self.assertEqual(missing_corners(matrix, normalise_runs(RUNS)), [])

    def test_dropped_run_is_reported_as_missing(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        table = normalise_runs(RUNS[:3])
        self.assertEqual(len(missing_corners(matrix, table)), 1)

    def test_run_outside_the_matrix_is_reported_as_extra(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        runs = copy.deepcopy(RUNS)
        runs.append(
            {
                "process": "typical", "temperature_c": 25.0, "supply_v": 5.0,
                "values": {"gain_db": 20.0, "noise_figure_db": 2.0},
            }
        )
        self.assertEqual(len(extra_corners(matrix, normalise_runs(runs))), 1)

    def test_parameter_samples_report_absent_corners(self):
        matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        runs = copy.deepcopy(RUNS)
        runs[1]["values"].pop("gain_db")
        samples, absent = parameter_samples("gain_db", normalise_runs(runs), matrix)
        self.assertEqual(len(samples), 3)
        self.assertEqual(absent, [("slow", 85.0, 5.0)])


class WorstCornerTests(unittest.TestCase):
    def test_minimum_target_is_worst_at_the_lowest_sample(self):
        samples = {("slow", 85.0, 5.0): 18.6, ("fast", -30.0, 5.0): 21.8}
        key, value = worst_corner(samples, "min")
        self.assertEqual(key, ("slow", 85.0, 5.0))
        self.assertAlmostEqual(value, 18.6, places=9)

    def test_maximum_target_is_worst_at_the_highest_sample(self):
        samples = {("slow", 85.0, 5.0): 2.2, ("fast", 85.0, 5.0): 2.35}
        key, value = worst_corner(samples, "max")
        self.assertEqual(key, ("fast", 85.0, 5.0))

    def test_tie_resolves_to_the_first_corner_in_order(self):
        samples = {("slow", 85.0, 5.0): 19.0, ("fast", 85.0, 5.0): 19.0}
        key, _ = worst_corner(samples, "min")
        self.assertEqual(key, ("fast", 85.0, 5.0))

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            worst_corner({("slow", 85.0, 5.0): 1.0}, "nominal")

    def test_empty_sample_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_corner({}, "min")

    def test_directions_are_the_two_documented_ones(self):
        self.assertEqual(set(DIRECTIONS), {"min", "max"})


class MarginTests(unittest.TestCase):
    def test_minimum_target_margin_is_value_minus_target(self):
        self.assertAlmostEqual(parameter_margin(18.6, 18.0, "min"), 0.6, places=9)

    def test_maximum_target_margin_is_target_minus_value(self):
        self.assertAlmostEqual(parameter_margin(2.35, 2.5, "max"), 0.15, places=9)

    def test_shortfall_is_negative(self):
        self.assertAlmostEqual(parameter_margin(17.4, 18.0, "min"), -0.6, places=9)

    def test_fraction_is_relative_to_the_target_magnitude(self):
        self.assertAlmostEqual(margin_fraction(0.6, 18.0), 0.6 / 18.0, places=9)

    def test_fraction_uses_the_magnitude_of_a_negative_target(self):
        self.assertAlmostEqual(margin_fraction(2.0, -10.0), 0.2, places=9)

    def test_zero_target_has_no_fraction(self):
        with self.assertRaises(ValueError):
            margin_fraction(1.0, 0.0)

    def test_spread_is_the_range_of_the_samples(self):
        samples = {("a", 1.0, 1.0): 18.6, ("b", 1.0, 1.0): 21.8}
        self.assertAlmostEqual(corner_spread(samples), 3.2, places=9)

    def test_spread_of_a_single_sample_is_zero(self):
        self.assertAlmostEqual(corner_spread({("a", 1.0, 1.0): 18.6}), 0.0, places=9)

    def test_margin_tolerance_is_small_and_positive(self):
        self.assertGreater(MARGIN_TOLERANCE, 0.0)
        self.assertLess(MARGIN_TOLERANCE, 1e-6)


class EvaluateParameterTests(unittest.TestCase):
    def setUp(self):
        self.matrix = required_corner_set(PROCESSES, TEMPERATURES, SUPPLIES)
        self.table = normalise_runs(RUNS)

    def test_compliant_parameter_meets_its_target(self):
        record = evaluate_parameter(PARAMETERS[0], self.table, self.matrix)
        self.assertTrue(record["meets_target"])
        self.assertEqual(record["worst_corner"], ("slow", 85.0, 5.0))
        self.assertAlmostEqual(record["margin"], 0.6, places=9)

    def test_maximum_type_parameter_uses_the_hottest_sample(self):
        record = evaluate_parameter(PARAMETERS[1], self.table, self.matrix)
        self.assertEqual(record["worst_corner"], ("fast", 85.0, 5.0))
        self.assertAlmostEqual(record["margin"], 0.15, places=9)

    def test_parameter_exactly_on_target_still_meets_it(self):
        runs = copy.deepcopy(RUNS)
        runs[1]["values"]["gain_db"] = 18.0
        record = evaluate_parameter(PARAMETERS[0], normalise_runs(runs), self.matrix)
        self.assertAlmostEqual(record["margin"], 0.0, places=9)
        self.assertTrue(record["meets_target"])

    def test_shortfall_produces_a_finding(self):
        runs = copy.deepcopy(RUNS)
        runs[1]["values"]["gain_db"] = 17.2
        record = evaluate_parameter(PARAMETERS[0], normalise_runs(runs), self.matrix)
        self.assertFalse(record["meets_target"])
        self.assertTrue(any("worst corner" in item for item in record["findings"]))

    def test_flat_parameter_is_flagged_as_never_swept(self):
        runs = copy.deepcopy(RUNS)
        for run in runs:
            run["values"]["gain_db"] = 20.0
        record = evaluate_parameter(PARAMETERS[0], normalise_runs(runs), self.matrix)
        self.assertTrue(record["meets_target"])
        self.assertTrue(any("did not reach it" in item for item in record["findings"]))

    def test_parameter_absent_everywhere_is_reported(self):
        runs = copy.deepcopy(RUNS)
        for run in runs:
            run["values"].pop("gain_db")
        record = evaluate_parameter(PARAMETERS[0], normalise_runs(runs), self.matrix)
        self.assertFalse(record["meets_target"])
        self.assertIsNone(record["worst_corner"])

    def test_unknown_direction_in_a_parameter_rejected(self):
        bad = dict(PARAMETERS[0], direction="typical")
        with self.assertRaises(ValueError):
            evaluate_parameter(bad, self.table, self.matrix)

    def test_parameter_without_unit_rejected(self):
        bad = dict(PARAMETERS[0])
        bad.pop("unit")
        with self.assertRaises(ValueError):
            evaluate_parameter(bad, self.table, self.matrix)


class ReviewSimulationResultsTests(unittest.TestCase):
    def test_complete_compliant_package_passes(self):
        result = review_simulation_results(package())
        self.assertTrue(result["item_passed"])
        self.assertEqual(result["missing_corners"], [])
        self.assertEqual(result["covered_corner_count"], 4)

    def test_tightest_parameter_is_reported_by_fractional_margin(self):
        result = review_simulation_results(package())
        self.assertEqual(result["tightest_parameter"], "gain_db")
        self.assertAlmostEqual(result["tightest_margin_fraction"], 0.6 / 18.0, places=9)

    def test_missing_corner_fails_the_item_even_when_every_number_passes(self):
        result = review_simulation_results(package(runs=copy.deepcopy(RUNS[:3])))
        self.assertFalse(result["item_passed"])
        self.assertEqual(len(result["missing_corners"]), 1)

    def test_extra_corner_is_a_finding(self):
        runs = copy.deepcopy(RUNS)
        runs.append(
            {
                "process": "typical", "temperature_c": 25.0, "supply_v": 5.0,
                "values": {"gain_db": 20.0, "noise_figure_db": 2.0},
            }
        )
        result = review_simulation_results(package(runs=runs))
        self.assertFalse(result["item_passed"])
        self.assertEqual(len(result["extra_corners"]), 1)

    def test_shortfall_at_one_corner_fails_the_item(self):
        runs = copy.deepcopy(RUNS)
        runs[3]["values"]["noise_figure_db"] = 2.9
        result = review_simulation_results(package(runs=runs))
        self.assertFalse(result["item_passed"])

    def test_duplicate_parameter_rejected(self):
        parameters = copy.deepcopy(PARAMETERS) + [copy.deepcopy(PARAMETERS[0])]
        with self.assertRaises(ValueError):
            review_simulation_results(package(parameters=parameters))

    def test_missing_package_key_rejected(self):
        broken = package()
        broken.pop("supplies_v")
        with self.assertRaises(ValueError):
            review_simulation_results(broken)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            review_simulation_results(["runs"])

    def test_empty_parameter_list_rejected(self):
        with self.assertRaises(ValueError):
            review_simulation_results(package(parameters=[]))


if __name__ == "__main__":
    unittest.main()
