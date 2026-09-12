#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C Annex F fracture control plan
screening logic.

Exercises scripts/drd_fracture_control_plan_logic.py (stdlib unittest,
offline). Contract: a structural item with a catastrophic failure
consequence is categorized as fracture-critical and one with a
non-catastrophic consequence as fracture-non-critical, and an
unrecognized consequence raises; the critical flaw size is computed as
(K_Ic / (Y * sigma * sqrt(pi)))^2 and non-positive inputs raise; a
proof-test factor below 1.25 is flagged and one at or above is not;
a safe-life factor below 4.0 is flagged and one at or above is not;
NDI is flagged when its detection threshold exceeds the assumed flaw
and passes when it does not; the critical-vs-assumed check flags an
item when a_c <= assumed and passes when a_c > assumed; the aggregated
review collects all violation categories for a fracture-critical item
and skips fracture checks for a fracture-non-critical item; and
is_fcp_compliant returns True only when violations is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import drd_fracture_control_plan_logic as fcp  # noqa: E402


def _compliant_item(**overrides):
    """Return a fully compliant fracture-critical item dict, with any
    fields replaced by overrides."""
    base = {
        "item_id": "bracket-001",
        "failure_consequence": "catastrophic",
        "K_Ic_MPa_sqrt_m": 30.0,
        "geometry_factor_Y": 1.0,
        "applied_stress_MPa": 100.0,
        "assumed_flaw_size_m": 0.001,
        "ndi_detection_threshold_m": 0.0005,
        "proof_factor": 1.33,
        "safe_life_factor": 4.0,
    }
    return {**base, **overrides}


class CategorizeItemTest(unittest.TestCase):
    def test_catastrophic_is_fracture_critical(self):
        self.assertEqual(fcp.categorize_item("catastrophic"), "fracture_critical")

    def test_non_catastrophic_is_fracture_non_critical(self):
        self.assertEqual(
            fcp.categorize_item("non_catastrophic"), "fracture_non_critical"
        )

    def test_unknown_consequence_raises(self):
        with self.assertRaises(ValueError):
            fcp.categorize_item("undefined_consequence")


class CriticalFlawSizeTest(unittest.TestCase):
    def test_known_values(self):
        # a_c = (30 / (1.0 * 100 * sqrt(pi)))^2
        expected = (30.0 / (1.0 * 100.0 * math.sqrt(math.pi))) ** 2
        result = fcp.critical_flaw_size_m(30.0, 1.0, 100.0)
        self.assertAlmostEqual(result, expected, places=10)

    def test_higher_toughness_gives_larger_flaw(self):
        a_low = fcp.critical_flaw_size_m(20.0, 1.0, 100.0)
        a_high = fcp.critical_flaw_size_m(40.0, 1.0, 100.0)
        self.assertGreater(a_high, a_low)

    def test_higher_stress_gives_smaller_flaw(self):
        a_low_stress = fcp.critical_flaw_size_m(30.0, 1.0, 50.0)
        a_high_stress = fcp.critical_flaw_size_m(30.0, 1.0, 200.0)
        self.assertGreater(a_low_stress, a_high_stress)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            fcp.critical_flaw_size_m(30.0, 1.0, 0.0)

    def test_negative_toughness_raises(self):
        with self.assertRaises(ValueError):
            fcp.critical_flaw_size_m(-1.0, 1.0, 100.0)

    def test_zero_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            fcp.critical_flaw_size_m(30.0, 0.0, 100.0)


class ProofTestFactorTest(unittest.TestCase):
    def test_factor_at_minimum_no_violation(self):
        self.assertEqual(fcp.check_proof_test_factor(1.25), [])

    def test_factor_above_minimum_no_violation(self):
        self.assertEqual(fcp.check_proof_test_factor(1.33), [])

    def test_factor_below_minimum_flagged(self):
        violations = fcp.check_proof_test_factor(1.10)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "proof_test_factor_below_threshold")
        self.assertAlmostEqual(violations[0]["proof_factor"], 1.10)
        self.assertAlmostEqual(violations[0]["min_required"], 1.25)

    def test_custom_minimum_respected(self):
        self.assertEqual(fcp.check_proof_test_factor(1.5, min_required=1.5), [])
        self.assertEqual(len(fcp.check_proof_test_factor(1.4, min_required=1.5)), 1)


class SafeLifeFactorTest(unittest.TestCase):
    def test_factor_at_minimum_no_violation(self):
        self.assertEqual(fcp.check_safe_life_factor(4.0), [])

    def test_factor_above_minimum_no_violation(self):
        self.assertEqual(fcp.check_safe_life_factor(5.0), [])

    def test_factor_below_minimum_flagged(self):
        violations = fcp.check_safe_life_factor(3.5)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "safe_life_factor_below_threshold")
        self.assertAlmostEqual(violations[0]["safe_life_factor"], 3.5)
        self.assertAlmostEqual(violations[0]["min_required"], 4.0)


