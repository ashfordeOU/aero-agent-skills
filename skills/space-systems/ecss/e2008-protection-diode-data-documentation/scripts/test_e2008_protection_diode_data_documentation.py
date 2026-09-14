#!/usr/bin/env python3
"""Contract test for protection diode data documentation, clause 9.8 (offline)."""

import copy
import unittest

from e2008_protection_diode_data_documentation_logic import (
    APPROVAL_STATES,
    DEFAULT_DOCUMENTATION_POLICY,
    FILE_COMPLETE,
    FILE_FIELDS_MISSING,
    FILE_ROWS_FOREIGN,
    FILE_ROWS_MISSING,
    FILE_UNAPPROVED,
    PACKAGE_NOT_RELEASABLE,
    PACKAGE_RELEASABLE,
    RECORD_COMPLETE,
    RECORD_FIELDS_MISSING,
    RECORD_SUPERSEDED_ISSUE,
    RECORD_UNAPPROVED,
    REQUIRED_BATCH_FILE_FIELDS,
    REQUIRED_QUALIFICATION_RECORDS,
    approval_state,
    assess_batch_file,
    assess_qualification_record,
    audit_batch_file_fields,
    audit_data_package,
    audit_qualification_fields,
    reconcile_batches,
    required_batch_file_fields,
    required_qualification_records,
    row_coverage,
    validate_documentation_policy,
)

GOVERNING = {family: "issue-c" for family in REQUIRED_QUALIFICATION_RECORDS}
GOVERNING["batch-data-file"] = "issue-c"

BATCH_PARTS = {
    "batch-a": ["pd-001", "pd-002"],
    "batch-b": ["pd-003", "pd-004"],
}


def _record(family=REQUIRED_QUALIFICATION_RECORDS[0], **overrides):
    record = {
        "record_id": "rec-%s" % family[-8:],
        "family": family,
        "issue": "issue-c",
        "reference": "doc-%s" % family[-8:],
        "approval_status": "approved",
    }
    record.update(overrides)
    return record


def _batch_file(batch_id="batch-a", part_ids=None, **overrides):
    if part_ids is None:
        part_ids = BATCH_PARTS[batch_id]
    rows = [{"part_id": pid} for pid in part_ids]
    data_file = {
        "file_id": "file-%s" % batch_id,
        "batch_id": batch_id,
        "characterisation_rows": rows,
        "inspection_summary": "all parts inspected, no listed condition raised",
        "issue": "issue-c",
        "approval_status": "approved",
    }
    data_file.update(overrides)
    return data_file


def _package(**overrides):
    package = {
        "package_id": "pkg-pd-2026-03",
        "governing_issues": dict(GOVERNING),
        "qualification_records": [
            _record(family) for family in REQUIRED_QUALIFICATION_RECORDS
        ],
        "delivered_batches": [
            {"batch_id": bid, "delivered_part_ids": list(parts)}
            for bid, parts in sorted(BATCH_PARTS.items())
        ],
        "batch_data_files": [_batch_file(bid) for bid in sorted(BATCH_PARTS)],
    }
    package.update(overrides)
    return package


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_documentation_policy(DEFAULT_DOCUMENTATION_POLICY),
            DEFAULT_DOCUMENTATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy("ship it")

    def test_non_boolean_per_part_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["require_per_part_rows"] = "sometimes"
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)

    def test_family_share_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["min_recorded_family_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)


class VocabularyTests(unittest.TestCase):
    def test_required_families_come_back_as_a_tuple_copy(self):
        families = required_qualification_records()
        self.assertEqual(families, REQUIRED_QUALIFICATION_RECORDS)
        self.assertIsInstance(families, tuple)

    def test_required_file_fields_come_back_as_a_tuple_copy(self):
        fields = required_batch_file_fields()
        self.assertEqual(fields, REQUIRED_BATCH_FILE_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_the_source_control_drawing_is_a_required_family(self):
        self.assertIn(
            "protection-diode-source-control-drawing", required_qualification_records()
        )


class ApprovalStateTests(unittest.TestCase):
    def test_an_absent_status_reads_as_pending(self):
        self.assertEqual(approval_state({}), "pending")

    def test_a_known_status_comes_back_lowercased(self):
        self.assertEqual(approval_state({"approval_status": "APPROVED"}), "approved")

    def test_an_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            approval_state({"approval_status": "nearly-signed"})

    def test_every_declared_state_is_accepted(self):
        for state in APPROVAL_STATES:
            self.assertEqual(approval_state({"approval_status": state}), state)


class QualificationRecordTests(unittest.TestCase):
    def test_a_complete_record_is_complete(self):
        result = assess_qualification_record(_record(), GOVERNING)
        self.assertEqual(result["verdict"], RECORD_COMPLETE)
        self.assertTrue(result["complete"])

    def test_missing_fields_are_named(self):
        record = _record()
        del record["reference"]
        self.assertEqual(audit_qualification_fields(record), ["reference"])

    def test_a_record_missing_a_field_is_incomplete(self):
        record = _record()
        record["reference"] = "  "
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_FIELDS_MISSING)

    def test_a_superseded_issue_outranks_a_missing_field(self):
        record = _record(issue="issue-a")
        del record["reference"]
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_SUPERSEDED_ISSUE)

    def test_a_pending_approval_is_not_released(self):
        record = _record(approval_status="pending")
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)

    def test_an_unknown_family_rejected(self):
        record = _record(family="protection-diode-horoscope")
        with self.assertRaises(ValueError):
            assess_qualification_record(record, GOVERNING)

    def test_a_family_with_no_governing_issue_declared_rejected(self):
        governing = dict(GOVERNING)
        del governing[REQUIRED_QUALIFICATION_RECORDS[0]]
        with self.assertRaises(ValueError):
            assess_qualification_record(_record(), governing)

    def test_empty_governing_issues_rejected(self):
        with self.assertRaises(ValueError):
            assess_qualification_record(_record(), {})


