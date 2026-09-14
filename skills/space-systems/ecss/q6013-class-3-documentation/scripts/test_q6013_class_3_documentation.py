"""Contract tests for the clause 6.7 class 3 kept-document logic."""

import datetime
import unittest

from q6013_class_3_documentation_logic import (
    ABOVE_MINIMUM_DOCUMENTS,
    COMPLETENESS_TOLERANCE,
    CUSTODY_MODES,
    DEFAULT_RETENTION_FLOOR_YEARS,
    MINIMUM_DOCUMENTS,
    PROJECT_REACHABLE_CUSTODY,
    RECOGNIZED_DOCUMENTS,
    above_minimum_types,
    absent_minimum_types,
    assess_document,
    assess_documentation_file,
    minimum_set_completeness,
    normalize_token,
    retention_end,
    validate_activity,
    validate_custody,
    validate_document,
    validate_document_type,
    validate_iso_date,
)

ACTIVITY = {
    "part_number": "CM-8802-TR",
    "supplier": "catalogue distributor",
    "project": "technology demonstrator",
}


def _document(document_type="procurement-specification", **overrides):
    document = {
        "document_type": document_type,
        "identifier": "DOC-%s" % document_type[:6].upper(),
        "issue": "issue 1",
        "date": "2026-04-01",
        "custody": "project-held",
        "retention_years": 4,
        "covers_part_numbers": ["CM-8802-TR"],
    }
    document.update(overrides)
    return document


def _minimum_documents():
    return [_document(document_type=t) for t in MINIMUM_DOCUMENTS]


def _file(**overrides):
    kept = {
        "activity": dict(ACTIVITY),
        "documents": _minimum_documents(),
        "retention_floor_years": 2,
        "required_retention_until": "2029-01-01",
    }
    kept.update(overrides)
    return kept


class ActivityTests(unittest.TestCase):
    def test_activity_returned_stripped(self):
        activity = validate_activity(dict(ACTIVITY, part_number="  CM-8802-TR "))
        self.assertEqual(activity["part_number"], "CM-8802-TR")

    def test_missing_supplier_rejected(self):
        bad = dict(ACTIVITY)
        del bad["supplier"]
        with self.assertRaises(ValueError):
            validate_activity(bad)

    def test_blank_project_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(dict(ACTIVITY, project="  "))

    def test_non_mapping_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity("CM-8802-TR")

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(
            normalize_token("Traceability_Record"), "traceability-record"
        )


class DocumentValidationTests(unittest.TestCase):
    def test_document_returned_validated(self):
        entry = validate_document(_document())
        self.assertEqual(entry["document_type"], "procurement-specification")
        self.assertEqual(entry["date"], datetime.date(2026, 4, 1))

    def test_unknown_document_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_document_type("expenses-claim")

    def test_every_recognized_type_validates(self):
        for document_type in RECOGNIZED_DOCUMENTS:
            self.assertEqual(validate_document_type(document_type), document_type)

    def test_above_minimum_types_are_not_in_the_minimum_set(self):
        for document_type in ABOVE_MINIMUM_DOCUMENTS:
            self.assertNotIn(document_type, MINIMUM_DOCUMENTS)

    def test_missing_issue_rejected(self):
        bad = _document()
        del bad["issue"]
        with self.assertRaises(ValueError):
            validate_document(bad)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(_document(identifier="   "))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(_document(date="01-04-2026"))

    def test_date_object_accepted(self):
        entry = validate_document(_document(date=datetime.date(2026, 4, 1)))
        self.assertEqual(entry["date"], datetime.date(2026, 4, 1))

    def test_zero_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(_document(retention_years=0))

    def test_fractional_retention_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(_document(retention_years=3.5))

    def test_repeated_part_on_one_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_document(
                _document(covers_part_numbers=["CM-8802-TR", "CM-8802-TR"])
            )

    def test_iso_date_helper_rejects_a_non_string(self):
        with self.assertRaises(ValueError):
            validate_iso_date(20260401, "document date")


