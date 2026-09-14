#!/usr/bin/env python3
"""Contract test for bare-cell acceptance documentation, clause 7.3.3 (offline)."""

import copy
import unittest

from e2008_bare_cell_acceptance_documentation_logic import (
    DEFAULT_DOCUMENTATION_POLICY,
    PACKAGE_NOT_RELEASABLE,
    PACKAGE_RELEASABLE,
    RECORD_COMPLETE,
    RECORD_FIELDS_MISSING,
    RECORD_UNAPPROVED,
    RECORD_UNTRACEABLE,
    REQUIRED_ACCEPTANCE_RECORDS,
    REQUIRED_RECORD_FIELDS,
    activity_cell_coverage,
    record_approval_state,
    assess_acceptance_documentation,
    assess_acceptance_record,
    audit_record_fields,
    record_traceability,
    required_acceptance_records,
    required_record_fields,
    validate_documentation_policy,
)

DELIVERED = ["cell-001", "cell-002", "cell-003"]


def _record(activity, record_id=None, cells=None, **overrides):
    record = {
        "record_id": record_id or ("rec-%s" % activity),
        "activity": activity,
        "lot_id": "lot-a",
        "cell_ids": list(cells if cells is not None else DELIVERED),
        "test_conditions": "AM0 spectrum, 25 degrees celsius, normal incidence",
        "measured_results": "per-cell current and voltage table attached",
        "equipment_calibration_ref": "cal-2026-0142",
        "performed_on": "2026-09-01",
        "approved_by": "quality-engineer-one",
        "approval_status": "approved",
    }
    record.update(overrides)
    return record


