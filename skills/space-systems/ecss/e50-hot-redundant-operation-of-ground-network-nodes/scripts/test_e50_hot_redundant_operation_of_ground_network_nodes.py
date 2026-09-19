"""Contract tests for the clause 5.8.5 hot redundant node logic."""

import unittest

from e50_hot_redundant_operation_of_ground_network_nodes_logic import (
    GAP_EXCEEDED,
    HOT_COMPLIANT,
    INSUFFICIENT_REDUNDANCY,
    NOT_HOT,
    SECONDS_PER_YEAR,
    assess_hot_redundancy,
    combined_availability,
    gap_unavailability,
    is_hot_transition,
    k_of_n_availability,
    maximum_tolerable_gap_s,
    minimum_hot_nodes,
    outage_seconds_per_period,
    service_gap_s,
    validate_availability,
    validate_node_count,
    validate_non_negative,
    validate_positive,
)

NODE_A = 0.99
HOUR = 3600.0


class ValidationTests(unittest.TestCase):
    def test_zero_availability_accepted(self):
        self.assertAlmostEqual(validate_availability(0), 0.0, places=9)

    def test_full_availability_accepted(self):
        self.assertAlmostEqual(validate_availability(1), 1.0, places=9)

    def test_availability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability(1.000001)

    def test_boolean_availability_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability(True)

    def test_text_availability_rejected(self):
        with self.assertRaises(ValueError):
            validate_availability("0.99")

    def test_infinite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(float("inf"))

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-0.1)

    def test_zero_rejected_where_positive_required(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0)

    def test_zero_node_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_count(0)

    def test_float_node_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_count(2.0)


class RedundancyTests(unittest.TestCase):
    def test_one_of_one_is_the_node(self):
        self.assertAlmostEqual(k_of_n_availability(NODE_A, 1, 1), NODE_A, places=9)

    def test_one_of_two_beats_one_of_one(self):
        self.assertAlmostEqual(
            k_of_n_availability(NODE_A, 2, 1), 1.0 - (1.0 - NODE_A) ** 2, places=9
        )

    def test_two_of_two_is_the_product(self):
        self.assertAlmostEqual(
            k_of_n_availability(NODE_A, 2, 2), NODE_A * NODE_A, places=9
        )

    def test_adding_a_hot_node_never_hurts(self):
        self.assertGreater(
            k_of_n_availability(NODE_A, 3, 1), k_of_n_availability(NODE_A, 2, 1)
        )

    def test_two_of_three_is_the_binomial_tail(self):
        expected = 3.0 * NODE_A ** 2 * (1.0 - NODE_A) + NODE_A ** 3
        self.assertAlmostEqual(k_of_n_availability(NODE_A, 3, 2), expected, places=9)

    def test_perfect_nodes_give_perfect_service(self):
        self.assertAlmostEqual(k_of_n_availability(1.0, 3, 2), 1.0, places=9)

    def test_dead_nodes_give_no_service(self):
        self.assertAlmostEqual(k_of_n_availability(0.0, 3, 1), 0.0, places=9)

    def test_requiring_more_than_exist_rejected(self):
        with self.assertRaises(ValueError):
            k_of_n_availability(NODE_A, 2, 3)


class GapTests(unittest.TestCase):
    def test_hot_gap_is_detection_plus_switchover(self):
        self.assertAlmostEqual(service_gap_s(2.0, 3.0), 5.0, places=9)

    def test_startup_and_recovery_add_to_the_gap(self):
        self.assertAlmostEqual(service_gap_s(2.0, 3.0, 60.0, 30.0), 95.0, places=9)

    def test_a_running_in_state_spare_is_hot(self):
        self.assertTrue(is_hot_transition(0.0, 0.0))

    def test_a_spare_that_has_to_start_is_not_hot(self):
        self.assertFalse(is_hot_transition(60.0, 0.0))

    def test_a_spare_that_has_to_catch_up_is_not_hot(self):
        self.assertFalse(is_hot_transition(0.0, 30.0))

    def test_negative_gap_component_rejected(self):
        with self.assertRaises(ValueError):
            service_gap_s(-1.0, 3.0)


class DowntimeTests(unittest.TestCase):
    def test_gap_unavailability_is_lost_over_period(self):
        self.assertAlmostEqual(
            gap_unavailability(36.0, 10.0, 3600.0), 0.1, places=9
        )

    def test_a_gap_longer_than_the_period_is_total_loss(self):
        self.assertAlmostEqual(gap_unavailability(7200.0, 1.0, 3600.0), 1.0, places=9)

    def test_no_failures_cost_nothing(self):
        self.assertAlmostEqual(gap_unavailability(36.0, 0.0, 3600.0), 0.0, places=9)

    def test_combined_availability_charges_the_gap(self):
        self.assertAlmostEqual(combined_availability(0.5, 0.5), 0.25, places=9)

    def test_outage_seconds_follow_the_availability(self):
        self.assertAlmostEqual(
            outage_seconds_per_period(0.99, 100.0), 1.0, places=9
        )

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            gap_unavailability(1.0, 1.0, 0.0)


