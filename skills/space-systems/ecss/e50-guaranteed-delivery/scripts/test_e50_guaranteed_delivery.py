"""Contract tests for the clause 5.6.14.2 guaranteed delivery logic."""

import unittest

from e50_guaranteed_delivery_logic import (
    BOUNDED,
    BROKEN,
    GUARANTEED,
    assess_guaranteed_delivery,
    attempts_for_residual_target,
    expected_undelivered_units,
    replay_delivery,
    residual_loss_probability,
    validate_count,
    validate_identifiers,
    validate_probability,
)

SENT = [1, 2, 3, 4, 5]


def transfer(**overrides):
    base = dict(
        handed_over=list(SENT),
        delivered=list(SENT),
        sender_notified=False,
        per_attempt_loss=0.05,
        attempts=4,
        residual_target=1e-4,
    )
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_identifier_list_accepted(self):
        self.assertEqual(validate_identifiers([1, 2, 3]), [1, 2, 3])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifiers(3)

    def test_non_integer_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifiers([1, "2"])

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifiers([1, True])

    def test_negative_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifiers([1, -2])

    def test_repeated_handover_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifiers([1, 1, 2])

    def test_repeats_allowed_on_the_delivered_list(self):
        self.assertEqual(validate_identifiers([1, 1], allow_repeats=True), [1, 1])

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.01)

    def test_infinite_probability_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(float("nan"))

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0)


class ReplayTests(unittest.TestCase):
    def test_clean_delivery_meets_every_part(self):
        result = replay_delivery(SENT, SENT)
        self.assertTrue(result["complete"])
        self.assertTrue(result["exactly_once"])
        self.assertTrue(result["in_order"])

    def test_lost_unit_is_named(self):
        result = replay_delivery(SENT, [1, 2, 4, 5])
        self.assertEqual(result["missing"], [3])

    def test_duplicate_is_named(self):
        result = replay_delivery(SENT, [1, 2, 2, 3, 4, 5])
        self.assertEqual(result["duplicates"], [2])

    def test_duplicate_does_not_count_as_a_second_delivery(self):
        result = replay_delivery(SENT, [1, 2, 2, 3, 4, 5])
        self.assertEqual(result["delivered"], 5)

    def test_reordering_is_not_a_loss(self):
        result = replay_delivery(SENT, [1, 3, 2, 4, 5])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["out_of_order"], [2])

    def test_late_arrival_clears_the_loss(self):
        result = replay_delivery(SENT, [1, 4, 5, 2, 3])
        self.assertTrue(result["complete"])
        self.assertFalse(result["in_order"])

    def test_identifier_never_handed_over_rejected(self):
        with self.assertRaises(ValueError):
            replay_delivery(SENT, [1, 2, 99])

    def test_empty_delivery_loses_everything(self):
        result = replay_delivery(SENT, [])
        self.assertEqual(result["missing"], SENT)


class ResidualTests(unittest.TestCase):
    def test_residual_compounds_over_the_attempts(self):
        self.assertAlmostEqual(residual_loss_probability(0.5, 4), 0.0625, places=12)

    def test_single_attempt_residual_is_the_loss(self):
        self.assertAlmostEqual(residual_loss_probability(0.05, 1), 0.05, places=12)

    def test_lossless_link_leaves_no_residual(self):
        self.assertAlmostEqual(residual_loss_probability(0.0, 4), 0.0, places=12)

    def test_more_attempts_never_raise_the_residual(self):
        self.assertLessEqual(
            residual_loss_probability(0.05, 5), residual_loss_probability(0.05, 4)
        )

    def test_attempts_for_target_is_minimal(self):
        self.assertEqual(attempts_for_residual_target(0.5, 0.0625), 4)

    def test_attempts_for_target_actually_reaches_it(self):
        target = 1e-8
        attempts = attempts_for_residual_target(0.05, target)
        self.assertLessEqual(residual_loss_probability(0.05, attempts), target)

    def test_total_loss_link_never_reaches_a_target(self):
        self.assertIsNone(attempts_for_residual_target(1.0, 1e-6))

    def test_ceiling_stops_an_unreachable_search(self):
        self.assertIsNone(attempts_for_residual_target(0.999999, 1e-30, ceiling=5))

    def test_expected_undelivered_scales_with_the_transfer(self):
        one = expected_undelivered_units(0.05, 4, 1)
        many = expected_undelivered_units(0.05, 4, 1000)
        self.assertAlmostEqual(many, 1000.0 * one, places=12)


class AssessTests(unittest.TestCase):
    def test_clean_transfer_is_guaranteed(self):
        result = assess_guaranteed_delivery(**transfer())
        self.assertEqual(result["verdict"], GUARANTEED)
        self.assertEqual(result["findings"], [])

    def test_silent_loss_breaks_the_guarantee(self):
        result = assess_guaranteed_delivery(**transfer(delivered=[1, 2, 4, 5]))
        self.assertEqual(result["verdict"], BROKEN)
        self.assertTrue(any("guarantee is broken" in f for f in result["findings"]))

    def test_notified_loss_is_bounded_not_broken(self):
        result = assess_guaranteed_delivery(
            **transfer(delivered=[1, 2, 4, 5], sender_notified=True)
        )
        self.assertEqual(result["verdict"], BOUNDED)
        self.assertTrue(any("bounded rather than guaranteed" in f for f in result["findings"]))

    def test_duplicate_breaks_the_guarantee_even_when_notified(self):
        result = assess_guaranteed_delivery(
            **transfer(delivered=[1, 2, 2, 3, 4, 5], sender_notified=True)
        )
        self.assertEqual(result["verdict"], BROKEN)
        self.assertFalse(result["exactly_once"])

    def test_reordering_breaks_the_guarantee(self):
        result = assess_guaranteed_delivery(**transfer(delivered=[1, 3, 2, 4, 5]))
        self.assertEqual(result["verdict"], BROKEN)
        self.assertFalse(result["in_order"])

    def test_residual_above_the_target_is_reported(self):
        result = assess_guaranteed_delivery(**transfer(attempts=2))
        self.assertFalse(result["residual_ok"])
        self.assertTrue(any("residual loss" in f for f in result["findings"]))

    def test_recommended_attempt_count_clears_the_residual(self):
        result = assess_guaranteed_delivery(**transfer(attempts=2))
        fixed = assess_guaranteed_delivery(**transfer(attempts=result["attempts_for_target"]))
        self.assertTrue(fixed["residual_ok"])

    def test_residual_exactly_at_the_target_is_accepted(self):
        exact = residual_loss_probability(0.05, 4)
        result = assess_guaranteed_delivery(**transfer(residual_target=exact))
        self.assertAlmostEqual(result["residual_loss"], result["residual_target"], places=15)
        self.assertTrue(result["residual_ok"])

    def test_expected_undelivered_is_carried(self):
        result = assess_guaranteed_delivery(**transfer())
        self.assertAlmostEqual(
            result["expected_undelivered_units"],
            result["residual_loss"] * float(len(SENT)),
            places=15,
        )

    def test_notification_flag_must_be_a_boolean(self):
        with self.assertRaises(ValueError):
            assess_guaranteed_delivery(**transfer(sender_notified="yes"))

    def test_bad_target_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_guaranteed_delivery(**transfer(residual_target=2.0))

    def test_unknown_delivered_identifier_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_guaranteed_delivery(**transfer(delivered=[1, 2, 3, 4, 5, 6]))


if __name__ == "__main__":
    unittest.main()
