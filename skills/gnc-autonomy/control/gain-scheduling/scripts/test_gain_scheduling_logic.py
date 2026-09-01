#!/usr/bin/env python3
"""Gate 3 contract test: gain scheduling.

Exercises scripts/gain_scheduling_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: interpolate a gain from a
breakpoint/gain schedule table (nearest and linear methods), clamp or
reject out-of-range scheduling values, validate table monotonicity, and
rate limit the scheduling variable; malformed tables and invalid
arguments raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gain_scheduling_logic as gs  # noqa: E402

# Dynamic-pressure schedule (Pa) -> pitch rate gain (dimensionless):
# gains rise with dynamic pressure because control effectiveness grows.
Q_PA = [(10000.0, 0.5), (20000.0, 1.0), (40000.0, 2.0)]


class ScheduleGainLinearTest(unittest.TestCase):
    def test_midpoint_interpolation(self):
        # Halfway between 10000 Pa (0.5) and 20000 Pa (1.0) -> 0.75
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 15000.0, method="linear"), 0.75, delta=1e-9
        )

    def test_third_point_interpolation(self):
        # One third of the way from 20000 (1.0) to 40000 (2.0) -> 1.3333
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 26666.6667, method="linear"),
            1.0 + (2.0 - 1.0) * (26666.6667 - 20000.0) / 20000.0,
            delta=1e-6,
        )

    def test_linear_is_default_method(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 15000.0), 0.75, delta=1e-9
        )

    def test_exact_breakpoint_returns_table_gain(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 20000.0), 1.0, delta=1e-12
        )
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 10000.0), 0.5, delta=1e-12
        )

    def test_interpolation_is_linear_across_full_span(self):
        # Gain at 30000 Pa must lie exactly on the 20000->40000 segment
        g = gs.schedule_gain(Q_PA, 30000.0, method="linear")
        self.assertAlmostEqual(g, 1.5, delta=1e-9)

    def test_dict_table_sorted_by_breakpoint(self):
        table = {40000.0: 2.0, 10000.0: 0.5, 20000.0: 1.0}
        self.assertAlmostEqual(
            gs.schedule_gain(table, 15000.0, method="linear"), 0.75, delta=1e-9
        )
        self.assertAlmostEqual(
            gs.schedule_gain(table, 30000.0, method="linear"), 1.5, delta=1e-9
        )


class ScheduleGainNearestTest(unittest.TestCase):
    def test_below_midpoint_rounds_down(self):
        # 14999 is closer to 10000 (0.5) than to 20000 (1.0)
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 14999.0, method="nearest"), 0.5, delta=1e-12
        )

    def test_above_midpoint_rounds_up(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 15001.0, method="nearest"), 1.0, delta=1e-12
        )

    def test_tie_rounds_down_by_convention(self):
        # Exactly halfway rounds to the lower breakpoint gain
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 15000.0, method="nearest"), 0.5, delta=1e-12
        )

    def test_exact_breakpoint(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 40000.0, method="nearest"), 2.0, delta=1e-12
        )


class OutOfRangeTest(unittest.TestCase):
    def test_below_range_clamps_to_first_gain(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 0.0), 0.5, delta=1e-12
        )

    def test_above_range_clamps_to_last_gain(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 100000.0), 2.0, delta=1e-12
        )

    def test_clamp_is_default(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, -5000.0, method="linear"), 0.5, delta=1e-12
        )

    def test_error_mode_rejects_below_range(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, 0.0, out_of_range="error")

    def test_error_mode_rejects_above_range(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, 100000.0, out_of_range="error")

    def test_error_mode_accepts_in_range(self):
        self.assertAlmostEqual(
            gs.schedule_gain(Q_PA, 15000.0, out_of_range="error"),
            0.75,
            delta=1e-9,
        )


class TableValidationTest(unittest.TestCase):
    def test_duplicate_breakpoint_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(10000.0, 0.5), (10000.0, 0.9)], 10000.0)

    def test_decreasing_breakpoints_raise(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(40000.0, 2.0), (10000.0, 0.5)], 10000.0)

    def test_single_row_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(10000.0, 0.5)], 10000.0)

    def test_empty_table_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([], 10000.0)

    def test_non_numeric_row_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(10000.0, "high"), (20000.0, 1.0)], 10000.0)
        with self.assertRaises(ValueError):
            gs.schedule_gain([("low", 0.5), (20000.0, 1.0)], 10000.0)

    def test_malformed_row_shape_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(10000.0,), (20000.0, 1.0)], 10000.0)
        with self.assertRaises(ValueError):
            gs.schedule_gain([10000.0, 20000.0], 10000.0)

    def test_bool_entries_raise(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain([(True, 0.5), (20000.0, 1.0)], 10000.0)

    def test_non_iterable_table_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(3.14, 10000.0)

    def test_non_numeric_sched_value_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, "fast")
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, True)

    def test_invalid_method_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, 15000.0, method="cubic")

    def test_invalid_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            gs.schedule_gain(Q_PA, 15000.0, out_of_range="ignore")

    def test_spline_is_overview_only(self):
        # Spline fitting is an overview option, not implemented: the
        # contract test pins the NotImplementedError so the intent stays
        # explicit.
        with self.assertRaises(NotImplementedError):
            gs.schedule_gain(Q_PA, 15000.0, method="spline")


class RateLimitTest(unittest.TestCase):
    def test_within_limit_passes_through(self):
        # 0.5 Pa/s over 2 s allows +1.0; commanded +0.6 arrives fully
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(10000.0, 10000.6, 0.5, 2.0),
            10000.6,
            delta=1e-12,
        )

    def test_exceeding_limit_clamps_to_cap(self):
        # Commanded +2.0 exceeds the 0.5 Pa/s * 2 s = 1.0 cap
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(10000.0, 10002.0, 0.5, 2.0),
            10001.0,
            delta=1e-12,
        )

    def test_negative_step_clamps_down(self):
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(20000.0, 10000.0, 1000.0, 1.0),
            19000.0,
            delta=1e-12,
        )

    def test_zero_max_rate_freezes(self):
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(15000.0, 30000.0, 0.0, 1.0),
            15000.0,
            delta=1e-12,
        )

    def test_rate_limit_never_overshoots_commanded_value(self):
        # Even with a huge cap the applied value never passes new_value
        v = gs.rate_limited_scheduling_variable(10000.0, 10000.3, 1e6, 1.0)
        self.assertLessEqual(v, 10000.3)
        self.assertAlmostEqual(v, 10000.3, delta=1e-9)

    def test_negative_max_rate_raises(self):
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable(10000.0, 20000.0, -1.0, 1.0)

    def test_non_positive_dt_raises(self):
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable(10000.0, 20000.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable(10000.0, 20000.0, 1.0, -0.5)

    def test_non_numeric_inputs_raise(self):
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable("slow", 20000.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable(10000.0, 20000.0, "fast", 1.0)
        with self.assertRaises(ValueError):
            gs.rate_limited_scheduling_variable(10000.0, 20000.0, 1.0, None)

    def test_math_consistency(self):
        # A unit-step with max_rate=dt recovers the commanded value
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(0.0, 1.0, 1.0, 1.0),
            1.0,
            delta=1e-12,
        )
        # And half the rate lands exactly halfway
        self.assertAlmostEqual(
            gs.rate_limited_scheduling_variable(0.0, 1.0, 0.5, 1.0),
            0.5,
            delta=1e-12,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
