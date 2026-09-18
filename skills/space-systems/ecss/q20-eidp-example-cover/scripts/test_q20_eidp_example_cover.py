"""Contract tests for the Annex F data package cover header logic."""

import unittest
from datetime import date

from q20_eidp_example_cover_logic import (
    APPROVAL_ROLES,
    HEADER_FIELDS,
    MANDATORY_HEADER_FIELDS,
    approval_chain_findings,
    assess_eidp_cover,
    document_count_findings,
    format_eidp_number,
    normalise_identifier,
    number_findings,
    parse_day,
    render_header,
    validate_header,
)

INDEX = ["as-built-configuration-list", "acceptance-test-report", "certificate-of-conformity"]


def header(**changes):
    """Return a cover header filled the way the worked example fills it."""
    base = {
        "project": "orion-payload",
        "contract_number": "ct-99120",
        "item_designation": "star-tracker-head",
        "part_number": "sth-4100-02",
        "serial_number": "sn-0031",
        "eidp_number": "ct-99120-eidp-sn-0031",
        "issue": 1,
        "issue_date": "2026-05-20",
        "document_count": 3,
        "index_reference": "idx-4100-0031",
        "customer_acceptance": "pending",
    }
    for key, value in changes.items():
        if value is None and key in base:
            del base[key]
        else:
            base[key] = value
    return base


def approvals(**changes):
    base = {
        "prepared-by": {"name": "m-fischer", "signed_on": "2026-05-12"},
        "checked-by": {"name": "l-oduya", "signed_on": "2026-05-15"},
        "approved-by": {"name": "a-nowak", "signed_on": "2026-05-18"},
    }
    for key, value in changes.items():
        role = key.replace("_", "-")
        if value is None and role in base:
            del base[role]
        else:
            base[role] = value
    return base


class VocabularyTests(unittest.TestCase):
    def test_header_opens_with_the_project(self):
        self.assertEqual(HEADER_FIELDS[0], "project")

    def test_mandatory_fields_are_header_fields(self):
        self.assertTrue(set(MANDATORY_HEADER_FIELDS).issubset(set(HEADER_FIELDS)))

    def test_customer_acceptance_is_optional(self):
        self.assertNotIn("customer_acceptance", MANDATORY_HEADER_FIELDS)

    def test_three_approval_roles_in_signing_order(self):
        self.assertEqual(APPROVAL_ROLES, ("prepared-by", "checked-by", "approved-by"))

    def test_package_number_is_built_from_contract_and_serial(self):
        self.assertEqual(format_eidp_number("CT-99120", " sn-0031 "), "ct-99120-eidp-sn-0031")

    def test_blank_contract_number_rejected(self):
        with self.assertRaises(ValueError):
            format_eidp_number("  ", "sn-0031")

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" IDX-01 ", "i"), "idx-01")

    def test_day_parsed_from_iso(self):
        self.assertEqual(parse_day("2026-05-20", "d"), date(2026, 5, 20))


class ValidationTests(unittest.TestCase):
    def test_clean_header_validates(self):
        normalised = validate_header(header())
        self.assertEqual(normalised["serial_number"], "sn-0031")
        self.assertEqual(normalised["issue_date"], date(2026, 5, 20))

    def test_non_mapping_header_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(["project"])

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(header(shipping_crate="crate-2"))

    def test_blank_mandatory_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(header(index_reference=None))

    def test_absent_customer_acceptance_accepted(self):
        self.assertIsNone(validate_header(header(customer_acceptance=None))["customer_acceptance"])

    def test_zero_document_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(header(document_count=0))

    def test_boolean_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(header(issue=True))

    def test_bad_issue_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_header(header(issue_date="20.05.2026"))


class NumberTests(unittest.TestCase):
    def test_matching_number_is_clean(self):
        self.assertEqual(number_findings(validate_header(header())), [])

    def test_number_from_another_serial_is_a_finding(self):
        findings = number_findings(validate_header(header(eidp_number="ct-99120-eidp-sn-0099")))
        self.assertIn("ct-99120-eidp-sn-0031", findings[0])

    def test_number_from_another_contract_is_a_finding(self):
        findings = number_findings(validate_header(header(eidp_number="ct-11111-eidp-sn-0031")))
        self.assertIn("while the contract and serial number give", findings[0])


