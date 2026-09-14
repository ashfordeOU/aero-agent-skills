#!/usr/bin/env python3
"""Contract test for the standard recalibration schedule check (offline)."""

import copy
import unittest

from e2008_standard_recalibration_and_intercomparison_logic import (
    ACTIVITIES,
    DAYS_PER_YEAR,
    DEFAULT_SCHEDULE_POLICY,
    DEVIATION_OUT_OF_BAND,
    DEVIATION_WITHIN_BAND,
    STANDARD_ROLES,
    STATUS_DUE_SOON,
    STATUS_IN_DATE,
    STATUS_OVERDUE,
    VERDICT_DUE_SOON,
    VERDICT_FIT,
    VERDICT_INTERCOMPARISON_OVERDUE,
    VERDICT_OUT_OF_BAND,
    VERDICT_RECALIBRATION_OVERDUE,
    agreed_interval_days,
    days_to_band_edge,
    deviation_status,
    drift_rate_percent_per_year,
    interval_status,
    plan_standard_recalibration,
    relative_deviation_percent,
    validate_schedule_policy,
)

HEALTHY_CASE = {
    "role": "working-standard",
    "days_since_recalibration": 120.0,
    "days_since_intercomparison": 30.0,
    "working_standard_isc_a": 0.4980,
    "primary_standard_isc_a": 0.5000,
}

DRIFT_HISTORY = [
    {"day": 0.0, "deviation_percent": 0.0},
    {"day": 182.0, "deviation_percent": 0.2},
    {"day": 364.0, "deviation_percent": 0.4},
]


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_schedule_policy(DEFAULT_SCHEDULE_POLICY), DEFAULT_SCHEDULE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule_policy("default")

    def test_warning_fraction_above_one_rejected(self):
        broken = dict(DEFAULT_SCHEDULE_POLICY, warning_fraction=1.2)
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_intercomparison_longer_than_recalibration_rejected(self):
        broken = dict(DEFAULT_SCHEDULE_POLICY, intercomparison_interval_days=900.0)
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_zero_interval_rejected(self):
        broken = dict(DEFAULT_SCHEDULE_POLICY, recalibration_interval_days=0.0)
        with self.assertRaises(ValueError):
            validate_schedule_policy(broken)

    def test_customer_agreed_interval_beats_the_default(self):
        for activity in ACTIVITIES:
            key = "agreed_%s_interval_days" % activity
            agreed = agreed_interval_days(activity, {key: 90.0})
            self.assertAlmostEqual(agreed, 90.0, places=9)

    def test_default_interval_used_when_nothing_is_agreed(self):
        agreed = agreed_interval_days("recalibration", {})
        self.assertAlmostEqual(
            agreed, DEFAULT_SCHEDULE_POLICY["recalibration_interval_days"], places=9
        )

    def test_agreed_interval_rejects_an_unknown_activity(self):
        with self.assertRaises(ValueError):
            agreed_interval_days("re-certification", {})


class IntervalTests(unittest.TestCase):
    def test_fresh_interval_is_in_date(self):
        result = interval_status(10.0, 730.0, 0.9)
        self.assertEqual(result["status"], STATUS_IN_DATE)
        self.assertAlmostEqual(result["days_remaining"], 720.0, places=9)

    def test_interval_inside_the_warning_fraction_is_due_soon(self):
        result = interval_status(700.0, 730.0, 0.9)
        self.assertEqual(result["status"], STATUS_DUE_SOON)

    def test_day_count_exactly_on_the_interval_is_not_yet_overdue(self):
        result = interval_status(730.0, 730.0, 0.9)
        self.assertEqual(result["status"], STATUS_DUE_SOON)
        self.assertAlmostEqual(result["days_remaining"], 0.0, places=9)
        self.assertAlmostEqual(result["fraction_elapsed"], 1.0, places=9)

    def test_day_count_past_the_interval_is_overdue(self):
        result = interval_status(800.0, 730.0, 0.9)
        self.assertEqual(result["status"], STATUS_OVERDUE)
        self.assertAlmostEqual(result["days_remaining"], -70.0, places=9)

    def test_interval_rejects_a_negative_day_count(self):
        with self.assertRaises(ValueError):
            interval_status(-1.0, 730.0)

    def test_interval_rejects_a_missing_day_count(self):
        with self.assertRaises(ValueError):
            interval_status(None, 730.0)


