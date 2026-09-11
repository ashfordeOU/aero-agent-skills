"""
Unit tests for e1006_types_logic — ECSS-E-ST-10C §6.2.1–6.2.13.

Run: python3 test_e1006_types.py
Expected output: OK
"""
import sys
import os
import unittest

# Allow running from the scripts/ directory or repo root.
sys.path.insert(0, os.path.dirname(__file__))

from e1006_types_logic import (
    VALID_TYPES,
    RequirementRecord,
    categorize_requirement,
    categorize_batch,
    validate_type_coverage,
)


class TestValidTypes(unittest.TestCase):
    def test_twelve_types_defined(self):
        self.assertEqual(len(VALID_TYPES), 12)

    def test_all_expected_type_keys_present(self):
        expected = {
            "functional", "mission", "interface", "environmental",
            "operational", "human_factor", "ils", "physical",
            "pa_induced", "configuration", "design", "verification",
        }
        self.assertEqual(set(VALID_TYPES), expected)


class TestExplicitTypeAssignment(unittest.TestCase):
    """Explicit type tags are validated and accepted for all 12 types."""

    def _make(self, req_id, explicit_type):
        return RequirementRecord(
            req_id=req_id,
            text="Placeholder requirement text.",
            explicit_type=explicit_type,
        )

    def test_functional_type(self):
        result = categorize_requirement(self._make("R001", "functional"))
        self.assertEqual(result.assigned_type, "functional")
        self.assertIsNone(result.error)
        self.assertTrue(result.is_categorized)

    def test_mission_type(self):
        result = categorize_requirement(self._make("R002", "mission"))
        self.assertEqual(result.assigned_type, "mission")
        self.assertIsNone(result.error)

    def test_interface_type(self):
        result = categorize_requirement(self._make("R003", "interface"))
        self.assertEqual(result.assigned_type, "interface")
        self.assertIsNone(result.error)

    def test_environmental_type(self):
        result = categorize_requirement(self._make("R004", "environmental"))
        self.assertEqual(result.assigned_type, "environmental")
        self.assertIsNone(result.error)

    def test_operational_type(self):
        result = categorize_requirement(self._make("R005", "operational"))
        self.assertEqual(result.assigned_type, "operational")
        self.assertIsNone(result.error)

    def test_human_factor_type(self):
        result = categorize_requirement(self._make("R006", "human_factor"))
        self.assertEqual(result.assigned_type, "human_factor")
        self.assertIsNone(result.error)

    def test_ils_type(self):
        result = categorize_requirement(self._make("R007", "ils"))
        self.assertEqual(result.assigned_type, "ils")
        self.assertIsNone(result.error)

    def test_physical_type(self):
        result = categorize_requirement(self._make("R008", "physical"))
        self.assertEqual(result.assigned_type, "physical")
        self.assertIsNone(result.error)

    def test_pa_induced_type(self):
        result = categorize_requirement(self._make("R009", "pa_induced"))
        self.assertEqual(result.assigned_type, "pa_induced")
        self.assertIsNone(result.error)

    def test_configuration_type(self):
        result = categorize_requirement(self._make("R010", "configuration"))
        self.assertEqual(result.assigned_type, "configuration")
        self.assertIsNone(result.error)

    def test_design_type(self):
        result = categorize_requirement(self._make("R011", "design"))
        self.assertEqual(result.assigned_type, "design")
        self.assertIsNone(result.error)

    def test_verification_type(self):
        result = categorize_requirement(self._make("R012", "verification"))
        self.assertEqual(result.assigned_type, "verification")
        self.assertIsNone(result.error)


class TestAliasNormalisation(unittest.TestCase):
    """Alternate spellings of type labels resolve to the canonical key."""

    def test_human_factor_space_separated(self):
        rec = RequirementRecord("R020", "text", explicit_type="human factor")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "human_factor")
        self.assertIsNone(result.error)

    def test_human_factor_hyphenated(self):
        rec = RequirementRecord("R021", "text", explicit_type="human-factor")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "human_factor")
        self.assertIsNone(result.error)

    def test_pa_induced_hyphenated(self):
        rec = RequirementRecord("R022", "text", explicit_type="pa-induced")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "pa_induced")
        self.assertIsNone(result.error)

    def test_pa_induced_space_separated(self):
        rec = RequirementRecord("R023", "text", explicit_type="pa induced")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "pa_induced")
        self.assertIsNone(result.error)

    def test_ils_logistic_alias(self):
        rec = RequirementRecord("R024", "text", explicit_type="logistic")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "ils")
        self.assertIsNone(result.error)

    def test_ils_full_alias(self):
        rec = RequirementRecord("R025", "text", explicit_type="integrated logistic support")
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "ils")
        self.assertIsNone(result.error)


class TestUnknownTypeError(unittest.TestCase):
    def test_unknown_type_returns_error(self):
        rec = RequirementRecord("R030", "text", explicit_type="political")
        result = categorize_requirement(rec)
        self.assertIsNone(result.assigned_type)
        self.assertIsNotNone(result.error)
        self.assertFalse(result.is_categorized)
        self.assertIn("political", result.error)

    def test_empty_string_type_returns_error(self):
        rec = RequirementRecord("R031", "text", explicit_type="")
        result = categorize_requirement(rec)
        self.assertIsNone(result.assigned_type)
        self.assertIsNotNone(result.error)


