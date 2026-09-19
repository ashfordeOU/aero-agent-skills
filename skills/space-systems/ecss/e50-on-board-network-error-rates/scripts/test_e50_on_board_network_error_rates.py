"""Contract tests for the clause 5.7.1.8 on-board network error-rate logic."""

import unittest

from e50_on_board_network_error_rates_logic import (
    BER_EXCEEDED,
    RESIDUAL_EXCEEDED,
    WITHIN_BUDGET,
    assess_error_rates,
    errored_frames_per_second,
    frame_error_rate,
    frames_per_second,
    mean_time_between_errored_frames_s,
    required_bit_error_rate,
    residual_undetected_error_rate,
    undetected_errors_in,
    validate_bit_count,
    validate_positive,
    validate_probability,
)

BER = 1.0e-9
FRAME_BITS = 1024
RATE = 1.0e7
FCS = 32
MISSION = 1.0e7
NOMINAL_FER = 1.0239994762241786e-06
NOMINAL_FPS = 9765.625
NOMINAL_RESIDUAL = 2.3841845715050086e-16


class ValidationTests(unittest.TestCase):
    def test_negative_bit_error_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(-1.0e-12, "ber")

    def test_bit_error_rate_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.0000001, "ber")

    def test_boolean_bit_error_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(False, "ber")

    def test_text_bit_error_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability("1e-9", "ber")

    def test_nan_bit_error_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(float("nan"), "ber")

    def test_zero_frame_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(0, "frame_bits")

    def test_fractional_frame_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(1024.5, "frame_bits")

    def test_negative_check_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(-1, "fcs_bits", minimum=0)

    def test_absent_check_sequence_accepted(self):
        self.assertEqual(validate_bit_count(0, "fcs_bits", minimum=0), 0)

    def test_zero_link_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "rate_bps")


class FrameErrorRateTests(unittest.TestCase):
    def test_an_error_free_channel_damages_no_frames(self):
        self.assertAlmostEqual(frame_error_rate(0.0, FRAME_BITS), 0.0, places=12)

    def test_a_certainly_wrong_bit_damages_every_frame(self):
        self.assertAlmostEqual(frame_error_rate(1.0, FRAME_BITS), 1.0, places=12)

    def test_a_one_bit_frame_fails_at_the_bit_error_rate(self):
        self.assertAlmostEqual(frame_error_rate(BER, 1) / BER, 1.0, places=12)

    def test_a_long_frame_is_close_to_the_naive_product(self):
        naive = FRAME_BITS * BER
        self.assertAlmostEqual(frame_error_rate(BER, FRAME_BITS) / naive, 1.0, places=5)

    def test_the_nominal_frame_error_rate(self):
        self.assertAlmostEqual(
            frame_error_rate(BER, FRAME_BITS) / NOMINAL_FER, 1.0, places=12
        )

    def test_a_longer_frame_is_damaged_more_often(self):
        short = frame_error_rate(BER, FRAME_BITS)
        long_frame = frame_error_rate(BER, 2 * FRAME_BITS)
        self.assertGreater(long_frame, short)


class ThroughputTests(unittest.TestCase):
    def test_frames_a_second_at_the_link_rate(self):
        self.assertAlmostEqual(
            frames_per_second(RATE, FRAME_BITS), NOMINAL_FPS, places=9
        )

    def test_damaged_frames_a_second(self):
        self.assertAlmostEqual(
            errored_frames_per_second(NOMINAL_FER, NOMINAL_FPS),
            0.009999994885001744,
            places=12,
        )

    def test_a_fractional_frame_length_is_rejected_by_the_frame_rate(self):
        with self.assertRaises(ValueError):
            frames_per_second(RATE, 1024.0)


class MeanTimeTests(unittest.TestCase):
    def test_mean_time_is_the_reciprocal_of_the_errored_rate(self):
        mtbe = mean_time_between_errored_frames_s(NOMINAL_FER, NOMINAL_FPS)
        self.assertAlmostEqual(mtbe / 100.00005115000873, 1.0, places=12)

    def test_an_error_free_channel_has_no_mean_time(self):
        self.assertIsNone(mean_time_between_errored_frames_s(0.0, NOMINAL_FPS))

    def test_a_silent_link_has_no_mean_time(self):
        self.assertIsNone(mean_time_between_errored_frames_s(NOMINAL_FER, 0.0))


