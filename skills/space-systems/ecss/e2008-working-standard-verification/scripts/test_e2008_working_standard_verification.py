#!/usr/bin/env python3
"""Contract test for the working standard verification leaf (offline)."""

import copy
import datetime
import math
import unittest

from e2008_working_standard_verification_logic import (
    DEFAULT_LIMITS,
    DUE_VERDICT,
    INTERVAL_STATES,
    OUT_OF_LIMIT_VERDICT,
    TRACEABLE_VERDICT,
    UNCERTAINTY_COMPONENTS,
    assess_working_standard_verification,
    combined_standard_uncertainty_percent,
    cumulative_drift_percent,
    drift_is_significant,
    elapsed_days,
    expanded_uncertainty_percent,
    interval_state,
    longest_same_sign_run,
    parse_day,
    step_drifts_percent,
    validate_correlation,
    validate_history,
    validate_limits,
    validate_uncertainty_budget,
)

STEADY_HISTORY = [
    {"date": "2025-03-10", "reference_value_a": 0.45, "working_value_a": 0.4520},
    {"date": "2025-09-08", "reference_value_a": 0.45, "working_value_a": 0.4521},
    {"date": "2026-03-09", "reference_value_a": 0.45, "working_value_a": 0.4519},
]

CREEPING_HISTORY = [
    {"date": "2024-03-11", "reference_value_a": 0.45, "working_value_a": 0.4520},
    {"date": "2024-09-09", "reference_value_a": 0.45, "working_value_a": 0.4521},
    {"date": "2025-03-10", "reference_value_a": 0.45, "working_value_a": 0.4522},
    {"date": "2025-09-08", "reference_value_a": 0.45, "working_value_a": 0.4523},
]

SOUND_BUDGET = {
    "primary-reference": 0.40,
    "transfer-measurement": 0.20,
    "working-standard-repeatability": 0.15,
    "temperature-correction": 0.10,
    "spectral-mismatch": 0.25,
}

COARSE_BUDGET = {"primary-reference": 1.5, "transfer-measurement": 0.8}

SOUND_CASE = {
    "id": "WS-014",
    "agreed_interval_days": 365,
    "assessment_date": "2026-05-01",
    "history": STEADY_HISTORY,
    "uncertainty_budget": SOUND_BUDGET,
}


def _case(**changes):
    record = copy.deepcopy(SOUND_CASE)
    record.update(changes)
    return record


def _defect_names(result):
    return {entry["defect"] for entry in result["defects"]}


class DayParsingTests(unittest.TestCase):
    def test_an_iso_day_is_read(self):
        self.assertEqual(parse_day("d", "2026-03-09"), datetime.date(2026, 3, 9))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 3, 9)
        self.assertEqual(parse_day("d", day), day)

    def test_a_malformed_day_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("d", "09/03/2026")

    def test_an_empty_day_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("d", "  ")


class BudgetTests(unittest.TestCase):
    def test_a_sound_budget_is_normalised(self):
        budget = validate_uncertainty_budget(SOUND_BUDGET)
        self.assertEqual(set(budget), set(SOUND_BUDGET))

    def test_every_declared_component_name_is_accepted(self):
        budget = {name: 0.1 for name in UNCERTAINTY_COMPONENTS}
        self.assertEqual(len(validate_uncertainty_budget(budget)), len(UNCERTAINTY_COMPONENTS))

    def test_an_unknown_component_is_rejected(self):
        broken = dict(SOUND_BUDGET)
        broken["operator-mood"] = 0.1
        with self.assertRaises(ValueError):
            validate_uncertainty_budget(broken)

    def test_a_budget_without_the_primary_reference_is_rejected(self):
        broken = dict(SOUND_BUDGET)
        del broken["primary-reference"]
        with self.assertRaises(ValueError):
            validate_uncertainty_budget(broken)

    def test_an_empty_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_uncertainty_budget({})

    def test_a_negative_component_is_rejected(self):
        broken = dict(SOUND_BUDGET)
        broken["transfer-measurement"] = -0.2
        with self.assertRaises(ValueError):
            validate_uncertainty_budget(broken)

    def test_the_combined_uncertainty_is_a_root_sum_of_squares(self):
        combined = combined_standard_uncertainty_percent(COARSE_BUDGET)
        self.assertAlmostEqual(combined, math.sqrt(1.5 ** 2 + 0.8 ** 2), places=12)
        self.assertAlmostEqual(combined, 1.7, places=9)

    def test_the_expanded_uncertainty_is_the_coverage_factor_times_the_combined(self):
        expanded = expanded_uncertainty_percent(COARSE_BUDGET, 2.0)
        self.assertAlmostEqual(expanded, 3.4, places=9)

    def test_a_non_positive_coverage_factor_is_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty_percent(COARSE_BUDGET, 0.0)


