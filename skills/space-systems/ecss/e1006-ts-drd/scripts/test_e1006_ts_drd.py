"""
Gate 3 contract tests for e1006-ts-drd logic.
Run: python3 test_e1006_ts_drd.py
Stdlib unittest only — deterministic, offline, no network.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1006_ts_drd_logic import (
    MANDATORY_SECTIONS,
    TsValidationError,
    validate_ts_structure,
    categorize_verification_method,
    validate_requirement,
    check_interface_requirement_linkage,
    score_ts_completeness,
    validate_ts_document,
)


def _minimal_ts_doc():
    return {
        "identification": {"system": "SAT-1", "subsystem": "OBC", "revision": "A"},
        "mission_context": "Onboard computer for LEO Earth-observation mission",
        "technical_performance_requirements": [
            {
                "id": "TPR-001",
                "text": "Processing throughput shall be no less than 200 MIPS",
                "verification_method": "test",
                "req_type": "performance",
            }
        ],
        "interface_requirements": [
            {
                "id": "IR-001",
                "text": "The OBC shall interface to the power bus per ICD-PWR-001",
                "verification_method": "inspection",
                "req_type": "interface",
                "icd_reference": "ICD-PWR-001",
            }
        ],
        "environmental_requirements": [
            {
                "id": "ENV-001",
                "text": "The unit shall operate up to a total ionising dose of 20 krad(Si)",
                "verification_method": "analysis",
                "req_type": "environmental",
            }
        ],
        "verification_table": {"generated": True},
    }


# ---------------------------------------------------------------------------
# Structure validation
# ---------------------------------------------------------------------------

class TestStructureValidation(unittest.TestCase):

    def test_complete_document_has_no_structure_findings(self):
        findings = validate_ts_structure(_minimal_ts_doc())
        self.assertEqual(findings, [])

    def test_missing_verification_table_is_flagged(self):
        ts_doc = _minimal_ts_doc()
        del ts_doc["verification_table"]
        sections = [f["section"] for f in validate_ts_structure(ts_doc)]
        self.assertIn("verification_table", sections)

    def test_missing_identification_is_flagged(self):
        ts_doc = _minimal_ts_doc()
        del ts_doc["identification"]
        sections = [f["section"] for f in validate_ts_structure(ts_doc)]
        self.assertIn("identification", sections)

    def test_all_absent_sections_are_reported(self):
        ts_doc = {"identification": {"system": "X"}}
        absent = [f["section"] for f in validate_ts_structure(ts_doc)]
        for section in MANDATORY_SECTIONS:
            if section != "identification":
                self.assertIn(section, absent)

    def test_structure_finding_severity_is_major(self):
        ts_doc = _minimal_ts_doc()
        del ts_doc["mission_context"]
        findings = validate_ts_structure(ts_doc)
        self.assertTrue(all(f["severity"] == "major" for f in findings))

    def test_non_dict_ts_doc_raises(self):
        with self.assertRaises(TsValidationError):
            validate_ts_structure("not-a-dict")

    def test_none_section_value_is_flagged(self):
        ts_doc = _minimal_ts_doc()
        ts_doc["environmental_requirements"] = None
        sections = [f["section"] for f in validate_ts_structure(ts_doc)]
        self.assertIn("environmental_requirements", sections)


# ---------------------------------------------------------------------------
# Verification method mapping
# ---------------------------------------------------------------------------

class TestVerificationMethodMapping(unittest.TestCase):

    def test_test_maps_to_T(self):
        self.assertEqual(categorize_verification_method("test"), "T")

    def test_analysis_maps_to_A(self):
        self.assertEqual(categorize_verification_method("analysis"), "A")

    def test_inspection_maps_to_I(self):
        self.assertEqual(categorize_verification_method("inspection"), "I")

    def test_review_of_design_maps_to_R(self):
        self.assertEqual(categorize_verification_method("review of design"), "R")

    def test_rod_abbreviation_maps_to_R(self):
        self.assertEqual(categorize_verification_method("rod"), "R")

    def test_single_letter_T_maps_to_T(self):
        self.assertEqual(categorize_verification_method("T"), "T")

    def test_unknown_method_returns_none(self):
        self.assertIsNone(categorize_verification_method("simulation"))

    def test_tbd_method_returns_none(self):
        self.assertIsNone(categorize_verification_method("TBD"))

    def test_non_string_input_returns_none(self):
        self.assertIsNone(categorize_verification_method(42))

    def test_whitespace_padded_method_is_accepted(self):
        self.assertEqual(categorize_verification_method("  test  "), "T")


# ---------------------------------------------------------------------------
# Requirement validation
# ---------------------------------------------------------------------------

class TestRequirementValidation(unittest.TestCase):

    def test_valid_requirement_has_no_findings(self):
        req = {
            "id": "TPR-001",
            "text": "Throughput shall be ≥ 200 MIPS",
            "verification_method": "test",
            "req_type": "performance",
        }
        self.assertEqual(validate_requirement(req), [])

    def test_missing_id_is_flagged_critical(self):
        req = {"text": "Some requirement", "verification_method": "analysis"}
        findings = validate_requirement(req)
        self.assertTrue(
            any(f["severity"] == "critical" and "identifier" in f["issue"] for f in findings)
        )

    def test_empty_text_is_flagged(self):
        req = {"id": "TPR-002", "text": "", "verification_method": "inspection"}
        findings = validate_requirement(req)
        self.assertTrue(any("text is empty" in f["issue"] for f in findings))

    def test_missing_verification_method_is_flagged(self):
        req = {"id": "TPR-003", "text": "Some requirement"}
        findings = validate_requirement(req)
        self.assertTrue(any("verification method" in f["issue"] for f in findings))

    def test_unrecognized_verification_method_is_flagged(self):
        req = {"id": "TPR-004", "text": "Some requirement", "verification_method": "simulation"}
        findings = validate_requirement(req)
        self.assertTrue(any("Unrecognized verification method" in f["issue"] for f in findings))

    def test_unknown_req_type_is_flagged_minor(self):
        req = {
            "id": "TPR-005",
            "text": "Some requirement",
            "verification_method": "test",
            "req_type": "exotic",
        }
        findings = validate_requirement(req)
        self.assertTrue(any(f["severity"] == "minor" for f in findings))

    def test_valid_req_type_environmental_has_no_type_finding(self):
        req = {
            "id": "ENV-001",
            "text": "Operate in vacuum",
            "verification_method": "analysis",
            "req_type": "environmental",
        }
        self.assertEqual(validate_requirement(req), [])

    def test_non_dict_raises(self):
        with self.assertRaises(TsValidationError):
            validate_requirement(["not", "a", "dict"])


# ---------------------------------------------------------------------------
# Interface requirement ICD linkage
# ---------------------------------------------------------------------------

class TestInterfaceRequirementLinkage(unittest.TestCase):

    def test_registered_icd_produces_no_finding(self):
        req = {
            "id": "IR-001",
            "text": "Interface to power bus per ICD-PWR-001",
            "verification_method": "inspection",
            "req_type": "interface",
            "icd_reference": "ICD-PWR-001",
        }
        self.assertEqual(
            check_interface_requirement_linkage(req, ["ICD-PWR-001", "ICD-COMM-002"]), []
        )

    def test_unregistered_icd_is_flagged(self):
        req = {
            "id": "IR-002",
            "text": "Interface to AOCS",
            "verification_method": "inspection",
            "req_type": "interface",
            "icd_reference": "ICD-AOCS-003",
        }
        findings = check_interface_requirement_linkage(req, ["ICD-PWR-001"])
        self.assertTrue(any("not in the registered ICD list" in f["issue"] for f in findings))

    def test_missing_icd_reference_is_flagged(self):
        req = {
            "id": "IR-003",
            "text": "Interface req with no ICD ref",
            "verification_method": "inspection",
            "req_type": "interface",
        }
        findings = check_interface_requirement_linkage(req, ["ICD-PWR-001"])
        self.assertTrue(any("no ICD reference" in f["issue"] for f in findings))

    def test_non_interface_req_is_skipped(self):
        req = {
            "id": "TPR-006",
            "text": "Performance requirement",
            "verification_method": "test",
            "req_type": "performance",
        }
        self.assertEqual(check_interface_requirement_linkage(req, []), [])

    def test_set_of_icds_is_accepted(self):
        req = {
            "id": "IR-004",
            "text": "Interface to thermal control",
            "verification_method": "inspection",
            "req_type": "interface",
            "icd_reference": "ICD-TC-001",
        }
        self.assertEqual(
            check_interface_requirement_linkage(req, {"ICD-TC-001", "ICD-PWR-001"}), []
        )

    def test_non_dict_req_raises(self):
        with self.assertRaises(TsValidationError):
            check_interface_requirement_linkage("bad", [])

    def test_invalid_registered_icds_type_raises(self):
        req = {"id": "IR-005", "req_type": "interface", "icd_reference": "X"}
        with self.assertRaises(TsValidationError):
            check_interface_requirement_linkage(req, "not-a-list")


# ---------------------------------------------------------------------------
# Completeness scoring
# ---------------------------------------------------------------------------

class TestCompletenessScore(unittest.TestCase):

    def test_complete_document_scores_1_0(self):
        self.assertAlmostEqual(score_ts_completeness(_minimal_ts_doc()), 1.0)

    def test_empty_document_scores_0(self):
        self.assertAlmostEqual(score_ts_completeness({}), 0.0)

    def test_partial_document_scores_proportionally(self):
        ts_doc = {s: "present" for s in MANDATORY_SECTIONS[:3]}
        expected = 3 / len(MANDATORY_SECTIONS)
        self.assertAlmostEqual(score_ts_completeness(ts_doc), expected)

    def test_non_dict_raises(self):
        with self.assertRaises(TsValidationError):
            score_ts_completeness(None)


# ---------------------------------------------------------------------------
# Full document validation
# ---------------------------------------------------------------------------

class TestFullDocumentValidation(unittest.TestCase):

    def test_valid_document_is_compliant(self):
        result = validate_ts_document(_minimal_ts_doc(), registered_icds=["ICD-PWR-001"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["structure_findings"], [])

    def test_missing_section_makes_document_non_compliant(self):
        ts_doc = _minimal_ts_doc()
        del ts_doc["verification_table"]
        result = validate_ts_document(ts_doc, registered_icds=["ICD-PWR-001"])
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["structure_findings"]), 0)

    def test_invalid_requirement_makes_document_non_compliant(self):
        ts_doc = _minimal_ts_doc()
        ts_doc["technical_performance_requirements"].append(
            {"id": "TPR-BAD", "text": "Underdefined requirement"}  # no verification_method
        )
        result = validate_ts_document(ts_doc, registered_icds=["ICD-PWR-001"])
        self.assertFalse(result["compliant"])

    def test_unregistered_icd_makes_document_non_compliant(self):
        result = validate_ts_document(_minimal_ts_doc(), registered_icds=[])
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["interface_findings"]) > 0)

    def test_completeness_score_present_in_result(self):
        result = validate_ts_document(_minimal_ts_doc(), registered_icds=["ICD-PWR-001"])
        self.assertIn("completeness_score", result)
        self.assertAlmostEqual(result["completeness_score"], 1.0)

    def test_result_contains_all_expected_keys(self):
        result = validate_ts_document({})
        self.assertIn("structure_findings", result)
        self.assertIn("requirement_findings", result)
        self.assertIn("interface_findings", result)
        self.assertIn("completeness_score", result)
        self.assertIn("compliant", result)

    def test_no_registered_icds_defaults_to_empty(self):
        ts_doc = _minimal_ts_doc()
        ts_doc["interface_requirements"] = []
        result = validate_ts_document(ts_doc)
        self.assertIsInstance(result["interface_findings"], list)


if __name__ == "__main__":
    unittest.main()
