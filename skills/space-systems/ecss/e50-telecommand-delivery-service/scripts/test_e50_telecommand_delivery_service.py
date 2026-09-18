#!/usr/bin/env python3
"""Gate 3 contract test for e50-telecommand-delivery-service.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_telecommand_delivery_service.py
"""

import unittest

from e50_telecommand_delivery_service_logic import (
    ACCEPTED,
    DEFAULT_SEQUENCE_MODULUS,
    DEFAULT_WINDOW_WIDTH,
    DUPLICATE,
    GAP_REFUSED,
    GUARANTEE_MET,
    OUT_OF_WINDOW,
    RETRANSMISSION_OWED,
    SENDER_OUT_OF_STEP,
    advance_expected,
    assess_delivery_service,
    categorize_frame,
    deliver_stream,
    delivery_is_ordered,
    delivery_is_unique,
    signed_offset,
    validate_modulus,
    validate_sequence_number,
    validate_window_width,
)


class TestValidation(unittest.TestCase):
    def test_the_default_modulus_is_accepted(self):
        self.assertEqual(validate_modulus(), DEFAULT_SEQUENCE_MODULUS)

    def test_a_tiny_modulus_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_modulus(2)

    def test_an_odd_modulus_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_modulus(255)

    def test_a_boolean_modulus_is_not_an_integer(self):
        with self.assertRaises(ValueError):
            validate_modulus(True)

    def test_the_default_window_fits_the_default_modulus(self):
        self.assertEqual(validate_window_width(), DEFAULT_WINDOW_WIDTH)

    def test_a_window_past_half_the_modulus_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_window_width(200, 256)

    def test_a_zero_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_window_width(0)

    def test_a_sequence_number_past_the_modulus_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_number(256, 256)

    def test_a_negative_sequence_number_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence_number(-1)


class TestOffsets(unittest.TestCase):
    def test_the_expected_frame_sits_at_zero(self):
        self.assertEqual(signed_offset(40, 40), 0)

    def test_a_frame_ahead_has_a_positive_offset(self):
        self.assertEqual(signed_offset(43, 40), 3)

    def test_a_frame_behind_has_a_negative_offset(self):
        self.assertEqual(signed_offset(37, 40), -3)

    def test_the_offset_wraps_across_the_counter_roll(self):
        self.assertEqual(signed_offset(1, 254), 3)
        self.assertEqual(signed_offset(254, 1), -3)

    def test_the_expected_value_advances_and_wraps(self):
        self.assertEqual(advance_expected(255), 0)
        self.assertEqual(advance_expected(7), 8)


class TestDisposition(unittest.TestCase):
    def test_the_expected_frame_is_accepted(self):
        self.assertEqual(categorize_frame(40, 40), ACCEPTED)

    def test_an_early_frame_inside_the_window_is_refused_as_a_gap(self):
        self.assertEqual(categorize_frame(43, 40), GAP_REFUSED)

    def test_an_already_delivered_frame_is_a_duplicate(self):
        self.assertEqual(categorize_frame(37, 40), DUPLICATE)

    def test_a_frame_far_ahead_falls_outside_the_window(self):
        self.assertEqual(categorize_frame(80, 40), OUT_OF_WINDOW)

    def test_a_frame_far_behind_falls_outside_the_window(self):
        self.assertEqual(categorize_frame(200, 40), OUT_OF_WINDOW)

    def test_the_frame_one_past_the_window_edge_is_outside_it(self):
        self.assertEqual(categorize_frame(50, 40, 10), OUT_OF_WINDOW)


class TestStream(unittest.TestCase):
    def test_a_clean_run_is_delivered_in_full(self):
        report = deliver_stream([0, 1, 2, 3], expected=0)
        self.assertEqual(report["delivered"], (0, 1, 2, 3))
        self.assertEqual(report["next_expected"], 4)
        self.assertEqual(report["counts"][ACCEPTED], 4)

    def test_a_repeated_frame_is_discarded_not_delivered_twice(self):
        report = deliver_stream([0, 1, 1, 2], expected=0)
        self.assertEqual(report["delivered"], (0, 1, 2))
        self.assertEqual(report["counts"][DUPLICATE], 1)

    def test_a_skipped_frame_blocks_the_ones_behind_it(self):
        report = deliver_stream([0, 2, 3], expected=0)
        self.assertEqual(report["delivered"], (0,))
        self.assertEqual(report["counts"][GAP_REFUSED], 2)

    def test_a_gap_names_the_frame_that_must_be_retransmitted(self):
        report = deliver_stream([0, 2], expected=0)
        self.assertEqual(report["retransmission_requests"], (1,))

    def test_delivery_resumes_once_the_missing_frame_arrives(self):
        report = deliver_stream([0, 2, 1, 2, 3], expected=0)
        self.assertEqual(report["delivered"], (0, 1, 2, 3))

    def test_the_stream_wraps_across_the_counter_roll(self):
        report = deliver_stream([254, 255, 0, 1], expected=254)
        self.assertEqual(report["delivered"], (254, 255, 0, 1))
        self.assertEqual(report["next_expected"], 2)

    def test_a_malformed_frame_number_is_rejected(self):
        with self.assertRaises(ValueError):
            deliver_stream([0, 1, 999])

    def test_a_non_sequence_stream_is_rejected(self):
        with self.assertRaises(ValueError):
            deliver_stream(17)


class TestPromise(unittest.TestCase):
    def test_a_contiguous_run_is_ordered(self):
        self.assertTrue(delivery_is_ordered((4, 5, 6)))

    def test_a_run_with_a_hole_is_not_ordered(self):
        self.assertFalse(delivery_is_ordered((4, 6)))

    def test_a_run_with_a_repeat_is_not_unique(self):
        self.assertFalse(delivery_is_unique((4, 5, 5)))

    def test_an_empty_run_is_trivially_ordered_and_unique(self):
        self.assertTrue(delivery_is_ordered(()))
        self.assertTrue(delivery_is_unique(()))


class TestAssessment(unittest.TestCase):
    def test_a_clean_stream_meets_the_guarantee(self):
        report = assess_delivery_service([0, 1, 2, 3])
        self.assertEqual(report["verdict"], GUARANTEE_MET)
        self.assertTrue(report["guarantee_held"])
        self.assertEqual(report["findings"], [])

    def test_a_gap_leaves_a_retransmission_owed(self):
        report = assess_delivery_service([0, 2, 3])
        self.assertEqual(report["verdict"], RETRANSMISSION_OWED)
        self.assertTrue(any("retransmission" in note for note in report["limitations"]))

    def test_a_frame_outside_the_window_puts_the_sender_out_of_step(self):
        report = assess_delivery_service([0, 90])
        self.assertEqual(report["verdict"], SENDER_OUT_OF_STEP)
        self.assertTrue(report["findings"])

    def test_a_duplicate_is_a_limitation_not_a_finding(self):
        report = assess_delivery_service([0, 0, 1])
        self.assertEqual(report["verdict"], GUARANTEE_MET)
        self.assertTrue(any("duplicate" in note for note in report["limitations"]))

    def test_delivery_stays_ordered_and_unique_under_disorder(self):
        report = assess_delivery_service([0, 3, 1, 2, 1, 3])
        self.assertTrue(report["in_order"])
        self.assertTrue(report["delivered_once"])

    def test_the_report_carries_the_window_it_used(self):
        report = assess_delivery_service([0, 1], window_width=4)
        self.assertEqual(report["window_width"], 4)


if __name__ == "__main__":
    unittest.main()
