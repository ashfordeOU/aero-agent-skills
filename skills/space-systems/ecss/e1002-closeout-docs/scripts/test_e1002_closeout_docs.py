#!/usr/bin/env python3
"""Offline deterministic tests for e1002_closeout_docs_logic.

Run: python3 test_e1002_closeout_docs.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1002_closeout_docs_logic import (
    CloseoutError,
    consolidate_verification_reports,
    build_waiver_deviation_entry,
    apply_waivers_deviations,
    check_gate_readiness,
    summarise_register,
    validate_risk_level,
    validate_entry_type,
    validate_verification_status,
    validate_verification_method,
)


class TestConsolidateVerificationReports(unittest.TestCase):

    def test_empty_reports_returns_empty_list(self):
        result = consolidate_verification_reports([])
        self.assertEqual(result, [])

    def test_single_pass_record_sets_disposition_pass(self):
        reports = [
            {"requirement_id": "SYS-001", "method": "Test",
             "status": "Pass", "notes": "Passed in thermal-vac"}
        ]
        result = consolidate_verification_reports(reports)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["disposition"], "Pass")
        self.assertEqual(result[0]["requirement_id"], "SYS-001")

    def test_fail_status_sets_disposition_fail(self):
        reports = [
            {"requirement_id": "SYS-002", "method": "Analysis",
             "status": "Fail", "notes": "Margin exceeded"}
        ]
        result = consolidate_verification_reports(reports)
        self.assertEqual(result[0]["disposition"], "Fail")

    def test_not_verified_status_sets_disposition_deferred(self):
        reports = [
            {"requirement_id": "SYS-003", "method": "Inspection",
             "status": "Not_Verified", "notes": ""}
        ]
        result = consolidate_verification_reports(reports)
        self.assertEqual(result[0]["disposition"], "Deferred")

    def test_mixed_statuses_produce_correct_dispositions(self):
        reports = [
            {"requirement_id": "R-001", "method": "Test", "status": "Pass", "notes": ""},
            {"requirement_id": "R-002", "method": "Analysis", "status": "Fail", "notes": ""},
            {"requirement_id": "R-003", "method": "Review", "status": "Not_Verified", "notes": ""},
        ]
        result = consolidate_verification_reports(reports)
        by_id = {r["requirement_id"]: r["disposition"] for r in result}
        self.assertEqual(by_id["R-001"], "Pass")
        self.assertEqual(by_id["R-002"], "Fail")
        self.assertEqual(by_id["R-003"], "Deferred")

    def test_duplicate_requirement_id_raises_error(self):
        reports = [
            {"requirement_id": "SYS-001", "method": "Test", "status": "Pass", "notes": ""},
            {"requirement_id": "SYS-001", "method": "Test", "status": "Pass", "notes": ""},
        ]
        with self.assertRaises(CloseoutError):
            consolidate_verification_reports(reports)

    def test_missing_requirement_id_raises_error(self):
        reports = [{"method": "Test", "status": "Pass", "notes": ""}]
        with self.assertRaises(CloseoutError):
            consolidate_verification_reports(reports)

    def test_empty_requirement_id_raises_error(self):
        reports = [{"requirement_id": "   ", "method": "Test", "status": "Pass", "notes": ""}]
        with self.assertRaises(CloseoutError):
            consolidate_verification_reports(reports)

    def test_unknown_method_raises_error(self):
        reports = [
            {"requirement_id": "SYS-010", "method": "Simulation",
             "status": "Pass", "notes": ""}
        ]
        with self.assertRaises(CloseoutError):
            consolidate_verification_reports(reports)

    def test_unknown_status_raises_error(self):
        reports = [
            {"requirement_id": "SYS-011", "method": "Test",
             "status": "Pending", "notes": ""}
        ]
        with self.assertRaises(CloseoutError):
            consolidate_verification_reports(reports)

    def test_all_four_valid_methods_accepted(self):
        reports = [
            {"requirement_id": f"R-{m}", "method": m, "status": "Pass", "notes": ""}
            for m in ["Test", "Analysis", "Inspection", "Review"]
        ]
        result = consolidate_verification_reports(reports)
        self.assertEqual(len(result), 4)

    def test_output_records_preserve_notes(self):
        reports = [
            {"requirement_id": "SYS-020", "method": "Test",
             "status": "Pass", "notes": "See test report TR-042"}
        ]
        result = consolidate_verification_reports(reports)
        self.assertEqual(result[0]["notes"], "See test report TR-042")


class TestBuildWaiverDeviationEntry(unittest.TestCase):

    def test_valid_waiver_entry_returned(self):
        entry = build_waiver_deviation_entry(
            "SYS-002", "WAIVER", "Interface constraint prevents full test coverage.", "MEDIUM"
        )
        self.assertEqual(entry["requirement_id"], "SYS-002")
        self.assertEqual(entry["type"], "WAIVER")
        self.assertEqual(entry["risk_level"], "MEDIUM")
        self.assertIn("Interface", entry["justification"])

    def test_valid_deviation_entry_returned(self):
        entry = build_waiver_deviation_entry(
            "SYS-003", "DEVIATION", "Unit A only; rework scheduled for PDR+3.", "LOW"
        )
        self.assertEqual(entry["type"], "DEVIATION")

    def test_all_risk_levels_accepted(self):
        for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            entry = build_waiver_deviation_entry("R-X", "WAIVER", "Justified.", level)
            self.assertEqual(entry["risk_level"], level)

    def test_invalid_entry_type_raises_error(self):
        with self.assertRaises(CloseoutError):
            build_waiver_deviation_entry("R-X", "EXEMPTION", "Justified.", "LOW")

    def test_invalid_risk_level_raises_error(self):
        with self.assertRaises(CloseoutError):
            build_waiver_deviation_entry("R-X", "WAIVER", "Justified.", "NEGLIGIBLE")

    def test_empty_justification_raises_error(self):
        with self.assertRaises(CloseoutError):
            build_waiver_deviation_entry("R-X", "WAIVER", "   ", "LOW")

    def test_empty_requirement_id_raises_error(self):
        with self.assertRaises(CloseoutError):
            build_waiver_deviation_entry("", "WAIVER", "Justified.", "LOW")

    def test_whitespace_stripped_from_requirement_id(self):
        entry = build_waiver_deviation_entry("  SYS-005  ", "DEVIATION", "Note.", "HIGH")
        self.assertEqual(entry["requirement_id"], "SYS-005")


class TestApplyWaiversDeviations(unittest.TestCase):

    def _make_register(self, rows):
        return [
            {"requirement_id": r, "method": "Test", "status": s,
             "notes": "", "disposition": d}
            for r, s, d in rows
        ]

    def test_fail_disposition_updated_to_waived(self):
        reg = self._make_register([("SYS-002", "Fail", "Fail")])
        wd = [build_waiver_deviation_entry("SYS-002", "WAIVER", "Approved.", "LOW")]
        result = apply_waivers_deviations(reg, wd)
        self.assertEqual(result[0]["disposition"], "Waived")

    def test_deferred_disposition_updated_to_waived(self):
        reg = self._make_register([("SYS-003", "Not_Verified", "Deferred")])
        wd = [build_waiver_deviation_entry("SYS-003", "DEVIATION", "Planned.", "MEDIUM")]
        result = apply_waivers_deviations(reg, wd)
        self.assertEqual(result[0]["disposition"], "Waived")

    def test_pass_disposition_not_changed(self):
        reg = self._make_register([("SYS-001", "Pass", "Pass")])
        wd = [build_waiver_deviation_entry("SYS-001", "WAIVER", "Unnecessary.", "LOW")]
        result = apply_waivers_deviations(reg, wd)
        self.assertEqual(result[0]["disposition"], "Pass")

    def test_unknown_requirement_in_wd_raises_error(self):
        reg = self._make_register([("SYS-001", "Pass", "Pass")])
        wd = [build_waiver_deviation_entry("SYS-999", "WAIVER", "Unknown.", "LOW")]
        with self.assertRaises(CloseoutError):
            apply_waivers_deviations(reg, wd)

    def test_input_register_not_mutated(self):
        reg = self._make_register([("SYS-002", "Fail", "Fail")])
        original_disposition = reg[0]["disposition"]
        wd = [build_waiver_deviation_entry("SYS-002", "WAIVER", "Approved.", "LOW")]
        apply_waivers_deviations(reg, wd)
        self.assertEqual(reg[0]["disposition"], original_disposition)

    def test_empty_wd_register_returns_unchanged_records(self):
        reg = self._make_register([("SYS-001", "Pass", "Pass"), ("SYS-002", "Fail", "Fail")])
        result = apply_waivers_deviations(reg, [])
        self.assertEqual([r["disposition"] for r in result], ["Pass", "Fail"])


class TestCheckGateReadiness(unittest.TestCase):

    def _record(self, req_id, disposition):
        return {"requirement_id": req_id, "method": "Test",
                "status": "Pass", "notes": "", "disposition": disposition}

    def test_all_pass_is_gate_ready(self):
        reg = [self._record("R-1", "Pass"), self._record("R-2", "Pass")]
        result = check_gate_readiness(reg)
        self.assertTrue(result["gate_ready"])
        self.assertEqual(result["blocking_requirements"], [])
        self.assertEqual(result["open_items"], [])

    def test_fail_disposition_blocks_gate(self):
        reg = [self._record("R-1", "Pass"), self._record("R-2", "Fail")]
        result = check_gate_readiness(reg)
        self.assertFalse(result["gate_ready"])
        self.assertIn("R-2", result["blocking_requirements"])

    def test_deferred_appears_in_open_items_not_blocking(self):
        reg = [self._record("R-1", "Pass"), self._record("R-3", "Deferred")]
        result = check_gate_readiness(reg)
        self.assertTrue(result["gate_ready"])
        self.assertIn("R-3", result["open_items"])

    def test_waived_appears_in_open_items_not_blocking(self):
        reg = [self._record("R-1", "Pass"), self._record("R-4", "Waived")]
        result = check_gate_readiness(reg)
        self.assertTrue(result["gate_ready"])
        self.assertIn("R-4", result["open_items"])

    def test_blocking_requirements_sorted(self):
        reg = [self._record("R-B", "Fail"), self._record("R-A", "Fail")]
        result = check_gate_readiness(reg)
        self.assertEqual(result["blocking_requirements"], ["R-A", "R-B"])


class TestSummariseRegister(unittest.TestCase):

    def _record(self, req_id, disposition):
        return {"requirement_id": req_id, "method": "Test",
                "status": "Pass", "notes": "", "disposition": disposition}

    def test_counts_all_dispositions(self):
        reg = [
            self._record("R-1", "Pass"),
            self._record("R-2", "Pass"),
            self._record("R-3", "Fail"),
            self._record("R-4", "Waived"),
            self._record("R-5", "Deferred"),
        ]
        summary = summarise_register(reg)
        self.assertEqual(summary["Pass"], 2)
        self.assertEqual(summary["Fail"], 1)
        self.assertEqual(summary["Waived"], 1)
        self.assertEqual(summary["Deferred"], 1)
        self.assertEqual(summary["total"], 5)

    def test_empty_register_returns_zero_counts(self):
        summary = summarise_register([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["Pass"], 0)


class TestValidators(unittest.TestCase):

    def test_validate_risk_level_accepts_all_levels(self):
        for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            validate_risk_level(level)

    def test_validate_risk_level_rejects_unknown(self):
        with self.assertRaises(CloseoutError):
            validate_risk_level("NEGLIGIBLE")

    def test_validate_entry_type_accepts_waiver_and_deviation(self):
        validate_entry_type("WAIVER")
        validate_entry_type("DEVIATION")

    def test_validate_entry_type_rejects_unknown(self):
        with self.assertRaises(CloseoutError):
            validate_entry_type("EXEMPTION")

    def test_validate_verification_status_accepts_all_statuses(self):
        for s in ("Pass", "Fail", "Not_Verified"):
            validate_verification_status(s)

    def test_validate_verification_status_rejects_unknown(self):
        with self.assertRaises(CloseoutError):
            validate_verification_status("Pending")

    def test_validate_verification_method_accepts_all_methods(self):
        for m in ("Test", "Analysis", "Inspection", "Review"):
            validate_verification_method(m)

    def test_validate_verification_method_rejects_unknown(self):
        with self.assertRaises(CloseoutError):
            validate_verification_method("Simulation")


if __name__ == "__main__":
    unittest.main()
