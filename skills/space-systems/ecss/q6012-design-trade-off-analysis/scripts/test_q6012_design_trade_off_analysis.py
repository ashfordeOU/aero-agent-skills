"""Contract tests for the clause 7.1.4 architecture trade-off logic."""

import unittest

from q6012_design_trade_off_analysis_logic import (
    CRITERIA,
    HIGHER_IS_BETTER,
    SCORE_TIE_TOLERANCE,
    candidate_utilities,
    normalise_metric,
    rank_candidates,
    score_candidate,
    select_architecture,
    threshold_violations,
    validate_bounds,
    validate_weights,
    weight_sensitivity,
)

# performance = small-signal gain in dB, yield = fraction, size = die area in
# mm2, power = dc consumption in W.
THRESHOLDS = {"performance": 18.0, "yield": 0.55, "size": 12.0, "power": 3.0}
GOALS = {"performance": 26.0, "yield": 0.85, "size": 4.0, "power": 1.0}
WEIGHTS = {"performance": 0.40, "yield": 0.30, "size": 0.15, "power": 0.15}

BOUNDS = validate_bounds(THRESHOLDS, GOALS)

BALANCED = {"name": "balanced-cascode", "performance": 23.0, "yield": 0.76,
            "size": 7.0, "power": 1.8}
HIGH_GAIN = {"name": "high-gain-stack", "performance": 25.5, "yield": 0.60,
             "size": 10.5, "power": 2.7}
COMPACT = {"name": "compact-single-stage", "performance": 19.0, "yield": 0.82,
           "size": 4.5, "power": 1.2}
INFEASIBLE = {"name": "wideband-distributed", "performance": 16.0, "yield": 0.50,
              "size": 14.0, "power": 3.4}


def clean_spec(**overrides):
    spec = {
        "candidates": [BALANCED, HIGH_GAIN, COMPACT, INFEASIBLE],
        "thresholds": dict(THRESHOLDS),
        "goals": dict(GOALS),
        "weights": dict(WEIGHTS),
    }
    spec.update(overrides)
    return spec


class ValidateWeightsTests(unittest.TestCase):
    def test_partition_of_one_accepted(self):
        self.assertEqual(set(validate_weights(WEIGHTS)), set(CRITERIA))

    def test_weights_not_summing_to_one_rejected(self):
        bad = dict(WEIGHTS)
        bad["power"] = 0.30
        with self.assertRaises(ValueError):
            validate_weights(bad)

    def test_missing_criterion_rejected(self):
        bad = dict(WEIGHTS)
        del bad["size"]
        with self.assertRaises(ValueError):
            validate_weights(bad)

    def test_unknown_criterion_rejected(self):
        bad = dict(WEIGHTS)
        bad["cost"] = 0.0
        with self.assertRaises(ValueError):
            validate_weights(bad)

    def test_negative_weight_rejected(self):
        bad = dict(WEIGHTS)
        bad["size"] = -0.15
        bad["performance"] = 0.70
        with self.assertRaises(ValueError):
            validate_weights(bad)

    def test_non_mapping_weights_rejected(self):
        with self.assertRaises(ValueError):
            validate_weights([0.4, 0.3, 0.15, 0.15])


class ValidateBoundsTests(unittest.TestCase):
    def test_bounds_returned_per_criterion(self):
        self.assertEqual(BOUNDS["performance"], (18.0, 26.0))
        self.assertEqual(BOUNDS["size"], (12.0, 4.0))

    def test_higher_is_better_goal_below_threshold_rejected(self):
        bad = dict(GOALS)
        bad["performance"] = 15.0
        with self.assertRaises(ValueError):
            validate_bounds(THRESHOLDS, bad)

    def test_lower_is_better_goal_above_threshold_rejected(self):
        bad = dict(GOALS)
        bad["power"] = 4.0
        with self.assertRaises(ValueError):
            validate_bounds(THRESHOLDS, bad)

    def test_missing_goal_rejected(self):
        bad = dict(GOALS)
        del bad["yield"]
        with self.assertRaises(ValueError):
            validate_bounds(THRESHOLDS, bad)

    def test_non_numeric_threshold_rejected(self):
        bad = dict(THRESHOLDS)
        bad["size"] = "12"
        with self.assertRaises(ValueError):
            validate_bounds(bad, GOALS)


