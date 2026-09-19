"""Contract tests for the clause 5.6.13.5 ARQ settings logic."""

import unittest

from e50_arq_settings_logic import (
    CONSISTENT,
    INCONSISTENT,
    assess_arq_settings,
    attempts_for_residual_target,
    required_window_units,
    residual_loss_probability,
    retransmission_timeout_floor,
    validate_commandability,
    validate_count,
    validate_positive_number,
    validate_positive_time,
    validate_probability,
    validate_time,
    worst_case_delivery_s,
)

TRIP = 2.0
ACK = 0.5
JITTER = 0.25
RATE = 2000000.0
UNIT = 8192.0
ALL_SETTABLE = {"timeout_s": True, "window_units": True, "retry_limit": True}


def settings(**overrides):
    base = dict(
        timeout_s=3.0,
        window_units=700,
        retry_limit=4,
        per_attempt_loss=0.05,
        commandable=dict(ALL_SETTABLE),
        round_trip_s=TRIP,
        ack_delay_s=ACK,
        jitter_s=JITTER,
        rate_bps=RATE,
        unit_bits=UNIT,
        residual_target=1e-4,
    )
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_zero_time_accepted_where_optional(self):
        self.assertAlmostEqual(validate_time(0), 0.0, places=9)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(-0.1)

    def test_zero_positive_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_time(0.0)

    def test_boolean_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(True)

    def test_infinite_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(float("inf"))

    def test_zero_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_number(0.0, "rate_bps")

    def test_zero_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(4.0)

    def test_probability_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_probability(1.2)

    def test_commandability_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_commandability(["timeout_s"])

    def test_commandability_missing_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_commandability({"timeout_s": True, "window_units": True})

    def test_commandability_unknown_parameter_rejected(self):
        extra = dict(ALL_SETTABLE)
        extra["ack_delay_s"] = True
        with self.assertRaises(ValueError):
            validate_commandability(extra)

    def test_commandability_non_boolean_rejected(self):
        bad = dict(ALL_SETTABLE)
        bad["retry_limit"] = "yes"
        with self.assertRaises(ValueError):
            validate_commandability(bad)


class TimeoutFloorTests(unittest.TestCase):
    def test_floor_is_the_sum_of_the_three_terms(self):
        self.assertAlmostEqual(
            retransmission_timeout_floor(TRIP, ACK, JITTER), 2.75, places=9
        )

    def test_floor_without_ack_or_jitter_is_the_round_trip(self):
        self.assertAlmostEqual(retransmission_timeout_floor(TRIP, 0.0, 0.0), TRIP, places=9)

    def test_zero_round_trip_rejected(self):
        with self.assertRaises(ValueError):
            retransmission_timeout_floor(0.0, ACK, JITTER)


class WindowTests(unittest.TestCase):
    def test_window_covers_the_round_trip(self):
        self.assertEqual(required_window_units(8192.0, 8192.0, 4.0), 4)

    def test_partial_unit_rounds_up(self):
        self.assertEqual(required_window_units(8192.0, 8192.0, 4.5), 5)

    def test_ack_delay_widens_the_window(self):
        self.assertGreater(
            required_window_units(8192.0, 8192.0, 4.0, 4.0),
            required_window_units(8192.0, 8192.0, 4.0),
        )


class WorstCaseTests(unittest.TestCase):
    def test_single_attempt_costs_one_round_trip(self):
        self.assertAlmostEqual(worst_case_delivery_s(3.0, 1, TRIP), TRIP, places=9)

    def test_each_extra_attempt_costs_a_timeout(self):
        self.assertAlmostEqual(
            worst_case_delivery_s(3.0, 4, TRIP) - worst_case_delivery_s(3.0, 3, TRIP),
            3.0,
            places=9,
        )

    def test_zero_retry_limit_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_delivery_s(3.0, 0, TRIP)


class ResidualTests(unittest.TestCase):
    def test_residual_compounds_over_the_attempts(self):
        self.assertAlmostEqual(residual_loss_probability(0.5, 3), 0.125, places=12)

    def test_single_attempt_residual_is_the_loss(self):
        self.assertAlmostEqual(residual_loss_probability(0.05, 1), 0.05, places=12)

    def test_lossless_link_leaves_no_residual(self):
        self.assertAlmostEqual(residual_loss_probability(0.0, 3), 0.0, places=12)

    def test_attempts_for_target_is_minimal(self):
        attempts = attempts_for_residual_target(0.5, 0.125)
        self.assertEqual(attempts, 3)

    def test_attempts_for_target_actually_reaches_it(self):
        target = 1e-6
        attempts = attempts_for_residual_target(0.05, target)
        self.assertLessEqual(residual_loss_probability(0.05, attempts), target)

    def test_total_loss_link_never_reaches_a_target(self):
        self.assertIsNone(attempts_for_residual_target(1.0, 1e-6))


