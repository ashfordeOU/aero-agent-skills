#!/usr/bin/env python3
"""Contract test for the ECSS-Q-ST-60-05 clause 13.2.2 cover-sheet leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q6005_data_package_cover_sheets.py
"""

import unittest

from q6005_data_package_cover_sheets_logic import (
    ACCEPTANCE_COVER_SHEET_INDEX,
    COVER_SHEET_FIELDS,
    COVER_SHEET_TOLERANCE,
    FIELD_STATE_CREDIT,
    MANDATORY_COVER_SHEET_FIELDS,
    VERDICTS,
    assess_cover_sheet,
    assess_field,
    build_standard_findings,
    cover_sheet_completeness_index,
    cover_sheet_field_weight,
    field_state_credit,
    normalize_field,
    quantity_reconciliation,
    reconcile_enclosures,
    serial_range_coverage,
)

SPARE_FIELD = "page-count-of-the-package"
DELIVERED = [1, 2, 3, 4, 5]
ENCLOSURES = [
    "screening-test-data",
    "lot-acceptance-test-data",
    "certificate-of-conformity",
]


def build_standard(**overrides):
    """A configuration the enclosed data can be attached to."""
    record = {
        "drawing_reference": "DRW-4471",
        "drawing_issue": "C",
        "specification_reference": "DET-SPEC-1234",
    }
    record.update(overrides)
    return record


def sheet(**overrides):
    """A cover sheet that agrees with the shipment behind it."""
    record = {
        "first_serial": 1,
        "last_serial": 5,
        "declared_quantity": 5,
        "listed_enclosures": list(ENCLOSURES),
        "build_standard": build_standard(),
    }
    record.update(overrides)
    return record


def present_fields(**states):
    """Every cover-sheet field present, with named exceptions."""
    fields = []
    for name in sorted(COVER_SHEET_FIELDS):
        entry = {"field": name, "state": "present"}
        if name in states:
            entry["state"] = states[name]
        fields.append(entry)
    return fields


def run(**overrides):
    """Grade one cover sheet."""
    case = {
        "batch_id": "HYB-1234-B07",
        "sheet": sheet(),
        "delivered_serials": list(DELIVERED),
        "enclosed_records": list(ENCLOSURES),
        "fields": present_fields(),
    }
    case.update(overrides)
    return assess_cover_sheet(**case)


class SerialRangeTests(unittest.TestCase):
    def test_a_range_that_matches_the_shipment_raises_nothing(self):
        result = serial_range_coverage(1, 5, DELIVERED)
        self.assertTrue(result["range_matches_shipment"])
        self.assertEqual(result["findings"], [])

    def test_a_unit_outside_the_printed_range_is_named(self):
        result = serial_range_coverage(1, 4, DELIVERED)
        self.assertEqual(result["serials_outside_range"], [5])
        self.assertIn("delivered-unit-outside-the-printed-serial-range", result["findings"])

    def test_a_range_wider_than_the_shipment_is_reported(self):
        result = serial_range_coverage(1, 9, DELIVERED)
        self.assertEqual(result["unused_numbers_in_range"], 4)
        self.assertIn("serial-range-wider-than-the-units-delivered", result["findings"])

    def test_the_span_counts_both_ends(self):
        self.assertEqual(serial_range_coverage(10, 14, [10, 11, 12, 13, 14])["range_span"], 5)

    def test_a_range_that_ends_before_it_begins_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_range_coverage(9, 2, DELIVERED)

    def test_an_empty_shipment_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_range_coverage(1, 5, [])

    def test_a_repeated_delivered_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_range_coverage(1, 5, [1, 2, 2])

    def test_a_fractional_serial_is_rejected(self):
        with self.assertRaises(ValueError):
            serial_range_coverage(1, 5, [1, 2.5])


