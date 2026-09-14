#!/usr/bin/env python3
"""Contract test for protection diode acceptance documentation, clause 9.4.6 (offline)."""

import copy
import unittest

from e2008_protection_diode_acceptance_documentation_logic import (
    ADMISSIBLE_RULE_SETS,
    DEFAULT_DIODE_DOCUMENTATION_POLICY,
    DELEGATED_RULE_SET,
    PACKAGE_NOT_RELEASABLE,
    PACKAGE_RELEASABLE,
    RECORD_COMPLETE,
    RECORD_FIELDS_MISSING,
    RECORD_UNAPPROVED,
    RECORD_UNTRACEABLE,
    REQUIRED_ACCEPTANCE_ACTIVITIES,
    REQUIRED_RECORD_FIELDS,
    activity_diode_coverage,
    applicable_record_fields,
    assess_acceptance_record,
    assess_diode_acceptance_documentation,
    audit_record_fields,
    record_approval_state,
    record_traceability,
    required_acceptance_activities,
    required_record_fields,
    resolve_governing_rule_set,
    validate_diode_documentation_policy,
)

DELIVERED = ["diode-001", "diode-002", "diode-003"]
LOCAL_RULES = "supplier-local-documentation-rules"


def _record(activity, record_id=None, diodes=None, **overrides):
    record = {
        "record_id": record_id or ("rec-%s" % activity),
        "activity": activity,
        "lot_id": "lot-d1",
        "diode_ids": list(diodes if diodes is not None else DELIVERED),
        "bias_conditions": "forward 1 A, reverse 30 V hold",
        "junction_temperature": "25 degrees celsius",
        "measured_results": "per-diode forward drop and leakage table attached",
        "equipment_calibration_ref": "cal-2026-0311",
        "performed_on": "2026-09-02",
        "approved_by": "quality-engineer-two",
        "approval_status": "approved",
    }
    record.update(overrides)
    return record


def _package(records=None, **overrides):
    package = {
        "lot_id": "lot-d1",
        "delivered_diode_ids": list(DELIVERED),
        "documentation_rule_set": DELEGATED_RULE_SET,
        "records": records
        if records is not None
        else [_record(activity) for activity in REQUIRED_ACCEPTANCE_ACTIVITIES],
    }
    package.update(overrides)
    return package


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_diode_documentation_policy(DEFAULT_DIODE_DOCUMENTATION_POLICY),
            DEFAULT_DIODE_DOCUMENTATION_POLICY,
        )

    def test_default_policy_demands_the_delegated_rule_set(self):
        self.assertTrue(
            DEFAULT_DIODE_DOCUMENTATION_POLICY["require_delegated_rule_set"]
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_diode_documentation_policy("write it all down")

    def test_out_of_range_activity_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_DOCUMENTATION_POLICY)
        broken["min_recorded_activity_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_diode_documentation_policy(broken)

    def test_non_boolean_coverage_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIODE_DOCUMENTATION_POLICY)
        broken["require_full_diode_coverage"] = "yes"
        with self.assertRaises(ValueError):
            validate_diode_documentation_policy(broken)