class NormaliseMetricTests(unittest.TestCase):
    def test_value_at_threshold_is_zero_utility(self):
        self.assertAlmostEqual(normalise_metric(18.0, 18.0, 26.0, True), 0.0, places=9)

    def test_value_at_goal_is_unit_utility(self):
        self.assertAlmostEqual(normalise_metric(26.0, 18.0, 26.0, True), 1.0, places=9)

    def test_midpoint_is_half_utility(self):
        self.assertAlmostEqual(normalise_metric(22.0, 18.0, 26.0, True), 0.5, places=9)

    def test_lower_is_better_direction_inverts(self):
        self.assertAlmostEqual(normalise_metric(8.0, 12.0, 4.0, False), 0.5, places=9)

    def test_over_delivery_is_clamped_at_one(self):
        self.assertAlmostEqual(normalise_metric(40.0, 18.0, 26.0, True), 1.0, places=9)

    def test_under_delivery_is_clamped_at_zero(self):
        self.assertAlmostEqual(normalise_metric(10.0, 18.0, 26.0, True), 0.0, places=9)

    def test_equal_threshold_and_goal_rejected(self):
        with self.assertRaises(ValueError):
            normalise_metric(20.0, 20.0, 20.0, True)

    def test_direction_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            normalise_metric(20.0, 18.0, 26.0, False)

    def test_non_boolean_direction_rejected(self):
        with self.assertRaises(ValueError):
            normalise_metric(20.0, 18.0, 26.0, "higher")


class ThresholdViolationTests(unittest.TestCase):
    def test_compliant_candidate_violates_nothing(self):
        self.assertEqual(threshold_violations(BALANCED, BOUNDS), [])

    def test_every_missed_criterion_is_named(self):
        self.assertEqual(
            threshold_violations(INFEASIBLE, BOUNDS),
            ["performance", "yield", "size", "power"],
        )

    def test_candidate_exactly_on_every_threshold_is_feasible(self):
        on_limit = {"name": "on-limit", "performance": 18.0, "yield": 0.55,
                    "size": 12.0, "power": 3.0}
        self.assertEqual(threshold_violations(on_limit, BOUNDS), [])

    def test_single_axis_miss_is_reported_alone(self):
        nearly = dict(BALANCED)
        nearly["name"] = "nearly"
        nearly["power"] = 3.5
        self.assertEqual(threshold_violations(nearly, BOUNDS), ["power"])

    def test_missing_metric_rejected(self):
        short = dict(BALANCED)
        del short["yield"]
        with self.assertRaises(ValueError):
            threshold_violations(short, BOUNDS)

    def test_unnamed_candidate_rejected(self):
        anonymous = dict(BALANCED)
        anonymous["name"] = "  "
        with self.assertRaises(ValueError):
            threshold_violations(anonymous, BOUNDS)

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            threshold_violations(["balanced-cascode"], BOUNDS)


class ScoringTests(unittest.TestCase):
    def test_utilities_cover_all_four_criteria(self):
        self.assertEqual(set(candidate_utilities(BALANCED, BOUNDS)), set(CRITERIA))

    def test_score_is_the_weighted_sum_of_utilities(self):
        utilities = candidate_utilities(BALANCED, BOUNDS)
        expected = sum(WEIGHTS[c] * utilities[c] for c in CRITERIA)
        self.assertAlmostEqual(
            score_candidate(BALANCED, BOUNDS, WEIGHTS), expected, places=9
        )

    def test_a_candidate_at_every_goal_scores_one(self):
        perfect = {"name": "ideal", "performance": 26.0, "yield": 0.85,
                   "size": 4.0, "power": 1.0}
        self.assertAlmostEqual(
            score_candidate(perfect, BOUNDS, WEIGHTS), 1.0, places=9
        )

    def test_a_candidate_at_every_threshold_scores_zero(self):
        marginal = {"name": "marginal", "performance": 18.0, "yield": 0.55,
                    "size": 12.0, "power": 3.0}
        self.assertAlmostEqual(
            score_candidate(marginal, BOUNDS, WEIGHTS), 0.0, places=9
        )

    def test_over_delivery_on_one_axis_cannot_exceed_unity(self):
        lopsided = {"name": "lopsided", "performance": 60.0, "yield": 0.85,
                    "size": 4.0, "power": 1.0}
        self.assertAlmostEqual(
            score_candidate(lopsided, BOUNDS, WEIGHTS), 1.0, places=9
        )

    def test_direction_map_covers_every_criterion(self):
        self.assertEqual(set(HIGHER_IS_BETTER), set(CRITERIA))


