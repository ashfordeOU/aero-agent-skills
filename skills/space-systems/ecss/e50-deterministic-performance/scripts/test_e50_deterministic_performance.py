"""Contract tests for the clause 5.7.1.2 deterministic performance logic."""

import unittest

from e50_deterministic_performance_logic import (
    DEADLINE_MISS,
    DETERMINISTIC,
    JITTER_EXCEEDED,
    UNBOUNDED,
    assess_deterministic_performance,
    best_case_latency_s,
    jitter_s,
    link_response_time_s,
    path_utilisation,
    transmission_time_s,
    validate_hops,
    validate_nonnegative,
    validate_positive,
    validate_streams,
    worst_case_latency_s,
)

RATE = 1.0e7
OWN_BITS = 8000.0
OWN_PERIOD = 0.1
BLOCKING_BITS = 1500.0
SWITCH = 5.0e-5
ACCESS = 1.0e-5
SLOW_RIVAL = [{"bits": 2000.0, "period_s": 0.01}]
FAST_RIVAL = [{"bits": 2000.0, "period_s": 0.001}]
SATURATING = [
    {"bits": 6000.0, "period_s": 0.001},
    {"bits": 5000.0, "period_s": 0.001},
]


class ValidationTests(unittest.TestCase):
    def test_zero_rejected_by_positive(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "rate_bps")

    def test_negative_rejected_by_positive(self):
        with self.assertRaises(ValueError):
            validate_positive(-1.0, "rate_bps")

    def test_boolean_rejected_by_positive(self):
        with self.assertRaises(ValueError):
            validate_positive(True, "rate_bps")

    def test_text_rejected_by_positive(self):
        with self.assertRaises(ValueError):
            validate_positive("1e7", "rate_bps")

    def test_infinity_rejected_by_positive(self):
        with self.assertRaises(ValueError):
            validate_positive(float("inf"), "rate_bps")

    def test_zero_accepted_by_nonnegative(self):
        self.assertAlmostEqual(validate_nonnegative(0, "switch_latency_s"), 0.0, places=9)

    def test_negative_rejected_by_nonnegative(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1e-9, "switch_latency_s")

    def test_zero_hops_rejected(self):
        with self.assertRaises(ValueError):
            validate_hops(0)

    def test_fractional_hops_rejected(self):
        with self.assertRaises(ValueError):
            validate_hops(1.5)

    def test_streams_none_is_empty(self):
        self.assertEqual(validate_streams(None), [])

    def test_streams_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_streams({"bits": 1.0, "period_s": 1.0})

    def test_stream_missing_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_streams([{"bits": 1000.0}])

    def test_stream_with_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_streams([{"bits": 1000.0, "period_s": 0.0}])


class TransmissionTests(unittest.TestCase):
    def test_transmission_time_of_one_frame(self):
        self.assertAlmostEqual(transmission_time_s(OWN_BITS, RATE), 0.0008, places=12)

    def test_transmission_time_scales_with_size(self):
        single = transmission_time_s(OWN_BITS, RATE)
        double = transmission_time_s(2.0 * OWN_BITS, RATE)
        self.assertAlmostEqual(double, 2.0 * single, places=12)

    def test_transmission_rejects_a_dead_link(self):
        with self.assertRaises(ValueError):
            transmission_time_s(OWN_BITS, 0.0)


class UtilisationTests(unittest.TestCase):
    def test_own_stream_load(self):
        self.assertAlmostEqual(
            path_utilisation(OWN_BITS, OWN_PERIOD, RATE), 0.008, places=12
        )

    def test_rivals_add_their_load(self):
        self.assertAlmostEqual(
            path_utilisation(OWN_BITS, OWN_PERIOD, RATE, SLOW_RIVAL), 0.028, places=12
        )


class BestCaseTests(unittest.TestCase):
    def test_single_hop_idle_path(self):
        self.assertAlmostEqual(
            best_case_latency_s(OWN_BITS, RATE, 1, SWITCH, ACCESS), 0.00081, places=12
        )

    def test_second_hop_adds_transmission_and_switching(self):
        self.assertAlmostEqual(
            best_case_latency_s(OWN_BITS, RATE, 2, SWITCH, ACCESS), 0.00167, places=12
        )


class ResponseTimeTests(unittest.TestCase):
    def test_blocking_only(self):
        self.assertAlmostEqual(
            link_response_time_s(OWN_BITS, OWN_PERIOD, RATE, BLOCKING_BITS),
            0.00095,
            places=12,
        )

    def test_slow_rival_interferes_once(self):
        self.assertAlmostEqual(
            link_response_time_s(OWN_BITS, OWN_PERIOD, RATE, BLOCKING_BITS, SLOW_RIVAL),
            0.00115,
            places=12,
        )

    def test_fast_rival_is_counted_twice_by_the_fixed_point(self):
        self.assertAlmostEqual(
            link_response_time_s(OWN_BITS, OWN_PERIOD, RATE, BLOCKING_BITS, FAST_RIVAL),
            0.00135,
            places=12,
        )

    def test_saturated_link_has_no_fixed_point(self):
        self.assertIsNone(
            link_response_time_s(OWN_BITS, OWN_PERIOD, RATE, BLOCKING_BITS, SATURATING)
        )