def _package(records=None, **overrides):
    package = {
        "lot_id": "lot-a",
        "delivered_cell_ids": list(DELIVERED),
        "records": records
        if records is not None
        else [_record(activity) for activity in REQUIRED_ACCEPTANCE_RECORDS],
    }
    package.update(overrides)
    return package


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_documentation_policy(DEFAULT_DOCUMENTATION_POLICY),
            DEFAULT_DOCUMENTATION_POLICY,
        )

    def test_default_policy_refuses_a_summary_for_results(self):
        self.assertFalse(
            DEFAULT_DOCUMENTATION_POLICY["admit_summary_in_place_of_results"]
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_policy("record everything")

    def test_out_of_range_activity_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["min_recorded_activity_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)

    def test_non_boolean_coverage_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        broken["require_full_cell_coverage"] = "yes"
        with self.assertRaises(ValueError):
            validate_documentation_policy(broken)


class RequiredSetTests(unittest.TestCase):
    def test_activity_set_is_returned_as_a_tuple_copy(self):
        activities = required_acceptance_records()
        self.assertEqual(activities, REQUIRED_ACCEPTANCE_RECORDS)
        self.assertIsInstance(activities, tuple)

    def test_field_set_is_returned_as_a_tuple_copy(self):
        fields = required_record_fields()
        self.assertEqual(fields, REQUIRED_RECORD_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_field_set_carries_conditions_and_calibration(self):
        fields = required_record_fields()
        self.assertIn("test_conditions", fields)
        self.assertIn("equipment_calibration_ref", fields)


class FieldAuditTests(unittest.TestCase):
    def test_a_full_record_is_missing_nothing(self):
        self.assertEqual(
            audit_record_fields(_record("bare-cell-visual-inspection")), []
        )

    def test_a_dropped_condition_field_is_named(self):
        record = _record("bare-cell-visual-inspection", test_conditions="")
        self.assertEqual(audit_record_fields(record), ["test_conditions"])

    def test_a_missing_calibration_reference_is_named(self):
        record = _record("bare-cell-visual-inspection")
        del record["equipment_calibration_ref"]
        self.assertEqual(audit_record_fields(record), ["equipment_calibration_ref"])

    def test_an_empty_cell_list_is_named(self):
        record = _record("bare-cell-visual-inspection", cell_ids=[])
        self.assertEqual(audit_record_fields(record), ["cell_ids"])

    def test_missing_results_stand_when_policy_admits_a_summary(self):
        record = _record("bare-cell-visual-inspection", measured_results="")
        policy = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        policy["admit_summary_in_place_of_results"] = True
        self.assertEqual(audit_record_fields(record, policy), [])

    def test_a_missing_approver_is_named(self):
        record = _record("bare-cell-visual-inspection", approved_by="")
        self.assertEqual(audit_record_fields(record), ["approved_by"])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_record_fields("a record")


class TraceabilityTests(unittest.TestCase):
    def test_a_record_on_delivered_cells_is_traceable(self):
        result = record_traceability(_record("bare-cell-mass-measurement"), DELIVERED)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["foreign_cell_ids"], [])

    def test_a_foreign_cell_is_named(self):
        record = _record("bare-cell-mass-measurement", cells=["cell-001", "cell-999"])
        result = record_traceability(record, DELIVERED)
        self.assertFalse(result["traceable"])
        self.assertEqual(result["foreign_cell_ids"], ["cell-999"])

    def test_covered_cells_are_the_intersection(self):
        record = _record("bare-cell-mass-measurement", cells=["cell-001", "cell-999"])
        result = record_traceability(record, DELIVERED)
        self.assertEqual(result["covered_cell_ids"], ["cell-001"])

    def test_empty_delivered_list_rejected(self):
        with self.assertRaises(ValueError):
            record_traceability(_record("bare-cell-mass-measurement"), [])


class RecordVerdictTests(unittest.TestCase):
    def test_a_full_record_is_complete(self):
        result = assess_acceptance_record(
            _record("bare-cell-visual-inspection"), DELIVERED
        )
        self.assertEqual(result["verdict"], RECORD_COMPLETE)
        self.assertTrue(result["complete"])

    def test_a_foreign_cell_outranks_a_missing_field(self):
        record = _record(
            "bare-cell-visual-inspection",
            cells=["cell-999"],
            test_conditions="",
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNTRACEABLE)

    def test_a_missing_field_outranks_a_missing_approval(self):
        record = _record(
            "bare-cell-visual-inspection", test_conditions="", approved_by=""
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_FIELDS_MISSING)

    def test_a_full_but_still_pending_record_is_unapproved(self):
        record = _record("bare-cell-visual-inspection", approval_status="pending")
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)
        self.assertFalse(result["approved"])

    def test_a_pending_record_stands_when_policy_drops_the_signature(self):
        record = _record("bare-cell-visual-inspection", approval_status="pending")
        policy = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        policy["require_approval_signature"] = False
        result = assess_acceptance_record(record, DELIVERED, policy)
        self.assertEqual(result["verdict"], RECORD_COMPLETE)

    def test_a_withdrawn_record_is_not_approved(self):
        record = _record("bare-cell-visual-inspection", approval_status="withdrawn")
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)

    def test_an_unknown_activity_rejected(self):
        record = _record("bare-cell-visual-inspection")
        record["activity"] = "cell-taste-test"
        with self.assertRaises(ValueError):
            assess_acceptance_record(record, DELIVERED)

    def test_a_record_without_an_identifier_rejected(self):
        record = _record("bare-cell-visual-inspection")
        del record["record_id"]
        with self.assertRaises(ValueError):
            assess_acceptance_record(record, DELIVERED)

    def test_findings_name_the_record(self):
        record = _record("bare-cell-visual-inspection", test_conditions="")
        result = assess_acceptance_record(record, DELIVERED)
        self.assertTrue(any("rec-bare-cell-visual" in f for f in result["findings"]))


class ApprovalStateTests(unittest.TestCase):
    def test_a_record_with_no_status_is_pending(self):
        record = _record("bare-cell-visual-inspection")
        del record["approval_status"]
        self.assertEqual(record_approval_state(record), "pending")

    def test_an_approved_record_reads_back(self):
        self.assertEqual(
            record_approval_state(_record("bare-cell-visual-inspection")), "approved"
        )

    def test_an_unknown_approval_state_rejected(self):
        record = _record("bare-cell-visual-inspection", approval_status="rubber-stamped")
        with self.assertRaises(ValueError):
            record_approval_state(record)

    def test_non_mapping_record_rejected_for_approval_state(self):
        with self.assertRaises(ValueError):
            record_approval_state("approved")


