#!/usr/bin/env python3
"""Contract tests for the periodic records analysis of clause 5.5.3.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused analysis
policy, an analysis never run, one gone stale, a basis of too few
periods, cause groups accounting for more records than were counted, a
recurring cause that calls for corrective action, an indicator above its
alert, a rising slope at the action level and one below it.
"""

import unittest

from q1009_records_analysis_logic import (
    ANALYSIS_BASIS_TOO_SHORT,
    ANALYSIS_REPORTED_NO_ACTION,
    CORRECTIVE_ACTION_REQUIRED,
    DEFAULT_ANALYSIS_POLICY,
    RECORDS_NOT_ANALYSED,
    TREND_FALLING,
    TREND_FLAT,
    TREND_RISING,
    TREND_UNDER_WATCH,
    analysis_is_current,
    assess_nonconformance_records_analysis,
    cause_totals,
    check_cause_consistency,
    dominant_cause,
    latest_rate,
    mean_rate,
    pareto_cause_count,
    period_rates,
    ranked_causes,
    recurrence_calls_for_action,
    total_nonconformances,
    trend_direction,
    trend_slope,
    validate_analysis_policy,
    validate_cause_record,
    validate_period_record,
    validate_periods,
)


def _policy(**overrides):
    policy = dict(DEFAULT_ANALYSIS_POLICY)
    policy.update(overrides)
    return policy


def _periods(counts=(4, 4, 4), exposures=None):
    exposures = exposures or [20.0] * len(counts)
    return [
        {
            "period": "month-%d" % (index + 1),
            "nonconformance_count": count,
            "exposure": exposures[index],
        }
        for index, count in enumerate(counts)
    ]


def _causes(**overrides):
    causes = {
        "workmanship-solder-bridge": 2,
        "drawing-tolerance-error": 2,
        "supplier-material-deviation": 2,
    }
    causes.update(overrides)
    return [
        {"cause_category": name, "count": count} for name, count in causes.items()
    ]


def _analysis(**overrides):
    analysis = {
        "periods": _periods(),
        "causes": _causes(),
        "last_analysis_day": 300,
        "as_of_day": 330,
    }
    analysis.update(overrides)
    return analysis


