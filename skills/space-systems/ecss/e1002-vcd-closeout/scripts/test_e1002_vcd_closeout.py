#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.4.4.1 VCD closeout.

Exercises scripts/e1002_vcd_closeout_logic.py (stdlib unittest,
offline). Contract: a row with an approved waiver reference is waived
regardless of its records; a row with no records is not compliant; a row
with any open record is not compliant and surfaces open_records_blocking_closeout;
a row with any failed record (no waiver) is not compliant and surfaces
failed_records_without_waiver; a row whose records are all passed or
not_applicable is compliant; an unrecognized outcome raises ValueError;
vcd_closeout aggregates across rows; compliance_summary counts by status
and sets all_closed correctly; blocking_findings flattens per-row findings.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_vcd_closeout_logic as vc  # noqa: E402


class DetermineRowStatusCompliantTest(unittest.TestCase):
    def test_all_passed_is_compliant(self):
        records = [
            {"record_id": "TR-001", "outcome": "passed"},
            {"record_id": "TR-002", "outcome": "passed"},
        ]
        result = vc.determine_row_status("REQ-1", records)
        self.assertEqual(result["status"], vc.COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_passed_and_not_applicable_is_compliant(self):
        records = [
            {"record_id": "TR-001", "outcome": "passed"},
            {"record_id": "AR-001", "outcome": "not_applicable"},
        ]
        result = vc.determine_row_status("REQ-2", records)
        self.assertEqual(result["status"], vc.COMPLIANT)

    def test_all_not_applicable_is_compliant(self):
        records = [{"record_id": "AR-001", "outcome": "not_applicable"}]
        result = vc.determine_row_status("REQ-3", records)
        self.assertEqual(result["status"], vc.COMPLIANT)
        self.assertEqual(result["findings"], [])


class DetermineRowStatusNotCompliantTest(unittest.TestCase):
    def test_no_records_is_not_compliant(self):
        result = vc.determine_row_status("REQ-4", [])
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["issue"], "no_verification_records")
        self.assertEqual(result["findings"][0]["req_id"], "REQ-4")

    def test_open_record_is_not_compliant(self):
        records = [{"record_id": "TR-010", "outcome": "open"}]
        result = vc.determine_row_status("REQ-5", records)
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("open_records_blocking_closeout", issues)

    def test_open_finding_names_the_record(self):
        records = [{"record_id": "TR-010", "outcome": "open"}]
        result = vc.determine_row_status("REQ-5", records)
        finding = next(
            f for f in result["findings"]
            if f["issue"] == "open_records_blocking_closeout"
        )
        self.assertIn("TR-010", finding["record_ids"])

    def test_failed_record_is_not_compliant(self):
        records = [{"record_id": "TR-020", "outcome": "failed"}]
        result = vc.determine_row_status("REQ-6", records)
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("failed_records_without_waiver", issues)

    def test_failed_finding_names_the_record(self):
        records = [{"record_id": "TR-020", "outcome": "failed"}]
        result = vc.determine_row_status("REQ-6", records)
        finding = next(
            f for f in result["findings"]
            if f["issue"] == "failed_records_without_waiver"
        )
        self.assertIn("TR-020", finding["record_ids"])

    def test_open_and_failed_produce_separate_findings(self):
        records = [
            {"record_id": "TR-030", "outcome": "open"},
            {"record_id": "TR-031", "outcome": "failed"},
        ]
        result = vc.determine_row_status("REQ-7", records)
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)
        issues = {f["issue"] for f in result["findings"]}
        self.assertIn("open_records_blocking_closeout", issues)
        self.assertIn("failed_records_without_waiver", issues)


class DetermineRowStatusWaivedTest(unittest.TestCase):
    def test_waiver_ref_gives_waived_status(self):
        records = [{"record_id": "TR-040", "outcome": "passed"}]
        result = vc.determine_row_status("REQ-8", records, waiver_ref="WVR-001")
        self.assertEqual(result["status"], vc.WAIVED)
        self.assertEqual(result["findings"], [])

    def test_waiver_overrides_failed_records(self):
        records = [{"record_id": "TR-041", "outcome": "failed"}]
        result = vc.determine_row_status("REQ-9", records, waiver_ref="WVR-002")
        self.assertEqual(result["status"], vc.WAIVED)
        self.assertEqual(result["findings"], [])

    def test_waiver_overrides_open_records(self):
        records = [{"record_id": "TR-042", "outcome": "open"}]
        result = vc.determine_row_status("REQ-10", records, waiver_ref="WVR-003")
        self.assertEqual(result["status"], vc.WAIVED)

    def test_empty_string_waiver_ref_not_waived(self):
        records = [{"record_id": "TR-043", "outcome": "open"}]
        result = vc.determine_row_status("REQ-11", records, waiver_ref="")
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)

    def test_none_waiver_ref_not_waived(self):
        records = [{"record_id": "TR-044", "outcome": "open"}]
        result = vc.determine_row_status("REQ-12", records, waiver_ref=None)
        self.assertEqual(result["status"], vc.NOT_COMPLIANT)


