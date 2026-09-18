"""Contract tests for the Annex D certificate of conformity DRD logic."""

import unittest
from datetime import date

from q20_coc_drd_logic import (
    EVIDENCE_KINDS,
    INDEPENDENT_AUTHORITIES,
    REQUIRED_FIELDS,
    STATEMENTS,
    assess_certificate,
    evidence_coverage,
    evidence_findings,
    field_findings,
    normalise_identifier,
    normalise_register,
    parse_day,
    signature_findings,
    statement_findings,
    validate_certificate,
)

REGISTER = {
    "abcl-1102-iss3": "2026-04-01",
    "atr-4471-iss1": "2026-04-08",
    "insp-0099": "2026-04-09",
    "matcert-5510": "2026-03-02",
}


def certificate(**changes):
    """Return a certificate that answers the whole DRD."""
    base = {
        "item_designation": "reaction-wheel-assembly",
        "part_number": "rwa-2200-03",
        "serial_number": "sn-0147",
        "quantity": 1,
        "order_reference": "po-88231",
        "specification_reference": "spec-rwa-2200",
        "specification_issue": 4,
        "statement": "conforms-fully",
        "signatory": "a-nowak",
        "signatory_function": "quality-assurance",
        "signature_date": "2026-04-14",
        "deviations": [],
        "evidence": {
            "as-built-configuration-list": "abcl-1102-iss3",
            "acceptance-test-report": "atr-4471-iss1",
            "inspection-record": "insp-0099",
            "material-certificate": "matcert-5510",
        },
    }
    for key, value in changes.items():
        if value is None and key in base:
            del base[key]
        else:
            base[key] = value
    return base


class VocabularyTests(unittest.TestCase):
    def test_required_fields_cover_identification_and_signature(self):
        self.assertIn("serial_number", REQUIRED_FIELDS)
        self.assertIn("signature_date", REQUIRED_FIELDS)

    def test_two_statements_are_admitted(self):
        self.assertEqual(len(STATEMENTS), 2)

    def test_four_evidence_kinds(self):
        self.assertEqual(len(EVIDENCE_KINDS), 4)

    def test_independent_authorities_are_quality_functions(self):
        self.assertIn("quality-assurance", INDEPENDENT_AUTHORITIES)
        self.assertNotIn("production-manager", INDEPENDENT_AUTHORITIES)

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" SN-0147 ", "s"), "sn-0147")

    def test_day_parsed_from_iso(self):
        self.assertEqual(parse_day("2026-04-14", "d"), date(2026, 4, 14))

    def test_register_normalises_its_keys_and_dates(self):
        normalised = normalise_register({" ATR-4471-ISS1 ": "2026-04-08"})
        self.assertEqual(normalised["atr-4471-iss1"], date(2026, 4, 8))


class ValidationTests(unittest.TestCase):
    def test_clean_certificate_validates(self):
        normalised = validate_certificate(certificate())
        self.assertEqual(normalised["serial_number"], "sn-0147")

    def test_non_mapping_certificate_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(["sn-0147"])

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(quantity=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(quantity=True))

    def test_zero_specification_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(specification_issue=0))

    def test_unknown_statement_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(statement="probably-conforms"))

    def test_non_sequence_deviations_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(deviations="wv-1"))

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(evidence=["abcl-1102-iss3"]))

    def test_bad_signature_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_certificate(certificate(signature_date="14.04.2026"))


class FieldTests(unittest.TestCase):
    def test_complete_certificate_has_no_field_finding(self):
        self.assertEqual(field_findings(validate_certificate(certificate())), [])

    def test_absent_field_is_named(self):
        findings = field_findings(validate_certificate(certificate(serial_number=None)))
        self.assertIn("serial_number", findings[0])

    def test_several_absent_fields_are_named_together(self):
        normalised = validate_certificate(certificate(signatory=None, order_reference=None))
        findings = field_findings(normalised)
        self.assertIn("signatory", findings[0])
        self.assertIn("order_reference", findings[0])

    def test_malformed_input_rejected(self):
        with self.assertRaises(ValueError):
            field_findings("sn-0147")


class StatementTests(unittest.TestCase):
    def test_full_conformity_with_no_deviation_is_clean(self):
        self.assertEqual(statement_findings(validate_certificate(certificate())), [])

    def test_full_conformity_listing_a_deviation_is_contradictory(self):
        normalised = validate_certificate(certificate(deviations=["wv-3312"]))
        findings = statement_findings(normalised)
        self.assertIn("asserts full conformity while listing", findings[0])

    def test_qualified_conformity_with_deviations_is_clean(self):
        normalised = validate_certificate(
            certificate(statement="conforms-with-listed-deviations", deviations=["wv-3312"])
        )
        self.assertEqual(statement_findings(normalised), [])

    def test_qualified_conformity_with_no_deviation_is_a_finding(self):
        normalised = validate_certificate(
            certificate(statement="conforms-with-listed-deviations")
        )
        self.assertIn("enumerates no deviation", statement_findings(normalised)[0])


