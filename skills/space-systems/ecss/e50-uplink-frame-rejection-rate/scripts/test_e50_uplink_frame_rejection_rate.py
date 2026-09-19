#!/usr/bin/env python3
"""Gate 3 contract test for e50-uplink-frame-rejection-rate.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_uplink_frame_rejection_rate.py
"""

import unittest

from e50_uplink_frame_rejection_rate_logic import (
    ERROR_CORRECTING,
    EXCEEDED,
    SUMMATION_GUARD,
    UNCODED,
    WITHIN,
    assess_uplink_frame_rejection,
    binomial_tail_probability,
    coding_scheme,
    expected_rejections,
    frame_bits,
    frame_rejection_rate,
    retransmission_overhead,
    uncoded_frame_error_probability,
    validate_bound,
    validate_count,
    validate_probability,
    within_bound,
)

BER = 1e-6
INFORMATION_BITS = 8000
OVERHEAD_BITS = 192
TOTAL_BITS = INFORMATION_BITS + OVERHEAD_BITS


class TestValidation(unittest.TestCase):
    def test_a_boolean_is_not_a_probability(self):
        with self.assertRaises(ValueError):
            validate_probability(True, "ber")

    def test_a_probability_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_probability(1.0, "ber")

    def test_a_negative_probability_is_refused(self):
        with self.assertRaises(ValueError):
            validate_probability(-1e-6, "ber")

    def test_a_bound_may_sit_at_zero(self):
        self.assertEqual(validate_bound(0.0, "bound"), 0.0)

    def test_a_bound_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bound(1.5, "bound")

    def test_a_fractional_bit_count_is_refused(self):
        with self.assertRaises(ValueError):
            validate_count(8192.5, "total_bits")

    def test_overhead_bits_may_be_zero_but_information_bits_may_not(self):
        self.assertEqual(frame_bits(100, 0), 100)
        with self.assertRaises(ValueError):
            frame_bits(0, 16)


class TestUncodedRate(unittest.TestCase):
    def test_the_uncoded_rate_matches_the_tail_with_no_correction(self):
        self.assertAlmostEqual(
            uncoded_frame_error_probability(BER, TOTAL_BITS),
            binomial_tail_probability(BER, TOTAL_BITS, 0),
            places=15,
        )

    def test_a_longer_frame_is_rejected_more_often(self):
        short = uncoded_frame_error_probability(BER, 1024)
        long = uncoded_frame_error_probability(BER, 8192)
        self.assertGreater(long, short * 7.0)

    def test_the_rate_stays_a_probability_at_a_punishing_bit_error_rate(self):
        rate = uncoded_frame_error_probability(0.4, 8192)
        # -expm1(8192 * log1p(-0.4)) has an argument near -4184, where the
        # exponential underflows, so the rate saturates: it IS exactly one
        # here, on any libm, rather than sitting a hair under the bound.
        # assertEqual states that contract; it also implies the > 0.999
        # this case used to check.
        self.assertEqual(rate, 1.0)

    def test_a_very_low_bit_error_rate_does_not_collapse_to_zero(self):
        rate = uncoded_frame_error_probability(1e-12, 1024)
        self.assertGreater(rate, 1e-10)
        self.assertAlmostEqual(rate / (1024 * 1e-12), 1.0, places=6)


class TestCodedRate(unittest.TestCase):
    def test_correcting_one_bit_cuts_the_rate_by_orders_not_by_half(self):
        uncoded = frame_rejection_rate(BER, TOTAL_BITS, 0)
        corrected = frame_rejection_rate(BER, TOTAL_BITS, 1)
        self.assertLess(corrected, uncoded / 100.0)

    def test_a_stronger_decoder_never_rejects_more(self):
        rates = [frame_rejection_rate(BER, TOTAL_BITS, t) for t in range(0, 5)]
        for weaker, stronger in zip(rates, rates[1:]):
            self.assertLess(stronger, weaker)

    def test_a_deep_tail_is_still_a_positive_number(self):
        self.assertGreater(frame_rejection_rate(BER, TOTAL_BITS, 10), 0.0)

    def test_a_decoder_stronger_than_the_frame_never_rejects(self):
        self.assertEqual(binomial_tail_probability(BER, 100, 100), 0.0)

    def test_a_decoder_strength_past_the_summation_guard_is_refused(self):
        with self.assertRaises(ValueError):
            binomial_tail_probability(0.9, 100000, SUMMATION_GUARD + 1)

    def test_a_noisy_channel_with_a_weak_decoder_still_rejects_most_frames(self):
        self.assertGreater(frame_rejection_rate(0.01, 1024, 5), 0.9)

    def test_the_scheme_is_named_from_the_correctable_bit_count(self):
        self.assertEqual(coding_scheme(0), UNCODED)
        self.assertEqual(coding_scheme(3), ERROR_CORRECTING)


class TestOperationalConsequence(unittest.TestCase):
    def test_expected_rejections_scale_with_the_frames_in_a_pass(self):
        rate = frame_rejection_rate(BER, TOTAL_BITS)
        self.assertAlmostEqual(
            expected_rejections(rate, 4000), rate * 4000, places=12
        )

    def test_a_clean_link_costs_about_one_transmission_per_frame(self):
        self.assertAlmostEqual(retransmission_overhead(1e-9), 1.0, places=8)

    def test_a_rejection_rate_of_one_never_delivers(self):
        with self.assertRaises(ValueError):
            retransmission_overhead(1.0)

    def test_half_the_frames_rejected_doubles_the_transmissions(self):
        self.assertAlmostEqual(retransmission_overhead(0.5), 2.0, places=12)


class TestBoundComparison(unittest.TestCase):
    def test_a_rate_on_the_bound_is_within_it(self):
        self.assertTrue(within_bound(1e-5, 1e-5))

    def test_a_rate_clearly_over_the_bound_is_not_within_it(self):
        self.assertFalse(within_bound(1e-4, 1e-6))


class TestAssessment(unittest.TestCase):
    def test_a_compliant_uplink_is_graded_within_bound(self):
        report = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-2, 0, 4000
        )
        self.assertEqual(report["verdict"], WITHIN)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["frame_bits"], TOTAL_BITS)

    def test_a_tight_bound_on_an_uncoded_frame_is_exceeded(self):
        report = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-6
        )
        self.assertEqual(report["verdict"], EXCEEDED)
        self.assertFalse(report["compliant"])
        self.assertIn("exceeds", report["finding"])

    def test_adding_a_decoder_brings_the_same_link_inside_the_bound(self):
        uncoded = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-6, 0
        )
        coded = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-6, 2
        )
        self.assertFalse(uncoded["compliant"])
        self.assertTrue(coded["compliant"])
        self.assertEqual(coded["coding"], ERROR_CORRECTING)

    def test_the_report_names_the_pass_level_consequence(self):
        report = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-2, 0, 4000
        )
        self.assertAlmostEqual(
            report["expected_rejections_per_pass"],
            report["rejection_rate"] * 4000,
            places=12,
        )
        self.assertGreater(report["mean_transmissions_per_delivered_frame"], 1.0)

    def test_the_report_carries_the_assumption_it_was_derived_from(self):
        report = assess_uplink_frame_rejection(
            BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-2
        )
        self.assertAlmostEqual(report["assumed_ber"], BER, places=15)

    def test_a_frame_count_of_zero_is_refused(self):
        with self.assertRaises(ValueError):
            assess_uplink_frame_rejection(
                BER, INFORMATION_BITS, OVERHEAD_BITS, 1e-2, 0, 0
            )


if __name__ == "__main__":
    unittest.main()