class DeviationTests(unittest.TestCase):
    def test_deviation_is_signed_against_the_primary(self):
        low = relative_deviation_percent(0.495, 0.500)
        high = relative_deviation_percent(0.505, 0.500)
        self.assertAlmostEqual(low, -1.0, places=9)
        self.assertAlmostEqual(high, 1.0, places=9)

    def test_matching_standards_show_no_deviation(self):
        self.assertAlmostEqual(
            relative_deviation_percent(0.5, 0.5), 0.0, places=9
        )

    def test_deviation_rejects_a_zero_primary_value(self):
        with self.assertRaises(ValueError):
            relative_deviation_percent(0.5, 0.0)

    def test_deviation_on_the_band_edge_is_within_band(self):
        self.assertEqual(deviation_status(1.0, 1.0), DEVIATION_WITHIN_BAND)
        self.assertEqual(deviation_status(-1.0, 1.0), DEVIATION_WITHIN_BAND)

    def test_deviation_past_the_band_is_out_of_band(self):
        self.assertEqual(deviation_status(1.4, 1.0), DEVIATION_OUT_OF_BAND)

    def test_deviation_rejects_a_non_positive_band(self):
        with self.assertRaises(ValueError):
            deviation_status(0.2, 0.0)


class DriftTests(unittest.TestCase):
    def test_drift_rate_is_fitted_per_year(self):
        rate = drift_rate_percent_per_year(DRIFT_HISTORY)
        expected = (0.4 / 364.0) * DAYS_PER_YEAR
        self.assertAlmostEqual(rate, expected, places=9)

    def test_flat_history_shows_no_drift(self):
        flat = [
            {"day": 0.0, "deviation_percent": 0.2},
            {"day": 200.0, "deviation_percent": 0.2},
        ]
        self.assertAlmostEqual(drift_rate_percent_per_year(flat), 0.0, places=9)

    def test_drift_rejects_a_single_point(self):
        with self.assertRaises(ValueError):
            drift_rate_percent_per_year(DRIFT_HISTORY[:1])

    def test_drift_rejects_duplicate_days(self):
        doubled = [
            {"day": 10.0, "deviation_percent": 0.1},
            {"day": 10.0, "deviation_percent": 0.3},
        ]
        with self.assertRaises(ValueError):
            drift_rate_percent_per_year(doubled)

    def test_drift_rejects_a_non_list_history(self):
        with self.assertRaises(ValueError):
            drift_rate_percent_per_year({"day": 1.0, "deviation_percent": 0.1})

    def test_projection_reaches_the_positive_band_edge(self):
        days = days_to_band_edge(0.4, 0.4, 1.0)
        self.assertAlmostEqual(days, (0.6 / 0.4) * DAYS_PER_YEAR, places=9)

    def test_projection_reaches_the_negative_band_edge(self):
        days = days_to_band_edge(-0.4, -0.4, 1.0)
        self.assertAlmostEqual(days, (0.6 / 0.4) * DAYS_PER_YEAR, places=9)

    def test_projection_is_none_without_drift(self):
        self.assertIsNone(days_to_band_edge(0.4, 0.0, 1.0))

    def test_projection_is_zero_once_already_out_of_band(self):
        self.assertAlmostEqual(days_to_band_edge(1.5, 0.4, 1.0), 0.0, places=9)

    def test_projection_is_none_when_drift_moves_back_inward(self):
        self.assertIsNone(days_to_band_edge(0.9, 0.0, 1.0))


