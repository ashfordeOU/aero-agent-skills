"""Contract tests for the clause 5.6.13.3 sequence identifier logic."""

import unittest

from e50_sequence_identifier_logic import (
    AMBIGUOUS,
    GO_BACK_N,
    SELECTIVE_REPEAT,
    UNAMBIGUOUS,
    assess_sequence_identifier,
    bandwidth_delay_window,
    identifier_space,
    replay_identifier_trace,
    required_identifier_bits,
    unambiguous_window,
    validate_bits,
    validate_count,
    validate_positive_number,
    validate_scheme,
    wrap_time_s,
)

RATE = 1000000.0
UNIT = 8192.0
TRIP = 0.6


class ValidationTests(unittest.TestCase):
    def test_bit_width_accepted(self):
        self.assertEqual(validate_bits(8), 8)

    def test_zero_bit_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(0)

    def test_boolean_bit_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(True)

    def test_float_bit_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(8.0)

    def test_absurd_bit_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(128)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_number(-1.0, "rate_bps")

    def test_infinite_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_number(float("inf"), "rate_bps")

    def test_unknown_scheme_rejected(self):
        with self.assertRaises(ValueError):
            validate_scheme("stop-and-wait")

    def test_known_scheme_accepted(self):
        self.assertEqual(validate_scheme(SELECTIVE_REPEAT), SELECTIVE_REPEAT)


class SpaceTests(unittest.TestCase):
    def test_space_is_a_power_of_two(self):
        self.assertEqual(identifier_space(8), 256)

    def test_one_bit_gives_two_identifiers(self):
        self.assertEqual(identifier_space(1), 2)

    def test_go_back_n_leaves_one_spare(self):
        self.assertEqual(unambiguous_window(8, GO_BACK_N), 255)

    def test_selective_repeat_leaves_half_spare(self):
        self.assertEqual(unambiguous_window(8, SELECTIVE_REPEAT), 128)

    def test_selective_repeat_window_is_never_more_than_go_back_n(self):
        for bits in range(1, 17):
            self.assertLessEqual(
                unambiguous_window(bits, SELECTIVE_REPEAT),
                unambiguous_window(bits, GO_BACK_N),
            )


class RequiredWidthTests(unittest.TestCase):
    def test_exact_power_of_two_window_under_selective_repeat(self):
        self.assertEqual(required_identifier_bits(128, SELECTIVE_REPEAT), 8)

    def test_one_unit_beyond_a_power_of_two_needs_another_bit(self):
        self.assertEqual(required_identifier_bits(129, SELECTIVE_REPEAT), 9)

    def test_go_back_n_fits_one_more_than_selective_repeat_boundary(self):
        self.assertEqual(required_identifier_bits(255, GO_BACK_N), 8)

    def test_go_back_n_full_space_needs_another_bit(self):
        self.assertEqual(required_identifier_bits(256, GO_BACK_N), 9)

    def test_required_width_actually_holds_the_window(self):
        for window in (1, 2, 3, 17, 100, 1000):
            bits = required_identifier_bits(window, SELECTIVE_REPEAT)
            self.assertGreaterEqual(unambiguous_window(bits, SELECTIVE_REPEAT), window)

    def test_required_width_is_minimal(self):
        for window in (2, 3, 17, 100, 1000):
            bits = required_identifier_bits(window, SELECTIVE_REPEAT)
            if bits > 1:
                self.assertLess(unambiguous_window(bits - 1, SELECTIVE_REPEAT), window)


class BandwidthDelayTests(unittest.TestCase):
    def test_window_covers_the_round_trip(self):
        self.assertEqual(bandwidth_delay_window(8192.0, 8192.0, 4.0), 4)

    def test_partial_unit_rounds_up(self):
        self.assertEqual(bandwidth_delay_window(8192.0, 8192.0, 4.5), 5)

    def test_zero_round_trip_rejected(self):
        with self.assertRaises(ValueError):
            bandwidth_delay_window(RATE, UNIT, 0.0)


class WrapTests(unittest.TestCase):
    def test_wrap_time_is_the_space_over_the_unit_rate(self):
        self.assertAlmostEqual(wrap_time_s(8, 8192.0, 8192.0), 256.0, places=9)

    def test_wider_field_wraps_later(self):
        self.assertAlmostEqual(
            wrap_time_s(9, RATE, UNIT), 2.0 * wrap_time_s(8, RATE, UNIT), places=9
        )

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            wrap_time_s(8, 0.0, UNIT)


