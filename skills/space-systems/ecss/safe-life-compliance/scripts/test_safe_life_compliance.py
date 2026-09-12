"""
Offline stdlib unittest for safe_life_compliance_logic.py.
Run: python3 test_safe_life_compliance.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from safe_life_compliance_logic import (
    DEFAULT_SCATTER_FACTOR,
    RESIDUAL_STRENGTH_RATIO_MINIMUM,
    VALID_CATEGORIES,
    VALID_EVIDENCE_TYPES,
    ItemResult,
    SafeLifeItem,
    assess_item,
    assess_items,
    categorize_item,
    check_crack_growth_life,
    check_evidence,
    check_residual_strength,
)


class TestItemCategorization(unittest.TestCase):
    def test_safe_life_is_valid(self):
        item = SafeLifeItem(item_id="CAT-01", category="safe-life")
        valid, notes = categorize_item(item)
        self.assertTrue(valid)
        self.assertEqual(notes, [])

    def test_fail_safe_is_valid(self):
        item = SafeLifeItem(item_id="CAT-02", category="fail-safe")
        valid, notes = categorize_item(item)
        self.assertTrue(valid)

    def test_unknown_category_is_invalid(self):
        item = SafeLifeItem(item_id="CAT-03", category="damage-tolerant")
        valid, notes = categorize_item(item)
        self.assertFalse(valid)
        self.assertTrue(any("Unknown category" in n for n in notes))

    def test_empty_category_is_invalid(self):
        item = SafeLifeItem(item_id="CAT-04", category="")
        valid, notes = categorize_item(item)
        self.assertFalse(valid)


class TestEvidenceCheck(unittest.TestCase):
    def test_analysis_evidence_passes(self):
        item = SafeLifeItem(item_id="EV-01", category="safe-life", evidence=["analysis"])
        status, notes = check_evidence(item)
        self.assertEqual(status, "PASS")
        self.assertTrue(any("analysis" in n for n in notes))

    def test_test_evidence_passes(self):
        item = SafeLifeItem(item_id="EV-02", category="safe-life", evidence=["test"])
        status, _ = check_evidence(item)
        self.assertEqual(status, "PASS")

    def test_both_evidence_types_passes(self):
        item = SafeLifeItem(item_id="EV-03", category="safe-life", evidence=["analysis", "test"])
        status, _ = check_evidence(item)
        self.assertEqual(status, "PASS")

    def test_no_evidence_fails(self):
        item = SafeLifeItem(item_id="EV-04", category="safe-life", evidence=[])
        status, notes = check_evidence(item)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("no valid evidence" in n for n in notes))

    def test_unrecognized_evidence_type_fails(self):
        item = SafeLifeItem(item_id="EV-05", category="safe-life", evidence=["spreadsheet"])
        status, _ = check_evidence(item)
        self.assertEqual(status, "FAIL")

    def test_evidence_not_applicable_for_fail_safe(self):
        item = SafeLifeItem(item_id="EV-06", category="fail-safe", evidence=[])
        status, _ = check_evidence(item)
        self.assertEqual(status, "N/A")


class TestCrackGrowthLifeCheck(unittest.TestCase):
    def test_passes_when_life_exceeds_required(self):
        item = SafeLifeItem(
            item_id="CG-01", category="safe-life",
            crack_growth_life=50000.0, design_life=10000.0, scatter_factor=4.0,
        )
        status, notes = check_crack_growth_life(item)
        self.assertEqual(status, "PASS")
        self.assertTrue(any("margin" in n for n in notes))

    def test_fails_when_life_below_required(self):
        item = SafeLifeItem(
            item_id="CG-02", category="safe-life",
            crack_growth_life=30000.0, design_life=10000.0, scatter_factor=4.0,
        )
        status, notes = check_crack_growth_life(item)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("shortfall" in n for n in notes))

    def test_exact_boundary_passes(self):
        # crack_growth_life == design_life * scatter_factor should PASS
        item = SafeLifeItem(
            item_id="CG-03", category="safe-life",
            crack_growth_life=40000.0, design_life=10000.0, scatter_factor=4.0,
        )
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "PASS")

    def test_missing_data_when_no_crack_growth_life(self):
        item = SafeLifeItem(
            item_id="CG-04", category="safe-life",
            crack_growth_life=None, design_life=10000.0,
        )
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "MISSING_DATA")

    def test_missing_data_when_no_design_life(self):
        item = SafeLifeItem(
            item_id="CG-05", category="safe-life",
            crack_growth_life=50000.0, design_life=None,
        )
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "MISSING_DATA")

    def test_not_applicable_for_fail_safe(self):
        item = SafeLifeItem(
            item_id="CG-06", category="fail-safe",
            crack_growth_life=50000.0, design_life=10000.0,
        )
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "N/A")

    def test_default_scatter_factor_is_four(self):
        self.assertEqual(DEFAULT_SCATTER_FACTOR, 4.0)
        item = SafeLifeItem(
            item_id="CG-07", category="safe-life",
            crack_growth_life=39999.0, design_life=10000.0,
            # scatter_factor defaults to 4.0
        )
        status, _ = check_crack_growth_life(item)
        # 39999 < 40000 required → FAIL
        self.assertEqual(status, "FAIL")

    def test_project_specific_scatter_factor_used(self):
        item = SafeLifeItem(
            item_id="CG-08", category="safe-life",
            crack_growth_life=30000.0, design_life=10000.0, scatter_factor=3.0,
        )
        # 30000 >= 10000 * 3.0 = 30000 → PASS
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "PASS")

    def test_zero_crack_growth_life_fails(self):
        item = SafeLifeItem(
            item_id="CG-09", category="safe-life",
            crack_growth_life=0.0, design_life=10000.0,
        )
        status, _ = check_crack_growth_life(item)
        self.assertEqual(status, "FAIL")


class TestResidualStrengthCheck(unittest.TestCase):
    def test_passes_when_strength_exceeds_limit(self):
        item = SafeLifeItem(
            item_id="RS-01", category="safe-life",
            residual_strength=120.0, limit_load=100.0,
        )
        status, notes = check_residual_strength(item)
        self.assertEqual(status, "PASS")
        self.assertTrue(any("margin" in n for n in notes))

    def test_fails_when_strength_below_limit(self):
        item = SafeLifeItem(
            item_id="RS-02", category="safe-life",
            residual_strength=80.0, limit_load=100.0,
        )
        status, notes = check_residual_strength(item)
        self.assertEqual(status, "FAIL")
        self.assertTrue(any("deficit" in n for n in notes))

    def test_exact_boundary_passes(self):
        # ratio == 1.0 is the minimum acceptable
        item = SafeLifeItem(
            item_id="RS-03", category="safe-life",
            residual_strength=100.0, limit_load=100.0,
        )
        status, _ = check_residual_strength(item)
        self.assertEqual(status, "PASS")

    def test_missing_data_when_no_residual_strength(self):
        item = SafeLifeItem(
            item_id="RS-04", category="safe-life",
            residual_strength=None, limit_load=100.0,
        )
        status, _ = check_residual_strength(item)
        self.assertEqual(status, "MISSING_DATA")

    def test_missing_data_when_no_limit_load(self):
        item = SafeLifeItem(
            item_id="RS-05", category="safe-life",
            residual_strength=120.0, limit_load=None,
        )
        status, _ = check_residual_strength(item)
        self.assertEqual(status, "MISSING_DATA")

    def test_not_applicable_for_fail_safe(self):
        item = SafeLifeItem(
            item_id="RS-06", category="fail-safe",
            residual_strength=80.0, limit_load=100.0,
        )
        status, _ = check_residual_strength(item)
        self.assertEqual(status, "N/A")

    def test_residual_strength_ratio_minimum_is_one(self):
        self.assertEqual(RESIDUAL_STRENGTH_RATIO_MINIMUM, 1.0)


class TestAssessItem(unittest.TestCase):
    def test_fully_compliant_safe_life_item(self):
        item = SafeLifeItem(
            item_id="AI-01", category="safe-life",
            crack_growth_life=50000.0, design_life=10000.0, scatter_factor=4.0,
            residual_strength=120.0, limit_load=100.0,
            evidence=["analysis"],
        )
        result = assess_item(item)
        self.assertTrue(result.compliant)
        self.assertEqual(result.crack_growth_check, "PASS")
        self.assertEqual(result.residual_strength_check, "PASS")
        self.assertEqual(result.evidence_check, "PASS")

    def test_non_compliant_crack_growth_failure(self):
        item = SafeLifeItem(
            item_id="AI-02", category="safe-life",
            crack_growth_life=10000.0, design_life=10000.0, scatter_factor=4.0,
            residual_strength=120.0, limit_load=100.0,
            evidence=["test"],
        )
        result = assess_item(item)
        self.assertFalse(result.compliant)
        self.assertEqual(result.crack_growth_check, "FAIL")

    def test_non_compliant_residual_strength_failure(self):
        item = SafeLifeItem(
            item_id="AI-03", category="safe-life",
            crack_growth_life=50000.0, design_life=10000.0, scatter_factor=4.0,
            residual_strength=90.0, limit_load=100.0,
            evidence=["analysis"],
        )
        result = assess_item(item)
        self.assertFalse(result.compliant)
        self.assertEqual(result.residual_strength_check, "FAIL")

    def test_non_compliant_missing_evidence(self):
        item = SafeLifeItem(
            item_id="AI-04", category="safe-life",
            crack_growth_life=50000.0, design_life=10000.0, scatter_factor=4.0,
            residual_strength=120.0, limit_load=100.0,
            evidence=[],
        )
        result = assess_item(item)
        self.assertFalse(result.compliant)
        self.assertEqual(result.evidence_check, "FAIL")

    def test_invalid_category_yields_non_compliant(self):
        item = SafeLifeItem(item_id="AI-05", category="bogus")
        result = assess_item(item)
        self.assertFalse(result.category_valid)
        self.assertFalse(result.compliant)

    def test_fail_safe_item_is_compliant(self):
        item = SafeLifeItem(item_id="AI-06", category="fail-safe")
        result = assess_item(item)
        self.assertTrue(result.compliant)
        self.assertEqual(result.crack_growth_check, "N/A")
        self.assertEqual(result.residual_strength_check, "N/A")
        self.assertEqual(result.evidence_check, "N/A")

    def test_missing_data_makes_item_non_compliant(self):
        item = SafeLifeItem(
            item_id="AI-07", category="safe-life",
            crack_growth_life=None, design_life=10000.0,
            residual_strength=120.0, limit_load=100.0,
            evidence=["analysis"],
        )
        result = assess_item(item)
        self.assertFalse(result.compliant)
        self.assertEqual(result.crack_growth_check, "MISSING_DATA")


class TestAssessItems(unittest.TestCase):
    def _make_passing_item(self, item_id: str) -> SafeLifeItem:
        return SafeLifeItem(
            item_id=item_id, category="safe-life",
            crack_growth_life=50000.0, design_life=10000.0, scatter_factor=4.0,
            residual_strength=120.0, limit_load=100.0, evidence=["analysis"],
        )

    def test_all_compliant_summary(self):
        items = [
            self._make_passing_item("SUM-01"),
            SafeLifeItem(item_id="SUM-02", category="fail-safe"),
        ]
        summary = assess_items(items)
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["compliant"], 2)
        self.assertEqual(summary["non_compliant"], 0)
        self.assertEqual(summary["findings"], [])

    def test_mixed_compliance_reports_findings(self):
        items = [
            self._make_passing_item("MIX-01"),
            SafeLifeItem(
                item_id="MIX-02", category="safe-life",
                crack_growth_life=10000.0, design_life=10000.0, scatter_factor=4.0,
                residual_strength=120.0, limit_load=100.0, evidence=["test"],
            ),
        ]
        summary = assess_items(items)
        self.assertFalse(summary["all_compliant"])
        self.assertIn("MIX-02", summary["findings"])
        self.assertEqual(summary["non_compliant"], 1)
        self.assertEqual(summary["compliant"], 1)

    def test_empty_list_is_all_compliant(self):
        summary = assess_items([])
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 0)

    def test_results_list_length_matches_input(self):
        items = [self._make_passing_item(f"LEN-{i:02d}") for i in range(5)]
        summary = assess_items(items)
        self.assertEqual(len(summary["results"]), 5)


if __name__ == "__main__":
    unittest.main()
