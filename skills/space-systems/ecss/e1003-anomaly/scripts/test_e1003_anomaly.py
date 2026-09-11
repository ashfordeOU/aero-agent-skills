#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §4.3.4 anomaly handling during testing.

Exercises scripts/e1003_anomaly_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — an anomaly type maps to exactly
one failure-domain category and an unrecognized type raises; severity level
determines an ordered containment-action list and an unrecognized severity
raises; an anomaly record is validated against a required field set and
missing fields are returned as a sorted list; disposition codes are validated
and only 'repair_and_retest' mandates retesting; the retest scope is the
union of directly affected test IDs and any tests overlapping the repair
scope, and is empty for all other dispositions; the full anomaly review
aggregates category, containment, record gaps, disposition validity, retest
requirement, retest scope, and findings into a single result dict.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_anomaly_logic as al  # noqa: E402


def _full_record():
    return {
        "anomaly_id": "AN-001",
        "description": "Vibration level exceeded limit at 120 Hz",
        "detected_at": "2026-09-11T08:32:00Z",
        "affected_item": "STR-PANEL-A",
        "test_procedure_ref": "TP-MECH-005",
        "detected_by": "J. Smith",
        "initial_findings": "Accelerometer reading 4.2 g vs 3.0 g limit",
    }


class CategorizeAnomalyTest(unittest.TestCase):
    def test_hardware_failure_returns_correct_category(self):
        self.assertEqual(al.categorize_anomaly("hardware_failure"), "hardware_failure")

    def test_software_failure_returns_correct_category(self):
        self.assertEqual(al.categorize_anomaly("software_failure"), "software_failure")

    def test_environmental_exceedance_returns_correct_category(self):
        self.assertEqual(
            al.categorize_anomaly("environmental_exceedance"),
            "environmental_exceedance",
        )

    def test_electrical_anomaly_returns_correct_category(self):
        self.assertEqual(
            al.categorize_anomaly("electrical_anomaly"), "electrical_anomaly"
        )

    def test_mechanical_anomaly_returns_correct_category(self):
        self.assertEqual(
            al.categorize_anomaly("mechanical_anomaly"), "mechanical_anomaly"
        )

    def test_unrecognized_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            al.categorize_anomaly("cosmic_ray_upset")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            al.categorize_anomaly("")


class ContainmentActionsTest(unittest.TestCase):
    def test_critical_includes_halt_test(self):
        actions = al.containment_actions("critical")
        self.assertIn("halt_test_immediately", actions)

    def test_critical_includes_isolate_unit(self):
        actions = al.containment_actions("critical")
        self.assertIn("isolate_affected_unit", actions)

    def test_critical_includes_notify_engineer(self):
        actions = al.containment_actions("critical")
        self.assertIn("notify_responsible_engineer", actions)

    def test_major_includes_suspend_activity(self):
        actions = al.containment_actions("major")
        self.assertIn("suspend_test_activity", actions)

    def test_major_includes_risk_assessment(self):
        actions = al.containment_actions("major")
        self.assertIn("assess_risk_to_hardware", actions)

    def test_minor_includes_enhanced_monitoring(self):
        actions = al.containment_actions("minor")
        self.assertIn("continue_with_enhanced_monitoring", actions)

    def test_minor_does_not_halt_test(self):
        self.assertNotIn("halt_test_immediately", al.containment_actions("minor"))

    def test_unrecognized_severity_raises_value_error(self):
        with self.assertRaises(ValueError):
            al.containment_actions("catastrophic")

    def test_returns_new_list_each_call(self):
        a = al.containment_actions("critical")
        b = al.containment_actions("critical")
        self.assertIsNot(a, b)


class ValidateRecordTest(unittest.TestCase):
    def test_complete_record_returns_empty_list(self):
        self.assertEqual(al.validate_record(_full_record()), [])

    def test_missing_description_flagged(self):
        rec = {k: v for k, v in _full_record().items() if k != "description"}
        gaps = al.validate_record(rec)
        self.assertIn("description", gaps)

    def test_missing_anomaly_id_flagged(self):
        rec = {k: v for k, v in _full_record().items() if k != "anomaly_id"}
        self.assertIn("anomaly_id", al.validate_record(rec))

    def test_multiple_missing_fields_all_returned(self):
        gaps = al.validate_record({})
        self.assertEqual(len(gaps), len(al.REQUIRED_RECORD_FIELDS))

    def test_gaps_returned_in_sorted_order(self):
        gaps = al.validate_record({})
        self.assertEqual(gaps, sorted(gaps))

    def test_extra_fields_do_not_cause_gaps(self):
        rec = dict(_full_record())
        rec["extra_field"] = "extra value"
        self.assertEqual(al.validate_record(rec), [])

    def test_validate_record_does_not_mutate_input(self):
        rec = _full_record()
        original_keys = set(rec.keys())
        al.validate_record(rec)
        self.assertEqual(set(rec.keys()), original_keys)