class RankingTests(unittest.TestCase):
    def test_infeasible_candidate_is_not_ranked(self):
        names = [row["name"] for row in rank_candidates(
            [BALANCED, HIGH_GAIN, COMPACT, INFEASIBLE], BOUNDS, WEIGHTS)]
        self.assertNotIn("wideband-distributed", names)
        self.assertEqual(len(names), 3)

    def test_ranking_is_ordered_best_first(self):
        ranked = rank_candidates([BALANCED, HIGH_GAIN, COMPACT], BOUNDS, WEIGHTS)
        scores = [row["score"] for row in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_equal_scores_fall_back_to_the_name_for_reproducibility(self):
        twin_a = dict(BALANCED)
        twin_a["name"] = "zeta-variant"
        twin_b = dict(BALANCED)
        twin_b["name"] = "alpha-variant"
        ranked = rank_candidates([twin_a, twin_b], BOUNDS, WEIGHTS)
        self.assertEqual(ranked[0]["name"], "alpha-variant")

    def test_duplicate_candidate_name_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([BALANCED, dict(BALANCED)], BOUNDS, WEIGHTS)

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([], BOUNDS, WEIGHTS)


class SensitivityTests(unittest.TestCase):
    def test_a_robust_preference_reports_no_flip(self):
        dominant = {"name": "dominant", "performance": 26.0, "yield": 0.85,
                    "size": 4.0, "power": 1.0}
        flips = weight_sensitivity([dominant, BALANCED], BOUNDS, WEIGHTS)
        self.assertEqual(flips, [])

    def test_a_close_pair_flips_under_a_weight_move(self):
        flips = weight_sensitivity(
            [BALANCED, COMPACT], BOUNDS, WEIGHTS, perturbation=0.35
        )
        self.assertTrue(flips)
        self.assertTrue(all(f["new_leader"] != "balanced-cascode" for f in flips))

    def test_perturbation_at_or_above_one_rejected(self):
        with self.assertRaises(ValueError):
            weight_sensitivity([BALANCED, COMPACT], BOUNDS, WEIGHTS, perturbation=1.0)

    def test_non_positive_perturbation_rejected(self):
        with self.assertRaises(ValueError):
            weight_sensitivity([BALANCED, COMPACT], BOUNDS, WEIGHTS, perturbation=0.0)


class SelectArchitectureTests(unittest.TestCase):
    def test_preferred_architecture_is_the_top_of_the_ranking(self):
        result = select_architecture(clean_spec())
        self.assertEqual(result["preferred"], result["ranking"][0]["name"])

    def test_infeasible_candidate_is_eliminated_with_its_reasons(self):
        result = select_architecture(clean_spec())
        eliminated = {row["name"]: row["violated"] for row in result["eliminated"]}
        self.assertIn("wideband-distributed", eliminated)
        self.assertIn("power", eliminated["wideband-distributed"])

    def test_elimination_is_a_finding_not_a_silent_drop(self):
        result = select_architecture(clean_spec())
        self.assertTrue(
            any("wideband-distributed" in f for f in result["findings"])
        )

    def test_no_feasible_candidate_settles_nothing(self):
        result = select_architecture(clean_spec(candidates=[INFEASIBLE]))
        self.assertIsNone(result["preferred"])
        self.assertFalse(result["decision_supported"])
        self.assertEqual(result["ranking"], [])

    def test_a_tie_is_reported_rather_than_broken_by_float_noise(self):
        twin_a = dict(BALANCED)
        twin_a["name"] = "alpha-variant"
        twin_b = dict(BALANCED)
        twin_b["name"] = "zeta-variant"
        result = select_architecture(clean_spec(candidates=[twin_a, twin_b]))
        self.assertEqual(result["tied_with_leader"], ["zeta-variant"])
        self.assertFalse(result["decision_supported"])

    def test_scores_inside_the_tie_tolerance_count_as_tied(self):
        twin_a = dict(BALANCED)
        twin_a["name"] = "alpha-variant"
        twin_b = dict(BALANCED)
        twin_b["name"] = "zeta-variant"
        twin_b["performance"] = BALANCED["performance"] + SCORE_TIE_TOLERANCE / 10.0
        result = select_architecture(clean_spec(candidates=[twin_a, twin_b]))
        self.assertEqual(len(result["tied_with_leader"]), 1)

    def test_a_weighting_driven_preference_is_not_decision_supported(self):
        result = select_architecture(
            clean_spec(candidates=[BALANCED, COMPACT], perturbation=0.35)
        )
        self.assertTrue(result["sensitivity"])
        self.assertFalse(result["decision_supported"])

    def test_a_dominant_candidate_supports_the_decision(self):
        dominant = {"name": "dominant", "performance": 26.0, "yield": 0.85,
                    "size": 4.0, "power": 1.0}
        result = select_architecture(clean_spec(candidates=[dominant, BALANCED]))
        self.assertEqual(result["preferred"], "dominant")
        self.assertTrue(result["decision_supported"])

    def test_reweighting_towards_size_can_change_the_preference(self):
        size_led = {"performance": 0.10, "yield": 0.10, "size": 0.70, "power": 0.10}
        balanced_led = select_architecture(
            clean_spec(candidates=[BALANCED, COMPACT])
        )["preferred"]
        size_result = select_architecture(
            clean_spec(candidates=[BALANCED, COMPACT], weights=size_led)
        )
        self.assertEqual(balanced_led, "balanced-cascode")
        self.assertEqual(size_result["preferred"], "compact-single-stage")

    def test_missing_spec_key_rejected(self):
        spec = clean_spec()
        del spec["goals"]
        with self.assertRaises(ValueError):
            select_architecture(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            select_architecture(["candidates"])

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            select_architecture(clean_spec(candidates=[]))

    def test_ranking_carries_the_per_criterion_utilities(self):
        result = select_architecture(clean_spec())
        self.assertEqual(
            set(result["ranking"][0]["utilities"]), set(CRITERIA)
        )


if __name__ == "__main__":
    unittest.main()
