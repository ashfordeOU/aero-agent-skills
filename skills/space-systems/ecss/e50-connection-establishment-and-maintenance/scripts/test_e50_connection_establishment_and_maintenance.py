"""Contract tests for the clause 5.6.14.1 connection establishment logic."""

import unittest

from e50_connection_establishment_and_maintenance_logic import (
    CLOSED,
    CLOSING,
    ESTABLISHING,
    MAINTAINING,
    OPEN,
    SUPPORTED,
    UNSUPPORTED,
    assess_connection,
    establishment_timeout_floor_s,
    keepalive_budget_s,
    recommended_keepalive_interval_s,
    replay_state_trace,
    transition_allowed,
    validate_count,
    validate_positive_time,
    validate_state,
    validate_time,
    worst_case_time_to_open_s,
)

TRIP = 2.0
PROCESSING = 0.25


def service(**overrides):
    base = dict(
        handshake_exchanges=3,
        round_trip_s=TRIP,
        far_end_processing_s=PROCESSING,
        establishment_timeout_s=8.0,
        attempts=3,
        contact_time_s=600.0,
        keepalive_interval_s=20.0,
        inactivity_timeout_s=70.0,
        tolerated_losses=2,
    )
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_known_state_accepted(self):
        self.assertEqual(validate_state(OPEN), OPEN)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_state("half-open")

    def test_zero_exchanges_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(0, "handshake_exchanges")

    def test_zero_losses_accepted_where_the_minimum_allows_it(self):
        self.assertEqual(validate_count(0, "tolerated_losses", minimum=0), 0)

    def test_float_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_count(3.0)

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(-1.0)

    def test_zero_positive_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_time(0.0)

    def test_infinite_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive_time(float("inf"))

    def test_boolean_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_time(True)


class TransitionTests(unittest.TestCase):
    def test_closed_may_begin_establishing(self):
        self.assertTrue(transition_allowed(CLOSED, ESTABLISHING))

    def test_closed_may_not_jump_to_open(self):
        self.assertFalse(transition_allowed(CLOSED, OPEN))

    def test_establishing_may_fail_back_to_closed(self):
        self.assertTrue(transition_allowed(ESTABLISHING, CLOSED))

    def test_open_may_be_maintained(self):
        self.assertTrue(transition_allowed(OPEN, MAINTAINING))

    def test_maintaining_returns_to_open(self):
        self.assertTrue(transition_allowed(MAINTAINING, OPEN))

    def test_closing_only_ends_closed(self):
        self.assertTrue(transition_allowed(CLOSING, CLOSED))
        self.assertFalse(transition_allowed(CLOSING, OPEN))

    def test_unknown_state_in_a_transition_rejected(self):
        with self.assertRaises(ValueError):
            transition_allowed(CLOSED, "half-open")


class ReplayTests(unittest.TestCase):
    def test_clean_trace_is_valid(self):
        result = replay_state_trace([CLOSED, ESTABLISHING, OPEN, MAINTAINING, OPEN, CLOSING, CLOSED])
        self.assertTrue(result["valid"])
        self.assertEqual(result["violations"], [])

    def test_illegal_step_is_named_with_its_index(self):
        result = replay_state_trace([CLOSED, OPEN])
        self.assertEqual(result["violations"][0]["index"], 1)
        self.assertEqual(result["violations"][0]["to"], OPEN)

    def test_every_illegal_step_is_reported(self):
        result = replay_state_trace([CLOSED, OPEN, ESTABLISHING])
        self.assertEqual(len(result["violations"]), 2)

    def test_trace_that_never_opened_is_flagged(self):
        result = replay_state_trace([CLOSED, ESTABLISHING, CLOSED])
        self.assertFalse(result["reached_open"])

    def test_final_state_is_carried(self):
        result = replay_state_trace([CLOSED, ESTABLISHING, OPEN])
        self.assertEqual(result["final_state"], OPEN)

    def test_empty_trace_rejected(self):
        with self.assertRaises(ValueError):
            replay_state_trace([])

    def test_non_sequence_trace_rejected(self):
        with self.assertRaises(ValueError):
            replay_state_trace(OPEN)


class EstablishmentTests(unittest.TestCase):
    def test_floor_is_one_round_trip_per_exchange(self):
        self.assertAlmostEqual(establishment_timeout_floor_s(3, 2.0, 0.0), 6.0, places=9)

    def test_far_end_processing_is_paid_per_exchange(self):
        self.assertAlmostEqual(establishment_timeout_floor_s(3, 2.0, 0.25), 6.75, places=9)

    def test_single_exchange_costs_one_round_trip(self):
        self.assertAlmostEqual(establishment_timeout_floor_s(1, 2.0, 0.0), 2.0, places=9)

    def test_single_attempt_costs_only_the_handshake(self):
        self.assertAlmostEqual(
            worst_case_time_to_open_s(8.0, 1, 2.0, 3, 0.25),
            establishment_timeout_floor_s(3, 2.0, 0.25),
            places=9,
        )

    def test_each_retry_costs_a_full_timeout(self):
        self.assertAlmostEqual(
            worst_case_time_to_open_s(8.0, 3, 2.0, 3, 0.25)
            - worst_case_time_to_open_s(8.0, 2, 2.0, 3, 0.25),
            8.0,
            places=9,
        )


