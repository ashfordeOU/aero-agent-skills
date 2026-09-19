"""Contract tests for the clause 5.8.4 ground network error-rate logic."""

import math
import unittest

from e50_error_rates_logic import (
    COMPLIANT,
    MARGINAL,
    NON_COMPLIANT,
    allocate_segment_error_rate,
    assess_error_rates,
    block_error_rate,
    chain_error_rate,
    errored_second_ratio,
    expected_errored_bits,
    expected_errored_blocks,
    margin_db,
    margin_ratio,
    validate_bits,
    validate_duration,
    validate_margin_factor,
    validate_probability,
)

BER = 1e-9
FRAME_BITS = 8920.0
CHAIN = [1e-7, 2e-7, 3e-7]


class ValidationTests(unittest.TestCase):
    def test_zero_probability_accepted(self):
        self.assertAlmostEqual(validate_probability(0), 0.0, places=9)

    def test_unit_probability_accepted(self):
        self.assertAlmostEqual(validate_probability(1), 1.0, places=9)

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.5)

    def test_negative_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(-1e-12)

    def test_boolean_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(True)

    def test_text_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability("1e-9")

    def test_nan_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(float("nan"))

    def test_zero_bits_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(-1.0)

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_margin_factor(0.5)

    def test_unit_margin_factor_accepted(self):
        self.assertAlmostEqual(validate_margin_factor(1.0), 1.0, places=9)


class BlockErrorRateTests(unittest.TestCase):
    def test_small_ber_over_a_frame_is_near_the_linear_estimate(self):
        self.assertAlmostEqual(
            block_error_rate(BER, FRAME_BITS), BER * FRAME_BITS, places=9
        )

    def test_block_rate_is_below_the_linear_estimate(self):
        big = block_error_rate(1e-3, 1000.0)
        self.assertLess(big, 1e-3 * 1000.0)

    def test_zero_ber_gives_a_clean_block(self):
        self.assertAlmostEqual(block_error_rate(0.0, FRAME_BITS), 0.0, places=9)

    def test_unit_ber_corrupts_every_block(self):
        self.assertAlmostEqual(block_error_rate(1.0, FRAME_BITS), 1.0, places=9)

    def test_single_bit_block_returns_the_bit_rate(self):
        self.assertAlmostEqual(block_error_rate(0.25, 1.0), 0.25, places=9)

    def test_block_rate_never_exceeds_one(self):
        # A million bits at a one-half bit error rate saturates the
        # probability: expm1() of an argument near -7e5 is exactly -1.0 on
        # any IEEE-754 platform, so the block rate IS one.
        self.assertEqual(block_error_rate(0.5, 1e6), 1.0)
        # Away from saturation the ceiling holds with margin.
        self.assertLess(block_error_rate(1e-9, 1e6), 1.0)


class ChainTests(unittest.TestCase):
    def test_chain_is_near_the_sum_for_small_rates(self):
        self.assertAlmostEqual(chain_error_rate(CHAIN), sum(CHAIN), places=9)

    def test_chain_is_below_the_sum(self):
        self.assertLess(chain_error_rate([0.1, 0.1, 0.1]), 0.3)

    def test_single_segment_chain_is_the_segment(self):
        self.assertAlmostEqual(chain_error_rate([3e-7]), 3e-7, places=9)

    def test_a_dead_segment_kills_the_path(self):
        self.assertAlmostEqual(chain_error_rate([1e-9, 1.0]), 1.0, places=9)

    def test_clean_chain_is_clean(self):
        self.assertAlmostEqual(chain_error_rate([0.0, 0.0]), 0.0, places=9)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_error_rate([])

    def test_string_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_error_rate("1e-9")

    def test_bad_member_rejected(self):
        with self.assertRaises(ValueError):
            chain_error_rate([1e-9, 2.0])


class AllocationTests(unittest.TestCase):
    def test_allocation_composes_back_to_the_target(self):
        per = allocate_segment_error_rate(1e-6, 4)
        self.assertAlmostEqual(chain_error_rate([per] * 4), 1e-6, places=9)

    def test_one_segment_takes_the_whole_target(self):
        self.assertAlmostEqual(allocate_segment_error_rate(1e-6, 1), 1e-6, places=9)

    def test_more_segments_ask_more_of_each(self):
        self.assertLess(
            allocate_segment_error_rate(1e-6, 8),
            allocate_segment_error_rate(1e-6, 2),
        )

    def test_zero_target_allocates_zero(self):
        self.assertAlmostEqual(allocate_segment_error_rate(0.0, 5), 0.0, places=9)

    def test_zero_segments_rejected(self):
        with self.assertRaises(ValueError):
            allocate_segment_error_rate(1e-6, 0)

    def test_boolean_segment_count_rejected(self):
        with self.assertRaises(ValueError):
            allocate_segment_error_rate(1e-6, True)