class RequiredSetTests(unittest.TestCase):
    def test_activity_set_is_returned_as_a_tuple_copy(self):
        activities = required_acceptance_activities()
        self.assertEqual(activities, REQUIRED_ACCEPTANCE_ACTIVITIES)
        self.assertIsInstance(activities, tuple)

    def test_field_set_is_returned_as_a_tuple_copy(self):
        fields = required_record_fields()
        self.assertEqual(fields, REQUIRED_RECORD_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_field_set_carries_bias_and_junction_temperature(self):
        fields = required_record_fields()
        self.assertIn("bias_conditions", fields)
        self.assertIn("junction_temperature", fields)


class RuleSetDelegationTests(unittest.TestCase):
    def test_the_delegated_rule_set_applies_every_field(self):
        self.assertEqual(
            applicable_record_fields(DELEGATED_RULE_SET), REQUIRED_RECORD_FIELDS
        )

    def test_a_local_rule_set_drops_the_diode_measurement_context(self):
        applied = applicable_record_fields(LOCAL_RULES)
        self.assertNotIn("bias_conditions", applied)
        self.assertNotIn("junction_temperature", applied)
        self.assertNotIn("equipment_calibration_ref", applied)

    def test_an_unknown_rule_set_rejected(self):
        with self.assertRaises(ValueError):
            applicable_record_fields("whatever-the-supplier-likes")

    def test_every_admissible_rule_set_resolves_a_field_set(self):
        for rule_set in ADMISSIBLE_RULE_SETS:
            self.assertTrue(applicable_record_fields(rule_set))

    def test_a_package_with_no_declaration_defaults_to_delegation(self):
        package = _package()
        del package["documentation_rule_set"]
        resolved = resolve_governing_rule_set(package)
        self.assertTrue(resolved["delegated"])
        self.assertEqual(resolved["findings"], [])

    def test_a_local_rule_set_is_reported_with_what_it_drops(self):
        resolved = resolve_governing_rule_set(
            _package(documentation_rule_set=LOCAL_RULES)
        )
        self.assertFalse(resolved["delegated"])
        self.assertIn("junction_temperature", resolved["dropped_fields"])
        self.assertTrue(resolved["findings"])

    def test_a_local_rule_set_stands_when_policy_admits_it(self):
        policy = copy.deepcopy(DEFAULT_DIODE_DOCUMENTATION_POLICY)
        policy["require_delegated_rule_set"] = False
        resolved = resolve_governing_rule_set(
            _package(documentation_rule_set=LOCAL_RULES), policy
        )
        self.assertEqual(resolved["findings"], [])

    def test_non_mapping_package_rejected_for_rule_resolution(self):
        with self.assertRaises(ValueError):
            resolve_governing_rule_set("the diode clause rules")


class FieldAuditTests(unittest.TestCase):
    def test_a_full_record_is_missing_nothing(self):
        self.assertEqual(
            audit_record_fields(_record("protection-diode-visual-inspection")), []
        )

    def test_a_dropped_bias_field_is_named(self):
        record = _record("protection-diode-visual-inspection", bias_conditions="")
        self.assertEqual(audit_record_fields(record), ["bias_conditions"])

    def test_a_missing_calibration_reference_is_named(self):
        record = _record("protection-diode-visual-inspection")
        del record["equipment_calibration_ref"]
        self.assertEqual(audit_record_fields(record), ["equipment_calibration_ref"])

    def test_an_empty_diode_list_is_named(self):
        record = _record("protection-diode-visual-inspection", diode_ids=[])
        self.assertEqual(audit_record_fields(record), ["diode_ids"])

    def test_a_local_rule_set_stops_asking_for_the_junction_temperature(self):
        record = _record("protection-diode-visual-inspection", junction_temperature="")
        self.assertEqual(audit_record_fields(record, LOCAL_RULES), [])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_record_fields("a record")


class TraceabilityTests(unittest.TestCase):
    def test_a_record_on_delivered_diodes_is_traceable(self):
        result = record_traceability(
            _record("protection-diode-dimensional-measurement"), DELIVERED
        )
        self.assertTrue(result["traceable"])
        self.assertEqual(result["foreign_diode_ids"], [])

    def test_a_foreign_diode_is_named(self):
        record = _record(
            "protection-diode-dimensional-measurement",
            diodes=["diode-001", "diode-999"],
        )
        result = record_traceability(record, DELIVERED)
        self.assertFalse(result["traceable"])
        self.assertEqual(result["foreign_diode_ids"], ["diode-999"])

    def test_covered_diodes_are_the_intersection(self):
        record = _record(
            "protection-diode-dimensional-measurement",
            diodes=["diode-001", "diode-999"],
        )
        result = record_traceability(record, DELIVERED)
        self.assertEqual(result["covered_diode_ids"], ["diode-001"])

    def test_empty_delivered_list_rejected(self):
        with self.assertRaises(ValueError):
            record_traceability(
                _record("protection-diode-dimensional-measurement"), []
            )


class RecordVerdictTests(unittest.TestCase):
    def test_a_full_record_is_complete(self):
        result = assess_acceptance_record(
            _record("protection-diode-visual-inspection"), DELIVERED
        )
        self.assertEqual(result["verdict"], RECORD_COMPLETE)
        self.assertTrue(result["complete"])

    def test_a_foreign_diode_outranks_a_missing_field(self):
        record = _record(
            "protection-diode-visual-inspection",
            diodes=["diode-999"],
            bias_conditions="",
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNTRACEABLE)

    def test_a_missing_field_outranks_a_missing_approval(self):
        record = _record(
            "protection-diode-visual-inspection",
            junction_temperature="",
            approval_status="pending",
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_FIELDS_MISSING)

    def test_a_full_but_still_pending_record_is_unapproved(self):
        record = _record(
            "protection-diode-visual-inspection", approval_status="pending"
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)
        self.assertFalse(result["approved"])

    def test_a_pending_record_stands_when_policy_drops_the_signature(self):
        record = _record(
            "protection-diode-visual-inspection", approval_status="pending"
        )
        policy = copy.deepcopy(DEFAULT_DIODE_DOCUMENTATION_POLICY)
        policy["require_approval_signature"] = False
        result = assess_acceptance_record(
            record, DELIVERED, DELEGATED_RULE_SET, policy
        )
        self.assertEqual(result["verdict"], RECORD_COMPLETE)

    def test_a_withdrawn_record_is_not_approved(self):
        record = _record(
            "protection-diode-visual-inspection", approval_status="withdrawn"
        )
        result = assess_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)

    def test_an_unknown_activity_rejected(self):
        record = _record("protection-diode-visual-inspection")
        record["activity"] = "diode-taste-test"
        with self.assertRaises(ValueError):
            assess_acceptance_record(record, DELIVERED)

    def test_a_record_without_an_identifier_rejected(self):
        record = _record("protection-diode-visual-inspection")
        del record["record_id"]
        with self.assertRaises(ValueError):
            assess_acceptance_record(record, DELIVERED)

    def test_findings_name_the_record(self):
        record = _record("protection-diode-visual-inspection", bias_conditions="")
        result = assess_acceptance_record(record, DELIVERED)
        self.assertTrue(any("rec-protection-diode" in f for f in result["findings"]))