class DetermineRowStatusErrorTest(unittest.TestCase):
    def test_unrecognized_outcome_raises(self):
        records = [{"record_id": "TR-099", "outcome": "pending_review"}]
        with self.assertRaises(ValueError):
            vc.determine_row_status("REQ-ERR", records)

    def test_error_raised_before_waiver_check(self):
        records = [{"record_id": "TR-100", "outcome": "UNKNOWN"}]
        with self.assertRaises(ValueError):
            vc.determine_row_status("REQ-ERR2", records, waiver_ref="WVR-999")


class VcdCloseoutTest(unittest.TestCase):
    def _make_rows(self):
        return [
            {
                "req_id": "REQ-A",
                "records": [{"record_id": "TR-1", "outcome": "passed"}],
            },
            {
                "req_id": "REQ-B",
                "records": [{"record_id": "TR-2", "outcome": "open"}],
            },
            {
                "req_id": "REQ-C",
                "records": [{"record_id": "TR-3", "outcome": "failed"}],
                "waiver_ref": "WVR-C",
            },
        ]

    def test_returns_one_result_per_row(self):
        rows = self._make_rows()
        results = vc.vcd_closeout(rows)
        self.assertEqual(len(results), 3)

    def test_compliant_row_in_aggregate(self):
        results = vc.vcd_closeout(self._make_rows())
        req_a = next(r for r in results if r["req_id"] == "REQ-A")
        self.assertEqual(req_a["status"], vc.COMPLIANT)

    def test_not_compliant_row_in_aggregate(self):
        results = vc.vcd_closeout(self._make_rows())
        req_b = next(r for r in results if r["req_id"] == "REQ-B")
        self.assertEqual(req_b["status"], vc.NOT_COMPLIANT)

    def test_waived_row_in_aggregate(self):
        results = vc.vcd_closeout(self._make_rows())
        req_c = next(r for r in results if r["req_id"] == "REQ-C")
        self.assertEqual(req_c["status"], vc.WAIVED)

    def test_empty_vcd_returns_empty_list(self):
        self.assertEqual(vc.vcd_closeout([]), [])


class ComplianceSummaryTest(unittest.TestCase):
    def _results(self):
        return vc.vcd_closeout(
            [
                {
                    "req_id": "REQ-1",
                    "records": [{"record_id": "TR-1", "outcome": "passed"}],
                },
                {
                    "req_id": "REQ-2",
                    "records": [{"record_id": "TR-2", "outcome": "open"}],
                },
                {
                    "req_id": "REQ-3",
                    "records": [],
                    "waiver_ref": "WVR-3",
                },
            ]
        )

    def test_counts_are_correct(self):
        summary = vc.compliance_summary(self._results())
        self.assertEqual(summary["compliant"], 1)
        self.assertEqual(summary["not_compliant"], 1)
        self.assertEqual(summary["waived"], 1)
        self.assertEqual(summary["total"], 3)

    def test_all_closed_false_when_not_compliant_present(self):
        summary = vc.compliance_summary(self._results())
        self.assertFalse(summary["all_closed"])

    def test_all_closed_true_when_no_not_compliant(self):
        rows = [
            {
                "req_id": "REQ-X",
                "records": [{"record_id": "TR-X", "outcome": "passed"}],
            },
            {
                "req_id": "REQ-Y",
                "records": [],
                "waiver_ref": "WVR-Y",
            },
        ]
        summary = vc.compliance_summary(vc.vcd_closeout(rows))
        self.assertTrue(summary["all_closed"])
        self.assertEqual(summary["not_compliant"], 0)

    def test_empty_results_all_closed(self):
        summary = vc.compliance_summary([])
        self.assertTrue(summary["all_closed"])
        self.assertEqual(summary["total"], 0)


class BlockingFindingsTest(unittest.TestCase):
    def test_no_findings_returns_empty(self):
        rows = [
            {
                "req_id": "REQ-P",
                "records": [{"record_id": "TR-P", "outcome": "passed"}],
            }
        ]
        self.assertEqual(vc.blocking_findings(vc.vcd_closeout(rows)), [])

    def test_flattens_all_findings(self):
        rows = [
            {
                "req_id": "REQ-Q",
                "records": [{"record_id": "TR-Q", "outcome": "open"}],
            },
            {
                "req_id": "REQ-R",
                "records": [],
            },
        ]
        findings = vc.blocking_findings(vc.vcd_closeout(rows))
        self.assertEqual(len(findings), 2)

    def test_finding_issues_are_expected(self):
        rows = [
            {
                "req_id": "REQ-S",
                "records": [{"record_id": "TR-S", "outcome": "failed"}],
            },
        ]
        findings = vc.blocking_findings(vc.vcd_closeout(rows))
        self.assertEqual(findings[0]["issue"], "failed_records_without_waiver")


if __name__ == "__main__":
    unittest.main()
