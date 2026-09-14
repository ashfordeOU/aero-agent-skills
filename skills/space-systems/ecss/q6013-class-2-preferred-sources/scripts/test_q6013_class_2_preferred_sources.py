#!/usr/bin/env python3
"""Contract test for the Class 2 preferred sources rules (offline)."""

import copy
import unittest

from q6013_class_2_preferred_sources_logic import (
    ACCEPT_AS_DIRECTED,
    ACCEPT_WITH_ADDED_EVALUATION,
    ACCEPT_WITH_FULL_UPSCREENING,
    ADDED_EVALUATION_INDEX,
    CHAIN_RECORDS,
    DIRECTED_INDEX,
    REJECT_SOURCE,
    SOURCE_TIERS,
    TIER_CREDIT,
    added_evaluation,
    assess_sourcing,
    chain_completeness,
    choose_disposition,
    line_stability,
    shelf_age_penalty,
    sourcing_assurance_index,
    tier_credit,
)

GOOD_CASE = {
    "source_tier": "qualified-parts-listing",
    "records_held": list(CHAIN_RECORDS),
    "counterfeit_inspection": False,
    "change_notice_subscribed": True,
    "line_changes_since_evidence": 0,
    "date_code_age_months": 12.0,
    "shelf_policy_months": 24.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class TierTests(unittest.TestCase):
    def test_every_tier_carries_a_credit(self):
        for tier in SOURCE_TIERS:
            self.assertIn(tier, TIER_CREDIT)

    def test_credits_fall_down_the_ladder(self):
        credits = [tier_credit(tier) for tier in SOURCE_TIERS]
        for stronger, weaker in zip(credits, credits[1:]):
            self.assertGreater(stronger - weaker, 1.0e-6)

    def test_qualified_listing_is_the_full_credit(self):
        self.assertAlmostEqual(tier_credit("qualified-parts-listing"), 1.0, places=9)

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            tier_credit("garage-sale")


class ChainTests(unittest.TestCase):
    def test_full_chain_is_complete(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertTrue(chain["complete"])
        self.assertAlmostEqual(chain["fraction"], 1.0, places=9)
        self.assertEqual(chain["missing"], ())

    def test_one_gap_is_covered_by_the_incoming_inspection(self):
        held = [r for r in CHAIN_RECORDS if r != "distribution-chain-record"]
        chain = chain_completeness(held, counterfeit_inspection=True)
        self.assertTrue(chain["complete"])
        self.assertEqual(chain["substituted_record"], "distribution-chain-record")

    def test_one_gap_without_the_inspection_is_not_covered(self):
        held = [r for r in CHAIN_RECORDS if r != "distribution-chain-record"]
        chain = chain_completeness(held, counterfeit_inspection=False)
        self.assertFalse(chain["complete"])
        self.assertIsNone(chain["substituted_record"])
        self.assertAlmostEqual(chain["fraction"], 2.0 / 3.0, places=9)

    def test_two_gaps_cannot_be_covered(self):
        chain = chain_completeness(
            ["project-receipt-record"], counterfeit_inspection=True
        )
        self.assertFalse(chain["complete"])
        self.assertIsNone(chain["substituted_record"])
        self.assertAlmostEqual(chain["fraction"], 1.0 / 3.0, places=9)

    def test_unknown_record_rejected(self):
        with self.assertRaises(ValueError):
            chain_completeness(["a-verbal-assurance"])

    def test_string_instead_of_a_record_collection_rejected(self):
        with self.assertRaises(ValueError):
            chain_completeness("maker-lot-record")

    def test_non_boolean_inspection_flag_rejected(self):
        with self.assertRaises(ValueError):
            chain_completeness(CHAIN_RECORDS, counterfeit_inspection="yes")


class ShelfAgeTests(unittest.TestCase):
    def test_age_inside_the_policy_costs_nothing(self):
        self.assertAlmostEqual(shelf_age_penalty(10.0, 24.0), 0.0, places=9)

    def test_age_exactly_on_the_policy_costs_nothing(self):
        self.assertAlmostEqual(shelf_age_penalty(24.0, 24.0), 0.0, places=9)

    def test_penalty_ramps_past_the_policy(self):
        self.assertAlmostEqual(shelf_age_penalty(36.0, 24.0), 0.5, places=9)

    def test_penalty_holds_at_one(self):
        self.assertAlmostEqual(shelf_age_penalty(240.0, 24.0), 1.0, places=9)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            shelf_age_penalty(-1.0, 24.0)

    def test_zero_shelf_policy_rejected(self):
        with self.assertRaises(ValueError):
            shelf_age_penalty(10.0, 0.0)


class StabilityTests(unittest.TestCase):
    def test_subscribed_clean_line_is_fully_stable(self):
        self.assertAlmostEqual(line_stability(True, 0, 0.0), 1.0, places=9)

    def test_unsubscribed_line_starts_lower(self):
        self.assertAlmostEqual(line_stability(False, 0, 0.0), 0.65, places=9)

    def test_each_line_change_costs_the_same(self):
        self.assertAlmostEqual(line_stability(True, 3, 0.0), 0.70, places=9)

    def test_ageing_pulls_stability_down(self):
        self.assertAlmostEqual(line_stability(True, 0, 0.5), 0.90, places=9)

    def test_stability_never_goes_below_zero(self):
        self.assertAlmostEqual(line_stability(False, 20, 1.0), 0.0, places=9)

    def test_fractional_line_change_count_rejected(self):
        with self.assertRaises(ValueError):
            line_stability(True, 1.5, 0.0)

    def test_age_penalty_above_one_rejected(self):
        with self.assertRaises(ValueError):
            line_stability(True, 0, 1.4)


class IndexTests(unittest.TestCase):
    def test_fully_preferred_sourcing_scores_one(self):
        self.assertAlmostEqual(sourcing_assurance_index(1.0, 1.0, 1.0), 1.0, places=9)

    def test_index_is_the_weighted_blend(self):
        self.assertAlmostEqual(
            sourcing_assurance_index(0.90, 1.0, 0.25), 0.80, places=9
        )

    def test_index_component_above_one_rejected(self):
        with self.assertRaises(ValueError):
            sourcing_assurance_index(1.2, 1.0, 1.0)

    def test_negative_index_component_rejected(self):
        with self.assertRaises(ValueError):
            sourcing_assurance_index(0.5, -0.1, 1.0)


class DispositionTests(unittest.TestCase):
    def test_strong_source_is_accepted_as_directed(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertEqual(
            choose_disposition("qualified-parts-listing", chain, 0.95),
            ACCEPT_AS_DIRECTED,
        )

    def test_index_exactly_on_the_directed_threshold_is_directed(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertEqual(
            choose_disposition("preferred-manufacturer", chain, DIRECTED_INDEX),
            ACCEPT_AS_DIRECTED,
        )

    def test_representation_error_at_the_threshold_is_absorbed(self):
        chain = chain_completeness(CHAIN_RECORDS)
        drifted = DIRECTED_INDEX - DIRECTED_INDEX * 2.0e-16
        self.assertEqual(
            choose_disposition("preferred-manufacturer", chain, drifted),
            ACCEPT_AS_DIRECTED,
        )

    def test_index_exactly_on_the_added_evaluation_threshold(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertEqual(
            choose_disposition(
                "franchised-distributor", chain, ADDED_EVALUATION_INDEX
            ),
            ACCEPT_WITH_ADDED_EVALUATION,
        )

    def test_broker_without_an_inspection_is_refused(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertEqual(
            choose_disposition("independent-broker", chain, 0.99),
            REJECT_SOURCE,
        )

    def test_broker_with_an_inspection_never_rises_above_upscreening(self):
        chain = chain_completeness(CHAIN_RECORDS)
        self.assertEqual(
            choose_disposition(
                "independent-broker", chain, 0.99, counterfeit_inspection=True
            ),
            ACCEPT_WITH_FULL_UPSCREENING,
        )

    def test_broken_chain_cannot_reach_directed(self):
        chain = chain_completeness(["maker-lot-record", "project-receipt-record"])
        self.assertEqual(
            choose_disposition("qualified-parts-listing", chain, 0.95),
            ACCEPT_WITH_ADDED_EVALUATION,
        )

    def test_chain_argument_must_be_a_chain_result(self):
        with self.assertRaises(ValueError):
            choose_disposition("preferred-manufacturer", "complete", 0.9)


class AddedEvaluationTests(unittest.TestCase):
    def test_broker_is_told_to_re_source(self):
        chain = chain_completeness(CHAIN_RECORDS)
        actions = added_evaluation("independent-broker", chain, True, 0, 0.0)
        self.assertTrue(any("re-source" in action for action in actions))

    def test_missing_record_has_to_be_recovered(self):
        chain = chain_completeness(["maker-lot-record"])
        actions = added_evaluation("assessed-manufacturer", chain, True, 0, 0.0)
        self.assertTrue(any("recover the" in action for action in actions))

    def test_aged_lot_earns_a_solderability_recheck(self):
        chain = chain_completeness(CHAIN_RECORDS)
        actions = added_evaluation("preferred-manufacturer", chain, True, 0, 0.4)
        self.assertTrue(any("solderability" in action for action in actions))

    def test_strong_source_buys_no_extra_record_work(self):
        chain = chain_completeness(CHAIN_RECORDS)
        actions = added_evaluation("qualified-parts-listing", chain, True, 0, 0.0)
        self.assertEqual(actions, [])


class AssessSourcingTests(unittest.TestCase):
    def test_preferred_case_is_accepted_as_directed(self):
        result = assess_sourcing(GOOD_CASE)
        self.assertEqual(result["disposition"], ACCEPT_AS_DIRECTED)
        self.assertTrue(result["usable"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["index"], 1.0, places=9)
        self.assertAlmostEqual(result["index_gap"], 0.0, places=9)

    def test_broker_case_is_refused_and_unusable(self):
        result = assess_sourcing(_case(GOOD_CASE, source_tier="independent-broker"))
        self.assertEqual(result["disposition"], REJECT_SOURCE)
        self.assertFalse(result["usable"])
        self.assertTrue(any("refused" in f for f in result["findings"]))

    def test_broker_with_an_inspection_is_usable_only_upscreened(self):
        result = assess_sourcing(
            _case(
                GOOD_CASE,
                source_tier="independent-broker",
                counterfeit_inspection=True,
            )
        )
        self.assertEqual(result["disposition"], ACCEPT_WITH_FULL_UPSCREENING)
        self.assertTrue(result["usable"])

    def test_substituted_record_is_reported_not_hidden(self):
        case = _case(
            GOOD_CASE,
            records_held=["maker-lot-record", "project-receipt-record"],
            counterfeit_inspection=True,
        )
        result = assess_sourcing(case)
        self.assertEqual(
            result["chain"]["substituted_record"], "distribution-chain-record"
        )
        self.assertTrue(any("covered at this class" in f for f in result["findings"]))

    def test_index_gap_shows_what_preferred_sourcing_would_earn(self):
        result = assess_sourcing(
            _case(GOOD_CASE, source_tier="franchised-distributor")
        )
        self.assertAlmostEqual(result["directed_index"], 1.0, places=9)
        self.assertGreater(result["index_gap"], 1.0e-6)

    def test_unsubscribed_line_is_a_finding(self):
        result = assess_sourcing(_case(GOOD_CASE, change_notice_subscribed=False))
        self.assertTrue(any("subscription" in f for f in result["findings"]))

    def test_aged_lot_is_a_finding(self):
        result = assess_sourcing(_case(GOOD_CASE, date_code_age_months=60.0))
        self.assertTrue(any("shelf policy" in f for f in result["findings"]))
        self.assertGreater(result["shelf_age_penalty"], 1.0e-6)

    def test_uncategorized_tier_rejected(self):
        with self.assertRaises(ValueError):
            assess_sourcing(_case(GOOD_CASE, source_tier=None))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_sourcing(["qualified-parts-listing"])

    def test_every_tier_is_gradeable(self):
        for tier in SOURCE_TIERS:
            result = assess_sourcing(
                _case(GOOD_CASE, source_tier=tier, counterfeit_inspection=True)
            )
            self.assertIn(result["disposition"], (
                ACCEPT_AS_DIRECTED,
                ACCEPT_WITH_ADDED_EVALUATION,
                ACCEPT_WITH_FULL_UPSCREENING,
            ))


if __name__ == "__main__":
    unittest.main(verbosity=1)
