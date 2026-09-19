"""Contract test for the operator check and logbook leaf (stdlib unittest)."""

import datetime
import unittest

from q7026_tool_operator_checks_logic import (
    BOUNDED_BY_LAST_PASS,
    BOUNDED_OPEN,
    GAUGE_INVALID,
    GAUGE_OVERSIZE,
    GAUGE_PASS,
    GAUGE_UNDERSIZE,
    HELD,
    RELEASED,
    REQUIRED_LOG_FIELDS,
    assess_shift,
    gauge_verdict,
    logbook_gaps,
    parse_check_datetime,
    quarantine_span,
    release_decision,
    validate_check,
    validate_log,
)


def check(**kw):
    c = {
        "tool_id": "CT-0114",
        "operator_id": "OP-31",
        "check_datetime": "2026-09-14T06:05:00",
        "gauge_set_id": "GS-07",
        "crimp_count_at_check": 1200,
        "go_pin_enters": True,
        "no_go_pin_enters": False,
        "tool_on_hold": False,
    }
    c.update(kw)
    return c


class TestGauge(unittest.TestCase):
    def test_go_in_and_no_go_out_is_a_pass(self):
        self.assertEqual(gauge_verdict(True, False), GAUGE_PASS)

    def test_a_go_pin_refused_means_the_die_closes_undersize(self):
        self.assertEqual(gauge_verdict(False, False), GAUGE_UNDERSIZE)

    def test_a_no_go_pin_accepted_means_the_die_is_worn_open(self):
        self.assertEqual(gauge_verdict(True, True), GAUGE_OVERSIZE)

    def test_both_pins_wrong_is_an_untrustworthy_gauge_set(self):
        self.assertEqual(gauge_verdict(False, True), GAUGE_INVALID)

    def test_a_non_boolean_pin_reading_raises(self):
        with self.assertRaises(ValueError):
            gauge_verdict("in", False)


class TestLogbook(unittest.TestCase):
    def test_a_complete_entry_has_no_gaps(self):
        self.assertEqual(logbook_gaps(check()), [])

    def test_every_required_field_is_checked(self):
        for field in REQUIRED_LOG_FIELDS:
            entry = check()
            entry[field] = None
            self.assertIn("missing-%s" % field, logbook_gaps(entry))

    def test_a_blank_operator_is_unusable_not_missing(self):
        self.assertIn("unusable-operator_id", logbook_gaps(check(operator_id="   ")))

    def test_a_malformed_timestamp_is_unusable(self):
        self.assertIn(
            "unusable-check_datetime", logbook_gaps(check(check_datetime="14/09/2026"))
        )

    def test_a_negative_counter_reading_is_unusable(self):
        self.assertIn(
            "unusable-crimp_count_at_check",
            logbook_gaps(check(crimp_count_at_check=-5)),
        )

    def test_a_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            logbook_gaps("CT-0114")

    def test_an_incomplete_entry_cannot_be_validated(self):
        with self.assertRaises(ValueError):
            validate_check(check(gauge_set_id=None))

    def test_a_timestamp_object_passes_through(self):
        stamp = datetime.datetime(2026, 9, 14, 6, 5)
        self.assertEqual(parse_check_datetime(stamp), stamp)


class TestRelease(unittest.TestCase):
    def test_a_passing_recorded_check_releases_the_tool(self):
        result = release_decision(check())
        self.assertEqual(result["decision"], RELEASED)
        self.assertEqual(result["verdict"], GAUGE_PASS)

    def test_a_failing_gauge_holds_the_tool(self):
        result = release_decision(check(no_go_pin_enters=True))
        self.assertEqual(result["decision"], HELD)
        self.assertIn(GAUGE_OVERSIZE, result["reasons"])

    def test_a_passing_gauge_with_an_incomplete_entry_releases_nothing(self):
        result = release_decision(check(operator_id=None))
        self.assertEqual(result["decision"], HELD)
        self.assertIn("missing-operator_id", result["reasons"])
        self.assertIsNone(result["verdict"])

    def test_a_tool_already_on_hold_stays_held(self):
        result = release_decision(check(tool_on_hold=True))
        self.assertEqual(result["decision"], HELD)
        self.assertIn("tool-already-on-hold", result["reasons"])


