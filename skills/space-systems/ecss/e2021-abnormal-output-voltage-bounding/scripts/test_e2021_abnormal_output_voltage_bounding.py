#!/usr/bin/env python3
"""Gate 3 contract test for e2021-abnormal-output-voltage-bounding.

Stdlib unittest only, offline, deterministic. A fault peak landing exactly on
the supply bound is asserted with assertAlmostEqual against the bound and on
the decision the logic then takes, never with a strict inequality whose truth
would depend on the last bit of a subtraction.
"""

import unittest

from e2021_abnormal_output_voltage_bounding_logic import (
    BOOST_CONVERSION,
    COMMAND_LOSS,
    DRIVE_STAGE_OPEN,
    DRIVE_STAGE_SHORT,
    INDUCTIVE_KICK,
    NO_PATH,
    REQUIRED_FAULT_CATEGORIES,
    SUPPLY_TRANSIENT,
    VOLTAGE_EPS,
    bound_ratio,
    bounding_status,
    categorize_exceedance,
    coverage_gaps,
    evaluate_bounding,
    evaluate_case,
    group_by_path,
    require_fault_category,
    supply_bound_v,
    worst_case,
)


def nominal_supply():
    return {"min_v": 22.0, "max_v": 34.0}


def nominal_cases():
    return [
        {"name": "output-stage-shorted", "category": DRIVE_STAGE_SHORT,
         "peak_output_voltage_v": 30.0},
        {"name": "output-stage-opened", "category": DRIVE_STAGE_OPEN,
         "peak_output_voltage_v": 34.0},
        {"name": "command-line-lost", "category": COMMAND_LOSS,
         "peak_output_voltage_v": 12.0},
        {"name": "bus-transient-applied", "category": SUPPLY_TRANSIENT,
         "peak_output_voltage_v": 33.5},
    ]


def nominal_config():
    return {"supply": nominal_supply(), "cases": nominal_cases()}


class TestSupplyBound(unittest.TestCase):
    def test_the_bound_is_the_top_of_the_supply_envelope(self):
        self.assertAlmostEqual(supply_bound_v(nominal_supply()), 34.0, places=9)

    def test_the_nominal_bus_is_not_the_bound(self):
        bound = supply_bound_v({"min_v": 22.0, "max_v": 34.0})
        self.assertNotAlmostEqual(bound, 28.0, places=9)

    def test_an_inverted_supply_envelope_is_rejected(self):
        with self.assertRaises(ValueError):
            supply_bound_v({"min_v": 34.0, "max_v": 22.0})

    def test_a_non_positive_supply_minimum_is_rejected(self):
        with self.assertRaises(ValueError):
            supply_bound_v({"min_v": 0.0, "max_v": 34.0})

    def test_a_non_mapping_supply_is_rejected(self):
        with self.assertRaises(ValueError):
            supply_bound_v([22.0, 34.0])

    def test_a_non_numeric_supply_end_is_rejected(self):
        with self.assertRaises(ValueError):
            supply_bound_v({"min_v": "22", "max_v": 34.0})


class TestBoundRatio(unittest.TestCase):
    def test_a_peak_on_the_bound_is_unity(self):
        self.assertAlmostEqual(bound_ratio(34.0, 34.0), 1.0, places=9)

    def test_a_peak_under_the_bound_is_below_unity(self):
        self.assertAlmostEqual(bound_ratio(17.0, 34.0), 0.5, places=9)

    def test_a_zero_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            bound_ratio(34.0, 0.0)

    def test_an_infinite_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            bound_ratio(float("inf"), 34.0)


class TestFaultCategories(unittest.TestCase):
    def test_a_recognized_category_is_returned(self):
        self.assertEqual(require_fault_category(COMMAND_LOSS), COMMAND_LOSS)

    def test_an_unrecognized_category_is_rejected(self):
        with self.assertRaises(ValueError):
            require_fault_category("someone-tripped-over-it")

    def test_the_required_set_is_a_subset_of_the_known_set(self):
        for category in REQUIRED_FAULT_CATEGORIES:
            self.assertEqual(require_fault_category(category), category)


class TestExceedancePath(unittest.TestCase):
    def test_a_bounded_case_names_no_path(self):
        case = {"peak_output_voltage_v": 30.0, "path": INDUCTIVE_KICK}
        self.assertEqual(categorize_exceedance(case, 34.0), NO_PATH)

    def test_an_exceeding_case_keeps_its_declared_path(self):
        case = {"peak_output_voltage_v": 40.0, "path": BOOST_CONVERSION}
        self.assertEqual(categorize_exceedance(case, 34.0), BOOST_CONVERSION)

    def test_an_exceeding_case_without_a_path_reports_none(self):
        case = {"peak_output_voltage_v": 40.0}
        self.assertEqual(categorize_exceedance(case, 34.0), NO_PATH)

    def test_an_unrecognized_path_is_rejected(self):
        case = {"peak_output_voltage_v": 40.0, "path": "magic"}
        with self.assertRaises(ValueError):
            categorize_exceedance(case, 34.0)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_exceedance(["40.0"], 34.0)


