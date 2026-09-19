#!/usr/bin/env python3
"""Contract tests for documentation, records and data control, clause 5.2.1.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused policy,
control never established, an unapproved issue in circulation, a
superseded issue still on the floor, two approved issues circulating at
once, a record disposed of before its retention elapsed, a retention
declared under the centre floor, a test-data set with no integrity
evidence, no backup or a traceability pointer at nothing, and a
circulating issue past its review age.
"""

import unittest

from q2007_documentation_logic import (
    CATEGORY_CALIBRATION,
    CATEGORY_TEST_REPORT,
    CONTROL_ABSENT,
    DAYS_PER_YEAR,
    DEFAULT_CONTROL_POLICY,
    DOCUMENTATION_CONTROLLED,
    DOCUMENT_APPROVAL_BROKEN,
    DOC_APPROVED,
    DOC_DRAFT,
    DOC_SUPERSEDED,
    DOC_WITHDRAWN,
    ISSUE_CONTROL_BROKEN,
    RECORDS_RETENTION_BROKEN,
    TEST_DATA_CONTROL_BROKEN,
    assess_documentation_control,
    at_least,
    data_control_gaps,
    documents_past_review,
    issue_collisions,
    premature_disposals,
    retention_shortfalls,
    superseded_in_circulation,
    unapproved_in_circulation,
    validate_control_policy,
    validate_control_system,
    validate_dataset,
    validate_document,
    validate_record,
    years_to_days,
)


def _document(document_id="TC-PROC-01", **overrides):
    record = {
        "document_id": document_id,
        "issue": 3,
        "state": DOC_APPROVED,
        "in_circulation": True,
        "approved_on_day": 1500,
        "issued_on_day": 1505,
    }
    record.update(overrides)
    return record


def _record(record_id="REC-0001", **overrides):
    row = {
        "record_id": record_id,
        "category": CATEGORY_TEST_REPORT,
        "created_on_day": 100,
        "retention_years": 10.0,
        "disposed_on_day": None,
    }
    row.update(overrides)
    return row


def _dataset(dataset_id="DS-0001", **overrides):
    row = {
        "dataset_id": dataset_id,
        "integrity_evidence": True,
        "backup_held": True,
        "traces_to_record": "REC-0001",
    }
    row.update(overrides)
    return row


def _control(**overrides):
    system = {
        "established": True,
        "documents": [_document("TC-PROC-01"), _document("TC-PROC-02", issue=1)],
        "records": [_record("REC-0001"), _record("REC-0002", category=CATEGORY_CALIBRATION)],
        "datasets": [_dataset("DS-0001"), _dataset("DS-0002", traces_to_record="REC-0002")],
        "as_of_day": 2000,
    }
    system.update(overrides)
    return system


def _case(**overrides):
    case = {"control": _control(), "policy": dict(DEFAULT_CONTROL_POLICY)}
    case.update(overrides)
    return case


class ControlPolicyValidation(unittest.TestCase):
    def test_default_policy_round_trips(self):
        rules = validate_control_policy({})
        self.assertAlmostEqual(rules["min_retention_years"], 5.0, places=9)
        self.assertTrue(rules["require_traceability"])

    def test_unrecognised_policy_key_refused(self):
        with self.assertRaises(ValueError):
            validate_control_policy({"retention": 5})

    def test_non_positive_retention_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_control_policy({"min_retention_years": 0.0})

    def test_non_whole_review_interval_refused(self):
        with self.assertRaises(ValueError):
            validate_control_policy({"document_review_interval_days": 365.5})

    def test_non_boolean_backup_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_control_policy({"require_backup": 1})


class RecordValidation(unittest.TestCase):
    def test_document_missing_field_refused(self):
        bad = _document()
        del bad["issue"]
        with self.assertRaises(ValueError):
            validate_document(bad)

    def test_issue_zero_refused(self):
        with self.assertRaises(ValueError):
            validate_document(_document(issue=0))

    def test_issued_before_approved_refused(self):
        with self.assertRaises(ValueError):
            validate_document(_document(approved_on_day=1500, issued_on_day=1400))

    def test_unrecognised_document_state_refused(self):
        with self.assertRaises(ValueError):
            validate_document(_document(state="circulating"))

    def test_unrecognised_record_category_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_record(category="shipping-note"))

    def test_record_disposed_before_creation_refused(self):
        with self.assertRaises(ValueError):
            validate_record(_record(created_on_day=200, disposed_on_day=100))

    def test_dataset_missing_field_refused(self):
        bad = _dataset()
        del bad["backup_held"]
        with self.assertRaises(ValueError):
            validate_dataset(bad)

    def test_duplicate_document_issue_refused(self):
        control = _control(documents=[_document("TC-PROC-01"), _document("TC-PROC-01")])
        with self.assertRaises(ValueError):
            validate_control_system(control)

    def test_duplicate_record_id_refused(self):
        control = _control(records=[_record("REC-0001"), _record("REC-0001")])
        with self.assertRaises(ValueError):
            validate_control_system(control)

    def test_document_day_after_assessment_day_refused(self):
        control = _control(documents=[_document(issued_on_day=2500, approved_on_day=2400)])
        with self.assertRaises(ValueError):
            validate_control_system(control)

    def test_non_mapping_control_refused(self):
        with self.assertRaises(ValueError):
            validate_control_system(["established"])


