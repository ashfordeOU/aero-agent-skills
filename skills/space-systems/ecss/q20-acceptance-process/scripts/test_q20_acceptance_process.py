"""Contract tests for the clause 5.7.1 acceptance and delivery logic."""

import unittest

from q20_acceptance_process_logic import (
    DEFAULT_HOLD_POINTS,
    NONCONFORMANCE_SEVERITIES,
    VERIFICATION_METHODS,
    VERIFICATION_STATES,
    assess_acceptance,
    compliance_fraction,
    hold_point_findings,
    nonconformance_findings,
    normalise_identifier,
    requirement_findings,
    validate_concessions,
    validate_register,
)

REGISTER = [
    {"requirement": "req-010", "method": "test", "state": "verified", "evidence": "tr-tv-001"},
    {"requirement": "req-020", "method": "analysis", "state": "verified", "evidence": "an-114"},
    {"requirement": "req-030", "method": "inspection", "state": "verified", "evidence": "ir-props-2"},
]

SIGNATURES = [
    {"hold_point": "physical-configuration-audit", "signed_by": "product-assurance"},
    {"hold_point": "pre-delivery-review", "signed_by": "product-assurance"},
    {"hold_point": "customer-acceptance-review", "signed_by": "customer"},
]

PACKAGE = {
    "register": REGISTER,
    "concessions": [],
    "nonconformances": [],
    "signatures": SIGNATURES,
}


def package(**overrides):
    """Return a copy of the clean acceptance package with overrides applied."""
    item = dict(PACKAGE)
    item.update(overrides)
    return item


class VocabularyTests(unittest.TestCase):
    def test_verification_methods(self):
        self.assertEqual(
            VERIFICATION_METHODS, ("test", "analysis", "inspection", "review-of-design")
        )

    def test_verification_states(self):
        self.assertEqual(
            VERIFICATION_STATES, ("verified", "partially-verified", "not-verified")
        )

    def test_severities(self):
        self.assertEqual(NONCONFORMANCE_SEVERITIES, ("minor", "major", "critical"))

    def test_default_hold_points_carry_their_owner(self):
        self.assertEqual(len(DEFAULT_HOLD_POINTS), 3)
        self.assertEqual(DEFAULT_HOLD_POINTS[2], ("customer-acceptance-review", "customer"))

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" REQ-010 ", "req"), "req-010")


class RegisterTests(unittest.TestCase):
    def test_clean_register_validates(self):
        entries = validate_register(REGISTER)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries["req-010"]["method"], "test")

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            validate_register([])

    def test_duplicate_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_register(REGISTER + [dict(REGISTER[0])])

    def test_unknown_method_rejected(self):
        bad = [dict(REGISTER[0], method="demonstration-by-similarity")]
        with self.assertRaises(ValueError):
            validate_register(bad)

    def test_unknown_state_rejected(self):
        bad = [dict(REGISTER[0], state="probably-fine")]
        with self.assertRaises(ValueError):
            validate_register(bad)

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_register(["req-010"])


class ConcessionTests(unittest.TestCase):
    def test_empty_concession_list_is_allowed(self):
        self.assertEqual(validate_concessions(None), {})

    def test_duplicate_reference_rejected(self):
        entry = {"reference": "wvr-1", "approved": True, "approved_by": "customer"}
        with self.assertRaises(ValueError):
            validate_concessions([entry, dict(entry)])

    def test_concession_normalises(self):
        entries = validate_concessions(
            [{"reference": " WVR-1 ", "approved": True, "approved_by": "Customer"}]
        )
        self.assertTrue(entries["wvr-1"]["approved"])
        self.assertEqual(entries["wvr-1"]["approved_by"], "customer")


class RequirementGradingTests(unittest.TestCase):
    def test_fully_verified_register_gives_no_finding(self):
        result = requirement_findings(validate_register(REGISTER), {})
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["carried_concessions"], [])

    def test_verified_without_evidence_is_a_finding(self):
        bad = [dict(REGISTER[0], evidence=None)] + [dict(e) for e in REGISTER[1:]]
        result = requirement_findings(validate_register(bad), {})
        self.assertIn("no evidence", result["findings"][0])

    def test_unverified_without_a_concession_is_a_finding(self):
        bad = [dict(REGISTER[0], state="not-verified", evidence=None)] + [
            dict(e) for e in REGISTER[1:]
        ]
        result = requirement_findings(validate_register(bad), {})
        self.assertIn("no deviation or waiver raised", result["findings"][0])

    def test_concession_not_in_the_register_is_a_finding(self):
        bad = [dict(REGISTER[0], state="partially-verified", concession="wvr-9")] + [
            dict(e) for e in REGISTER[1:]
        ]
        result = requirement_findings(validate_register(bad), {})
        self.assertIn("not in the register", result["findings"][0])

    def test_unapproved_concession_is_a_finding(self):
        bad = [dict(REGISTER[0], state="partially-verified", concession="wvr-9")] + [
            dict(e) for e in REGISTER[1:]
        ]
        concessions = validate_concessions([{"reference": "wvr-9", "approved": False}])
        result = requirement_findings(validate_register(bad), concessions)
        self.assertIn("unapproved concession", result["findings"][0])

    def test_approved_concession_without_an_approver_is_a_finding(self):
        bad = [dict(REGISTER[0], state="partially-verified", concession="wvr-9")] + [
            dict(e) for e in REGISTER[1:]
        ]
        concessions = validate_concessions([{"reference": "wvr-9", "approved": True}])
        result = requirement_findings(validate_register(bad), concessions)
        self.assertIn("no approver named", result["findings"][0])

    def test_approved_concession_is_carried(self):
        bad = [dict(REGISTER[0], state="partially-verified", concession="wvr-9")] + [
            dict(e) for e in REGISTER[1:]
        ]
        concessions = validate_concessions(
            [{"reference": "wvr-9", "approved": True, "approved_by": "customer"}]
        )
        result = requirement_findings(validate_register(bad), concessions)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["carried_concessions"], ["wvr-9"])


