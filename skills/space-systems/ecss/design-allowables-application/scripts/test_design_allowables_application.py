"""
Gate 3 contract tests for design_allowables_application_logic.

Run: python3 test_design_allowables_application.py
Expected output: OK (all tests pass, offline, deterministic, stdlib only).
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from design_allowables_application_logic import (
    AllowablesError,
    select_basis,
    source_for_material,
    compute_margin_of_safety,
    is_margin_acceptable,
    check_basis_match,
    assess_member,
    batch_assess,
)


class TestSelectBasis(unittest.TestCase):
    def test_single_load_path_requires_a_basis(self):
        self.assertEqual(select_basis("single"), "A")

    def test_multiple_load_path_permits_b_basis(self):
        self.assertEqual(select_basis("multiple"), "B")

    def test_unknown_load_path_raises_error(self):
        with self.assertRaises(AllowablesError):
            select_basis("unknown")

    def test_empty_string_raises_error(self):
        with self.assertRaises(AllowablesError):
            select_basis("")


class TestSourceForMaterial(unittest.TestCase):
    def test_metal_source_is_mmpds(self):
        self.assertEqual(source_for_material("metal"), "MMPDS")

    def test_composite_source_is_cmh17(self):
        self.assertEqual(source_for_material("composite"), "CMH-17")

    def test_non_metal_source_is_supplier_data_sheet(self):
        self.assertEqual(source_for_material("non-metal"), "supplier-data-sheet")

    def test_adhesive_source_is_supplier_data_sheet(self):
        self.assertEqual(source_for_material("adhesive"), "supplier-data-sheet")

    def test_unknown_material_raises_error(self):
        with self.assertRaises(AllowablesError):
            source_for_material("titanium-alloy")


class TestComputeMarginOfSafety(unittest.TestCase):
    def test_positive_margin_when_allowable_exceeds_stress(self):
        mos = compute_margin_of_safety(100.0, 80.0)
        self.assertAlmostEqual(mos, 0.25)

    def test_zero_margin_at_equality(self):
        mos = compute_margin_of_safety(100.0, 100.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_negative_margin_when_stress_exceeds_allowable(self):
        mos = compute_margin_of_safety(80.0, 100.0)
        self.assertAlmostEqual(mos, -0.2)

    def test_zero_applied_stress_raises_error(self):
        with self.assertRaises(AllowablesError):
            compute_margin_of_safety(100.0, 0.0)

    def test_negative_applied_stress_raises_error(self):
        with self.assertRaises(AllowablesError):
            compute_margin_of_safety(100.0, -10.0)

    def test_zero_allowable_raises_error(self):
        with self.assertRaises(AllowablesError):
            compute_margin_of_safety(0.0, 50.0)

    def test_negative_allowable_raises_error(self):
        with self.assertRaises(AllowablesError):
            compute_margin_of_safety(-50.0, 50.0)


class TestIsMarginAcceptable(unittest.TestCase):
    def test_zero_margin_is_acceptable(self):
        self.assertTrue(is_margin_acceptable(0.0))

    def test_positive_margin_is_acceptable(self):
        self.assertTrue(is_margin_acceptable(0.5))

    def test_negative_margin_is_not_acceptable(self):
        self.assertFalse(is_margin_acceptable(-0.01))


class TestCheckBasisMatch(unittest.TestCase):
    def test_a_versus_a_matches(self):
        self.assertTrue(check_basis_match("A", "A"))

    def test_b_versus_b_matches(self):
        self.assertTrue(check_basis_match("B", "B"))

    def test_a_required_b_retrieved_does_not_match(self):
        self.assertFalse(check_basis_match("A", "B"))

    def test_b_required_a_retrieved_does_not_match(self):
        self.assertFalse(check_basis_match("B", "A"))

    def test_invalid_required_basis_raises_error(self):
        with self.assertRaises(AllowablesError):
            check_basis_match("C", "A")

    def test_invalid_retrieved_basis_raises_error(self):
        with self.assertRaises(AllowablesError):
            check_basis_match("A", "X")


class TestAssessMember(unittest.TestCase):
    def test_single_path_metal_positive_margin_acceptable(self):
        result = assess_member(
            load_path_type="single",
            material_class="metal",
            allowable_value=500.0,
            applied_stress=400.0,
            retrieved_basis="A",
        )
        self.assertEqual(result["required_basis"], "A")
        self.assertEqual(result["source"], "MMPDS")
        self.assertAlmostEqual(result["margin_of_safety"], 0.25)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["basis_match"])
        self.assertEqual(result["findings"], [])

    def test_multiple_path_composite_positive_margin_acceptable(self):
        result = assess_member(
            load_path_type="multiple",
            material_class="composite",
            allowable_value=300.0,
            applied_stress=200.0,
            retrieved_basis="B",
        )
        self.assertEqual(result["required_basis"], "B")
        self.assertEqual(result["source"], "CMH-17")
        self.assertTrue(result["acceptable"])

    def test_negative_margin_makes_result_not_acceptable(self):
        result = assess_member(
            load_path_type="single",
            material_class="metal",
            allowable_value=300.0,
            applied_stress=400.0,
            retrieved_basis="A",
        )
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("MoS", result["findings"][0])

    def test_basis_mismatch_single_path_b_retrieved_not_acceptable(self):
        result = assess_member(
            load_path_type="single",
            material_class="metal",
            allowable_value=500.0,
            applied_stress=400.0,
            retrieved_basis="B",
        )
        self.assertFalse(result["acceptable"])
        self.assertFalse(result["basis_match"])
        self.assertTrue(any("Basis mismatch" in f for f in result["findings"]))

    def test_no_retrieved_basis_skips_basis_check(self):
        result = assess_member(
            load_path_type="multiple",
            material_class="adhesive",
            allowable_value=100.0,
            applied_stress=50.0,
        )
        self.assertIsNone(result["basis_match"])
        self.assertTrue(result["acceptable"])

    def test_both_findings_reported_when_margin_negative_and_basis_wrong(self):
        result = assess_member(
            load_path_type="single",
            material_class="metal",
            allowable_value=200.0,
            applied_stress=400.0,
            retrieved_basis="B",
        )
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 2)


class TestBatchAssess(unittest.TestCase):
    def test_batch_with_all_acceptable_members(self):
        members = [
            {
                "load_path_type": "single",
                "material_class": "metal",
                "allowable_value": 500.0,
                "applied_stress": 400.0,
                "retrieved_basis": "A",
            },
            {
                "load_path_type": "multiple",
                "material_class": "composite",
                "allowable_value": 300.0,
                "applied_stress": 150.0,
                "retrieved_basis": "B",
            },
        ]
        results = batch_assess(members)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["acceptable"] for r in results))
        self.assertTrue(all(r["error"] is None for r in results))

    def test_batch_captures_error_for_invalid_member(self):
        members = [
            {
                "load_path_type": "bad-type",
                "material_class": "metal",
                "allowable_value": 500.0,
                "applied_stress": 400.0,
            },
        ]
        results = batch_assess(members)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["acceptable"])
        self.assertIsNotNone(results[0]["error"])

    def test_batch_mixed_good_and_bad_members(self):
        members = [
            {
                "load_path_type": "single",
                "material_class": "metal",
                "allowable_value": 500.0,
                "applied_stress": 400.0,
                "retrieved_basis": "A",
            },
            {
                "load_path_type": "single",
                "material_class": "metal",
                "allowable_value": 200.0,
                "applied_stress": 400.0,
                "retrieved_basis": "A",
            },
        ]
        results = batch_assess(members)
        self.assertTrue(results[0]["acceptable"])
        self.assertFalse(results[1]["acceptable"])

    def test_empty_batch_returns_empty_list(self):
        self.assertEqual(batch_assess([]), [])

    def test_batch_non_metal_adhesive_member(self):
        members = [
            {
                "load_path_type": "multiple",
                "material_class": "adhesive",
                "allowable_value": 50.0,
                "applied_stress": 30.0,
                "retrieved_basis": "B",
            },
        ]
        results = batch_assess(members)
        self.assertEqual(results[0]["source"], "supplier-data-sheet")
        self.assertTrue(results[0]["acceptable"])


if __name__ == "__main__":
    unittest.main()