class UnitConversion(unittest.TestCase):
    def test_years_to_days_uses_one_named_factor(self):
        self.assertAlmostEqual(years_to_days(4.0), 4.0 * DAYS_PER_YEAR, places=9)

    def test_zero_years_is_zero_days(self):
        self.assertAlmostEqual(years_to_days(0.0), 0.0, places=9)

    def test_negative_retention_years_refused(self):
        with self.assertRaises(ValueError):
            years_to_days(-1.0)

    def test_at_least_accepts_an_exact_equality(self):
        self.assertTrue(at_least(years_to_days(4.0), years_to_days(4.0)))

    def test_at_least_rejects_a_real_shortfall(self):
        self.assertFalse(at_least(years_to_days(3.0), years_to_days(4.0)))


class DocumentControl(unittest.TestCase):
    def test_a_clean_register_has_no_approval_gaps(self):
        self.assertEqual(unapproved_in_circulation(_control()), [])

    def test_a_draft_in_circulation_is_an_approval_gap(self):
        control = _control(
            documents=[_document(state=DOC_DRAFT, approved_on_day=None, issued_on_day=None)]
        )
        self.assertEqual(unapproved_in_circulation(control), ["TC-PROC-01/3"])

    def test_a_draft_not_in_circulation_is_not_a_gap(self):
        control = _control(
            documents=[
                _document(
                    state=DOC_DRAFT,
                    in_circulation=False,
                    approved_on_day=None,
                    issued_on_day=None,
                )
            ]
        )
        self.assertEqual(unapproved_in_circulation(control), [])

    def test_a_superseded_issue_on_the_floor_is_named(self):
        control = _control(
            documents=[
                _document("TC-PROC-01", issue=3),
                _document("TC-PROC-01", issue=2, state=DOC_SUPERSEDED),
            ]
        )
        self.assertEqual(superseded_in_circulation(control), ["TC-PROC-01/2"])

    def test_a_withdrawn_issue_on_the_shelf_is_not_named(self):
        control = _control(
            documents=[
                _document("TC-PROC-01", issue=3),
                _document("TC-PROC-01", issue=2, state=DOC_WITHDRAWN, in_circulation=False),
            ]
        )
        self.assertEqual(superseded_in_circulation(control), [])

    def test_a_withdrawn_issue_still_circulating_is_named(self):
        control = _control(
            documents=[
                _document("TC-PROC-01", issue=3),
                _document("TC-PROC-01", issue=2, state=DOC_WITHDRAWN),
            ]
        )
        self.assertEqual(superseded_in_circulation(control), ["TC-PROC-01/2"])
        self.assertEqual(unapproved_in_circulation(control), [])

    def test_two_approved_issues_in_circulation_collide(self):
        control = _control(
            documents=[
                _document("TC-PROC-01", issue=3),
                _document("TC-PROC-01", issue=4),
            ]
        )
        self.assertEqual(issue_collisions(control), ["TC-PROC-01"])

    def test_an_issue_exactly_at_the_review_age_is_not_past_review(self):
        control = _control(
            as_of_day=2000,
            documents=[_document(approved_on_day=900, issued_on_day=905)],
        )
        self.assertEqual(documents_past_review(control, {}), [])

    def test_an_issue_one_day_past_the_review_age_is_named(self):
        control = _control(
            as_of_day=2000,
            documents=[_document(approved_on_day=900, issued_on_day=904)],
        )
        self.assertEqual(documents_past_review(control, {}), ["TC-PROC-01/3"])


