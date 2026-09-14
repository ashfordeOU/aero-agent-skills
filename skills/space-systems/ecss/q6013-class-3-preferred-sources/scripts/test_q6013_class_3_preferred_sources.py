#!/usr/bin/env python3
"""Contract test for the Class 3 preferred sourcing order (offline)."""

import copy
import unittest

from q6013_class_3_preferred_sources_logic import (
    BUY_RESOLVED,
    BUY_UNRESOLVED,
    DEFAULT_DATE_CODE_LIMIT_MONTHS,
    MAX_POINTS,
    QUALITY_POINTS,
    QUALITY_SYSTEMS,
    SOURCE_CONDITIONAL,
    SOURCE_PREFERRED,
    SOURCE_REJECTED,
    SOURCE_TIERS,
    TIER_POINTS,
    TRACEABILITY_CHAINS,
    TRACEABILITY_POINTS,
    rank_sources,
    score_source,
    source_tier_rank,
    validate_candidate,
)

MAKER = {
    "name": "part-maker-direct",
    "source_tier": "manufacturer-direct",
    "traceability_chain": "unbroken-to-manufacturer",
    "quality_system": "certified-quality-system",
    "single_lot_delivery": True,
    "counterfeit_screening": True,
    "date_code_age_months": 4.0,
}

FRANCHISED = {
    "name": "franchised-stockist",
    "source_tier": "franchised-distributor",
    "traceability_chain": "unbroken-to-manufacturer",
    "quality_system": "certified-quality-system",
    "single_lot_delivery": True,
    "counterfeit_screening": True,
    "date_code_age_months": 9.0,
}

BROKER = {
    "name": "open-market-house",
    "source_tier": "open-market-broker",
    "traceability_chain": "documented-with-gaps",
    "quality_system": "declared-not-verified",
    "single_lot_delivery": False,
    "counterfeit_screening": True,
    "date_code_age_months": 40.0,
}