class ComplianceFractionTests(unittest.TestCase):
    def test_all_verified_gives_one(self):
        self.assertAlmostEqual(compliance_fraction(validate_register(REGISTER)), 1.0, places=9)

    def test_one_open_requirement_lowers_the_fraction(self):
        bad = [dict(REGISTER[0], state="not-verified", evidence=None)] + [
            dict(e) for e in REGISTER[1:]
        ]
        self.assertAlmostEqual(
            compliance_fraction(validate_register(bad)), 2.0 / 3.0, places=9
        )

    def test_partial_verification_does_not_count_as_verified(self):
        bad = [dict(REGISTER[0], state="partially-verified")] + [dict(e) for e in REGISTER[1:]]
        self.assertAlmostEqual(
            compliance_fraction(validate_register(bad)), 2.0 / 3.0, places=9
        )


class NonconformanceTests(unittest.TestCase):
    def test_no_nonconformances_gives_no_finding(self):
        self.assertEqual(nonconformance_findings([]), [])

    def test_closed_nonconformance_is_ignored(self):
        self.assertEqual(
            nonconformance_findings([{"id": "ncr-1", "severity": "major", "closed": True}]), []
        )

    def test_open_critical_nonconformance_blocks(self):
        findings = nonconformance_findings(
            [
                {
                    "id": "ncr-2",
                    "severity": "critical",
                    "disposition": "repair",
                    "disposition_approved": True,
                }
            ]
        )
        self.assertIn("critical nonconformance ncr-2 is open", findings[0])

    def test_open_major_without_disposition_is_a_finding(self):
        findings = nonconformance_findings([{"id": "ncr-3", "severity": "major"}])
        self.assertIn("has no disposition", findings[0])

    def test_unapproved_disposition_is_a_finding(self):
        findings = nonconformance_findings(
            [{"id": "ncr-4", "severity": "minor", "disposition": "use-as-is"}]
        )
        self.assertIn("is not approved", findings[0])

    def test_approved_disposition_clears_an_open_minor(self):
        self.assertEqual(
            nonconformance_findings(
                [
                    {
                        "id": "ncr-5",
                        "severity": "minor",
                        "disposition": "use-as-is",
                        "disposition_approved": True,
                    }
                ]
            ),
            [],
        )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_findings([{"id": "ncr-6", "severity": "cosmetic"}])

    def test_duplicate_nonconformance_id_rejected(self):
        entry = {"id": "ncr-7", "severity": "minor", "closed": True}
        with self.assertRaises(ValueError):
            nonconformance_findings([entry, dict(entry)])


class HoldPointTests(unittest.TestCase):
    def test_all_signed_gives_no_finding(self):
        self.assertEqual(hold_point_findings(SIGNATURES), [])

    def test_missing_signature_is_a_finding(self):
        findings = hold_point_findings(SIGNATURES[:2])
        self.assertEqual(findings, ["acceptance hold point customer-acceptance-review is not signed"])

    def test_signature_by_the_wrong_party_is_a_finding(self):
        swapped = [dict(SIGNATURES[0]), dict(SIGNATURES[1]), dict(SIGNATURES[2], signed_by="supplier")]
        self.assertIn("not by the customer", hold_point_findings(swapped)[0])

    def test_duplicate_signature_rejected(self):
        with self.assertRaises(ValueError):
            hold_point_findings(SIGNATURES + [dict(SIGNATURES[0])])

    def test_custom_hold_point_set_is_honoured(self):
        findings = hold_point_findings(SIGNATURES, (("pre-delivery-review", "product-assurance"),))
        self.assertEqual(findings, [])


class AssessmentTests(unittest.TestCase):
    def test_clean_package_is_accepted(self):
        result = assess_acceptance(package())
        self.assertEqual(result["verdict"], "accepted")
        self.assertAlmostEqual(result["compliance_fraction"], 1.0, places=9)

    def test_approved_concession_gives_conditional_acceptance(self):
        register = [dict(REGISTER[0], state="partially-verified", concession="wvr-9")] + [
            dict(e) for e in REGISTER[1:]
        ]
        result = assess_acceptance(
            package(
                register=register,
                concessions=[
                    {"reference": "wvr-9", "approved": True, "approved_by": "customer"}
                ],
            )
        )
        self.assertEqual(result["verdict"], "conditionally-accepted")
        self.assertEqual(result["carried_concessions"], ["wvr-9"])

    def test_open_critical_nonconformance_rejects_the_delivery(self):
        result = assess_acceptance(
            package(nonconformances=[{"id": "ncr-9", "severity": "critical"}])
        )
        self.assertEqual(result["verdict"], "rejected")

    def test_unsigned_hold_point_rejects_the_delivery(self):
        result = assess_acceptance(package(signatures=SIGNATURES[:1]))
        self.assertEqual(result["verdict"], "rejected")
        self.assertEqual(len(result["findings"]), 2)

    def test_requirement_count_is_reported(self):
        self.assertEqual(assess_acceptance(package())["requirement_count"], 3)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_acceptance(REGISTER)


if __name__ == "__main__":
    unittest.main()