class RetentionAndData(unittest.TestCase):
    def test_a_retention_under_the_floor_is_a_shortfall(self):
        control = _control(records=[_record(retention_years=2.0)])
        self.assertEqual(retention_shortfalls(control, {}), ["REC-0001"])

    def test_a_retention_exactly_at_the_floor_is_not_a_shortfall(self):
        control = _control(records=[_record(retention_years=5.0)])
        self.assertEqual(retention_shortfalls(control, {}), [])

    def test_a_record_disposed_of_early_is_named(self):
        control = _control(
            records=[_record(created_on_day=0, retention_years=10.0, disposed_on_day=100)]
        )
        self.assertEqual(premature_disposals(control), ["REC-0001"])

    def test_a_record_disposed_of_exactly_at_its_retention_is_not_named(self):
        held = int(round(years_to_days(4.0)))
        control = _control(
            records=[_record(created_on_day=0, retention_years=4.0, disposed_on_day=held)]
        )
        self.assertAlmostEqual(float(held), years_to_days(4.0), places=9)
        self.assertEqual(premature_disposals(control), [])

    def test_a_record_still_held_is_never_a_premature_disposal(self):
        self.assertEqual(premature_disposals(_control()), [])

    def test_a_dataset_without_integrity_evidence_is_a_gap(self):
        control = _control(datasets=[_dataset(integrity_evidence=False)])
        self.assertEqual(data_control_gaps(control, {}), [("DS-0001", ["integrity-evidence"])])

    def test_a_dataset_without_a_backup_is_a_gap(self):
        control = _control(datasets=[_dataset(backup_held=False)])
        self.assertEqual(data_control_gaps(control, {}), [("DS-0001", ["backup"])])

    def test_a_dataset_pointing_at_no_record_is_a_traceability_gap(self):
        control = _control(datasets=[_dataset(traces_to_record=None)])
        self.assertEqual(data_control_gaps(control, {}), [("DS-0001", ["traceability"])])

    def test_a_dataset_pointing_at_an_unknown_record_dangles(self):
        control = _control(datasets=[_dataset(traces_to_record="REC-9999")])
        self.assertEqual(data_control_gaps(control, {}), [("DS-0001", ["dangling-traceability"])])

    def test_traceability_can_be_switched_off_by_policy(self):
        control = _control(datasets=[_dataset(traces_to_record=None)])
        self.assertEqual(data_control_gaps(control, {"require_traceability": False}), [])


class Verdicts(unittest.TestCase):
    def test_a_clean_centre_is_controlled(self):
        result = assess_documentation_control(_case())
        self.assertEqual(result["verdict"], DOCUMENTATION_CONTROLLED)
        self.assertEqual(result["findings"], [])

    def test_control_never_established_short_circuits(self):
        result = assess_documentation_control(_case(control=_control(established=False)))
        self.assertEqual(result["verdict"], CONTROL_ABSENT)

    def test_an_unapproved_issue_outranks_a_superseded_one(self):
        control = _control(
            documents=[
                _document("TC-PROC-01", issue=3, state=DOC_DRAFT, approved_on_day=None,
                          issued_on_day=None),
                _document("TC-PROC-02", issue=1, state=DOC_SUPERSEDED),
            ]
        )
        result = assess_documentation_control(_case(control=control))
        self.assertEqual(result["verdict"], DOCUMENT_APPROVAL_BROKEN)

    def test_a_superseded_issue_outranks_a_retention_shortfall(self):
        control = _control(
            documents=[_document("TC-PROC-01", issue=2, state=DOC_SUPERSEDED)],
            records=[_record(retention_years=1.0)],
        )
        result = assess_documentation_control(_case(control=control))
        self.assertEqual(result["verdict"], ISSUE_CONTROL_BROKEN)

    def test_a_retention_shortfall_outranks_a_data_gap(self):
        control = _control(
            records=[_record(retention_years=1.0)],
            datasets=[_dataset(backup_held=False)],
        )
        result = assess_documentation_control(_case(control=control))
        self.assertEqual(result["verdict"], RECORDS_RETENTION_BROKEN)

    def test_a_data_gap_alone_is_the_last_verdict_before_pass(self):
        control = _control(datasets=[_dataset(integrity_evidence=False)])
        result = assess_documentation_control(_case(control=control))
        self.assertEqual(result["verdict"], TEST_DATA_CONTROL_BROKEN)

    def test_a_stale_issue_is_an_advisory_not_a_verdict(self):
        control = _control(
            as_of_day=2000,
            documents=[_document(approved_on_day=90, issued_on_day=100)],
        )
        result = assess_documentation_control(_case(control=control))
        self.assertEqual(result["verdict"], DOCUMENTATION_CONTROLLED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_case_without_control_is_refused(self):
        with self.assertRaises(ValueError):
            assess_documentation_control({"policy": {}})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_documentation_control(("control",))


if __name__ == "__main__":
    unittest.main()