class CustodyTests(unittest.TestCase):
    def test_every_custody_mode_validates(self):
        for mode in CUSTODY_MODES:
            self.assertEqual(validate_custody(mode), mode)

    def test_unknown_custody_mode_rejected(self):
        with self.assertRaises(ValueError):
            validate_custody("somewhere-in-the-office")

    def test_reachable_modes_are_a_subset_of_the_modes(self):
        for mode in PROJECT_REACHABLE_CUSTODY:
            self.assertIn(mode, CUSTODY_MODES)

    def test_no_access_mode_is_not_reachable(self):
        self.assertNotIn("supplier-held-no-access", PROJECT_REACHABLE_CUSTODY)

    def test_unreachable_minimum_document_is_a_finding(self):
        entry = assess_document(_document(custody="supplier-held-no-access"))
        self.assertFalse(entry["project_reachable"])
        self.assertTrue(any("cannot produce" in f for f in entry["findings"]))

    def test_supplier_access_without_a_reference_is_a_finding(self):
        entry = assess_document(_document(custody="supplier-held-with-access"))
        self.assertTrue(any("access reference" in f for f in entry["findings"]))

    def test_supplier_access_with_a_reference_is_admissible(self):
        entry = assess_document(
            _document(
                custody="supplier-held-with-access",
                access_reference="purchase order clause 14",
            )
        )
        self.assertTrue(entry["acceptable"])

    def test_above_minimum_document_held_with_no_access_is_not_a_finding(self):
        entry = assess_document(
            _document(
                document_type="evaluation-report",
                custody="supplier-held-no-access",
            )
        )
        self.assertFalse(entry["is_minimum"])
        self.assertEqual(entry["findings"], [])


class RetentionTests(unittest.TestCase):
    def test_retention_end_is_the_same_day_years_later(self):
        self.assertEqual(retention_end("2026-04-01", 4), datetime.date(2030, 4, 1))

    def test_leap_day_start_falls_back_to_the_28th(self):
        self.assertEqual(retention_end("2024-02-29", 1), datetime.date(2025, 2, 28))

    def test_leap_day_start_stays_on_the_29th_in_a_leap_year(self):
        self.assertEqual(retention_end("2024-02-29", 4), datetime.date(2028, 2, 29))

    def test_retention_below_the_floor_is_a_finding(self):
        entry = assess_document(_document(retention_years=1), floor_years=2)
        self.assertTrue(any("floor" in f for f in entry["findings"]))

    def test_retention_exactly_on_the_floor_is_admissible(self):
        entry = assess_document(_document(retention_years=2), floor_years=2)
        self.assertEqual(entry["retention_years"], entry["retention_floor_years"])
        self.assertTrue(entry["acceptable"])

    def test_retention_end_before_the_horizon_is_a_finding(self):
        entry = assess_document(
            _document(retention_years=2), floor_years=2, required_until="2035-01-01"
        )
        self.assertFalse(entry["reaches_horizon"])

    def test_retention_end_on_the_horizon_reaches_it(self):
        entry = assess_document(
            _document(date="2026-01-01", retention_years=3),
            floor_years=2,
            required_until="2029-01-01",
        )
        self.assertEqual(entry["retention_end"], datetime.date(2029, 1, 1))
        self.assertTrue(entry["reaches_horizon"])

    def test_default_floor_applies_when_none_declared(self):
        entry = assess_document(_document())
        self.assertEqual(
            entry["retention_floor_years"], DEFAULT_RETENTION_FLOOR_YEARS
        )

    def test_minimum_document_covering_no_part_is_a_finding(self):
        entry = assess_document(_document(covers_part_numbers=[]))
        self.assertTrue(any("no part number" in f for f in entry["findings"]))