class SizingTests(unittest.TestCase):
    def test_minimum_nodes_reaches_the_target(self):
        n = minimum_hot_nodes(0.9, 1, 0.999)
        self.assertEqual(n, 3)
        # The binomial sum is built from ** (libm pow), which is not
        # correctly rounded, so the three-node figure can land a unit in
        # the last place either side of the 0.999 target. Judge it to
        # 1e-9 relative: nine significant figures is far finer than any
        # availability is ever quoted to and far coarser than the
        # last-place spread. The target itself stays at 0.999.
        self.assertGreaterEqual(
            k_of_n_availability(0.9, n, 1), 0.999 * (1.0 - 1e-9)
        )
        # One node fewer genuinely misses, by orders more than rounding.
        self.assertLess(k_of_n_availability(0.9, n - 1, 1), 0.999)

    def test_a_target_at_the_single_node_value_needs_one_node(self):
        self.assertEqual(minimum_hot_nodes(0.9, 1, 0.9), 1)

    def test_an_unreachable_target_returns_none(self):
        self.assertIsNone(minimum_hot_nodes(0.9, 1, 1.0, ceiling=4))

    def test_maximum_gap_is_none_when_redundancy_already_misses(self):
        self.assertIsNone(maximum_tolerable_gap_s(0.999, 0.99, 1.0, HOUR))

    def test_maximum_gap_is_zero_at_an_exact_match(self):
        self.assertAlmostEqual(
            maximum_tolerable_gap_s(0.99, 0.99, 1.0, HOUR), 0.0, places=9
        )

    def test_maximum_gap_scales_with_the_slack(self):
        gap = maximum_tolerable_gap_s(0.5, 1.0, 1.0, 100.0)
        self.assertAlmostEqual(gap, 50.0, places=9)


class AssessTests(unittest.TestCase):
    def test_a_hot_pair_inside_its_gap_is_compliant(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 1.0, 2.0, max_gap_s=5.0, target_availability=0.99
        )
        self.assertEqual(result["verdict"], HOT_COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_a_gap_exactly_on_its_allowance_still_passes(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 2.0, 3.0, max_gap_s=5.0, target_availability=0.99
        )
        self.assertAlmostEqual(result["service_gap_s"], result["max_gap_s"], places=9)
        self.assertEqual(result["verdict"], HOT_COMPLIANT)

    def test_a_longer_gap_is_reported(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 5.0, 5.0, max_gap_s=5.0, target_availability=0.9
        )
        self.assertEqual(result["verdict"], GAP_EXCEEDED)
        self.assertTrue(any("switchover costs" in f for f in result["findings"]))

    def test_a_standby_spare_is_not_hot(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 1.0, 2.0, startup_s=120.0, max_gap_s=600.0
        )
        self.assertEqual(result["verdict"], NOT_HOT)
        self.assertFalse(result["hot"])
        self.assertTrue(any("standby node" in f for f in result["findings"]))

    def test_a_state_recovering_spare_is_not_hot(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 1.0, 2.0, state_recovery_s=45.0, max_gap_s=600.0
        )
        self.assertEqual(result["verdict"], NOT_HOT)

    def test_a_single_node_has_no_spare(self):
        result = assess_hot_redundancy(0.99, 1, 1, 1.0, 1.0, max_gap_s=5.0)
        self.assertEqual(result["verdict"], INSUFFICIENT_REDUNDANCY)
        self.assertTrue(any("no spare" in f for f in result["findings"]))

    def test_a_missed_target_names_the_node_count_that_meets_it(self):
        result = assess_hot_redundancy(
            0.9, 2, 1, 1.0, 1.0, max_gap_s=60.0, target_availability=0.999
        )
        self.assertEqual(result["verdict"], INSUFFICIENT_REDUNDANCY)
        self.assertTrue(any("hot node(s) would carry" in f for f in result["findings"]))

    def test_the_named_node_count_actually_meets_the_target(self):
        result = assess_hot_redundancy(
            0.9, 2, 1, 1.0, 1.0, max_gap_s=60.0, target_availability=0.999
        )
        fixed = assess_hot_redundancy(
            0.9,
            result["minimum_hot_nodes"],
            1,
            1.0,
            1.0,
            max_gap_s=60.0,
            target_availability=0.999,
        )
        self.assertEqual(fixed["verdict"], HOT_COMPLIANT)

    def test_a_target_no_node_count_can_reach_is_named_as_such(self):
        result = assess_hot_redundancy(
            0.99,
            2,
            1,
            10.0,
            10.0,
            max_gap_s=60.0,
            target_availability=0.999,
            failures_per_period=100.0,
            period_s=3600.0,
        )
        self.assertIsNone(result["minimum_hot_nodes"])
        self.assertTrue(any("has to improve" in f for f in result["findings"]))

    def test_the_gap_alone_can_make_a_target_unreachable(self):
        self.assertIsNone(minimum_hot_nodes(0.99, 1, 0.9, gap_unavailability_value=0.5))

    def test_charging_the_gap_asks_for_more_nodes(self):
        bare = minimum_hot_nodes(0.9, 1, 0.99)
        charged = minimum_hot_nodes(0.9, 1, 0.99, gap_unavailability_value=0.005)
        self.assertGreater(charged, bare)

    def test_outage_seconds_are_carried_in_the_result(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 1.0, 2.0, max_gap_s=5.0, target_availability=0.99
        )
        self.assertGreater(result["outage_seconds_per_period"], 0.0)
        self.assertLess(result["outage_seconds_per_period"], SECONDS_PER_YEAR)

    def test_maximum_tolerable_gap_is_carried_when_a_target_is_set(self):
        result = assess_hot_redundancy(
            0.99, 2, 1, 1.0, 2.0, max_gap_s=5.0, target_availability=0.99
        )
        self.assertIsNotNone(result["maximum_tolerable_gap_s"])

    def test_maximum_tolerable_gap_is_absent_without_a_target(self):
        result = assess_hot_redundancy(0.99, 2, 1, 1.0, 2.0, max_gap_s=5.0)
        self.assertIsNone(result["maximum_tolerable_gap_s"])

    def test_bad_node_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(0.99, 0, 1, 1.0, 1.0)

    def test_bad_gap_allowance_rejected(self):
        with self.assertRaises(ValueError):
            assess_hot_redundancy(0.99, 2, 1, 1.0, 1.0, max_gap_s=-1.0)


if __name__ == "__main__":
    unittest.main()