class ApprovalStateTests(unittest.TestCase):
    def test_a_record_with_no_status_is_pending(self):
        record = _record("protection-diode-visual-inspection")
        del record["approval_status"]
        self.assertEqual(record_approval_state(record), "pending")

    def test_an_approved_record_reads_back(self):
        self.assertEqual(
            record_approval_state(_record("protection-diode-visual-inspection")),
            "approved",
        )

    def test_an_unknown_approval_state_rejected(self):
        record = _record(
            "protection-diode-visual-inspection", approval_status="rubber-stamped"
        )
        with self.assertRaises(ValueError):
            record_approval_state(record)

    def test_non_mapping_record_rejected_for_approval_state(self):
        with self.assertRaises(ValueError):
            record_approval_state("approved")


class CoverageTests(unittest.TestCase):
    def test_every_delivered_diode_is_reached(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_ACTIVITIES]
        coverage = activity_diode_coverage(records, DELIVERED)
        self.assertTrue(all(entry["complete"] for entry in coverage.values()))

    def test_an_unreached_diode_is_named(self):
        records = [
            _record(a, diodes=["diode-001", "diode-002"])
            for a in REQUIRED_ACCEPTANCE_ACTIVITIES
        ]
        coverage = activity_diode_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["protection-diode-dimensional-measurement"][
                "uncovered_diode_ids"
            ],
            ["diode-003"],
        )

    def test_two_records_together_cover_an_activity(self):
        records = [
            _record(
                "protection-diode-visual-inspection",
                record_id="rec-1",
                diodes=["diode-001"],
            ),
            _record(
                "protection-diode-visual-inspection",
                record_id="rec-2",
                diodes=["diode-002", "diode-003"],
            ),
        ]
        coverage = activity_diode_coverage(records, DELIVERED)
        self.assertTrue(coverage["protection-diode-visual-inspection"]["complete"])

    def test_an_activity_with_no_record_covers_nothing(self):
        records = [_record("protection-diode-visual-inspection")]
        coverage = activity_diode_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["protection-diode-reverse-leakage-measurement"][
                "covered_diode_ids"
            ],
            [],
        )

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            activity_diode_coverage("records", DELIVERED)


