#!/usr/bin/env python3
"""Contract test for coverglass acceptance documentation, clause 8.5.4 (offline)."""

import copy
import unittest

from e2008_coverglass_acceptance_documentation_logic import (
    DEFAULT_COVERGLASS_DOCUMENTATION_RULES,
    EDITION_CURRENT,
    EDITION_SUPERSEDED,
    PACKAGE_NOT_RELEASABLE,
    PACKAGE_RELEASABLE,
    RECORD_CONFORMANT,
    RECORD_EDITION_SUPERSEDED,
    RECORD_FIELDS_MISSING,
    RECORD_OUTSIDE_BATCH,
    RECORD_RETENTION_SHORT,
    RECORD_UNAPPROVED,
    REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES,
    REQUIRED_COVERGLASS_RECORD_FIELDS,
    activity_sample_coverage,
    assess_coverglass_acceptance_documentation,
    assess_coverglass_acceptance_record,
    audit_record_fields,
    record_approval_state,
    record_batch_traceability,
    record_retention,
    record_rule_edition,
    required_coverglass_acceptance_activities,
    required_coverglass_record_fields,
    validate_documentation_rules,
)

DELIVERED = ["cg-001", "cg-002", "cg-003"]
CURRENT_EDITION = DEFAULT_COVERGLASS_DOCUMENTATION_RULES["rule_edition"]
OLD_EDITION = DEFAULT_COVERGLASS_DOCUMENTATION_RULES["superseded_editions"][0]


def _record(activity, record_id=None, pieces=None, **overrides):
    record = {
        "record_id": record_id or ("cgr-%s" % activity),
        "activity": activity,
        "batch_id": "batch-a",
        "coverglass_ids": list(pieces if pieces is not None else DELIVERED),
        "documentation_rule_edition": CURRENT_EDITION,
        "test_conditions": "AM0 spectrum, 25 degrees celsius, normal incidence",
        "measured_results": "per-piece transmittance and thickness table attached",
        "measurement_uncertainty": "plus or minus 0.4 percent, coverage factor two",
        "equipment_calibration_ref": "cal-2026-0771",
        "performed_on": "2026-09-02",
        "approved_by": "quality-engineer-two",
        "approval_status": "approved",
        "retention_years": 12.0,
    }
    record.update(overrides)
    return record


def _package(records=None, **overrides):
    package = {
        "batch_id": "batch-a",
        "delivered_coverglass_ids": list(DELIVERED),
        "records": records
        if records is not None
        else [
            _record(activity)
            for activity in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ],
    }
    package.update(overrides)
    return package


