"""Contract tests for the clause 5.7.1.5 on-board network medium access logic."""

import unittest

from e50_on_board_network_medium_access_logic import (
    BOUNDED,
    BUDGET_EXCEEDED,
    OVERSUBSCRIBED,
    UNBOUNDED,
    assess_medium_access,
    fixed_priority_access_delay_s,
    frame_time_s,
    medium_utilisation,
    tdma_access_delay_s,
    tdma_slot_time_s,
    token_access_delay_s,
    token_rotation_time_s,
    validate_nodes,
    validate_nonnegative,
    validate_positive,
    validate_scheme,
)

RATE = 1.0e6
TOKEN_PASS = 1.0e-5
BLOCKING = 1000.0
NODES = [
    {"name": "obc", "frame_bits": 1000.0, "period_s": 0.01},
    {"name": "star-tracker", "frame_bits": 500.0, "period_s": 0.02},
    {"name": "reaction-wheel", "frame_bits": 800.0, "period_s": 0.04},
]
SATURATED = [
    {"name": "obc-bulk", "frame_bits": 9000.0, "period_s": 0.01},
    {"name": "nav-fix", "frame_bits": 2000.0, "period_s": 0.01},
    {"name": "low-rate-hk", "frame_bits": 500.0, "period_s": 0.1},
]


class ValidationTests(unittest.TestCase):
    def test_unknown_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_scheme("best-effort")

    def test_non_string_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_scheme(3)

    def test_scheme_case_is_normalised(self):
        self.assertEqual(validate_scheme("  Time-Slotted "), "time-slotted")

    def test_nodes_none_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes(None)

    def test_empty_node_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes([])

    def test_duplicate_node_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes([
                {"name": "obc", "frame_bits": 100.0, "period_s": 0.1},
                {"name": "obc", "frame_bits": 200.0, "period_s": 0.1},
            ])

    def test_missing_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes([{"name": "obc", "frame_bits": 100.0}])

    def test_zero_frame_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes([{"name": "obc", "frame_bits": 0.0, "period_s": 0.1}])

    def test_blank_node_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_nodes([{"name": "", "frame_bits": 100.0, "period_s": 0.1}])

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "rate_bps")

    def test_negative_guard_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1.0e-9, "guard_s")


class FrameAndLoadTests(unittest.TestCase):
    def test_frame_time_carries_overhead_and_guard(self):
        self.assertAlmostEqual(
            frame_time_s(1000.0, RATE, 96.0, 1.0e-5), 0.001106, places=12
        )

    def test_bare_frame_time_is_bits_over_rate(self):
        self.assertAlmostEqual(frame_time_s(1000.0, RATE), 0.001, places=12)

    def test_utilisation_sums_every_node(self):
        self.assertAlmostEqual(medium_utilisation(NODES, RATE), 0.145, places=12)

    def test_overhead_raises_utilisation(self):
        bare = medium_utilisation(NODES, RATE)
        framed = medium_utilisation(NODES, RATE, 96.0)
        self.assertGreater(framed, bare)


class TimeSlottedTests(unittest.TestCase):
    def test_slot_is_sized_on_the_longest_frame(self):
        self.assertAlmostEqual(tdma_slot_time_s(NODES, RATE), 0.001, places=12)

    def test_three_nodes_wait_two_slots(self):
        self.assertAlmostEqual(tdma_access_delay_s(3, 0.001), 0.002, places=12)

    def test_a_lone_node_waits_for_nobody(self):
        self.assertAlmostEqual(tdma_access_delay_s(1, 0.001), 0.0, places=12)

    def test_zero_node_count_rejected(self):
        with self.assertRaises(ValueError):
            tdma_access_delay_s(0, 0.001)


class TokenTests(unittest.TestCase):
    def test_rotation_adds_holding_times_and_token_passes(self):
        self.assertAlmostEqual(
            token_rotation_time_s(NODES, RATE, TOKEN_PASS), 0.00233, places=12
        )

    def test_a_node_waits_a_rotation_less_its_own_turn(self):
        self.assertAlmostEqual(
            token_access_delay_s("obc", NODES, RATE, TOKEN_PASS), 0.00133, places=12
        )

    def test_the_shortest_frame_waits_longest(self):
        big = token_access_delay_s("obc", NODES, RATE, TOKEN_PASS)
        small = token_access_delay_s("star-tracker", NODES, RATE, TOKEN_PASS)
        self.assertAlmostEqual(small, 0.00183, places=12)
        self.assertGreater(small, big)

    def test_unknown_node_rejected_by_token_delay(self):
        with self.assertRaises(ValueError):
            token_access_delay_s("gyro", NODES, RATE, TOKEN_PASS)