class WorstCaseTests(unittest.TestCase):
    def test_quiet_path_equals_the_idle_path(self):
        best = best_case_latency_s(OWN_BITS, RATE, 2, SWITCH, ACCESS)
        worst = worst_case_latency_s(
            OWN_BITS, OWN_PERIOD, RATE, 2, 0.0, None, SWITCH, ACCESS
        )
        self.assertAlmostEqual(worst, best, places=12)

    def test_blocking_and_rivals_push_the_bound_out(self):
        best = best_case_latency_s(OWN_BITS, RATE, 2, SWITCH, ACCESS)
        worst = worst_case_latency_s(
            OWN_BITS, OWN_PERIOD, RATE, 2, BLOCKING_BITS, SLOW_RIVAL, SWITCH, ACCESS
        )
        self.assertAlmostEqual(worst, 0.00237, places=12)
        self.assertGreater(worst, best)

    def test_saturated_path_has_no_bound(self):
        self.assertIsNone(
            worst_case_latency_s(
                OWN_BITS, OWN_PERIOD, RATE, 2, BLOCKING_BITS, SATURATING, SWITCH, ACCESS
            )
        )


class JitterTests(unittest.TestCase):
    def test_jitter_is_the_spread(self):
        self.assertAlmostEqual(jitter_s(0.00237, 0.00167), 0.0007, places=12)

    def test_jitter_of_an_unbounded_path_is_undefined(self):
        self.assertIsNone(jitter_s(None, 0.00167))

    def test_best_above_worst_rejected(self):
        with self.assertRaises(ValueError):
            jitter_s(0.001, 0.002)


class AssessTests(unittest.TestCase):
    def _nominal(self, deadline, budget=None):
        return assess_deterministic_performance(
            OWN_BITS, OWN_PERIOD, RATE, 2, deadline, BLOCKING_BITS, SLOW_RIVAL,
            SWITCH, ACCESS, budget,
        )

    def test_comfortable_path_is_deterministic(self):
        result = self._nominal(0.02)
        self.assertEqual(result["verdict"], DETERMINISTIC)
        self.assertTrue(result["bounded"])

    def test_latency_exactly_at_the_deadline_still_passes(self):
        result = self._nominal(0.00237)
        self.assertAlmostEqual(result["worst_case_latency_s"], 0.00237, places=12)
        self.assertEqual(result["verdict"], DETERMINISTIC)

    def test_tight_deadline_is_missed(self):
        result = self._nominal(0.002)
        self.assertEqual(result["verdict"], DEADLINE_MISS)
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_margin_is_reported(self):
        self.assertAlmostEqual(self._nominal(0.02)["margin_s"], 0.01763, places=12)

    def test_jitter_budget_exactly_met_passes(self):
        self.assertEqual(self._nominal(0.02, 0.0007)["verdict"], DETERMINISTIC)

    def test_jitter_budget_breach_is_separate_from_the_deadline(self):
        result = self._nominal(0.02, 0.0005)
        self.assertEqual(result["verdict"], JITTER_EXCEEDED)
        self.assertAlmostEqual(result["jitter_s"], 0.0007, places=12)

    def test_saturated_path_is_reported_unbounded(self):
        result = assess_deterministic_performance(
            OWN_BITS, OWN_PERIOD, RATE, 2, 0.02, BLOCKING_BITS, SATURATING,
            SWITCH, ACCESS,
        )
        self.assertEqual(result["verdict"], UNBOUNDED)
        self.assertFalse(result["bounded"])
        self.assertIsNone(result["margin_s"])

    def test_idle_path_input_is_flagged_not_silently_passed(self):
        result = assess_deterministic_performance(
            OWN_BITS, OWN_PERIOD, RATE, 2, 0.02, 0.0, None, SWITCH, ACCESS
        )
        self.assertEqual(result["verdict"], DETERMINISTIC)
        self.assertTrue(any("idle-path figure" in f for f in result["findings"]))

    def test_bad_deadline_rejected(self):
        with self.assertRaises(ValueError):
            self._nominal(0.0)

    def test_bad_hop_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_deterministic_performance(
                OWN_BITS, OWN_PERIOD, RATE, 0, 0.02, BLOCKING_BITS, SLOW_RIVAL
            )


if __name__ == "__main__":
    unittest.main()
