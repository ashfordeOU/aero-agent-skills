"""
Gate 3 contract tests for interface_and_tolerance_requirements_logic.
stdlib unittest only; offline; deterministic.
Run: python3 test_interface_and_tolerance_requirements.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interface_and_tolerance_requirements_logic import (
    INTERFACE_TYPES,
    STACKUP_METHODS,
    TOLERANCE_TYPES,
    InterfaceDefinitionError,
    ToleranceStackupError,
    categorize_interface,
    validate_interface_record,
    compute_tolerance_stackup,
    check_alignment_budget,
    assess_interface_set,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(
    iid="IF-001",
    itype="mechanical-fastened",
    tolerances=None,
    reference_frame="CS-1",
    icd_reference="ICD-STR-001",
):
    if tolerances is None:
        tolerances = [{"type": "linear", "value": 0.1, "unit": "mm"}]
    return {
        "id": iid,
        "type": itype,
        "tolerances": tolerances,
        "reference_frame": reference_frame,
        "icd_reference": icd_reference,
    }


# ---------------------------------------------------------------------------
# categorize_interface
# ---------------------------------------------------------------------------

class TestCategorizeInterface(unittest.TestCase):

    def test_mechanical_fastened_accepted(self):
        self.assertEqual(categorize_interface("mechanical-fastened"), "mechanical-fastened")

    def test_adhesive_bonded_accepted(self):
        self.assertEqual(categorize_interface("adhesive-bonded"), "adhesive-bonded")

    def test_bearing_contact_accepted(self):
        self.assertEqual(categorize_interface("bearing-contact"), "bearing-contact")

    def test_alignment_critical_accepted(self):
        self.assertEqual(categorize_interface("alignment-critical"), "alignment-critical")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(categorize_interface("  bearing-contact  "), "bearing-contact")

    def test_case_normalized(self):
        self.assertEqual(categorize_interface("MECHANICAL-FASTENED"), "mechanical-fastened")

    def test_unknown_type_raises(self):
        with self.assertRaises(InterfaceDefinitionError):
            categorize_interface("welded-joint")

    def test_empty_string_raises(self):
        with self.assertRaises(InterfaceDefinitionError):
            categorize_interface("")


# ---------------------------------------------------------------------------
# validate_interface_record
# ---------------------------------------------------------------------------

class TestValidateInterfaceRecord(unittest.TestCase):

    def test_complete_record_no_findings(self):
        record = _make_record()
        findings = validate_interface_record(record)
        self.assertEqual(findings, [])

    def test_missing_reference_frame_flagged(self):
        record = _make_record(reference_frame="")
        findings = validate_interface_record(record)
        self.assertTrue(any("reference frame" in f for f in findings))

    def test_missing_icd_reference_flagged(self):
        record = _make_record(icd_reference="")
        findings = validate_interface_record(record)
        self.assertTrue(any("ICD" in f for f in findings))

    def test_unrecognized_interface_type_flagged(self):
        record = _make_record(itype="spot-welded")
        findings = validate_interface_record(record)
        self.assertTrue(any("Unrecognized interface type" in f for f in findings))

    def test_no_tolerances_flagged(self):
        record = _make_record(tolerances=[])
        findings = validate_interface_record(record)
        self.assertTrue(any("no tolerance features" in f for f in findings))

    def test_bad_tolerance_type_flagged(self):
        record = _make_record(tolerances=[{"type": "roundness", "value": 0.05, "unit": "mm"}])
        findings = validate_interface_record(record)
        self.assertTrue(any("unrecognized type" in f for f in findings))

    def test_negative_tolerance_value_flagged(self):
        record = _make_record(tolerances=[{"type": "linear", "value": -0.1, "unit": "mm"}])
        findings = validate_interface_record(record)
        self.assertTrue(any("non-negative" in f for f in findings))

    def test_none_tolerance_value_flagged(self):
        record = _make_record(tolerances=[{"type": "angular", "value": None, "unit": "deg"}])
        findings = validate_interface_record(record)
        self.assertTrue(any("non-negative" in f for f in findings))

    def test_multiple_valid_tolerances_no_findings(self):
        tols = [
            {"type": "linear", "value": 0.1, "unit": "mm"},
            {"type": "angular", "value": 0.05, "unit": "deg"},
            {"type": "flatness", "value": 0.02, "unit": "mm"},
        ]
        record = _make_record(tolerances=tols)
        self.assertEqual(validate_interface_record(record), [])

    def test_zero_tolerance_value_allowed(self):
        record = _make_record(tolerances=[{"type": "linear", "value": 0.0, "unit": "mm"}])
        self.assertEqual(validate_interface_record(record), [])


# ---------------------------------------------------------------------------
# compute_tolerance_stackup
# ---------------------------------------------------------------------------

class TestComputeToleranceStackup(unittest.TestCase):

    def _tols(self, values):
        return [{"type": "linear", "value": v, "unit": "mm"} for v in values]

    def test_worst_case_sum(self):
        result = compute_tolerance_stackup(self._tols([0.1, 0.2, 0.3]), "worst-case")
        self.assertAlmostEqual(result, 0.6)

    def test_rss_value(self):
        result = compute_tolerance_stackup(self._tols([3.0, 4.0]), "rss")
        self.assertAlmostEqual(result, 5.0)

    def test_rss_single_value(self):
        result = compute_tolerance_stackup(self._tols([7.0]), "rss")
        self.assertAlmostEqual(result, 7.0)

    def test_worst_case_single_value(self):
        result = compute_tolerance_stackup(self._tols([0.5]), "worst-case")
        self.assertAlmostEqual(result, 0.5)

    def test_empty_list_raises(self):
        with self.assertRaises(ToleranceStackupError):
            compute_tolerance_stackup([], "worst-case")

    def test_unknown_method_raises(self):
        with self.assertRaises(ToleranceStackupError):
            compute_tolerance_stackup(self._tols([0.1]), "monte-carlo")

    def test_negative_value_raises(self):
        with self.assertRaises(ToleranceStackupError):
            compute_tolerance_stackup([{"type": "linear", "value": -1.0}], "rss")

    def test_zero_values_worst_case(self):
        result = compute_tolerance_stackup(self._tols([0.0, 0.0, 0.0]), "worst-case")
        self.assertAlmostEqual(result, 0.0)

    def test_rss_four_equal_values(self):
        result = compute_tolerance_stackup(self._tols([1.0, 1.0, 1.0, 1.0]), "rss")
        self.assertAlmostEqual(result, 2.0)


# ---------------------------------------------------------------------------
# check_alignment_budget
# ---------------------------------------------------------------------------

class TestCheckAlignmentBudget(unittest.TestCase):

    def test_compliant_when_stackup_below_budget(self):
        result = check_alignment_budget(0.4, 0.5)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])
        self.assertAlmostEqual(result["margin"], 0.1)

    def test_compliant_when_stackup_equals_budget(self):
        result = check_alignment_budget(0.5, 0.5)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.0)

    def test_non_compliant_when_stackup_exceeds_budget(self):
        result = check_alignment_budget(0.7, 0.5)
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["finding"])
        self.assertAlmostEqual(result["margin"], -0.2)

    def test_finding_contains_values_when_exceeded(self):
        result = check_alignment_budget(1.5, 1.0)
        self.assertIn("1.5", result["finding"])
        self.assertIn("1", result["finding"])

    def test_zero_budget_raises(self):
        with self.assertRaises(InterfaceDefinitionError):
            check_alignment_budget(0.1, 0.0)

    def test_negative_budget_raises(self):
        with self.assertRaises(InterfaceDefinitionError):
            check_alignment_budget(0.1, -1.0)

    def test_result_contains_all_keys(self):
        result = check_alignment_budget(0.3, 0.5)
        for key in ("stackup", "budget", "margin", "compliant", "finding"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# assess_interface_set
# ---------------------------------------------------------------------------

class TestAssessInterfaceSet(unittest.TestCase):

    def _good_set(self):
        return [
            _make_record("IF-001", "mechanical-fastened",
                         [{"type": "linear", "value": 0.1, "unit": "mm"}]),
            _make_record("IF-002", "alignment-critical",
                         [{"type": "angular", "value": 0.05, "unit": "deg"}]),
        ]

    def test_all_compliant_returns_compliant_true(self):
        result = assess_interface_set(self._good_set(), 1.0, "worst-case")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["interface_findings"], [])
        self.assertEqual(result["budget_findings"], [])
        self.assertEqual(result["missing_icd"], [])

    def test_budget_exceedance_captured(self):
        records = [
            _make_record("IF-003", "mechanical-fastened",
                         [{"type": "linear", "value": 0.9, "unit": "mm"}]),
        ]
        result = assess_interface_set(records, 0.5, "worst-case")
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["budget_findings"]) > 0)
        self.assertIn("IF-003", result["budget_findings"][0])

    def test_missing_icd_surfaces_in_output(self):
        records = [_make_record("IF-004", icd_reference="")]
        result = assess_interface_set(records, 1.0, "worst-case")
        self.assertFalse(result["compliant"])
        self.assertIn("IF-004", result["missing_icd"])

    def test_missing_reference_frame_surfaces_in_output(self):
        records = [_make_record("IF-005", reference_frame="")]
        result = assess_interface_set(records, 1.0, "worst-case")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("IF-005" in f for f in result["interface_findings"]))

    def test_rss_method_accepted(self):
        records = [
            _make_record("IF-006", "bearing-contact",
                         [{"type": "linear", "value": 0.3, "unit": "mm"},
                          {"type": "linear", "value": 0.4, "unit": "mm"}]),
        ]
        result = assess_interface_set(records, 1.0, "rss")
        self.assertTrue(result["compliant"])

    def test_empty_interface_list_is_compliant(self):
        result = assess_interface_set([], 1.0, "worst-case")
        self.assertTrue(result["compliant"])

    def test_mixed_findings_not_compliant(self):
        records = [
            _make_record("IF-007", icd_reference=""),
            _make_record("IF-008", "adhesive-bonded",
                         [{"type": "linear", "value": 0.8, "unit": "mm"}]),
        ]
        result = assess_interface_set(records, 0.5, "worst-case")
        self.assertFalse(result["compliant"])

    def test_result_contains_required_keys(self):
        result = assess_interface_set(self._good_set(), 1.0, "worst-case")
        for key in ("interface_findings", "budget_findings", "missing_icd", "compliant"):
            self.assertIn(key, result)

    def test_unrecognized_interface_type_is_finding(self):
        records = [_make_record("IF-009", itype="bolted-flange")]
        result = assess_interface_set(records, 1.0, "worst-case")
        self.assertFalse(result["compliant"])
        self.assertTrue(any("IF-009" in f for f in result["interface_findings"]))

    def test_rss_stack_under_tight_budget(self):
        records = [
            _make_record("IF-010", "alignment-critical",
                         [{"type": "linear", "value": 0.1, "unit": "mm"},
                          {"type": "angular", "value": 0.1, "unit": "deg"}]),
        ]
        expected_su = math.sqrt(0.01 + 0.01)
        result = assess_interface_set(records, expected_su + 0.001, "rss")
        self.assertTrue(result["compliant"])


if __name__ == "__main__":
    unittest.main()