class EnclosureIndexTests(unittest.TestCase):
    def test_an_index_matching_the_package_reconciles(self):
        result = reconcile_enclosures(ENCLOSURES, ENCLOSURES)
        self.assertTrue(result["index_reconciled"])
        self.assertAlmostEqual(result["index_agreement_ratio"], 1.0, places=9)

    def test_a_listed_record_that_is_absent_is_named(self):
        result = reconcile_enclosures(ENCLOSURES, ENCLOSURES[:2])
        self.assertEqual(result["listed_but_absent"], ["certificate-of-conformity"])
        self.assertIn("enclosure-listed-but-not-in-the-package", result["findings"])

    def test_a_record_present_but_unlisted_is_named(self):
        result = reconcile_enclosures(ENCLOSURES, ENCLOSURES + ["rework-records"])
        self.assertEqual(result["present_but_unlisted"], ["rework-records"])
        self.assertIn("record-in-the-package-but-not-on-the-index", result["findings"])

    def test_the_agreement_ratio_falls_with_a_missing_enclosure(self):
        result = reconcile_enclosures(ENCLOSURES, ENCLOSURES[:2])
        self.assertAlmostEqual(result["index_agreement_ratio"], 2.0 / 3.0, places=9)

    def test_an_empty_index_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_enclosures([], ENCLOSURES)

    def test_a_repeated_index_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_enclosures(ENCLOSURES + ENCLOSURES[:1], ENCLOSURES)

    def test_a_blank_index_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_enclosures(["screening-test-data", "  "], ENCLOSURES)


class QuantityTests(unittest.TestCase):
    def test_three_agreeing_statements_reconcile(self):
        coverage = serial_range_coverage(1, 5, DELIVERED)
        self.assertTrue(quantity_reconciliation(5, DELIVERED, coverage)["reconciled"])

    def test_a_quantity_that_differs_from_the_serials_is_reported(self):
        coverage = serial_range_coverage(1, 5, DELIVERED)
        result = quantity_reconciliation(6, DELIVERED, coverage)
        self.assertIn("declared-quantity-differs-from-the-serials-handed-over", result["findings"])

    def test_a_quantity_that_differs_from_the_range_span_is_reported(self):
        coverage = serial_range_coverage(1, 9, DELIVERED)
        result = quantity_reconciliation(5, DELIVERED, coverage)
        self.assertIn(
            "declared-quantity-differs-from-the-printed-range-span", result["findings"]
        )

    def test_a_zero_quantity_is_rejected(self):
        coverage = serial_range_coverage(1, 5, DELIVERED)
        with self.assertRaises(ValueError):
            quantity_reconciliation(0, DELIVERED, coverage)

    def test_a_coverage_record_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            quantity_reconciliation(5, DELIVERED, [1, 5])


class BuildStandardTests(unittest.TestCase):
    def test_a_complete_build_standard_raises_nothing(self):
        self.assertEqual(build_standard_findings(build_standard()), [])

    def test_a_missing_drawing_issue_is_reported(self):
        self.assertIn(
            "build-standard-without-a-drawing-issue",
            build_standard_findings(build_standard(drawing_issue="")),
        )

    def test_a_missing_specification_reference_is_reported(self):
        record = build_standard()
        del record["specification_reference"]
        self.assertIn(
            "build-standard-without-a-specification-reference", build_standard_findings(record)
        )

    def test_a_build_standard_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            build_standard_findings("DRW-4471 issue C")


class FieldTests(unittest.TestCase):
    def test_every_mandatory_field_carries_a_published_weight(self):
        for name in MANDATORY_COVER_SHEET_FIELDS:
            self.assertIn(name, COVER_SHEET_FIELDS)

    def test_an_unknown_cover_sheet_field_is_rejected(self):
        with self.assertRaises(ValueError):
            cover_sheet_field_weight("company-logo")

    def test_an_unknown_field_state_is_rejected(self):
        with self.assertRaises(ValueError):
            field_state_credit("smudged-but-guessable")

    def test_a_field_nobody_mentioned_defaults_to_absent(self):
        self.assertEqual(normalize_field({"field": SPARE_FIELD})["state"], "absent")

    def test_a_present_field_earns_its_full_weight(self):
        record = assess_field({"field": SPARE_FIELD, "state": "present"})
        self.assertAlmostEqual(record["weighted_credit"], COVER_SHEET_FIELDS[SPARE_FIELD], places=9)

    def test_a_missing_mandatory_field_is_marked_missing(self):
        self.assertTrue(assess_field({"field": "serial-range"})["mandatory_missing"])

    def test_an_illegible_mandatory_field_is_flagged_separately(self):
        record = assess_field({"field": "part-number", "state": "illegible"})
        self.assertTrue(record["mandatory_illegible"])
        self.assertFalse(record["mandatory_missing"])

    def test_a_fully_present_sheet_reaches_a_full_index(self):
        records = [assess_field(entry) for entry in present_fields()]
        self.assertAlmostEqual(cover_sheet_completeness_index(records), 1.0, places=9)

    def test_an_empty_field_set_is_rejected(self):
        with self.assertRaises(ValueError):
            cover_sheet_completeness_index([])


