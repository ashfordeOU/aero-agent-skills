"""Contract tests for the clause 4.7 retained record-package logic."""

import datetime
import unittest

from q6013_class_1_documentation_logic import (
    COMPLETENESS_TOLERANCE,
    DEFAULT_RETENTION_FLOOR_YEARS,
    MANDATORY_RECORDS,
    OPTIONAL_RECORDS,
    RECOGNIZED_RECORDS,
    absent_record_types,
    assess_record,
    assess_record_package,
    normalize_token,
    package_completeness,
    reconcile_part_coverage,
    retention_end,
    validate_activity,
    validate_iso_date,
    validate_record,
    validate_record_type,
)

ACTIVITY = {
    "part_number": "XS-4417-QT",
    "lot_identifier": "date code 2341",
    "project": "orbital demonstrator",
}


def _record(record_type="evaluation-report", **overrides):
    record = {
        "record_type": record_type,
        "identifier": "REC-%s" % record_type[:6].upper(),
        "issue": "issue 1",
        "date": "2026-03-01",
        "approved_by": "component engineering authority",
        "retention_years": 12,
        "covers_part_numbers": ["XS-4417-QT"],
    }
    record.update(overrides)
    return record


def _full_records():
    return [_record(record_type=t) for t in MANDATORY_RECORDS]


def _package(**overrides):
    package = {
        "activity": dict(ACTIVITY),
        "parts_list": ["XS-4417-QT"],
        "records": _full_records(),
        "retention_floor_years": 10,
        "required_retention_until": "2035-01-01",
    }
    package.update(overrides)
    return package


class ActivityTests(unittest.TestCase):
    def test_activity_returned_stripped(self):
        activity = validate_activity(dict(ACTIVITY, part_number="  XS-4417-QT "))
        self.assertEqual(activity["part_number"], "XS-4417-QT")

    def test_missing_lot_identifier_rejected(self):
        bad = dict(ACTIVITY)
        del bad["lot_identifier"]
        with self.assertRaises(ValueError):
            validate_activity(bad)

    def test_blank_project_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(dict(ACTIVITY, project="   "))

    def test_non_mapping_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity("XS-4417-QT")

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Screening_Report"), "screening-report"
        )


class RecordValidationTests(unittest.TestCase):
    def test_record_returned_validated(self):
        entry = validate_record(_record())
        self.assertEqual(entry["record_type"], "evaluation-report")
        self.assertEqual(entry["date"], datetime.date(2026, 3, 1))

    def test_unknown_record_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_record_type("holiday-photographs")

    def test_every_recognized_type_validates(self):
        for record_type in RECOGNIZED_RECORDS:
            self.assertEqual(validate_record_type(record_type), record_type)

    def test_optional_types_are_not_in_the_mandatory_set(self):
        for record_type in OPTIONAL_RECORDS:
            self.assertNotIn(record_type, MANDATORY_RECORDS)

    def test_missing_issue_rejected(self):
        bad = _record()
        del bad["issue"]
        with self.assertRaises(ValueError):
            validate_record(bad)

    def test_blank_approving_authority_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(approved_by="  "))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(date="01-03-2026"))

    def test_date_object_accepted(self):
        entry = validate_record(_record(date=datetime.date(2026, 3, 1)))
        self.assertEqual(entry["date"], datetime.date(2026, 3, 1))

    def test_zero_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(retention_years=0))

    def test_fractional_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(_record(retention_years=10.5))

    def test_repeated_part_on_one_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_record(
                _record(covers_part_numbers=["XS-4417-QT", "XS-4417-QT"])
            )

    def test_iso_date_helper_rejects_a_non_string(self):
        with self.assertRaises(ValueError):
            validate_iso_date(20260301, "record date")


class RetentionTests(unittest.TestCase):
    def test_retention_end_is_the_same_day_years_later(self):
        self.assertEqual(
            retention_end("2026-03-01", 10), datetime.date(2036, 3, 1)
        )

    def test_leap_day_start_falls_back_to_the_28th(self):
        self.assertEqual(
            retention_end("2024-02-29", 1), datetime.date(2025, 2, 28)
        )

    def test_leap_day_start_stays_on_the_29th_in_a_leap_year(self):
        self.assertEqual(
            retention_end("2024-02-29", 4), datetime.date(2028, 2, 29)
        )

    def test_retention_below_the_floor_is_a_finding(self):
        entry = assess_record(_record(retention_years=3), floor_years=10)
        self.assertFalse(entry["acceptable"])
        self.assertTrue(any("floor" in f for f in entry["findings"]))

    def test_retention_exactly_on_the_floor_is_admissible(self):
        entry = assess_record(_record(retention_years=10), floor_years=10)
        self.assertEqual(entry["retention_years"], entry["retention_floor_years"])
        self.assertTrue(entry["acceptable"])

    def test_retention_end_before_the_horizon_is_a_finding(self):
        entry = assess_record(
            _record(retention_years=5), floor_years=5, required_until="2035-01-01"
        )
        self.assertFalse(entry["reaches_horizon"])

    def test_retention_end_on_the_horizon_reaches_it(self):
        entry = assess_record(
            _record(date="2026-01-01", retention_years=9),
            floor_years=5,
            required_until="2035-01-01",
        )
        self.assertEqual(entry["retention_end"], datetime.date(2035, 1, 1))
        self.assertTrue(entry["reaches_horizon"])

    def test_default_floor_applies_when_none_declared(self):
        entry = assess_record(_record())
        self.assertEqual(
            entry["retention_floor_years"], DEFAULT_RETENTION_FLOOR_YEARS
        )

    def test_record_covering_no_part_is_a_finding(self):
        entry = assess_record(_record(covers_part_numbers=[]))
        self.assertTrue(any("no part number" in f for f in entry["findings"]))


