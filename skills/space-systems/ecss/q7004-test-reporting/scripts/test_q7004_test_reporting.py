#!/usr/bin/env python3
"""Contract test for the thermal test report grading (offline)."""

import copy
import unittest

from q7004_test_reporting_logic import (
    ANOMALIES,
    BLOCKED,
    CLOSED_NO_IMPACT,
    CLOSED_RETESTED,
    CONDITIONS,
    DEFAULT_REPORT_FORMAT,
    DEVIATIONS,
    IDENTIFICATION,
    INCOMPLETE,
    OPEN,
    RELEASABLE,
    RESULTS,
    document_test_report,
    is_supplied,
    missing_fields,
    section_completeness,
    validate_anomaly,
    validate_conditions,
    validate_report_format,
)

BASE_REPORT = {
    IDENTIFICATION: {
        "report_id": "TR-70-04-118",
        "item_id": "BRACKET-01",
        "test_facility": "chamber-2",
        "test_date": "2026-05-04",
    },
    CONDITIONS: {
        "temperature_min_k": 213.15,
        "temperature_max_k": 373.15,
        "cycle_count": 100,
        "dwell_s": 3600.0,
        "pressure_pa": 0.001,
    },
    RESULTS: {
        "verdict": "pass",
        "inspection_outcome": "no cracking observed",
        "functional_outcome": "within specification",
        "mass_change_pct": 0.0,
    },
    ANOMALIES: [],
    DEVIATIONS: {"deviation_summary": "none"},
}

CLOSED_ANOMALY = {
    "anomaly_id": "AN-01",
    "description": "chamber overshoot on the hot transition",
    "occurred_at_cycle": 12,
    "disposition": CLOSED_NO_IMPACT,
}


def _report(base, **overrides):
    report = copy.deepcopy(base)
    report.update(overrides)
    return report


def _without(base, section, field):
    report = copy.deepcopy(base)
    del report[section][field]
    return report


class FormatTests(unittest.TestCase):
    def test_default_format_validates(self):
        self.assertIs(
            validate_report_format(DEFAULT_REPORT_FORMAT), DEFAULT_REPORT_FORMAT
        )

    def test_a_format_missing_a_graded_section_rejected(self):
        broken = copy.deepcopy(DEFAULT_REPORT_FORMAT)
        del broken["required_fields"][CONDITIONS]
        with self.assertRaises(ValueError):
            validate_report_format(broken)

    def test_a_format_without_a_disposition_field_rejected(self):
        broken = copy.deepcopy(DEFAULT_REPORT_FORMAT)
        broken["anomaly_fields"] = ("anomaly_id", "description")
        with self.assertRaises(ValueError):
            validate_report_format(broken)

    def test_a_section_requiring_nothing_rejected(self):
        broken = copy.deepcopy(DEFAULT_REPORT_FORMAT)
        broken["required_fields"][DEVIATIONS] = ()
        with self.assertRaises(ValueError):
            validate_report_format(broken)

    def test_non_mapping_format_rejected(self):
        with self.assertRaises(ValueError):
            validate_report_format("the usual template")


class SuppliedTests(unittest.TestCase):
    def test_a_measured_zero_is_supplied(self):
        self.assertTrue(is_supplied(0.0))

    def test_a_blank_string_is_not_supplied(self):
        self.assertFalse(is_supplied("   "))

    def test_an_absent_value_is_not_supplied(self):
        self.assertFalse(is_supplied(None))

    def test_an_empty_list_is_not_supplied(self):
        self.assertFalse(is_supplied([]))

    def test_a_missing_field_is_named_by_its_section(self):
        gaps = missing_fields(CONDITIONS, {"temperature_min_k": 213.15})
        self.assertIn("cycle_count", gaps)
        self.assertNotIn("temperature_min_k", gaps)

    def test_a_complete_section_scores_one(self):
        self.assertAlmostEqual(
            section_completeness(RESULTS, BASE_REPORT[RESULTS]), 1.0, places=9
        )

    def test_half_a_section_scores_a_half(self):
        content = {"report_id": "TR-1", "item_id": "BRACKET-01"}
        self.assertAlmostEqual(
            section_completeness(IDENTIFICATION, content), 0.5, places=9
        )

    def test_the_anomaly_section_is_not_graded_by_field(self):
        with self.assertRaises(ValueError):
            missing_fields(ANOMALIES, {})