class TestAutoScoring(unittest.TestCase):
    """Auto-scoring assigns type from keyword signals in requirement text."""

    def test_auto_score_physical_mass(self):
        rec = RequirementRecord(
            "R040",
            "The unit mass shall not exceed 5 kg (mass budget allocation).",
        )
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "physical")
        self.assertIsNone(result.error)

    def test_auto_score_environmental_vibration(self):
        rec = RequirementRecord(
            "R041",
            "The equipment shall withstand the launch vibration spectrum defined in the launch vehicle ICD.",
        )
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "environmental")
        self.assertIsNone(result.error)

    def test_auto_score_verification_test(self):
        rec = RequirementRecord(
            "R042",
            "Compliance shall be verified by qualification test at unit level.",
        )
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "verification")
        self.assertIsNone(result.error)

    def test_auto_score_pa_induced_reliability(self):
        rec = RequirementRecord(
            "R043",
            "The subsystem reliability shall meet the product assurance plan target of 0.98 over the design lifetime.",
        )
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "pa_induced")
        self.assertIsNone(result.error)

    def test_auto_score_ils_maintainability(self):
        rec = RequirementRecord(
            "R044",
            "The system maintainability target requires a mean time to repair below 4 hours.",
        )
        result = categorize_requirement(rec)
        self.assertEqual(result.assigned_type, "ils")
        self.assertIsNone(result.error)

    def test_zero_score_returns_error(self):
        rec = RequirementRecord(
            "R045",
            "The widget shall be blue.",
        )
        result = categorize_requirement(rec)
        self.assertIsNone(result.assigned_type)
        self.assertIsNotNone(result.error)
        self.assertIn("No keyword signal", result.error)
        self.assertFalse(result.is_categorized)


class TestBatchCategorization(unittest.TestCase):
    def test_batch_all_explicit_pass(self):
        records = [
            RequirementRecord("B001", "text", explicit_type="functional"),
            RequirementRecord("B002", "text", explicit_type="mission"),
            RequirementRecord("B003", "text", explicit_type="verification"),
        ]
        report = categorize_batch(records)
        self.assertTrue(report.all_categorized)
        self.assertEqual(len(report.uncategorized_ids), 0)
        self.assertEqual(len(report.results), 3)

    def test_batch_with_one_error(self):
        records = [
            RequirementRecord("B010", "text", explicit_type="functional"),
            RequirementRecord("B011", "text", explicit_type="unknown-bogus"),
        ]
        report = categorize_batch(records)
        self.assertFalse(report.all_categorized)
        self.assertIn("B011", report.uncategorized_ids)
        self.assertEqual(len(report.uncategorized_ids), 1)

    def test_batch_type_counts(self):
        records = [
            RequirementRecord("C001", "text", explicit_type="physical"),
            RequirementRecord("C002", "text", explicit_type="physical"),
            RequirementRecord("C003", "text", explicit_type="verification"),
        ]
        report = categorize_batch(records)
        counts = report.type_counts
        self.assertEqual(counts["physical"], 2)
        self.assertEqual(counts["verification"], 1)
        self.assertEqual(counts["functional"], 0)

    def test_empty_batch(self):
        report = categorize_batch([])
        self.assertTrue(report.all_categorized)
        self.assertEqual(len(report.results), 0)


class TestValidateCoverage(unittest.TestCase):
    def test_no_invalid_types(self):
        records = [
            RequirementRecord("V001", "text", explicit_type="design"),
            RequirementRecord("V002", "text", explicit_type="configuration"),
        ]
        invalid = validate_type_coverage(records)
        self.assertEqual(invalid, [])

    def test_invalid_type_detected(self):
        records = [
            RequirementRecord("V010", "text", explicit_type="design"),
            RequirementRecord("V011", "text", explicit_type="political"),
        ]
        invalid = validate_type_coverage(records)
        self.assertIn("political", invalid)

    def test_none_explicit_type_skipped(self):
        records = [
            RequirementRecord("V020", "mass budget requirement text", explicit_type=None),
        ]
        invalid = validate_type_coverage(records)
        self.assertEqual(invalid, [])


class TestForbiddenWords(unittest.TestCase):
    """Gate: ensure no forbidden words appear in module output strings."""

    FORBIDDEN = ("class" + "ified", "un" + "class" + "ified")

    def _check_result(self, result):
        for word in self.FORBIDDEN:
            if result.rationale:
                self.assertNotIn(word, result.rationale.lower(), f"'{word}' found in rationale")
            if result.error:
                self.assertNotIn(word, result.error.lower(), f"'{word}' found in error")

    def test_error_message_is_free_of_forbidden_words(self):
        rec = RequirementRecord("F001", "text", explicit_type="bogus-type")
        result = categorize_requirement(rec)
        self._check_result(result)

    def test_success_rationale_is_free_of_forbidden_words(self):
        rec = RequirementRecord("F002", "text", explicit_type="functional")
        result = categorize_requirement(rec)
        self._check_result(result)

    def test_auto_score_rationale_is_free_of_forbidden_words(self):
        rec = RequirementRecord(
            "F003",
            "The unit mass shall not exceed 10 kg (mass budget).",
        )
        result = categorize_requirement(rec)
        self._check_result(result)


if __name__ == "__main__":
    unittest.main()