class ApprovalTests(unittest.TestCase):
    def test_clean_approval_block_is_clean(self):
        self.assertEqual(approval_chain_findings(validate_header(header()), approvals()), [])

    def test_unsigned_role_is_a_finding(self):
        findings = approval_chain_findings(validate_header(header()), approvals(checked_by=None))
        self.assertIn("unsigned by checked-by", findings[0])

    def test_one_person_holding_two_roles_is_a_finding(self):
        block = approvals(
            checked_by={"name": "m-fischer", "signed_on": "2026-05-15"}
        )
        findings = approval_chain_findings(validate_header(header()), block)
        self.assertIn("more than one role", findings[0])

    def test_signatures_out_of_order_is_a_finding(self):
        block = approvals(checked_by={"name": "l-oduya", "signed_on": "2026-05-10"})
        findings = approval_chain_findings(validate_header(header()), block)
        self.assertIn("before prepared-by signed", findings[0])

    def test_signatures_on_the_same_day_are_accepted(self):
        block = approvals(
            prepared_by={"name": "m-fischer", "signed_on": "2026-05-15"},
            checked_by={"name": "l-oduya", "signed_on": "2026-05-15"},
            approved_by={"name": "a-nowak", "signed_on": "2026-05-15"},
        )
        self.assertEqual(approval_chain_findings(validate_header(header()), block), [])

    def test_signature_after_the_issue_date_is_a_finding(self):
        block = approvals(approved_by={"name": "a-nowak", "signed_on": "2026-06-01"})
        findings = approval_chain_findings(validate_header(header()), block)
        self.assertIn("after the cover was issued", findings[-1])

    def test_signature_on_the_issue_date_is_accepted(self):
        block = approvals(approved_by={"name": "a-nowak", "signed_on": "2026-05-20"})
        self.assertEqual(approval_chain_findings(validate_header(header()), block), [])

    def test_unknown_approval_role_rejected(self):
        block = approvals()
        block["witnessed-by"] = {"name": "k-park", "signed_on": "2026-05-19"}
        with self.assertRaises(ValueError):
            approval_chain_findings(validate_header(header()), block)

    def test_non_mapping_approvals_rejected(self):
        with self.assertRaises(ValueError):
            approval_chain_findings(validate_header(header()), ["m-fischer"])


class DocumentCountTests(unittest.TestCase):
    def test_matching_count_is_clean(self):
        self.assertEqual(document_count_findings(validate_header(header()), INDEX), [])

    def test_short_count_is_a_finding(self):
        findings = document_count_findings(validate_header(header(document_count=5)), INDEX)
        self.assertIn("declares 5 document(s) while the index lists 3", findings[0])

    def test_repeated_index_line_is_a_finding(self):
        index = INDEX + ["certificate-of-conformity"]
        findings = document_count_findings(validate_header(header(document_count=4)), index)
        self.assertIn("lists twice", findings[0])

    def test_non_sequence_index_rejected(self):
        with self.assertRaises(ValueError):
            document_count_findings(validate_header(header()), "delivery-note")

    def test_blank_index_line_rejected(self):
        with self.assertRaises(ValueError):
            document_count_findings(validate_header(header()), ["  ", "delivery-note"])


class RenderingTests(unittest.TestCase):
    def test_every_field_gets_a_line(self):
        self.assertEqual(len(render_header(validate_header(header()))), len(HEADER_FIELDS))

    def test_labels_are_aligned_to_one_column(self):
        lines = render_header(validate_header(header()))
        self.assertEqual(len({line.index(" : ") for line in lines}), 1)

    def test_issue_date_prints_as_an_iso_day(self):
        lines = render_header(validate_header(header()))
        self.assertTrue(any(line.endswith("2026-05-20") for line in lines))

    def test_absent_optional_field_prints_a_dash(self):
        lines = render_header(validate_header(header(customer_acceptance=None)))
        self.assertTrue(lines[-1].endswith(": -"))

    def test_rendering_rejects_a_raw_header(self):
        with self.assertRaises(ValueError):
            render_header(["project"])


class AssessmentTests(unittest.TestCase):
    def test_clean_cover_is_conformant(self):
        result = assess_eidp_cover(header(), approvals(), INDEX)
        self.assertEqual(result["verdict"], "cover-conformant")
        self.assertEqual(result["indexed_count"], 3)

    def test_wrong_number_makes_it_nonconformant(self):
        result = assess_eidp_cover(
            header(eidp_number="ct-99120-eidp-sn-0099"), approvals(), INDEX
        )
        self.assertEqual(result["verdict"], "cover-nonconformant")

    def test_self_checked_block_makes_it_nonconformant(self):
        block = approvals(approved_by={"name": "m-fischer", "signed_on": "2026-05-18"})
        result = assess_eidp_cover(header(), block, INDEX)
        self.assertEqual(result["verdict"], "cover-nonconformant")

    def test_count_mismatch_makes_it_nonconformant(self):
        result = assess_eidp_cover(header(document_count=9), approvals(), INDEX)
        self.assertEqual(result["verdict"], "cover-nonconformant")
        self.assertEqual(result["declared_count"], 9)

    def test_rendered_header_travels_with_the_result(self):
        result = assess_eidp_cover(header(), approvals(), INDEX)
        self.assertEqual(len(result["rendered"]), len(HEADER_FIELDS))

    def test_package_number_is_reported_for_evidence(self):
        result = assess_eidp_cover(header(), approvals(), INDEX)
        self.assertEqual(result["eidp_number"], "ct-99120-eidp-sn-0031")

    def test_blank_mandatory_field_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_eidp_cover(header(part_number=None), approvals(), INDEX)


if __name__ == "__main__":
    unittest.main()
