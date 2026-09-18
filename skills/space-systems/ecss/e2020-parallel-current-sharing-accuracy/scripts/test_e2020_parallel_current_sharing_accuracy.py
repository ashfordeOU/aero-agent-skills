"""Contract tests for the clause 5.2.12.2.1 paralleled current sharing logic."""

import unittest

from e2020_parallel_current_sharing_accuracy_logic import (
    BRANCH_CURRENT_UNMEASURED,
    BRANCH_HEADROOM_EXHAUSTED,
    BRANCH_SHARE_BALANCED,
    BRANCH_SHARE_HIGH,
    BRANCH_SHARE_STARVED,
    DEFAULT_CURRENT_SHARING_POLICY,
    FOLDBACK_LIMITER,
    HIGH_POWER_LIMITER,
    LATCHING_CURRENT_LIMITER,
    RETRIGGERABLE_LIMITER,
    SHARING_ACCEPTABLE,
    SHARING_BRANCH_WILL_TRIP,
    SHARING_CAPABILITY_SHORT,
    SHARING_IMBALANCE_OUT_OF_BAND,
    SHARING_NOT_MEASURED,
    assess_branch_share,
    assess_current_sharing,
    branch_headroom_fraction,
    categorize_limiter_type,
    equal_share_fraction,
    group_capability_a,
    share_fractions,
    share_imbalance_fraction,
    validate_current_sharing_policy,
    worst_branch_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CURRENT_SHARING_POLICY)
    policy.update(overrides)
    return policy


def _branch(identifier="lcl-a", current=2.0, threshold=3.0, **overrides):
    branch = {
        "id": identifier,
        "limiter_type": LATCHING_CURRENT_LIMITER,
        "branch_current_a": current,
        "trip_threshold_a": threshold,
        "current_measured": True,
    }
    branch.update(overrides)
    return branch


def _group(branches=None, **overrides):
    group = {
        "branches": branches
        if branches is not None
        else [_branch("lcl-a"), _branch("lcl-b")],
        "load_demand_a": 4.0,
    }
    group.update(overrides)
    return group


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_current_sharing_policy(DEFAULT_CURRENT_SHARING_POLICY),
            DEFAULT_CURRENT_SHARING_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_current_sharing_policy("balanced")

    def test_an_imbalance_ceiling_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_current_sharing_policy(_policy(max_share_imbalance_fraction=1.0))

    def test_a_negative_headroom_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_current_sharing_policy(_policy(min_branch_headroom_fraction=-0.05))

    def test_a_starved_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_current_sharing_policy(_policy(min_share_fraction_of_equal=1.5))

    def test_a_starved_floor_of_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_current_sharing_policy(_policy(min_share_fraction_of_equal=0.0))


