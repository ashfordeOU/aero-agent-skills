"""Contract tests for the clause 4.3.11 manufacturer-data-delivery logic."""

import unittest

from q60_class_1_manufacturer_data_deliveries_logic import (
    BOUND_TOLERANCE,
    CONDITIONAL_RECORDS,
    CORE_RECORDS,
    TRACEABILITY_CHAIN,
    assess_manufacturer_data_delivery,
    defect_severity,
    delivery_verdict,
    package_completeness,
    record_defects,
    required_records,
    traceability_gaps,
)

SHIPMENT = {
    "lot_code": "LOT-4471-A",
    "dispatch_date": "2025-04-18",
    "quantity": 240.0,
}


def _entry(record_type, **over):
    base = {
        "type": record_type,
        "signed": True,
        "lot_code": "LOT-4471-A",
        "issue_date": "2025-04-10",
        "quantity_covered": 240.0,
    }
    base.update(over)
    return base


def _delivery(**over):
    base = {
        "shipment": dict(SHIPMENT),
        "records": [_entry(name) for name in CORE_RECORDS],
        "context": {},
        "traceability_links": list(TRACEABILITY_CHAIN),
    }
    base.update(over)
    return base


class RequiredRecordTests(unittest.TestCase):
    def test_core_records_are_always_owed(self):
        self.assertEqual(required_records({}), sorted(CORE_RECORDS))

    def test_radiation_duty_adds_its_record(self):
        owed = required_records({"radiation_duty": True})
        self.assertIn(CONDITIONAL_RECORDS["radiation_duty"], owed)

    def test_a_false_condition_adds_nothing(self):
        self.assertEqual(required_records({"rework_performed": False}), sorted(CORE_RECORDS))

    def test_several_conditions_accumulate(self):
        owed = required_records({"delta_qualified": True, "approved_deviation": True})
        self.assertEqual(len(owed), len(CORE_RECORDS) + 2)

    def test_unknown_condition_rejected(self):
        with self.assertRaises(ValueError):
            required_records({"radiation-duty": True})

    def test_non_boolean_condition_rejected(self):
        with self.assertRaises(ValueError):
            required_records({"radiation_duty": 1})


class RecordDefectTests(unittest.TestCase):
    def test_a_clean_record_carries_no_defect(self):
        self.assertEqual(record_defects(_entry("certificate-of-conformity"), SHIPMENT), [])

    def test_unsigned_record_is_flagged(self):
        codes = record_defects(_entry("certificate-of-conformity", signed=False), SHIPMENT)
        self.assertIn("unsigned-by-issuing-authority", codes)

    def test_lot_code_mismatch_is_flagged(self):
        codes = record_defects(_entry("screening-test-data", lot_code="LOT-9999-Z"), SHIPMENT)
        self.assertIn("lot-code-mismatch", codes)

    def test_lot_code_comparison_ignores_case(self):
        codes = record_defects(_entry("screening-test-data", lot_code="lot-4471-a"), SHIPMENT)
        self.assertEqual(codes, [])

    def test_record_issued_after_dispatch_is_flagged(self):
        codes = record_defects(_entry("lot-acceptance-test-report", issue_date="2025-04-30"),
                               SHIPMENT)
        self.assertIn("issued-after-dispatch", codes)

    def test_record_issued_on_the_dispatch_date_is_accepted(self):
        codes = record_defects(_entry("lot-acceptance-test-report", issue_date="2025-04-18"),
                               SHIPMENT)
        self.assertEqual(codes, [])

    def test_short_quantity_coverage_is_flagged(self):
        codes = record_defects(_entry("lot-traceability-record", quantity_covered=100.0),
                               SHIPMENT)
        self.assertIn("quantity-not-covered", codes)

    def test_coverage_exactly_at_the_shipped_quantity_is_accepted(self):
        codes = record_defects(_entry("lot-traceability-record", quantity_covered=240.0),
                               SHIPMENT)
        self.assertEqual(codes, [])

    def test_superseded_issue_is_flagged(self):
        codes = record_defects(_entry("screening-test-data", superseded=True), SHIPMENT)
        self.assertIn("superseded-issue-delivered", codes)

    def test_malformed_issue_date_rejected(self):
        with self.assertRaises(ValueError):
            record_defects(_entry("screening-test-data", issue_date="18-04-2025"), SHIPMENT)

    def test_missing_entry_key_rejected(self):
        entry = _entry("screening-test-data")
        del entry["signed"]
        with self.assertRaises(ValueError):
            record_defects(entry, SHIPMENT)

    def test_zero_shipment_quantity_rejected(self):
        shipment = dict(SHIPMENT, quantity=0.0)
        with self.assertRaises(ValueError):
            record_defects(_entry("screening-test-data"), shipment)