def _source(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class TierOrderTests(unittest.TestCase):
    def test_maker_is_first_in_the_order(self):
        self.assertEqual(source_tier_rank("manufacturer-direct"), 0)

    def test_broker_is_last_in_the_order(self):
        self.assertEqual(source_tier_rank("open-market-broker"), len(SOURCE_TIERS) - 1)

    def test_tier_points_fall_with_distance_from_the_maker(self):
        points = [TIER_POINTS[tier] for tier in SOURCE_TIERS]
        for nearer, farther in zip(points, points[1:]):
            self.assertGreater(nearer, farther)

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            source_tier_rank("a-guy-i-know")

    def test_traceability_points_fall_with_evidence(self):
        self.assertGreater(
            TRACEABILITY_POINTS["unbroken-to-manufacturer"],
            TRACEABILITY_POINTS["documented-with-gaps"],
        )
        self.assertGreater(TRACEABILITY_POINTS["documented-with-gaps"], 0)
        self.assertEqual(TRACEABILITY_POINTS["none"], 0)

    def test_quality_points_cover_every_system(self):
        for system in QUALITY_SYSTEMS:
            self.assertIn(system, QUALITY_POINTS)


class CandidateValidationTests(unittest.TestCase):
    def test_complete_candidate_validates(self):
        self.assertIs(validate_candidate(MAKER), MAKER)

    def test_missing_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(_source(MAKER, name="  "))

    def test_unknown_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(_source(MAKER, traceability_chain="probably-fine"))

    def test_unknown_quality_system_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(_source(MAKER, quality_system="they-seem-good"))

    def test_non_boolean_screening_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(_source(MAKER, counterfeit_screening="yes"))

    def test_negative_date_code_age_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate(_source(MAKER, date_code_age_months=-3.0))

    def test_non_mapping_candidate_rejected(self):
        with self.assertRaises(ValueError):
            validate_candidate("the maker")


class ScoreSourceTests(unittest.TestCase):
    def test_maker_direct_scores_the_maximum(self):
        graded = score_source(MAKER)
        self.assertEqual(graded["points"], MAX_POINTS)
        self.assertAlmostEqual(graded["normalized_score"], 1.0, places=9)
        self.assertEqual(graded["verdict"], SOURCE_PREFERRED)

    def test_franchised_scores_below_the_maker(self):
        self.assertLess(score_source(FRANCHISED)["points"], score_source(MAKER)["points"])

    def test_points_are_the_declared_sum(self):
        graded = score_source(FRANCHISED)
        expected = (
            TIER_POINTS["franchised-distributor"]
            + TRACEABILITY_POINTS["unbroken-to-manufacturer"]
            + QUALITY_POINTS["certified-quality-system"]
            + 6
            + 6
            + 8
        )
        self.assertEqual(graded["points"], expected)

    def test_no_traceability_is_a_blocker_whatever_the_tier(self):
        graded = score_source(_source(MAKER, traceability_chain="none"))
        self.assertEqual(graded["verdict"], SOURCE_REJECTED)
        self.assertFalse(graded["admissible"])
        self.assertTrue(graded["blockers"])

    def test_broker_without_screening_is_a_blocker(self):
        graded = score_source(_source(BROKER, counterfeit_screening=False))
        self.assertEqual(graded["verdict"], SOURCE_REJECTED)

    def test_broker_with_screening_is_conditional_not_rejected(self):
        graded = score_source(BROKER)
        self.assertEqual(graded["verdict"], SOURCE_CONDITIONAL)
        self.assertTrue(graded["admissible"])
        self.assertTrue(graded["conditions"])

    def test_independent_without_screening_is_a_condition_not_a_blocker(self):
        graded = score_source(
            _source(
                FRANCHISED,
                name="independent-house",
                source_tier="independent-distributor",
                counterfeit_screening=False,
            )
        )
        self.assertEqual(graded["verdict"], SOURCE_CONDITIONAL)
        self.assertTrue(
            any("counterfeit screening" in c for c in graded["conditions"])
        )

    def test_date_code_exactly_on_the_limit_still_earns_the_points(self):
        graded = score_source(
            _source(MAKER, date_code_age_months=DEFAULT_DATE_CODE_LIMIT_MONTHS)
        )
        self.assertTrue(graded["date_code_within_limit"])
        self.assertEqual(graded["points"], MAX_POINTS)

    def test_representation_error_at_the_date_code_limit_is_absorbed(self):
        limit = DEFAULT_DATE_CODE_LIMIT_MONTHS
        drifted = limit + limit * 2.0e-16
        graded = score_source(_source(MAKER, date_code_age_months=drifted))
        self.assertTrue(graded["date_code_within_limit"])

    def test_stale_date_code_loses_its_points_and_adds_a_condition(self):
        graded = score_source(_source(MAKER, date_code_age_months=60.0))
        self.assertFalse(graded["date_code_within_limit"])
        self.assertEqual(graded["points"], MAX_POINTS - 8)
        self.assertTrue(any("solderability" in c for c in graded["conditions"]))

    def test_mixed_lot_delivery_adds_a_condition(self):
        graded = score_source(_source(MAKER, single_lot_delivery=False))
        self.assertEqual(graded["verdict"], SOURCE_CONDITIONAL)
        self.assertTrue(any("single lot" in c for c in graded["conditions"]))

    def test_zero_date_code_limit_rejected(self):
        with self.assertRaises(ValueError):
            score_source(MAKER, 0.0)


class RankSourcesTests(unittest.TestCase):
    def test_maker_wins_over_franchised_and_broker(self):
        result = rank_sources([BROKER, FRANCHISED, MAKER])
        self.assertEqual(result["verdict"], BUY_RESOLVED)
        self.assertEqual(result["preferred_source"], "part-maker-direct")

    def test_order_runs_from_best_to_worst(self):
        result = rank_sources([BROKER, FRANCHISED, MAKER])
        points = [entry["points"] for entry in result["ordered"]]
        self.assertEqual(points, sorted(points, reverse=True))

    def test_runner_up_and_margin_are_reported(self):
        result = rank_sources([MAKER, FRANCHISED])
        self.assertEqual(result["runner_up"], "franchised-stockist")
        self.assertEqual(
            result["margin_points"],
            score_source(MAKER)["points"] - score_source(FRANCHISED)["points"],
        )

    def test_a_rejected_source_is_never_preferred_even_when_it_scores_well(self):
        rich_but_blocked = _source(
            MAKER, name="no-chain-maker", traceability_chain="none"
        )
        result = rank_sources([rich_but_blocked, FRANCHISED])
        self.assertEqual(result["preferred_source"], "franchised-stockist")
        self.assertEqual(
            [entry["name"] for entry in result["rejected"]], ["no-chain-maker"]
        )

    def test_no_admissible_source_is_reported_not_forced(self):
        result = rank_sources(
            [
                _source(MAKER, name="no-chain", traceability_chain="none"),
                _source(BROKER, name="blind-broker", counterfeit_screening=False),
            ]
        )
        self.assertEqual(result["verdict"], BUY_UNRESOLVED)
        self.assertIsNone(result["preferred_source"])
        self.assertFalse(result["resolved"])

    def test_tie_is_broken_by_the_nearer_tier(self):
        near = _source(
            MAKER,
            name="near-source",
            source_tier="manufacturer-approved-subcontractor",
            quality_system="certified-quality-system",
        )
        far = _source(
            MAKER,
            name="far-source",
            source_tier="independent-distributor",
            quality_system="certified-quality-system",
        )
        far["source_tier"] = "independent-distributor"
        near_points = score_source(near)["points"]
        far_points = score_source(far)["points"]
        if near_points == far_points:
            result = rank_sources([far, near])
            self.assertEqual(result["preferred_source"], "near-source")
        else:
            self.assertGreater(near_points, far_points)

    def test_single_offer_is_still_ranked(self):
        result = rank_sources([FRANCHISED])
        self.assertEqual(result["preferred_source"], "franchised-stockist")
        self.assertIsNone(result["runner_up"])
        self.assertIsNone(result["margin_points"])

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources([MAKER, _source(MAKER)])

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources([])

    def test_non_sequence_candidates_rejected(self):
        with self.assertRaises(ValueError):
            rank_sources(MAKER)

    def test_rationale_names_the_preferred_source(self):
        result = rank_sources([BROKER, MAKER])
        self.assertIn("part-maker-direct", result["rationale"])

    def test_normalized_score_never_exceeds_one(self):
        for entry in rank_sources([BROKER, FRANCHISED, MAKER])["ordered"]:
            self.assertTrue(entry["normalized_score"] <= 1.0)
            self.assertTrue(entry["normalized_score"] >= 0.0)

    def test_every_tier_can_be_scored(self):
        for index, tier in enumerate(SOURCE_TIERS):
            candidate = _source(MAKER, name="offer-%d" % index, source_tier=tier)
            self.assertIn(score_source(candidate)["verdict"],
                          (SOURCE_PREFERRED, SOURCE_CONDITIONAL, SOURCE_REJECTED))

    def test_every_chain_can_be_scored(self):
        for index, chain in enumerate(TRACEABILITY_CHAINS):
            candidate = _source(
                MAKER, name="chain-%d" % index, traceability_chain=chain
            )
            self.assertIn(score_source(candidate)["admissible"], (True, False))


if __name__ == "__main__":
    unittest.main(verbosity=1)