class ResidualTests(unittest.TestCase):
    def test_residual_is_the_frame_error_rate_scaled_by_the_check_width(self):
        self.assertAlmostEqual(
            residual_undetected_error_rate(NOMINAL_FER, FCS) / NOMINAL_RESIDUAL,
            1.0,
            places=12,
        )

    def test_no_check_sequence_catches_nothing(self):
        self.assertAlmostEqual(
            residual_undetected_error_rate(NOMINAL_FER, 0) / NOMINAL_FER, 1.0, places=12
        )

    def test_one_more_check_bit_halves_the_residual(self):
        wide = residual_undetected_error_rate(NOMINAL_FER, FCS + 1)
        narrow = residual_undetected_error_rate(NOMINAL_FER, FCS)
        self.assertAlmostEqual(narrow / wide, 2.0, places=12)

    def test_an_error_free_channel_leaves_no_residual(self):
        self.assertAlmostEqual(
            residual_undetected_error_rate(0.0, FCS), 0.0, places=12
        )


class ExposureTests(unittest.TestCase):
    def test_mission_exposure_scales_the_residual(self):
        exposure = undetected_errors_in(MISSION, NOMINAL_RESIDUAL, NOMINAL_FPS)
        self.assertAlmostEqual(exposure / 2.32830524561036e-05, 1.0, places=12)

    def test_no_mission_time_means_no_exposure(self):
        self.assertAlmostEqual(
            undetected_errors_in(0.0, NOMINAL_RESIDUAL, NOMINAL_FPS), 0.0, places=12
        )


class InverseTests(unittest.TestCase):
    def test_the_required_bit_error_rate_round_trips(self):
        recovered = required_bit_error_rate(
            frame_error_rate(BER, FRAME_BITS), FRAME_BITS
        )
        self.assertAlmostEqual(recovered / BER, 1.0, places=9)

    def test_a_long_frame_demands_a_far_better_channel(self):
        needed = required_bit_error_rate(1.0e-6, FRAME_BITS)
        self.assertLess(needed, 1.0e-8)


class AssessTests(unittest.TestCase):
    def test_a_nominal_link_is_within_budget(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS, MISSION, 1.0e-9, 1.0e-15)
        self.assertEqual(result["verdict"], WITHIN_BUDGET)
        self.assertTrue(result["ber_within_budget"])

    def test_a_bit_error_rate_exactly_at_the_requirement_passes(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS, MISSION, BER)
        self.assertEqual(result["verdict"], WITHIN_BUDGET)

    def test_a_bit_error_rate_past_the_requirement_is_reported(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS, MISSION, 5.0e-10)
        self.assertEqual(result["verdict"], BER_EXCEEDED)
        self.assertTrue(any("exceeds the required" in f for f in result["findings"]))

    def test_a_residual_exactly_at_the_requirement_passes(self):
        result = assess_error_rates(
            BER, FRAME_BITS, RATE, FCS, MISSION, 1.0e-9, NOMINAL_RESIDUAL
        )
        self.assertEqual(result["verdict"], WITHIN_BUDGET)

    def test_a_residual_past_the_requirement_is_reported_separately(self):
        result = assess_error_rates(
            BER, FRAME_BITS, RATE, FCS, MISSION, 1.0e-9, 1.0e-16
        )
        self.assertEqual(result["verdict"], RESIDUAL_EXCEEDED)
        self.assertTrue(result["ber_within_budget"])

    def test_a_bit_error_rate_breach_outranks_the_residual(self):
        result = assess_error_rates(
            BER, FRAME_BITS, RATE, FCS, MISSION, 5.0e-10, 1.0e-30
        )
        self.assertEqual(result["verdict"], BER_EXCEEDED)

    def test_an_error_free_claim_is_flagged(self):
        result = assess_error_rates(0.0, FRAME_BITS, RATE, FCS, MISSION, 1.0e-9)
        self.assertIsNone(result["mean_time_between_errored_frames_s"])
        self.assertTrue(any("is a claim rather" in f for f in result["findings"]))

    def test_an_undeclared_requirement_is_flagged(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS, MISSION)
        self.assertTrue(any("no required error rate" in f for f in result["findings"]))

    def test_an_undeclared_mission_duration_is_flagged(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS)
        self.assertTrue(any("no mission duration" in f for f in result["findings"]))

    def test_the_mean_time_is_carried_in_the_result(self):
        result = assess_error_rates(BER, FRAME_BITS, RATE, FCS, MISSION, 1.0e-9)
        self.assertAlmostEqual(
            result["mean_time_between_errored_frames_s"] / 100.00005115000873,
            1.0,
            places=12,
        )

    def test_a_bad_frame_length_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_error_rates(BER, 0, RATE, FCS, MISSION)

    def test_a_bad_link_rate_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_error_rates(BER, FRAME_BITS, 0.0, FCS, MISSION)


if __name__ == "__main__":
    unittest.main()