class TraceabilityTests(unittest.TestCase):
    def test_a_complete_chain_reports_no_gap(self):
        self.assertEqual(traceability_gaps(TRACEABILITY_CHAIN), [])

    def test_gaps_are_returned_coarsest_first(self):
        gaps = traceability_gaps(["shipment-lot"])
        self.assertEqual(gaps, ["wafer-lot", "assembly-lot", "date-code"])

    def test_unknown_link_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(["serial-number"])

    def test_blank_link_rejected(self):
        with self.assertRaises(ValueError):
            traceability_gaps(["  "])


class CompletenessTests(unittest.TestCase):
    def test_a_full_package_reads_one(self):
        self.assertAlmostEqual(package_completeness(CORE_RECORDS, CORE_RECORDS), 1.0, places=9)

    def test_half_a_package_reads_a_half(self):
        value = package_completeness(CORE_RECORDS, CORE_RECORDS[:2])
        self.assertAlmostEqual(value, 0.5, places=9)

    def test_an_empty_delivery_reads_zero(self):
        self.assertAlmostEqual(package_completeness(CORE_RECORDS, []), 0.0, places=9)

    def test_extra_records_do_not_push_completeness_past_one(self):
        value = package_completeness(CORE_RECORDS, list(CORE_RECORDS) + ["packing-list"])
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_empty_owed_set_rejected(self):
        with self.assertRaises(ValueError):
            package_completeness([], CORE_RECORDS)

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class SeverityAndVerdictTests(unittest.TestCase):
    def test_a_missing_record_is_critical(self):
        self.assertEqual(defect_severity("missing-record"), "critical")

    def test_a_late_issue_is_major(self):
        self.assertEqual(defect_severity("issued-after-dispatch"), "major")

    def test_unknown_defect_code_rejected(self):
        with self.assertRaises(ValueError):
            defect_severity("paperwork-smudged")

    def test_no_findings_accepts(self):
        self.assertEqual(delivery_verdict([]), "accepted")

    def test_a_major_finding_accepts_with_actions(self):
        self.assertEqual(
            delivery_verdict([{"severity": "major", "topic": "t", "message": "m"}]),
            "accepted-with-actions",
        )

    def test_a_critical_finding_holds_the_shipment(self):
        self.assertEqual(
            delivery_verdict([{"severity": "critical", "topic": "t", "message": "m"}]),
            "hold-shipment",
        )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            delivery_verdict([{"severity": "blocking", "topic": "t", "message": "m"}])


class AssessmentTests(unittest.TestCase):
    def test_a_complete_delivery_is_accepted(self):
        result = assess_manufacturer_data_delivery(_delivery())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness_fraction"], 1.0, places=9)

    def test_a_missing_conditional_record_holds_the_shipment(self):
        result = assess_manufacturer_data_delivery(
            _delivery(context={"radiation_duty": True})
        )
        self.assertEqual(result["verdict"], "hold-shipment")
        self.assertIn(CONDITIONAL_RECORDS["radiation_duty"], result["missing_records"])

    def test_a_late_certificate_accepts_with_actions(self):
        records = [_entry(name) for name in CORE_RECORDS]
        records[0] = _entry(CORE_RECORDS[0], issue_date="2025-05-02")
        result = assess_manufacturer_data_delivery(_delivery(records=records))
        self.assertEqual(result["verdict"], "accepted-with-actions")

    def test_a_broken_identity_chain_holds_the_shipment(self):
        result = assess_manufacturer_data_delivery(
            _delivery(traceability_links=["shipment-lot", "date-code"])
        )
        self.assertEqual(result["verdict"], "hold-shipment")
        self.assertEqual(result["traceability_gaps"], ["wafer-lot", "assembly-lot"])

    def test_findings_are_ranked_critical_first(self):
        records = [_entry(name) for name in CORE_RECORDS]
        records[1] = _entry(CORE_RECORDS[1], lot_code="LOT-0000-X", issue_date="2025-05-02")
        result = assess_manufacturer_data_delivery(_delivery(records=records))
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_partial_completeness_is_reported(self):
        records = [_entry(name) for name in CORE_RECORDS[:3]]
        result = assess_manufacturer_data_delivery(_delivery(records=records))
        self.assertAlmostEqual(result["completeness_fraction"], 0.75, places=9)

    def test_a_duplicated_record_type_rejected(self):
        records = [_entry(CORE_RECORDS[0]) for _ in range(2)]
        with self.assertRaises(ValueError):
            assess_manufacturer_data_delivery(_delivery(records=records))

    def test_missing_delivery_key_rejected(self):
        delivery = _delivery()
        del delivery["shipment"]
        with self.assertRaises(ValueError):
            assess_manufacturer_data_delivery(delivery)

    def test_delivery_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_manufacturer_data_delivery([_delivery()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
