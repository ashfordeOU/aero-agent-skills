"""Contract tests for the shelf-life procurement data requirements logic."""

import datetime
import unittest

from q7022_procurement_data_requirements_logic import (
    FLOOR_REMAINING_FRACTION,
    MANDATORY_DATA_ITEMS,
    TARGET_REMAINING_FRACTION,
    assess_procurement_package,
    declared_duration_findings,
    grade_remaining_life,
    missing_data_items,
    parse_date,
    remaining_days_at_receipt,
    remaining_fraction,
    shelf_life_days,
    storage_evidence_findings,
    validate_date_chain,
)


def base_package(**overrides):
    """A complete, compliant two-part epoxy delivery: 400-day life, 40 days old."""
    package = {
        "manufacturer": "Adhesive supplier",
        "batch_identifier": "LOT-4471",
        "manufacture_date": "2026-01-01",
        "expiry_date": "2027-02-05",
        "conformity_certificate": "CoC-4471",
        "receipt_date": "2026-02-10",
        "declared_shelf_life_days": 400,
        "recorded_storage_temperature_c": (2.0, 7.0),
        "specified_storage_temperature_c": (2.0, 8.0),
        "recorded_storage_humidity_pct": (20.0, 50.0),
        "specified_storage_humidity_pct": (0.0, 60.0),
    }
    package.update(overrides)
    return package


class ParseDateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2026-03-04"), datetime.date(2026, 3, 4))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 3, 4)
        self.assertEqual(parse_date(day), day)

    def test_datetime_is_narrowed_to_its_date(self):
        stamp = datetime.datetime(2026, 3, 4, 17, 30)
        self.assertEqual(parse_date(stamp), datetime.date(2026, 3, 4))

    def test_non_iso_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("04/03/2026")

    def test_empty_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20260304)

    def test_impossible_calendar_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2026-02-30")


class MandatoryItemTests(unittest.TestCase):
    def test_complete_package_has_no_missing_items(self):
        self.assertEqual(missing_data_items(base_package()), [])

    def test_absent_expiry_date_is_reported(self):
        package = base_package()
        del package["expiry_date"]
        self.assertIn("expiry_date", missing_data_items(package))

    def test_blank_batch_identifier_counts_as_missing(self):
        self.assertIn("batch_identifier", missing_data_items(base_package(batch_identifier="  ")))

    def test_certificate_declared_false_counts_as_missing(self):
        self.assertIn(
            "conformity_certificate",
            missing_data_items(base_package(conformity_certificate=False)),
        )

    def test_every_mandatory_item_is_detected_when_absent(self):
        missing = missing_data_items({})
        self.assertEqual(sorted(missing), sorted(MANDATORY_DATA_ITEMS))

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            missing_data_items(["manufacturer"])


class DateChainTests(unittest.TestCase):
    def test_consistent_chain_has_no_findings(self):
        _, findings = validate_date_chain("2026-01-01", "2026-02-10", "2027-02-05")
        self.assertEqual(findings, [])

    def test_expiry_before_manufacture_is_flagged(self):
        _, findings = validate_date_chain("2026-06-01", "2026-06-10", "2026-01-01")
        self.assertTrue(any("does not follow" in f for f in findings))

    def test_receipt_before_manufacture_is_flagged(self):
        _, findings = validate_date_chain("2026-06-01", "2026-05-01", "2027-06-01")
        self.assertTrue(any("precedes the manufacture" in f for f in findings))

    def test_receipt_after_expiry_is_flagged(self):
        _, findings = validate_date_chain("2026-01-01", "2027-06-01", "2027-02-05")
        self.assertTrue(any("already past its expiry" in f for f in findings))


class ShelfLifeArithmeticTests(unittest.TestCase):
    def test_full_shelf_life_in_days(self):
        self.assertEqual(shelf_life_days("2026-01-01", "2027-02-05"), 400)

    def test_zero_length_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_days("2026-01-01", "2026-01-01")

    def test_remaining_days_at_receipt(self):
        self.assertEqual(remaining_days_at_receipt("2026-02-10", "2027-02-05"), 360)

    def test_remaining_days_are_negative_past_expiry(self):
        self.assertLess(remaining_days_at_receipt("2027-03-05", "2027-02-05"), 0)

    def test_remaining_fraction_is_the_day_ratio(self):
        self.assertAlmostEqual(
            remaining_fraction("2026-01-01", "2026-02-10", "2027-02-05"), 0.9, places=9
        )


class DeclaredDurationTests(unittest.TestCase):
    def test_agreeing_duration_has_no_finding(self):
        self.assertEqual(declared_duration_findings(base_package()), [])

    def test_disagreeing_duration_is_flagged(self):
        findings = declared_duration_findings(base_package(declared_shelf_life_days=365))
        self.assertTrue(any("disagrees" in f for f in findings))

    def test_absent_duration_is_not_a_finding(self):
        package = base_package()
        del package["declared_shelf_life_days"]
        self.assertEqual(declared_duration_findings(package), [])

    def test_non_numeric_duration_rejected(self):
        with self.assertRaises(ValueError):
            declared_duration_findings(base_package(declared_shelf_life_days="400"))

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            declared_duration_findings(base_package(declared_shelf_life_days=-10))


