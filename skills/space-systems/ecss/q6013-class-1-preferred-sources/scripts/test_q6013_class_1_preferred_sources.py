#!/usr/bin/env python3
"""Contract test for the Class 1 preferred-source decision (offline)."""

import copy
import unittest

from q6013_class_1_preferred_sources_logic import (
    ACCEPT_AS_PREFERRED,
    ACCEPT_WITH_ADDED_EVALUATION,
    ACCEPT_WITH_FULL_UPSCREENING,
    DEFAULT_SOURCING_POLICY,
    DISPOSITIONS,
    REJECT_SOURCE,
    SOURCE_TIERS,
    TRACEABILITY_RECORDS,
    added_evaluation_tasks,
    disposition_for,
    evaluate_source,
    line_stability_factor,
    shelf_age_penalty,
    sourcing_assurance_index,
    tier_assurance,
    traceability_completeness,
    validate_sourcing_policy,
)

PREFERRED_CASE = {
    "source_tier": "preferred-parts-listing",
    "traceability_records": TRACEABILITY_RECORDS,
    "change_notice_subscription": True,
    "line_changes_since_evidence": 0,
    "lot_date_code_age_months": 6.0,
}

BROKER_CASE = {
    "source_tier": "independent-broker",
    "traceability_records": ("project-receipt-record",),
    "change_notice_subscription": False,
    "line_changes_since_evidence": 2,
    "lot_date_code_age_months": 40.0,
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_sourcing_policy(DEFAULT_SOURCING_POLICY), DEFAULT_SOURCING_POLICY
        )

    def test_policy_covers_every_source_tier(self):
        for tier in SOURCE_TIERS:
            self.assertIn(tier, DEFAULT_SOURCING_POLICY["tier_assurance"])

    def test_policy_weights_sum_to_one(self):
        weights = DEFAULT_SOURCING_POLICY["weights"]
        total = weights["tier"] + weights["traceability"] + weights["line_stability"]
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_sourcing_policy("default")

    def test_policy_missing_a_tier_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOURCING_POLICY)
        del broken["tier_assurance"]["assessed-manufacturer"]
        with self.assertRaises(ValueError):
            validate_sourcing_policy(broken)

    def test_policy_with_unbalanced_weights_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOURCING_POLICY)
        broken["weights"]["tier"] = 0.9
        with self.assertRaises(ValueError):
            validate_sourcing_policy(broken)

    def test_policy_thresholds_must_descend(self):
        broken = copy.deepcopy(DEFAULT_SOURCING_POLICY)
        broken["added_evaluation_threshold"] = 0.95
        with self.assertRaises(ValueError):
            validate_sourcing_policy(broken)

    def test_policy_with_unknown_banned_tier_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOURCING_POLICY)
        broken["banned_tiers"] = ("grey-market",)
        with self.assertRaises(ValueError):
            validate_sourcing_policy(broken)


class TierTests(unittest.TestCase):
    def test_listing_tier_earns_full_credit(self):
        self.assertAlmostEqual(tier_assurance("preferred-parts-listing"), 1.0, places=9)

    def test_broker_tier_earns_no_credit(self):
        self.assertAlmostEqual(tier_assurance("independent-broker"), 0.0, places=9)

    def test_tier_credit_never_rises_down_the_ladder(self):
        values = [tier_assurance(tier) for tier in SOURCE_TIERS]
        for stronger, weaker in zip(values, values[1:]):
            self.assertGreater(stronger, weaker)

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            tier_assurance("auction-lot")