class MaintenanceTests(unittest.TestCase):
    def test_budget_is_one_more_interval_than_the_losses(self):
        self.assertAlmostEqual(keepalive_budget_s(20.0, 2), 60.0, places=9)

    def test_no_tolerated_losses_still_needs_one_interval(self):
        self.assertAlmostEqual(keepalive_budget_s(20.0, 0), 20.0, places=9)

    def test_recommended_interval_exactly_fills_the_timeout(self):
        interval = recommended_keepalive_interval_s(60.0, 2)
        self.assertAlmostEqual(keepalive_budget_s(interval, 2), 60.0, places=9)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            keepalive_budget_s(0.0, 2)


class AssessTests(unittest.TestCase):
    def test_sound_service_is_supported(self):
        result = assess_connection(**service())
        self.assertEqual(result["verdict"], SUPPORTED)
        self.assertEqual(result["findings"], [])

    def test_timeout_below_the_handshake_cost_is_reported(self):
        result = assess_connection(**service(establishment_timeout_s=2.0))
        self.assertFalse(result["timeout_ok"])
        self.assertEqual(result["verdict"], UNSUPPORTED)

    def test_timeout_exactly_at_the_floor_is_accepted(self):
        floor = establishment_timeout_floor_s(3, TRIP, PROCESSING)
        result = assess_connection(**service(establishment_timeout_s=floor))
        self.assertAlmostEqual(
            result["establishment_timeout_s"], result["establishment_timeout_floor_s"], places=9
        )
        self.assertTrue(result["timeout_ok"])

    def test_worst_case_beyond_the_contact_is_reported(self):
        result = assess_connection(**service(attempts=20, contact_time_s=30.0))
        self.assertFalse(result["contact_ok"])
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_worst_case_exactly_at_the_contact_is_accepted(self):
        worst = worst_case_time_to_open_s(8.0, 3, TRIP, 3, PROCESSING)
        result = assess_connection(**service(contact_time_s=worst))
        self.assertAlmostEqual(
            result["worst_case_time_to_open_s"], result["contact_time_s"], places=9
        )
        self.assertTrue(result["contact_ok"])

    def test_keepalive_that_cannot_survive_the_losses_is_reported(self):
        result = assess_connection(**service(keepalive_interval_s=40.0))
        self.assertFalse(result["maintenance_ok"])
        self.assertTrue(any("lost keepalives" in f for f in result["findings"]))

    def test_recommended_interval_clears_the_maintenance_finding(self):
        result = assess_connection(**service(keepalive_interval_s=40.0))
        fixed = assess_connection(
            **service(keepalive_interval_s=result["recommended_keepalive_interval_s"])
        )
        self.assertTrue(fixed["maintenance_ok"])

    def test_budget_exactly_at_the_inactivity_timeout_is_accepted(self):
        interval = recommended_keepalive_interval_s(70.0, 2)
        result = assess_connection(**service(keepalive_interval_s=interval))
        self.assertAlmostEqual(
            result["keepalive_budget_s"], result["inactivity_timeout_s"], places=9
        )
        self.assertTrue(result["maintenance_ok"])

    def test_over_frequent_keepalive_is_reported_as_wasteful(self):
        result = assess_connection(**service(keepalive_interval_s=0.5))
        self.assertTrue(result["keepalive_is_wasteful"])
        self.assertTrue(any("competes with the data" in f for f in result["findings"]))

    def test_illegal_trace_makes_the_service_unsupported(self):
        result = assess_connection(**service(state_trace=[CLOSED, OPEN]))
        self.assertFalse(result["trace_ok"])
        self.assertEqual(result["verdict"], UNSUPPORTED)

    def test_legal_trace_leaves_the_service_supported(self):
        result = assess_connection(
            **service(state_trace=[CLOSED, ESTABLISHING, OPEN, CLOSING, CLOSED])
        )
        self.assertTrue(result["trace_ok"])
        self.assertEqual(result["verdict"], SUPPORTED)

    def test_trace_is_optional(self):
        result = assess_connection(**service())
        self.assertIsNone(result["state_replay"])
        self.assertTrue(result["trace_ok"])

    def test_bad_contact_time_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_connection(**service(contact_time_s=0.0))

    def test_bad_state_in_the_trace_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_connection(**service(state_trace=[CLOSED, "half-open"]))


if __name__ == "__main__":
    unittest.main()