class StorageEvidenceTests(unittest.TestCase):
    def test_envelope_inside_the_specified_limits_is_clean(self):
        self.assertEqual(storage_evidence_findings(base_package()), [])

    def test_over_temperature_excursion_is_flagged(self):
        findings = storage_evidence_findings(
            base_package(recorded_storage_temperature_c=(2.0, 14.0))
        )
        self.assertTrue(any("above the specified" in f for f in findings))

    def test_under_temperature_excursion_is_flagged(self):
        findings = storage_evidence_findings(
            base_package(recorded_storage_temperature_c=(-4.0, 7.0))
        )
        self.assertTrue(any("below the specified" in f for f in findings))

    def test_touching_the_specified_bound_is_not_an_excursion(self):
        findings = storage_evidence_findings(
            base_package(recorded_storage_temperature_c=(2.0, 8.0))
        )
        self.assertEqual(findings, [])

    def test_no_evidence_at_all_is_a_finding(self):
        package = base_package()
        for key in (
            "recorded_storage_temperature_c",
            "recorded_storage_humidity_pct",
        ):
            del package[key]
        findings = storage_evidence_findings(package)
        self.assertTrue(any("no storage evidence" in f for f in findings))

    def test_evidence_without_a_specified_limit_is_a_finding(self):
        package = base_package()
        del package["specified_storage_humidity_pct"]
        findings = storage_evidence_findings(package)
        self.assertTrue(any("no specified humidity limit" in f for f in findings))

    def test_inverted_envelope_rejected(self):
        with self.assertRaises(ValueError):
            storage_evidence_findings(base_package(recorded_storage_temperature_c=(9.0, 2.0)))

    def test_malformed_envelope_rejected(self):
        with self.assertRaises(ValueError):
            storage_evidence_findings(base_package(recorded_storage_temperature_c=(2.0,)))


class RemainingGradeTests(unittest.TestCase):
    def test_full_life_is_adequate(self):
        self.assertEqual(grade_remaining_life(1.0), "adequate")

    def test_exactly_at_the_target_is_adequate(self):
        self.assertEqual(grade_remaining_life(TARGET_REMAINING_FRACTION), "adequate")

    def test_between_floor_and_target_is_short(self):
        self.assertEqual(grade_remaining_life(0.6), "short")

    def test_exactly_at_the_floor_is_short(self):
        self.assertEqual(grade_remaining_life(FLOOR_REMAINING_FRACTION), "short")

    def test_below_the_floor_is_insufficient(self):
        self.assertEqual(grade_remaining_life(0.2), "insufficient")

    def test_non_numeric_fraction_rejected(self):
        with self.assertRaises(ValueError):
            grade_remaining_life("0.8")


class AssessmentTests(unittest.TestCase):
    def test_compliant_delivery_is_accepted(self):
        result = assess_procurement_package(base_package())
        self.assertEqual(result["disposition"], "accept")
        self.assertEqual(result["findings"], [])

    def test_accepted_delivery_reports_its_remaining_life(self):
        result = assess_procurement_package(base_package())
        self.assertEqual(result["shelf_life_days"], 400)
        self.assertEqual(result["remaining_days"], 360)
        self.assertAlmostEqual(result["remaining_fraction"], 0.9, places=9)

    def test_missing_mandatory_item_rejects_before_any_arithmetic(self):
        package = base_package()
        del package["conformity_certificate"]
        result = assess_procurement_package(package)
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["remaining_fraction"], None)

    def test_short_remaining_life_accepts_with_actions(self):
        result = assess_procurement_package(base_package(receipt_date="2026-05-31"))
        self.assertEqual(result["disposition"], "accept-with-actions")
        self.assertEqual(result["remaining_grade"], "short")

    def test_insufficient_remaining_life_is_rejected(self):
        result = assess_procurement_package(base_package(receipt_date="2026-11-01"))
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["remaining_grade"], "insufficient")

    def test_storage_excursion_rejects_an_otherwise_fresh_lot(self):
        result = assess_procurement_package(
            base_package(recorded_storage_temperature_c=(2.0, 22.0))
        )
        self.assertEqual(result["disposition"], "reject")

    def test_absent_storage_evidence_downgrades_to_actions(self):
        package = base_package()
        del package["recorded_storage_temperature_c"]
        del package["recorded_storage_humidity_pct"]
        result = assess_procurement_package(package)
        self.assertEqual(result["disposition"], "accept-with-actions")

    def test_broken_date_chain_is_rejected(self):
        result = assess_procurement_package(base_package(receipt_date="2025-06-01"))
        self.assertEqual(result["disposition"], "reject")
        self.assertEqual(result["remaining_grade"], "unknown")

    def test_missing_receipt_date_rejected(self):
        package = base_package()
        del package["receipt_date"]
        with self.assertRaises(ValueError):
            assess_procurement_package(package)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_procurement_package("LOT-4471")

    def test_boundary_remaining_fraction_lands_on_the_target(self):
        # 400-day life received exactly 100 days in leaves 0.75 of the life.
        result = assess_procurement_package(base_package(receipt_date="2026-04-11"))
        self.assertAlmostEqual(
            result["remaining_fraction"], TARGET_REMAINING_FRACTION, places=9
        )
        self.assertEqual(result["remaining_grade"], "adequate")


if __name__ == "__main__":
    unittest.main()
