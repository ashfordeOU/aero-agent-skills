#!/usr/bin/env python3
"""Gate 3 contract test for e2007-susceptibility-threshold-determination.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_susceptibility_threshold_determination.py
"""

import unittest

from e2007_susceptibility_threshold_determination_logic import (
    CATEGORY_COMPLIANT,
    CATEGORY_MARGINAL,
    CATEGORY_SUSCEPTIBLE,
    DB_TOL,
    DEFAULT_MAX_BRACKET_DB,
    DEFAULT_REQUIRED_MARGIN_DB,
    RECOGNIZED_MODULATIONS,
    RECOGNIZED_RUN_TYPES,
    assess_susceptibility_thresholds,
    at_least,
    at_most,
    bracket_is_resolved,
    categorize_margin,
    cessation_index,
    cessation_level_dbuv,
    determine_threshold,
    governing_observation,
    last_disturbed_level_dbuv,
    normalize_modulation,
    normalize_run_type,
    search_bracket_db,
    susceptibility_margin_db,
    validate_level_search,
    validate_observation,
    validate_run_context,
)


def descending_search():
    return [
        {"level_dbuv": 140.0, "disturbance": True},
        {"level_dbuv": 138.0, "disturbance": True},
        {"level_dbuv": 136.0, "disturbance": False},
        {"level_dbuv": 132.0, "disturbance": False},
    ]


def good_observation(**over):
    record = {
        "frequency_hz": 4.0e6,
        "modulation": "pulse-modulated",
        "affected_function": "star tracker quaternion output",
        "observed_parameter": "attitude residual beyond its declared band",
        "required_level_dbuv": 128.0,
        "search": descending_search(),
    }
    record.update(over)
    return record


def good_context(**over):
    record = {
        "run_type": "radiated-susceptibility",
        "function_monitored": True,
        "required_margin_db": DEFAULT_REQUIRED_MARGIN_DB,
        "max_bracket_db": DEFAULT_MAX_BRACKET_DB,
    }
    record.update(over)
    return record


class TestVocabulary(unittest.TestCase):
    def test_every_recognized_modulation_normalizes(self):
        for name in RECOGNIZED_MODULATIONS:
            self.assertEqual(normalize_modulation(name.upper()), name)

    def test_unrecognized_modulation_rejected(self):
        with self.assertRaises(ValueError):
            normalize_modulation("swept-noise")

    def test_every_recognized_run_type_normalizes(self):
        for name in RECOGNIZED_RUN_TYPES:
            self.assertEqual(normalize_run_type(" %s " % name), name)

    def test_non_string_run_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_run_type(7)


class TestSearchValidation(unittest.TestCase):
    def test_clean_search_normalizes(self):
        points = validate_level_search(descending_search())
        self.assertEqual(len(points), 4)
        self.assertTrue(points[0]["disturbance"])

    def test_single_point_search_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_search([{"level_dbuv": 140.0, "disturbance": True}])

    def test_non_list_search_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_search({"level_dbuv": 140.0, "disturbance": True})

    def test_missing_search_rejected(self):
        with self.assertRaises(ValueError):
            validate_level_search(None)

    def test_rising_level_rejected(self):
        points = descending_search()
        points[2]["level_dbuv"] = 139.0
        points[3]["level_dbuv"] = 141.0
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_repeated_level_rejected(self):
        points = descending_search()
        points[1]["level_dbuv"] = points[0]["level_dbuv"]
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_search_that_never_disturbs_rejected(self):
        points = descending_search()
        points[0]["disturbance"] = False
        points[1]["disturbance"] = False
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_search_still_disturbed_at_the_bottom_rejected(self):
        points = descending_search()
        for point in points:
            point["disturbance"] = True
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_reappearing_disturbance_rejected(self):
        points = descending_search()
        points[3]["disturbance"] = True
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_non_boolean_indication_rejected(self):
        points = descending_search()
        points[1]["disturbance"] = "yes"
        with self.assertRaises(ValueError):
            validate_level_search(points)

    def test_missing_level_rejected(self):
        points = descending_search()
        del points[1]["level_dbuv"]
        with self.assertRaises(ValueError):
            validate_level_search(points)