class AssessTests(unittest.TestCase):
    def test_sound_configuration_is_consistent(self):
        result = assess_arq_settings(**settings())
        self.assertEqual(result["verdict"], CONSISTENT)
        self.assertEqual(result["findings"], [])

    def test_timeout_below_the_floor_is_reported(self):
        result = assess_arq_settings(**settings(timeout_s=2.1))
        self.assertFalse(result["timeout_ok"])
        self.assertEqual(result["verdict"], INCONSISTENT)

    def test_timeout_exactly_at_the_floor_is_accepted(self):
        floor = retransmission_timeout_floor(TRIP, ACK, JITTER)
        result = assess_arq_settings(**settings(timeout_s=floor))
        self.assertAlmostEqual(result["timeout_s"], result["timeout_floor_s"], places=9)
        self.assertTrue(result["timeout_ok"])

    def test_short_window_is_reported(self):
        result = assess_arq_settings(**settings(window_units=10))
        self.assertFalse(result["window_ok"])
        self.assertTrue(any("bandwidth-delay product" in f for f in result["findings"]))

    def test_window_exactly_at_the_requirement_is_accepted(self):
        needed = required_window_units(RATE, UNIT, TRIP, ACK)
        result = assess_arq_settings(**settings(window_units=needed))
        self.assertTrue(result["window_ok"])

    def test_residual_above_the_target_is_reported(self):
        result = assess_arq_settings(**settings(retry_limit=2))
        self.assertFalse(result["residual_ok"])
        self.assertTrue(any("residual loss" in f for f in result["findings"]))

    def test_recommended_retry_limit_clears_the_residual(self):
        result = assess_arq_settings(**settings(retry_limit=2))
        fixed = assess_arq_settings(
            **settings(retry_limit=result["recommended"]["retry_limit"])
        )
        self.assertTrue(fixed["residual_ok"])

    def test_recommended_timeout_clears_the_floor_finding(self):
        result = assess_arq_settings(**settings(timeout_s=1.0))
        fixed = assess_arq_settings(**settings(timeout_s=result["recommended"]["timeout_s"]))
        self.assertTrue(fixed["timeout_ok"])

    def test_recommended_window_clears_the_window_finding(self):
        result = assess_arq_settings(**settings(window_units=10))
        fixed = assess_arq_settings(
            **settings(window_units=result["recommended"]["window_units"])
        )
        self.assertTrue(fixed["window_ok"])

    def test_fixed_parameter_fails_even_when_the_values_fit(self):
        frozen = dict(ALL_SETTABLE)
        frozen["timeout_s"] = False
        result = assess_arq_settings(**settings(commandable=frozen))
        self.assertTrue(result["consistent"])
        self.assertFalse(result["adjustable"])
        self.assertEqual(result["verdict"], INCONSISTENT)

    def test_fixed_parameter_is_named(self):
        frozen = dict(ALL_SETTABLE)
        frozen["retry_limit"] = False
        result = assess_arq_settings(**settings(commandable=frozen))
        self.assertEqual(result["fixed_parameters"], ["retry_limit"])
        self.assertTrue(any("cannot be changed in flight" in f for f in result["findings"]))

    def test_deadline_is_optional(self):
        result = assess_arq_settings(**settings())
        self.assertIsNone(result["delivery_deadline_s"])
        self.assertTrue(result["deadline_ok"])

    def test_worst_case_beyond_the_deadline_is_reported(self):
        result = assess_arq_settings(**settings(delivery_deadline_s=5.0))
        self.assertFalse(result["deadline_ok"])
        self.assertTrue(any("worst case delivery" in f for f in result["findings"]))

    def test_worst_case_exactly_at_the_deadline_is_accepted(self):
        worst = worst_case_delivery_s(3.0, 4, TRIP)
        result = assess_arq_settings(**settings(delivery_deadline_s=worst))
        self.assertAlmostEqual(
            result["worst_case_delivery_s"], result["delivery_deadline_s"], places=9
        )
        self.assertTrue(result["deadline_ok"])

    def test_bad_commandability_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_arq_settings(**settings(commandable={"timeout_s": True}))

    def test_bad_loss_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_arq_settings(**settings(per_attempt_loss=1.5))


if __name__ == "__main__":
    unittest.main()