class TraceabilityTests(unittest.TestCase):
    def test_full_chain_is_unbroken(self):
        chain = traceability_completeness(TRACEABILITY_RECORDS)
        self.assertTrue(chain["unbroken"])
        self.assertAlmostEqual(chain["completeness"], 1.0, places=9)

    def test_partial_chain_names_the_gaps(self):
        chain = traceability_completeness(("project-receipt-record",))
        self.assertFalse(chain["unbroken"])
        self.assertIn("manufacturer-lot-record", chain["gaps"])
        self.assertIn("distribution-chain-record", chain["gaps"])

    def test_repeated_record_counted_once(self):
        chain = traceability_completeness(
            ("project-receipt-record", "project-receipt-record")
        )
        self.assertAlmostEqual(chain["completeness"], 1.0 / 3.0, places=9)

    def test_unknown_record_rejected(self):
        with self.assertRaises(ValueError):
            traceability_completeness(("broker-invoice",))

    def test_bare_string_rejected_as_record_sequence(self):
        with self.assertRaises(ValueError):
            traceability_completeness("project-receipt-record")


class ShelfAndStabilityTests(unittest.TestCase):
    def test_fresh_lot_carries_no_penalty(self):
        self.assertAlmostEqual(shelf_age_penalty(0.0), 0.0, places=9)

    def test_age_exactly_on_the_shelf_limit_carries_no_penalty(self):
        limit = DEFAULT_SOURCING_POLICY["shelf_limit_months"]
        self.assertAlmostEqual(shelf_age_penalty(limit), 0.0, places=9)

    def test_representation_error_at_the_shelf_limit_is_absorbed(self):
        limit = DEFAULT_SOURCING_POLICY["shelf_limit_months"]
        drifted = limit + limit * 2.0e-16
        self.assertAlmostEqual(shelf_age_penalty(drifted), 0.0, places=9)

    def test_penalty_saturates_at_one(self):
        self.assertAlmostEqual(shelf_age_penalty(500.0), 1.0, places=9)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            shelf_age_penalty(-1.0)

    def test_subscribed_stable_line_keeps_full_credit(self):
        self.assertAlmostEqual(line_stability_factor(True, 0, 0.0), 1.0, places=9)

    def test_missing_subscription_cuts_stability(self):
        self.assertAlmostEqual(line_stability_factor(False, 0, 0.0), 0.6, places=9)

    def test_line_changes_cut_stability_further(self):
        self.assertAlmostEqual(line_stability_factor(True, 2, 0.0), 0.5, places=9)

    def test_non_boolean_subscription_rejected(self):
        with self.assertRaises(ValueError):
            line_stability_factor("yes", 0, 0.0)

    def test_fractional_line_change_count_rejected(self):
        with self.assertRaises(ValueError):
            line_stability_factor(True, 1.5, 0.0)


class IndexTests(unittest.TestCase):
    def test_perfect_preferred_case_scores_one(self):
        scored = sourcing_assurance_index(
            _case(PREFERRED_CASE, lot_date_code_age_months=0.0)
        )
        self.assertAlmostEqual(scored["index"], 1.0, places=9)

    def test_index_stays_inside_the_unit_interval(self):
        for tier in SOURCE_TIERS:
            scored = sourcing_assurance_index(_case(PREFERRED_CASE, source_tier=tier))
            self.assertGreaterEqual(scored["index"], 0.0)
            self.assertLessEqual(scored["index"], 1.0)

    def test_weaker_tier_scores_lower(self):
        strong = sourcing_assurance_index(PREFERRED_CASE)["index"]
        weak = sourcing_assurance_index(
            _case(PREFERRED_CASE, source_tier="franchised-distributor")
        )["index"]
        self.assertGreater(strong - weak, 1.0e-6)

    def test_broken_chain_scores_lower(self):
        whole = sourcing_assurance_index(PREFERRED_CASE)["index"]
        broken = sourcing_assurance_index(
            _case(PREFERRED_CASE, traceability_records=("project-receipt-record",))
        )["index"]
        self.assertGreater(whole - broken, 1.0e-6)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            sourcing_assurance_index(["preferred-parts-listing"])


