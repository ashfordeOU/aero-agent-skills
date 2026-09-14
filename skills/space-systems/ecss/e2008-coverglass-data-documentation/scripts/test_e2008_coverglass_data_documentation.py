#!/usr/bin/env python3
"""Contract test for coverglass data documentation, clause 8.9 (offline)."""

import copy
import unittest

from e2008_coverglass_data_documentation_logic import (
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
    assess_data_package,
    assess_qualification_record,
    audit_batch_file_fields,
    audit_qualification_fields,
    reconcile_batches,
    required_batch_file_fields,
    required_qualification_records,
    row_piece_ids,
    validate_documentation_policy,
)

GOVERNING = {family: "issue-c" for family in REQUIRED_QUALIFICATION_RECORDS}
BATCH_PIECES = ["cg-001", "cg-002", "cg-003"]


def _record(family, record_id=None, **overrides):
    record = {
        "record_id": record_id or ("qr-%s" % family),
        "family": family,
        "issue": "issue-c",
        "reference": "doc-%s-issue-c" % family,
        "approval_status": "approved",
    }
    record.update(overrides)
    return record


def _batch(batch_id="cg-batch-a", pieces=None):
    return {
        "batch_id": batch_id,
        "piece_ids": list(pieces if pieces is not None else BATCH_PIECES),
    }


def _rows(pieces=None):
    return [
        {"piece_id": piece, "transmittance": 0.95, "thickness_mm": 0.100}
        for piece in (pieces if pieces is not None else BATCH_PIECES)
    ]


def _file(batch_id="cg-batch-a", file_id=None, pieces=None, **overrides):
    batch_file = {
        "file_id": file_id or ("df-%s" % batch_id),
        "batch_id": batch_id,
        "measured_data_rows": _rows(pieces),
        "inspection_summary": "visual and dimensional inspection outcome table",
        "issue": "issue-c",
        "approval_status": "approved",
    }
    batch_file.update(overrides)
    return batch_file


def _package(records=None, batches=None, files=None, **overrides):
    package = {
        "package_id": "cg-data-package-1",
        "governing_issues": dict(GOVERNING),
        "qualification_records": records
        if records is not None
        else [_record(f) for f in REQUIRED_QUALIFICATION_RECORDS],
        "delivered_batches": batches if batches is not None else [_batch()],
        "batch_files": files if files is not None else [_file()],
    }
    package.update(overrides)
    return package


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_documentation_policy(DEFAULT_DOCUMENTATION_POLICY),
            DEFAULT_DOCUMENTATION_POLICY,
        )

    def test_default_policy_demands_a_row_per_piece(self):
        self.assertTrue(DEFAULT_DOCUMENTATION_POLICY["require_per_piece_rows"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy("file everything")

    def test_out_of_range_family_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["min_recorded_family_fraction"] = 2.0
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)

    def test_non_boolean_issue_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["require_governing_issue_match"] = "yes"
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)


class RequiredSetTests(unittest.TestCase):
    def test_family_set_comes_back_as_a_tuple_copy(self):
        families = required_qualification_records()
        self.assertEqual(families, REQUIRED_QUALIFICATION_RECORDS)
        self.assertIsInstance(families, tuple)

    def test_batch_field_set_comes_back_as_a_tuple_copy(self):
        fields = required_batch_file_fields()
        self.assertEqual(fields, REQUIRED_BATCH_FILE_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_the_process_document_is_a_qualification_family(self):
        self.assertIn("coverglass-process-document", required_qualification_records())


class QualificationRecordTests(unittest.TestCase):
    def test_a_full_record_is_missing_nothing(self):
        self.assertEqual(
            audit_qualification_fields(_record("coverglass-process-document")), []
        )

    def test_a_blank_reference_is_named(self):
        record = _record("coverglass-process-document", reference="  ")
        self.assertEqual(audit_qualification_fields(record), ["reference"])

    def test_a_full_record_is_complete(self):
        result = assess_qualification_record(
            _record("coverglass-process-document"), GOVERNING
        )
        self.assertEqual(result["verdict"], RECORD_COMPLETE)
        self.assertTrue(result["issue_matches"])

    def test_a_record_at_a_superseded_issue_is_caught(self):
        record = _record("coverglass-process-document", issue="issue-b")
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_SUPERSEDED_ISSUE)
        self.assertFalse(result["issue_matches"])

    def test_a_superseded_issue_outranks_a_missing_field(self):
        record = _record("coverglass-process-document", issue="issue-b", reference="")
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_SUPERSEDED_ISSUE)

    def test_a_missing_field_outranks_a_pending_approval(self):
        record = _record(
            "coverglass-process-document", reference="", approval_status="pending"
        )
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_FIELDS_MISSING)

    def test_a_pending_record_is_unapproved(self):
        record = _record("coverglass-process-document", approval_status="pending")
        result = assess_qualification_record(record, GOVERNING)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)

    def test_the_issue_check_can_be_dropped_by_policy(self):
        policy = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        policy["require_governing_issue_match"] = False
        record = _record("coverglass-process-document", issue="issue-b")
        result = assess_qualification_record(record, GOVERNING, policy)
        self.assertEqual(result["verdict"], RECORD_COMPLETE)

    def test_an_unknown_family_rejected(self):
        record = _record("coverglass-process-document")
        record["family"] = "coverglass-horoscope"
        with self.assertRaises(ValueError):
            assess_qualification_record(record, GOVERNING)

    def test_an_undeclared_governing_issue_rejected(self):
        governing = dict(GOVERNING)
        del governing["coverglass-process-document"]
        with self.assertRaises(ValueError):
            assess_qualification_record(
                _record("coverglass-process-document"), governing
            )

    def test_an_unknown_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            approval_state(_record("coverglass-process-document", approval_status="waved through"))

    def test_a_record_with_no_approval_field_reads_as_pending(self):
        record = _record("coverglass-process-document")
        del record["approval_status"]
        self.assertEqual(approval_state(record), "pending")


