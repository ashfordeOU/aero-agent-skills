"""
test_life_extension_reactivation.py

Stdlib unittest suite for life_extension_reactivation_logic.py.
Deterministic, offline.  Run: python3 test_life_extension_reactivation.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from life_extension_reactivation_logic import (
    assess_life_extension,
    check_reactivation_readiness,
    evaluate_re_acceptance,
    summarize_assessment,
    STATUS_APPROVED,
    STATUS_REJECTED,
    STATUS_CONDITIONAL,
    STATUS_REQUIRES_REQUALIFICATION,
    MIN_EXTENSION_SAFETY_FACTOR,
    MAX_DORMANCY_MONTHS,
)


class TestLifeExtensionApproval(unittest.TestCase):

    def test_approved_when_ample_remaining_life(self):
        result = assess_life_extension(
            certified_life=10000,
            consumed_life=5000,
            extension_request=2000,
            applied_safety_factor=1.5,
        )
        self.assertEqual(result.status, STATUS_APPROVED)

    def test_rejected_when_insufficient_remaining_life(self):
        result = assess_life_extension(
            certified_life=10000,
            consumed_life=9800,
            extension_request=500,
            applied_safety_factor=1.0,
        )
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_safety_margin_exact_value(self):
        # remaining=1000, extension=500, factor=2.0 → margin = (1000/500)*2.0 = 4.0
        result = assess_life_extension(
            certified_life=1000,
            consumed_life=0,
            extension_request=500,
            applied_safety_factor=2.0,
        )
        self.assertAlmostEqual(result.safety_margin, 4.0)
        self.assertEqual(result.status, STATUS_APPROVED)

    def test_load_increase_reduces_safety_margin(self):
        base = assess_life_extension(10000, 8000, 1000, 1.5)
        with_load = assess_life_extension(10000, 8000, 1000, 1.5, load_increase_fraction=0.5)
        self.assertLess(with_load.safety_margin, base.safety_margin)

    def test_load_increase_can_cause_rejection(self):
        # Without load increase: margin = (200/180)*1.0 ≈ 1.11 — already below 1.25
        # With load this gets even worse; ensure rejection in both cases here
        result = assess_life_extension(
            certified_life=1000,
            consumed_life=800,
            extension_request=180,
            applied_safety_factor=1.0,
            load_increase_fraction=0.5,
        )
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_remaining_life_reported_correctly(self):
        result = assess_life_extension(
            certified_life=5000,
            consumed_life=2000,
            extension_request=1000,
            applied_safety_factor=2.0,
        )
        self.assertAlmostEqual(result.remaining_life, 3000.0)

    def test_invalid_certified_life_raises(self):
        with self.assertRaises(ValueError):
            assess_life_extension(0, 0, 100, 1.0)

    def test_consumed_equals_certified_raises(self):
        with self.assertRaises(ValueError):
            assess_life_extension(1000, 1000, 100, 1.0)

    def test_negative_extension_raises(self):
        with self.assertRaises(ValueError):
            assess_life_extension(1000, 500, -50, 1.0)

    def test_safety_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            assess_life_extension(1000, 500, 100, 0.9)

    def test_negative_load_increase_raises(self):
        with self.assertRaises(ValueError):
            assess_life_extension(1000, 500, 100, 1.0, load_increase_fraction=-0.1)


class TestReactivationReadiness(unittest.TestCase):

    def test_approved_when_all_checks_pass(self):
        result = check_reactivation_readiness(
            dormancy_months=12,
            seal_inspection_passed=True,
            structural_inspection_passed=True,
            functional_test_passed=True,
        )
        self.assertEqual(result.status, STATUS_APPROVED)
        self.assertEqual(len(result.items_failed), 0)

    def test_requires_requalification_when_dormancy_exceeded(self):
        result = check_reactivation_readiness(
            dormancy_months=MAX_DORMANCY_MONTHS + 1,
            seal_inspection_passed=True,
            structural_inspection_passed=True,
            functional_test_passed=True,
        )
        self.assertEqual(result.status, STATUS_REQUIRES_REQUALIFICATION)

    def test_rejected_when_seal_inspection_fails(self):
        result = check_reactivation_readiness(
            dormancy_months=6,
            seal_inspection_passed=False,
            structural_inspection_passed=True,
            functional_test_passed=True,
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertTrue(any("Seal" in item for item in result.items_failed))

    def test_rejected_when_structural_inspection_fails(self):
        result = check_reactivation_readiness(
            dormancy_months=6,
            seal_inspection_passed=True,
            structural_inspection_passed=False,
            functional_test_passed=True,
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertTrue(any("Structural" in item for item in result.items_failed))

    def test_rejected_when_functional_test_fails(self):
        result = check_reactivation_readiness(
            dormancy_months=6,
            seal_inspection_passed=True,
            structural_inspection_passed=True,
            functional_test_passed=False,
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertTrue(any("Functional" in item for item in result.items_failed))

    def test_multiple_failed_checks_all_reported(self):
        result = check_reactivation_readiness(
            dormancy_months=6,
            seal_inspection_passed=False,
            structural_inspection_passed=False,
            functional_test_passed=False,
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertEqual(len(result.items_failed), 3)

    def test_negative_dormancy_raises(self):
        with self.assertRaises(ValueError):
            check_reactivation_readiness(-1, True, True, True)

    def test_custom_dormancy_limit_respected(self):
        result = check_reactivation_readiness(
            dormancy_months=25,
            seal_inspection_passed=True,
            structural_inspection_passed=True,
            functional_test_passed=True,
            max_dormancy_months=24,
        )
        self.assertEqual(result.status, STATUS_REQUIRES_REQUALIFICATION)


class TestReAcceptance(unittest.TestCase):

    def test_approved_when_all_criteria_met(self):
        result = evaluate_re_acceptance(
            design_changed=False,
            material_traceability_confirmed=True,
            original_certification_valid=True,
            updated_test_data_available=True,
        )
        self.assertEqual(result.status, STATUS_APPROVED)

    def test_rejected_when_no_material_traceability(self):
        result = evaluate_re_acceptance(
            design_changed=False,
            material_traceability_confirmed=False,
            original_certification_valid=True,
            updated_test_data_available=True,
        )
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_conditional_when_design_changed_with_test_data(self):
        result = evaluate_re_acceptance(
            design_changed=True,
            material_traceability_confirmed=True,
            original_certification_valid=True,
            updated_test_data_available=True,
        )
        self.assertEqual(result.status, STATUS_CONDITIONAL)
        self.assertTrue(len(result.required_actions) > 0)

    def test_rejected_when_design_changed_without_test_data(self):
        result = evaluate_re_acceptance(
            design_changed=True,
            material_traceability_confirmed=True,
            original_certification_valid=True,
            updated_test_data_available=False,
        )
        self.assertEqual(result.status, STATUS_REJECTED)

    def test_conditional_when_certification_not_valid(self):
        result = evaluate_re_acceptance(
            design_changed=False,
            material_traceability_confirmed=True,
            original_certification_valid=False,
            updated_test_data_available=True,
        )
        self.assertEqual(result.status, STATUS_CONDITIONAL)

    def test_conditional_when_no_test_data_but_cert_valid(self):
        result = evaluate_re_acceptance(
            design_changed=False,
            material_traceability_confirmed=True,
            original_certification_valid=True,
            updated_test_data_available=False,
        )
        self.assertEqual(result.status, STATUS_CONDITIONAL)

    def test_traceability_rejection_overrides_design_change(self):
        # Even with a design change, missing traceability is the first rejection
        result = evaluate_re_acceptance(
            design_changed=True,
            material_traceability_confirmed=False,
            original_certification_valid=False,
            updated_test_data_available=False,
        )
        self.assertEqual(result.status, STATUS_REJECTED)
        self.assertTrue(
            any("traceability" in a.lower() for a in result.required_actions)
        )


class TestSummaryAssessment(unittest.TestCase):

    def _approved_trio(self):
        le = assess_life_extension(10000, 5000, 2000, 1.5)
        ra = check_reactivation_readiness(12, True, True, True)
        re = evaluate_re_acceptance(False, True, True, True)
        return le, ra, re

    def test_all_approved_gives_overall_approved(self):
        le, ra, re = self._approved_trio()
        summary = summarize_assessment(le, ra, re)
        self.assertEqual(summary["overall_status"], STATUS_APPROVED)

    def test_rejected_life_extension_gives_overall_rejected(self):
        le = assess_life_extension(1000, 999, 500, 1.0)
        ra = check_reactivation_readiness(12, True, True, True)
        re = evaluate_re_acceptance(False, True, True, True)
        summary = summarize_assessment(le, ra, re)
        self.assertEqual(summary["overall_status"], STATUS_REJECTED)

    def test_conditional_re_acceptance_gives_overall_conditional(self):
        le = assess_life_extension(10000, 5000, 2000, 1.5)
        ra = check_reactivation_readiness(12, True, True, True)
        re = evaluate_re_acceptance(True, True, True, True)  # design changed → conditional
        summary = summarize_assessment(le, ra, re)
        self.assertEqual(summary["overall_status"], STATUS_CONDITIONAL)

    def test_requalification_required_gives_overall_rejected(self):
        le = assess_life_extension(10000, 5000, 2000, 1.5)
        ra = check_reactivation_readiness(MAX_DORMANCY_MONTHS + 5, True, True, True)
        re = evaluate_re_acceptance(False, True, True, True)
        summary = summarize_assessment(le, ra, re)
        self.assertEqual(summary["overall_status"], STATUS_REJECTED)

    def test_summary_findings_keys_present(self):
        le, ra, re = self._approved_trio()
        summary = summarize_assessment(le, ra, re)
        self.assertIn("life_extension", summary["findings"])
        self.assertIn("reactivation", summary["findings"])
        self.assertIn("re_acceptance", summary["findings"])

    def test_summary_contains_overall_status_key(self):
        le, ra, re = self._approved_trio()
        summary = summarize_assessment(le, ra, re)
        self.assertIn("overall_status", summary)


if __name__ == "__main__":
    unittest.main()