class TestLogValidation(unittest.TestCase):
    def test_a_well_ordered_log_validates(self):
        log = [check(), check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=1380)]
        self.assertEqual(len(validate_log(log)), 2)

    def test_two_tools_in_one_run_raises(self):
        log = [check(), check(tool_id="CT-0115")]
        with self.assertRaises(ValueError):
            validate_log(log)

    def test_entries_out_of_time_order_raise(self):
        log = [check(), check(check_datetime="2026-09-14T05:00:00")]
        with self.assertRaises(ValueError):
            validate_log(log)

    def test_a_counter_going_backwards_raises(self):
        log = [
            check(),
            check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=900),
        ]
        with self.assertRaises(ValueError):
            validate_log(log)

    def test_an_empty_log_raises(self):
        with self.assertRaises(ValueError):
            validate_log([])

    def test_a_non_list_log_raises(self):
        with self.assertRaises(ValueError):
            validate_log(check())


class TestQuarantine(unittest.TestCase):
    def setUp(self):
        self.log = [
            check(crimp_count_at_check=1200),
            check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=1380),
            check(
                check_datetime="2026-09-14T14:05:00",
                crimp_count_at_check=1520,
                no_go_pin_enters=True,
            ),
        ]

    def test_the_span_runs_back_to_the_last_passing_check(self):
        span = quarantine_span(self.log, 2)
        self.assertEqual(span["from_count"], 1380)
        self.assertEqual(span["to_count"], 1520)
        self.assertEqual(span["crimps_affected"], 140)
        self.assertEqual(span["bounded_by"], BOUNDED_BY_LAST_PASS)

    def test_the_span_does_not_run_back_to_the_shift_start(self):
        self.assertNotEqual(quarantine_span(self.log, 2)["from_count"], 1200)

    def test_a_first_entry_failure_leaves_the_span_open(self):
        log = [check(no_go_pin_enters=True)]
        span = quarantine_span(log, 0)
        self.assertEqual(span["bounded_by"], BOUNDED_OPEN)
        self.assertEqual(span["crimps_affected"], 0)

    def test_quarantining_a_passing_check_raises(self):
        with self.assertRaises(ValueError):
            quarantine_span(self.log, 1)

    def test_an_index_past_the_log_raises(self):
        with self.assertRaises(ValueError):
            quarantine_span(self.log, 9)

    def test_a_negative_index_raises(self):
        with self.assertRaises(ValueError):
            quarantine_span(self.log, -1)


class TestShift(unittest.TestCase):
    def test_a_clean_shift_quarantines_nothing(self):
        log = [
            check(),
            check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=1380),
        ]
        report = assess_shift(log)
        self.assertTrue(report["clean"])
        self.assertEqual(report["released_count"], 2)
        self.assertEqual(report["held_count"], 0)

    def test_a_failed_check_holds_the_tool_and_opens_a_quarantine(self):
        log = [
            check(),
            check(
                check_datetime="2026-09-14T14:05:00",
                crimp_count_at_check=1520,
                no_go_pin_enters=True,
            ),
        ]
        report = assess_shift(log)
        self.assertFalse(report["clean"])
        self.assertEqual(report["held_count"], 1)
        self.assertEqual(report["crimps_affected"], 320)

    def test_the_quarantine_fraction_is_affected_over_produced(self):
        log = [
            check(crimp_count_at_check=1000),
            check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=1500),
            check(
                check_datetime="2026-09-14T14:05:00",
                crimp_count_at_check=2000,
                no_go_pin_enters=True,
            ),
        ]
        report = assess_shift(log)
        self.assertAlmostEqual(report["quarantine_fraction"], 0.5, places=9)

    def test_a_shift_with_no_production_reports_a_zero_fraction(self):
        log = [
            check(),
            check(check_datetime="2026-09-14T10:05:00", crimp_count_at_check=1200),
        ]
        self.assertAlmostEqual(assess_shift(log)["quarantine_fraction"], 0.0, places=9)

    def test_the_roll_up_names_the_tool(self):
        self.assertEqual(assess_shift([check()])["tool_id"], "CT-0114")

    def test_each_quarantine_carries_the_index_that_raised_it(self):
        log = [
            check(),
            check(
                check_datetime="2026-09-14T14:05:00",
                crimp_count_at_check=1520,
                no_go_pin_enters=True,
            ),
        ]
        self.assertEqual(assess_shift(log)["quarantines"][0]["at_index"], 1)


if __name__ == "__main__":
    unittest.main()
