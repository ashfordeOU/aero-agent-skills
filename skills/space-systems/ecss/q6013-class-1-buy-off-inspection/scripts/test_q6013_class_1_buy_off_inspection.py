"""Contract tests for the clause 4.3.6 source buy-off inspection logic.

The cases follow the buy-off workflow one step at a time: inspector
qualification and independence, the mandatory evidence checklist, the
date-sequence gate, the nonconformance review, and the disposition that
stops a lot at source. Each step is exercised on both sides of its limit,
so the record shows what was judged and not only the verdict.
"""

import unittest

from q6013_class_1_buy_off_inspection_logic import (
    DEFAULT_MINOR_ALLOWANCE,
    REQUIRED_EVIDENCE,
    assess_buy_off,
    categorize_nonconformances,
    evidence_completeness,
    missing_evidence,
    normalize_evidence,
    parse_inspection_date,
    validate_inspector,
    validate_sequence,
)

FULL_PACK = {item: True for item in REQUIRED_EVIDENCE}


def _inspector(**extra):
    record = {
        "name": "source inspector",
        "organisation": "customer quality assurance",
        "qualification_expiry": "2027-03-31",
    }
    record.update(extra)
    return record


def _spec(**overrides):
    spec = {
        "lot_id": "LOT-2537-A",
        "inspection_date": "2026-05-12",
        "lot_acceptance_completed": "2026-05-08",
        "inspector": _inspector(),
        "evidence": dict(FULL_PACK),
    }
    spec.update(overrides)
    return spec


class EvidenceTests(unittest.TestCase):
    def test_sequence_of_names_becomes_a_seen_pack(self):
        pack = normalize_evidence(["part-marking", "esd-packaging"])
        self.assertTrue(pack["part-marking"])
        self.assertTrue(pack["esd-packaging"])

    def test_names_are_case_and_space_insensitive(self):
        pack = normalize_evidence({"  Part-Marking ": True})
        self.assertEqual(list(pack), ["part-marking"])

    def test_non_boolean_evidence_value_rejected(self):
        with self.assertRaises(ValueError):
            normalize_evidence({"part-marking": "yes"})

    def test_empty_evidence_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_evidence({"   ": True})

    def test_full_pack_has_nothing_missing(self):
        self.assertEqual(missing_evidence(FULL_PACK), [])

    def test_absent_item_reported_missing(self):
        pack = dict(FULL_PACK)
        del pack["screening-report"]
        self.assertEqual(missing_evidence(pack), ["screening-report"])

    def test_item_marked_not_seen_reported_missing(self):
        pack = dict(FULL_PACK)
        pack["certificate-of-conformity"] = False
        self.assertIn("certificate-of-conformity", missing_evidence(pack))

    def test_completeness_of_full_pack_is_one(self):
        self.assertAlmostEqual(evidence_completeness(FULL_PACK), 1.0, places=9)

    def test_completeness_drops_with_each_absent_item(self):
        pack = dict(FULL_PACK)
        del pack["esd-packaging"]
        expected = (len(REQUIRED_EVIDENCE) - 1) / len(REQUIRED_EVIDENCE)
        self.assertAlmostEqual(evidence_completeness(pack), expected, places=9)


