"""Contract tests for the clause 5.7.5 delivery control logic."""

import unittest

from q20_delivery_logic import (
    AUTHORISED_SIGNATORY_FUNCTIONS,
    BASE_SHIPPING_DOCUMENTS,
    assess_delivery_control,
    certificate_findings,
    document_findings,
    excursion_report,
    identification_findings,
    monitoring_coverage,
    monitoring_findings,
    normalize_token,
    required_shipping_documents,
    validate_consignment,
    validate_limits,
)

CONSIGNMENT = {"part_number": "PN-4417", "serial_number": "SN-0009", "quantity": 2}

LIMITS = {"temperature-c": (-10.0, 45.0), "shock-g": (None, 8.0), "humidity-rh": (0.0, 60.0)}

CLEAN_READINGS = [
    {"parameter": "temperature-c", "value": 18.0},
    {"parameter": "shock-g", "value": 3.5},
    {"parameter": "humidity-rh", "value": 41.0},
]

CERTIFICATE = {
    "part_number": "PN-4417",
    "serial_number": "SN-0009",
    "quantity": 2,
    "signatory_function": "quality-assurance",
    "reservations_listed": False,
}


def _spec(**overrides):
    consignment = dict(CONSIGNMENT)
    consignment.update(overrides.pop("consignment", {}))
    certificate = dict(CERTIFICATE)
    certificate.update(overrides.pop("certificate", {}))
    spec = {
        "consignment": consignment,
        "carried_documents": list(required_shipping_documents(consignment)),
        "transport": {
            "limits": dict(LIMITS),
            "readings": [dict(r) for r in CLEAN_READINGS],
            "recorded_hours": 30.0,
            "transit_hours": 30.0,
        },
        "certificate": certificate,
        "board_decision": "deliver",
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Packing_List"), "packing-list")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("")


class ValidateConsignmentTests(unittest.TestCase):
    def test_states_default_to_false(self):
        record = validate_consignment(CONSIGNMENT)
        self.assertFalse(record["cross_border"])
        self.assertEqual(record["quantity"], 2)

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_consignment(dict(CONSIGNMENT, quantity=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_consignment(dict(CONSIGNMENT, quantity=True))

    def test_missing_serial_rejected(self):
        with self.assertRaises(ValueError):
            validate_consignment({"part_number": "PN-1", "quantity": 1})

    def test_non_boolean_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_consignment(dict(CONSIGNMENT, hazardous="yes"))


class ShippingDocumentTests(unittest.TestCase):
    def test_domestic_benign_consignment_needs_the_base_set(self):
        self.assertEqual(required_shipping_documents(CONSIGNMENT), list(BASE_SHIPPING_DOCUMENTS))

    def test_cross_border_adds_customs_and_export(self):
        documents = required_shipping_documents(dict(CONSIGNMENT, cross_border=True))
        self.assertIn("customs-declaration", documents)
        self.assertIn("export-authorisation", documents)

    def test_hazardous_adds_the_dangerous_goods_declaration(self):
        documents = required_shipping_documents(dict(CONSIGNMENT, hazardous=True))
        self.assertIn("dangerous-goods-declaration", documents)

    def test_monitoring_record_added_once_for_two_limits(self):
        documents = required_shipping_documents(
            dict(CONSIGNMENT, temperature_controlled=True, shock_limited=True)
        )
        self.assertEqual(documents.count("transport-monitoring-record"), 1)

    def test_missing_document_named(self):
        findings = document_findings(list(BASE_SHIPPING_DOCUMENTS[:-1]), list(BASE_SHIPPING_DOCUMENTS))
        self.assertEqual(len(findings), 1)
        self.assertIn("transport-handling-instructions", findings[0])

    def test_case_difference_is_not_a_gap(self):
        self.assertEqual(document_findings(["Packing List"], ["packing-list"]), [])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            document_findings("packing-list", ["packing-list"])


class LimitTests(unittest.TestCase):
    def test_one_sided_limit_accepted(self):
        bounds = validate_limits({"shock-g": (None, 8.0)})
        self.assertEqual(bounds["shock-g"], (None, 8.0))

    def test_unbounded_parameter_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"shock-g": (None, None)})

    def test_inverted_bounds_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({"temperature-c": (45.0, -10.0)})

    def test_empty_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_limits({})


class ExcursionTests(unittest.TestCase):
    def test_clean_journey_reports_no_excursion(self):
        report = excursion_report(CLEAN_READINGS, LIMITS)
        self.assertEqual(report["temperature-c"]["excursions"], 0)
        self.assertIsNone(report["shock-g"]["worst_value"])

    def test_reading_exactly_on_the_bound_is_inside_it(self):
        report = excursion_report([{"parameter": "shock-g", "value": 8.0}], LIMITS)
        self.assertEqual(report["shock-g"]["excursions"], 0)

    def test_worst_high_reading_is_kept(self):
        report = excursion_report(
            [
                {"parameter": "shock-g", "value": 9.0},
                {"parameter": "shock-g", "value": 14.5},
                {"parameter": "shock-g", "value": 8.5},
            ],
            LIMITS,
        )
        self.assertEqual(report["shock-g"]["excursions"], 3)
        self.assertAlmostEqual(report["shock-g"]["worst_value"], 14.5, places=9)
        self.assertEqual(report["shock-g"]["side"], "above")

    def test_low_side_excursion_is_recorded_below(self):
        report = excursion_report([{"parameter": "temperature-c", "value": -25.0}], LIMITS)
        self.assertEqual(report["temperature-c"]["side"], "below")

    def test_undeclared_parameter_rejected(self):
        with self.assertRaises(ValueError):
            excursion_report([{"parameter": "pressure-kpa", "value": 90.0}], LIMITS)

    def test_reading_without_value_rejected(self):
        with self.assertRaises(ValueError):
            excursion_report([{"parameter": "shock-g"}], LIMITS)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_is_unity(self):
        self.assertAlmostEqual(monitoring_coverage(30.0, 30.0), 1.0, places=9)

    def test_partial_coverage_is_the_ratio(self):
        self.assertAlmostEqual(monitoring_coverage(15.0, 30.0), 0.5, places=9)

    def test_recorded_longer_than_transit_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_coverage(31.0, 30.0)

    def test_negative_recording_rejected(self):
        with self.assertRaises(ValueError):
            monitoring_coverage(-1.0, 30.0)

    def test_gap_is_reported_as_unknown_not_compliant(self):
        result = monitoring_findings(CLEAN_READINGS, LIMITS, 20.0, 30.0)
        self.assertTrue(any("unknown" in f for f in result["findings"]))

    def test_full_coverage_and_clean_readings_give_no_findings(self):
        result = monitoring_findings(CLEAN_READINGS, LIMITS, 30.0, 30.0)
        self.assertEqual(result["findings"], [])


class IdentificationTests(unittest.TestCase):
    def test_matching_certificate_is_clean(self):
        self.assertEqual(identification_findings(CONSIGNMENT, CERTIFICATE), [])

    def test_serial_mismatch_named(self):
        certificate = dict(CERTIFICATE, serial_number="SN-0010")
        findings = identification_findings(CONSIGNMENT, certificate)
        self.assertEqual(len(findings), 1)
        self.assertIn("serial-number", findings[0])

    def test_quantity_mismatch_named(self):
        certificate = dict(CERTIFICATE, quantity=1)
        findings = identification_findings(CONSIGNMENT, certificate)
        self.assertIn("quantity", findings[0])

    def test_missing_certificate_field_rejected(self):
        certificate = dict(CERTIFICATE)
        del certificate["part_number"]
        with self.assertRaises(ValueError):
            identification_findings(CONSIGNMENT, certificate)


class CertificateAuthorityTests(unittest.TestCase):
    def test_authorised_signatory_on_a_clean_delivery(self):
        self.assertEqual(certificate_findings(CERTIFICATE, "deliver"), [])

    def test_held_delivery_blocks_the_certificate(self):
        findings = certificate_findings(CERTIFICATE, "hold")
        self.assertTrue(any("held the delivery" in f for f in findings))

    def test_unauthorised_signatory_named(self):
        certificate = dict(CERTIFICATE, signatory_function="production-supervisor")
        findings = certificate_findings(certificate, "deliver")
        self.assertIn("not authorised", findings[0])

    def test_missing_signatory_is_a_finding(self):
        certificate = dict(CERTIFICATE)
        del certificate["signatory_function"]
        self.assertTrue(any("no signatory" in f for f in certificate_findings(certificate, "deliver")))

    def test_reservations_must_be_listed_on_the_certificate(self):
        findings = certificate_findings(CERTIFICATE, "deliver-with-reservation")
        self.assertTrue(any("does not list" in f for f in findings))

    def test_listed_reservations_clear_the_finding(self):
        certificate = dict(CERTIFICATE, reservations_listed=True)
        self.assertEqual(certificate_findings(certificate, "deliver-with-reservation"), [])

    def test_unknown_board_decision_rejected(self):
        with self.assertRaises(ValueError):
            certificate_findings(CERTIFICATE, "maybe")

    def test_signatory_list_is_not_empty(self):
        self.assertGreaterEqual(len(AUTHORISED_SIGNATORY_FUNCTIONS), 1)


class AssessDeliveryControlTests(unittest.TestCase):
    def test_clean_delivery_may_issue_the_certificate(self):
        result = assess_delivery_control(_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["certificate_issuable"])

    def test_missing_customs_paper_blocks_a_cross_border_delivery(self):
        spec = _spec(consignment={"cross_border": True})
        spec["carried_documents"] = list(BASE_SHIPPING_DOCUMENTS)
        result = assess_delivery_control(spec)
        self.assertFalse(result["certificate_issuable"])
        self.assertEqual(len(result["document_findings"]), 2)

    def test_shock_excursion_blocks_the_certificate(self):
        spec = _spec()
        spec["transport"]["readings"] = [{"parameter": "shock-g", "value": 12.0}]
        result = assess_delivery_control(spec)
        self.assertFalse(result["certificate_issuable"])
        self.assertTrue(any("shock-g" in f for f in result["findings"]))

    def test_monitoring_gap_blocks_the_certificate(self):
        spec = _spec()
        spec["transport"]["recorded_hours"] = 10.0
        result = assess_delivery_control(spec)
        self.assertAlmostEqual(result["monitoring"]["coverage"], 1.0 / 3.0, places=9)
        self.assertFalse(result["certificate_issuable"])

    def test_missing_transport_key_rejected(self):
        spec = _spec()
        del spec["transport"]["limits"]
        with self.assertRaises(ValueError):
            assess_delivery_control(spec)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["certificate"]
        with self.assertRaises(ValueError):
            assess_delivery_control(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_control(["consignment"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            consignment={"cross_border": True, "hazardous": True},
            certificate={"serial_number": "SN-9999", "signatory_function": "storeman"},
        )
        spec["carried_documents"] = []
        spec["transport"]["readings"] = [{"parameter": "humidity-rh", "value": 85.0}]
        spec["transport"]["recorded_hours"] = 5.0
        result = assess_delivery_control(spec)
        self.assertGreaterEqual(len(result["findings"]), 10)


if __name__ == "__main__":
    unittest.main()
