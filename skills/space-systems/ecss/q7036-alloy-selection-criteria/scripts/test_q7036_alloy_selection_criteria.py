"""Contract tests for the SCC alloy selection criteria logic."""

import unittest

from q7036_alloy_selection_criteria_logic import (
    ACCEPTANCE_RULES,
    RANK_TOLERANCE,
    RESISTANCE_CATEGORIES,
    acceptance_for,
    category_rank,
    downgrade_category,
    effective_category,
    evaluate_candidate,
    normalize_category,
    normalize_criticality,
    normalize_direction,
    rank_candidates,
    select_alloy,
)


def candidate(cid, category="high", direction="longitudinal", strength=430.0):
    return {
        "id": cid,
        "resistance_category": category,
        "grain_direction": direction,
        "yield_strength_mpa": strength,
    }


class NormalizationTests(unittest.TestCase):
    def test_category_alias(self):
        self.assertEqual(normalize_category("Resistant"), "high")

    def test_category_unknown_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("immune")

    def test_criticality_alias(self):
        self.assertEqual(normalize_criticality("critical"), "scc-critical")

    def test_criticality_unknown_rejected(self):
        with self.assertRaises(ValueError):
            normalize_criticality("maybe")

    def test_direction_alias(self):
        self.assertEqual(normalize_direction("ST"), "short-transverse")

    def test_direction_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction("  ")

    def test_direction_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction(2)


class RatingAlgebraTests(unittest.TestCase):
    def test_rank_orders_most_resistant_first(self):
        self.assertEqual(category_rank("high"), 0)
        self.assertLess(category_rank("high"), category_rank("low"))

    def test_downgrade_moves_one_step(self):
        self.assertEqual(downgrade_category("high"), "medium")

    def test_downgrade_floors_at_the_lowest_rating(self):
        self.assertEqual(downgrade_category("low"), "low")
        self.assertEqual(downgrade_category("high", 9), "low")

    def test_zero_step_downgrade_is_identity(self):
        self.assertEqual(downgrade_category("medium", 0), "medium")

    def test_negative_steps_rejected(self):
        with self.assertRaises(ValueError):
            downgrade_category("high", -1)

    def test_non_integer_steps_rejected(self):
        with self.assertRaises(ValueError):
            downgrade_category("high", 1.5)

    def test_short_transverse_costs_a_rating_step(self):
        self.assertEqual(effective_category("high", "short-transverse"), "medium")

    def test_longitudinal_keeps_the_published_rating(self):
        self.assertEqual(effective_category("medium", "longitudinal"), "medium")

    def test_long_transverse_keeps_the_published_rating(self):
        self.assertEqual(effective_category("high", "lt"), "high")


class AcceptanceRuleTests(unittest.TestCase):
    def test_rules_cover_every_grade_and_rating(self):
        for grade, table in ACCEPTANCE_RULES.items():
            self.assertEqual(sorted(table), sorted(RESISTANCE_CATEGORIES), grade)

    def test_critical_takes_a_resistant_state(self):
        self.assertEqual(acceptance_for("scc-critical", "high"), "accepted")

    def test_critical_needs_evidence_for_an_intermediate_state(self):
        self.assertEqual(
            acceptance_for("scc-critical", "medium"), "accepted-with-evidence"
        )

    def test_critical_rejects_a_susceptible_state(self):
        self.assertEqual(acceptance_for("scc-critical", "low"), "rejected")

    def test_monitored_takes_an_intermediate_state(self):
        self.assertEqual(acceptance_for("scc-monitored", "medium"), "accepted")

    def test_cleared_application_takes_anything(self):
        for rating in RESISTANCE_CATEGORIES:
            self.assertEqual(acceptance_for("not-scc-critical", rating), "accepted")