class TestCaseVerdict(unittest.TestCase):
    def test_a_case_under_the_bound_is_bounded(self):
        result = evaluate_case(nominal_cases()[0], 34.0)
        self.assertTrue(result["bounded"])
        self.assertAlmostEqual(result["exceedance_v"], 0.0, places=9)

    def test_a_case_exactly_on_the_bound_is_bounded(self):
        result = evaluate_case(nominal_cases()[1], 34.0)
        self.assertAlmostEqual(result["peak_output_voltage_v"], 34.0, places=9)
        self.assertAlmostEqual(result["supply_bound_v"], 34.0, places=9)
        self.assertTrue(result["bounded"])
        self.assertAlmostEqual(result["bound_ratio"], 1.0, places=9)

    def test_a_case_over_the_bound_reports_its_exceedance(self):
        case = nominal_cases()[0]
        case["peak_output_voltage_v"] = 40.0
        case["path"] = INDUCTIVE_KICK
        result = evaluate_case(case, 34.0)
        self.assertFalse(result["bounded"])
        self.assertAlmostEqual(result["exceedance_v"], 6.0, places=9)
        self.assertEqual(result["path"], INDUCTIVE_KICK)
        self.assertTrue(result["path_named"])

    def test_an_exceedance_with_no_named_path_is_flagged(self):
        case = nominal_cases()[0]
        case["peak_output_voltage_v"] = 40.0
        self.assertFalse(evaluate_case(case, 34.0)["path_named"])

    def test_a_negative_peak_is_rejected(self):
        case = nominal_cases()[0]
        case["peak_output_voltage_v"] = -1.0
        with self.assertRaises(ValueError):
            evaluate_case(case, 34.0)

    def test_a_case_without_a_name_is_rejected(self):
        case = nominal_cases()[0]
        case["name"] = " "
        with self.assertRaises(ValueError):
            evaluate_case(case, 34.0)

    def test_a_non_positive_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_case(nominal_cases()[0], 0.0)


class TestCoverageAndGrouping(unittest.TestCase):
    def test_a_complete_case_list_has_no_gap(self):
        results = [evaluate_case(c, 34.0) for c in nominal_cases()]
        self.assertEqual(coverage_gaps(results), [])

    def test_a_missing_required_category_is_a_gap(self):
        cases = [c for c in nominal_cases() if c["category"] != COMMAND_LOSS]
        results = [evaluate_case(c, 34.0) for c in cases]
        self.assertEqual(coverage_gaps(results), [COMMAND_LOSS])

    def test_an_unrecognized_required_category_is_rejected(self):
        results = [evaluate_case(c, 34.0) for c in nominal_cases()]
        with self.assertRaises(ValueError):
            coverage_gaps(results, ["kitchen-fire"])

    def test_an_empty_required_set_is_rejected(self):
        results = [evaluate_case(c, 34.0) for c in nominal_cases()]
        with self.assertRaises(ValueError):
            coverage_gaps(results, [])

    def test_bounded_cases_appear_under_no_path(self):
        results = [evaluate_case(c, 34.0) for c in nominal_cases()]
        self.assertEqual(group_by_path(results), {})

    def test_two_exceedances_on_one_path_group_together(self):
        cases = nominal_cases()
        for case in cases[:2]:
            case["peak_output_voltage_v"] = 40.0
            case["path"] = INDUCTIVE_KICK
        results = [evaluate_case(c, 34.0) for c in cases]
        self.assertEqual(
            group_by_path(results),
            {INDUCTIVE_KICK: ["output-stage-shorted", "output-stage-opened"]},
        )

    def test_grouping_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            group_by_path("results")


class TestWorstCase(unittest.TestCase):
    def test_the_worst_case_is_the_highest_relative_peak(self):
        results = [evaluate_case(c, 34.0) for c in nominal_cases()]
        self.assertEqual(worst_case(results)["name"], "output-stage-opened")

    def test_worst_case_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_case([])


class TestEndToEnd(unittest.TestCase):
    def test_a_bounded_case_list_reports_no_findings(self):
        report = evaluate_bounding(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "output-bounded-by-supply")
        self.assertTrue(report["bounded"])

    def test_one_exceedance_holds_the_bounding_statement(self):
        config = nominal_config()
        config["cases"][0]["peak_output_voltage_v"] = 40.0
        config["cases"][0]["path"] = INDUCTIVE_KICK
        report = evaluate_bounding(config)
        self.assertFalse(report["bounded"])
        self.assertEqual(report["status"], "hold-output-bounding")
        self.assertTrue(any("output-stage-shorted" in f for f in report["findings"]))

    def test_an_unnamed_path_adds_a_second_finding(self):
        config = nominal_config()
        config["cases"][0]["peak_output_voltage_v"] = 40.0
        report = evaluate_bounding(config)
        self.assertEqual(len(report["findings"]), 2)

    def test_a_missing_required_category_holds_the_statement(self):
        config = nominal_config()
        config["cases"] = [c for c in config["cases"]
                           if c["category"] != SUPPLY_TRANSIENT]
        report = evaluate_bounding(config)
        self.assertFalse(report["bounded"])
        self.assertEqual(report["coverage_gaps"], [SUPPLY_TRANSIENT])

    def test_a_higher_supply_envelope_can_bound_a_previous_exceedance(self):
        config = nominal_config()
        config["cases"][0]["peak_output_voltage_v"] = 40.0
        config["cases"][0]["path"] = INDUCTIVE_KICK
        self.assertFalse(evaluate_bounding(config)["bounded"])
        config["supply"]["max_v"] = 40.0
        self.assertTrue(evaluate_bounding(config)["bounded"])

    def test_the_report_carries_the_resolved_bound(self):
        self.assertAlmostEqual(
            evaluate_bounding(nominal_config())["supply_bound_v"], 34.0, places=9
        )

    def test_duplicate_case_names_are_rejected(self):
        config = nominal_config()
        config["cases"][1]["name"] = config["cases"][0]["name"]
        with self.assertRaises(ValueError):
            evaluate_bounding(config)

    def test_an_empty_case_list_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bounding({"supply": nominal_supply(), "cases": []})

    def test_a_missing_supply_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_bounding({"cases": nominal_cases()})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_bounding([("cases", [])])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            bounding_status("hold")

    def test_the_named_tolerance_is_far_below_any_supply_bound(self):
        self.assertLess(VOLTAGE_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