class DocumentationRuleTests(unittest.TestCase):
    def test_default_rules_validate(self):
        self.assertIs(
            validate_documentation_rules(DEFAULT_COVERGLASS_DOCUMENTATION_RULES),
            DEFAULT_COVERGLASS_DOCUMENTATION_RULES,
        )

    def test_default_rules_refuse_a_summary_for_results(self):
        self.assertFalse(
            DEFAULT_COVERGLASS_DOCUMENTATION_RULES[
                "admit_summary_in_place_of_results"
            ]
        )

    def test_non_mapping_rule_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_documentation_rules("write it all down")

    def test_governing_edition_also_listed_superseded_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        broken["superseded_editions"] = (broken["rule_edition"],)
        with self.assertRaises(ValueError):
            validate_documentation_rules(broken)

    def test_negative_retention_period_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        broken["min_retention_years"] = -1.0
        with self.assertRaises(ValueError):
            validate_documentation_rules(broken)

    def test_out_of_range_activity_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        broken["min_recorded_activity_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_documentation_rules(broken)

    def test_non_boolean_coverage_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        broken["require_full_sample_coverage"] = "yes"
        with self.assertRaises(ValueError):
            validate_documentation_rules(broken)


class RequiredSetTests(unittest.TestCase):
    def test_activity_set_is_returned_as_a_tuple_copy(self):
        activities = required_coverglass_acceptance_activities()
        self.assertEqual(activities, REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES)
        self.assertIsInstance(activities, tuple)

    def test_field_set_is_returned_as_a_tuple_copy(self):
        fields = required_coverglass_record_fields()
        self.assertEqual(fields, REQUIRED_COVERGLASS_RECORD_FIELDS)
        self.assertIsInstance(fields, tuple)

    def test_field_set_carries_uncertainty_and_rule_edition(self):
        fields = required_coverglass_record_fields()
        self.assertIn("measurement_uncertainty", fields)
        self.assertIn("documentation_rule_edition", fields)

    def test_transmittance_is_an_acceptance_activity(self):
        self.assertIn(
            "coverglass-solar-transmittance-measurement",
            required_coverglass_acceptance_activities(),
        )


class FieldAuditTests(unittest.TestCase):
    def test_a_full_record_is_missing_nothing(self):
        self.assertEqual(
            audit_record_fields(_record("coverglass-visual-inspection")), []
        )

    def test_a_dropped_condition_field_is_named(self):
        record = _record("coverglass-visual-inspection", test_conditions="")
        self.assertEqual(audit_record_fields(record), ["test_conditions"])

    def test_a_missing_calibration_reference_is_named(self):
        record = _record("coverglass-visual-inspection")
        del record["equipment_calibration_ref"]
        self.assertEqual(audit_record_fields(record), ["equipment_calibration_ref"])

    def test_a_missing_uncertainty_is_named_by_default(self):
        record = _record("coverglass-visual-inspection", measurement_uncertainty="")
        self.assertEqual(audit_record_fields(record), ["measurement_uncertainty"])

    def test_uncertainty_stands_down_when_the_rules_drop_it(self):
        record = _record("coverglass-visual-inspection", measurement_uncertainty="")
        rules = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        rules["require_measurement_uncertainty"] = False
        self.assertEqual(audit_record_fields(record, rules), [])

    def test_an_empty_piece_list_is_named(self):
        record = _record("coverglass-visual-inspection", coverglass_ids=[])
        self.assertEqual(audit_record_fields(record), ["coverglass_ids"])

    def test_missing_results_stand_when_the_rules_admit_a_summary(self):
        record = _record("coverglass-visual-inspection", measured_results="")
        rules = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        rules["admit_summary_in_place_of_results"] = True
        self.assertEqual(audit_record_fields(record, rules), [])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            audit_record_fields("a record")


class RuleEditionTests(unittest.TestCase):
    def test_a_record_on_the_governing_edition_reads_current(self):
        self.assertEqual(
            record_rule_edition(_record("coverglass-thickness-measurement")),
            EDITION_CURRENT,
        )

    def test_a_record_on_a_retired_edition_reads_superseded(self):
        record = _record(
            "coverglass-thickness-measurement",
            documentation_rule_edition=OLD_EDITION,
        )
        self.assertEqual(record_rule_edition(record), EDITION_SUPERSEDED)

    def test_an_edition_the_rule_set_never_heard_of_is_rejected(self):
        record = _record(
            "coverglass-thickness-measurement",
            documentation_rule_edition="test-house-template-4",
        )
        with self.assertRaises(ValueError):
            record_rule_edition(record)

    def test_a_record_with_no_edition_cited_rejected(self):
        record = _record("coverglass-thickness-measurement")
        del record["documentation_rule_edition"]
        with self.assertRaises(ValueError):
            record_rule_edition(record)


class RetentionTests(unittest.TestCase):
    def test_a_long_retention_period_is_sufficient(self):
        result = record_retention(_record("coverglass-coating-adhesion-test"))
        self.assertTrue(result["sufficient"])

    def test_a_retention_period_exactly_on_the_bound_is_sufficient(self):
        record = _record("coverglass-coating-adhesion-test", retention_years=10.0)
        result = record_retention(record)
        self.assertTrue(result["sufficient"])
        self.assertAlmostEqual(
            result["declared_retention_years"],
            result["required_retention_years"],
            places=9,
        )

    def test_a_short_retention_period_is_insufficient(self):
        record = _record("coverglass-coating-adhesion-test", retention_years=3.0)
        self.assertFalse(record_retention(record)["sufficient"])

    def test_an_undeclared_retention_period_reads_as_none_held(self):
        record = _record("coverglass-coating-adhesion-test")
        del record["retention_years"]
        result = record_retention(record)
        self.assertAlmostEqual(result["declared_retention_years"], 0.0, places=9)
        self.assertFalse(result["sufficient"])

    def test_a_non_numeric_retention_period_rejected(self):
        record = _record("coverglass-coating-adhesion-test", retention_years="ten")
        with self.assertRaises(ValueError):
            record_retention(record)


class TraceabilityTests(unittest.TestCase):
    def test_a_record_on_delivered_pieces_is_traceable(self):
        result = record_batch_traceability(
            _record("coverglass-dimensional-measurement"), DELIVERED
        )
        self.assertTrue(result["traceable"])
        self.assertEqual(result["foreign_coverglass_ids"], [])

    def test_a_foreign_piece_is_named(self):
        record = _record(
            "coverglass-dimensional-measurement", pieces=["cg-001", "cg-999"]
        )
        result = record_batch_traceability(record, DELIVERED)
        self.assertFalse(result["traceable"])
        self.assertEqual(result["foreign_coverglass_ids"], ["cg-999"])

    def test_covered_pieces_are_the_intersection(self):
        record = _record(
            "coverglass-dimensional-measurement", pieces=["cg-001", "cg-999"]
        )
        result = record_batch_traceability(record, DELIVERED)
        self.assertEqual(result["covered_coverglass_ids"], ["cg-001"])

    def test_empty_delivered_list_rejected(self):
        with self.assertRaises(ValueError):
            record_batch_traceability(
                _record("coverglass-dimensional-measurement"), []
            )


class RecordVerdictTests(unittest.TestCase):
    def test_a_full_record_is_conformant(self):
        result = assess_coverglass_acceptance_record(
            _record("coverglass-visual-inspection"), DELIVERED
        )
        self.assertEqual(result["verdict"], RECORD_CONFORMANT)
        self.assertTrue(result["conformant"])

    def test_a_foreign_piece_outranks_a_superseded_edition(self):
        record = _record(
            "coverglass-visual-inspection",
            pieces=["cg-999"],
            documentation_rule_edition=OLD_EDITION,
        )
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_OUTSIDE_BATCH)

    def test_a_superseded_edition_outranks_a_missing_field(self):
        record = _record(
            "coverglass-visual-inspection",
            documentation_rule_edition=OLD_EDITION,
            test_conditions="",
        )
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_EDITION_SUPERSEDED)

    def test_a_missing_field_outranks_a_short_retention_period(self):
        record = _record(
            "coverglass-visual-inspection", test_conditions="", retention_years=1.0
        )
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_FIELDS_MISSING)

    def test_a_short_retention_period_outranks_a_pending_approval(self):
        record = _record(
            "coverglass-visual-inspection",
            retention_years=2.0,
            approval_status="pending",
        )
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_RETENTION_SHORT)

    def test_a_full_but_still_pending_record_is_unapproved(self):
        record = _record("coverglass-visual-inspection", approval_status="pending")
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)
        self.assertFalse(result["approved"])

    def test_a_pending_record_stands_when_the_rules_drop_the_signature(self):
        record = _record("coverglass-visual-inspection", approval_status="pending")
        rules = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        rules["require_approval_signature"] = False
        result = assess_coverglass_acceptance_record(record, DELIVERED, rules)
        self.assertEqual(result["verdict"], RECORD_CONFORMANT)

    def test_a_withdrawn_record_is_not_approved(self):
        record = _record("coverglass-visual-inspection", approval_status="withdrawn")
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertEqual(result["verdict"], RECORD_UNAPPROVED)

    def test_an_unknown_activity_rejected(self):
        record = _record("coverglass-visual-inspection")
        record["activity"] = "coverglass-taste-test"
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_record(record, DELIVERED)

    def test_a_record_without_an_identifier_rejected(self):
        record = _record("coverglass-visual-inspection")
        del record["record_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_record(record, DELIVERED)

    def test_findings_name_the_record(self):
        record = _record("coverglass-visual-inspection", test_conditions="")
        result = assess_coverglass_acceptance_record(record, DELIVERED)
        self.assertTrue(
            any("cgr-coverglass-visual" in f for f in result["findings"])
        )


class ApprovalStateTests(unittest.TestCase):
    def test_a_record_with_no_status_is_pending(self):
        record = _record("coverglass-visual-inspection")
        del record["approval_status"]
        self.assertEqual(record_approval_state(record), "pending")

    def test_an_approved_record_reads_back(self):
        self.assertEqual(
            record_approval_state(_record("coverglass-visual-inspection")),
            "approved",
        )

    def test_an_unknown_approval_state_rejected(self):
        record = _record(
            "coverglass-visual-inspection", approval_status="rubber-stamped"
        )
        with self.assertRaises(ValueError):
            record_approval_state(record)

    def test_non_mapping_record_rejected_for_approval_state(self):
        with self.assertRaises(ValueError):
            record_approval_state("approved")


class CoverageTests(unittest.TestCase):
    def test_every_delivered_piece_is_reached(self):
        records = [
            _record(a) for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        coverage = activity_sample_coverage(records, DELIVERED)
        self.assertTrue(all(entry["complete"] for entry in coverage.values()))

    def test_an_unreached_piece_is_named(self):
        records = [
            _record(a, pieces=["cg-001", "cg-002"])
            for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        coverage = activity_sample_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["coverglass-thickness-measurement"][
                "uncovered_coverglass_ids"
            ],
            ["cg-003"],
        )

    def test_two_records_together_cover_an_activity(self):
        records = [
            _record(
                "coverglass-visual-inspection",
                record_id="cgr-1",
                pieces=["cg-001"],
            ),
            _record(
                "coverglass-visual-inspection",
                record_id="cgr-2",
                pieces=["cg-002", "cg-003"],
            ),
        ]
        coverage = activity_sample_coverage(records, DELIVERED)
        self.assertTrue(coverage["coverglass-visual-inspection"]["complete"])

    def test_an_activity_with_no_record_covers_nothing(self):
        records = [_record("coverglass-visual-inspection")]
        coverage = activity_sample_coverage(records, DELIVERED)
        self.assertEqual(
            coverage["coverglass-coating-adhesion-test"][
                "covered_coverglass_ids"
            ],
            [],
        )

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            activity_sample_coverage("records", DELIVERED)


class PackageTests(unittest.TestCase):
    def test_a_full_package_is_releasable(self):
        result = assess_coverglass_acceptance_documentation(_package())
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["every_activity_recorded"])

    def test_the_governing_edition_is_reported(self):
        result = assess_coverglass_acceptance_documentation(_package())
        self.assertEqual(result["governing_rule_edition"], CURRENT_EDITION)

    def test_a_missing_activity_is_named_and_blocks_release(self):
        records = [
            _record(a)
            for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
            if a != "coverglass-coating-adhesion-test"
        ]
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["unrecorded_activities"], ["coverglass-coating-adhesion-test"]
        )

    def test_recorded_activity_fraction_is_reported(self):
        records = [
            _record(a)
            for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
            if a != "coverglass-coating-adhesion-test"
        ]
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertAlmostEqual(
            result["recorded_activity_fraction"], 5.0 / 6.0, places=9
        )

    def test_a_full_package_records_every_activity(self):
        result = assess_coverglass_acceptance_documentation(_package())
        self.assertAlmostEqual(result["recorded_activity_fraction"], 1.0, places=9)

    def test_an_uncovered_piece_blocks_release(self):
        records = [
            _record(a, pieces=["cg-001", "cg-002"])
            for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertIn(
            "cg-003",
            result["uncovered_samples_by_activity"][
                "coverglass-thickness-measurement"
            ],
        )

    def test_sample_coverage_is_skipped_when_the_rules_drop_it(self):
        records = [
            _record(a, pieces=["cg-001", "cg-002"])
            for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        rules = copy.deepcopy(DEFAULT_COVERGLASS_DOCUMENTATION_RULES)
        rules["require_full_sample_coverage"] = False
        result = assess_coverglass_acceptance_documentation(
            _package(records), rules
        )
        self.assertEqual(result["verdict"], PACKAGE_RELEASABLE)

    def test_open_records_are_listed(self):
        records = [
            _record(a) for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        records[0]["test_conditions"] = ""
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertEqual(
            result["open_record_ids"], ["cgr-coverglass-visual-inspection"]
        )

    def test_records_are_grouped_by_verdict(self):
        records = [
            _record(a) for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        records[0]["coverglass_ids"] = ["cg-999"]
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertEqual(
            result["grouped_by_verdict"][RECORD_OUTSIDE_BATCH],
            ["cgr-coverglass-visual-inspection"],
        )

    def test_a_superseded_edition_blocks_release(self):
        records = [
            _record(a) for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        records[0]["documentation_rule_edition"] = OLD_EDITION
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertEqual(result["verdict"], PACKAGE_NOT_RELEASABLE)
        self.assertEqual(
            result["grouped_by_verdict"][RECORD_EDITION_SUPERSEDED],
            ["cgr-coverglass-visual-inspection"],
        )

    def test_assessments_come_back_in_identifier_order(self):
        result = assess_coverglass_acceptance_documentation(_package())
        ids = [entry["record_id"] for entry in result["record_assessments"]]
        self.assertEqual(ids, sorted(ids))

    def test_repeated_record_identifier_rejected(self):
        records = [
            _record("coverglass-visual-inspection", record_id="cgr-1"),
            _record("coverglass-thickness-measurement", record_id="cgr-1"),
        ]
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_documentation(_package(records))

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_documentation(_package([]))

    def test_package_without_a_batch_identifier_rejected(self):
        package = _package()
        del package["batch_id"]
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_documentation(package)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_acceptance_documentation(
                [_record("coverglass-visual-inspection")]
            )

    def test_package_carries_every_record_finding(self):
        records = [
            _record(a) for a in REQUIRED_COVERGLASS_ACCEPTANCE_ACTIVITIES
        ]
        records[0]["equipment_calibration_ref"] = ""
        result = assess_coverglass_acceptance_documentation(_package(records))
        self.assertTrue(
            any("equipment_calibration_ref" in f for f in result["findings"])
        )


if __name__ == "__main__":
    unittest.main()