class NdiDetectabilityTest(unittest.TestCase):
    def test_threshold_below_assumed_flaw_no_violation(self):
        self.assertEqual(fcp.check_ndi_detectability(0.001, 0.0005), [])

    def test_threshold_equal_assumed_flaw_no_violation(self):
        self.assertEqual(fcp.check_ndi_detectability(0.001, 0.001), [])

    def test_threshold_above_assumed_flaw_flagged(self):
        violations = fcp.check_ndi_detectability(0.001, 0.002)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "ndi_cannot_detect_assumed_flaw")
        self.assertAlmostEqual(violations[0]["assumed_flaw_size_m"], 0.001)
        self.assertAlmostEqual(violations[0]["ndi_detection_threshold_m"], 0.002)

    def test_zero_assumed_flaw_raises(self):
        with self.assertRaises(ValueError):
            fcp.check_ndi_detectability(0.0, 0.001)

    def test_zero_ndi_threshold_raises(self):
        with self.assertRaises(ValueError):
            fcp.check_ndi_detectability(0.001, 0.0)


class CriticalVsAssumedTest(unittest.TestCase):
    def test_critical_larger_than_assumed_no_violation(self):
        self.assertEqual(fcp.check_critical_vs_assumed("part-1", 0.005, 0.001), [])

    def test_critical_equal_to_assumed_flagged(self):
        violations = fcp.check_critical_vs_assumed("part-1", 0.001, 0.001)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "critical_flaw_not_larger_than_assumed")

    def test_critical_smaller_than_assumed_flagged(self):
        violations = fcp.check_critical_vs_assumed("part-1", 0.0005, 0.001)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["item"], "part-1")


class FciReviewTest(unittest.TestCase):
    def test_fully_compliant_fci_no_violations(self):
        item = _compliant_item()
        review = fcp.fci_review(item)
        self.assertEqual(review["categorization"], "fracture_critical")
        self.assertEqual(review["violations"], [])
        self.assertTrue(fcp.is_fcp_compliant(review))

    def test_non_critical_item_skips_fracture_checks(self):
        item = _compliant_item(failure_consequence="non_catastrophic")
        review = fcp.fci_review(item)
        self.assertEqual(review["categorization"], "fracture_non_critical")
        self.assertEqual(review["violations"], [])
        self.assertTrue(fcp.is_fcp_compliant(review))

    def test_low_proof_factor_flagged(self):
        item = _compliant_item(proof_factor=1.10)
        review = fcp.fci_review(item)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("proof_test_factor_below_threshold", issues)
        self.assertFalse(fcp.is_fcp_compliant(review))

    def test_low_safe_life_flagged(self):
        item = _compliant_item(safe_life_factor=2.0)
        review = fcp.fci_review(item)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("safe_life_factor_below_threshold", issues)

    def test_ndi_gap_flagged(self):
        item = _compliant_item(ndi_detection_threshold_m=0.005)
        review = fcp.fci_review(item)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("ndi_cannot_detect_assumed_flaw", issues)

    def test_critical_flaw_smaller_than_assumed_flagged(self):
        # Very high stress so a_c < assumed_flaw_size_m (0.001 m)
        item = _compliant_item(applied_stress_MPa=600.0)
        review = fcp.fci_review(item)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("critical_flaw_not_larger_than_assumed", issues)

    def test_multiple_violations_collected(self):
        item = _compliant_item(proof_factor=1.10, safe_life_factor=2.0)
        review = fcp.fci_review(item)
        issues = [v["issue"] for v in review["violations"]]
        self.assertIn("proof_test_factor_below_threshold", issues)
        self.assertIn("safe_life_factor_below_threshold", issues)
        self.assertGreaterEqual(len(review["violations"]), 2)

    def test_unknown_consequence_raises(self):
        item = _compliant_item(failure_consequence="unknown")
        with self.assertRaises(ValueError):
            fcp.fci_review(item)


class FcpComplianceTest(unittest.TestCase):
    def test_empty_violations_is_compliant(self):
        self.assertTrue(fcp.is_fcp_compliant({"categorization": "fracture_critical", "violations": []}))

    def test_nonempty_violations_is_not_compliant(self):
        review = {
            "categorization": "fracture_critical",
            "violations": [{"issue": "proof_test_factor_below_threshold"}],
        }
        self.assertFalse(fcp.is_fcp_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