class EvidenceTests(unittest.TestCase):
    def test_complete_resolvable_evidence_is_clean(self):
        self.assertEqual(evidence_findings(validate_certificate(certificate()), REGISTER), [])

    def test_absent_evidence_kind_is_a_finding(self):
        evidence = dict(certificate()["evidence"])
        del evidence["inspection-record"]
        normalised = validate_certificate(certificate(evidence=evidence))
        self.assertIn("inspection-record", evidence_findings(normalised, REGISTER)[0])

    def test_dangling_reference_is_a_finding(self):
        evidence = dict(certificate()["evidence"])
        evidence["acceptance-test-report"] = "atr-9999-iss1"
        normalised = validate_certificate(certificate(evidence=evidence))
        findings = evidence_findings(normalised, REGISTER)
        self.assertIn("atr-9999-iss1", findings[-1])

    def test_full_coverage_is_one(self):
        coverage = evidence_coverage(validate_certificate(certificate()), REGISTER)
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_one_unresolvable_reference_lowers_coverage(self):
        evidence = dict(certificate()["evidence"])
        evidence["material-certificate"] = "matcert-0000"
        normalised = validate_certificate(certificate(evidence=evidence))
        total = len(EVIDENCE_KINDS)
        self.assertAlmostEqual(
            evidence_coverage(normalised, REGISTER), (total - 1) / float(total), places=9
        )

    def test_empty_evidence_gives_zero_coverage(self):
        normalised = validate_certificate(certificate(evidence={}))
        self.assertAlmostEqual(evidence_coverage(normalised, REGISTER), 0.0, places=9)

    def test_non_mapping_register_rejected(self):
        with self.assertRaises(ValueError):
            evidence_coverage(validate_certificate(certificate()), ["abcl-1102-iss3"])


class SignatureTests(unittest.TestCase):
    def test_independent_signatory_after_the_evidence_is_clean(self):
        self.assertEqual(signature_findings(validate_certificate(certificate()), REGISTER), [])

    def test_production_signatory_is_a_finding(self):
        normalised = validate_certificate(certificate(signatory_function="production-manager"))
        findings = signature_findings(normalised, REGISTER)
        self.assertIn("independent quality authority", findings[0])

    def test_signature_before_the_latest_evidence_is_a_finding(self):
        normalised = validate_certificate(certificate(signature_date="2026-04-05"))
        findings = signature_findings(normalised, REGISTER)
        self.assertIn("before insp-0099 was issued", findings[0])

    def test_signature_on_the_day_of_the_latest_evidence_is_accepted(self):
        normalised = validate_certificate(certificate(signature_date="2026-04-09"))
        self.assertEqual(signature_findings(normalised, REGISTER), [])

    def test_certificate_without_a_signature_date_raises_no_date_finding(self):
        normalised = validate_certificate(certificate(signature_date=None))
        self.assertEqual(signature_findings(normalised, REGISTER), [])


class AssessmentTests(unittest.TestCase):
    def test_clean_certificate_is_valid(self):
        result = assess_certificate(certificate(), REGISTER)
        self.assertEqual(result["verdict"], "certificate-valid")
        self.assertAlmostEqual(result["evidence_coverage"], 1.0, places=9)

    def test_deviation_count_is_reported(self):
        result = assess_certificate(
            certificate(statement="conforms-with-listed-deviations", deviations=["wv-1", "wv-2"]),
            REGISTER,
        )
        self.assertEqual(result["deviation_count"], 2)
        self.assertEqual(result["verdict"], "certificate-valid")

    def test_contradictory_statement_invalidates_it(self):
        result = assess_certificate(certificate(deviations=["wv-3312"]), REGISTER)
        self.assertEqual(result["verdict"], "certificate-invalid")

    def test_dependent_signatory_invalidates_it(self):
        result = assess_certificate(
            certificate(signatory_function="manufacturing-supervisor"), REGISTER
        )
        self.assertEqual(result["verdict"], "certificate-invalid")

    def test_absent_field_invalidates_it(self):
        result = assess_certificate(certificate(part_number=None), REGISTER)
        self.assertEqual(result["verdict"], "certificate-invalid")

    def test_serial_number_is_reported_for_evidence(self):
        self.assertEqual(assess_certificate(certificate(), REGISTER)["serial_number"], "sn-0147")

    def test_non_mapping_register_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_certificate(certificate(), "abcl-1102-iss3")


if __name__ == "__main__":
    unittest.main()
