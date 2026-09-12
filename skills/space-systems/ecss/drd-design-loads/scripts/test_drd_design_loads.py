"""
Gate 3 contract test for drd_design_loads_logic.
stdlib unittest only — offline, deterministic.
Run: python3 test_drd_design_loads.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from drd_design_loads_logic import (
    LOAD_CASE_TYPES,
    DEFAULT_YIELD_FACTOR,
    DEFAULT_ULTIMATE_FACTOR,
    DEFAULT_PARTIAL_SAFETY_FACTOR,
    categorize_load_type,
    compute_dll,
    compute_dyl,
    compute_dul,
    process_load_case,
    process_design_loads_document,
)


class TestCategorizeLadType(unittest.TestCase):

    def test_categorize_valid_static(self):
        self.assertEqual(categorize_load_type("static"), "static")

    def test_categorize_valid_quasi_static(self):
        self.assertEqual(categorize_load_type("quasi-static"), "quasi-static")

    def test_categorize_valid_dynamic_sine(self):
        self.assertEqual(categorize_load_type("dynamic-sine"), "dynamic-sine")

    def test_categorize_valid_acoustic(self):
        self.assertEqual(categorize_load_type("acoustic"), "acoustic")

    def test_categorize_strips_whitespace(self):
        self.assertEqual(categorize_load_type("  thermal  "), "thermal")

    def test_categorize_case_insensitive(self):
        self.assertEqual(categorize_load_type("PRESSURE"), "pressure")

    def test_categorize_unknown_type_raises(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_load_type("aerodynamic-buffet")
        self.assertIn("not in the ECSS-E-ST-32C recognized taxonomy", str(ctx.exception))

    def test_categorize_non_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_load_type(42)

    def test_all_taxonomy_types_accepted(self):
        for load_type in LOAD_CASE_TYPES:
            self.assertEqual(categorize_load_type(load_type), load_type)


class TestComputeDLL(unittest.TestCase):

    def test_dll_default_factor(self):
        self.assertAlmostEqual(compute_dll(1000.0), 1000.0)

    def test_dll_custom_factor(self):
        self.assertAlmostEqual(compute_dll(1000.0, 1.2), 1200.0)

    def test_dll_maximum_factor(self):
        self.assertAlmostEqual(compute_dll(500.0, 4.0), 2000.0)

    def test_dll_zero_ll(self):
        self.assertAlmostEqual(compute_dll(0.0, 1.25), 0.0)

    def test_dll_negative_ll_raises(self):
        with self.assertRaises(ValueError) as ctx:
            compute_dll(-100.0)
        self.assertIn("non-negative", str(ctx.exception))

    def test_dll_factor_below_minimum_raises(self):
        with self.assertRaises(ValueError) as ctx:
            compute_dll(1000.0, 0.5)
        self.assertIn("outside the accepted range", str(ctx.exception))

    def test_dll_factor_above_maximum_raises(self):
        with self.assertRaises(ValueError) as ctx:
            compute_dll(1000.0, 5.0)
        self.assertIn("outside the accepted range", str(ctx.exception))


class TestComputeDYL(unittest.TestCase):

    def test_dyl_default_factor_equals_dll(self):
        self.assertAlmostEqual(compute_dyl(1000.0), 1000.0 * DEFAULT_YIELD_FACTOR)

    def test_dyl_custom_factor(self):
        self.assertAlmostEqual(compute_dyl(1000.0, 1.1), 1100.0)

    def test_dyl_negative_dll_raises(self):
        with self.assertRaises(ValueError):
            compute_dyl(-50.0)

    def test_dyl_out_of_range_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_dyl(1000.0, 0.9)


class TestComputeDUL(unittest.TestCase):

    def test_dul_default_factor(self):
        self.assertAlmostEqual(compute_dul(1000.0), 1000.0 * DEFAULT_ULTIMATE_FACTOR)

    def test_dul_custom_factor(self):
        self.assertAlmostEqual(compute_dul(800.0, 1.5), 1200.0)

    def test_dul_negative_dll_raises(self):
        with self.assertRaises(ValueError):
            compute_dul(-1.0)

    def test_dul_out_of_range_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_dul(1000.0, 4.5)


class TestDULExceedsDYLForDefaultFactors(unittest.TestCase):

    def test_dul_greater_than_dyl_with_defaults(self):
        dll = compute_dll(1000.0, DEFAULT_PARTIAL_SAFETY_FACTOR)
        dyl = compute_dyl(dll, DEFAULT_YIELD_FACTOR)
        dul = compute_dul(dll, DEFAULT_ULTIMATE_FACTOR)
        self.assertGreater(dul, dyl)


class TestProcessLoadCase(unittest.TestCase):

    def _valid_case(self):
        return {
            "id": "LC-001",
            "type": "quasi-static",
            "limit_load": 5000.0,
        }

    def test_valid_case_no_findings(self):
        result = process_load_case(self._valid_case())
        self.assertEqual(result["findings"], [])

    def test_valid_case_dll_computed(self):
        result = process_load_case(self._valid_case())
        self.assertAlmostEqual(result["dll"], 5000.0 * DEFAULT_PARTIAL_SAFETY_FACTOR)

    def test_valid_case_dyl_computed(self):
        result = process_load_case(self._valid_case())
        self.assertAlmostEqual(result["dyl"], result["dll"] * DEFAULT_YIELD_FACTOR)

    def test_valid_case_dul_computed(self):
        result = process_load_case(self._valid_case())
        self.assertAlmostEqual(result["dul"], result["dll"] * DEFAULT_ULTIMATE_FACTOR)

    def test_missing_limit_load_produces_finding(self):
        case = {"id": "LC-002", "type": "static"}
        result = process_load_case(case)
        self.assertTrue(any("limit_load" in f for f in result["findings"]))
        self.assertIsNone(result["dll"])

    def test_missing_id_produces_finding(self):
        case = {"type": "static", "limit_load": 100.0}
        result = process_load_case(case)
        self.assertTrue(any("id" in f for f in result["findings"]))

    def test_unknown_type_produces_finding(self):
        case = {"id": "LC-003", "type": "buffeting", "limit_load": 200.0}
        result = process_load_case(case)
        self.assertTrue(any("taxonomy" in f for f in result["findings"]))

    def test_custom_safety_factors_applied(self):
        case = {
            "id": "LC-004",
            "type": "dynamic-random",
            "limit_load": 2000.0,
            "partial_safety_factor": 1.1,
            "yield_factor": 1.0,
            "ultimate_factor": 1.5,
        }
        result = process_load_case(case)
        self.assertAlmostEqual(result["dll"], 2000.0 * 1.1)
        self.assertAlmostEqual(result["dyl"], 2000.0 * 1.1 * 1.0)
        self.assertAlmostEqual(result["dul"], 2000.0 * 1.1 * 1.5)

    def test_out_of_range_psf_produces_finding(self):
        case = {
            "id": "LC-005",
            "type": "inertia",
            "limit_load": 1000.0,
            "partial_safety_factor": 0.5,
        }
        result = process_load_case(case)
        self.assertTrue(len(result["findings"]) > 0)
        self.assertIsNone(result["dll"])


class TestProcessDesignLoadsDocument(unittest.TestCase):

    def _valid_document(self):
        return [
            {"id": "LC-A", "type": "static",       "limit_load": 3000.0},
            {"id": "LC-B", "type": "dynamic-sine",  "limit_load": 1500.0},
            {"id": "LC-C", "type": "thermal",       "limit_load": 800.0},
        ]

    def test_empty_document_not_compliant(self):
        result = process_design_loads_document([])
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_valid_document_is_compliant(self):
        result = process_design_loads_document(self._valid_document())
        self.assertTrue(result["compliant"], msg=result["findings"])

    def test_valid_document_result_count(self):
        result = process_design_loads_document(self._valid_document())
        self.assertEqual(len(result["load_case_results"]), 3)

    def test_duplicate_id_produces_finding(self):
        cases = [
            {"id": "LC-X", "type": "pressure",      "limit_load": 500.0},
            {"id": "LC-X", "type": "dynamic-shock", "limit_load": 700.0},
        ]
        result = process_design_loads_document(cases)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Duplicate" in f for f in result["findings"]))

    def test_missing_ll_propagates_to_document_findings(self):
        cases = [
            {"id": "LC-M", "type": "acoustic"},
        ]
        result = process_design_loads_document(cases)
        self.assertFalse(result["compliant"])

    def test_document_findings_aggregated_across_cases(self):
        cases = [
            {"id": "LC-G1", "type": "static",  "limit_load": 1000.0},
            {"id": "LC-G2", "type": "unknown", "limit_load": 500.0},
        ]
        result = process_design_loads_document(cases)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) >= 1)

    def test_all_cases_have_dll_when_valid(self):
        result = process_design_loads_document(self._valid_document())
        for r in result["load_case_results"]:
            self.assertIsNotNone(r["dll"], msg=f"DLL missing for {r['id']}")

    def test_all_cases_dul_greater_than_dyl(self):
        result = process_design_loads_document(self._valid_document())
        for r in result["load_case_results"]:
            self.assertGreater(r["dul"], r["dyl"],
                               msg=f"Expected DUL > DYL for {r['id']}")


if __name__ == "__main__":
    unittest.main()