class TestCessationAndBracket(unittest.TestCase):
    def test_cessation_index_is_the_first_undisturbed_step(self):
        points = validate_level_search(descending_search())
        self.assertEqual(cessation_index(points), 2)

    def test_threshold_is_the_level_at_which_it_ceases(self):
        points = validate_level_search(descending_search())
        self.assertAlmostEqual(cessation_level_dbuv(points), 136.0)

    def test_last_disturbed_level_is_one_step_up(self):
        points = validate_level_search(descending_search())
        self.assertAlmostEqual(last_disturbed_level_dbuv(points), 138.0)

    def test_bracket_is_the_step_across_the_transition(self):
        points = validate_level_search(descending_search())
        self.assertAlmostEqual(search_bracket_db(points), 2.0)

    def test_fine_bracket_is_resolved(self):
        self.assertTrue(bracket_is_resolved(1.0))

    def test_coarse_bracket_is_not_resolved(self):
        self.assertFalse(bracket_is_resolved(6.0))

    def test_bracket_on_the_bound_is_resolved_despite_float_error(self):
        # 136.3 - 134.3 is 2.0000000000000284 in binary floating point, so a
        # step that is physically exactly the 2 dB bound reads over it.
        points = validate_level_search(
            [
                {"level_dbuv": 140.0, "disturbance": True},
                {"level_dbuv": 136.3, "disturbance": True},
                {"level_dbuv": 134.3, "disturbance": False},
            ]
        )
        self.assertAlmostEqual(search_bracket_db(points), 2.0, places=9)
        self.assertTrue(bracket_is_resolved(search_bracket_db(points)))

    def test_zero_bracket_bound_rejected(self):
        with self.assertRaises(ValueError):
            bracket_is_resolved(1.0, max_bracket_db=0.0)


class TestMarginCategorization(unittest.TestCase):
    def test_margin_is_threshold_minus_requirement(self):
        self.assertAlmostEqual(susceptibility_margin_db(136.0, 128.0), 8.0)

    def test_wide_margin_is_compliant(self):
        self.assertEqual(categorize_margin(12.0), CATEGORY_COMPLIANT)

    def test_short_margin_is_marginal(self):
        self.assertEqual(categorize_margin(3.0), CATEGORY_MARGINAL)

    def test_zero_margin_is_susceptible(self):
        self.assertEqual(categorize_margin(0.0), CATEGORY_SUSCEPTIBLE)

    def test_negative_margin_is_susceptible(self):
        self.assertEqual(categorize_margin(-4.0), CATEGORY_SUSCEPTIBLE)

    def test_exact_required_margin_is_compliant_despite_float_error(self):
        # 134.3 - 128.3 is 5.999999999999972 in binary floating point, so a
        # physically compliant 6 dB margin reads short of the requirement.
        margin = susceptibility_margin_db(134.3, 128.3)
        self.assertAlmostEqual(margin, DEFAULT_REQUIRED_MARGIN_DB, places=9)
        self.assertEqual(categorize_margin(margin), CATEGORY_COMPLIANT)

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            categorize_margin(8.0, required_margin_db=-1.0)

    def test_non_numeric_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            categorize_margin(8.0, required_margin_db="six")

    def test_comparison_helpers_absorb_float_error_only(self):
        self.assertTrue(at_least(6.0, 6.0))
        self.assertTrue(at_least(6.0 - DB_TOL / 2.0, 6.0))
        self.assertFalse(at_least(5.0, 6.0))
        self.assertTrue(at_most(2.0, 2.0))
        self.assertTrue(at_most(2.0 + DB_TOL / 2.0, 2.0))
        self.assertFalse(at_most(3.0, 2.0))


class TestObservationValidation(unittest.TestCase):
    def test_good_observation_normalizes(self):
        record = validate_observation(good_observation())
        self.assertAlmostEqual(record["frequency_hz"], 4.0e6)
        self.assertEqual(record["modulation"], "pulse-modulated")

    def test_missing_affected_function_rejected(self):
        record = good_observation()
        del record["affected_function"]
        with self.assertRaises(ValueError):
            validate_observation(record)

    def test_blank_observed_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(good_observation(observed_parameter="   "))

    def test_zero_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation(good_observation(frequency_hz=0.0))

    def test_missing_required_level_rejected(self):
        record = good_observation()
        del record["required_level_dbuv"]
        with self.assertRaises(ValueError):
            validate_observation(record)

    def test_non_mapping_observation_rejected(self):
        with self.assertRaises(ValueError):
            validate_observation("disturbed at 138 dBuV")