class WholeCoverSheetTests(unittest.TestCase):
    def test_a_sound_cover_sheet_passes_with_no_findings(self):
        result = run()
        self.assertEqual(result["verdict"], "cover-sheet-acceptable")
        self.assertTrue(result["cover_sheet_accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["cover_sheet_completeness_index"], 1.0, places=9)

    def test_every_verdict_returned_is_one_of_the_published_verdicts(self):
        self.assertIn(run()["verdict"], VERDICTS)

    def test_a_sheet_missing_a_mandatory_field_is_incomplete(self):
        result = run(fields=present_fields(**{"enclosure-index": "absent"}))
        self.assertEqual(result["verdict"], "cover-sheet-assessment-incomplete")

    def test_a_unit_outside_the_range_rejects_the_sheet(self):
        result = run(sheet=sheet(last_serial=4, declared_quantity=4))
        self.assertEqual(result["verdict"], "cover-sheet-rejected")
        self.assertFalse(result["cover_sheet_accepted"])

    def test_an_unlisted_enclosure_rejects_the_sheet(self):
        result = run(enclosed_records=ENCLOSURES + ["rework-records"])
        self.assertEqual(result["verdict"], "cover-sheet-rejected")
        self.assertIn(
            "record-in-the-package-but-not-on-the-index",
            [f["finding"] for f in result["findings"]],
        )

    def test_a_quantity_that_does_not_reconcile_rejects_the_sheet(self):
        result = run(sheet=sheet(declared_quantity=6))
        self.assertEqual(result["verdict"], "cover-sheet-rejected")

    def test_a_build_standard_without_a_drawing_issue_rejects_the_sheet(self):
        result = run(sheet=sheet(build_standard=build_standard(drawing_issue="  ")))
        self.assertEqual(result["verdict"], "cover-sheet-rejected")

    def test_an_observation_on_an_optional_field_leaves_open_actions(self):
        result = run(fields=present_fields(**{SPARE_FIELD: "present-with-observation"}))
        self.assertEqual(result["verdict"], "cover-sheet-acceptable-with-open-actions")
        self.assertTrue(result["cover_sheet_accepted"])

    def test_a_field_nobody_listed_is_graded_as_absent(self):
        result = run(fields=[{"field": SPARE_FIELD, "state": "present"}])
        states = {r["field"]: r["state"] for r in result["fields"]}
        self.assertEqual(states["issue-date"], "absent")
        self.assertEqual(len(result["fields"]), len(COVER_SHEET_FIELDS))

    def test_a_repeated_cover_sheet_field_is_rejected(self):
        with self.assertRaises(ValueError):
            run(fields=present_fields() + [{"field": SPARE_FIELD, "state": "present"}])

    def test_a_blank_batch_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            run(batch_id="   ")

    def test_a_sheet_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            run(sheet=["HYB-1234-B07"])


class ConstantsTests(unittest.TestCase):
    def test_the_tolerance_is_small_enough_to_separate_the_bounds(self):
        self.assertLess(COVER_SHEET_TOLERANCE, 1e-6)

    def test_the_field_credits_span_the_published_scale(self):
        self.assertAlmostEqual(max(FIELD_STATE_CREDIT.values()), 1.0, places=9)
        self.assertAlmostEqual(min(FIELD_STATE_CREDIT.values()), 0.0, places=9)

    def test_the_acceptance_index_sits_under_a_fully_present_sheet(self):
        self.assertLess(ACCEPTANCE_COVER_SHEET_INDEX, 1.0)

    def test_every_mandatory_field_outweighs_the_lightest_optional_one(self):
        lightest = min(COVER_SHEET_FIELDS.values())
        for name in MANDATORY_COVER_SHEET_FIELDS:
            self.assertGreater(COVER_SHEET_FIELDS[name], lightest, name)


if __name__ == "__main__":
    unittest.main()