class PlanTests(unittest.TestCase):
    def test_healthy_standard_is_in_date_and_consistent(self):
        result = plan_standard_recalibration(HEALTHY_CASE)
        self.assertEqual(result["verdict"], VERDICT_FIT)
        self.assertTrue(result["usable_for_measurement"])
        self.assertEqual(result["deviation_status"], DEVIATION_WITHIN_BAND)

    def test_out_of_band_deviation_outranks_an_in_date_calendar(self):
        case = _case(HEALTHY_CASE, working_standard_isc_a=0.4880)
        result = plan_standard_recalibration(case)
        self.assertEqual(result["recalibration"]["status"], STATUS_IN_DATE)
        self.assertEqual(result["verdict"], VERDICT_OUT_OF_BAND)
        self.assertFalse(result["usable_for_measurement"])

    def test_overdue_recalibration_outranks_an_overdue_intercomparison(self):
        case = _case(
            HEALTHY_CASE,
            days_since_recalibration=900.0,
            days_since_intercomparison=400.0,
        )
        result = plan_standard_recalibration(case)
        self.assertEqual(result["verdict"], VERDICT_RECALIBRATION_OVERDUE)

    def test_overdue_intercomparison_is_reported_on_its_own(self):
        case = _case(HEALTHY_CASE, days_since_intercomparison=400.0)
        result = plan_standard_recalibration(case)
        self.assertEqual(result["verdict"], VERDICT_INTERCOMPARISON_OVERDUE)
        self.assertFalse(result["usable_for_measurement"])

    def test_warning_fraction_raises_a_due_soon_verdict(self):
        case = _case(HEALTHY_CASE, days_since_intercomparison=175.0)
        result = plan_standard_recalibration(case)
        self.assertEqual(result["verdict"], VERDICT_DUE_SOON)
        self.assertTrue(result["usable_for_measurement"])

    def test_a_shorter_agreed_interval_pulls_the_verdict_forward(self):
        case = _case(HEALTHY_CASE, agreed_intercomparison_interval_days=20.0)
        result = plan_standard_recalibration(case)
        self.assertEqual(result["verdict"], VERDICT_INTERCOMPARISON_OVERDUE)

    def test_drift_projection_warns_before_the_next_agreed_slot(self):
        case = _case(
            HEALTHY_CASE,
            intercomparison_history=DRIFT_HISTORY,
            working_standard_isc_a=0.5045,
        )
        result = plan_standard_recalibration(case)
        self.assertEqual(result["deviation_status"], DEVIATION_WITHIN_BAND)
        self.assertGreater(result["drift_rate_percent_per_year"], 0.1)
        self.assertLess(result["days_to_band_edge"], 152.0)
        self.assertTrue(any("band edge" in f for f in result["findings"]))

    def test_a_far_off_band_edge_raises_no_projection_warning(self):
        case = _case(
            HEALTHY_CASE,
            intercomparison_history=DRIFT_HISTORY,
            working_standard_isc_a=0.4955,
        )
        result = plan_standard_recalibration(case)
        self.assertGreater(result["days_to_band_edge"], 1000.0)
        self.assertFalse(any("band edge" in f for f in result["findings"]))

    def test_primary_standard_schedule_rests_on_recalibration(self):
        case = _case(
            HEALTHY_CASE, role="primary-standard", days_since_intercomparison=400.0
        )
        result = plan_standard_recalibration(case)
        self.assertTrue(any("no higher artefact" in f for f in result["findings"]))

    def test_plan_rejects_an_unknown_role(self):
        with self.assertRaises(ValueError):
            plan_standard_recalibration(_case(HEALTHY_CASE, role="spare"))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_standard_recalibration("working-standard")

    def test_plan_rejects_a_missing_recalibration_day_count(self):
        case = _case(HEALTHY_CASE)
        del case["days_since_recalibration"]
        with self.assertRaises(ValueError):
            plan_standard_recalibration(case)

    def test_every_role_is_accepted_by_the_plan(self):
        for role in STANDARD_ROLES:
            result = plan_standard_recalibration(_case(HEALTHY_CASE, role=role))
            self.assertEqual(result["role"], role)


if __name__ == "__main__":
    unittest.main()