class MinimumSetTests(unittest.TestCase):
    def test_full_minimum_set_names_nothing_absent(self):
        self.assertEqual(absent_minimum_types(MINIMUM_DOCUMENTS), [])

    def test_absent_minimum_type_is_named(self):
        present = [t for t in MINIMUM_DOCUMENTS if t != "traceability-record"]
        self.assertEqual(absent_minimum_types(present), ["traceability-record"])

    def test_above_minimum_documents_do_not_raise_completeness(self):
        present = list(MINIMUM_DOCUMENTS[:-1]) + list(ABOVE_MINIMUM_DOCUMENTS)
        self.assertEqual(len(absent_minimum_types(present)), 1)

    def test_above_minimum_types_are_reported_separately(self):
        present = list(MINIMUM_DOCUMENTS) + ["screening-report"]
        self.assertEqual(above_minimum_types(present), ["screening-report"])

    def test_full_minimum_set_completeness_is_unity(self):
        self.assertAlmostEqual(
            minimum_set_completeness(MINIMUM_DOCUMENTS), 1.0, places=9
        )

    def test_three_of_five_reports_a_partial_fraction(self):
        self.assertAlmostEqual(
            minimum_set_completeness(MINIMUM_DOCUMENTS[:3]), 0.6, places=9
        )

    def test_completeness_tolerance_is_representation_sized(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)

    def test_unknown_type_in_the_present_set_rejected(self):
        with self.assertRaises(ValueError):
            absent_minimum_types(["expenses-claim"])

    def test_non_collection_present_types_rejected(self):
        with self.assertRaises(ValueError):
            absent_minimum_types("traceability-record")


class FileAssessmentTests(unittest.TestCase):
    def test_complete_file_is_fit_to_keep(self):
        result = assess_documentation_file(_file())
        self.assertTrue(result["fit_to_keep"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["minimum_set_complete"])

    def test_complete_file_reports_unity_completeness(self):
        result = assess_documentation_file(_file())
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)
        self.assertAlmostEqual(result["effective_completeness"], 1.0, places=9)

    def test_absent_minimum_document_reaches_the_verdict(self):
        documents = [
            d for d in _minimum_documents()
            if d["document_type"] != "nonconformance-and-alert-record"
        ]
        result = assess_documentation_file(_file(documents=documents))
        self.assertEqual(
            result["absent_minimum_types"], ["nonconformance-and-alert-record"]
        )
        self.assertFalse(result["fit_to_keep"])
        self.assertFalse(result["minimum_set_complete"])

    def test_unreachable_minimum_document_lowers_effective_completeness(self):
        documents = _minimum_documents()
        documents[0]["custody"] = "supplier-held-no-access"
        result = assess_documentation_file(_file(documents=documents))
        self.assertTrue(result["minimum_set_complete"])
        self.assertFalse(result["effectively_complete"])
        self.assertAlmostEqual(result["effective_completeness"], 0.8, places=9)

    def test_above_minimum_documents_are_listed_not_counted(self):
        documents = _minimum_documents() + [
            _document(document_type="evaluation-report")
        ]
        result = assess_documentation_file(_file(documents=documents))
        self.assertEqual(result["above_minimum_types"], ["evaluation-report"])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_above_minimum_documents_cannot_cover_a_shortfall(self):
        documents = [
            d for d in _minimum_documents()
            if d["document_type"] != "as-built-parts-list"
        ]
        documents.append(_document(document_type="screening-report"))
        result = assess_documentation_file(_file(documents=documents))
        self.assertIn("as-built-parts-list", result["absent_minimum_types"])
        self.assertFalse(result["minimum_set_complete"])

    def test_repeated_document_type_rejected(self):
        documents = _minimum_documents() + [
            _document(document_type="traceability-record")
        ]
        with self.assertRaises(ValueError):
            assess_documentation_file(_file(documents=documents))

    def test_empty_document_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_documentation_file(_file(documents=[]))

    def test_missing_file_key_rejected(self):
        kept = _file()
        del kept["documents"]
        with self.assertRaises(ValueError):
            assess_documentation_file(kept)

    def test_non_mapping_file_rejected(self):
        with self.assertRaises(ValueError):
            assess_documentation_file(["activity"])

    def test_horizon_shortfall_reaches_the_verdict(self):
        result = assess_documentation_file(
            _file(required_retention_until="2040-01-01")
        )
        self.assertFalse(result["fit_to_keep"])

    def test_every_finding_is_named_not_only_the_first(self):
        documents = [
            d for d in _minimum_documents()
            if d["document_type"] not in ("traceability-record", "as-built-parts-list")
        ]
        documents[0]["retention_years"] = 1
        documents[1]["custody"] = "supplier-held-no-access"
        result = assess_documentation_file(_file(documents=documents))
        self.assertGreaterEqual(len(result["findings"]), 4)


if __name__ == "__main__":
    unittest.main()