class LimiterTypeTests(unittest.TestCase):
    def test_a_latching_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type(LATCHING_CURRENT_LIMITER),
            LATCHING_CURRENT_LIMITER,
        )

    def test_a_high_power_limiter_is_governed(self):
        self.assertEqual(
            categorize_limiter_type(" high-power-limiter  "), HIGH_POWER_LIMITER
        )

    def test_a_retriggerable_limiter_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(RETRIGGERABLE_LIMITER)

    def test_a_foldback_device_is_refused(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type(FOLDBACK_LIMITER)

    def test_an_unrecognised_limiter_type_rejected(self):
        with self.assertRaises(ValueError):
            categorize_limiter_type("shunt-regulator")


class ShareArithmeticTests(unittest.TestCase):
    def test_the_equal_share_of_a_pair_is_a_half(self):
        self.assertAlmostEqual(equal_share_fraction(2), 0.5, places=9)

    def test_the_equal_share_of_four_branches_is_a_quarter(self):
        self.assertAlmostEqual(equal_share_fraction(4), 0.25, places=9)

    def test_a_single_branch_has_no_share_to_measure(self):
        with self.assertRaises(ValueError):
            equal_share_fraction(1)

    def test_a_non_integer_member_count_rejected(self):
        with self.assertRaises(ValueError):
            equal_share_fraction(2.0)

    def test_shares_of_an_even_pair_are_halves(self):
        shares = share_fractions([2.0, 2.0])
        self.assertAlmostEqual(shares[0], 0.5, places=9)
        self.assertAlmostEqual(shares[1], 0.5, places=9)

    def test_shares_sum_to_one(self):
        shares = share_fractions([3.0, 1.0, 4.0])
        self.assertAlmostEqual(sum(shares), 1.0, places=9)

    def test_an_idle_group_has_no_share(self):
        with self.assertRaises(ValueError):
            share_fractions([0.0, 0.0])

    def test_a_negative_branch_current_rejected(self):
        with self.assertRaises(ValueError):
            share_fractions([2.0, -1.0])

    def test_a_balanced_pair_has_no_imbalance(self):
        self.assertAlmostEqual(share_imbalance_fraction([2.0, 2.0]), 0.0, places=9)

    def test_imbalance_is_measured_against_the_equal_share(self):
        self.assertAlmostEqual(
            share_imbalance_fraction([2.5, 1.5]), 0.25, places=9
        )

    def test_headroom_is_the_distance_to_the_branch_threshold(self):
        self.assertAlmostEqual(branch_headroom_fraction(4.5, 5.0), 0.1, places=9)

    def test_a_branch_at_its_threshold_has_no_headroom(self):
        self.assertAlmostEqual(branch_headroom_fraction(5.0, 5.0), 0.0, places=9)

    def test_a_zero_threshold_rejected(self):
        with self.assertRaises(ValueError):
            branch_headroom_fraction(1.0, 0.0)


class CapabilityTests(unittest.TestCase):
    def test_capability_is_set_by_the_worst_sharing_branch(self):
        branches = [
            {"share_fraction": 0.75, "trip_threshold_a": 6.0},
            {"share_fraction": 0.25, "trip_threshold_a": 6.0},
        ]
        self.assertAlmostEqual(group_capability_a(branches, 0.0), 8.0, places=9)

    def test_capability_is_derated_by_the_margin(self):
        branches = [
            {"share_fraction": 0.5, "trip_threshold_a": 3.0},
            {"share_fraction": 0.5, "trip_threshold_a": 3.0},
        ]
        self.assertAlmostEqual(group_capability_a(branches, 0.20), 4.8, places=9)

    def test_capability_is_not_the_smallest_threshold(self):
        branches = [
            {"share_fraction": 0.2, "trip_threshold_a": 2.0},
            {"share_fraction": 0.8, "trip_threshold_a": 8.0},
        ]
        self.assertAlmostEqual(group_capability_a(branches, 0.0), 10.0, places=9)

    def test_a_single_branch_has_no_group_capability(self):
        with self.assertRaises(ValueError):
            group_capability_a([{"share_fraction": 1.0, "trip_threshold_a": 3.0}], 0.0)

    def test_a_zero_share_rejected(self):
        branches = [
            {"share_fraction": 0.0, "trip_threshold_a": 3.0},
            {"share_fraction": 1.0, "trip_threshold_a": 3.0},
        ]
        with self.assertRaises(ValueError):
            group_capability_a(branches, 0.0)


class BranchStandingTests(unittest.TestCase):
    def test_an_even_branch_is_balanced(self):
        record = assess_branch_share(_branch("lcl-a"), 0.5, 0.5)
        self.assertEqual(record["standing"], BRANCH_SHARE_BALANCED)
        self.assertEqual(record["gaps"], [])

    def test_a_branch_exactly_on_the_imbalance_ceiling_is_balanced(self):
        record = assess_branch_share(
            _branch("lcl-a", current=2.5, threshold=6.0), 0.625, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_SHARE_BALANCED)

    def test_a_branch_above_the_imbalance_ceiling_takes_too_much(self):
        record = assess_branch_share(
            _branch("lcl-a", current=3.0, threshold=6.0), 0.75, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_SHARE_HIGH)

    def test_a_branch_exactly_on_the_starved_floor_is_balanced(self):
        record = assess_branch_share(
            _branch("lcl-b", current=1.0, threshold=6.0), 0.25, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_SHARE_BALANCED)

    def test_a_branch_below_the_starved_floor_is_starved(self):
        record = assess_branch_share(
            _branch("lcl-b", current=0.8, threshold=6.0), 0.2, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_SHARE_STARVED)

    def test_a_branch_exactly_on_the_headroom_floor_is_kept(self):
        record = assess_branch_share(
            _branch("lcl-a", current=4.5, threshold=5.0), 0.5, 0.5
        )
        self.assertAlmostEqual(record["headroom_fraction"], 0.1, places=9)
        self.assertEqual(record["standing"], BRANCH_SHARE_BALANCED)

    def test_a_branch_below_the_headroom_floor_will_trip(self):
        record = assess_branch_share(
            _branch("lcl-a", current=4.6, threshold=5.0), 0.5, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_HEADROOM_EXHAUSTED)

    def test_an_unmeasured_branch_has_no_share_to_grade(self):
        record = assess_branch_share(
            _branch("lcl-a", current_measured=False), 0.5, 0.5
        )
        self.assertEqual(record["standing"], BRANCH_CURRENT_UNMEASURED)
        self.assertIsNone(record["headroom_fraction"])

    def test_a_branch_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_branch_share(_branch(""), 0.5, 0.5)

    def test_a_branch_with_an_out_of_scope_limiter_rejected(self):
        with self.assertRaises(ValueError):
            assess_branch_share(
                _branch("lcl-a", limiter_type=FOLDBACK_LIMITER), 0.5, 0.5
            )


class GroupAssessmentTests(unittest.TestCase):
    def test_a_balanced_group_is_acceptable(self):
        result = assess_current_sharing(_group())
        self.assertEqual(result["verdict"], SHARING_ACCEPTABLE)
        self.assertAlmostEqual(result["share_imbalance_fraction"], 0.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_demand_exactly_on_the_capability_still_fits(self):
        result = assess_current_sharing(_group(load_demand_a=4.8))
        self.assertAlmostEqual(result["group_capability_a"], 4.8, places=9)
        self.assertTrue(result["capability_covers_demand"])
        self.assertEqual(result["verdict"], SHARING_ACCEPTABLE)

    def test_a_demand_above_the_capability_is_capability_short(self):
        result = assess_current_sharing(_group(load_demand_a=5.2))
        self.assertEqual(result["verdict"], SHARING_CAPABILITY_SHORT)

    def test_an_imbalanced_group_is_out_of_band(self):
        result = assess_current_sharing(
            _group(
                [
                    _branch("lcl-a", current=3.0, threshold=6.0),
                    _branch("lcl-b", current=1.0, threshold=6.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], SHARING_IMBALANCE_OUT_OF_BAND)
        self.assertIn("lcl-a", result["standings"][BRANCH_SHARE_HIGH])

    def test_a_branch_out_of_headroom_outranks_an_imbalance(self):
        result = assess_current_sharing(
            _group(
                [
                    _branch("lcl-a", current=3.0, threshold=3.1),
                    _branch("lcl-b", current=1.0, threshold=6.0),
                ]
            )
        )
        self.assertEqual(result["verdict"], SHARING_BRANCH_WILL_TRIP)

    def test_an_unmeasured_branch_stops_the_group_at_not_measured(self):
        result = assess_current_sharing(
            _group([_branch("lcl-a"), _branch("lcl-b", current_measured=False)])
        )
        self.assertEqual(result["verdict"], SHARING_NOT_MEASURED)
        self.assertIsNone(result["group_capability_a"])

    def test_a_single_branch_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_current_sharing(_group([_branch("lcl-a")]))

    def test_a_duplicate_branch_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_current_sharing(_group([_branch("lcl-a"), _branch("lcl-a")]))

    def test_a_missing_load_demand_rejected(self):
        group = _group()
        del group["load_demand_a"]
        with self.assertRaises(ValueError):
            assess_current_sharing(group)

    def test_findings_name_the_branch_that_produced_them(self):
        result = assess_current_sharing(
            _group(
                [
                    _branch("lcl-x", current=3.2, threshold=6.0),
                    _branch("lcl-y", current=0.8, threshold=6.0),
                ]
            )
        )
        self.assertTrue(result["findings"])
        self.assertTrue(result["findings"][0].startswith("lcl-x:"))

    def test_the_reported_shares_match_the_measured_currents(self):
        result = assess_current_sharing(
            _group(
                [
                    _branch("lcl-a", current=2.5, threshold=6.0),
                    _branch("lcl-b", current=1.5, threshold=6.0),
                ],
                load_demand_a=3.0,
            )
        )
        self.assertAlmostEqual(result["share_fractions"][0], 0.625, places=9)
        self.assertAlmostEqual(result["share_imbalance_fraction"], 0.25, places=9)

    def test_the_worst_branch_standing_is_the_one_reported(self):
        records = [
            assess_branch_share(_branch("lcl-a"), 0.5, 0.5),
            assess_branch_share(
                _branch("lcl-b", current=3.0, threshold=6.0), 0.75, 0.5
            ),
            assess_branch_share(
                _branch("lcl-c", current_measured=False), 0.5, 0.5
            ),
        ]
        self.assertEqual(worst_branch_standing(records), BRANCH_CURRENT_UNMEASURED)

    def test_worst_branch_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_branch_standing([])


if __name__ == "__main__":
    unittest.main()
