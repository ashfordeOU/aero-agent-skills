#!/usr/bin/env python3
"""Gate 3 contract test: trade study and Pugh matrix analysis.

Exercises scripts/trade_study_analysis.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - weighted scoring with
weights validated to sum 1.0, Pugh matrix verdict counting plus and
minus marks against a baseline, sensitivity re-ranking after weight
perturbation, selection verdict with margin and tie handling, and
requirement traceability of the alternatives. Run directly:
python3 scripts/test_trade_study_analysis.py
"""

import unittest

from trade_study_analysis import (
    pugh_matrix_verdict,
    selection_verdict,
    sensitivity_ranking,
    traceability_check,
    weighted_score,
)


class WeightedScoreTest(unittest.TestCase):
    def test_basic_weighted_score(self):
        self.assertAlmostEqual(weighted_score([0.5, 0.3, 0.2], [8, 6, 9]), 7.6)

    def test_weights_within_tolerance_accepted(self):
        # 0.3 + 0.3 + 0.4 = 1.0000000001, inside the 1e-9 tolerance.
        self.assertAlmostEqual(weighted_score([0.3, 0.3, 0.4], [1, 2, 3]), 2.1)

    def test_weights_not_summing_to_one_rejected(self):
        with self.assertRaises(ValueError):
            weighted_score([0.6, 0.5], [8, 6])

    def test_empty_lists_rejected(self):
        with self.assertRaises(ValueError):
            weighted_score([], [])

    def test_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            weighted_score([0.5, 0.5], [8, 6, 4])

    def test_negative_scores_allowed(self):
        self.assertAlmostEqual(weighted_score([1.0], [-3.0]), -3.0)


class PughMatrixVerdictTest(unittest.TestCase):
    # Rows are criteria; columns are alternatives (0 = baseline, whose
    # cells are 0 by definition). Alt 1 beats the baseline on rows 0
    # and 1; alt 2 loses on row 0 and ties elsewhere.
    MATRIX = [[0, 1, -1], [0, 1, 0], [0, 0, 0]]

    def test_baseline_nets_zero(self):
        verdicts = pugh_matrix_verdict(self.MATRIX, baseline_index=0)
        by_index = {v["index"]: v for v in verdicts}
        self.assertEqual(by_index[0]["net"], 0)

    def test_ranking_orders_alternatives(self):
        verdicts = pugh_matrix_verdict(self.MATRIX, baseline_index=0)
        self.assertEqual([v["index"] for v in verdicts], [1, 0, 2])

    def test_plus_minus_counts(self):
        verdicts = pugh_matrix_verdict(self.MATRIX, baseline_index=0)
        by_index = {v["index"]: v for v in verdicts}
        self.assertEqual(by_index[1]["plus"], 2)
        self.assertEqual(by_index[1]["minus"], 0)
        self.assertEqual(by_index[2]["minus"], 1)

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            pugh_matrix_verdict([])

    def test_ragged_rows_rejected(self):
        with self.assertRaises(ValueError):
            pugh_matrix_verdict([[1, 0], [1]])

    def test_invalid_cell_rejected(self):
        with self.assertRaises(ValueError):
            pugh_matrix_verdict([[1, 2, 0]])

    def test_baseline_index_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            pugh_matrix_verdict([[1, 0, -1]], baseline_index=5)

    def test_tie_between_alternatives(self):
        verdicts = pugh_matrix_verdict([[0, 1, 1], [0, 0, 0]])
        # Alternatives 1 and 2 both net +1; index ascending breaks the tie.
        self.assertEqual([v["index"] for v in verdicts], [1, 2, 0])
        self.assertEqual(verdicts[0]["net"], verdicts[1]["net"])


class SensitivityRankingTest(unittest.TestCase):
    WEIGHTS = [0.6, 0.4]
    SCORES = [[10, 0], [6, 5]]  # alt 0 wins base; alt 1 wins when weight 1 rises

    def test_base_winner_reported(self):
        result = sensitivity_ranking(self.WEIGHTS, self.SCORES, perturbation=0.3)
        self.assertEqual(result["base"]["winner"], 0)
        self.assertEqual(result["base"]["ranking"], [0, 1])

    def test_perturbation_flips_winner(self):
        # Base: alt 0 scores 6.0 vs alt 1 at 5.6. Raising weight 1 to
        # 0.7 renormalizes weight 0 down to 0.3, flipping the winner.
        result = sensitivity_ranking(self.WEIGHTS, self.SCORES, perturbation=0.3)
        flipped = [s for s in result["scenarios"] if s["criterion"] == 1][0]
        self.assertTrue(flipped["changed"])
        self.assertEqual(flipped["winner"], 1)

    def test_renormalized_weights_sum_to_one(self):
        result = sensitivity_ranking(self.WEIGHTS, self.SCORES, perturbation=0.3)
        for scenario in result["scenarios"]:
            self.assertAlmostEqual(sum(scenario["weights"]), 1.0)

    def test_perturbation_past_one_rejected(self):
        with self.assertRaises(ValueError):
            sensitivity_ranking([0.9, 0.1], [[1, 1]], perturbation=0.5)


class SelectionVerdictTest(unittest.TestCase):
    def test_clear_margin_is_confident(self):
        verdict = selection_verdict(8.0, 6.0)
        self.assertEqual(verdict["winner"], "best")
        self.assertAlmostEqual(verdict["margin"], 2.0)
        self.assertFalse(verdict["tie"])
        self.assertTrue(verdict["confident"])

    def test_tie_returns_tie_verdict(self):
        verdict = selection_verdict(6.0, 6.0)
        self.assertEqual(verdict["winner"], "tie")
        self.assertTrue(verdict["tie"])
        self.assertFalse(verdict["confident"])

    def test_small_margin_not_confident(self):
        verdict = selection_verdict(7.0, 6.98)
        self.assertEqual(verdict["winner"], "best")
        self.assertFalse(verdict["confident"])


class TraceabilityCheckTest(unittest.TestCase):
    ALTS = [
        {"id": "A1", "requirements": ["REQ-101", "REQ-102"]},
        {"id": "A2", "requirements": ["REQ-102"]},
    ]

    def test_full_traceability_passes(self):
        verdict = traceability_check(self.ALTS, ["REQ-101", "REQ-102"])
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["alternatives_missing"], [])
        self.assertEqual(verdict["uncovered_requirements"], [])

    def test_alternative_without_requirements_fails(self):
        alts = self.ALTS + [{"id": "A3", "requirements": []}]
        verdict = traceability_check(alts, ["REQ-101", "REQ-102"])
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["alternatives_missing"], ["A3"])

    def test_uncovered_requirement_fails(self):
        verdict = traceability_check(self.ALTS, ["REQ-101", "REQ-102", "REQ-103"])
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["uncovered_requirements"], ["REQ-103"])


if __name__ == "__main__":
    unittest.main()