class TestThresholdDetermination(unittest.TestCase):
    def test_threshold_and_margin_are_recorded(self):
        result = determine_threshold(good_observation())
        self.assertAlmostEqual(result["threshold_dbuv"], 136.0)
        self.assertAlmostEqual(result["margin_db"], 8.0)
        self.assertEqual(result["category"], CATEGORY_COMPLIANT)
        self.assertTrue(result["resolved"])

    def test_threshold_below_the_requirement_is_susceptible(self):
        result = determine_threshold(good_observation(required_level_dbuv=140.0))
        self.assertEqual(result["category"], CATEGORY_SUSCEPTIBLE)

    def test_short_margin_is_marginal(self):
        result = determine_threshold(good_observation(required_level_dbuv=133.0))
        self.assertEqual(result["category"], CATEGORY_MARGINAL)

    def test_coarse_search_is_reported_unresolved(self):
        coarse = [
            {"level_dbuv": 150.0, "disturbance": True},
            {"level_dbuv": 136.0, "disturbance": False},
        ]
        result = determine_threshold(good_observation(search=coarse))
        self.assertFalse(result["resolved"])
        self.assertAlmostEqual(result["bracket_db"], 14.0)

    def test_step_count_is_carried(self):
        self.assertEqual(determine_threshold(good_observation())["steps"], 4)

    def test_governing_observation_holds_the_smallest_margin(self):
        wide = determine_threshold(good_observation())
        tight = determine_threshold(
            good_observation(frequency_hz=8.0e6, required_level_dbuv=134.0)
        )
        self.assertAlmostEqual(
            governing_observation([wide, tight])["frequency_hz"], 8.0e6
        )

    def test_governing_observation_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            governing_observation([])


class TestRunAssessment(unittest.TestCase):
    def test_clean_run_demonstrates_immunity(self):
        report = assess_susceptibility_thresholds(
            good_context(), [good_observation()]
        )
        self.assertEqual(report["verdict"], "immunity-demonstrated")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["counts"][CATEGORY_COMPLIANT], 1)

    def test_susceptible_frequency_raises_a_finding(self):
        report = assess_susceptibility_thresholds(
            good_context(),
            [good_observation(), good_observation(frequency_hz=9.0e6, required_level_dbuv=141.0)],
        )
        self.assertEqual(report["verdict"], "susceptibility-finding")
        self.assertTrue(any("susceptibility of" in f for f in report["findings"]))

    def test_marginal_frequency_is_a_limitation_not_a_finding(self):
        report = assess_susceptibility_thresholds(
            good_context(), [good_observation(required_level_dbuv=133.0)]
        )
        self.assertEqual(report["verdict"], "immunity-demonstrated")
        self.assertTrue(any("margin of only" in l for l in report["limitations"]))

    def test_unresolved_bracket_is_carried_as_a_limitation(self):
        coarse = [
            {"level_dbuv": 150.0, "disturbance": True},
            {"level_dbuv": 136.0, "disturbance": False},
        ]
        report = assess_susceptibility_thresholds(
            good_context(), [good_observation(search=coarse)]
        )
        self.assertTrue(any("bracketed to" in l for l in report["limitations"]))

    def test_observations_are_ordered_by_frequency(self):
        report = assess_susceptibility_thresholds(
            good_context(),
            [good_observation(frequency_hz=9.0e6), good_observation(frequency_hz=2.0e6)],
        )
        self.assertEqual(
            [r["frequency_hz"] for r in report["observations"]], [2.0e6, 9.0e6]
        )

    def test_governing_frequency_is_reported(self):
        report = assess_susceptibility_thresholds(
            good_context(),
            [good_observation(), good_observation(frequency_hz=6.0e6, required_level_dbuv=134.0)],
        )
        self.assertAlmostEqual(report["governing_frequency_hz"], 6.0e6)
        self.assertAlmostEqual(report["governing_margin_db"], 2.0)

    def test_unmonitored_function_rejects_the_context(self):
        with self.assertRaises(ValueError):
            validate_run_context(good_context(function_monitored=False))

    def test_zero_bracket_bound_rejects_the_context(self):
        with self.assertRaises(ValueError):
            validate_run_context(good_context(max_bracket_db=0.0))

    def test_non_mapping_context_rejected(self):
        with self.assertRaises(ValueError):
            validate_run_context("radiated susceptibility, function monitored")

    def test_empty_observation_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_thresholds(good_context(), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
