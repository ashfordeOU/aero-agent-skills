"""Contract tests for the clause 5.7.1.4 asynchronous data transfer logic."""

import unittest

from e50_asynchronous_data_transfers_logic import (
    ACCOMMODATED,
    NO_SPARE_WINDOW,
    SEGMENTATION_REQUIRED,
    STARVED,
    assess_asynchronous_transfers,
    required_link_rate_bps,
    required_spare_time_s,
    segments_required,
    spare_window_s,
    sustained_capacity_bps,
    transfer_completion_s,
    validate_nonnegative,
    validate_positive,
    validate_reservation,
    window_capacity_bits,
    worst_case_start_delay_s,
)

CYCLE = 0.1
RESERVED = 0.02
RATE = 1.0e6
BIG_MESSAGE = 200000.0
SMALL_MESSAGE = 40000.0


class ValidationTests(unittest.TestCase):
    def test_zero_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "cycle_s")

    def test_negative_reservation_rejected(self):
        with self.assertRaises(ValueError):
            validate_reservation(-1.0e-6, CYCLE)

    def test_reservation_longer_than_the_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_reservation(0.11, CYCLE)

    def test_reservation_equal_to_the_cycle_accepted(self):
        self.assertAlmostEqual(validate_reservation(CYCLE, CYCLE), CYCLE, places=12)

    def test_boolean_reservation_rejected(self):
        with self.assertRaises(ValueError):
            validate_reservation(True, CYCLE)

    def test_text_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive("1e6", "rate_bps")

    def test_nan_cycle_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(float("nan"), "cycle_s")

    def test_zero_message_rejected(self):
        with self.assertRaises(ValueError):
            segments_required(0.0, 80000.0)

    def test_negative_overhead_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1.0, "overhead_bits")


class WindowTests(unittest.TestCase):
    def test_spare_is_the_cycle_less_the_reservation(self):
        self.assertAlmostEqual(spare_window_s(CYCLE, RESERVED), 0.08, places=12)

    def test_capacity_is_the_window_at_the_link_rate(self):
        self.assertAlmostEqual(window_capacity_bits(0.08, RATE), 80000.0, places=9)

    def test_sustained_capacity_is_the_window_per_cycle(self):
        self.assertAlmostEqual(
            sustained_capacity_bps(80000.0, CYCLE), 800000.0, places=9
        )

    def test_a_fully_reserved_cycle_leaves_no_window(self):
        self.assertAlmostEqual(spare_window_s(CYCLE, CYCLE), 0.0, places=12)


class SegmentTests(unittest.TestCase):
    def test_message_inside_one_window_needs_one_segment(self):
        self.assertEqual(segments_required(SMALL_MESSAGE, 80000.0), 1)

    def test_message_exactly_filling_a_window_needs_one_segment(self):
        self.assertEqual(segments_required(80000.0, 80000.0), 1)

    def test_message_over_two_and_a_half_windows_needs_three(self):
        self.assertEqual(segments_required(BIG_MESSAGE, 80000.0), 3)

    def test_no_window_means_no_segmentation_can_help(self):
        self.assertIsNone(segments_required(BIG_MESSAGE, 0.0))


class TimingTests(unittest.TestCase):
    def test_start_delay_is_the_synchronous_block(self):
        self.assertAlmostEqual(
            worst_case_start_delay_s(CYCLE, RESERVED), RESERVED, places=12
        )

    def test_segmented_transfer_finishes_in_the_third_cycle(self):
        self.assertAlmostEqual(
            transfer_completion_s(BIG_MESSAGE, RATE, CYCLE, RESERVED), 0.26, places=12
        )

    def test_single_window_transfer_finishes_inside_its_cycle(self):
        self.assertAlmostEqual(
            transfer_completion_s(80000.0, RATE, CYCLE, RESERVED), 0.1, places=12
        )

    def test_no_window_means_the_transfer_never_finishes(self):
        self.assertIsNone(transfer_completion_s(BIG_MESSAGE, RATE, CYCLE, CYCLE))

    def test_a_heavier_reservation_pushes_completion_out(self):
        light = transfer_completion_s(BIG_MESSAGE, RATE, CYCLE, 0.02)
        heavy = transfer_completion_s(BIG_MESSAGE, RATE, CYCLE, 0.05)
        self.assertAlmostEqual(heavy, 0.4, places=12)
        self.assertGreater(heavy, light)


