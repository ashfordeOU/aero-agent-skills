#!/usr/bin/env python3
"""Gate 3 contract test for e50-downlink-frame-rejection-rate.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_downlink_frame_rejection_rate.py
"""

import math
import unittest

from e50_downlink_frame_rejection_rate_logic import (
    EXCEEDED,
    WITHIN,
    assess_downlink_frame_rejection,
    codeword_failure_probability,
    downlink_frame_rejection_rate,
    frame_rejection_from_codewords,
    frames_lost_per_pass,
    information_bits_lost_per_pass,
    symbol_error_probability,
    validate_count,
    validate_probability,
    within_bound,
)

BER = 1e-3
SYMBOL_BITS = 8
CODEWORD_SYMBOLS = 255
CORRECTABLE_SYMBOLS = 16
INTERLEAVE_DEPTH = 5


def reference_tail(ps, n, t):
    """Independent brute-force binomial tail for cross-checking."""
    return sum(
        math.comb(n, i) * ps ** i * (1.0 - ps) ** (n - i) for i in range(t + 1, n + 1)
    )


class TestValidation(unittest.TestCase):
    def test_a_boolean_is_not_a_probability(self):
        with self.assertRaises(ValueError):
            validate_probability(True, "ber")

    def test_a_bit_error_rate_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            symbol_error_probability(0.0)

    def test_a_fractional_symbol_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_count(255.5, "codeword_symbols")

    def test_an_interleaving_depth_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            frame_rejection_from_codewords(1e-9, 0)


class TestSymbolErrors(unittest.TestCase):
    def test_a_symbol_fails_roughly_eight_times_as_often_as_a_bit(self):
        ps = symbol_error_probability(BER, SYMBOL_BITS)
        self.assertAlmostEqual(ps / (SYMBOL_BITS * BER), 1.0, places=2)

    def test_a_wider_symbol_fails_more_often(self):
        self.assertGreater(
            symbol_error_probability(BER, 16), symbol_error_probability(BER, 8)
        )

    def test_a_one_bit_symbol_is_the_bit_error_rate(self):
        self.assertAlmostEqual(symbol_error_probability(BER, 1), BER, places=15)

    def test_a_very_low_rate_does_not_collapse_to_zero(self):
        ps = symbol_error_probability(1e-12, 8)
        self.assertGreater(ps, 1e-12)
        self.assertAlmostEqual(ps / (8 * 1e-12), 1.0, places=6)


class TestCodewordFailure(unittest.TestCase):
    def test_the_tail_matches_an_independent_brute_force_sum(self):
        for ps in (0.001, 0.01, 0.1):
            with self.subTest(ps=ps):
                got = codeword_failure_probability(
                    ps, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS
                )
                want = reference_tail(ps, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS)
                self.assertAlmostEqual(got / want, 1.0, places=9)

    def test_a_short_codeword_tail_also_matches_brute_force(self):
        got = codeword_failure_probability(0.3, 20, 2)
        self.assertAlmostEqual(got / reference_tail(0.3, 20, 2), 1.0, places=9)

    def test_a_stronger_decoder_never_fails_more_often(self):
        rates = [
            codeword_failure_probability(0.01, CODEWORD_SYMBOLS, t)
            for t in (8, 12, 16, 20)
        ]
        for weaker, stronger in zip(rates, rates[1:]):
            self.assertLess(stronger, weaker)

    def test_a_decoder_stronger_than_the_codeword_never_fails(self):
        self.assertEqual(codeword_failure_probability(0.5, 20, 20), 0.0)

    def test_a_clean_channel_fails_no_codeword(self):
        self.assertEqual(
            codeword_failure_probability(0.0, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS),
            0.0,
        )

    def test_a_deep_tail_stays_a_positive_number(self):
        ps = symbol_error_probability(1e-5, SYMBOL_BITS)
        self.assertGreater(
            codeword_failure_probability(ps, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS),
            0.0,
        )


