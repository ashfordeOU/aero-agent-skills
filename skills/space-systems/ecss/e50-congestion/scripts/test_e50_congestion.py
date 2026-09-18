"""Contract tests for the clause 5.3.2 congestion containment logic."""

import unittest

from e50_congestion_logic import (
    CONTAINED,
    NO_CONGESTION,
    OVERFLOW,
    assess_congestion,
    backlog_bits,
    drain_time,
    required_buffer_bits,
    required_service_rate,
    time_to_overflow,
    validate_buffer,
    validate_duration,
    validate_rate,
)

OFFERED = 1000000.0
SERVICE = 800000.0
DURATION = 2.0


class ValidationTests(unittest.TestCase):
    def test_zero_rate_accepted(self):
        self.assertAlmostEqual(validate_rate(0), 0.0, places=9)

    def test_negative_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(-1.0)

    def test_boolean_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(True)

    def test_text_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate("800000")

    def test_infinite_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_rate(float("inf"))

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(0.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_duration(-2.0)

    def test_zero_buffer_accepted(self):
        self.assertAlmostEqual(validate_buffer(0), 0.0, places=9)

    def test_negative_buffer_rejected(self):
        with self.assertRaises(ValueError):
            validate_buffer(-1.0)


class BacklogTests(unittest.TestCase):
    def test_overload_leaves_a_backlog(self):
        self.assertAlmostEqual(backlog_bits(OFFERED, SERVICE, DURATION), 400000.0, places=9)

    def test_underload_leaves_nothing(self):
        self.assertAlmostEqual(backlog_bits(500000.0, SERVICE, DURATION), 0.0, places=9)

    def test_offered_equal_to_service_leaves_nothing(self):
        self.assertAlmostEqual(backlog_bits(SERVICE, SERVICE, DURATION), 0.0, places=9)

    def test_backlog_scales_with_duration(self):
        short = backlog_bits(OFFERED, SERVICE, 1.0)
        long = backlog_bits(OFFERED, SERVICE, 2.0)
        self.assertAlmostEqual(long, 2.0 * short, places=9)

    def test_required_buffer_is_the_backlog(self):
        self.assertAlmostEqual(
            required_buffer_bits(OFFERED, SERVICE, DURATION),
            backlog_bits(OFFERED, SERVICE, DURATION),
            places=9,
        )


class OverflowTimeTests(unittest.TestCase):
    def test_overload_fills_the_buffer_in_finite_time(self):
        self.assertAlmostEqual(time_to_overflow(OFFERED, SERVICE, 500000.0), 2.5, places=9)

    def test_no_overload_never_fills_the_buffer(self):
        self.assertIsNone(time_to_overflow(500000.0, SERVICE, 500000.0))

    def test_empty_buffer_fills_immediately_under_overload(self):
        self.assertAlmostEqual(time_to_overflow(OFFERED, SERVICE, 0.0), 0.0, places=9)


class DrainTests(unittest.TestCase):
    def test_backlog_drains_at_the_spare_rate(self):
        self.assertAlmostEqual(drain_time(400000.0, SERVICE), 0.5, places=9)

    def test_continuing_load_slows_the_drain(self):
        self.assertAlmostEqual(drain_time(400000.0, SERVICE, 400000.0), 1.0, places=9)

    def test_load_at_the_service_rate_never_drains(self):
        self.assertIsNone(drain_time(400000.0, SERVICE, SERVICE))

    def test_no_backlog_drains_in_no_time(self):
        self.assertAlmostEqual(drain_time(0.0, SERVICE), 0.0, places=9)


class RequiredRateTests(unittest.TestCase):
    def test_rate_that_holds_the_burst_in_the_buffer(self):
        self.assertAlmostEqual(
            required_service_rate(OFFERED, DURATION, 500000.0), 750000.0, places=9
        )

    def test_buffer_large_enough_asks_nothing_of_the_rate(self):
        self.assertAlmostEqual(
            required_service_rate(OFFERED, DURATION, 4000000.0), 0.0, places=9
        )

    def test_no_buffer_requires_the_full_offered_rate(self):
        self.assertAlmostEqual(
            required_service_rate(OFFERED, DURATION, 0.0), OFFERED, places=9
        )


class AssessTests(unittest.TestCase):
    def test_underloaded_link_is_not_congested(self):
        result = assess_congestion(500000.0, SERVICE, DURATION, 500000.0)
        self.assertEqual(result["verdict"], NO_CONGESTION)
        self.assertFalse(result["congested"])

    def test_burst_inside_the_buffer_is_contained(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 500000.0)
        self.assertEqual(result["verdict"], CONTAINED)
        self.assertTrue(result["contained"])

    def test_burst_exactly_filling_the_buffer_is_contained(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 400000.0)
        self.assertAlmostEqual(result["backlog_bits"], result["buffer_bits"], places=9)
        self.assertEqual(result["verdict"], CONTAINED)

    def test_burst_beyond_the_buffer_overflows(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        self.assertEqual(result["verdict"], OVERFLOW)
        self.assertFalse(result["contained"])

    def test_overflow_reports_the_loss(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        self.assertTrue(any("rather than held" in f for f in result["findings"]))

    def test_overflow_reports_both_ways_out(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        self.assertTrue(any("or a service rate of at least" in f for f in result["findings"]))

    def test_contained_burst_reports_no_findings(self):
        self.assertEqual(assess_congestion(OFFERED, SERVICE, DURATION, 500000.0)["findings"], [])

    def test_overflow_time_is_reported_for_a_congested_link(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 500000.0)
        self.assertAlmostEqual(result["time_to_overflow_s"], 2.5, places=9)

    def test_overflow_time_is_absent_without_congestion(self):
        self.assertIsNone(assess_congestion(500000.0, SERVICE, DURATION, 500000.0)["time_to_overflow_s"])

    def test_drain_time_is_reported(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 500000.0)
        self.assertAlmostEqual(result["drain_time_s"], 0.5, places=9)

    def test_required_service_rate_is_carried_in_the_result(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        self.assertAlmostEqual(result["required_service_bps"], 850000.0, places=9)

    def test_required_buffer_is_carried_in_the_result(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        self.assertAlmostEqual(result["required_buffer_bits"], 400000.0, places=9)

    def test_stated_required_rate_actually_contains_the_burst(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        fixed = assess_congestion(OFFERED, result["required_service_bps"], DURATION, 300000.0)
        self.assertTrue(fixed["contained"])

    def test_stated_required_buffer_actually_contains_the_burst(self):
        result = assess_congestion(OFFERED, SERVICE, DURATION, 300000.0)
        fixed = assess_congestion(OFFERED, SERVICE, DURATION, result["required_buffer_bits"])
        self.assertTrue(fixed["contained"])

    def test_bad_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_congestion(OFFERED, SERVICE, 0.0, 300000.0)

    def test_bad_buffer_rejected(self):
        with self.assertRaises(ValueError):
            assess_congestion(OFFERED, SERVICE, DURATION, -1.0)


if __name__ == "__main__":
    unittest.main()
