#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-tradeoff-drd (stdlib unittest, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_tradeoff_drd_logic import (  # noqa: E402
    SCORE_MAX, decision_margin, is_tradeoff_conclusive, missing_scores,
    rank_options, tradeoff_review, validate_score, validate_weights,
    weight_sensitivity, weighted_score, zero_weight_criteria,
)

CRIT = {"mass": 0.5, "cost": 0.3, "risk": 0.2}


def opts():
    return [
        {"option_id": "A", "scores": {"mass": 8.0, "cost": 6.0, "risk": 7.0}},
        {"option_id": "B", "scores": {"mass": 5.0, "cost": 9.0, "risk": 4.0}},
    ]


class WeightTest(unittest.TestCase):
    def test_normalized_weights_accepted(self):
        self.assertEqual(validate_weights(dict(CRIT)), CRIT)

    def test_unnormalized_weights_raise(self):
        with self.assertRaises(ValueError):
            validate_weights({"mass": 0.5, "cost": 0.2})

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            validate_weights({"mass": 1.2, "cost": -0.2})

    def test_empty_criteria_raise(self):
        with self.assertRaises(ValueError):
            validate_weights({})

    def test_zero_weight_criterion_is_surfaced(self):
        self.assertEqual(zero_weight_criteria({"a": 1.0, "b": 0.0}), ["b"])


class ScoreTest(unittest.TestCase):
    def test_in_range_score_accepted(self):
        self.assertEqual(validate_score(7), 7.0)

    def test_out_of_range_score_raises(self):
        with self.assertRaises(ValueError):
            validate_score(11.0)

    def test_boolean_is_not_a_score(self):
        with self.assertRaises(ValueError):
            validate_score(True)

    def test_missing_scores_are_listed_not_defaulted(self):
        o = opts()
        del o[0]["scores"]["risk"]
        self.assertEqual(missing_scores(CRIT, o), [("A", "risk")])

    def test_weighted_score_is_the_weighted_sum(self):
        got = weighted_score(CRIT, {"mass": 10.0, "cost": 0.0, "risk": 0.0})
        self.assertAlmostEqual(got, 5.0)

    def test_weighted_score_raises_on_a_gap(self):
        with self.assertRaises(ValueError):
            weighted_score(CRIT, {"mass": 5.0, "cost": 5.0})


class RankingTest(unittest.TestCase):
    def test_ranking_is_descending_by_score(self):
        r = rank_options(CRIT, opts())
        self.assertEqual(r[0][0], "A")
        self.assertGreater(r[0][1], r[1][1])

    def test_tie_is_broken_deterministically_by_id(self):
        same = {"mass": 5.0, "cost": 5.0, "risk": 5.0}
        o = [{"option_id": "Z", "scores": dict(same)},
             {"option_id": "A", "scores": dict(same)}]
        self.assertEqual([p[0] for p in rank_options(CRIT, o)], ["A", "Z"])

    def test_margin_is_the_gap_to_the_runner_up(self):
        r = rank_options(CRIT, opts())
        self.assertAlmostEqual(decision_margin(r), r[0][1] - r[1][1])

    def test_margin_needs_two_options(self):
        with self.assertRaises(ValueError):
            decision_margin([("A", 5.0)])


class SensitivityTest(unittest.TestCase):
    def test_robust_winner_reports_no_sensitive_criteria(self):
        o = [{"option_id": "A", "scores": {"mass": 10.0, "cost": 10.0, "risk": 10.0}},
             {"option_id": "B", "scores": {"mass": 1.0, "cost": 1.0, "risk": 1.0}}]
        self.assertEqual(weight_sensitivity(CRIT, o), [])

    def test_a_close_call_flips_on_some_weight(self):
        o = [{"option_id": "A", "scores": {"mass": 9.0, "cost": 1.0, "risk": 5.0}},
             {"option_id": "B", "scores": {"mass": 1.0, "cost": 9.0, "risk": 5.0}}]
        self.assertTrue(weight_sensitivity({"mass": 0.5, "cost": 0.45, "risk": 0.05},
                                           o, delta=0.4))

    def test_invalid_delta_raises(self):
        with self.assertRaises(ValueError):
            weight_sensitivity(CRIT, opts(), delta=0.0)

    def test_sensitivity_does_not_mutate_the_weighting(self):
        c = dict(CRIT)
        weight_sensitivity(c, opts())
        self.assertEqual(c, CRIT)


class ReviewTest(unittest.TestCase):
    def test_clean_report_is_conclusive(self):
        o = [{"option_id": "A", "scores": {"mass": 10.0, "cost": 10.0, "risk": 10.0}},
             {"option_id": "B", "scores": {"mass": 1.0, "cost": 1.0, "risk": 1.0}}]
        r = tradeoff_review({"criteria": CRIT, "options": o})
        self.assertEqual(r["winner"], "A")
        self.assertTrue(is_tradeoff_conclusive(r))

    def test_single_option_is_not_a_trade_off(self):
        r = tradeoff_review({"criteria": CRIT, "options": opts()[:1]})
        self.assertIn("not_a_trade_off", [f["issue"] for f in r["findings"]])
        self.assertIsNone(r["winner"])

    def test_missing_score_stops_before_ranking(self):
        o = opts()
        del o[1]["scores"]["cost"]
        r = tradeoff_review({"criteria": CRIT, "options": o})
        self.assertEqual(r["ranking"], [])
        self.assertIn("missing_score", [f["issue"] for f in r["findings"]])

    def test_indecisive_margin_is_flagged(self):
        o = [{"option_id": "A", "scores": {"mass": 5.0, "cost": 5.0, "risk": 5.0}},
             {"option_id": "B", "scores": {"mass": 5.0, "cost": 5.0, "risk": 4.9}}]
        r = tradeoff_review({"criteria": CRIT, "options": o})
        self.assertIn("indecisive_margin", [f["issue"] for f in r["findings"]])
        self.assertFalse(is_tradeoff_conclusive(r))

    def test_duplicate_option_id_raises(self):
        o = opts() + [opts()[0]]
        with self.assertRaises(ValueError):
            tradeoff_review({"criteria": CRIT, "options": o})

    def test_option_without_id_raises(self):
        with self.assertRaises(ValueError):
            tradeoff_review({"criteria": CRIT, "options": [{"scores": {}}]})

    def test_review_does_not_mutate_input(self):
        import copy
        rep = {"criteria": dict(CRIT), "options": opts()}
        before = copy.deepcopy(rep)
        tradeoff_review(rep)
        self.assertEqual(rep, before)

    def test_score_out_of_range_raises_from_the_review(self):
        o = opts()
        o[0]["scores"]["mass"] = 99.0
        with self.assertRaises(ValueError):
            tradeoff_review({"criteria": CRIT, "options": o})

    def test_score_scale_is_the_declared_maximum(self):
        self.assertEqual(SCORE_MAX, 10.0)


if __name__ == "__main__":
    unittest.main()
