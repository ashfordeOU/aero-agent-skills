#!/usr/bin/env python3
"""Contract tests for facility dependability, clause 5.6.6.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: refused targets,
no record at all, hours that exceed their own period, an availability
landing exactly on its target, a period with no failure leaving the
mean time between failures undefined, waiting hours kept out of the
mean time to restore, a stale monitoring record and each target missed.
"""

import unittest

from q2007_tf_dependability_logic import (
    AVAILABILITY_TARGET_MISSED,
    DEFAULT_DEPENDABILITY_TARGETS,
    LOGISTIC_GAP_UNDER_WATCH,
    MONITORING_STALE,
    NO_DEPENDABILITY_RECORD,
    RELIABILITY_TARGET_MISSED,
    RESTORE_TARGET_MISSED,
    TARGETS_MET,
    achieved_availability,
    assess_facility_dependability,
    downtime_hours,
    inherent_availability,
    logistic_gap,
    mean_time_between_failures,
    mean_time_to_restore,
    monitoring_is_current,
    validate_dependability_targets,
    validate_operating_record,
)


def _targets(**overrides):
    targets = dict(DEFAULT_DEPENDABILITY_TARGETS)
    targets.update(overrides)
    return targets


def _record(**overrides):
    record = {
        "period_hours": 1000.0,
        "operating_hours": 960.0,
        "repair_hours": 24.0,
        "waiting_hours": 16.0,
        "failure_count": 4,
        "repair_count": 4,
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {
        "targets": _targets(),
        "record": _record(),
        "last_review_day": 300,
        "as_of_day": 400,
    }
    case.update(overrides)
    return case


class TargetValidationTests(unittest.TestCase):
    def test_default_targets_are_usable(self):
        self.assertIs(
            validate_dependability_targets(DEFAULT_DEPENDABILITY_TARGETS),
            DEFAULT_DEPENDABILITY_TARGETS,
        )

    def test_non_mapping_targets_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(0.95)

    def test_an_availability_target_of_zero_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(_targets(availability_target=0.0))

    def test_an_availability_target_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(_targets(availability_target=1.2))

    def test_a_non_positive_mtbf_target_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(_targets(mtbf_target_hours=0.0))

    def test_a_zero_review_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(_targets(review_interval_days=0))

    def test_a_watch_band_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_dependability_targets(_targets(logistic_gap_watch=1.5))


class RecordValidationTests(unittest.TestCase):
    def test_record_is_read_back(self):
        checked = validate_operating_record(_record())
        self.assertAlmostEqual(checked["operating_hours"], 960.0, places=9)
        self.assertEqual(checked["failure_count"], 4)

    def test_a_record_filling_its_period_exactly_is_accepted(self):
        checked = validate_operating_record(
            _record(operating_hours=960.0, repair_hours=24.0, waiting_hours=16.0)
        )
        self.assertAlmostEqual(checked["period_hours"], 1000.0, places=9)

    def test_hours_beyond_the_period_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_record(
                _record(operating_hours=990.0, repair_hours=20.0)
            )

    def test_a_zero_period_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_record(_record(period_hours=0.0))

    def test_negative_repair_hours_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_record(_record(repair_hours=-1.0))

    def test_a_non_integer_failure_count_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_record(_record(failure_count=2.5))

    def test_repair_hours_against_no_repair_refused(self):
        with self.assertRaises(ValueError):
            validate_operating_record(_record(repair_count=0, failure_count=0))


class AvailabilityTests(unittest.TestCase):
    def test_downtime_is_repair_plus_waiting(self):
        self.assertAlmostEqual(downtime_hours(_record()), 40.0, places=9)

    def test_achieved_availability_comes_out_of_the_record(self):
        self.assertAlmostEqual(achieved_availability(_record()), 0.96, places=9)

    def test_a_facility_with_no_downtime_is_fully_available(self):
        self.assertAlmostEqual(
            achieved_availability(
                _record(
                    operating_hours=1000.0,
                    repair_hours=0.0,
                    waiting_hours=0.0,
                    failure_count=0,
                    repair_count=0,
                )
            ),
            1.0,
            places=9,
        )

    def test_a_record_with_neither_uptime_nor_downtime_refused(self):
        with self.assertRaises(ValueError):
            achieved_availability(
                _record(
                    operating_hours=0.0,
                    repair_hours=0.0,
                    waiting_hours=0.0,
                    failure_count=0,
                    repair_count=0,
                )
            )


class MeanTimeTests(unittest.TestCase):
    def test_mtbf_is_operating_hours_per_failure(self):
        self.assertAlmostEqual(
            mean_time_between_failures(_record()), 240.0, places=9
        )

    def test_a_period_with_no_failure_has_no_mtbf(self):
        self.assertIsNone(
            mean_time_between_failures(
                _record(
                    failure_count=0,
                    repair_count=0,
                    repair_hours=0.0,
                    operating_hours=1000.0,
                    waiting_hours=0.0,
                )
            )
        )

    def test_mttr_leaves_the_waiting_hours_out(self):
        self.assertAlmostEqual(mean_time_to_restore(_record()), 6.0, places=9)

    def test_more_waiting_does_not_move_the_mttr(self):
        self.assertAlmostEqual(
            mean_time_to_restore(_record(waiting_hours=30.0, operating_hours=940.0)),
            6.0,
            places=9,
        )

    def test_inherent_availability_follows_the_two_mean_times(self):
        self.assertAlmostEqual(
            inherent_availability(_record()), 240.0 / 246.0, places=9
        )

    def test_inherent_availability_is_absent_without_a_failure(self):
        self.assertIsNone(
            inherent_availability(
                _record(
                    failure_count=0,
                    repair_count=0,
                    repair_hours=0.0,
                    operating_hours=1000.0,
                    waiting_hours=0.0,
                )
            )
        )

    def test_the_logistic_gap_is_the_inherent_less_the_achieved(self):
        self.assertAlmostEqual(
            logistic_gap(_record()), 240.0 / 246.0 - 0.96, places=9
        )

    def test_the_inherent_value_never_sits_below_the_achieved_one(self):
        self.assertGreater(logistic_gap(_record()), 0.0)


class MonitoringTests(unittest.TestCase):
    def test_a_review_inside_the_interval_is_current(self):
        self.assertTrue(monitoring_is_current(300, 400))

    def test_a_review_outside_the_interval_is_not(self):
        self.assertFalse(monitoring_is_current(100, 400))

    def test_no_review_at_all_is_not_current(self):
        self.assertFalse(monitoring_is_current(None, 400))

    def test_a_review_dated_after_today_refused(self):
        with self.assertRaises(ValueError):
            monitoring_is_current(500, 400)


class AssessmentTests(unittest.TestCase):
    def test_a_dependable_facility_meets_its_targets(self):
        result = assess_facility_dependability(_case())
        self.assertEqual(result["verdict"], TARGETS_MET)
        self.assertAlmostEqual(result["achieved_availability"], 0.96, places=9)
        self.assertAlmostEqual(result["mttr_hours"], 6.0, places=9)

    def test_no_record_at_all_stops_the_assessment(self):
        result = assess_facility_dependability(_case(record=None))
        self.assertEqual(result["verdict"], NO_DEPENDABILITY_RECORD)

    def test_a_stale_monitoring_record_outranks_a_missed_target(self):
        result = assess_facility_dependability(
            _case(
                last_review_day=10,
                record=_record(operating_hours=800.0, waiting_hours=176.0),
            )
        )
        self.assertEqual(result["verdict"], MONITORING_STALE)

    def test_a_missed_availability_target_is_reported(self):
        result = assess_facility_dependability(
            _case(
                record=_record(
                    operating_hours=900.0, repair_hours=50.0, waiting_hours=50.0
                )
            )
        )
        self.assertEqual(result["verdict"], AVAILABILITY_TARGET_MISSED)
        self.assertAlmostEqual(result["achieved_availability"], 0.9, places=9)

    def test_an_availability_landing_on_its_target_is_not_a_miss(self):
        result = assess_facility_dependability(
            _case(
                record=_record(
                    operating_hours=950.0,
                    repair_hours=20.0,
                    waiting_hours=30.0,
                    failure_count=4,
                    repair_count=4,
                )
            )
        )
        self.assertNotEqual(result["verdict"], AVAILABILITY_TARGET_MISSED)
        self.assertAlmostEqual(result["achieved_availability"], 0.95, places=9)

    def test_a_missed_reliability_target_is_reported(self):
        result = assess_facility_dependability(
            _case(record=_record(failure_count=8, repair_count=8))
        )
        self.assertEqual(result["verdict"], RELIABILITY_TARGET_MISSED)
        self.assertAlmostEqual(result["mtbf_hours"], 120.0, places=9)

    def test_a_missed_restore_target_is_reported(self):
        result = assess_facility_dependability(
            _case(
                record=_record(
                    operating_hours=950.0,
                    repair_hours=40.0,
                    waiting_hours=10.0,
                    failure_count=4,
                    repair_count=4,
                )
            )
        )
        self.assertEqual(result["verdict"], RESTORE_TARGET_MISSED)
        self.assertAlmostEqual(result["mttr_hours"], 10.0, places=9)

    def test_a_shortfall_that_is_mostly_waiting_is_put_under_watch(self):
        result = assess_facility_dependability(
            _case(
                record=_record(
                    operating_hours=950.0,
                    repair_hours=20.0,
                    waiting_hours=30.0,
                    failure_count=4,
                    repair_count=4,
                )
            )
        )
        self.assertEqual(result["verdict"], LOGISTIC_GAP_UNDER_WATCH)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_period_with_no_failure_is_advised_not_graded_on_reliability(self):
        result = assess_facility_dependability(
            _case(
                record=_record(
                    operating_hours=1000.0,
                    repair_hours=0.0,
                    waiting_hours=0.0,
                    failure_count=0,
                    repair_count=0,
                )
            )
        )
        self.assertEqual(result["verdict"], TARGETS_MET)
        self.assertIsNone(result["mtbf_hours"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_facility_dependability(["record"])


if __name__ == "__main__":
    unittest.main()