class BatchFileTests(unittest.TestCase):
    def test_a_full_file_is_missing_nothing(self):
        self.assertEqual(audit_batch_file_fields(_file()), [])

    def test_an_empty_row_table_is_named(self):
        self.assertEqual(
            audit_batch_file_fields(_file(measured_data_rows=[])),
            ["measured_data_rows"],
        )

    def test_row_piece_identifiers_are_read_back(self):
        self.assertEqual(row_piece_ids(_file()), sorted(BATCH_PIECES))

    def test_a_row_without_a_piece_identifier_rejected(self):
        batch_file = _file()
        batch_file["measured_data_rows"] = [{"transmittance": 0.9}]
        with self.assertRaises(ValueError):
            row_piece_ids(batch_file)

    def test_a_full_file_is_complete(self):
        result = assess_batch_file(_file(), _batch())
        self.assertEqual(result["verdict"], FILE_COMPLETE)
        self.assertAlmostEqual(result["row_coverage_fraction"], 1.0, places=9)

    def test_a_piece_with_no_row_is_named(self):
        result = assess_batch_file(_file(pieces=["cg-001", "cg-002"]), _batch())
        self.assertEqual(result["verdict"], FILE_ROWS_MISSING)
        self.assertEqual(result["uncovered_piece_ids"], ["cg-003"])

    def test_the_row_coverage_share_is_reported(self):
        result = assess_batch_file(_file(pieces=["cg-001", "cg-002"]), _batch())
        self.assertAlmostEqual(result["row_coverage_fraction"], 2.0 / 3.0, places=9)

    def test_a_foreign_row_outranks_a_missing_row(self):
        result = assess_batch_file(
            _file(pieces=["cg-001", "cg-999"]), _batch()
        )
        self.assertEqual(result["verdict"], FILE_ROWS_FOREIGN)
        self.assertEqual(result["foreign_piece_ids"], ["cg-999"])

    def test_a_missing_field_outranks_a_missing_row(self):
        batch_file = _file(pieces=["cg-001"], inspection_summary="")
        result = assess_batch_file(batch_file, _batch())
        self.assertEqual(result["verdict"], FILE_FIELDS_MISSING)

    def test_a_complete_but_pending_file_is_unapproved(self):
        result = assess_batch_file(_file(approval_status="pending"), _batch())
        self.assertEqual(result["verdict"], FILE_UNAPPROVED)

    def test_per_piece_rows_can_be_dropped_by_policy(self):
        policy = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        policy["require_per_piece_rows"] = False
        result = assess_batch_file(_file(pieces=["cg-001"]), _batch(), policy)
        self.assertEqual(result["verdict"], FILE_COMPLETE)

    def test_a_file_read_against_the_wrong_batch_rejected(self):
        with self.assertRaises(ValueError):
            assess_batch_file(_file(batch_id="cg-batch-b"), _batch("cg-batch-a"))

    def test_a_batch_without_piece_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            assess_batch_file(_file(), _batch(pieces=[]))