class FixedPriorityTests(unittest.TestCase):
    def test_top_priority_waits_only_for_the_blocking_frame(self):
        self.assertAlmostEqual(
            fixed_priority_access_delay_s("obc", NODES, RATE, BLOCKING),
            0.001,
            places=12,
        )

    def test_second_priority_adds_one_higher_frame(self):
        self.assertAlmostEqual(
            fixed_priority_access_delay_s("star-tracker", NODES, RATE, BLOCKING),
            0.002,
            places=12,
        )

    def test_lowest_priority_adds_every_higher_frame(self):
        self.assertAlmostEqual(
            fixed_priority_access_delay_s("reaction-wheel", NODES, RATE, BLOCKING),
            0.0025,
            places=12,
        )

    def test_saturating_higher_priority_admits_no_bound(self):
        self.assertIsNone(
            fixed_priority_access_delay_s("low-rate-hk", SATURATED, RATE, BLOCKING)
        )

    def test_unknown_node_rejected_by_priority_delay(self):
        with self.assertRaises(ValueError):
            fixed_priority_access_delay_s("gyro", NODES, RATE, BLOCKING)


class AssessTests(unittest.TestCase):
    def test_time_slotted_medium_is_bounded(self):
        result = assess_medium_access("time-slotted", NODES, RATE)
        self.assertEqual(result["verdict"], BOUNDED)
        self.assertAlmostEqual(result["worst_access_delay_s"], 0.002, places=12)

    def test_token_medium_reports_its_rotation(self):
        result = assess_medium_access("token", NODES, RATE, TOKEN_PASS)
        self.assertEqual(result["verdict"], BOUNDED)
        self.assertAlmostEqual(result["token_rotation_s"], 0.00233, places=12)

    def test_fixed_priority_worst_node_is_the_lowest_priority(self):
        result = assess_medium_access("fixed-priority", NODES, RATE, 0.0, BLOCKING)
        self.assertEqual(result["worst_node"], "reaction-wheel")
        self.assertEqual(result["verdict"], BOUNDED)

    def test_contention_gives_no_bound_at_all(self):
        result = assess_medium_access("contention", NODES, RATE)
        self.assertEqual(result["verdict"], UNBOUNDED)
        self.assertFalse(result["bounded"])

    def test_saturated_medium_under_a_round_is_oversubscribed(self):
        result = assess_medium_access("time-slotted", SATURATED, RATE)
        self.assertEqual(result["verdict"], OVERSUBSCRIBED)

    def test_starved_node_is_named_before_the_load_verdict(self):
        result = assess_medium_access("fixed-priority", SATURATED, RATE, 0.0, BLOCKING)
        self.assertEqual(result["verdict"], UNBOUNDED)
        self.assertTrue(any("low-rate-hk" in f for f in result["findings"]))

    def test_budget_exactly_at_the_worst_delay_passes(self):
        result = assess_medium_access(
            "fixed-priority", NODES, RATE, 0.0, BLOCKING, 0.0, 0.0, 0.0025
        )
        self.assertEqual(result["verdict"], BOUNDED)

    def test_budget_below_the_worst_delay_is_reported(self):
        result = assess_medium_access(
            "fixed-priority", NODES, RATE, 0.0, BLOCKING, 0.0, 0.0, 0.002
        )
        self.assertEqual(result["verdict"], BUDGET_EXCEEDED)
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_missing_blocking_frame_is_flagged(self):
        result = assess_medium_access("fixed-priority", NODES, RATE)
        self.assertTrue(
            any("no blocking frame was declared" in f for f in result["findings"])
        )

    def test_every_node_gets_a_delay_entry(self):
        result = assess_medium_access("token", NODES, RATE, TOKEN_PASS)
        self.assertEqual(
            sorted(result["access_delay_s"]),
            ["obc", "reaction-wheel", "star-tracker"],
        )

    def test_bad_rate_rejected(self):
        with self.assertRaises(ValueError):
            assess_medium_access("token", NODES, 0.0, TOKEN_PASS)


if __name__ == "__main__":
    unittest.main()