class DispositionTests(unittest.TestCase):
    def test_index_exactly_on_the_preferred_threshold_accepts_as_preferred(self):
        threshold = DEFAULT_SOURCING_POLICY["preferred_threshold"]
        self.assertEqual(
            disposition_for(threshold, "preferred-manufacturer", True),
            ACCEPT_AS_PREFERRED,
        )

    def test_representation_error_at_the_threshold_is_absorbed(self):
        threshold = DEFAULT_SOURCING_POLICY["preferred_threshold"]
        drifted = threshold - threshold * 2.0e-16
        self.assertEqual(
            disposition_for(drifted, "preferred-manufacturer", True),
            ACCEPT_AS_PREFERRED,
        )

    def test_broken_chain_blocks_the_preferred_disposition(self):
        self.assertEqual(
            disposition_for(0.99, "preferred-parts-listing", False),
            ACCEPT_WITH_ADDED_EVALUATION,
        )

    def test_banned_tier_is_rejected_at_any_index(self):
        self.assertEqual(
            disposition_for(1.0, "independent-broker", True), REJECT_SOURCE
        )

    def test_index_below_the_upscreening_floor_is_rejected(self):
        self.assertEqual(
            disposition_for(0.20, "assessed-manufacturer", True), REJECT_SOURCE
        )

    def test_index_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            disposition_for(1.4, "preferred-manufacturer", True)


class EvaluateSourceTests(unittest.TestCase):
    def test_listing_sourced_part_is_accepted_as_preferred(self):
        result = evaluate_source(_case(PREFERRED_CASE, lot_date_code_age_months=0.0))
        self.assertEqual(result["disposition"], ACCEPT_AS_PREFERRED)
        self.assertEqual(result["findings"], [])

    def test_broker_sourced_part_is_rejected_with_a_resource_task(self):
        result = evaluate_source(BROKER_CASE)
        self.assertEqual(result["disposition"], REJECT_SOURCE)
        self.assertIn("re-source through an authorised channel", result["added_evaluation_tasks"])

    def test_distributor_sourced_part_needs_full_upscreening(self):
        result = evaluate_source(
            _case(PREFERRED_CASE, source_tier="franchised-distributor")
        )
        self.assertEqual(result["disposition"], ACCEPT_WITH_FULL_UPSCREENING)

    def test_assessed_maker_lands_on_added_evaluation(self):
        result = evaluate_source(
            _case(
                PREFERRED_CASE,
                source_tier="assessed-manufacturer",
                lot_date_code_age_months=0.0,
            )
        )
        self.assertEqual(result["disposition"], ACCEPT_WITH_ADDED_EVALUATION)

    def test_every_disposition_is_a_known_token(self):
        for tier in SOURCE_TIERS:
            result = evaluate_source(_case(PREFERRED_CASE, source_tier=tier))
            self.assertIn(result["disposition"], DISPOSITIONS)

    def test_gap_to_preferred_sourcing_is_zero_for_the_best_case(self):
        result = evaluate_source(_case(PREFERRED_CASE, lot_date_code_age_months=0.0))
        self.assertAlmostEqual(result["index_gap_to_preferred_sourcing"], 0.0, places=9)

    def test_gap_to_preferred_sourcing_is_positive_for_a_weak_case(self):
        result = evaluate_source(
            _case(PREFERRED_CASE, source_tier="assessed-manufacturer")
        )
        self.assertGreater(result["index_gap_to_preferred_sourcing"], 1.0e-6)

    def test_aged_lot_raises_a_solderability_task_and_a_finding(self):
        result = evaluate_source(_case(PREFERRED_CASE, lot_date_code_age_months=40.0))
        self.assertIn(
            "re-verify solderability on the aged date code",
            result["added_evaluation_tasks"],
        )
        self.assertTrue(any("shelf policy" in f for f in result["findings"]))

    def test_missing_chain_record_is_reported_as_a_finding(self):
        result = evaluate_source(
            _case(PREFERRED_CASE, traceability_records=("project-receipt-record",))
        )
        self.assertTrue(any("traceability chain is broken" in f for f in result["findings"]))

    def test_unknown_tier_in_a_case_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_source(_case(PREFERRED_CASE, source_tier="surplus-stock"))

    def test_added_evaluation_tasks_is_empty_for_the_best_case(self):
        tasks = added_evaluation_tasks(_case(PREFERRED_CASE, lot_date_code_age_months=0.0))
        self.assertEqual(tasks, [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