class CandidateEvaluationTests(unittest.TestCase):
    def test_resistant_longitudinal_candidate_is_accepted(self):
        record = evaluate_candidate(candidate("c1"), "scc-critical")
        self.assertEqual(record["verdict"], "accepted")
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["notes"], [])

    def test_short_transverse_downgrade_is_noted(self):
        record = evaluate_candidate(
            candidate("c2", direction="short-transverse"), "scc-critical"
        )
        self.assertEqual(record["effective_category"], "medium")
        self.assertEqual(record["verdict"], "accepted-with-evidence")
        self.assertTrue(record["notes"])

    def test_susceptible_state_is_rejected_at_critical(self):
        record = evaluate_candidate(candidate("c3", category="low"), "scc-critical")
        self.assertFalse(record["acceptable"])

    def test_missing_key_rejected(self):
        broken = candidate("c4")
        del broken["grain_direction"]
        with self.assertRaises(ValueError):
            evaluate_candidate(broken, "scc-critical")

    def test_non_positive_strength_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(candidate("c5", strength=0.0), "scc-critical")

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(["c6"], "scc-critical")


class RankingTests(unittest.TestCase):
    def test_more_resistant_state_ranks_first(self):
        ranked = rank_candidates(
            [candidate("weak", category="low"), candidate("strong", category="high")],
            "scc-monitored",
        )
        self.assertEqual(ranked[0]["id"], "strong")

    def test_equal_rating_orders_on_strength(self):
        ranked = rank_candidates(
            [candidate("soft", strength=300.0), candidate("hard", strength=500.0)],
            "scc-critical",
        )
        self.assertEqual(ranked[0]["id"], "hard")

    def test_equal_rating_and_strength_orders_on_identifier(self):
        ranked = rank_candidates(
            [candidate("bravo", strength=430.0), candidate("alpha", strength=430.0)],
            "scc-critical",
        )
        self.assertEqual(ranked[0]["id"], "alpha")

    def test_strength_difference_inside_the_tolerance_is_a_tie(self):
        ranked = rank_candidates(
            [
                candidate("bravo", strength=430.0),
                candidate("alpha", strength=430.0 + RANK_TOLERANCE / 10.0),
            ],
            "scc-critical",
        )
        self.assertEqual(ranked[0]["id"], "alpha")

    def test_duplicate_candidate_id_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([candidate("c"), candidate("c")], "scc-critical")

    def test_empty_candidate_field_rejected(self):
        with self.assertRaises(ValueError):
            rank_candidates([], "scc-critical")


class SelectionTests(unittest.TestCase):
    def test_outright_acceptable_state_is_recommended(self):
        result = select_alloy(
            [candidate("plain", category="medium"), candidate("good", category="high")],
            "scc-critical",
        )
        self.assertEqual(result["recommended"]["id"], "good")
        self.assertTrue(result["compliant"])

    def test_evidence_only_field_is_flagged(self):
        result = select_alloy([candidate("only", category="medium")], "scc-critical")
        self.assertFalse(result["compliant"])
        self.assertEqual(result["recommended"]["id"], "only")
        self.assertTrue(any("test evidence" in f for f in result["findings"]))

    def test_no_usable_state_reports_no_recommendation(self):
        result = select_alloy([candidate("bad", category="low")], "scc-critical")
        self.assertIsNone(result["recommended"])
        self.assertEqual(result["acceptable_count"], 0)
        self.assertFalse(result["compliant"])

    def test_short_transverse_loss_appears_in_the_findings(self):
        result = select_alloy(
            [candidate("st", direction="short-transverse")], "scc-monitored"
        )
        self.assertTrue(any("short-transverse" in f for f in result["findings"]))

    def test_cleared_application_accepts_a_susceptible_state(self):
        result = select_alloy([candidate("bad", category="low")], "not-scc-critical")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_ranked_field_keeps_every_candidate(self):
        result = select_alloy(
            [candidate("a"), candidate("b", category="low"), candidate("c", category="medium")],
            "scc-critical",
        )
        self.assertEqual(len(result["ranked"]), 3)

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            select_alloy([candidate("a")], "very-critical")


if __name__ == "__main__":
    unittest.main()
