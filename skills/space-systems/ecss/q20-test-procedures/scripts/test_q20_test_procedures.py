"""Contract tests for the clause 5.6.3.1 test-procedure control logic."""

import unittest
from datetime import date

from q20_test_procedures_logic import (
    CUSTOMER_ROLE,
    MANDATORY_APPROVAL_ROLES,
    approval_findings,
    assess_procedure,
    assess_procedure_set,
    compare_revisions,
    consistency_findings,
    coverage_findings,
    normalise_identifier,
    parse_iso_date,
    revision_rank,
    update_control_findings,
    validate_procedure,
)

SPEC = {
    "id": "tspe-thermal-vacuum",
    "revision": "b",
    "revision_in_force": "b",
    "requirements": ["req-010", "req-020", "req-030"],
    "change_records": [
        {
            "procedure_id": "tpro-tv-001",
            "from_revision": "a",
            "to_revision": "b",
            "approved": True,
            "approval_date": "2026-03-01",
        }
    ],
}

GOOD_PROCEDURE = {
    "id": "tpro-tv-001",
    "revision": "b",
    "previous_revision": "a",
    "specification_id": "tspe-thermal-vacuum",
    "cited_specification_revision": "b",
    "issue_date": "2026-03-04",
    "steps": [
        {"id": "s-10", "covers": ["req-010", "req-020"]},
        {"id": "s-20", "covers": ["req-030"]},
    ],
    "approvals": [
        {"role": "engineering", "date": "2026-03-02"},
        {"role": "product-assurance", "date": "2026-03-03"},
    ],
}


def procedure(**overrides):
    """Return a copy of the good procedure with overrides applied."""
    item = dict(GOOD_PROCEDURE)
    item["steps"] = [dict(step) for step in GOOD_PROCEDURE["steps"]]
    item["approvals"] = [dict(app) for app in GOOD_PROCEDURE["approvals"]]
    item.update(overrides)
    return item


class IdentifierAndDateTests(unittest.TestCase):
    def test_identifier_is_trimmed_and_lowered(self):
        self.assertEqual(normalise_identifier("  REQ-010 ", "req"), "req-010")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("   ", "req")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(10, "req")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date("2026-03-04", "d"), date(2026, 3, 4))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_iso_date(date(2026, 1, 2), "d"), date(2026, 1, 2))

    def test_impossible_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30", "d")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("04/03/2026", "d")


class RevisionTests(unittest.TestCase):
    def test_letter_scheme_ranks_in_order(self):
        self.assertEqual(revision_rank("a")[1], 1)
        self.assertEqual(revision_rank("z")[1], 26)
        self.assertEqual(revision_rank("aa")[1], 27)

    def test_numeric_scheme_ranks_by_value(self):
        self.assertEqual(revision_rank("10"), ("numeric", 10))

    def test_mixed_mark_rejected(self):
        with self.assertRaises(ValueError):
            revision_rank("b2")

    def test_compare_orders_letters(self):
        self.assertEqual(compare_revisions("c", "b"), 1)
        self.assertEqual(compare_revisions("b", "c"), -1)
        self.assertEqual(compare_revisions("c", "c"), 0)

    def test_compare_across_schemes_rejected(self):
        with self.assertRaises(ValueError):
            compare_revisions("b", "2")


class ValidationTests(unittest.TestCase):
    def test_good_procedure_normalises(self):
        record = validate_procedure(procedure())
        self.assertEqual(record["id"], "tpro-tv-001")
        self.assertEqual(record["issue_date"], date(2026, 3, 4))

    def test_steps_must_not_be_empty(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(steps=[]))

    def test_duplicate_step_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(
                procedure(steps=[{"id": "s-10", "covers": []}, {"id": "s-10", "covers": []}])
            )

    def test_duplicate_approval_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(
                procedure(
                    approvals=[
                        {"role": "engineering", "date": "2026-03-02"},
                        {"role": "engineering", "date": "2026-03-03"},
                    ]
                )
            )

    def test_unorderable_revision_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(revision="rev-b"))

    def test_non_mapping_procedure_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(["tpro-tv-001"])


class ApprovalTests(unittest.TestCase):
    def test_mandatory_roles_are_engineering_and_product_assurance(self):
        self.assertEqual(MANDATORY_APPROVAL_ROLES, ("engineering", "product-assurance"))

    def test_complete_approvals_give_no_finding(self):
        self.assertEqual(approval_findings(validate_procedure(procedure())), [])

    def test_missing_role_is_a_finding(self):
        record = validate_procedure(
            procedure(approvals=[{"role": "engineering", "date": "2026-03-02"}])
        )
        self.assertEqual(approval_findings(record), ["missing product-assurance approval"])

    def test_customer_role_demanded_only_when_witnessed(self):
        record = validate_procedure(procedure(customer_witnessed=True))
        self.assertIn("missing %s approval" % CUSTOMER_ROLE, approval_findings(record))

    def test_signature_after_issue_is_a_finding(self):
        record = validate_procedure(
            procedure(
                approvals=[
                    {"role": "engineering", "date": "2026-03-02"},
                    {"role": "product-assurance", "date": "2026-03-09"},
                ]
            )
        )
        self.assertEqual(
            approval_findings(record),
            ["product-assurance approval is dated after the procedure issue date"],
        )