class DispositionTest(unittest.TestCase):
    def test_repair_and_retest_requires_retest(self):
        self.assertTrue(al.disposition_requires_retest("repair_and_retest"))

    def test_accept_as_is_does_not_require_retest(self):
        self.assertFalse(al.disposition_requires_retest("accept_as_is"))

    def test_reject_does_not_require_retest(self):
        self.assertFalse(al.disposition_requires_retest("reject"))

    def test_waiver_required_does_not_require_retest(self):
        self.assertFalse(al.disposition_requires_retest("waiver_required"))

    def test_pending_analysis_does_not_require_retest(self):
        self.assertFalse(al.disposition_requires_retest("pending_analysis"))

    def test_unknown_disposition_raises_value_error(self):
        with self.assertRaises(ValueError):
            al.validate_disposition("scrapped")

    def test_unknown_disposition_in_requires_retest_raises(self):
        with self.assertRaises(ValueError):
            al.disposition_requires_retest("unknown_code")


class RetestScopeTest(unittest.TestCase):
    def test_repair_and_retest_returns_affected_tests(self):
        scope = al.retest_scope("repair_and_retest", ["T01", "T02"])
        self.assertEqual(scope, {"T01", "T02"})

    def test_repair_and_retest_unions_with_repair_touches(self):
        scope = al.retest_scope("repair_and_retest", ["T01"], ["T03", "T04"])
        self.assertEqual(scope, {"T01", "T03", "T04"})

    def test_accept_as_is_returns_empty_set(self):
        self.assertEqual(al.retest_scope("accept_as_is", ["T01", "T02"]), set())

    def test_reject_returns_empty_set(self):
        self.assertEqual(al.retest_scope("reject", ["T01"]), set())

    def test_waiver_required_returns_empty_set(self):
        self.assertEqual(al.retest_scope("waiver_required", ["T01"]), set())

    def test_no_repair_touches_does_not_raise(self):
        scope = al.retest_scope("repair_and_retest", ["T01"], None)
        self.assertEqual(scope, {"T01"})

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            al.retest_scope("bad_code", ["T01"])

    def test_does_not_mutate_affected_test_ids(self):
        ids = ["T01", "T02"]
        al.retest_scope("repair_and_retest", ids, ["T03"])
        self.assertEqual(ids, ["T01", "T02"])


class AnomalyReviewTest(unittest.TestCase):
    def _base_anomaly(self):
        return {
            "anomaly_type": "mechanical_anomaly",
            "severity": "major",
            "record": _full_record(),
            "disposition": "repair_and_retest",
            "affected_test_ids": ["T10", "T11"],
            "repair_touches_test_ids": ["T12"],
        }

    def test_fully_resolved_review_has_no_findings(self):
        review = al.anomaly_review(self._base_anomaly())
        self.assertEqual(review["findings"], [])
        self.assertTrue(review["disposition_valid"])
        self.assertTrue(review["retest_required"])
        self.assertEqual(review["retest_scope"], {"T10", "T11", "T12"})

    def test_review_returns_correct_category(self):
        review = al.anomaly_review(self._base_anomaly())
        self.assertEqual(review["category"], "mechanical_anomaly")

    def test_review_returns_containment_for_severity(self):
        review = al.anomaly_review(self._base_anomaly())
        self.assertIn("suspend_test_activity", review["containment"])

    def test_missing_record_fields_flagged_in_findings(self):
        anomaly = self._base_anomaly()
        anomaly["record"] = {}
        review = al.anomaly_review(anomaly)
        self.assertTrue(
            any("missing_record_fields" in f for f in review["findings"])
        )

    def test_missing_disposition_flagged_in_findings(self):
        anomaly = self._base_anomaly()
        anomaly["disposition"] = None
        review = al.anomaly_review(anomaly)
        self.assertIn("missing_disposition", review["findings"])

    def test_pending_analysis_flagged_in_findings(self):
        anomaly = self._base_anomaly()
        anomaly["disposition"] = "pending_analysis"
        review = al.anomaly_review(anomaly)
        self.assertIn("disposition_pending_analysis", review["findings"])

    def test_unrecognized_anomaly_type_raises(self):
        anomaly = self._base_anomaly()
        anomaly["anomaly_type"] = "unicorn_event"
        with self.assertRaises(ValueError):
            al.anomaly_review(anomaly)

    def test_unrecognized_severity_raises(self):
        anomaly = self._base_anomaly()
        anomaly["severity"] = "negligible"
        with self.assertRaises(ValueError):
            al.anomaly_review(anomaly)

    def test_accept_as_is_has_no_retest_scope(self):
        anomaly = self._base_anomaly()
        anomaly["disposition"] = "accept_as_is"
        review = al.anomaly_review(anomaly)
        self.assertFalse(review["retest_required"])
        self.assertEqual(review["retest_scope"], set())

    def test_critical_severity_review_halts_test(self):
        anomaly = self._base_anomaly()
        anomaly["severity"] = "critical"
        anomaly["disposition"] = "reject"
        review = al.anomaly_review(anomaly)
        self.assertIn("halt_test_immediately", review["containment"])
        self.assertFalse(review["retest_required"])

    def test_review_does_not_mutate_input(self):
        anomaly = self._base_anomaly()
        original_type = anomaly["anomaly_type"]
        al.anomaly_review(anomaly)
        self.assertEqual(anomaly["anomaly_type"], original_type)


if __name__ == "__main__":
    unittest.main()