class TraceReplayTests(unittest.TestCase):
    def test_clean_run_reports_nothing(self):
        result = replay_identifier_trace([0, 1, 2, 3], 4)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["repeated"], [])
        self.assertEqual(result["out_of_order"], [])
        self.assertTrue(result["complete"])

    def test_gap_is_reported_as_missing(self):
        result = replay_identifier_trace([0, 1, 3, 4], 4)
        self.assertEqual(result["missing"], [2])

    def test_repeat_is_reported(self):
        result = replay_identifier_trace([0, 1, 1, 2], 4)
        self.assertEqual(result["repeated"], [1])

    def test_reordering_is_not_reported_as_loss(self):
        result = replay_identifier_trace([0, 2, 1, 3], 4)
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["out_of_order"], [2])

    def test_next_expected_advances_past_a_filled_gap(self):
        result = replay_identifier_trace([0, 2, 1, 3], 4)
        self.assertEqual(result["next_expected"], 4 % identifier_space(4))

    def test_identifier_outside_the_space_rejected(self):
        with self.assertRaises(ValueError):
            replay_identifier_trace([0, 1, 16], 4)

    def test_non_integer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            replay_identifier_trace([0, "1"], 4)

    def test_trace_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            replay_identifier_trace(3, 4)

    def test_first_expected_outside_the_space_rejected(self):
        with self.assertRaises(ValueError):
            replay_identifier_trace([0], 4, first_expected=99)

    def test_replay_can_start_away_from_zero(self):
        result = replay_identifier_trace([5, 6, 8], 4, first_expected=5)
        self.assertEqual(result["missing"], [7])


class AssessTests(unittest.TestCase):
    def test_adequate_design_is_unambiguous(self):
        result = assess_sequence_identifier(10, SELECTIVE_REPEAT, 128, RATE, UNIT, TRIP, 5.0)
        self.assertEqual(result["verdict"], UNAMBIGUOUS)
        self.assertEqual(result["findings"], [])

    def test_window_beyond_the_space_is_ambiguous(self):
        result = assess_sequence_identifier(6, SELECTIVE_REPEAT, 100, RATE, UNIT, TRIP, 1.0)
        self.assertEqual(result["verdict"], AMBIGUOUS)
        self.assertFalse(result["window_fits"])

    def test_window_exactly_at_the_bound_fits(self):
        result = assess_sequence_identifier(8, SELECTIVE_REPEAT, 128, RATE, UNIT, TRIP, 1.0)
        self.assertTrue(result["window_fits"])

    def test_overlarge_window_reports_the_width_that_carries_it(self):
        result = assess_sequence_identifier(6, SELECTIVE_REPEAT, 100, RATE, UNIT, TRIP, 1.0)
        self.assertEqual(result["required_identifier_bits"], 8)
        self.assertTrue(any("identifier bits carry it" in f for f in result["findings"]))

    def test_recommended_width_actually_clears_the_finding(self):
        result = assess_sequence_identifier(6, SELECTIVE_REPEAT, 100, RATE, UNIT, TRIP, 1.0)
        fixed = assess_sequence_identifier(
            result["required_identifier_bits"], SELECTIVE_REPEAT, 100, RATE, UNIT, TRIP, 1.0
        )
        self.assertTrue(fixed["window_fits"])

    def test_window_below_the_bandwidth_delay_product_is_reported(self):
        result = assess_sequence_identifier(10, SELECTIVE_REPEAT, 2, RATE, UNIT, 10.0, 1.0)
        self.assertTrue(any("bandwidth-delay product" in f for f in result["findings"]))

    def test_wrap_inside_the_accepted_latency_is_ambiguous(self):
        result = assess_sequence_identifier(3, GO_BACK_N, 4, RATE, UNIT, 0.01, 3600.0)
        self.assertFalse(result["wrap_clear_of_latency"])
        self.assertEqual(result["verdict"], AMBIGUOUS)

    def test_wrap_exactly_at_the_latency_is_clear(self):
        wrap = wrap_time_s(8, 8192.0, 8192.0)
        result = assess_sequence_identifier(8, GO_BACK_N, 4, 8192.0, 8192.0, 1.0, wrap)
        self.assertAlmostEqual(result["wrap_time_s"], wrap, places=9)
        self.assertTrue(result["wrap_clear_of_latency"])

    def test_bad_scheme_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_sequence_identifier(8, "stop-and-wait", 4, RATE, UNIT, TRIP, 1.0)

    def test_bad_latency_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_sequence_identifier(8, GO_BACK_N, 4, RATE, UNIT, TRIP, 0.0)


if __name__ == "__main__":
    unittest.main()
