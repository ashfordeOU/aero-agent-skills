#!/usr/bin/env python3
"""Gate 3 contract test: AS9100D operational risk management math.

Exercises scripts/risk_management_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - FMEA risk priority number
RPN = S * L * D, RPN classification bands, post-mitigation RPN with
reduction credits, risk reduction fraction, occurrence probability
from production history, residual risk acceptance, 5x5 risk-matrix
classification, and deterministic mitigation-priority ranking.

All expected values are hand-computed (see each docstring) and were
checked at authoring time against the logic module.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import risk_management_logic as rml  # noqa: E402


class RiskPriorityNumberTest(unittest.TestCase):
    def test_8_5_3(self):
        # 8 * 5 * 3 = 120.
        self.assertEqual(rml.risk_priority_number(8, 5, 3), 120)

    def test_6_2_2(self):
        # 6 * 2 * 2 = 24.
        self.assertEqual(rml.risk_priority_number(6, 2, 2), 24)

    def test_minimum_rpn(self):
        # 1 * 1 * 1 = 1.
        self.assertEqual(rml.risk_priority_number(1, 1, 1), 1)

    def test_maximum_rpn(self):
        # 10 * 10 * 10 = 1000.
        self.assertEqual(rml.risk_priority_number(10, 10, 10), 1000)

    def test_detection_axis_counts(self):
        # Worse detection (higher rating) raises the RPN at fixed S and L.
        self.assertGreater(
            rml.risk_priority_number(6, 3, 8), rml.risk_priority_number(6, 3, 2)
        )

    def test_out_of_range_severity_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_priority_number(11, 5, 3)
        with self.assertRaises(ValueError):
            rml.risk_priority_number(0, 5, 3)

    def test_non_integer_likelihood_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_priority_number(8, 5.5, 3)

    def test_out_of_range_detection_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_priority_number(8, 5, 0)


class RiskPriorityClassificationTest(unittest.TestCase):
    def test_low_band(self):
        self.assertEqual(rml.risk_priority_classification(25), "low")

    def test_medium_band(self):
        self.assertEqual(rml.risk_priority_classification(60), "medium")

    def test_high_band(self):
        self.assertEqual(rml.risk_priority_classification(120), "high")

    def test_low_threshold_boundary_is_medium(self):
        # rpn < 40 is low; exactly 40 is medium.
        self.assertEqual(rml.risk_priority_classification(40), "medium")

    def test_high_threshold_boundary_is_high(self):
        # rpn >= 100 is high; exactly 100 is high.
        self.assertEqual(rml.risk_priority_classification(100), "high")

    def test_custom_thresholds(self):
        self.assertEqual(
            rml.risk_priority_classification(30, low_threshold=25, high_threshold=80),
            "medium",
        )
        self.assertEqual(
            rml.risk_priority_classification(90, low_threshold=25, high_threshold=80),
            "high",
        )

    def test_negative_rpn_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_priority_classification(-5)

    def test_inverted_thresholds_raise(self):
        with self.assertRaises(ValueError):
            rml.risk_priority_classification(60, low_threshold=100, high_threshold=40)


class MitigatedRiskPriorityNumberTest(unittest.TestCase):
    def test_reductions_lower_rpn(self):
        # (8-2) * (5-3) * (3-1) = 6 * 2 * 2 = 24.
        self.assertEqual(rml.mitigated_risk_priority_number(8, 5, 3, 2, 3, 1), 24)

    def test_zero_reductions_keep_rpn(self):
        # No mitigation: RPN unchanged at 8 * 5 * 3 = 120.
        self.assertEqual(rml.mitigated_risk_priority_number(8, 5, 3, 0, 0, 0), 120)

    def test_likelihood_reduction_dominates(self):
        # Dropping likelihood 5 -> 1 halves the RPN (5*3 vs 5*3 scaled).
        self.assertEqual(rml.mitigated_risk_priority_number(8, 5, 3, 0, 4, 0), 24)

    def test_mitigation_can_reach_floor(self):
        # (8-7) * (5-4) * (3-2) = 1 * 1 * 1 = 1.
        self.assertEqual(rml.mitigated_risk_priority_number(8, 5, 3, 7, 4, 2), 1)

    def test_reduction_exceeding_rating_raises(self):
        with self.assertRaises(ValueError):
            rml.mitigated_risk_priority_number(8, 5, 3, 9, 0, 0)

    def test_negative_reduction_raises(self):
        with self.assertRaises(ValueError):
            rml.mitigated_risk_priority_number(8, 5, 3, -1, 0, 0)

    def test_non_integer_reduction_raises(self):
        with self.assertRaises(ValueError):
            rml.mitigated_risk_priority_number(8, 5, 3, 0, 1.5, 0)


class RiskReductionFractionTest(unittest.TestCase):
    def test_120_to_24(self):
        # (120 - 24) / 120 = 0.8.
        self.assertAlmostEqual(rml.risk_reduction_fraction(120, 24), 0.8, places=9)

    def test_full_reduction(self):
        self.assertAlmostEqual(rml.risk_reduction_fraction(100, 0), 1.0, places=9)

    def test_no_reduction(self):
        self.assertAlmostEqual(rml.risk_reduction_fraction(100, 100), 0.0, places=9)

    def test_ineffective_plan_negative_fraction(self):
        # Residual above the original flags an ineffective plan.
        self.assertAlmostEqual(rml.risk_reduction_fraction(100, 120), -0.2, places=9)

    def test_non_positive_before_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_reduction_fraction(0, 10)

    def test_negative_after_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_reduction_fraction(100, -5)


class OccurrenceProbabilityTest(unittest.TestCase):
    def test_3_of_10000(self):
        # 3 / 10000 = 3e-4 per unit.
        self.assertAlmostEqual(rml.occurrence_probability(3, 10000), 3e-4, places=9)

    def test_zero_occurrences(self):
        self.assertAlmostEqual(rml.occurrence_probability(0, 500), 0.0, places=9)

    def test_every_unit_affected(self):
        self.assertAlmostEqual(rml.occurrence_probability(500, 500), 1.0, places=9)

    def test_negative_occurrences_raise(self):
        with self.assertRaises(ValueError):
            rml.occurrence_probability(-1, 500)

    def test_non_positive_units_raise(self):
        with self.assertRaises(ValueError):
            rml.occurrence_probability(3, 0)

    def test_occurrences_exceeding_units_raise(self):
        with self.assertRaises(ValueError):
            rml.occurrence_probability(501, 500)


class ResidualRiskAcceptableTest(unittest.TestCase):
    def test_below_threshold_accepted(self):
        self.assertTrue(rml.residual_risk_acceptable(24, 40))

    def test_at_threshold_accepted(self):
        self.assertTrue(rml.residual_risk_acceptable(40, 40))

    def test_above_threshold_rejected(self):
        self.assertFalse(rml.residual_risk_acceptable(60, 40))

    def test_negative_after_raises(self):
        with self.assertRaises(ValueError):
            rml.residual_risk_acceptable(-1, 40)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            rml.residual_risk_acceptable(10, -5)


class RiskMatrixClassificationTest(unittest.TestCase):
    def test_4_4_high(self):
        # 4 * 4 = 16 >= 15: high.
        self.assertEqual(rml.risk_matrix_classification(4, 4), "high")

    def test_3_5_high(self):
        # 3 * 5 = 15: high (boundary inclusive).
        self.assertEqual(rml.risk_matrix_classification(3, 5), "high")

    def test_3_2_medium(self):
        # 3 * 2 = 6: medium (boundary inclusive).
        self.assertEqual(rml.risk_matrix_classification(3, 2), "medium")

    def test_2_2_low(self):
        # 2 * 2 = 4: low.
        self.assertEqual(rml.risk_matrix_classification(2, 2), "low")

    def test_out_of_range_severity_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_matrix_classification(6, 3)
        with self.assertRaises(ValueError):
            rml.risk_matrix_classification(0, 3)

    def test_out_of_range_likelihood_raises(self):
        with self.assertRaises(ValueError):
            rml.risk_matrix_classification(3, 7)


class RankRisksTest(unittest.TestCase):
    def test_descending_rpn_order(self):
        # B (120) first, then A (50), then C (20).
        self.assertEqual(
            rml.rank_risks([("A", 50), ("B", 120), ("C", 20)]), ["B", "A", "C"]
        )

    def test_tie_broken_by_identifier(self):
        # Equal RPN: identifier ascending keeps the order deterministic.
        self.assertEqual(rml.rank_risks([("Y", 10), ("X", 10)]), ["X", "Y"])

    def test_single_risk(self):
        self.assertEqual(rml.rank_risks([("only", 75)]), ["only"])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            rml.rank_risks([])

    def test_negative_rpn_raises(self):
        with self.assertRaises(ValueError):
            rml.rank_risks([("A", -3), ("B", 10)])

    def test_non_finite_rpn_raises(self):
        with self.assertRaises(ValueError):
            rml.rank_risks([("A", float("nan"))])


if __name__ == "__main__":
    unittest.main()
