"""
Offline, deterministic contract tests for pfci_evaluation_design_principles_logic.
Run: python3 scripts/test_pfci_evaluation_design_principles.py
"""

import sys
import os
import unittest

# Allow running from the leaf root as well as from the scripts directory.
sys.path.insert(0, os.path.dirname(__file__))

import pfci_evaluation_design_principles_logic as logic
from pfci_evaluation_design_principles_logic import (
    PfciItem,
    SAFE_LIFE,
    FAIL_SAFE,
    LOW_RISK_FRACTURE,
    LOW_RISK_STRESS_THRESHOLD_MPA,
    LOW_RISK_THICKNESS_THRESHOLD_MM,
    select_principle,
    evaluate_pfci_set,
)


def _item(
    item_id="PFCI-001",
    redundant=False,
    inspectable=False,
    stress=80.0,
    thickness=5.0,
    kic=None,
):
    return PfciItem(
        item_id=item_id,
        redundant_load_paths=redundant,
        inspectable_in_service=inspectable,
        net_stress_mpa=stress,
        cross_section_thickness_mm=thickness,
        material_fracture_toughness_kic=kic,
    )


class TestLowRiskFractureSelection(unittest.TestCase):
    def test_low_risk_selected_when_both_thresholds_met(self):
        item = _item(stress=30.0, thickness=1.5)
        result = select_principle(item)
        self.assertEqual(result.principle, LOW_RISK_FRACTURE)

    def test_low_risk_not_selected_when_only_stress_below_threshold(self):
        # Stress OK, thickness exceeds threshold → NOT low-risk
        item = _item(stress=30.0, thickness=5.0)
        result = select_principle(item)
        self.assertNotEqual(result.principle, LOW_RISK_FRACTURE)

    def test_low_risk_not_selected_when_only_thickness_below_threshold(self):
        # Thickness OK, stress exceeds threshold → NOT low-risk
        item = _item(stress=80.0, thickness=1.5)
        result = select_principle(item)
        self.assertNotEqual(result.principle, LOW_RISK_FRACTURE)

    def test_stress_exactly_at_threshold_yields_low_risk_when_thickness_ok(self):
        item = _item(stress=LOW_RISK_STRESS_THRESHOLD_MPA, thickness=1.0)
        result = select_principle(item)
        self.assertEqual(result.principle, LOW_RISK_FRACTURE)

    def test_thickness_exactly_at_threshold_yields_low_risk_when_stress_ok(self):
        item = _item(stress=10.0, thickness=LOW_RISK_THICKNESS_THRESHOLD_MM)
        result = select_principle(item)
        self.assertEqual(result.principle, LOW_RISK_FRACTURE)

    def test_low_risk_rationale_references_ecss_clause(self):
        item = _item(stress=10.0, thickness=1.0)
        result = select_principle(item)
        self.assertIn("6.2.1", result.rationale)


class TestFailSafeSelection(unittest.TestCase):
    def test_fail_safe_selected_when_redundant_load_paths(self):
        item = _item(redundant=True, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertEqual(result.principle, FAIL_SAFE)

    def test_fail_safe_selected_when_inspectable_in_service(self):
        item = _item(inspectable=True, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertEqual(result.principle, FAIL_SAFE)

    def test_fail_safe_selected_when_redundant_and_inspectable(self):
        item = _item(redundant=True, inspectable=True, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertEqual(result.principle, FAIL_SAFE)

    def test_fail_safe_rationale_mentions_inspection_plan(self):
        item = _item(redundant=True, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertIn("inspection", result.rationale.lower())


class TestSafeLifeSelection(unittest.TestCase):
    def test_safe_life_selected_for_single_path_non_inspectable_high_stress(self):
        item = _item(redundant=False, inspectable=False, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertEqual(result.principle, SAFE_LIFE)

    def test_safe_life_rationale_mentions_fracture_life_demonstration(self):
        item = _item(redundant=False, inspectable=False, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertIn("demonstration", result.rationale.lower())


class TestFindingGeneration(unittest.TestCase):
    def test_stress_finding_present_when_stress_exceeds_threshold(self):
        item = _item(stress=80.0, thickness=10.0)
        result = select_principle(item)
        stress_findings = [f for f in result.findings if "stress" in f.lower()]
        self.assertTrue(len(stress_findings) >= 1)

    def test_thickness_finding_present_when_thickness_exceeds_threshold(self):
        item = _item(stress=80.0, thickness=10.0)
        result = select_principle(item)
        thickness_findings = [f for f in result.findings if "thickness" in f.lower()]
        self.assertTrue(len(thickness_findings) >= 1)

    def test_both_findings_present_when_both_thresholds_exceeded(self):
        item = _item(redundant=False, inspectable=False, stress=100.0, thickness=10.0)
        result = select_principle(item)
        self.assertEqual(len(result.findings), 2)

    def test_no_findings_when_low_risk_criteria_met(self):
        item = _item(stress=10.0, thickness=1.0)
        result = select_principle(item)
        self.assertEqual(result.findings, [])


class TestEvaluatePfciSet(unittest.TestCase):
    def test_evaluate_set_counts_all_three_principles(self):
        items = [
            _item("A", stress=10.0, thickness=1.0),                       # LOW_RISK
            _item("B", redundant=True, stress=100.0, thickness=10.0),     # FAIL_SAFE
            _item("C", redundant=False, inspectable=False, stress=100.0, thickness=10.0),  # SAFE_LIFE
        ]
        result = evaluate_pfci_set(items)
        self.assertEqual(result["counts"][LOW_RISK_FRACTURE], 1)
        self.assertEqual(result["counts"][FAIL_SAFE], 1)
        self.assertEqual(result["counts"][SAFE_LIFE], 1)

    def test_evaluate_set_selections_length_matches_input(self):
        items = [_item(str(i), stress=10.0, thickness=1.0) for i in range(5)]
        result = evaluate_pfci_set(items)
        self.assertEqual(len(result["selections"]), 5)

    def test_evaluate_set_items_with_findings_counted_correctly(self):
        items = [
            _item("A", stress=10.0, thickness=1.0),       # no findings
            _item("B", redundant=True, stress=100.0, thickness=10.0),  # 2 findings
        ]
        result = evaluate_pfci_set(items)
        self.assertEqual(result["items_with_findings"], 1)

    def test_evaluate_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_pfci_set([])


class TestInputValidation(unittest.TestCase):
    def test_empty_item_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(item_id=""))

    def test_whitespace_only_item_id_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(item_id="   "))

    def test_negative_stress_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(stress=-1.0))

    def test_zero_thickness_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(thickness=0.0))

    def test_negative_thickness_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(thickness=-5.0))

    def test_negative_kic_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(kic=-10.0))

    def test_zero_kic_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_principle(_item(kic=0.0))

    def test_valid_kic_does_not_raise(self):
        # kic is optional meta-data; positive value must not raise
        item = _item(stress=10.0, thickness=1.0, kic=25.5)
        result = select_principle(item)
        self.assertEqual(result.principle, LOW_RISK_FRACTURE)


if __name__ == "__main__":
    unittest.main()