class VolumeTests(unittest.TestCase):
    def test_errored_bits_over_a_pass(self):
        self.assertAlmostEqual(
            expected_errored_bits(1e-6, 1e6, 600.0), 600.0, places=9
        )

    def test_errored_blocks_scale_with_the_count(self):
        one = expected_errored_blocks(BER, FRAME_BITS, 1.0)
        many = expected_errored_blocks(BER, FRAME_BITS, 1000.0)
        self.assertAlmostEqual(many, 1000.0 * one, places=9)

    def test_errored_second_ratio_is_a_probability(self):
        ratio = errored_second_ratio(1e-9, 2e6)
        self.assertGreater(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)

    def test_zero_duration_rejected_for_errored_bits(self):
        with self.assertRaises(ValueError):
            expected_errored_bits(1e-9, 1e6, 0.0)


class MarginTests(unittest.TestCase):
    def test_margin_ratio_of_a_path_exactly_at_its_bound_is_one(self):
        self.assertAlmostEqual(margin_ratio(1e-6, 1e-6), 1.0, places=9)

    def test_margin_db_of_a_path_exactly_at_its_bound_is_zero(self):
        self.assertAlmostEqual(margin_db(1e-6, 1e-6), 0.0, places=9)

    def test_ten_times_better_is_ten_decibels(self):
        self.assertAlmostEqual(margin_db(1e-7, 1e-6), 10.0, places=9)

    def test_error_free_path_has_no_finite_margin(self):
        self.assertIsNone(margin_ratio(0.0, 1e-6))
        self.assertIsNone(margin_db(0.0, 1e-6))

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            margin_ratio(1e-9, 0.0)


class AssessTests(unittest.TestCase):
    def test_path_with_headroom_is_compliant(self):
        result = assess_error_rates([1e-9, 1e-9], 1e-6)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], [])

    def test_path_exactly_on_the_headroom_bound_is_compliant(self):
        result = assess_error_rates([5e-7], 1e-6, margin_factor=2.0)
        self.assertAlmostEqual(
            result["achieved_end_to_end"], result["goal_with_margin"], places=9
        )
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_path_exactly_on_the_requirement_is_marginal(self):
        result = assess_error_rates([1e-6], 1e-6, margin_factor=2.0)
        self.assertEqual(result["verdict"], MARGINAL)

    def test_path_beyond_the_requirement_fails(self):
        result = assess_error_rates([2e-6], 1e-6)
        self.assertEqual(result["verdict"], NON_COMPLIANT)
        self.assertTrue(
            any("does not meet the stated error rate" in f for f in result["findings"])
        )

    def test_failing_path_is_told_the_per_segment_allocation(self):
        result = assess_error_rates([2e-6, 2e-6], 1e-6)
        self.assertTrue(
            any("segments has to hold" in f for f in result["findings"])
        )

    def test_stated_allocation_actually_meets_the_target(self):
        result = assess_error_rates([2e-6, 2e-6], 1e-6)
        fixed = assess_error_rates(
            [result["per_segment_allocation"]] * 2, 1e-6
        )
        self.assertEqual(fixed["verdict"], COMPLIANT)

    def test_worst_segment_is_named(self):
        result = assess_error_rates([1e-9, 4e-7, 2e-9], 1e-6)
        self.assertEqual(result["worst_segment_index"], 1)
        self.assertAlmostEqual(result["worst_segment_rate"], 4e-7, places=9)

    def test_unit_margin_factor_leaves_no_marginal_band(self):
        result = assess_error_rates([1e-6], 1e-6, margin_factor=1.0)
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_volume_figures_appear_when_the_pass_is_given(self):
        result = assess_error_rates(
            [1e-9], 1e-6, block_bits=8920.0, rate_bps=2e6, duration_s=600.0
        )
        self.assertIn("errored_bits_per_pass", result)
        self.assertIn("block_error_rate", result)
        self.assertAlmostEqual(result["errored_bits_per_pass"], 1.2, places=9)

    def test_volume_figures_are_absent_without_a_pass(self):
        self.assertNotIn("errored_bits_per_pass", assess_error_rates([1e-9], 1e-6))

    def test_bad_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_error_rates([1e-9], 2.0)

    def test_bad_margin_factor_rejected(self):
        with self.assertRaises(ValueError):
            assess_error_rates([1e-9], 1e-6, margin_factor=0.0)

    def test_margin_db_is_carried_in_the_result(self):
        result = assess_error_rates([1e-7], 1e-6)
        self.assertAlmostEqual(result["margin_db"], 10.0 * math.log10(10.0), places=9)


if __name__ == "__main__":
    unittest.main()
