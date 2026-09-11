#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.3.3 + Annex L
trade-off analysis.

Exercises scripts/e10_tradeoffs_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - criteria must be a
non-empty mapping with a positive weight per entry and a
pass_threshold on every mandatory entry; a candidate's scores must
cover exactly the criteria set and stay within the evaluation scale;
a candidate failing a mandatory criterion is disqualified rather than
scored; qualified candidates are ranked by descending weighted score
with standard competition ranking for ties; a close call (tied leaders
or a thin margin) suppresses a single winner recommendation.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_tradeoffs_logic as tr  # noqa: E402


class ValidateCriteriaTest(unittest.TestCase):
    def test_empty_criteria_raises(self):
        with self.assertRaises(ValueError):
            tr.validate_criteria({})

    def test_non_positive_weight_raises(self):
        with self.assertRaises(ValueError):
            tr.validate_criteria({"cost": {"weight": 0.0}})

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            tr.validate_criteria({"cost": {"weight": -1.0}})

    def test_mandatory_without_pass_threshold_raises(self):
        with self.assertRaises(ValueError):
            tr.validate_criteria({"safety": {"weight": 1.0, "mandatory": True}})

    def test_valid_criteria_passes(self):
        criteria = {
            "cost": {"weight": 1.0},
            "safety": {"weight": 2.0, "mandatory": True, "pass_threshold": 6.0},
        }
        tr.validate_criteria(criteria)  # does not raise


class NormalizedWeightsTest(unittest.TestCase):
    def test_weights_sum_to_one(self):
        criteria = {"a": {"weight": 1.0}, "b": {"weight": 3.0}}
        weights = tr.normalized_weights(criteria)
        self.assertAlmostEqual(weights["a"], 0.25)
        self.assertAlmostEqual(weights["b"], 0.75)
        self.assertAlmostEqual(sum(weights.values()), 1.0)


class ValidateCandidateScoresTest(unittest.TestCase):
    def setUp(self):
        self.criteria = {"cost": {"weight": 1.0}, "mass": {"weight": 1.0}}

    def test_missing_criterion_raises(self):
        with self.assertRaises(ValueError):
            tr.validate_candidate_scores("A", {"cost": 5.0}, self.criteria)

    def test_extra_criterion_raises(self):
        scores = {"cost": 5.0, "mass": 5.0, "power": 5.0}
        with self.assertRaises(ValueError):
            tr.validate_candidate_scores("A", scores, self.criteria)

    def test_score_above_scale_raises(self):
        scores = {"cost": 5.0, "mass": 11.0}
        with self.assertRaises(ValueError):
            tr.validate_candidate_scores("A", scores, self.criteria)

    def test_score_below_scale_raises(self):
        scores = {"cost": -1.0, "mass": 5.0}
        with self.assertRaises(ValueError):
            tr.validate_candidate_scores("A", scores, self.criteria)

    def test_valid_scores_passes(self):
        scores = {"cost": 5.0, "mass": 7.5}
        tr.validate_candidate_scores("A", scores, self.criteria)  # no raise


class MandatoryFailuresTest(unittest.TestCase):
    def test_no_mandatory_criteria_never_fails(self):
        criteria = {"cost": {"weight": 1.0}}
        self.assertEqual(tr.mandatory_failures({"cost": 0.0}, criteria), [])

    def test_below_threshold_flagged(self):
        criteria = {"safety": {"weight": 1.0, "mandatory": True, "pass_threshold": 6.0}}
        self.assertEqual(
            tr.mandatory_failures({"safety": 4.0}, criteria), ["safety"]
        )

    def test_at_or_above_threshold_not_flagged(self):
        criteria = {"safety": {"weight": 1.0, "mandatory": True, "pass_threshold": 6.0}}
        self.assertEqual(tr.mandatory_failures({"safety": 6.0}, criteria), [])