def _case(**overrides):
    case = {"policy": _policy(), "analysis": _analysis()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_analysis_policy(DEFAULT_ANALYSIS_POLICY), DEFAULT_ANALYSIS_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_analysis_policy(90)

    def test_single_period_basis_refused(self):
        with self.assertRaises(ValueError):
            validate_analysis_policy(_policy(min_periods=1))

    def test_single_occurrence_recurrence_refused(self):
        with self.assertRaises(ValueError):
            validate_analysis_policy(_policy(min_recurrence_count=1))

    def test_zero_rate_alert_refused(self):
        with self.assertRaises(ValueError):
            validate_analysis_policy(_policy(rate_alert=0.0))


class PeriodValidationTests(unittest.TestCase):
    def test_period_is_read_back(self):
        record = validate_period_record(_periods()[0])
        self.assertEqual(record["period"], "month-1")
        self.assertAlmostEqual(record["exposure"], 20.0, places=9)

    def test_zero_exposure_refused(self):
        with self.assertRaises(ValueError):
            validate_period_record(
                {"period": "month-9", "nonconformance_count": 3, "exposure": 0.0}
            )

    def test_negative_count_refused(self):
        with self.assertRaises(ValueError):
            validate_period_record(
                {"period": "month-9", "nonconformance_count": -1, "exposure": 5.0}
            )

    def test_duplicate_period_refused(self):
        with self.assertRaises(ValueError):
            validate_periods(_periods() + [_periods()[0]])

    def test_empty_period_list_refused(self):
        with self.assertRaises(ValueError):
            validate_periods([])


class RateAndTrendTests(unittest.TestCase):
    def test_rates_are_normalised_by_exposure(self):
        rates = period_rates(_periods(counts=(4, 6), exposures=[20.0, 20.0]))
        self.assertAlmostEqual(rates[0], 0.2, places=9)
        self.assertAlmostEqual(rates[1], 0.3, places=9)

    def test_the_same_count_over_more_exposure_is_a_lower_rate(self):
        rates = period_rates(_periods(counts=(6, 6), exposures=[20.0, 60.0]))
        self.assertAlmostEqual(rates[1], rates[0] / 3.0, places=9)

    def test_mean_and_latest_rate_are_taken_over_the_set(self):
        periods = _periods(counts=(2, 4, 6), exposures=[20.0, 20.0, 20.0])
        self.assertAlmostEqual(mean_rate(periods), 0.2, places=9)
        self.assertAlmostEqual(latest_rate(periods), 0.3, places=9)

    def test_total_nonconformances_sums_the_periods(self):
        self.assertEqual(total_nonconformances(_periods(counts=(2, 4, 6))), 12)

    def test_a_flat_series_has_no_slope(self):
        slope = trend_slope(_periods(counts=(4, 4, 4)))
        self.assertAlmostEqual(slope, 0.0, places=9)
        self.assertEqual(trend_direction(slope), TREND_FLAT)

    def test_a_rising_series_has_a_positive_slope(self):
        slope = trend_slope(_periods(counts=(2, 4, 6), exposures=[20.0] * 3))
        self.assertAlmostEqual(slope, 0.1, places=9)
        self.assertEqual(trend_direction(slope), TREND_RISING)

    def test_a_falling_series_has_a_negative_slope(self):
        slope = trend_slope(_periods(counts=(6, 4, 2), exposures=[20.0] * 3))
        self.assertAlmostEqual(slope, -0.1, places=9)
        self.assertEqual(trend_direction(slope), TREND_FALLING)

    def test_the_slope_does_not_swing_on_one_noisy_period(self):
        steady = trend_slope(_periods(counts=(4, 4, 4, 4, 9), exposures=[20.0] * 5))
        endpoints = (9 / 20.0 - 4 / 20.0) / 4.0
        self.assertLess(steady, endpoints)

    def test_a_single_period_has_no_trend(self):
        with self.assertRaises(ValueError):
            trend_slope(_periods(counts=(4,)))


class CauseGroupingTests(unittest.TestCase):
    def test_a_category_declared_twice_is_summed(self):
        totals = cause_totals(
            [
                {"cause_category": "workmanship-solder-bridge", "count": 2},
                {"cause_category": "workmanship-solder-bridge", "count": 3},
            ]
        )
        self.assertEqual(totals["workmanship-solder-bridge"], 5)

    def test_a_cause_group_with_no_occurrences_refused(self):
        with self.assertRaises(ValueError):
            validate_cause_record({"cause_category": "nothing-here", "count": 0})

    def test_a_blank_cause_category_refused(self):
        with self.assertRaises(ValueError):
            validate_cause_record({"cause_category": "   ", "count": 2})

    def test_causes_rank_by_occurrences(self):
        ranked = ranked_causes(_causes(**{"workmanship-solder-bridge": 7}))
        self.assertEqual(ranked[0][0], "workmanship-solder-bridge")

    def test_dominant_cause_carries_its_share(self):
        dominant = dominant_cause(_causes(**{"workmanship-solder-bridge": 6}))
        self.assertAlmostEqual(dominant["share"], 0.6, places=9)

    def test_no_causes_at_all_has_no_dominant_group(self):
        self.assertIsNone(dominant_cause([]))

    def test_pareto_count_is_the_categories_needed_to_reach_the_share(self):
        causes = [
            {"cause_category": "workmanship-solder-bridge", "count": 8},
            {"cause_category": "drawing-tolerance-error", "count": 1},
            {"cause_category": "supplier-material-deviation", "count": 1},
        ]
        self.assertEqual(pareto_cause_count(causes), 1)

    def test_cause_groups_above_the_records_counted_are_refused(self):
        with self.assertRaises(ValueError):
            check_cause_consistency(
                _periods(counts=(1, 1, 1)), _causes(**{"drawing-tolerance-error": 9})
            )

    def test_ungrouped_records_are_reported(self):
        self.assertEqual(check_cause_consistency(_periods(counts=(4, 4, 4)), _causes()), 6)

    def test_a_frequent_dominant_cause_calls_for_action(self):
        self.assertTrue(
            recurrence_calls_for_action(_causes(**{"workmanship-solder-bridge": 6}))
        )

    def test_a_dominant_but_rare_cause_does_not(self):
        causes = [
            {"cause_category": "workmanship-solder-bridge", "count": 2},
            {"cause_category": "drawing-tolerance-error", "count": 1},
        ]
        self.assertFalse(recurrence_calls_for_action(causes))


class CurrencyTests(unittest.TestCase):
    def test_an_analysis_inside_the_interval_is_current(self):
        self.assertTrue(analysis_is_current(300, 330))

    def test_an_analysis_outside_the_interval_is_not(self):
        self.assertFalse(analysis_is_current(100, 330))

    def test_no_analysis_at_all_is_not_current(self):
        self.assertFalse(analysis_is_current(None, 330))

    def test_an_analysis_dated_after_today_is_refused(self):
        with self.assertRaises(ValueError):
            analysis_is_current(400, 330)


class AssessmentTests(unittest.TestCase):
    def test_a_steady_analysed_set_needs_no_action(self):
        result = assess_nonconformance_records_analysis(_case())
        self.assertEqual(result["verdict"], ANALYSIS_REPORTED_NO_ACTION)
        self.assertAlmostEqual(result["trend_slope"], 0.0, places=9)

    def test_no_analysis_at_all_stops_the_assessment(self):
        result = assess_nonconformance_records_analysis(_case(analysis=None))
        self.assertEqual(result["verdict"], RECORDS_NOT_ANALYSED)

    def test_a_stale_analysis_is_not_an_analysis(self):
        result = assess_nonconformance_records_analysis(
            _case(analysis=_analysis(last_analysis_day=100))
        )
        self.assertEqual(result["verdict"], RECORDS_NOT_ANALYSED)

    def test_too_few_periods_outranks_the_later_checks(self):
        analysis = _analysis(periods=_periods(counts=(4, 4)), causes=[])
        result = assess_nonconformance_records_analysis(_case(analysis=analysis))
        self.assertEqual(result["verdict"], ANALYSIS_BASIS_TOO_SHORT)

    def test_a_recurring_cause_requires_corrective_action(self):
        analysis = _analysis(causes=_causes(**{"workmanship-solder-bridge": 6}))
        result = assess_nonconformance_records_analysis(_case(analysis=analysis))
        self.assertEqual(result["verdict"], CORRECTIVE_ACTION_REQUIRED)
        self.assertEqual(
            result["dominant_cause"]["cause_category"], "workmanship-solder-bridge"
        )

    def test_an_indicator_above_its_alert_requires_corrective_action(self):
        analysis = _analysis(
            periods=_periods(counts=(12, 12, 12), exposures=[20.0] * 3), causes=[]
        )
        result = assess_nonconformance_records_analysis(_case(analysis=analysis))
        self.assertEqual(result["verdict"], CORRECTIVE_ACTION_REQUIRED)

    def test_a_rising_slope_at_the_action_level_requires_corrective_action(self):
        analysis = _analysis(
            periods=_periods(counts=(1, 3, 5), exposures=[20.0] * 3), causes=[]
        )
        result = assess_nonconformance_records_analysis(_case(analysis=analysis))
        self.assertEqual(result["verdict"], CORRECTIVE_ACTION_REQUIRED)

    def test_a_rising_slope_below_the_action_level_is_watched(self):
        analysis = _analysis(
            periods=_periods(counts=(4, 4, 5), exposures=[100.0] * 3), causes=[]
        )
        result = assess_nonconformance_records_analysis(_case(analysis=analysis))
        self.assertEqual(result["verdict"], TREND_UNDER_WATCH)
        self.assertEqual(result["trend_direction"], TREND_RISING)
        self.assertEqual(len(result["advisories"]), 2)

    def test_ungrouped_records_are_advised_not_refused(self):
        result = assess_nonconformance_records_analysis(_case())
        self.assertEqual(result["ungrouped_records"], 6)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_analysis_with_no_periods_key_is_refused(self):
        analysis = _analysis()
        del analysis["periods"]
        with self.assertRaises(ValueError):
            assess_nonconformance_records_analysis(_case(analysis=analysis))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_nonconformance_records_analysis(("analysis",))


if __name__ == "__main__":
    unittest.main()