class HistoryTests(unittest.TestCase):
    def test_a_sound_history_is_normalised_with_its_ratios(self):
        history = validate_history(STEADY_HISTORY)
        self.assertEqual(len(history), 3)
        self.assertAlmostEqual(history[0]["ratio"], 0.4520 / 0.45, places=12)

    def test_the_laboratory_defaults_when_it_is_not_stated(self):
        entry = validate_correlation(STEADY_HISTORY[0])
        self.assertEqual(entry["laboratory"], "unstated-laboratory")

    def test_an_out_of_order_history_is_rejected(self):
        records = list(reversed(copy.deepcopy(STEADY_HISTORY)))
        with self.assertRaises(ValueError):
            validate_history(records)

    def test_a_repeated_correlation_day_is_rejected(self):
        records = copy.deepcopy(STEADY_HISTORY)
        records[2]["date"] = records[1]["date"]
        with self.assertRaises(ValueError):
            validate_history(records)

    def test_an_empty_history_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_history([])

    def test_a_non_positive_reference_reading_is_rejected(self):
        records = copy.deepcopy(STEADY_HISTORY)
        records[0]["reference_value_a"] = 0.0
        with self.assertRaises(ValueError):
            validate_history(records)

    def test_a_non_mapping_correlation_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_correlation("2026-03-09")


class DriftTests(unittest.TestCase):
    def test_the_cumulative_drift_runs_from_the_baseline_correlation(self):
        drift = cumulative_drift_percent(validate_history(STEADY_HISTORY))
        self.assertAlmostEqual(drift, (0.4519 / 0.4520 - 1.0) * 100.0, places=12)

    def test_a_history_of_one_correlation_has_no_drift_and_no_step(self):
        history = validate_history([STEADY_HISTORY[0]])
        self.assertAlmostEqual(cumulative_drift_percent(history), 0.0, places=12)
        self.assertEqual(step_drifts_percent(history), ())

    def test_there_is_one_step_fewer_than_there_are_correlations(self):
        history = validate_history(STEADY_HISTORY)
        self.assertEqual(len(step_drifts_percent(history)), len(history) - 1)

    def test_a_steady_history_alternates_and_keeps_a_short_run(self):
        self.assertEqual(longest_same_sign_run(validate_history(STEADY_HISTORY)), 1)

    def test_a_creeping_history_runs_the_same_way_three_times(self):
        self.assertEqual(longest_same_sign_run(validate_history(CREEPING_HISTORY)), 3)

    def test_an_unmoved_standard_starts_no_run(self):
        flat = [
            {"date": "2025-03-10", "reference_value_a": 0.45, "working_value_a": 0.452},
            {"date": "2025-09-08", "reference_value_a": 0.45, "working_value_a": 0.452},
            {"date": "2026-03-09", "reference_value_a": 0.45, "working_value_a": 0.452},
        ]
        self.assertEqual(longest_same_sign_run(validate_history(flat)), 0)

    def test_a_drift_inside_the_expanded_uncertainty_is_not_significant(self):
        self.assertFalse(drift_is_significant(0.02, 1.086))

    def test_a_drift_beyond_the_expanded_uncertainty_is_significant(self):
        self.assertTrue(drift_is_significant(-1.4, 1.086))

    def test_a_drift_sitting_on_the_expanded_uncertainty_is_not_significant(self):
        self.assertFalse(drift_is_significant(1.086, 1.086))


class IntervalTests(unittest.TestCase):
    def test_the_elapsed_days_are_counted_from_the_latest_correlation(self):
        self.assertEqual(elapsed_days(validate_history(STEADY_HISTORY), "2026-05-01"), 53)

    def test_an_assessment_before_the_latest_correlation_is_rejected(self):
        with self.assertRaises(ValueError):
            elapsed_days(validate_history(STEADY_HISTORY), "2026-01-01")

    def test_a_fresh_correlation_sits_inside_the_interval(self):
        self.assertEqual(interval_state(10, 365, 0.9), "within-interval")

    def test_the_due_window_opens_exactly_on_its_fraction(self):
        self.assertEqual(interval_state(90, 100, 0.9), "correlation-due")

    def test_a_correlation_on_its_interval_day_is_due_not_overdue(self):
        self.assertEqual(interval_state(100, 100, 0.9), "correlation-due")

    def test_a_correlation_past_its_interval_is_overdue(self):
        self.assertEqual(interval_state(101, 100, 0.9), "correlation-overdue")

    def test_every_returned_state_is_one_of_the_declared_states(self):
        for elapsed in (0, 90, 100, 400):
            self.assertIn(interval_state(elapsed, 100, 0.9), INTERVAL_STATES)

    def test_a_negative_elapsed_count_is_rejected(self):
        with self.assertRaises(ValueError):
            interval_state(-1, 100, 0.9)

    def test_a_non_positive_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            interval_state(10, 0, 0.9)