class CompletenessTests(unittest.TestCase):
    def test_full_package_names_nothing_absent(self):
        self.assertEqual(absent_record_types(MANDATORY_RECORDS), [])

    def test_absent_type_is_named(self):
        present = [t for t in MANDATORY_RECORDS if t != "screening-report"]
        self.assertEqual(absent_record_types(present), ["screening-report"])

    def test_optional_records_do_not_raise_completeness(self):
        present = list(MANDATORY_RECORDS[:-1]) + list(OPTIONAL_RECORDS)
        self.assertEqual(len(absent_record_types(present)), 1)

    def test_full_package_completeness_is_unity(self):
        self.assertAlmostEqual(package_completeness(MANDATORY_RECORDS), 1.0, places=9)

    def test_half_a_package_reports_a_partial_fraction(self):
        half = MANDATORY_RECORDS[: len(MANDATORY_RECORDS) // 2]
        self.assertAlmostEqual(package_completeness(half), 0.5, places=9)

    def test_completeness_tolerance_is_representation_sized(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)

    def test_unknown_type_in_the_present_set_rejected(self):
        with self.assertRaises(ValueError):
            absent_record_types(["holiday-photographs"])

    def test_non_collection_present_types_rejected(self):
        with self.assertRaises(ValueError):
            absent_record_types("screening-report")


class CoverageTests(unittest.TestCase):
    def test_matching_list_and_coverage_reconcile(self):
        coverage = reconcile_part_coverage(
            ["XS-4417-QT"], [validate_record(_record())]
        )
        self.assertEqual(coverage["uncovered_parts"], [])
        self.assertEqual(coverage["unlisted_parts"], [])

    def test_listed_part_with_no_record_is_named(self):
        coverage = reconcile_part_coverage(
            ["XS-4417-QT", "XS-4419-QT"], [validate_record(_record())]
        )
        self.assertEqual(coverage["uncovered_parts"], ["XS-4419-QT"])

    def test_covered_part_not_on_the_list_is_named(self):
        coverage = reconcile_part_coverage(
            ["XS-4417-QT"],
            [validate_record(_record(covers_part_numbers=["XS-9000-ZZ"]))],
        )
        self.assertEqual(coverage["unlisted_parts"], ["XS-9000-ZZ"])

    def test_empty_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_part_coverage([], [validate_record(_record())])

    def test_repeated_part_on_the_list_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_part_coverage(
                ["XS-4417-QT", "XS-4417-QT"], [validate_record(_record())]
            )

    def test_unvalidated_entry_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_part_coverage(["XS-4417-QT"], [{"identifier": "REC-1"}])


class PackageAssessmentTests(unittest.TestCase):
    def test_complete_package_is_fit_to_retain(self):
        result = assess_record_package(_package())
        self.assertTrue(result["fit_to_retain"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["package_complete"])

    def test_complete_package_reports_unity_completeness(self):
        result = assess_record_package(_package())
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_absent_mandatory_report_reaches_the_verdict(self):
        records = [r for r in _full_records()
                   if r["record_type"] != "radiation-verification-report"]
        result = assess_record_package(_package(records=records))
        self.assertEqual(
            result["absent_record_types"], ["radiation-verification-report"]
        )
        self.assertFalse(result["fit_to_retain"])
        self.assertFalse(result["package_complete"])

    def test_short_retention_reaches_the_verdict(self):
        records = _full_records()
        records[0]["retention_years"] = 2
        result = assess_record_package(_package(records=records))
        self.assertFalse(result["fit_to_retain"])

    def test_repeated_record_type_rejected(self):
        records = _full_records() + [_record(record_type="evaluation-report")]
        with self.assertRaises(ValueError):
            assess_record_package(_package(records=records))

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_record_package(_package(records=[]))

    def test_missing_package_key_rejected(self):
        package = _package()
        del package["parts_list"]
        with self.assertRaises(ValueError):
            assess_record_package(package)

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            assess_record_package(["activity"])

    def test_uncovered_listed_part_reaches_the_verdict(self):
        result = assess_record_package(
            _package(parts_list=["XS-4417-QT", "XS-4419-QT"])
        )
        self.assertFalse(result["fit_to_retain"])
        self.assertIn("XS-4419-QT", result["coverage"]["uncovered_parts"])

    def test_horizon_shortfall_reaches_the_verdict(self):
        result = assess_record_package(
            _package(required_retention_until="2045-01-01")
        )
        self.assertFalse(result["fit_to_retain"])

    def test_every_finding_is_named_not_only_the_first(self):
        records = [r for r in _full_records()
                   if r["record_type"] not in ("screening-report",
                                               "lot-acceptance-report")]
        records[0]["retention_years"] = 1
        result = assess_record_package(
            _package(records=records, parts_list=["XS-4417-QT", "XS-4419-QT"])
        )
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()