class CoverageTests(unittest.TestCase):
    def test_every_delivered_cell_is_reached(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_RECORDS]
        coverage = activity_cell_coverage(records, DELIVERED)
        self.assertTrue(
            all(entry["complete"] for entry in coverage.values())
        )

    def test_an_unreached_cell_is_named(self):
        records = [
            _record(a, cells=["cell-001", "cell-002"])
            for a in REQUIRED_ACCEPTANCE_RECORDS
        ]
        coverage = activity_cell_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["bare-cell-mass-measurement"]["uncovered_cell_ids"], ["cell-003"]
        )

    def test_two_records_together_cover_an_activity(self):
        records = [
            _record(
                "bare-cell-visual-inspection",
                record_id="rec-1",
                cells=["cell-001"],
            ),
            _record(
                "bare-cell-visual-inspection",
                record_id="rec-2",
                cells=["cell-002", "cell-003"],
            ),
        ]
        coverage = activity_cell_coverage(records, DELIVERED)
        self.assertTrue(coverage["bare-cell-visual-inspection"]["complete"])

    def test_an_activity_with_no_record_covers_nothing(self):
        records = [_record("bare-cell-visual-inspection")]
        coverage = activity_cell_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["bare-cell-mass-measurement"]["covered_cell_ids"], []
        )

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            activity_cell_coverage("records", DELIVERED)


class PackageTests(unittest.TestCase):
    def test_a_full_package_is_releasable(self):
        result = assess_acceptance_documentation(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_activity_recorded"])

    def test_a_missing_activity_is_named_and_blocks_release(self):
        records = [
            _record(a)
            for a in REQUIRED_ACCEPTANCE_RECORDS
            if a != "bare-cell-mass-measurement"
        ]
        result = assess_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["unrecorded_activities"], ["bare-cell-mass-measurement"]
        )

    def test_recorded_activity_fraction_is_reported(self):
        records = [
            _record(a)
            for a in REQUIRED_ACCEPTANCE_RECORDS
            if a != "bare-cell-mass-measurement"
        ]
        result = assess_acceptance_documentation(_package(records))
        self.assertAlmostEqual(
            result["recorded_activity_fraction"], 4.0 / 5.0, places=9
        )

    def test_a_full_package_records_every_activity(self):
        result = assess_acceptance_documentation(_package())
        self.assertAlmostEqual(result["recorded_activity_fraction"], 1.0, places=9)

    def test_an_uncovered_cell_blocks_release(self):
        records = [
            _record(a, cells=["cell-001", "cell-002"])
            for a in REQUIRED_ACCEPTANCE_RECORDS
        ]
        result = assess_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertIn(
            "cell-003",
            result["uncovered_cells_by_activity"]["bare-cell-mass-measurement"],
        )

    def test_cell_coverage_is_skipped_when_policy_drops_it(self):
        records = [
            _record(a, cells=["cell-001", "cell-002"])
            for a in REQUIRED_ACCEPTANCE_RECORDS
        ]
        policy = copy.deepcopy(DEFAULT_DOCUMENTATION_POLICY)
        policy["require_full_cell_coverage"] = False
        result = assess_acceptance_documentation(_package(records), policy)
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)

    def test_open_records_are_listed(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_RECORDS]
        records[0]["test_conditions"] = ""
        result = assess_acceptance_documentation(_package(records))
        self.assertEqual(
            result["open_record_ids"], ["rec-bare-cell-visual-inspection"]
        )

    def test_records_are_grouped_by_verdict(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_RECORDS]
        records[0]["cell_ids"] = ["cell-999"]
        result = assess_acceptance_documentation(_package(records))
        self.assertEqual(
            result["grouped_by_verdict"][RECORD_UNTRACEABLE],
            ["rec-bare-cell-visual-inspection"],
        )

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_acceptance_documentation(_package())
        ids = [entry["record_id"] for entry in result["record_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_repeated_record_identifier_rejected(self):
        records = [
            _record("bare-cell-visual-inspection", record_id="rec-1"),
            _record("bare-cell-mass-measurement", record_id="rec-1"),
        ]
        with self.assertRaises(ValueError):
            assess_acceptance_documentation(_package(records))

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_documentation(_package([]))

    def test_package_without_a_lot_identifier_rejected(self):
        package = _package()
        del package["lot_id"]
        with self.assertRaises(ValueError):
            assess_acceptance_documentation(package)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance_documentation([_record("bare-cell-visual-inspection")])

    def test_package_carries_every_record_finding(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_RECORDS]
        records[0]["equipment_calibration_ref"] = ""
        result = assess_acceptance_documentation(_package(records))
        self.assertTrue(
            any("equipment_calibration_ref" in f for f in result["findings"])
        )


if __name__ == "__main__":
    unittest.main()
