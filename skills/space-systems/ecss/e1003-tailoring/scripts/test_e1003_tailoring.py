"""
test_e1003_tailoring.py
Stdlib unittest for e1003_tailoring_logic.py.
Run: python3 test_e1003_tailoring.py
Deterministic, offline, no network dependencies.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_tailoring_logic import (
    VALID_PROJECT_CLASSES,
    APPLICABILITY_APPLICABLE,
    APPLICABILITY_NOT_APPLICABLE,
    APPLICABILITY_TAILORED,
    APPLICABILITY_CONDITIONAL,
    TailoringMatrix,
    ComplianceMatrix,
    VerificationMatrix,
    build_tailoring_matrix,
    generate_compliance_matrix,
    generate_verification_matrix,
    check_completeness,
    summarize_matrix,
    validate_project_class,
    validate_applicability,
    validate_verification_methods,
)


class TestValidateProjectClass(unittest.TestCase):
    def test_all_valid_classes_accepted(self):
        for cls in ("A", "B", "C", "D"):
            validate_project_class(cls)  # must not raise

    def test_invalid_letter_raises(self):
        with self.assertRaises(ValueError):
            validate_project_class("E")

    def test_lowercase_rejected(self):
        with self.assertRaises(ValueError):
            validate_project_class("a")

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_project_class("")

    def test_numeric_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_project_class("1")


class TestValidateApplicability(unittest.TestCase):
    def test_all_valid_statuses_accepted(self):
        for status in ("A", "NA", "T", "C"):
            validate_applicability(status)

    def test_unknown_code_raises(self):
        with self.assertRaises(ValueError):
            validate_applicability("X")

    def test_lowercase_raises(self):
        with self.assertRaises(ValueError):
            validate_applicability("na")


class TestValidateVerificationMethods(unittest.TestCase):
    def test_all_valid_method_codes_accepted(self):
        validate_verification_methods(["T", "A", "I", "R"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_verification_methods(["T", "Z"])

    def test_empty_list_accepted(self):
        validate_verification_methods([])


class TestBuildTailoringMatrix(unittest.TestCase):
    def test_returns_tailoring_matrix_instance(self):
        m = build_tailoring_matrix("A")
        self.assertIsInstance(m, TailoringMatrix)

    def test_project_class_stored_on_matrix(self):
        m = build_tailoring_matrix("B")
        self.assertEqual(m.project_class, "B")

    def test_all_catalogue_requirements_present(self):
        m = build_tailoring_matrix("A")
        self.assertGreaterEqual(len(m.entries), 15)

    def test_class_a_has_more_applicable_than_class_d(self):
        ma = build_tailoring_matrix("A")
        md = build_tailoring_matrix("D")
        sa = summarize_matrix(ma)
        sd = summarize_matrix(md)
        self.assertGreater(sa[APPLICABILITY_APPLICABLE], sd[APPLICABILITY_APPLICABLE])

    def test_req010_is_not_applicable_for_class_d(self):
        m = build_tailoring_matrix("D")
        entry = next(e for e in m.entries if e.requirement_id == "REQ-010")
        self.assertEqual(entry.applicability, APPLICABILITY_NOT_APPLICABLE)

    def test_override_applicability_applied(self):
        m = build_tailoring_matrix(
            "A",
            overrides={
                "REQ-010": {
                    "applicability": "NA",
                    "rationale": "Mission type excludes criticality tracking.",
                }
            },
        )
        entry = next(e for e in m.entries if e.requirement_id == "REQ-010")
        self.assertEqual(entry.applicability, "NA")

    def test_override_verification_methods_applied(self):
        m = build_tailoring_matrix(
            "B",
            overrides={
                "REQ-001": {
                    "verification_methods": ["R"],
                    "rationale": "Simplified review sufficient for this mission.",
                }
            },
        )
        entry = next(e for e in m.entries if e.requirement_id == "REQ-001")
        self.assertEqual(entry.verification_methods, ["R"])

    def test_override_rationale_stored(self):
        rationale = "Budget constraints prevent full test campaign."
        m = build_tailoring_matrix(
            "C",
            overrides={
                "REQ-009": {
                    "applicability": "T",
                    "verification_methods": ["I"],
                    "rationale": rationale,
                }
            },
        )
        entry = next(e for e in m.entries if e.requirement_id == "REQ-009")
        self.assertEqual(entry.rationale, rationale)

    def test_invalid_project_class_raises(self):
        with self.assertRaises(ValueError):
            build_tailoring_matrix("Z")

    def test_invalid_override_applicability_raises(self):
        with self.assertRaises(ValueError):
            build_tailoring_matrix(
                "A", overrides={"REQ-001": {"applicability": "BOGUS"}}
            )

    def test_invalid_override_verification_raises(self):
        with self.assertRaises(ValueError):
            build_tailoring_matrix(
                "A", overrides={"REQ-001": {"verification_methods": ["X"]}}
            )

    def test_no_overrides_arg_accepted(self):
        m = build_tailoring_matrix("C")
        self.assertGreater(len(m.entries), 0)

    def test_empty_overrides_dict_accepted(self):
        m = build_tailoring_matrix("B", overrides={})
        self.assertGreater(len(m.entries), 0)


class TestGenerateComplianceMatrix(unittest.TestCase):
    def test_returns_compliance_matrix_instance(self):
        m = build_tailoring_matrix("A")
        cm = generate_compliance_matrix(m)
        self.assertIsInstance(cm, ComplianceMatrix)

    def test_row_count_matches_entry_count(self):
        m = build_tailoring_matrix("A")
        cm = generate_compliance_matrix(m)
        self.assertEqual(len(cm.rows), len(m.entries))

    def test_project_class_propagated(self):
        m = build_tailoring_matrix("C")
        cm = generate_compliance_matrix(m)
        self.assertEqual(cm.project_class, "C")

    def test_applicable_count_positive_for_class_a(self):
        m = build_tailoring_matrix("A")
        cm = generate_compliance_matrix(m)
        self.assertGreater(cm.applicable_count, 0)

    def test_not_applicable_count_positive_for_class_d(self):
        m = build_tailoring_matrix("D")
        cm = generate_compliance_matrix(m)
        self.assertGreater(cm.not_applicable_count, 0)

    def test_applicable_plus_not_applicable_equals_total(self):
        m = build_tailoring_matrix("B")
        cm = generate_compliance_matrix(m)
        s = summarize_matrix(m)
        expected_na = s[APPLICABILITY_NOT_APPLICABLE]
        self.assertEqual(cm.not_applicable_count, expected_na)


class TestGenerateVerificationMatrix(unittest.TestCase):
    def test_returns_verification_matrix_instance(self):
        m = build_tailoring_matrix("A")
        vm = generate_verification_matrix(m)
        self.assertIsInstance(vm, VerificationMatrix)

    def test_not_applicable_requirements_excluded(self):
        m = build_tailoring_matrix("D")
        vm = generate_verification_matrix(m)
        na_ids = {
            e.requirement_id
            for e in m.entries
            if e.applicability == APPLICABILITY_NOT_APPLICABLE
        }
        vm_ids = {r.requirement_id for r in vm.rows}
        for na_id in na_ids:
            self.assertNotIn(na_id, vm_ids)

    def test_verification_methods_preserved(self):
        m = build_tailoring_matrix(
            "A",
            overrides={
                "REQ-001": {
                    "verification_methods": ["T", "R"],
                    "rationale": "Full test plus design review.",
                }
            },
        )
        vm = generate_verification_matrix(m)
        row = next(r for r in vm.rows if r.requirement_id == "REQ-001")
        self.assertIn("T", row.verification_methods)
        self.assertIn("R", row.verification_methods)

    def test_class_a_has_at_least_as_many_rows_as_class_d(self):
        vma = generate_verification_matrix(build_tailoring_matrix("A"))
        vmd = generate_verification_matrix(build_tailoring_matrix("D"))
        self.assertGreaterEqual(len(vma.rows), len(vmd.rows))

    def test_project_class_propagated(self):
        m = build_tailoring_matrix("B")
        vm = generate_verification_matrix(m)
        self.assertEqual(vm.project_class, "B")


class TestCheckCompleteness(unittest.TestCase):
    def test_default_class_a_matrix_is_complete(self):
        m = build_tailoring_matrix("A")
        findings = check_completeness(m)
        self.assertEqual(findings, [])

    def test_default_class_b_matrix_is_complete(self):
        m = build_tailoring_matrix("B")
        findings = check_completeness(m)
        self.assertEqual(findings, [])

    def test_missing_verification_method_flagged(self):
        m = build_tailoring_matrix("A")
        for e in m.entries:
            if e.applicability == APPLICABILITY_APPLICABLE:
                e.verification_methods = []
                target_id = e.requirement_id
                break
        findings = check_completeness(m)
        self.assertTrue(
            any(target_id in f and "verification method" in f for f in findings)
        )

    def test_tailored_without_rationale_flagged(self):
        m = build_tailoring_matrix(
            "A",
            overrides={
                "REQ-001": {
                    "applicability": "T",
                    "verification_methods": ["R"],
                    "rationale": "",
                }
            },
        )
        findings = check_completeness(m)
        self.assertTrue(any("REQ-001" in f and "rationale" in f for f in findings))

    def test_conditional_without_rationale_flagged(self):
        m = build_tailoring_matrix(
            "B",
            overrides={
                "REQ-003": {
                    "applicability": "C",
                    "verification_methods": ["A"],
                    "rationale": "",
                }
            },
        )
        findings = check_completeness(m)
        self.assertTrue(any("REQ-003" in f for f in findings))

    def test_not_applicable_not_flagged_for_missing_verification(self):
        m = build_tailoring_matrix("D")
        # REQ-010 is NA for class D — must not generate a "no verification" finding
        findings = check_completeness(m)
        false_positives = [
            f for f in findings
            if "REQ-010" in f and "verification method" in f
        ]
        self.assertEqual(false_positives, [])

    def test_tailored_with_rationale_not_flagged(self):
        m = build_tailoring_matrix(
            "A",
            overrides={
                "REQ-002": {
                    "applicability": "T",
                    "verification_methods": ["R"],
                    "rationale": "Consolidated with mission requirements document.",
                }
            },
        )
        findings = check_completeness(m)
        req002_findings = [f for f in findings if "REQ-002" in f]
        self.assertEqual(req002_findings, [])


class TestSummarizeMatrix(unittest.TestCase):
    def test_returns_dict_with_all_status_keys(self):
        m = build_tailoring_matrix("A")
        s = summarize_matrix(m)
        for key in ("A", "NA", "T", "C"):
            self.assertIn(key, s)

    def test_counts_sum_to_total_entry_count(self):
        m = build_tailoring_matrix("B")
        s = summarize_matrix(m)
        self.assertEqual(sum(s.values()), len(m.entries))

    def test_class_d_has_at_least_one_not_applicable(self):
        m = build_tailoring_matrix("D")
        s = summarize_matrix(m)
        self.assertGreater(s[APPLICABILITY_NOT_APPLICABLE], 0)


if __name__ == "__main__":
    unittest.main()