class ReconciliationTests(unittest.TestCase):
    def test_one_batch_and_one_file_reconcile(self):
        result = reconcile_batches([_batch()], [_file()])
        self.assertTrue(result["reconciled"])

    def test_a_batch_with_no_file_is_named(self):
        result = reconcile_batches([_batch("cg-batch-a"), _batch("cg-batch-b")], [_file()])
        self.assertEqual(result["batches_without_a_file"], ["cg-batch-b"])
        self.assertFalse(result["reconciled"])

    def test_a_file_with_no_batch_is_named(self):
        result = reconcile_batches([_batch()], [_file(), _file("cg-batch-z")])
        self.assertEqual(result["files_without_a_batch"], ["cg-batch-z"])

    def test_a_repeated_batch_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_batches([_batch(), _batch()], [_file()])

    def test_an_empty_batch_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_batches([], [_file()])


class PackageTests(unittest.TestCase):
    def test_a_full_package_is_releasable(self):
        result = assess_data_package(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_family_recorded"])

    def test_a_missing_qualification_family_blocks_release(self):
        records = [
            _record(f)
            for f in REQUIRED_QUALIFICATION_RECORDS
            if f != "coverglass-coating-specification"
        ]
        result = assess_data_package(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["missing_qualification_families"],
            ["coverglass-coating-specification"],
        )

    def test_the_recorded_family_share_is_reported(self):
        records = [
            _record(f)
            for f in REQUIRED_QUALIFICATION_RECORDS
            if f != "coverglass-coating-specification"
        ]
        result = assess_data_package(_package(records))
        self.assertAlmostEqual(result["recorded_family_fraction"], 4.0 / 5.0, places=9)

    def test_a_full_package_records_every_family(self):
        result = assess_data_package(_package())
        self.assertAlmostEqual(result["recorded_family_fraction"], 1.0, places=9)

    def test_a_delivered_batch_with_no_file_blocks_release(self):
        result = assess_data_package(
            _package(batches=[_batch("cg-batch-a"), _batch("cg-batch-b")])
        )
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["batch_reconciliation"]["batches_without_a_file"], ["cg-batch-b"]
        )

    def test_a_file_on_an_undelivered_batch_blocks_release(self):
        result = assess_data_package(
            _package(files=[_file(), _file("cg-batch-z")])
        )
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["batch_reconciliation"]["files_without_a_batch"], ["cg-batch-z"]
        )

    def test_an_uncovered_piece_blocks_release(self):
        result = assess_data_package(_package(files=[_file(pieces=["cg-001"])]))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(result["open_file_ids"], ["df-cg-batch-a"])

    def test_a_superseded_record_blocks_release(self):
        records = [_record(f) for f in REQUIRED_QUALIFICATION_RECORDS]
        records[0]["issue"] = "issue-a"
        result = assess_data_package(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertIn(
            records[0]["record_id"],
            result["grouped_records_by_verdict"][RECORD_SUPERSEDED_ISSUE],
        )

    def test_open_records_are_listed(self):
        records = [_record(f) for f in REQUIRED_QUALIFICATION_RECORDS]
        records[1]["approval_status"] = "withdrawn"
        result = assess_data_package(_package(records))
        self.assertEqual(result["open_record_ids"], [records[1]["record_id"]])

    def test_files_are_grouped_by_verdict(self):
        result = assess_data_package(_package(files=[_file(pieces=["cg-001"])]))
        self.assertEqual(
            result["grouped_files_by_verdict"][FILE_ROWS_MISSING], ["df-cg-batch-a"]
        )

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_data_package(_package())
        ids = [e["record_id"] for e in result["qualification_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_a_repeated_record_identifier_rejected(self):
        records = [
            _record("coverglass-process-document", record_id="qr-1"),
            _record("coverglass-material-specification", record_id="qr-1"),
        ]
        with self.assertRaises(ValueError):
            assess_data_package(_package(records))

    def test_a_repeated_file_identifier_rejected(self):
        files = [_file(file_id="df-1"), _file("cg-batch-b", file_id="df-1")]
        with self.assertRaises(ValueError):
            assess_data_package(_package(files=files))

    def test_a_package_without_governing_issues_rejected(self):
        package = _package()
        del package["governing_issues"]
        with self.assertRaises(ValueError):
            assess_data_package(package)

    def test_a_package_without_qualification_records_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_package(_package(records=[]))

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_data_package([_record("coverglass-process-document")])

    def test_the_package_carries_every_file_finding(self):
        result = assess_data_package(_package(files=[_file(pieces=["cg-001"])]))
        self.assertTrue(any("cg-003" in finding for finding in result["findings"]))


if __name__ == "__main__":
    unittest.main()