class ConditionsTests(unittest.TestCase):
    def test_recorded_conditions_carry_their_span(self):
        conditions = validate_conditions(BASE_REPORT[CONDITIONS])
        self.assertAlmostEqual(conditions["span_k"], 160.0, places=9)
        self.assertEqual(conditions["cycle_count"], 100)

    def test_inverted_recorded_temperatures_rejected(self):
        broken = dict(BASE_REPORT[CONDITIONS], temperature_max_k=200.0)
        with self.assertRaises(ValueError):
            validate_conditions(broken)

    def test_a_non_absolute_recorded_temperature_rejected(self):
        broken = dict(BASE_REPORT[CONDITIONS], temperature_min_k=-60.0)
        with self.assertRaises(ValueError):
            validate_conditions(broken)

    def test_a_zero_cycle_count_rejected(self):
        broken = dict(BASE_REPORT[CONDITIONS], cycle_count=0)
        with self.assertRaises(ValueError):
            validate_conditions(broken)

    def test_a_zero_dwell_rejected(self):
        broken = dict(BASE_REPORT[CONDITIONS], dwell_s=0.0)
        with self.assertRaises(ValueError):
            validate_conditions(broken)


class AnomalyTests(unittest.TestCase):
    def test_a_complete_closed_anomaly_is_accepted(self):
        anomaly = validate_anomaly(CLOSED_ANOMALY, 100)
        self.assertFalse(anomaly["is_open"])
        self.assertTrue(anomaly["within_test"])

    def test_an_open_anomaly_is_marked_open(self):
        record = dict(CLOSED_ANOMALY, disposition=OPEN)
        self.assertTrue(validate_anomaly(record, 100)["is_open"])

    def test_an_anomaly_beyond_the_cycle_count_is_inconsistent(self):
        record = dict(CLOSED_ANOMALY, occurred_at_cycle=140)
        self.assertFalse(validate_anomaly(record, 100)["within_test"])

    def test_an_anomaly_on_the_last_cycle_is_consistent(self):
        record = dict(CLOSED_ANOMALY, occurred_at_cycle=100)
        self.assertTrue(validate_anomaly(record, 100)["within_test"])

    def test_an_anomaly_without_a_description_rejected(self):
        record = dict(CLOSED_ANOMALY, description="  ")
        with self.assertRaises(ValueError):
            validate_anomaly(record, 100)

    def test_an_unknown_disposition_rejected(self):
        record = dict(CLOSED_ANOMALY, disposition="noted")
        with self.assertRaises(ValueError):
            validate_anomaly(record, 100)

    def test_a_negative_anomaly_cycle_rejected(self):
        record = dict(CLOSED_ANOMALY, occurred_at_cycle=-1)
        with self.assertRaises(ValueError):
            validate_anomaly(record, 100)


