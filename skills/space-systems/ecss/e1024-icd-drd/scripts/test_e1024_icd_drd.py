"""
Offline unittest for e1024_icd_drd_logic.py.
Run: python3 test_e1024_icd_drd.py
stdlib only; no network.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from e1024_icd_drd_logic import (
    ICDValidationError,
    validate_identification,
    validate_interface_types,
    validate_required_sections,
    validate_requirement_traceability,
    validate_verification_coverage,
    validate_icd_drd_compliance,
    KNOWN_INTERFACE_TYPES,
    KNOWN_VERIFICATION_METHODS,
    REQUIRED_SECTIONS,
)


def _minimal_valid_icd():
    return {
        "icd_id": "ICD-SAT-PLM-001",
        "revision": "A",
        "interface_pair": ["Satellite Platform", "Payload Module"],
        "interface_types": ["electrical", "mechanical"],
        "sections": {
            "scope": "Defines the interface between the platform and payload module.",
            "reference_documents": "IRD-SAT-001 rev B; SYS-SPEC-001 rev C",
            "interface_description": "Electrical connector J1 (28 V, 5 A max); bolt pattern M6x4.",
            "verification_requirements": "ICD-REQ-001 verified by test; ICD-REQ-002 by analysis.",
        },
        "requirements": [
            {"req_id": "ICD-REQ-001", "parent_ref": "IRD-SAT-001/REQ-042"},
            {"req_id": "ICD-REQ-002", "parent_ref": "SYS-SPEC-001/REQ-007"},
        ],
        "verification_methods": [
            {"req_id": "ICD-REQ-001", "method": "test"},
            {"req_id": "ICD-REQ-002", "method": "analysis"},
        ],
    }


class TestIdentification(unittest.TestCase):

    def test_valid_identification_passes(self):
        icd = _minimal_valid_icd()
        self.assertEqual(validate_identification(icd), [])

    def test_missing_icd_id_flagged(self):
        icd = _minimal_valid_icd()
        del icd["icd_id"]
        findings = validate_identification(icd)
        self.assertTrue(any("icd_id" in f for f in findings))

    def test_empty_icd_id_flagged(self):
        icd = _minimal_valid_icd()
        icd["icd_id"] = "   "
        findings = validate_identification(icd)
        self.assertTrue(any("icd_id" in f for f in findings))

    def test_missing_revision_flagged(self):
        icd = _minimal_valid_icd()
        del icd["revision"]
        findings = validate_identification(icd)
        self.assertTrue(any("revision" in f for f in findings))

    def test_interface_pair_wrong_size_flagged(self):
        icd = _minimal_valid_icd()
        icd["interface_pair"] = ["OnlyOneItem"]
        findings = validate_identification(icd)
        self.assertTrue(any("interface_pair" in f for f in findings))

    def test_interface_pair_empty_first_item_flagged(self):
        icd = _minimal_valid_icd()
        icd["interface_pair"] = ["", "Payload Module"]
        findings = validate_identification(icd)
        self.assertTrue(any("first item" in f for f in findings))

    def test_interface_pair_empty_second_item_flagged(self):
        icd = _minimal_valid_icd()
        icd["interface_pair"] = ["Satellite Platform", "  "]
        findings = validate_identification(icd)
        self.assertTrue(any("second item" in f for f in findings))

    def test_interface_pair_not_list_flagged(self):
        icd = _minimal_valid_icd()
        icd["interface_pair"] = "Satellite Platform / Payload Module"
        findings = validate_identification(icd)
        self.assertTrue(any("interface_pair" in f for f in findings))


class TestInterfaceTypes(unittest.TestCase):

    def test_all_known_types_pass(self):
        for t in KNOWN_INTERFACE_TYPES:
            self.assertEqual(validate_interface_types([t]), [])

    def test_unrecognized_type_flagged(self):
        findings = validate_interface_types(["electromagnetic"])
        self.assertTrue(any("unrecognized interface type" in f for f in findings))

    def test_empty_types_list_flagged(self):
        findings = validate_interface_types([])
        self.assertTrue(len(findings) > 0)

    def test_mixed_valid_invalid_flags_only_invalid(self):
        findings = validate_interface_types(["mechanical", "plasma"])
        self.assertTrue(any("plasma" in f for f in findings))
        self.assertFalse(any("mechanical" in f for f in findings))


class TestRequiredSections(unittest.TestCase):

    def test_all_sections_present_passes(self):
        sections = {s: "content" for s in REQUIRED_SECTIONS}
        self.assertEqual(validate_required_sections(sections), [])

    def test_missing_scope_flagged(self):
        sections = {s: "content" for s in REQUIRED_SECTIONS}
        del sections["scope"]
        findings = validate_required_sections(sections)
        self.assertTrue(any("scope" in f for f in findings))

    def test_empty_section_flagged(self):
        sections = {s: "content" for s in REQUIRED_SECTIONS}
        sections["interface_description"] = ""
        findings = validate_required_sections(sections)
        self.assertTrue(any("interface_description" in f for f in findings))

    def test_sections_not_dict_flagged(self):
        findings = validate_required_sections("not a dict")
        self.assertTrue(len(findings) > 0)


class TestRequirementTraceability(unittest.TestCase):

    def test_requirements_with_parent_ref_pass(self):
        reqs = [
            {"req_id": "REQ-001", "parent_ref": "IRD-001/REQ-01"},
            {"req_id": "REQ-002", "parent_ref": "SYS-SPEC/REQ-07"},
        ]
        self.assertEqual(validate_requirement_traceability(reqs), [])

    def test_requirement_without_parent_ref_flagged(self):
        reqs = [{"req_id": "REQ-001", "parent_ref": ""}]
        findings = validate_requirement_traceability(reqs)
        self.assertTrue(any("REQ-001" in f for f in findings))

    def test_requirement_missing_parent_ref_key_flagged(self):
        reqs = [{"req_id": "REQ-001"}]
        findings = validate_requirement_traceability(reqs)
        self.assertTrue(any("REQ-001" in f for f in findings))

    def test_empty_requirements_list_flagged(self):
        findings = validate_requirement_traceability([])
        self.assertTrue(len(findings) > 0)


class TestVerificationCoverage(unittest.TestCase):

    def test_all_requirements_covered_passes(self):
        reqs = [{"req_id": "REQ-001"}, {"req_id": "REQ-002"}]
        vms = [
            {"req_id": "REQ-001", "method": "test"},
            {"req_id": "REQ-002", "method": "analysis"},
        ]
        self.assertEqual(validate_verification_coverage(reqs, vms), [])

    def test_requirement_without_method_flagged(self):
        reqs = [{"req_id": "REQ-001"}]
        vms = []
        findings = validate_verification_coverage(reqs, vms)
        self.assertTrue(any("REQ-001" in f for f in findings))

    def test_unrecognized_method_flagged(self):
        reqs = [{"req_id": "REQ-001"}]
        vms = [{"req_id": "REQ-001", "method": "simulation"}]
        findings = validate_verification_coverage(reqs, vms)
        self.assertTrue(any("simulation" in f for f in findings))

    def test_all_known_methods_accepted(self):
        for method in KNOWN_VERIFICATION_METHODS:
            reqs = [{"req_id": "REQ-X"}]
            vms = [{"req_id": "REQ-X", "method": method}]
            self.assertEqual(validate_verification_coverage(reqs, vms), [])


class TestFullCompliance(unittest.TestCase):

    def test_clean_icd_returns_no_findings(self):
        icd = _minimal_valid_icd()
        self.assertEqual(validate_icd_drd_compliance(icd), [])

    def test_non_dict_raises_validation_error(self):
        with self.assertRaises(ICDValidationError):
            validate_icd_drd_compliance("not a dict")

    def test_multiple_issues_all_surfaced(self):
        icd = {
            "icd_id": "",
            "revision": "",
            "interface_pair": ["OnlyOne"],
            "interface_types": ["plasma"],
            "sections": {},
            "requirements": [{"req_id": "REQ-BAD"}],
            "verification_methods": [],
        }
        findings = validate_icd_drd_compliance(icd)
        self.assertGreater(len(findings), 4, "expected at least 5 findings for malformed ICD")

    def test_three_part_interface_pair_flagged(self):
        icd = _minimal_valid_icd()
        icd["interface_pair"] = ["A", "B", "C"]
        findings = validate_icd_drd_compliance(icd)
        self.assertTrue(any("interface_pair" in f for f in findings))

    def test_additional_unknown_section_does_not_cause_failure(self):
        icd = _minimal_valid_icd()
        icd["sections"]["notes"] = "Additional notes"
        self.assertEqual(validate_icd_drd_compliance(icd), [])


if __name__ == "__main__":
    unittest.main()