class CoverageTests(unittest.TestCase):
    def test_full_coverage_ratio_is_one(self):
        result = coverage_findings(validate_procedure(procedure()), SPEC["requirements"])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_partial_coverage_lists_the_gap(self):
        record = validate_procedure(
            procedure(steps=[{"id": "s-10", "covers": ["req-010"]}])
        )
        result = coverage_findings(record, SPEC["requirements"])
        self.assertEqual(result["missing"], ["req-020", "req-030"])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0 / 3.0, places=9)

    def test_orphan_step_requirement_is_reported(self):
        record = validate_procedure(
            procedure(
                steps=[
                    {"id": "s-10", "covers": ["req-010", "req-020", "req-030"]},
                    {"id": "s-20", "covers": ["req-999"]},
                ]
            )
        )
        result = coverage_findings(record, SPEC["requirements"])
        self.assertEqual(result["orphan"], ["req-999"])

    def test_empty_requirement_list_rejected(self):
        with self.assertRaises(ValueError):
            coverage_findings(validate_procedure(procedure()), [])


class ConsistencyTests(unittest.TestCase):
    def test_matching_revision_is_clean(self):
        self.assertEqual(consistency_findings(validate_procedure(procedure()), "b"), [])

    def test_stale_citation_is_a_finding(self):
        record = validate_procedure(procedure(cited_specification_revision="a"))
        self.assertEqual(len(consistency_findings(record, "b")), 1)

    def test_forward_citation_is_a_finding(self):
        record = validate_procedure(procedure(cited_specification_revision="c"))
        self.assertIn("ahead of", consistency_findings(record, "b")[0])


class UpdateControlTests(unittest.TestCase):
    def test_first_issue_needs_no_change_record(self):
        record = validate_procedure(procedure(previous_revision=None))
        self.assertEqual(update_control_findings(record, []), [])

    def test_matching_approved_change_record_clears_the_advance(self):
        record = validate_procedure(procedure())
        self.assertEqual(update_control_findings(record, SPEC["change_records"]), [])

    def test_missing_change_record_is_a_finding(self):
        record = validate_procedure(procedure())
        self.assertIn("no matching change record", update_control_findings(record, [])[0])

    def test_unapproved_change_record_is_a_finding(self):
        changes = [dict(SPEC["change_records"][0], approved=False)]
        record = validate_procedure(procedure())
        self.assertIn("not approved", update_control_findings(record, changes)[0])

    def test_change_approved_after_issue_is_a_finding(self):
        changes = [dict(SPEC["change_records"][0], approval_date="2026-03-20")]
        record = validate_procedure(procedure())
        self.assertIn("approved after", update_control_findings(record, changes)[0])

    def test_revision_going_backwards_is_a_finding(self):
        record = validate_procedure(procedure(revision="a", previous_revision="b"))
        self.assertIn("behind", update_control_findings(record, [])[0])


class AssessmentTests(unittest.TestCase):
    def test_clean_procedure_is_released(self):
        result = assess_procedure(procedure(), SPEC)
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])

    def test_wrong_specification_is_a_finding(self):
        result = assess_procedure(procedure(specification_id="tspe-vibration"), SPEC)
        self.assertFalse(result["released"])

    def test_set_verdict_released_when_every_requirement_is_exercised(self):
        result = assess_procedure_set(SPEC, [procedure()])
        self.assertEqual(result["verdict"], "released")
        self.assertAlmostEqual(result["set_coverage_ratio"], 1.0, places=9)

    def test_set_verdict_holds_on_an_uncovered_requirement(self):
        thin = procedure(steps=[{"id": "s-10", "covers": ["req-010", "req-020"]}])
        result = assess_procedure_set(SPEC, [thin])
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["uncovered_requirements"], ["req-030"])

    def test_two_procedures_may_share_the_coverage(self):
        first = procedure(id="tpro-tv-001", steps=[{"id": "s-10", "covers": ["req-010"]}])
        second = procedure(
            id="tpro-tv-002",
            previous_revision=None,
            steps=[{"id": "s-10", "covers": ["req-020", "req-030"]}],
        )
        result = assess_procedure_set(dict(SPEC, change_records=SPEC["change_records"]), [first, second])
        self.assertEqual(result["uncovered_requirements"], [])
        self.assertAlmostEqual(result["set_coverage_ratio"], 1.0, places=9)

    def test_duplicate_procedure_id_in_a_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure_set(SPEC, [procedure(), procedure()])

    def test_empty_procedure_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure_set(SPEC, [])


if __name__ == "__main__":
    unittest.main()