class BatchFileTests(unittest.TestCase):
    def test_a_complete_file_is_complete(self):
        result = assess_batch_file(
            _batch_file("batch-a"), BATCH_PARTS["batch-a"], "issue-c"
        )
        self.assertEqual(result["verdict"], FILE_COMPLETE)
        self.assertTrue(result["complete"])

    def test_missing_file_fields_are_named(self):
        data_file = _batch_file("batch-a")
        del data_file["inspection_summary"]
        self.assertEqual(audit_batch_file_fields(data_file), ["inspection_summary"])

    def test_an_empty_row_list_counts_as_a_missing_field(self):
        data_file = _batch_file("batch-a", part_ids=[])
        self.assertIn("characterisation_rows", audit_batch_file_fields(data_file))

    def test_a_delivered_part_with_no_row_is_caught(self):
        data_file = _batch_file("batch-a", part_ids=["pd-001"])
        result = assess_batch_file(data_file, BATCH_PARTS["batch-a"], "issue-c")
        self.assertEqual(result["verdict"], FILE_ROWS_MISSING)
        self.assertEqual(result["coverage"]["missing_row_part_ids"], ["pd-002"])

    def test_a_foreign_row_outranks_a_missing_row(self):
        data_file = _batch_file("batch-a", part_ids=["pd-001", "pd-900"])
        result = assess_batch_file(data_file, BATCH_PARTS["batch-a"], "issue-c")
        self.assertEqual(result["verdict"], FILE_ROWS_FOREIGN)
        self.assertEqual(result["coverage"]["foreign_row_part_ids"], ["pd-900"])

    def test_row_coverage_is_reported_either_way(self):
        data_file = _batch_file("batch-a", part_ids=["pd-001"])
        coverage = row_coverage(data_file, BATCH_PARTS["batch-a"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 0.5, places=9)

    def test_full_row_coverage_reads_as_one(self):
        coverage = row_coverage(_batch_file("batch-b"), BATCH_PARTS["batch-b"])
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=9)

    def test_a_pending_file_is_not_released(self):
        data_file = _batch_file("batch-a", approval_status="pending")
        result = assess_batch_file(data_file, BATCH_PARTS["batch-a"], "issue-c")
        self.assertEqual(result["verdict"], FILE_UNAPPROVED)

    def test_a_file_citing_another_issue_is_not_complete(self):
        data_file = _batch_file("batch-a", issue="issue-a")
        result = assess_batch_file(data_file, BATCH_PARTS["batch-a"], "issue-c")
        self.assertFalse(result["complete"])
        self.assertFalse(result["issue_matches_governing"])

    def test_a_row_without_a_part_identifier_rejected(self):
        data_file = _batch_file("batch-a")
        data_file["characterisation_rows"] = [{"reading": 0.8}]
        with self.assertRaises(ValueError):
            row_coverage(data_file, BATCH_PARTS["batch-a"])

    def test_a_missing_field_still_reads_as_fields_missing(self):
        data_file = _batch_file("batch-a")
        data_file["inspection_summary"] = "  "
        result = assess_batch_file(data_file, BATCH_PARTS["batch-a"], "issue-c")
        self.assertEqual(result["verdict"], FILE_FIELDS_MISSING)


