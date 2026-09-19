#!/usr/bin/env python3
"""Contract test for brazing supplier and facility audits (offline)."""

import copy
import datetime
import unittest

from q7040_brazing_audits_logic import (
    APPROVAL_CONDITIONAL,
    APPROVAL_MAINTAINED,
    APPROVAL_SUSPENDED,
    AREA_CONSUMABLE_CONTROL,
    AREA_FURNACE_CALIBRATION,
    AREA_OPERATOR_QUALIFICATION,
    AREA_PRE_BRAZE_CLEANLINESS,
    AREA_RECORDS,
    AUDIT_AREAS,
    CRITICAL_FOLLOW_UP_DAYS,
    FACILITY_APPROVED_SUPPLIER,
    FACILITY_IN_HOUSE,
    FACILITY_NEW_SUPPLIER,
    SEVERITY_CRITICAL,
    SEVERITY_MAJOR,
    SEVERITY_MINOR,
    approval_status,
    assess_audit,
    audit_interval_days,
    audit_scope,
    next_audit_date,
)

DATE = datetime.date


def _finding(finding_id, severity=SEVERITY_MINOR, area=AREA_RECORDS, closed=False):
    return {
        "finding_id": finding_id,
        "severity": severity,
        "area": area,
        "closed": closed,
    }


