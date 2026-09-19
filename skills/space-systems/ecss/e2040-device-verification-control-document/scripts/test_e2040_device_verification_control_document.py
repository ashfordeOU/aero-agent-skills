#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-verification-control-document.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_verification_control_document.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_verification_control_document_logic import (  # noqa: E402
    FLIGHT_RELEASE_STAGES,
    STAGE_STATUSES,
    VERIFICATION_STAGES,
    applicable_stages,
    assess_verification_control_document,
    closures_without_evidence,
    detect_stage_order_violations,
    meets_closure_target,
    normalize_stage,
    normalize_status,
    overall_closure,
    stage_closure,
    stage_counts,
    stage_index,
    validate_control,
    validate_rows,
)


def closed(reference):
    return {"status": "closed", "evidence": reference}


def base_document():
    return {
        "control": {
            "issue": 3,
            "revision": "B",
            "configuration_item": "power conditioning device",
        },
        "rows": [
            {
                "requirement": "R-1",
                "stages": {
                    "qualification": closed("QTR-001"),
                    "acceptance": closed("ATR-001"),
                    "pre-launch": {"status": "open"},
                    "in-orbit": {"status": "not-applicable"},
                },
            },
            {
                "requirement": "R-2",
                "stages": {
                    "qualification": closed("QTR-002"),
                    "acceptance": closed("ATR-002"),
                    "pre-launch": {"status": "in-work"},
                    "in-orbit": {"status": "open"},
                },
            },
            {
                "requirement": "R-3",
                "stages": {
                    "qualification": closed("ANA-003"),
                    "acceptance": {"status": "not-applicable"},
                    "pre-launch": {"status": "not-applicable"},
                    "in-orbit": {"status": "not-applicable"},
                },
            },
        ],
        "closure_targets": {"qualification": 1.0, "acceptance": 1.0},
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_stage_alias_folds(self):
        self.assertEqual(normalize_stage("Pre Launch"), "pre-launch")

    def test_in_flight_folds_to_in_orbit(self):
        self.assertEqual(normalize_stage("in flight"), "in-orbit")

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            normalize_stage("storage")

    def test_status_alias_folds(self):
        self.assertEqual(normalize_status("N/A"), "not-applicable")

    def test_in_work_alias_folds(self):
        self.assertEqual(normalize_status("Ongoing"), "in-work")

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_status("nearly done")

    def test_stage_order_is_fixed(self):
        self.assertEqual(stage_index("qualification"), 0)
        self.assertLess(stage_index("acceptance"), stage_index("pre-launch"))
        self.assertEqual(len(VERIFICATION_STAGES), 4)
        self.assertEqual(len(STAGE_STATUSES), 4)
        self.assertEqual(FLIGHT_RELEASE_STAGES, ("qualification", "acceptance"))


class TestControlBlock(unittest.TestCase):
    def test_valid_control_block_resolves(self):
        control = validate_control(base_document()["control"])
        self.assertEqual(control["issue"], 3)
        self.assertEqual(control["revision"], "B")

    def test_missing_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_control({"revision": "A"})

    def test_zero_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_control({"issue": 0, "revision": "A"})

    def test_boolean_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_control({"issue": True, "revision": "A"})

    def test_missing_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_control({"issue": 1, "revision": "  "})

    def test_unknown_control_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_control({"issue": 1, "revision": "A", "author": "x"})


class TestRows(unittest.TestCase):
    def test_duplicate_requirement_row_rejected(self):
        rows = base_document()["rows"]
        rows.append(dict(rows[0]))
        with self.assertRaises(ValueError):
            validate_rows(rows)

    def test_row_without_stages_rejected(self):
        with self.assertRaises(ValueError):
            validate_rows([{"requirement": "R-9", "stages": {}}])

    def test_unknown_stage_entry_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_rows(
                [
                    {
                        "requirement": "R-9",
                        "stages": {"qualification": {"status": "open", "who": "x"}},
                    }
                ]
            )

    def test_stage_entry_without_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_rows(
                [{"requirement": "R-9", "stages": {"qualification": {}}}]
            )

    def test_not_applicable_stage_leaves_the_applicable_list(self):
        rows = validate_rows(base_document()["rows"])
        self.assertEqual(applicable_stages(rows[2]), ["qualification"])


class TestStageOrdering(unittest.TestCase):
    def test_clean_document_has_no_ordering_violation(self):
        rows = validate_rows(base_document()["rows"])
        self.assertEqual(detect_stage_order_violations(rows), [])

    def test_acceptance_closed_ahead_of_qualification_is_caught(self):
        document = base_document()
        document["rows"][0]["stages"]["qualification"] = {"status": "in-work"}
        result = assess_verification_control_document(document)
        self.assertIn("stage-closed-out-of-order", codes(result))
        self.assertFalse(result["flight_release_supported"])

    def test_not_applicable_earlier_stage_does_not_block(self):
        document = base_document()
        document["rows"][2]["stages"]["acceptance"] = closed("ATR-003")
        rows = validate_rows(document["rows"])
        self.assertEqual(detect_stage_order_violations(rows), [])

    def test_open_later_stage_is_not_a_violation(self):
        rows = validate_rows(base_document()["rows"])
        self.assertEqual(detect_stage_order_violations(rows), [])


class TestEvidence(unittest.TestCase):
    def test_closure_without_evidence_is_caught(self):
        document = base_document()
        document["rows"][1]["stages"]["acceptance"] = {"status": "closed"}
        result = assess_verification_control_document(document)
        self.assertIn("closure-without-evidence", codes(result))
        self.assertFalse(result["flight_release_supported"])

    def test_open_stage_needs_no_evidence(self):
        rows = validate_rows(base_document()["rows"])
        self.assertEqual(closures_without_evidence(rows), [])


class TestCounting(unittest.TestCase):
    def test_not_applicable_rows_are_counted_separately(self):
        rows = validate_rows(base_document()["rows"])
        counts = stage_counts(rows, "acceptance")
        self.assertEqual(counts["applicable"], 2)
        self.assertEqual(counts["not_applicable"], 1)

    def test_stage_closure_uses_applicable_rows_only(self):
        rows = validate_rows(base_document()["rows"])
        self.assertAlmostEqual(stage_closure(rows, "acceptance"), 1.0, places=9)

    def test_stage_closure_without_applicable_rows_rejected(self):
        rows = validate_rows(
            [
                {
                    "requirement": "R-1",
                    "stages": {"in-orbit": {"status": "not-applicable"},
                               "qualification": closed("Q")},
                }
            ]
        )
        with self.assertRaises(ValueError):
            stage_closure(rows, "in-orbit")

    def test_overall_closure_is_five_in_eight(self):
        rows = validate_rows(base_document()["rows"])
        self.assertAlmostEqual(overall_closure(rows), 5.0 / 8.0, places=9)

    def test_pre_launch_closure_is_zero_over_two(self):
        rows = validate_rows(base_document()["rows"])
        self.assertAlmostEqual(stage_closure(rows, "pre-launch"), 0.0, places=9)


class TestTargetPortability(unittest.TestCase):
    def test_exact_landing_meets_the_target(self):
        self.assertTrue(meets_closure_target(3.0 / 4.0, 0.75))

    def test_one_in_three_meets_a_one_in_three_target(self):
        self.assertTrue(meets_closure_target(1.0 / 3.0, 1.0 / 3.0))

    def test_below_target_reported(self):
        self.assertFalse(meets_closure_target(0.25, 0.75))

    def test_target_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            meets_closure_target(0.5, -0.1)

    def test_missed_target_is_a_finding(self):
        document = base_document()
        document["closure_targets"]["pre-launch"] = 0.5
        result = assess_verification_control_document(document)
        self.assertIn("closure-target-missed", codes(result))

    def test_target_on_a_stage_with_no_applicable_row_is_a_finding(self):
        document = base_document()
        for row in document["rows"]:
            row["stages"]["in-orbit"] = {"status": "not-applicable"}
        document["closure_targets"]["in-orbit"] = 1.0
        result = assess_verification_control_document(document)
        self.assertIn("closure-target-without-applicable-row", codes(result))


class TestAssessment(unittest.TestCase):
    def test_clean_document_supports_flight_release(self):
        result = assess_verification_control_document(base_document())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["flight_release_supported"])
        self.assertTrue(result["acceptable"])

    def test_open_qualification_withholds_flight_release(self):
        document = base_document()
        document["rows"][1]["stages"]["qualification"] = {"status": "open"}
        document["rows"][1]["stages"]["acceptance"] = {"status": "open"}
        result = assess_verification_control_document(document)
        self.assertFalse(result["flight_release_supported"])

    def test_row_count_and_baseline_reported(self):
        result = assess_verification_control_document(base_document())
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["issue"], 3)
        self.assertEqual(result["revision"], "B")

    def test_unknown_document_key_rejected(self):
        document = base_document()
        document["annexes"] = []
        with self.assertRaises(ValueError):
            assess_verification_control_document(document)

    def test_missing_rows_rejected(self):
        document = base_document()
        del document["rows"]
        with self.assertRaises(ValueError):
            assess_verification_control_document(document)

    def test_empty_row_list_rejected(self):
        document = base_document()
        document["rows"] = []
        with self.assertRaises(ValueError):
            assess_verification_control_document(document)

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_control_document([("control", {})])


if __name__ == "__main__":
    unittest.main()