class ReconciliationTests(unittest.TestCase):
    def test_matching_batches_and_files_reconcile(self):
        result = reconcile_batches(
            sorted(BATCH_PARTS), [_batch_file(bid) for bid in sorted(BATCH_PARTS)]
        )
        self.assertTrue(result["reconciled"])

    def test_a_delivered_batch_with_no_file_is_named(self):
        result = reconcile_batches(sorted(BATCH_PARTS), [_batch_file("batch-a")])
        self.assertEqual(result["batches_without_a_file"], ["batch-b"])

    def test_a_file_for_a_batch_not_delivered_is_named(self):
        files = [_batch_file(bid) for bid in sorted(BATCH_PARTS)]
        stray = _batch_file("batch-a", part_ids=["pd-001"])
        stray["batch_id"] = "batch-z"
        stray["file_id"] = "file-batch-z"
        files.append(stray)
        result = reconcile_batches(sorted(BATCH_PARTS), files)
        self.assertEqual(result["files_without_a_batch"], ["batch-z"])

    def test_two_files_for_one_batch_rejected(self):
        files = [_batch_file("batch-a"), _batch_file("batch-a")]
        with self.assertRaises(ValueError):
            reconcile_batches(["batch-a"], files)

    def test_an_empty_delivered_batch_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_batches([], [_batch_file("batch-a")])


class PackageTests(unittest.TestCase):
    def test_a_complete_package_is_releasable(self):
        result = audit_data_package(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["recorded_family_fraction"], 1.0, places=9)

    def test_a_family_with_no_record_stops_release(self):
        package = _package()
        package["qualification_records"] = package["qualification_records"][:-1]
        result = audit_data_package(package)
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["unrecorded_families"], [REQUIRED_QUALIFICATION_RECORDS[-1]]
        )

    def test_the_recorded_family_share_is_reported(self):
        package = _package()
        package["qualification_records"] = package["qualification_records"][:-1]
        result = audit_data_package(package)
        self.assertAlmostEqual(result["recorded_family_fraction"], 0.8, places=9)

    def test_three_revisions_of_one_family_do_not_cover_the_others(self):
        family = REQUIRED_QUALIFICATION_RECORDS[0]
        package = _package(
            qualification_records=[
                _record(family, record_id="rec-%d" % n) for n in (1, 2, 3)
            ]
        )
        result = audit_data_package(package)
        self.assertEqual(len(result["unrecorded_families"]), 4)

    def test_a_superseded_record_stops_release(self):
        package = _package()
        package["qualification_records"][1] = _record(
            REQUIRED_QUALIFICATION_RECORDS[1], issue="issue-a"
        )
        result = audit_data_package(package)
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertFalse(result["records_complete"])

    def test_a_delivered_batch_with_no_file_stops_release(self):
        package = _package()
        package["batch_data_files"] = [_batch_file("batch-a")]
        result = audit_data_package(package)
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["reconciliation"]["batches_without_a_file"], ["batch-b"]
        )

    def test_a_file_for_an_undelivered_batch_stops_release(self):
        package = _package()
        extra = _batch_file("batch-a", part_ids=["pd-001"])
        extra["batch_id"] = "batch-z"
        extra["file_id"] = "file-batch-z"
        package["batch_data_files"] = package["batch_data_files"] + [extra]
        result = audit_data_package(package)
        self.assertEqual(result["reconciliation"]["files_without_a_batch"], ["batch-z"])
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)

    def test_a_delivered_part_with_no_row_stops_release(self):
        package = _package()
        package["batch_data_files"][0] = _batch_file("batch-a", part_ids=["pd-001"])
        result = audit_data_package(package)
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertFalse(result["files_complete"])

    def test_the_findings_are_collected_not_ranked_away(self):
        package = _package()
        package["qualification_records"][0] = _record(
            REQUIRED_QUALIFICATION_RECORDS[0], issue="issue-a"
        )
        package["batch_data_files"][1] = _batch_file(
            "batch-b", approval_status="pending"
        )
        result = audit_data_package(package)
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_file_assessments_come_back_in_batch_order(self):
        package = _package()
        package["batch_data_files"] = list(reversed(package["batch_data_files"]))
        result = audit_data_package(package)
        ids = [entry["batch_id"] for entry in result["file_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_package_without_an_identifier_rejected(self):
        package = _package()
        del package["package_id"]
        with self.assertRaises(ValueError):
            audit_data_package(package)

    def test_a_package_delivering_no_batch_rejected(self):
        package = _package(delivered_batches=[])
        with self.assertRaises(ValueError):
            audit_data_package(package)

    def test_a_batch_delivering_no_part_rejected(self):
        package = _package()
        package["delivered_batches"][0]["delivered_part_ids"] = []
        with self.assertRaises(ValueError):
            audit_data_package(package)

    def test_non_sequence_qualification_records_rejected(self):
        package = _package(qualification_records={"family": "x"})
        with self.assertRaises(ValueError):
            audit_data_package(package)


if __name__ == "__main__":
    unittest.main()