class PackageTests(unittest.TestCase):
    def test_a_full_package_is_releasable(self):
        result = assess_diode_acceptance_documentation(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_activity_recorded"])

    def test_a_local_rule_set_alone_blocks_release(self):
        result = assess_diode_acceptance_documentation(
            _package(documentation_rule_set=LOCAL_RULES)
        )
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertFalse(result["rule_set"]["delegated"])

    def test_a_missing_activity_is_named_and_blocks_release(self):
        records = [
            _record(a)
            for a in REQUIRED_ACCEPTANCE_ACTIVITIES
            if a != "protection-diode-reverse-leakage-measurement"
        ]
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["unrecorded_activities"],
            ["protection-diode-reverse-leakage-measurement"],
        )

    def test_recorded_activity_fraction_is_reported(self):
        records = [
            _record(a)
            for a in REQUIRED_ACCEPTANCE_ACTIVITIES
            if a != "protection-diode-reverse-leakage-measurement"
        ]
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertAlmostEqual(
            result["recorded_activity_fraction"], 4.0 / 5.0, places=9
        )

    def test_a_full_package_records_every_activity(self):
        result = assess_diode_acceptance_documentation(_package())
        self.assertAlmostEqual(result["recorded_activity_fraction"], 1.0, places=9)

    def test_an_uncovered_diode_blocks_release(self):
        records = [
            _record(a, diodes=["diode-001", "diode-002"])
            for a in REQUIRED_ACCEPTANCE_ACTIVITIES
        ]
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertIn(
            "diode-003",
            result["uncovered_diodes_by_activity"][
                "protection-diode-dimensional-measurement"
            ],
        )

    def test_diode_coverage_is_skipped_when_policy_drops_it(self):
        records = [
            _record(a, diodes=["diode-001", "diode-002"])
            for a in REQUIRED_ACCEPTANCE_ACTIVITIES
        ]
        policy = copy.deepcopy(DEFAULT_DIODE_DOCUMENTATION_POLICY)
        policy["require_full_diode_coverage"] = False
        result = assess_diode_acceptance_documentation(_package(records), policy)
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)

    def test_open_records_are_listed(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_ACTIVITIES]
        records[0]["bias_conditions"] = ""
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertEqual(
            result["open_record_ids"], ["rec-protection-diode-visual-inspection"]
        )

    def test_records_are_grouped_by_verdict(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_ACTIVITIES]
        records[0]["diode_ids"] = ["diode-999"]
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertEqual(
            result["grouped_by_verdict"][RECORD_UNTRACEABLE],
            ["rec-protection-diode-visual-inspection"],
        )

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_diode_acceptance_documentation(_package())
        ids = [entry["record_id"] for entry in result["record_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_repeated_record_identifier_rejected(self):
        records = [
            _record("protection-diode-visual-inspection", record_id="rec-1"),
            _record("protection-diode-dimensional-measurement", record_id="rec-1"),
        ]
        with self.assertRaises(ValueError):
            assess_diode_acceptance_documentation(_package(records))

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_acceptance_documentation(_package([]))

    def test_package_without_a_lot_identifier_rejected(self):
        package = _package()
        del package["lot_id"]
        with self.assertRaises(ValueError):
            assess_diode_acceptance_documentation(package)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_acceptance_documentation(
                [_record("protection-diode-visual-inspection")]
            )

    def test_package_carries_every_record_finding(self):
        records = [_record(a) for a in REQUIRED_ACCEPTANCE_ACTIVITIES]
        records[0]["equipment_calibration_ref"] = ""
        result = assess_diode_acceptance_documentation(_package(records))
        self.assertTrue(
            any("equipment_calibration_ref" in f for f in result["findings"])
        )


if __name__ == "__main__":
    unittest.main()
