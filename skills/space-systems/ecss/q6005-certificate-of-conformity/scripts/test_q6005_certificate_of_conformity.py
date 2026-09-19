#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 13.2.3 certificate leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_certificate_of_conformity.py
"""

import unittest

from q6005_certificate_of_conformity_logic import (
    ACCEPTANCE_CERTIFICATE_INDEX,
    AUTHORISED_SIGNATORY_ROLES,
    CERTIFICATE_FIELDS,
    CERTIFICATE_TOLERANCE,
    CONFIGURATION_ATTRIBUTES,
    FIELD_STATE_CREDIT,
    MANDATORY_CERTIFICATE_FIELDS,
    UNAUTHORISED_SIGNATORY_ROLES,
    VERDICTS,
    assess_certificate_of_conformity,
    assess_field,
    certificate_completeness_index,
    certificate_field_weight,
    configuration_differences,
    field_state_credit,
    normalize_configuration,
    normalize_field,
    normalize_waiver,
    quantity_declaration,
    signatory_findings,
    signatory_is_authorised,
    waiver_coverage,
)

SPARE_FIELD = "date-of-issue"
SERIALS = ["SN0001", "SN0002", "SN0003"]


def configuration(**overrides):
    """The configuration that was ordered."""
    record = {
        "part_number": "HYB-1234",
        "specification_issue": "DET-SPEC-1234 issue B",
        "build_standard_issue": "DRW-4471 issue C",
        "screening_level": "level-b",
        "lead_finish": "gold-plated",
    }
    record.update(overrides)
    return record


def signatory(**overrides):
    """A quality manager who actually signed."""
    record = {
        "name": "A. Quality Manager",
        "role": "quality-manager",
        "signature_applied": True,
    }
    record.update(overrides)
    return record


def declaration(**overrides):
    """The quantity and serials the certificate covers."""
    record = {"declared_quantity": 3, "certificate_serials": list(SERIALS)}
    record.update(overrides)
    return record


def present_fields(**states):
    """Every certificate field present, with named exceptions."""
    fields = []
    for name in sorted(CERTIFICATE_FIELDS):
        entry = {"field": name, "state": "present"}
        if name in states:
            entry["state"] = states[name]
        fields.append(entry)
    return fields


def waiver(**overrides):
    """An approved waiver referenced on the certificate."""
    record = {
        "reference": "WVR-0012",
        "covers": "screening_level",
        "approved": True,
        "referenced_on_certificate": True,
    }
    record.update(overrides)
    return record


def run(**overrides):
    """Grade one certificate of conformity."""
    case = {
        "lot_id": "HYB-1234-LOT-07",
        "ordered": configuration(),
        "delivered": configuration(),
        "waivers": [],
        "signatory": signatory(),
        "declaration": declaration(),
        "delivered_serials": list(SERIALS),
        "fields": present_fields(),
    }
    case.update(overrides)
    return assess_certificate_of_conformity(**case)


class SignatoryTests(unittest.TestCase):
    def test_a_quality_manager_may_release_product(self):
        self.assertTrue(signatory_is_authorised("quality-manager"))

    def test_a_test_technician_may_not_release_product(self):
        self.assertFalse(signatory_is_authorised("test-technician"))

    def test_the_two_role_lists_do_not_overlap(self):
        self.assertEqual(
            set(AUTHORISED_SIGNATORY_ROLES) & set(UNAUTHORISED_SIGNATORY_ROLES), set()
        )

    def test_an_unknown_role_is_rejected_rather_than_assumed(self):
        with self.assertRaises(ValueError):
            signatory_is_authorised("chief-vibes-officer")

    def test_a_blank_role_is_rejected(self):
        with self.assertRaises(ValueError):
            signatory_is_authorised("   ")

    def test_a_properly_signed_certificate_raises_nothing(self):
        self.assertEqual(signatory_findings(signatory()), [])

    def test_an_unnamed_signatory_is_reported(self):
        self.assertIn(
            "certificate-signed-by-nobody-named", signatory_findings(signatory(name="  "))
        )

    def test_a_role_without_release_authority_is_reported(self):
        self.assertIn(
            "signatory-role-cannot-release-product",
            signatory_findings(signatory(role="design-engineer")),
        )

    def test_a_certificate_nobody_signed_is_reported(self):
        self.assertIn(
            "certificate-not-signed", signatory_findings(signatory(signature_applied=False))
        )


class ConfigurationTests(unittest.TestCase):
    def test_identical_configurations_differ_on_nothing(self):
        self.assertEqual(configuration_differences(configuration(), configuration()), [])

    def test_a_changed_drawing_issue_is_reported_as_a_difference(self):
        differences = configuration_differences(
            configuration(), configuration(build_standard_issue="DRW-4471 issue D")
        )
        self.assertEqual(differences, ["build_standard_issue"])

    def test_several_differences_are_reported_in_the_published_order(self):
        differences = configuration_differences(
            configuration(),
            configuration(lead_finish="tin-plated", specification_issue="DET-SPEC-1234 issue C"),
        )
        self.assertEqual(differences, ["specification_issue", "lead_finish"])

    def test_a_configuration_missing_an_attribute_is_rejected(self):
        broken = configuration()
        del broken["screening_level"]
        with self.assertRaises(ValueError):
            normalize_configuration(broken, "ordered configuration")

    def test_a_configuration_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_configuration("HYB-1234", "ordered configuration")


class WaiverTests(unittest.TestCase):
    def test_an_approved_referenced_waiver_covers_its_difference(self):
        result = waiver_coverage(["screening_level"], [waiver()])
        self.assertTrue(result["all_differences_covered"])
        self.assertEqual(result["findings"], [])

    def test_a_difference_with_no_waiver_at_all_is_uncovered(self):
        result = waiver_coverage(["lead_finish"], [])
        self.assertEqual(result["uncovered_differences"], ["lead_finish"])
        self.assertIn("configuration-difference-with-no-approved-waiver", result["findings"])

    def test_a_waiver_covers_only_the_attribute_it_names(self):
        result = waiver_coverage(["lead_finish"], [waiver()])
        self.assertIn("lead_finish", result["uncovered_differences"])

    def test_an_unapproved_waiver_covers_nothing(self):
        result = waiver_coverage(["screening_level"], [waiver(approved=False)])
        self.assertFalse(result["all_differences_covered"])
        self.assertIn("waiver-referenced-but-not-approved", result["findings"])

    def test_an_approved_waiver_nobody_referenced_is_reported(self):
        result = waiver_coverage(
            ["screening_level"], [waiver(referenced_on_certificate=False)]
        )
        self.assertIn("approved-waiver-not-referenced-on-the-certificate", result["findings"])

    def test_a_waiver_against_an_attribute_that_matches_is_reported(self):
        result = waiver_coverage([], [waiver()])
        self.assertIn("waiver-raised-against-an-attribute-that-matches", result["findings"])

    def test_a_waiver_covering_an_unknown_attribute_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_waiver(waiver(covers="paint-colour"))

    def test_a_waiver_without_a_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_waiver(waiver(reference=""))

    def test_a_repeated_waiver_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            waiver_coverage(["screening_level"], [waiver(), waiver()])


class QuantityTests(unittest.TestCase):
    def test_a_certificate_covering_the_shipment_reconciles(self):
        self.assertTrue(quantity_declaration(3, SERIALS, SERIALS)["reconciled"])

    def test_a_quantity_that_differs_from_the_serial_list_is_reported(self):
        result = quantity_declaration(4, SERIALS, SERIALS)
        self.assertIn(
            "declared-quantity-differs-from-the-serials-on-the-certificate", result["findings"]
        )

    def test_a_delivered_unit_the_certificate_misses_is_named(self):
        result = quantity_declaration(2, SERIALS[:2], SERIALS)
        self.assertEqual(result["units_not_covered"], ["SN0003"])

    def test_a_certificate_covering_a_unit_nobody_shipped_is_reported(self):
        result = quantity_declaration(4, SERIALS + ["SN0099"], SERIALS)
        self.assertIn("certificate-covers-a-unit-that-was-not-delivered", result["findings"])

    def test_a_zero_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            quantity_declaration(0, SERIALS, SERIALS)

    def test_a_repeated_serial_on_the_certificate_is_rejected(self):
        with self.assertRaises(ValueError):
            quantity_declaration(3, ["SN0001", "SN0001", "SN0002"], SERIALS)


class FieldTests(unittest.TestCase):
    def test_every_mandatory_field_carries_a_published_weight(self):
        for name in MANDATORY_CERTIFICATE_FIELDS:
            self.assertIn(name, CERTIFICATE_FIELDS)

    def test_an_unknown_certificate_field_is_rejected(self):
        with self.assertRaises(ValueError):
            certificate_field_weight("customer-greeting")

    def test_an_unknown_field_state_is_rejected(self):
        with self.assertRaises(ValueError):
            field_state_credit("handwritten-in-pencil")

    def test_a_field_nobody_mentioned_defaults_to_absent(self):
        self.assertEqual(normalize_field({"field": SPARE_FIELD})["state"], "absent")

    def test_a_present_field_earns_its_full_weight(self):
        record = assess_field({"field": SPARE_FIELD, "state": "present"})
        self.assertAlmostEqual(record["weighted_credit"], CERTIFICATE_FIELDS[SPARE_FIELD], places=9)

    def test_a_missing_mandatory_field_is_marked_missing(self):
        self.assertTrue(assess_field({"field": "statement-of-conformity"})["mandatory_missing"])

    def test_a_fully_present_certificate_reaches_a_full_index(self):
        records = [assess_field(entry) for entry in present_fields()]
        self.assertAlmostEqual(certificate_completeness_index(records), 1.0, places=9)

    def test_an_empty_field_set_is_rejected(self):
        with self.assertRaises(ValueError):
            certificate_completeness_index([])


class WholeCertificateTests(unittest.TestCase):
    def test_a_sound_certificate_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "certificate-accepted")
        self.assertTrue(result["certificate_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["certificate_completeness_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_certificate_missing_a_mandatory_field_is_incomplete(self):
        result = run(fields=present_fields(**{"statement-of-conformity": "absent"}))
        self.assertEqual(result["verdict"], "certificate-assessment-incomplete")

    def test_an_unwaived_configuration_difference_refuses_the_certificate(self):
        result = run(delivered=configuration(lead_finish="tin-plated"))
        self.assertEqual(result["verdict"], "certificate-refused")
        self.assertFalse(result["certificate_accepted"])

    def test_a_covered_difference_leaves_the_certificate_acceptable(self):
        result = run(delivered=configuration(screening_level="level-c"), waivers=[waiver()])
        self.assertEqual(result["verdict"], "certificate-accepted")
        self.assertEqual(result["configuration_differences"], ["screening_level"])

    def test_an_unapproved_waiver_refuses_the_certificate(self):
        result = run(
            delivered=configuration(screening_level="level-c"),
            waivers=[waiver(approved=False)],
        )
        self.assertEqual(result["verdict"], "certificate-refused")

    def test_a_signatory_without_authority_refuses_the_certificate(self):
        result = run(signatory=signatory(role="shipping-clerk"))
        self.assertEqual(result["verdict"], "certificate-refused")

    def test_a_unit_the_certificate_does_not_cover_refuses_it(self):
        result = run(declaration=declaration(declared_quantity=2, certificate_serials=SERIALS[:2]))
        self.assertEqual(result["verdict"], "certificate-refused")
        self.assertIn(
            "delivered-unit-not-covered-by-the-certificate",
            [f["finding"] for f in result["findings"]],
        )

    def test_an_observation_on_an_optional_field_leaves_open_actions(self):
        result = run(fields=present_fields(**{SPARE_FIELD: "present-with-observation"}))
        self.assertEqual(result["verdict"], "certificate-accepted-with-open-actions")
        self.assertTrue(result["certificate_accepted"])

    def test_a_field_nobody_listed_is_graded_as_absent(self):
        result = run(fields=[{"field": SPARE_FIELD, "state": "present"}])
        states = {r["field"]: r["state"] for r in result["fields"]}
        self.assertEqual(states["supplier-identity"], "absent")
        self.assertEqual(len(result["fields"]), len(CERTIFICATE_FIELDS))

    def test_a_repeated_certificate_field_is_rejected(self):
        with self.assertRaises(ValueError):
            run(fields=present_fields() + [{"field": SPARE_FIELD, "state": "present"}])

    def test_a_blank_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(lot_id=" ")

    def test_a_declaration_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            run(declaration=[3, SERIALS])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(CERTIFICATE_TOLERANCE, 1e-6)

    def test_the_field_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(FIELD_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(FIELD_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_present_certificate(self):
        self.assertLess(ACCEPTANCE_CERTIFICATE_INDEX, 1.0)

    def test_every_compared_attribute_is_a_distinct_name(self):
        self.assertEqual(len(set(CONFIGURATION_ATTRIBUTES)), len(CONFIGURATION_ATTRIBUTES))


if __name__ == "__main__":
    unittest.main()
