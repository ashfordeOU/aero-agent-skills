"""Contract tests for the clause 5.6.14.4 isochronous service logic."""

import unittest

from e50_isochronous_services_logic import (
    ISOCHRONOUS,
    JITTER_EXCEEDED,
    RATE_DRIFT,
    assess_isochronous_service,
    deviations,
    ideal_grid,
    measured_period,
    minimum_tolerance,
    peak_to_peak_jitter,
    rate_error,
    required_playout_buffer_bits,
    required_playout_buffer_s,
    sustainable_rate_error,
    validate_delivery_times,
    validate_period,
    validate_tolerance,
    worst_deviation,
)

PERIOD = 0.25
ON_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
# Alternating early and late: a perfect mean rate that is never on time.
JITTERED = [0.0, 0.3125, 0.5, 0.6875, 1.0]
# A steady slip of 0.015625 s per delivery: a perfect-looking interval that
# walks the stream off the grid.
DRIFTING = [0.0, 0.265625, 0.53125, 0.796875, 1.0625]


class ValidationTests(unittest.TestCase):
    def test_positive_period_accepted(self):
        self.assertAlmostEqual(validate_period(0.25), 0.25, places=9)

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(0.0)

    def test_negative_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(-0.25)

    def test_boolean_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(True)

    def test_text_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period("0.25")

    def test_infinite_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_period(float("inf"))

    def test_zero_tolerance_accepted(self):
        self.assertAlmostEqual(validate_tolerance(0), 0.0, places=9)

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerance(-1e-3)

    def test_single_delivery_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_times([0.0])

    def test_non_increasing_deliveries_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_times([0.0, 0.25, 0.25])

    def test_string_of_deliveries_rejected(self):
        with self.assertRaises(ValueError):
            validate_delivery_times("0.0,0.25")


class GridTests(unittest.TestCase):
    def test_grid_starts_at_the_epoch(self):
        self.assertAlmostEqual(ideal_grid(4.0, PERIOD, 3)[0], 4.0, places=9)

    def test_grid_steps_by_the_period(self):
        grid = ideal_grid(0.0, PERIOD, 4)
        self.assertAlmostEqual(grid[3] - grid[2], PERIOD, places=9)

    def test_zero_slots_rejected(self):
        with self.assertRaises(ValueError):
            ideal_grid(0.0, PERIOD, 0)


class DeviationTests(unittest.TestCase):
    def test_on_grid_run_has_no_deviation(self):
        self.assertAlmostEqual(worst_deviation(deviations(ON_GRID, PERIOD)), 0.0, places=9)

    def test_first_delivery_anchors_the_default_grid(self):
        self.assertAlmostEqual(deviations(JITTERED, PERIOD)[0], 0.0, places=9)

    def test_declared_epoch_shifts_every_deviation(self):
        shifted = deviations(ON_GRID, PERIOD, epoch_s=-0.125)
        self.assertAlmostEqual(shifted[0], 0.125, places=9)
        self.assertAlmostEqual(shifted[4], 0.125, places=9)

    def test_late_delivery_reads_positive(self):
        self.assertAlmostEqual(deviations(JITTERED, PERIOD)[1], 0.0625, places=9)

    def test_early_delivery_reads_negative(self):
        self.assertAlmostEqual(deviations(JITTERED, PERIOD)[3], -0.0625, places=9)

    def test_peak_to_peak_spans_early_to_late(self):
        self.assertAlmostEqual(peak_to_peak_jitter(deviations(JITTERED, PERIOD)), 0.125, places=9)

    def test_empty_deviations_rejected(self):
        with self.assertRaises(ValueError):
            peak_to_peak_jitter([])


class RateTests(unittest.TestCase):
    def test_on_grid_run_measures_the_nominal_period(self):
        self.assertAlmostEqual(measured_period(ON_GRID), PERIOD, places=9)

    def test_alternating_jitter_keeps_a_perfect_mean_rate(self):
        self.assertAlmostEqual(rate_error(JITTERED, PERIOD), 0.0, places=9)

    def test_steady_slip_shows_as_a_rate_error(self):
        self.assertAlmostEqual(rate_error(DRIFTING, PERIOD), 0.015625, places=9)

    def test_longer_runs_absorb_less_rate_error(self):
        self.assertAlmostEqual(sustainable_rate_error(0.03125, 5), 0.0078125, places=9)

    def test_a_single_delivery_has_no_rate_budget(self):
        self.assertIsNone(sustainable_rate_error(0.03125, 1))


