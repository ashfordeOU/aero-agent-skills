#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-requirements-specification-data-item.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_requirements_specification_data_item.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_requirements_specification_data_item_logic import (  # noqa: E402
    FUNCTION,
    INTERFACE,
    MANDATORY_SECTIONS,
    PERFORMANCE,
    QUALITY,
    completeness_score,
    evaluate_requirements_specification,
    normalize_method,
    normalize_section,
    section_score,
    statement_findings,
    validate_statement,
    vague_terms_in,
)


def base_document():
    return {
        "Functional requirements": [
            {
                "id": "F-1",
                "text": "The device shall open the latch on command.",
                "verification_method": "test",
            }
        ],
        "Performance requirements": [
            {
                "id": "P-1",
                "text": "The device shall open the latch within 2 s.",
                "verification_method": "test",
                "value": 2.0,
                "unit": "s",
            }
        ],
        "Interface requirements": [
            {
                "id": "I-1",
                "text": "The device shall present a 15 pin connector.",
                "verification_method": "inspection",
                "counterpart": "platform harness",
            }
        ],
        "Quality requirements": [
            {
                "id": "Q-1",
                "text": "The device shall survive 500 actuation cycles.",
                "verification_method": "test",
                "acceptance_criterion": "no degradation after 500 cycles",
            }
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestSectionFolding(unittest.TestCase):
    def test_functional_folds_to_function(self):
        self.assertEqual(normalize_section("Functional requirements"), FUNCTION)

    def test_underscores_and_case_are_tolerated(self):
        self.assertEqual(normalize_section("PERFORMANCE_REQUIREMENTS"), PERFORMANCE)

    def test_plural_interfaces_folds(self):
        self.assertEqual(normalize_section("Interfaces"), INTERFACE)

    def test_quality_assurance_folds(self):
        self.assertEqual(normalize_section("quality assurance requirements"), QUALITY)

    def test_unrecognised_heading_is_kept_as_extra(self):
        self.assertEqual(normalize_section("Applicable documents"), "applicable documents")

    def test_blank_heading_rejected(self):
        with self.assertRaises(ValueError):
            normalize_section("   ")


class TestMethodFolding(unittest.TestCase):
    def test_review_of_design_spellings_fold(self):
        self.assertEqual(normalize_method("Review of Design"), "review-of-design")

    def test_single_letter_folds(self):
        self.assertEqual(normalize_method("T"), "test")

    def test_analysis_passes_through(self):
        self.assertEqual(normalize_method("analysis"), "analysis")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("demonstration")

    def test_empty_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("")


class TestVagueWording(unittest.TestCase):
    def test_adequate_is_caught(self):
        self.assertEqual(vague_terms_in("shall hold an adequate margin"), ["adequate"])

    def test_hyphenated_user_friendly_is_caught(self):
        self.assertIn("user friendly", vague_terms_in("a user-friendly interface"))

    def test_multi_word_term_is_caught(self):
        self.assertIn("as required", vague_terms_in("power shall be drawn as required"))

    def test_a_quantified_statement_is_clean(self):
        self.assertEqual(vague_terms_in("shall open within 2 s"), [])

    def test_substring_does_not_false_positive(self):
        self.assertEqual(vague_terms_in("the suitability study is referenced"), [])

    def test_non_string_text_rejected(self):
        with self.assertRaises(ValueError):
            vague_terms_in(None)


class TestStatementValidation(unittest.TestCase):
    def test_a_good_statement_resolves(self):
        resolved = validate_statement(
            {"id": " F-1 ", "text": " x ", "verification_method": "test"}
        )
        self.assertEqual(resolved["id"], "F-1")
        self.assertEqual(resolved["text"], "x")

    def test_unknown_statement_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_statement({"id": "F-1", "owner": "someone"})

    def test_non_mapping_statement_rejected(self):
        with self.assertRaises(ValueError):
            validate_statement(["F-1"])

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_statement({"id": "P-1", "value": "2 s"})

    def test_non_string_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_statement({"id": 1})


class TestStatementFindings(unittest.TestCase):
    def test_a_clean_function_statement_has_none(self):
        self.assertEqual(
            statement_findings(
                {"id": "F-1", "text": "shall open the latch", "verification_method": "test"},
                FUNCTION,
            ),
            [],
        )

    def test_missing_identifier_is_found(self):
        found = statement_findings(
            {"text": "shall open the latch", "verification_method": "test"}, FUNCTION
        )
        self.assertIn("statement-without-identifier", [f["code"] for f in found])

    def test_missing_verification_method_is_found(self):
        found = statement_findings({"id": "F-1", "text": "shall open"}, FUNCTION)
        self.assertIn(
            "statement-without-verification-method", [f["code"] for f in found]
        )

    def test_empty_text_is_found(self):
        found = statement_findings(
            {"id": "F-1", "text": "  ", "verification_method": "test"}, FUNCTION
        )
        self.assertIn("statement-without-text", [f["code"] for f in found])

    def test_performance_without_a_quantity_is_found(self):
        found = statement_findings(
            {"id": "P-1", "text": "shall be fast", "verification_method": "test"},
            PERFORMANCE,
        )
        self.assertIn("performance-without-quantity", [f["code"] for f in found])

    def test_performance_with_a_value_and_unit_is_clean(self):
        self.assertEqual(
            statement_findings(
                {
                    "id": "P-1",
                    "text": "shall open within 2 s",
                    "verification_method": "test",
                    "value": 2.0,
                    "unit": "s",
                },
                PERFORMANCE,
            ),
            [],
        )

    def test_interface_without_a_counterpart_is_found(self):
        found = statement_findings(
            {"id": "I-1", "text": "shall present a connector", "verification_method": "inspection"},
            INTERFACE,
        )
        self.assertIn("interface-without-counterpart", [f["code"] for f in found])

    def test_quality_without_an_acceptance_criterion_is_found(self):
        found = statement_findings(
            {"id": "Q-1", "text": "shall be reliable in service", "verification_method": "analysis"},
            QUALITY,
        )
        self.assertIn(
            "quality-without-acceptance-criterion", [f["code"] for f in found]
        )

    def test_vague_wording_is_found(self):
        found = statement_findings(
            {
                "id": "F-2",
                "text": "shall hold an adequate margin",
                "verification_method": "analysis",
            },
            FUNCTION,
        )
        self.assertIn("unverifiable-wording", [f["code"] for f in found])

    def test_unknown_method_on_a_statement_rejected(self):
        with self.assertRaises(ValueError):
            statement_findings(
                {"id": "F-1", "text": "shall open", "verification_method": "vibe"},
                FUNCTION,
            )


class TestScores(unittest.TestCase):
    def test_empty_section_scores_zero(self):
        self.assertAlmostEqual(section_score([], FUNCTION), 0.0, places=12)

    def test_all_clean_section_scores_one(self):
        statements = [
            {"id": "F-1", "text": "shall open", "verification_method": "test"},
            {"id": "F-2", "text": "shall close", "verification_method": "test"},
        ]
        self.assertAlmostEqual(section_score(statements, FUNCTION), 1.0, places=12)

    def test_half_clean_section_scores_a_half(self):
        statements = [
            {"id": "F-1", "text": "shall open", "verification_method": "test"},
            {"id": "F-2", "text": "shall close"},
        ]
        self.assertAlmostEqual(section_score(statements, FUNCTION), 0.5, places=12)

    def test_non_list_section_rejected(self):
        with self.assertRaises(ValueError):
            section_score("statements", FUNCTION)

    def test_completeness_is_the_mean_of_the_four(self):
        scores = {FUNCTION: 1.0, PERFORMANCE: 1.0, INTERFACE: 1.0, QUALITY: 0.0}
        self.assertAlmostEqual(completeness_score(scores), 0.75, places=12)

    def test_completeness_needs_all_four_areas(self):
        with self.assertRaises(ValueError):
            completeness_score({FUNCTION: 1.0})

    def test_out_of_range_score_rejected(self):
        scores = {FUNCTION: 1.5, PERFORMANCE: 1.0, INTERFACE: 1.0, QUALITY: 1.0}
        with self.assertRaises(ValueError):
            completeness_score(scores)


class TestEvaluateDocument(unittest.TestCase):
    def test_a_good_document_is_compliant(self):
        result = evaluate_requirements_specification(base_document())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["completeness_score"], 1.0, places=12)

    def test_all_four_areas_are_reported_present(self):
        result = evaluate_requirements_specification(base_document())
        for name in MANDATORY_SECTIONS:
            self.assertIn(name, result["sections_present"])

    def test_an_absent_area_is_reported(self):
        document = base_document()
        del document["Quality requirements"]
        result = evaluate_requirements_specification(document)
        self.assertIn("mandatory-section-absent", codes(result))

    def test_an_empty_heading_is_reported(self):
        document = base_document()
        document["Interface requirements"] = []
        result = evaluate_requirements_specification(document)
        self.assertIn("mandatory-section-empty", codes(result))
        self.assertAlmostEqual(result["section_scores"][INTERFACE], 0.0, places=12)

    def test_duplicate_identifier_across_areas_is_reported(self):
        document = base_document()
        document["Functional requirements"].append(
            {"id": "P-1", "text": "shall close the latch", "verification_method": "test"}
        )
        result = evaluate_requirements_specification(document)
        self.assertIn("duplicate-requirement-identifier", codes(result))

    def test_extra_sections_are_listed_and_allowed(self):
        document = base_document()
        document["Applicable documents"] = []
        result = evaluate_requirements_specification(document)
        self.assertEqual(result["extra_sections"], ["applicable documents"])
        self.assertTrue(result["compliant"])

    def test_statement_count_covers_every_area(self):
        result = evaluate_requirements_specification(base_document())
        self.assertEqual(result["statement_count"], 4)

    def test_two_headings_folding_to_one_area_rejected(self):
        document = base_document()
        document["Functions"] = []
        with self.assertRaises(ValueError):
            evaluate_requirements_specification(document)

    def test_non_list_section_rejected(self):
        document = base_document()
        document["Quality requirements"] = "none"
        with self.assertRaises(ValueError):
            evaluate_requirements_specification(document)

    def test_empty_document_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_requirements_specification({})

    def test_non_mapping_document_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_requirements_specification([("function", [])])


if __name__ == "__main__":
    unittest.main()