class RankCandidatesTest(unittest.TestCase):
    def test_empty_candidates_raises(self):
        with self.assertRaises(ValueError):
            tr.rank_candidates({}, {"cost": {"weight": 1.0}})

    def test_higher_score_ranks_first(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 3.0}}
        ranked = tr.rank_candidates(candidates, criteria)
        self.assertEqual(ranked[0]["candidate_id"], "A")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertEqual(ranked[1]["candidate_id"], "B")
        self.assertEqual(ranked[1]["rank"], 2)

    def test_tied_scores_share_rank_and_next_resumes_at_position(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 8.0}, "C": {"cost": 2.0}}
        ranked = tr.rank_candidates(candidates, criteria)
        ranks = {entry["candidate_id"]: entry["rank"] for entry in ranked}
        self.assertEqual(ranks["A"], 1)
        self.assertEqual(ranks["B"], 1)
        self.assertEqual(ranks["C"], 3)

    def test_mandatory_failure_disqualifies_regardless_of_other_scores(self):
        criteria = {
            "safety": {"weight": 1.0, "mandatory": True, "pass_threshold": 6.0},
            "cost": {"weight": 1.0},
        }
        candidates = {
            "A": {"safety": 2.0, "cost": 10.0},
            "B": {"safety": 7.0, "cost": 1.0},
        }
        ranked = tr.rank_candidates(candidates, criteria)
        by_id = {entry["candidate_id"]: entry for entry in ranked}
        self.assertTrue(by_id["A"]["disqualified"])
        self.assertEqual(by_id["A"]["mandatory_failures"], ["safety"])
        self.assertIsNone(by_id["A"]["rank"])
        self.assertFalse(by_id["B"]["disqualified"])
        self.assertEqual(by_id["B"]["rank"], 1)

    def test_weighted_score_computation(self):
        criteria = {"cost": {"weight": 1.0}, "mass": {"weight": 3.0}}
        candidates = {"A": {"cost": 4.0, "mass": 8.0}}
        ranked = tr.rank_candidates(candidates, criteria)
        # normalized weights: cost 0.25, mass 0.75 -> 0.25*4 + 0.75*8 = 7.0
        self.assertAlmostEqual(ranked[0]["weighted_score"], 7.0)


class IsCloseCallTest(unittest.TestCase):
    def test_bad_margin_fraction_raises(self):
        with self.assertRaises(ValueError):
            tr.is_close_call([], margin_fraction=1.5)

    def test_single_qualified_candidate_not_close_call(self):
        criteria = {"cost": {"weight": 1.0}}
        ranked = tr.rank_candidates({"A": {"cost": 5.0}}, criteria)
        self.assertFalse(tr.is_close_call(ranked))

    def test_tied_leaders_is_close_call(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 8.0}}
        ranked = tr.rank_candidates(candidates, criteria)
        self.assertTrue(tr.is_close_call(ranked))

    def test_thin_margin_is_close_call(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 7.9}}
        ranked = tr.rank_candidates(candidates, criteria)
        self.assertTrue(tr.is_close_call(ranked, margin_fraction=0.05))

    def test_wide_margin_is_not_close_call(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 3.0}}
        ranked = tr.rank_candidates(candidates, criteria)
        self.assertFalse(tr.is_close_call(ranked, margin_fraction=0.05))


class TradeoffReportTest(unittest.TestCase):
    def test_clear_winner_reported(self):
        criteria = {"cost": {"weight": 1.0}, "mass": {"weight": 1.0}}
        candidates = {
            "A": {"cost": 9.0, "mass": 9.0},
            "B": {"cost": 2.0, "mass": 2.0},
        }
        report = tr.tradeoff_report(criteria, candidates)
        self.assertEqual(report["winner"], "A")
        self.assertFalse(report["close_call"])
        self.assertFalse(report["all_disqualified"])

    def test_close_call_suppresses_winner(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 8.0}, "B": {"cost": 7.9}}
        report = tr.tradeoff_report(criteria, candidates, margin_fraction=0.05)
        self.assertIsNone(report["winner"])
        self.assertTrue(report["close_call"])

    def test_all_candidates_disqualified(self):
        criteria = {"safety": {"weight": 1.0, "mandatory": True, "pass_threshold": 6.0}}
        candidates = {"A": {"safety": 1.0}, "B": {"safety": 2.0}}
        report = tr.tradeoff_report(criteria, candidates)
        self.assertIsNone(report["winner"])
        self.assertTrue(report["all_disqualified"])
        self.assertEqual(len(report["ranking"]), 2)

    def test_unrecognized_candidate_criterion_raises(self):
        criteria = {"cost": {"weight": 1.0}}
        candidates = {"A": {"cost": 5.0, "extra": 1.0}}
        with self.assertRaises(ValueError):
            tr.tradeoff_report(criteria, candidates)


if __name__ == "__main__":
    unittest.main(verbosity=2)
