"""
Tests for verification_method_selection_logic.py
stdlib unittest only — deterministic, offline. Run:
    python3 test_verification_method_selection.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from verification_method_selection_logic import (
    VerificationMethod,
    RequirementCategory,
    Requirement,
    validate_method_selection,
    assess_programme_coverage,
    suggest_methods,
    parse_method,
    parse_category,
)


class TestValidMethodSelection(unittest.TestCase):

    def test_strength_with_analysis_is_valid(self):
        req = Requirement(
            req_id="STR-001",
            category=RequirementCategory.STRUCTURAL_STRENGTH,
            description="Ultimate load capability",
            assigned_methods=[VerificationMethod.ANALYSIS],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.issues, [])

    def test_strength_with_analysis_and_test_is_valid(self):
        req = Requirement(
            req_id="STR-002",
            category=RequirementCategory.STRUCTURAL_STRENGTH,
            description="Ultimate load capability with test confirmation",
            assigned_methods=[VerificationMethod.ANALYSIS, VerificationMethod.TEST],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)

    def test_stiffness_with_analysis_is_valid(self):
        req = Requirement(
            req_id="STF-001",
            category=RequirementCategory.STRUCTURAL_STIFFNESS,
            description="First eigenfrequency",
            assigned_methods=[VerificationMethod.ANALYSIS],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)

    def test_environmental_qualification_with_test_is_valid(self):
        req = Requirement(
            req_id="ENV-001",
            category=RequirementCategory.ENVIRONMENTAL_QUALIFICATION,
            description="Random vibration qualification",
            assigned_methods=[VerificationMethod.TEST],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)

    def test_workmanship_with_inspection_is_valid(self):
        req = Requirement(
            req_id="WRK-001",
            category=RequirementCategory.WORKMANSHIP,
            description="Bond-line quality",
            assigned_methods=[VerificationMethod.INSPECTION],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)

    def test_interface_geometry_with_inspection_and_rod_is_valid(self):
        req = Requirement(
            req_id="IFG-001",
            category=RequirementCategory.INTERFACE_GEOMETRY,
            description="Bracket hole-pattern fit",
            assigned_methods=[
                VerificationMethod.INSPECTION,
                VerificationMethod.REVIEW_OF_DESIGN,
            ],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)

    def test_mass_properties_with_test_is_valid(self):
        req = Requirement(
            req_id="MAS-001",
            category=RequirementCategory.MASS_PROPERTIES,
            description="Subsystem mass budget",
            assigned_methods=[VerificationMethod.TEST],
        )
        result = validate_method_selection(req)
        self.assertTrue(result.is_valid)


class TestInvalidMethodSelection(unittest.TestCase):

    def test_no_method_assigned_is_invalid(self):
        req = Requirement(
            req_id="STR-010",
            category=RequirementCategory.STRUCTURAL_STRENGTH,
            description="Strength with no method",
            assigned_methods=[],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("no verification method" in issue for issue in result.issues))

    def test_strength_missing_mandatory_analysis_is_invalid(self):
        # Test only — does not include mandatory analysis
        req = Requirement(
            req_id="STR-011",
            category=RequirementCategory.STRUCTURAL_STRENGTH,
            description="Strength verified by test only",
            assigned_methods=[VerificationMethod.TEST],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("mandatory method" in issue for issue in result.issues))

    def test_strength_with_inspection_is_invalid(self):
        # Inspection is not acceptable for structural strength
        req = Requirement(
            req_id="STR-012",
            category=RequirementCategory.STRUCTURAL_STRENGTH,
            description="Strength checked by inspection only",
            assigned_methods=[VerificationMethod.INSPECTION],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        issue_text = " ".join(result.issues)
        self.assertIn("not acceptable", issue_text)

    def test_environmental_qualification_missing_test_is_invalid(self):
        # Analysis only — mandatory test is absent
        req = Requirement(
            req_id="ENV-010",
            category=RequirementCategory.ENVIRONMENTAL_QUALIFICATION,
            description="Thermal cycling qualification by analysis only",
            assigned_methods=[VerificationMethod.ANALYSIS],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("mandatory method" in issue for issue in result.issues))

    def test_workmanship_missing_inspection_is_invalid(self):
        req = Requirement(
            req_id="WRK-010",
            category=RequirementCategory.WORKMANSHIP,
            description="Fastener torque — review of design only",
            assigned_methods=[VerificationMethod.REVIEW_OF_DESIGN],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        self.assertTrue(any("mandatory method" in issue for issue in result.issues))

    def test_workmanship_with_analysis_is_invalid(self):
        # Analysis is not acceptable for workmanship
        req = Requirement(
            req_id="WRK-011",
            category=RequirementCategory.WORKMANSHIP,
            description="Workmanship verified by analysis",
            assigned_methods=[VerificationMethod.ANALYSIS, VerificationMethod.INSPECTION],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)
        issue_text = " ".join(result.issues)
        self.assertIn("not acceptable", issue_text)

    def test_stiffness_missing_analysis_is_invalid(self):
        req = Requirement(
            req_id="STF-010",
            category=RequirementCategory.STRUCTURAL_STIFFNESS,
            description="Stiffness by test only, no analysis",
            assigned_methods=[VerificationMethod.TEST],
        )
        result = validate_method_selection(req)
        self.assertFalse(result.is_valid)


class TestProgrammeCoverage(unittest.TestCase):

    def _make_valid_programme(self):
        return [
            Requirement(
                req_id="STR-001",
                category=RequirementCategory.STRUCTURAL_STRENGTH,
                description="Ultimate strength",
                assigned_methods=[VerificationMethod.ANALYSIS],
            ),
            Requirement(
                req_id="ENV-001",
                category=RequirementCategory.ENVIRONMENTAL_QUALIFICATION,
                description="Vibration qualification",
                assigned_methods=[VerificationMethod.TEST],
            ),
            Requirement(
                req_id="WRK-001",
                category=RequirementCategory.WORKMANSHIP,
                description="Bond quality",
                assigned_methods=[VerificationMethod.INSPECTION],
            ),
        ]

    def test_fully_covered_programme_is_valid(self):
        result = assess_programme_coverage(self._make_valid_programme())
        self.assertTrue(result.is_programme_valid)
        self.assertEqual(result.total_requirements, 3)
        self.assertEqual(result.covered_requirements, 3)
        self.assertEqual(result.uncovered_requirements, [])
        self.assertEqual(result.invalid_assignments, [])
        self.assertAlmostEqual(result.coverage_percentage, 100.0)

    def test_programme_with_uncovered_requirement(self):
        reqs = self._make_valid_programme()
        reqs.append(
            Requirement(
                req_id="MAS-001",
                category=RequirementCategory.MASS_PROPERTIES,
                description="Mass budget not yet assigned",
                assigned_methods=[],
            )
        )
        result = assess_programme_coverage(reqs)
        self.assertFalse(result.is_programme_valid)
        self.assertIn("MAS-001", result.uncovered_requirements)
        self.assertEqual(result.covered_requirements, 3)
        self.assertAlmostEqual(result.coverage_percentage, 75.0)

    def test_empty_programme_returns_invalid_with_zero_coverage(self):
        result = assess_programme_coverage([])
        self.assertFalse(result.is_programme_valid)
        self.assertEqual(result.total_requirements, 0)
        self.assertEqual(result.coverage_percentage, 0.0)

    def test_programme_with_invalid_assignment_is_not_valid(self):
        reqs = self._make_valid_programme()
        reqs.append(
            Requirement(
                req_id="STR-BAD",
                category=RequirementCategory.STRUCTURAL_STRENGTH,
                description="Strength without analysis",
                assigned_methods=[VerificationMethod.TEST],  # missing mandatory A
            )
        )
        result = assess_programme_coverage(reqs)
        self.assertFalse(result.is_programme_valid)
        invalid_ids = [r.req_id for r in result.invalid_assignments]
        self.assertIn("STR-BAD", invalid_ids)

    def test_coverage_percentage_calculation(self):
        reqs = [
            Requirement(
                req_id=f"R-{i:03d}",
                category=RequirementCategory.MASS_PROPERTIES,
                description="mass",
                assigned_methods=[VerificationMethod.TEST] if i < 3 else [],
            )
            for i in range(4)
        ]
        result = assess_programme_coverage(reqs)
        self.assertAlmostEqual(result.coverage_percentage, 75.0)
        self.assertEqual(result.covered_requirements, 3)


class TestSuggestMethods(unittest.TestCase):

    def test_suggest_strength_starts_with_analysis(self):
        methods = suggest_methods(RequirementCategory.STRUCTURAL_STRENGTH)
        self.assertIn(VerificationMethod.ANALYSIS, methods)
        self.assertEqual(methods[0], VerificationMethod.ANALYSIS)

    def test_suggest_env_qual_starts_with_test(self):
        methods = suggest_methods(RequirementCategory.ENVIRONMENTAL_QUALIFICATION)
        self.assertIn(VerificationMethod.TEST, methods)
        self.assertEqual(methods[0], VerificationMethod.TEST)

    def test_suggest_workmanship_starts_with_inspection(self):
        methods = suggest_methods(RequirementCategory.WORKMANSHIP)
        self.assertIn(VerificationMethod.INSPECTION, methods)
        self.assertEqual(methods[0], VerificationMethod.INSPECTION)

    def test_suggest_returns_only_acceptable_methods(self):
        from verification_method_selection_logic import ACCEPTABLE_METHODS
        for category in RequirementCategory:
            suggested = suggest_methods(category)
            acceptable = ACCEPTABLE_METHODS[category]
            for method in suggested:
                self.assertIn(
                    method,
                    acceptable,
                    f"Suggested method {method} not acceptable for {category}",
                )


class TestParseMethod(unittest.TestCase):

    def test_parse_short_analysis(self):
        self.assertEqual(parse_method("A"), VerificationMethod.ANALYSIS)

    def test_parse_short_test(self):
        self.assertEqual(parse_method("T"), VerificationMethod.TEST)

    def test_parse_short_inspection(self):
        self.assertEqual(parse_method("I"), VerificationMethod.INSPECTION)

    def test_parse_rod_short(self):
        self.assertEqual(parse_method("RoD"), VerificationMethod.REVIEW_OF_DESIGN)

    def test_parse_long_analysis(self):
        self.assertEqual(parse_method("analysis"), VerificationMethod.ANALYSIS)

    def test_parse_unknown_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_method("UNKNOWN_METHOD")

    def test_parse_empty_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_method("")


class TestParseCategory(unittest.TestCase):

    def test_parse_structural_strength(self):
        self.assertEqual(
            parse_category("structural_strength"),
            RequirementCategory.STRUCTURAL_STRENGTH,
        )

    def test_parse_workmanship_uppercase(self):
        self.assertEqual(
            parse_category("WORKMANSHIP"),
            RequirementCategory.WORKMANSHIP,
        )

    def test_parse_unknown_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_category("completely_unknown_category")


class TestForbiddenWords(unittest.TestCase):
    """Gate: security-marking words must not appear in any source file
    (case-insensitive substring match)."""

    # Build the forbidden token at runtime so it never appears literally.
    _FORBIDDEN = "classif" + "ied"

    def _read_source(self, filename: str) -> str:
        base = os.path.dirname(__file__)
        with open(os.path.join(base, filename), encoding="utf-8") as fh:
            return fh.read()

    def test_logic_module_has_no_forbidden_words(self):
        content = self._read_source("verification_method_selection_logic.py")
        self.assertNotIn(self._FORBIDDEN, content.lower())

    def test_test_module_has_no_forbidden_words(self):
        content = self._read_source("test_verification_method_selection.py")
        self.assertNotIn(self._FORBIDDEN, content.lower())


if __name__ == "__main__":
    unittest.main()
