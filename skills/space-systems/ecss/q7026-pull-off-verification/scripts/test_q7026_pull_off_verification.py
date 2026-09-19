#!/usr/bin/env python3
"""Contract test for crimp pull-off verification (offline)."""

import copy
import unittest

from q7026_pull_off_verification_logic import (
    BREAK_CONDUCTOR,
    BREAK_CONTACT,
    BREAK_PULL_OUT,
    LOT_ACCEPT,
    LOT_REJECT,
    LOT_REVIEW,
    escalated_sample_size,
    evaluate_sample_size,
    evaluate_specimen,
    lookup_force,
    required_sample_size,
    validate_force_table,
    validate_sample_plan,
    verify_lot,
)

FORCES = {"22": 67.0, "20": 110.0, "24": 40.0}

PLAN = {
    "tiers": [
        {"up_to": 10, "sample": 2},
        {"up_to": 50, "sample": 5},
        {"up_to": 200, "sample": 8},
    ],
    "fraction_above": 0.05,
    "minimum_above": 8,
}


def _specimen(**overrides):
    specimen = {
        "identifier": "S-001",
        "gauge": "22",
        "force_n": 95.0,
        "break_mode": BREAK_CONDUCTOR,
    }
    specimen.update(overrides)
    return specimen


def _lot(**overrides):
    lot = {
        "force_table": FORCES,
        "sample_plan": copy.deepcopy(PLAN),
        "lot_size": 40,
        "specimens": [
            _specimen(identifier="S-00%d" % n, force_n=90.0 + n) for n in range(1, 6)
        ],
    }
    lot.update(overrides)
    return lot


class ForceTableTests(unittest.TestCase):
    def test_bare_numbers_normalise_to_entries(self):
        table = validate_force_table(FORCES)
        self.assertAlmostEqual(table["22"]["min_pull_off_n"], 67.0, places=9)

    def test_mapping_entries_are_accepted_too(self):
        table = validate_force_table({"22": {"min_pull_off_n": 67.0}})
        self.assertAlmostEqual(table["22"]["min_pull_off_n"], 67.0, places=9)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_force_table({})

    def test_non_positive_minimum_rejected(self):
        with self.assertRaises(ValueError):
            validate_force_table({"22": 0.0})

    def test_untabulated_gauge_is_not_interpolated(self):
        with self.assertRaises(ValueError):
            lookup_force(validate_force_table(FORCES), "21")


class SamplePlanTests(unittest.TestCase):
    def test_valid_plan_normalises(self):
        plan = validate_sample_plan(PLAN)
        self.assertEqual(plan["largest_tier"], 200)
        self.assertEqual(len(plan["tiers"]), 3)

    def test_unordered_tiers_rejected(self):
        bad = {"tiers": [{"up_to": 50, "sample": 5}, {"up_to": 10, "sample": 2}]}
        with self.assertRaises(ValueError):
            validate_sample_plan(bad)

    def test_shrinking_sample_on_a_bigger_lot_rejected(self):
        bad = {"tiers": [{"up_to": 10, "sample": 5}, {"up_to": 50, "sample": 2}]}
        with self.assertRaises(ValueError):
            validate_sample_plan(bad)

    def test_sample_larger_than_the_tier_rejected(self):
        bad = {"tiers": [{"up_to": 10, "sample": 12}]}
        with self.assertRaises(ValueError):
            validate_sample_plan(bad)

    def test_plan_with_no_rule_above_its_tiers_rejected(self):
        bad = {
            "tiers": [{"up_to": 10, "sample": 2}],
            "fraction_above": 0.0,
            "minimum_above": 0,
        }
        with self.assertRaises(ValueError):
            validate_sample_plan(bad)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_plan({"tiers": []})


class RequiredSampleTests(unittest.TestCase):
    def test_small_lot_takes_the_first_tier(self):
        self.assertEqual(required_sample_size(8, PLAN), 2)

    def test_lot_exactly_on_a_tier_boundary_stays_in_that_tier(self):
        self.assertEqual(required_sample_size(50, PLAN), 5)

    def test_lot_one_past_a_boundary_moves_up(self):
        self.assertEqual(required_sample_size(51, PLAN), 8)

    def test_lot_above_the_largest_tier_uses_the_fraction(self):
        self.assertEqual(required_sample_size(400, PLAN), 20)

    def test_fraction_below_the_floor_is_raised_to_it(self):
        self.assertEqual(required_sample_size(220, PLAN), 11)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(1, PLAN), 1)

    def test_zero_lot_size_rejected(self):
        with self.assertRaises(ValueError):
            required_sample_size(0, PLAN)


class SampleSizeTests(unittest.TestCase):
    def test_sufficient_sample_accepts(self):
        result = evaluate_sample_size(40, 5, PLAN)
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["disposition"], LOT_ACCEPT)

    def test_undersized_sample_is_review_not_accept(self):
        result = evaluate_sample_size(40, 3, PLAN)
        self.assertEqual(result["disposition"], LOT_REVIEW)
        self.assertEqual(result["shortfall"], 2)

    def test_coverage_fraction_is_reported(self):
        result = evaluate_sample_size(40, 5, PLAN)
        self.assertAlmostEqual(result["coverage_fraction"], 0.125, places=9)

    def test_more_specimens_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_size(4, 6, PLAN)

    def test_non_integer_tested_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_size(40, 5.0, PLAN)