class TestInterleaving(unittest.TestCase):
    def test_a_frame_is_rejected_about_depth_times_as_often_as_a_codeword(self):
        per_codeword = codeword_failure_probability(
            symbol_error_probability(BER, SYMBOL_BITS),
            CODEWORD_SYMBOLS,
            CORRECTABLE_SYMBOLS,
        )
        frame = frame_rejection_from_codewords(per_codeword, INTERLEAVE_DEPTH)
        self.assertAlmostEqual(frame / (INTERLEAVE_DEPTH * per_codeword), 1.0, places=6)

    def test_one_codeword_per_frame_leaves_the_rate_unchanged(self):
        self.assertAlmostEqual(
            frame_rejection_from_codewords(1e-9, 1), 1e-9, places=15
        )

    def test_a_certain_codeword_failure_rejects_the_frame(self):
        self.assertEqual(frame_rejection_from_codewords(1.0, 5), 1.0)

    def test_the_end_to_end_rate_agrees_with_its_two_steps(self):
        ps = symbol_error_probability(BER, SYMBOL_BITS)
        per_codeword = codeword_failure_probability(
            ps, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS
        )
        self.assertAlmostEqual(
            downlink_frame_rejection_rate(
                BER,
                SYMBOL_BITS,
                CODEWORD_SYMBOLS,
                CORRECTABLE_SYMBOLS,
                INTERLEAVE_DEPTH,
            ),
            frame_rejection_from_codewords(per_codeword, INTERLEAVE_DEPTH),
            places=18,
        )


class TestDataLoss(unittest.TestCase):
    def test_lost_frames_scale_with_the_frames_in_a_pass(self):
        self.assertAlmostEqual(frames_lost_per_pass(1e-4, 20000), 2.0, places=9)

    def test_lost_payload_is_lost_frames_times_the_payload(self):
        self.assertAlmostEqual(
            information_bits_lost_per_pass(1e-4, 20000, 8000), 16000.0, places=6
        )

    def test_a_payload_size_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            information_bits_lost_per_pass(1e-4, 20000, 0)


class TestAssessment(unittest.TestCase):
    def test_a_well_coded_downlink_meets_a_modest_bound(self):
        report = assess_downlink_frame_rejection(
            BER, 1e-6, SYMBOL_BITS, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS,
            INTERLEAVE_DEPTH, 20000, 8000,
        )
        self.assertEqual(report["verdict"], WITHIN)
        self.assertTrue(report["compliant"])

    def test_a_weak_decoder_on_a_noisy_channel_exceeds_the_bound(self):
        report = assess_downlink_frame_rejection(
            1e-2, 1e-6, SYMBOL_BITS, CODEWORD_SYMBOLS, 2, INTERLEAVE_DEPTH
        )
        self.assertEqual(report["verdict"], EXCEEDED)
        self.assertIn("not resent", report["finding"])

    def test_a_rate_on_the_bound_is_graded_within(self):
        rate = downlink_frame_rejection_rate(
            BER, SYMBOL_BITS, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS, INTERLEAVE_DEPTH
        )
        report = assess_downlink_frame_rejection(
            BER, rate, SYMBOL_BITS, CODEWORD_SYMBOLS, CORRECTABLE_SYMBOLS,
            INTERLEAVE_DEPTH,
        )
        self.assertAlmostEqual(report["rejection_rate"], rate, places=18)
        self.assertEqual(report["verdict"], WITHIN)

    def test_the_report_states_the_payload_a_pass_loses(self):
        report = assess_downlink_frame_rejection(
            1e-2, 1.0, SYMBOL_BITS, CODEWORD_SYMBOLS, 2, INTERLEAVE_DEPTH,
            20000, 8000,
        )
        self.assertGreater(report["information_bits_lost_per_pass"], 0.0)
        self.assertAlmostEqual(
            report["information_bits_lost_per_pass"],
            report["frames_lost_per_pass"] * 8000,
            places=6,
        )

    def test_the_report_carries_both_intermediate_figures(self):
        report = assess_downlink_frame_rejection(BER, 1e-6)
        self.assertGreater(report["symbol_error_probability"], 0.0)
        self.assertGreater(report["codeword_failure_probability"], 0.0)
        self.assertGreater(
            report["rejection_rate"], report["codeword_failure_probability"]
        )

    def test_a_bound_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_frame_rejection(BER, 1.5)


class TestBoundComparison(unittest.TestCase):
    def test_a_rate_on_the_bound_is_within_it(self):
        self.assertTrue(within_bound(1e-6, 1e-6))

    def test_a_rate_clearly_over_the_bound_is_not(self):
        self.assertFalse(within_bound(1e-3, 1e-6))


if __name__ == "__main__":
    unittest.main()