class ReportTests(unittest.TestCase):
    def test_a_complete_clean_report_is_releasable(self):
        graded = document_test_report(BASE_REPORT)
        self.assertEqual(graded["verdict"], RELEASABLE)
        self.assertAlmostEqual(graded["completeness"], 1.0, places=9)
        self.assertEqual(graded["missing_fields"], [])

    def test_a_missing_field_makes_the_report_incomplete(self):
        graded = document_test_report(_without(BASE_REPORT, RESULTS, "mass_change_pct"))
        self.assertEqual(graded["verdict"], INCOMPLETE)
        self.assertIn("results.mass_change_pct", graded["missing_fields"])

    def test_a_blank_field_counts_as_missing(self):
        report = copy.deepcopy(BASE_REPORT)
        report[DEVIATIONS]["deviation_summary"] = "   "
        graded = document_test_report(report)
        self.assertEqual(graded["verdict"], INCOMPLETE)

    def test_a_measured_zero_does_not_count_as_missing(self):
        report = copy.deepcopy(BASE_REPORT)
        report[RESULTS]["mass_change_pct"] = 0.0
        graded = document_test_report(report)
        self.assertNotIn("results.mass_change_pct", graded["missing_fields"])

    def test_an_open_anomaly_blocks_release(self):
        report = _report(
            BASE_REPORT, **{ANOMALIES: [dict(CLOSED_ANOMALY, disposition=OPEN)]}
        )
        graded = document_test_report(report)
        self.assertEqual(graded["verdict"], BLOCKED)
        self.assertEqual(graded["open_anomaly_count"], 1)

    def test_a_pass_over_an_open_anomaly_is_called_out(self):
        report = _report(
            BASE_REPORT, **{ANOMALIES: [dict(CLOSED_ANOMALY, disposition=OPEN)]}
        )
        graded = document_test_report(report)
        self.assertTrue(graded["claims_pass"])
        self.assertTrue(any("read as clearance" in f for f in graded["findings"]))

    def test_a_closed_anomaly_does_not_block_release(self):
        report = _report(BASE_REPORT, **{ANOMALIES: [CLOSED_ANOMALY]})
        graded = document_test_report(report)
        self.assertEqual(graded["verdict"], RELEASABLE)
        self.assertEqual(graded["anomaly_count"], 1)

    def test_an_anomaly_outside_the_test_blocks_release(self):
        report = _report(
            BASE_REPORT,
            **{ANOMALIES: [dict(CLOSED_ANOMALY, occurred_at_cycle=140)]}
        )
        graded = document_test_report(report)
        self.assertEqual(graded["verdict"], BLOCKED)
        self.assertEqual(graded["inconsistent_anomaly_count"], 1)
        self.assertTrue(any("one of the two numbers" in f for f in graded["findings"]))

    def test_a_retested_anomaly_closes_the_report(self):
        report = _report(
            BASE_REPORT,
            **{ANOMALIES: [dict(CLOSED_ANOMALY, disposition=CLOSED_RETESTED)]}
        )
        self.assertEqual(document_test_report(report)["verdict"], RELEASABLE)

    def test_an_incomplete_conditions_section_is_called_out(self):
        graded = document_test_report(_without(BASE_REPORT, CONDITIONS, "cycle_count"))
        self.assertIsNone(graded["conditions"])
        self.assertTrue(any("actually run" in f for f in graded["findings"]))

    def test_completeness_falls_as_fields_go_missing(self):
        full = document_test_report(BASE_REPORT)["completeness"]
        thin = document_test_report(
            _without(BASE_REPORT, IDENTIFICATION, "test_facility")
        )["completeness"]
        self.assertLess(thin, full)

    def test_a_duplicated_anomaly_id_rejected(self):
        report = _report(
            BASE_REPORT,
            **{ANOMALIES: [CLOSED_ANOMALY, copy.deepcopy(CLOSED_ANOMALY)]}
        )
        with self.assertRaises(ValueError):
            document_test_report(report)

    def test_every_report_carries_the_blank_versus_zero_duty(self):
        graded = document_test_report(BASE_REPORT)
        self.assertTrue(any("measured zero" in d for d in graded["duties"]))

    def test_an_open_anomaly_adds_the_verdict_statement_duty(self):
        report = _report(
            BASE_REPORT, **{ANOMALIES: [dict(CLOSED_ANOMALY, disposition=OPEN)]}
        )
        graded = document_test_report(report)
        self.assertTrue(any("verdict statement" in d for d in graded["duties"]))

    def test_a_non_list_anomaly_section_rejected(self):
        with self.assertRaises(ValueError):
            document_test_report(_report(BASE_REPORT, **{ANOMALIES: "none seen"}))

    def test_a_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            document_test_report("the bracket passed")


if __name__ == "__main__":
    unittest.main()