class SpecimenTests(unittest.TestCase):
    def test_conductor_break_above_the_minimum_accepts(self):
        result = evaluate_specimen(_specimen(), FORCES)
        self.assertEqual(result["disposition"], LOT_ACCEPT)
        self.assertTrue(result["reached_minimum"])

    def test_force_exactly_on_the_minimum_counts_as_reached(self):
        # The representation error that puts 0.1 + 0.2 above 0.3 also
        # reaches a force converted from a load cell reading.
        edge = 67.0 + (0.1 + 0.2 - 0.3)
        result = evaluate_specimen(_specimen(force_n=edge), FORCES)
        self.assertTrue(result["reached_minimum"])
        self.assertEqual(result["disposition"], LOT_ACCEPT)

    def test_force_below_the_minimum_rejects(self):
        result = evaluate_specimen(_specimen(force_n=50.0), FORCES)
        self.assertEqual(result["disposition"], LOT_REJECT)

    def test_pull_out_below_the_minimum_names_both_findings(self):
        result = evaluate_specimen(
            _specimen(force_n=50.0, break_mode=BREAK_PULL_OUT), FORCES
        )
        self.assertEqual(result["disposition"], LOT_REJECT)
        self.assertEqual(len(result["findings"]), 2)

    def test_pull_out_above_the_minimum_is_still_review(self):
        result = evaluate_specimen(
            _specimen(force_n=95.0, break_mode=BREAK_PULL_OUT), FORCES
        )
        self.assertEqual(result["disposition"], LOT_REVIEW)

    def test_contact_failure_says_nothing_about_the_crimp(self):
        result = evaluate_specimen(
            _specimen(force_n=95.0, break_mode=BREAK_CONTACT), FORCES
        )
        self.assertEqual(result["disposition"], LOT_REVIEW)

    def test_minimum_moves_with_the_gauge(self):
        result = evaluate_specimen(_specimen(gauge="20", force_n=95.0), FORCES)
        self.assertEqual(result["disposition"], LOT_REJECT)

    def test_margin_fraction_is_reported(self):
        result = evaluate_specimen(_specimen(gauge="24", force_n=80.0), FORCES)
        self.assertAlmostEqual(result["margin_fraction"], 1.0, places=9)

    def test_unknown_break_mode_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen(_specimen(break_mode="snapped"), FORCES)

    def test_non_mapping_specimen_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_specimen("pulled to 95 N", FORCES)


class EscalationTests(unittest.TestCase):
    def test_no_failure_keeps_the_base_rate(self):
        self.assertEqual(escalated_sample_size(40, PLAN, 0), 5)

    def test_one_failure_doubles_the_rate(self):
        self.assertEqual(escalated_sample_size(40, PLAN, 1), 10)

    def test_two_failures_take_the_whole_lot(self):
        self.assertEqual(escalated_sample_size(40, PLAN, 2), 40)

    def test_doubling_never_exceeds_the_lot(self):
        self.assertEqual(escalated_sample_size(8, PLAN, 1), 4)


class VerifyLotTests(unittest.TestCase):
    def test_clean_lot_accepts(self):
        result = verify_lot(_lot())
        self.assertEqual(result["disposition"], LOT_ACCEPT)
        self.assertFalse(result["escalated"])
        self.assertEqual(result["next_lot_sample_size"], 5)

    def test_undersized_sample_blocks_acceptance_even_when_all_passed(self):
        lot = _lot(specimens=[_specimen(), _specimen(identifier="S-002")])
        result = verify_lot(lot)
        self.assertEqual(result["disposition"], LOT_REVIEW)
        self.assertTrue(any(f.startswith("sampling:") for f in result["findings"]))

    def test_one_failing_specimen_rejects_and_escalates(self):
        specimens = [
            _specimen(identifier="S-00%d" % n, force_n=90.0 + n) for n in range(1, 5)
        ]
        specimens.append(_specimen(identifier="S-005", force_n=40.0))
        result = verify_lot(_lot(specimens=specimens))
        self.assertEqual(result["disposition"], LOT_REJECT)
        self.assertEqual(result["failed_specimens"], ["S-005"])
        self.assertEqual(result["next_lot_sample_size"], 10)

    def test_two_failures_escalate_to_the_whole_lot(self):
        specimens = [
            _specimen(identifier="S-00%d" % n, force_n=90.0 + n) for n in range(1, 4)
        ]
        specimens.append(_specimen(identifier="S-004", force_n=40.0))
        specimens.append(_specimen(identifier="S-005", force_n=41.0))
        result = verify_lot(_lot(specimens=specimens))
        self.assertEqual(result["next_lot_sample_size"], 40)

    def test_pull_out_specimens_are_counted_separately(self):
        specimens = [
            _specimen(identifier="S-00%d" % n, force_n=90.0 + n) for n in range(1, 5)
        ]
        specimens.append(
            _specimen(identifier="S-005", force_n=95.0, break_mode=BREAK_PULL_OUT)
        )
        result = verify_lot(_lot(specimens=specimens))
        self.assertEqual(result["pull_out_count"], 1)
        self.assertEqual(result["inconclusive_specimens"], ["S-005"])
        self.assertEqual(result["disposition"], LOT_REVIEW)

    def test_force_statistics_are_reported(self):
        result = verify_lot(_lot())
        self.assertAlmostEqual(result["min_force_n"], 91.0, places=9)
        self.assertAlmostEqual(result["mean_force_n"], 93.0, places=9)

    def test_empty_specimen_set_rejected(self):
        with self.assertRaises(ValueError):
            verify_lot(_lot(specimens=[]))

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            verify_lot("a pulled lot")


if __name__ == "__main__":
    unittest.main()