class LimitTests(unittest.TestCase):
    def test_the_default_limits_validate(self):
        self.assertIs(validate_limits(DEFAULT_LIMITS), DEFAULT_LIMITS)

    def test_a_missing_limit_is_rejected(self):
        broken = dict(DEFAULT_LIMITS)
        del broken["coverage_factor"]
        with self.assertRaises(ValueError):
            validate_limits(broken)

    def test_a_due_window_fraction_above_one_is_rejected(self):
        broken = dict(DEFAULT_LIMITS)
        broken["due_window_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_limits(broken)

    def test_a_run_limit_below_two_is_rejected(self):
        broken = dict(DEFAULT_LIMITS)
        broken["systematic_run_limit"] = 1
        with self.assertRaises(ValueError):
            validate_limits(broken)

    def test_a_non_mapping_limit_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits(["drift_limit_percent"])


class AssessmentTests(unittest.TestCase):
    def test_a_correlated_standard_is_traceable(self):
        result = assess_working_standard_verification(SOUND_CASE)
        self.assertEqual(result["verdict"], TRACEABLE_VERDICT)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["interval_state"], "within-interval")
        self.assertEqual(result["latest_correlation"], "2026-03-09")

    def test_the_assessment_reports_its_uncertainty_arithmetic(self):
        result = assess_working_standard_verification(SOUND_CASE)
        self.assertAlmostEqual(
            result["expanded_uncertainty_percent"],
            2.0 * result["combined_standard_uncertainty_percent"],
            places=12,
        )
        self.assertFalse(result["drift_is_significant"])

    def test_a_standard_approaching_its_interval_is_reported_as_due(self):
        result = assess_working_standard_verification(_case(assessment_date="2027-02-02"))
        self.assertEqual(result["verdict"], DUE_VERDICT)
        self.assertEqual(result["interval_state"], "correlation-due")
        self.assertEqual(result["findings"], [])

    def test_a_standard_past_its_interval_fails(self):
        result = assess_working_standard_verification(_case(assessment_date="2027-03-10"))
        self.assertEqual(result["verdict"], OUT_OF_LIMIT_VERDICT)
        self.assertIn("correlation-overdue", _defect_names(result))

    def test_a_standard_that_moved_beyond_the_limit_fails(self):
        moved = copy.deepcopy(STEADY_HISTORY)
        moved[2]["working_value_a"] = 0.4600
        result = assess_working_standard_verification(_case(history=moved))
        self.assertEqual(result["verdict"], OUT_OF_LIMIT_VERDICT)
        self.assertIn("cumulative-drift-beyond-limit", _defect_names(result))
        self.assertTrue(result["drift_is_significant"])

    def test_a_move_beyond_the_limit_but_inside_the_uncertainty_is_still_a_defect(self):
        moved = copy.deepcopy(STEADY_HISTORY)
        moved[2]["working_value_a"] = 0.4560
        result = assess_working_standard_verification(_case(history=moved))
        self.assertIn("cumulative-drift-beyond-limit", _defect_names(result))
        self.assertLess(
            abs(result["cumulative_drift_percent"]), result["expanded_uncertainty_percent"]
        )
        self.assertFalse(result["drift_is_significant"])

    def test_a_creeping_standard_fails_on_trend_alone(self):
        result = assess_working_standard_verification(
            _case(history=CREEPING_HISTORY, assessment_date="2025-10-01")
        )
        self.assertEqual(result["verdict"], OUT_OF_LIMIT_VERDICT)
        self.assertEqual(_defect_names(result), {"systematic-drift-trend"})
        self.assertEqual(result["same_sign_run"], 3)

    def test_a_coarse_budget_fails_the_uncertainty_limit(self):
        result = assess_working_standard_verification(_case(uncertainty_budget=COARSE_BUDGET))
        self.assertEqual(result["verdict"], OUT_OF_LIMIT_VERDICT)
        self.assertIn("expanded-uncertainty-beyond-limit", _defect_names(result))

    def test_a_budget_sitting_exactly_on_the_uncertainty_limit_is_accepted(self):
        limits = dict(DEFAULT_LIMITS)
        limits["expanded_uncertainty_limit_percent"] = 3.4
        result = assess_working_standard_verification(
            _case(uncertainty_budget=COARSE_BUDGET), limits
        )
        self.assertNotIn("expanded-uncertainty-beyond-limit", _defect_names(result))

    def test_a_case_without_an_identifier_is_rejected(self):
        broken = _case()
        del broken["id"]
        with self.assertRaises(ValueError):
            assess_working_standard_verification(broken)

    def test_a_case_without_a_history_is_rejected(self):
        broken = _case()
        del broken["history"]
        with self.assertRaises(ValueError):
            assess_working_standard_verification(broken)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_working_standard_verification(["WS-014"])

    def test_broken_limits_are_rejected_before_any_arithmetic(self):
        broken = dict(DEFAULT_LIMITS)
        broken["drift_limit_percent"] = -0.5
        with self.assertRaises(ValueError):
            assess_working_standard_verification(SOUND_CASE, broken)


if __name__ == "__main__":
    unittest.main()