class InverseTests(unittest.TestCase):
    def test_required_spare_time_is_the_airtime(self):
        self.assertAlmostEqual(
            required_spare_time_s(BIG_MESSAGE, RATE), 0.2, places=12
        )

    def test_required_link_rate_delivers_inside_one_window(self):
        needed = required_link_rate_bps(BIG_MESSAGE, 0.08)
        self.assertAlmostEqual(needed, 2500000.0, places=6)
        self.assertEqual(
            segments_required(BIG_MESSAGE, window_capacity_bits(0.08, needed)), 1
        )

    def test_no_window_admits_no_link_rate(self):
        self.assertIsNone(required_link_rate_bps(BIG_MESSAGE, 0.0))


class AssessTests(unittest.TestCase):
    def test_small_transfer_is_accommodated(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, SMALL_MESSAGE, 0.0, 500000.0
        )
        self.assertEqual(result["verdict"], ACCOMMODATED)
        self.assertTrue(result["fits_one_window"])

    def test_large_transfer_needs_segmentation(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, BIG_MESSAGE, 0.0, 500000.0
        )
        self.assertEqual(result["verdict"], SEGMENTATION_REQUIRED)
        self.assertEqual(result["segments_required"], 3)

    def test_segmentation_names_both_ways_out(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, BIG_MESSAGE, 0.0, 500000.0
        )
        self.assertTrue(
            any("or a link rate of at least" in f for f in result["findings"])
        )

    def test_offered_rate_above_capacity_starves(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, SMALL_MESSAGE, 0.0, 900000.0
        )
        self.assertEqual(result["verdict"], STARVED)

    def test_offered_rate_exactly_at_capacity_is_accommodated(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, SMALL_MESSAGE, 0.0, 800000.0
        )
        self.assertEqual(result["verdict"], ACCOMMODATED)

    def test_fully_reserved_cycle_leaves_nothing(self):
        result = assess_asynchronous_transfers(CYCLE, CYCLE, RATE, SMALL_MESSAGE)
        self.assertEqual(result["verdict"], NO_SPARE_WINDOW)
        self.assertIsNone(result["completion_s"])

    def test_no_window_outranks_a_throughput_shortfall(self):
        result = assess_asynchronous_transfers(
            CYCLE, CYCLE, RATE, SMALL_MESSAGE, 0.0, 900000.0
        )
        self.assertEqual(result["verdict"], NO_SPARE_WINDOW)

    def test_undeclared_offered_rate_is_flagged(self):
        result = assess_asynchronous_transfers(CYCLE, RESERVED, RATE, SMALL_MESSAGE)
        self.assertTrue(
            any("no offered asynchronous rate" in f for f in result["findings"])
        )

    def test_overhead_counts_towards_the_message(self):
        result = assess_asynchronous_transfers(
            CYCLE, RESERVED, RATE, SMALL_MESSAGE, 160.0, 500000.0
        )
        self.assertAlmostEqual(result["message_bits"], 40160.0, places=9)

    def test_bad_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            assess_asynchronous_transfers(CYCLE, RESERVED, 0.0, SMALL_MESSAGE)

    def test_reservation_beyond_the_cycle_rejected(self):
        with self.assertRaises(ValueError):
            assess_asynchronous_transfers(CYCLE, 0.2, RATE, SMALL_MESSAGE)


if __name__ == "__main__":
    unittest.main()