class SizingTests(unittest.TestCase):
    def test_minimum_tolerance_is_the_worst_deviation(self):
        self.assertAlmostEqual(minimum_tolerance(JITTERED, PERIOD), 0.0625, places=9)

    def test_playout_buffer_is_the_peak_to_peak_spread(self):
        self.assertAlmostEqual(required_playout_buffer_s(JITTERED, PERIOD), 0.125, places=9)

    def test_buffer_in_bits_follows_the_source_rate(self):
        self.assertAlmostEqual(required_playout_buffer_bits(0.125, 1000000.0), 125000.0, places=9)

    def test_negative_buffer_rejected(self):
        with self.assertRaises(ValueError):
            required_playout_buffer_bits(-0.1, 1000000.0)

    def test_negative_source_rate_rejected(self):
        with self.assertRaises(ValueError):
            required_playout_buffer_bits(0.125, -1.0)


class AssessTests(unittest.TestCase):
    def test_on_grid_run_conforms(self):
        result = assess_isochronous_service(ON_GRID, PERIOD, 0.03125)
        self.assertEqual(result["verdict"], ISOCHRONOUS)
        self.assertTrue(result["within_tolerance"])

    def test_run_sitting_exactly_on_the_bound_conforms(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.0625)
        self.assertAlmostEqual(result["worst_deviation_s"], result["jitter_tolerance_s"], places=9)
        self.assertEqual(result["verdict"], ISOCHRONOUS)

    def test_bounded_jitter_beyond_the_bound_is_not_a_rate_fault(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.03125)
        self.assertEqual(result["verdict"], JITTER_EXCEEDED)
        self.assertAlmostEqual(result["rate_error_s"], 0.0, places=9)

    def test_steady_slip_is_graded_as_rate_drift(self):
        result = assess_isochronous_service(DRIFTING, PERIOD, 0.03125)
        self.assertEqual(result["verdict"], RATE_DRIFT)

    def test_rate_drift_says_no_fixed_buffer_holds_it(self):
        result = assess_isochronous_service(DRIFTING, PERIOD, 0.03125)
        self.assertTrue(any("no buffer of fixed depth" in f for f in result["findings"]))

    def test_jitter_failure_offers_both_ways_out(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.03125)
        self.assertTrue(any("or a playout buffer of" in f for f in result["findings"]))

    def test_conforming_run_reports_no_findings(self):
        self.assertEqual(assess_isochronous_service(ON_GRID, PERIOD, 0.03125)["findings"], [])

    def test_late_and_early_slots_are_named(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.03125)
        self.assertEqual(result["late_slots"], [1])
        self.assertEqual(result["early_slots"], [3])

    def test_stated_minimum_tolerance_actually_accepts_the_run(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.03125)
        fixed = assess_isochronous_service(JITTERED, PERIOD, result["minimum_tolerance_s"])
        self.assertEqual(fixed["verdict"], ISOCHRONOUS)

    def test_playout_buffer_is_carried_in_bits(self):
        result = assess_isochronous_service(JITTERED, PERIOD, 0.03125, source_bps=1000000.0)
        self.assertAlmostEqual(result["required_playout_buffer_bits"], 125000.0, places=9)

    def test_mean_rate_alone_would_have_passed_both_failures(self):
        for run in (JITTERED, DRIFTING):
            result = assess_isochronous_service(run, PERIOD, 0.03125)
            self.assertNotEqual(result["verdict"], ISOCHRONOUS)

    def test_bad_period_rejected(self):
        with self.assertRaises(ValueError):
            assess_isochronous_service(ON_GRID, 0.0, 0.03125)

    def test_bad_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            assess_isochronous_service(ON_GRID, PERIOD, -0.01)


if __name__ == "__main__":
    unittest.main()