GOOD_CASE = {
    "facility_id": "SUP-1140",
    "facility_category": FACILITY_APPROVED_SUPPLIER,
    "audit_date": DATE(2026, 3, 10),
    "rotation_areas": [AREA_OPERATOR_QUALIFICATION, AREA_CONSUMABLE_CONTROL],
    "previous_findings": [],
    "findings": [],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ScopeTests(unittest.TestCase):
    def test_a_new_supplier_is_audited_across_every_area(self):
        self.assertEqual(audit_scope(FACILITY_NEW_SUPPLIER), list(AUDIT_AREAS))

    def test_furnace_calibration_and_records_never_rotate_out(self):
        scope = audit_scope(FACILITY_APPROVED_SUPPLIER, [], [])
        self.assertIn(AREA_FURNACE_CALIBRATION, scope)
        self.assertIn(AREA_RECORDS, scope)

    def test_a_rotation_area_is_added_to_the_permanent_ones(self):
        scope = audit_scope(
            FACILITY_APPROVED_SUPPLIER, [], [AREA_PRE_BRAZE_CLEANLINESS]
        )
        self.assertIn(AREA_PRE_BRAZE_CLEANLINESS, scope)

    def test_an_area_with_a_previous_major_finding_is_mandatory_again(self):
        scope = audit_scope(
            FACILITY_APPROVED_SUPPLIER,
            [_finding("F1", SEVERITY_MAJOR, AREA_CONSUMABLE_CONTROL)],
            [],
        )
        self.assertIn(AREA_CONSUMABLE_CONTROL, scope)

    def test_a_previous_minor_finding_does_not_pin_its_area(self):
        scope = audit_scope(
            FACILITY_APPROVED_SUPPLIER,
            [_finding("F1", SEVERITY_MINOR, AREA_PRE_BRAZE_CLEANLINESS)],
            [],
        )
        self.assertNotIn(AREA_PRE_BRAZE_CLEANLINESS, scope)

    def test_the_scope_comes_back_in_the_standard_area_order(self):
        scope = audit_scope(
            FACILITY_APPROVED_SUPPLIER,
            [],
            [AREA_PRE_BRAZE_CLEANLINESS, AREA_OPERATOR_QUALIFICATION],
        )
        self.assertEqual(scope, [a for a in AUDIT_AREAS if a in set(scope)])

    def test_an_unknown_rotation_area_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_scope(FACILITY_APPROVED_SUPPLIER, [], ["the canteen"])

    def test_an_unknown_facility_category_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_scope("a workshop down the road")


class IntervalTests(unittest.TestCase):
    def test_an_approved_supplier_has_the_longest_base_interval(self):
        self.assertGreater(
            audit_interval_days(FACILITY_APPROVED_SUPPLIER),
            audit_interval_days(FACILITY_IN_HOUSE),
        )

    def test_a_critical_finding_forces_a_short_follow_up(self):
        self.assertEqual(
            audit_interval_days(
                FACILITY_APPROVED_SUPPLIER, [_finding("F1", SEVERITY_CRITICAL)]
            ),
            CRITICAL_FOLLOW_UP_DAYS,
        )

    def test_a_major_finding_halves_the_interval(self):
        self.assertEqual(
            audit_interval_days(
                FACILITY_APPROVED_SUPPLIER, [_finding("F1", SEVERITY_MAJOR)]
            ),
            365,
        )

    def test_minor_findings_leave_the_interval_alone(self):
        self.assertEqual(
            audit_interval_days(
                FACILITY_IN_HOUSE, [_finding("F1"), _finding("F2")]
            ),
            365,
        )

    def test_a_critical_finding_outranks_a_major_one(self):
        self.assertEqual(
            audit_interval_days(
                FACILITY_IN_HOUSE,
                [_finding("F1", SEVERITY_MAJOR), _finding("F2", SEVERITY_CRITICAL)],
            ),
            CRITICAL_FOLLOW_UP_DAYS,
        )

    def test_the_next_date_is_the_audit_date_plus_the_interval(self):
        self.assertEqual(
            next_audit_date(DATE(2026, 3, 10), FACILITY_IN_HOUSE),
            DATE(2027, 3, 10),
        )

    def test_the_next_date_crosses_a_leap_day_without_help(self):
        self.assertEqual(
            next_audit_date(DATE(2027, 3, 10), FACILITY_IN_HOUSE),
            DATE(2028, 3, 9),
        )

    def test_a_datetime_instead_of_a_date_is_rejected(self):
        with self.assertRaises(ValueError):
            next_audit_date(datetime.datetime(2026, 3, 10), FACILITY_IN_HOUSE)


class ApprovalTests(unittest.TestCase):
    def test_no_findings_maintain_the_approval(self):
        self.assertEqual(approval_status([]), APPROVAL_MAINTAINED)

    def test_an_open_critical_finding_suspends_the_approval(self):
        self.assertEqual(
            approval_status([_finding("F1", SEVERITY_CRITICAL)]), APPROVAL_SUSPENDED
        )

    def test_an_open_major_finding_makes_the_approval_conditional(self):
        self.assertEqual(
            approval_status([_finding("F1", SEVERITY_MAJOR)]), APPROVAL_CONDITIONAL
        )

    def test_a_closed_critical_finding_no_longer_suspends(self):
        self.assertEqual(
            approval_status([_finding("F1", SEVERITY_CRITICAL, closed=True)]),
            APPROVAL_MAINTAINED,
        )

    def test_open_minor_findings_alone_maintain_the_approval(self):
        self.assertEqual(
            approval_status([_finding("F1"), _finding("F2")]), APPROVAL_MAINTAINED
        )

    def test_a_duplicate_finding_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            approval_status([_finding("F1"), _finding("F1")])

    def test_a_non_boolean_closure_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            approval_status([_finding("F1", closed="in progress")])

    def test_an_unknown_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            approval_status([_finding("F1", severity="serious")])


class AssessmentTests(unittest.TestCase):
    def test_a_clean_audit_maintains_the_approval_on_the_base_interval(self):
        result = assess_audit(_case())
        self.assertEqual(result["approval_status"], APPROVAL_MAINTAINED)
        self.assertEqual(result["interval_days"], 730)
        self.assertEqual(result["notes"], [])

    def test_a_critical_finding_suspends_and_brings_the_visit_forward(self):
        result = assess_audit(
            _case(
                findings=[
                    _finding("F1", SEVERITY_CRITICAL, AREA_FURNACE_CALIBRATION)
                ]
            )
        )
        self.assertEqual(result["approval_status"], APPROVAL_SUSPENDED)
        self.assertEqual(
            result["next_audit_due"],
            DATE(2026, 3, 10) + datetime.timedelta(days=CRITICAL_FOLLOW_UP_DAYS),
        )

    def test_a_finding_outside_the_audit_scope_is_flagged_as_a_disagreement(self):
        result = assess_audit(
            _case(findings=[_finding("F1", SEVERITY_MINOR, AREA_PRE_BRAZE_CLEANLINESS)])
        )
        self.assertEqual(len(result["notes"]), 1)

    def test_an_open_finding_is_listed_by_identifier(self):
        result = assess_audit(
            _case(findings=[_finding("F1", SEVERITY_MAJOR, AREA_RECORDS)])
        )
        self.assertEqual(result["open_findings"], ["F1"])
        self.assertEqual(result["approval_status"], APPROVAL_CONDITIONAL)

    def test_a_previous_major_finding_pulls_its_area_back_into_scope(self):
        result = assess_audit(
            _case(
                previous_findings=[
                    _finding("P1", SEVERITY_MAJOR, AREA_PRE_BRAZE_CLEANLINESS)
                ]
            )
        )
        self.assertIn(AREA_PRE_BRAZE_CLEANLINESS, result["scope"])

    def test_a_new_supplier_audit_covers_everything_regardless_of_rotation(self):
        result = assess_audit(
            _case(facility_category=FACILITY_NEW_SUPPLIER, rotation_areas=[])
        )
        self.assertEqual(result["scope"], list(AUDIT_AREAS))

    def test_an_audit_without_a_facility_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_audit(_case(facility_id=""))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_audit("we visited them in March")

    def test_findings_that_are_not_a_sequence_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_audit(_case(findings={"finding_id": "F1"}))


if __name__ == "__main__":
    unittest.main()
