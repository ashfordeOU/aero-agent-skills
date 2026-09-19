"""Contract tests for the clause 5.7.4.5 time synchronization logic."""

import unittest

from e50_time_synchronization_logic import (
    HELD,
    LOST,
    SPEED_OF_LIGHT_MPS,
    assess_synchronization,
    clock_offset_s,
    drift_error_ns,
    estimate_error_ns,
    max_sync_interval_s,
    motion_asymmetry_s,
    one_way_delay_s,
    round_trip_s,
    turnaround_s,
    validate_exchange,
    validate_nonnegative,
    validate_positive,
)

T1, T2, T3, T4 = 0.0, 1.2, 1.7, 2.5
ASYMMETRY = 2e-9
RANGE_RATE = 1.0
RESOLUTION = 1e-8
JITTER = 5.0
DRIFT_PPM = 2.0
INTERVAL = 60.0
WINDOW = 200000.0


def graded(**override):
    args = {
        "t1": T1,
        "t2": T2,
        "t3": T3,
        "t4": T4,
        "path_asymmetry_s": ASYMMETRY,
        "range_rate_mps": RANGE_RATE,
        "timestamp_resolution_s": RESOLUTION,
        "jitter_ns": JITTER,
        "relative_drift_ppm": DRIFT_PPM,
        "interval_s": INTERVAL,
        "required_ns": WINDOW,
    }
    args.update(override)
    return assess_synchronization(**args)


class ValidationTests(unittest.TestCase):
    def test_zero_is_a_valid_nonnegative(self):
        self.assertAlmostEqual(validate_nonnegative(0), 0.0, places=9)

    def test_negative_asymmetry_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1e-9, "path_asymmetry_s")

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive(True)

    def test_text_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_positive("60")

    def test_not_a_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(float("nan"))

    def test_reply_before_the_request_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchange(2.0, 1.2, 1.7, 1.0)

    def test_responder_timestamps_out_of_order_rejected(self):
        with self.assertRaises(ValueError):
            validate_exchange(0.0, 1.7, 1.2, 2.5)

    def test_a_clock_offset_is_not_an_ordering_error(self):
        self.assertEqual(validate_exchange(0.0, 500.0, 500.5, 2.5)[1], 500.0)

    def test_a_hold_longer_than_the_round_trip_rejected(self):
        with self.assertRaises(ValueError):
            round_trip_s(0.0, 1.0, 5.0, 2.5)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            drift_error_ns(DRIFT_PPM, 0.0)


class ExchangeTests(unittest.TestCase):
    def test_turnaround_is_the_responder_hold(self):
        self.assertAlmostEqual(turnaround_s(T1, T2, T3, T4), 0.5, places=9)

    def test_round_trip_removes_the_hold(self):
        self.assertAlmostEqual(round_trip_s(T1, T2, T3, T4), 2.0, places=9)

    def test_one_way_delay_is_half_the_round_trip(self):
        self.assertAlmostEqual(one_way_delay_s(T1, T2, T3, T4), 1.0, places=9)

    def test_offset_is_recovered_from_the_four_timestamps(self):
        self.assertAlmostEqual(clock_offset_s(T1, T2, T3, T4), 0.2, places=9)

    def test_a_synchronized_pair_shows_no_offset(self):
        self.assertAlmostEqual(clock_offset_s(0.0, 1.0, 1.5, 2.5), 0.0, places=9)

    def test_offset_does_not_move_with_the_hold_time(self):
        short = clock_offset_s(0.0, 1.2, 1.7, 2.5)
        long = clock_offset_s(0.0, 1.2, 2.7, 3.5)
        self.assertAlmostEqual(short, long, places=9)

    def test_a_longer_path_lengthens_the_round_trip(self):
        self.assertGreater(round_trip_s(0.0, 1.2, 1.7, 4.5), round_trip_s(T1, T2, T3, T4))


class MotionTests(unittest.TestCase):
    def test_a_stationary_pair_opens_no_motion_asymmetry(self):
        self.assertAlmostEqual(motion_asymmetry_s(0.0, 0.5), 0.0, places=15)

    def test_motion_asymmetry_grows_with_the_hold_time(self):
        self.assertGreater(motion_asymmetry_s(100.0, 5.0), motion_asymmetry_s(100.0, 0.5))

    def test_closing_and_opening_motion_cost_the_same(self):
        self.assertAlmostEqual(
            motion_asymmetry_s(-100.0, 0.5), motion_asymmetry_s(100.0, 0.5), places=15
        )

    def test_motion_asymmetry_is_range_rate_times_hold_over_light_speed(self):
        self.assertAlmostEqual(
            motion_asymmetry_s(100.0, 0.5), 100.0 * 0.5 / SPEED_OF_LIGHT_MPS, places=15
        )