class NonconformanceTests(unittest.TestCase):
    def test_empty_list_is_not_blocking(self):
        result = categorize_nonconformances([])
        self.assertFalse(result["blocking"])

    def test_open_major_blocks(self):
        result = categorize_nonconformances(
            [{"id": "NCR-1", "severity": "major", "status": "open"}]
        )
        self.assertEqual(result["open_major"], ["NCR-1"])
        self.assertTrue(result["blocking"])

    def test_waived_major_with_reference_does_not_block(self):
        result = categorize_nonconformances(
            [{"id": "NCR-1", "severity": "major", "status": "waived", "waiver_ref": "WVR-9"}]
        )
        self.assertEqual(result["open_major"], [])
        self.assertEqual(result["waived"], ["NCR-1"])
        self.assertFalse(result["blocking"])

    def test_waived_without_reference_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformances(
                [{"id": "NCR-1", "severity": "major", "status": "waived"}]
            )

    def test_minors_within_allowance_do_not_block(self):
        items = [
            {"id": "NCR-%d" % n, "severity": "minor", "status": "open"}
            for n in range(DEFAULT_MINOR_ALLOWANCE)
        ]
        self.assertFalse(categorize_nonconformances(items)["blocking"])

    def test_minors_over_allowance_block(self):
        items = [
            {"id": "NCR-%d" % n, "severity": "minor", "status": "open"}
            for n in range(DEFAULT_MINOR_ALLOWANCE + 1)
        ]
        result = categorize_nonconformances(items)
        self.assertTrue(result["minor_over_allowance"])
        self.assertTrue(result["blocking"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformances(
                [
                    {"id": "NCR-1", "severity": "minor", "status": "open"},
                    {"id": "NCR-1", "severity": "minor", "status": "closed"},
                ]
            )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformances(
                [{"id": "NCR-1", "severity": "critical", "status": "open"}]
            )

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformances(
                [{"id": "NCR-1", "severity": "minor", "status": "pending"}]
            )

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            categorize_nonconformances([], minor_allowance=-1)


class InspectorAndSequenceTests(unittest.TestCase):
    def test_current_qualification_accepted(self):
        record = validate_inspector(_inspector(), "2026-05-12")
        self.assertTrue(record["qualification_current"])
        self.assertTrue(record["independent"])

    def test_qualification_expiring_on_the_day_is_current(self):
        record = validate_inspector(
            _inspector(qualification_expiry="2026-05-12"), "2026-05-12"
        )
        self.assertTrue(record["qualification_current"])

    def test_expired_qualification_flagged(self):
        record = validate_inspector(
            _inspector(qualification_expiry="2026-05-11"), "2026-05-12"
        )
        self.assertFalse(record["qualification_current"])

    def test_producer_inspector_is_not_independent(self):
        record = validate_inspector(_inspector(produced_the_lot=True), "2026-05-12")
        self.assertFalse(record["independent"])

    def test_missing_inspector_key_rejected(self):
        bad = _inspector()
        del bad["organisation"]
        with self.assertRaises(ValueError):
            validate_inspector(bad, "2026-05-12")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_inspection_date("12-05-2026")

    def test_sequence_gap_is_positive_when_buy_off_follows_testing(self):
        self.assertEqual(validate_sequence("2026-05-08", "2026-05-12"), 4)

    def test_sequence_gap_is_negative_when_buy_off_precedes_testing(self):
        self.assertEqual(validate_sequence("2026-05-12", "2026-05-08"), -4)


class AssessmentTests(unittest.TestCase):
    def test_clean_buy_off_authorises_shipment(self):
        result = assess_buy_off(_spec())
        self.assertTrue(result["authorised"])
        self.assertEqual(result["disposition"], "authorize-shipment")
        self.assertEqual(result["findings"], [])

    def test_missing_mandatory_evidence_holds_the_lot(self):
        pack = dict(FULL_PACK)
        del pack["traceability-records"]
        result = assess_buy_off(_spec(evidence=pack))
        self.assertFalse(result["authorised"])
        self.assertEqual(result["disposition"], "hold-at-source")

    def test_open_major_holds_the_lot(self):
        result = assess_buy_off(
            _spec(nonconformances=[{"id": "NCR-7", "severity": "major", "status": "open"}])
        )
        self.assertFalse(result["authorised"])
        self.assertTrue(any("NCR-7" in item for item in result["findings"]))

    def test_non_independent_inspector_holds_the_lot(self):
        result = assess_buy_off(_spec(inspector=_inspector(produced_the_lot=True)))
        self.assertFalse(result["authorised"])
        self.assertTrue(any("independent" in item for item in result["findings"]))

    def test_buy_off_before_lot_acceptance_holds_the_lot(self):
        result = assess_buy_off(_spec(lot_acceptance_completed="2026-05-20"))
        self.assertFalse(result["authorised"])
        self.assertEqual(result["gap_days"], -8)

    def test_thin_optional_evidence_is_an_advisory_only(self):
        result = assess_buy_off(
            _spec(optional_evidence={"die-photographs": True, "sem-report": False})
        )
        self.assertTrue(result["authorised"])
        self.assertTrue(any("thin" in item for item in result["findings"]))
        self.assertAlmostEqual(result["optional_evidence_share"], 0.5, places=9)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["inspector"]
        with self.assertRaises(ValueError):
            assess_buy_off(spec)

    def test_blank_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_buy_off(_spec(lot_id="   "))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_buy_off(["not", "a", "mapping"])

    def test_completeness_reported_alongside_the_disposition(self):
        result = assess_buy_off(_spec())
        self.assertAlmostEqual(result["evidence_completeness"], 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