class EstimateTests(unittest.TestCase):
    def test_path_asymmetry_enters_at_half(self):
        estimate = estimate_error_ns(2e-9, 0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(estimate["path_asymmetry_ns"], 1.0, places=9)

    def test_timestamp_resolution_enters_at_half(self):
        estimate = estimate_error_ns(0.0, 0.0, 0.0, 1e-8, 0.0)
        self.assertAlmostEqual(estimate["resolution_ns"], 5.0, places=9)

    def test_jitter_is_carried_separately(self):
        estimate = estimate_error_ns(0.0, 0.0, 0.0, 0.0, 5.0)
        self.assertAlmostEqual(estimate["jitter_ns"], 5.0, places=9)

    def test_total_is_the_systematic_sum_plus_jitter(self):
        estimate = estimate_error_ns(2e-9, 100.0, 0.5, 1e-8, 5.0)
        self.assertAlmostEqual(
            estimate["total_ns"], estimate["systematic_ns"] + 5.0, places=9
        )

    def test_a_perfect_exchange_leaves_no_error(self):
        estimate = estimate_error_ns(0.0, 0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(estimate["total_ns"], 0.0, places=12)

    def test_a_negative_resolution_is_rejected(self):
        with self.assertRaises(ValueError):
            estimate_error_ns(0.0, 0.0, 0.0, -1e-9, 0.0)


class IntervalTests(unittest.TestCase):
    def test_drift_grows_with_the_interval(self):
        self.assertAlmostEqual(drift_error_ns(2.0, 60.0), 120000.0, places=6)

    def test_drift_is_linear_in_the_relative_rate(self):
        self.assertAlmostEqual(
            drift_error_ns(4.0, 60.0), 2.0 * drift_error_ns(2.0, 60.0), places=6
        )

    def test_longest_interval_spends_exactly_the_remaining_window(self):
        interval = max_sync_interval_s(94.0, 2.0, WINDOW)
        self.assertAlmostEqual(94.0 + drift_error_ns(2.0, interval), WINDOW, places=6)

    def test_an_exchange_that_fills_the_window_returns_zero(self):
        self.assertAlmostEqual(max_sync_interval_s(300000.0, 2.0, WINDOW), 0.0, places=9)

    def test_no_relative_drift_means_the_interval_is_unconstrained(self):
        self.assertIsNone(max_sync_interval_s(94.0, 0.0, WINDOW))

    def test_a_tighter_window_shortens_the_interval(self):
        loose = max_sync_interval_s(94.0, 2.0, 400000.0)
        tight = max_sync_interval_s(94.0, 2.0, 100000.0)
        self.assertLess(tight, loose)

    def test_zero_window_rejected(self):
        with self.assertRaises(ValueError):
            max_sync_interval_s(94.0, 2.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_pair_holds_synchronization(self):
        self.assertEqual(graded()["verdict"], HELD)

    def test_a_long_interval_loses_synchronization(self):
        self.assertEqual(graded(interval_s=600.0)["verdict"], LOST)

    def test_a_budget_landing_on_the_window_still_holds(self):
        total = graded()["total_ns"]
        self.assertEqual(graded(required_ns=total)["verdict"], HELD)

    def test_the_stated_interval_remedy_actually_holds_the_pair(self):
        result = graded(interval_s=600.0)
        fixed = graded(interval_s=result["max_interval_s"])
        self.assertEqual(fixed["verdict"], HELD)

    def test_an_exchange_that_fills_the_window_is_told_so(self):
        result = graded(required_ns=10.0)
        self.assertTrue(any("cannot recover it" in f for f in result["findings"]))

    def test_dominant_relative_motion_is_called_out(self):
        result = graded(range_rate_mps=8000.0)
        self.assertTrue(any("relative motion contributes" in f for f in result["findings"]))

    def test_a_slow_pair_does_not_raise_the_motion_finding(self):
        result = graded(range_rate_mps=0.1)
        self.assertFalse(any("relative motion contributes" in f for f in result["findings"]))

    def test_margin_is_the_window_less_the_budget(self):
        result = graded()
        self.assertAlmostEqual(
            result["margin_ns"], result["required_ns"] - result["total_ns"], places=6
        )

    def test_the_measured_offset_is_carried_in_the_result(self):
        self.assertAlmostEqual(graded()["offset_s"], 0.2, places=9)

    def test_a_sound_pair_raises_no_findings(self):
        self.assertEqual(graded()["findings"], [])

    def test_a_bad_exchange_is_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            graded(t4=-1.0)

    def test_a_zero_window_is_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            graded(required_ns=0.0)


if __name__ == "__main__":
    unittest.main()
