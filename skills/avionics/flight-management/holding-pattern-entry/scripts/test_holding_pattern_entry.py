"""Contract test for the holding-pattern-entry leaf (wave-37).

Deterministic, offline, stdlib only. Run with:

    python3 scripts/test_holding_pattern_entry.py

Covers the entry truth table across the 70 and 110 degree boundaries,
left-hand mirroring, the outbound leg timing truth table at 14000 ft and
just above, the 1-in-60 wind correction anchor (4.71 deg at the worked
example, within 0.1 deg), sign reversal for a wind 180 degrees opposite,
heading normalization to [0, 360), the entry-lap time offsets, float
output types, determinism, and ValueError rejection of non-physical
inputs (alpha outside [0, 180], bad turn direction, negative altitude,
non-positive TAS, negative wind speed, unknown entry, non-positive
outbound leg time).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from holding_pattern_entry_logic import (  # noqa: E402
    entry_type,
    outbound_leg_seconds,
    wind_correction_heading,
    entry_lap_time_seconds,
)


class TestEntryType(unittest.TestCase):
    """70/110 degree sector rule on the holding side."""

    def test_entry_alpha_0_direct(self):
        self.assertEqual(entry_type(0.0, "right"), "direct")

    def test_entry_alpha_50_direct(self):
        # Worked example: alpha 50 deg is a direct entry.
        self.assertEqual(entry_type(50.0, "right"), "direct")

    def test_entry_alpha_70_boundary_direct(self):
        # Boundary: alpha exactly 70 deg is still direct.
        self.assertEqual(entry_type(70.0, "right"), "direct")

    def test_entry_alpha_70_plus_teardrop(self):
        self.assertEqual(entry_type(70.001, "right"), "teardrop")

    def test_entry_alpha_90_teardrop(self):
        # Worked example: alpha 90 deg is a teardrop entry.
        self.assertEqual(entry_type(90.0, "right"), "teardrop")

    def test_entry_alpha_110_boundary_teardrop(self):
        # Boundary: alpha exactly 110 deg is still teardrop.
        self.assertEqual(entry_type(110.0, "right"), "teardrop")

    def test_entry_alpha_110_plus_parallel(self):
        self.assertEqual(entry_type(110.001, "right"), "parallel")

    def test_entry_alpha_130_parallel(self):
        # Worked example: alpha 130 deg is a parallel entry.
        self.assertEqual(entry_type(130.0, "right"), "parallel")

    def test_entry_alpha_180_parallel(self):
        self.assertEqual(entry_type(180.0, "right"), "parallel")

    def test_left_hand_mirror_same_rule(self):
        # alpha measured on the holding side: the sectors mirror and the
        # same thresholds apply for a left-hand hold.
        for alpha in (50.0, 90.0, 130.0, 70.0, 110.0):
            self.assertEqual(
                entry_type(alpha, "left"), entry_type(alpha, "right")
            )

    def test_entry_alpha_negative_valueerror(self):
        with self.assertRaises(ValueError):
            entry_type(-1.0, "right")

    def test_entry_alpha_above_180_valueerror(self):
        with self.assertRaises(ValueError):
            entry_type(180.001, "right")

    def test_entry_bad_turn_direction_valueerror(self):
        with self.assertRaises(ValueError):
            entry_type(90.0, "center")


class TestOutboundLegTiming(unittest.TestCase):
    """1 minute at or below 14000 ft, 1.5 minutes above."""

    def test_leg_at_sea_level_60(self):
        self.assertEqual(outbound_leg_seconds(0.0), 60.0)

    def test_leg_at_14000_60(self):
        # Boundary: exactly 14000 ft still gets the 1 minute leg.
        self.assertEqual(outbound_leg_seconds(14000.0), 60.0)

    def test_leg_just_above_14000_90(self):
        self.assertEqual(outbound_leg_seconds(14001.0), 90.0)

    def test_leg_at_20000_90(self):
        # Worked example: 20000 ft gives the 1.5 minute leg.
        self.assertEqual(outbound_leg_seconds(20000.0), 90.0)

    def test_leg_negative_altitude_valueerror(self):
        with self.assertRaises(ValueError):
            outbound_leg_seconds(-1.0)


class TestWindCorrection(unittest.TestCase):
    """1-in-60 crosswind correction on the outbound heading."""

    def setUp(self):
        # Worked example: outbound heading 090, wind from 135 at 20 kt,
        # TAS 180 kt.
        self.anchor = wind_correction_heading(90.0, 135.0, 20.0, 180.0)

    def test_wind_correction_anchor(self):
        # Anchor: correction 4.71 deg within 0.1 deg, heading near 094.7.
        self.assertAlmostEqual(self.anchor - 90.0, 4.71, delta=0.1)
        self.assertAlmostEqual(self.anchor, 94.7140, delta=0.01)

    def test_wind_correction_sign_reversal(self):
        # Wind 180 degrees opposite (from 315) reverses the correction
        # sign; the two corrected headings sum to 180 degrees.
        reversed_head = wind_correction_heading(90.0, 315.0, 20.0, 180.0)
        self.assertAlmostEqual(reversed_head, 85.2860, delta=0.01)
        self.assertAlmostEqual(self.anchor + reversed_head, 180.0, places=6)

    def test_wind_correction_no_crosswind(self):
        # Wind from the same direction as the outbound heading.
        self.assertEqual(
            wind_correction_heading(90.0, 90.0, 20.0, 180.0), 90.0
        )

    def test_wind_correction_tailwind_no_drift(self):
        # Pure tailwind (wind from 270 toward 090) has no crosswind.
        self.assertEqual(
            wind_correction_heading(90.0, 270.0, 20.0, 180.0), 90.0
        )

    def test_wind_correction_scales_with_wind_speed(self):
        # Doubling the wind doubles the correction (linear 1-in-60 rule).
        double_wind = wind_correction_heading(90.0, 135.0, 40.0, 180.0)
        self.assertAlmostEqual(
            double_wind - 90.0, 2.0 * (self.anchor - 90.0), places=6
        )

    def test_wind_heading_wrap_below_360(self):
        # Corrected heading normalizes into [0, 360).
        wrapped = wind_correction_heading(359.0, 90.0, 20.0, 180.0)
        self.assertGreaterEqual(wrapped, 0.0)
        self.assertLess(wrapped, 360.0)
        self.assertAlmostEqual(wrapped, 5.6657, delta=0.1)

    def test_wind_tas_zero_valueerror(self):
        with self.assertRaises(ValueError):
            wind_correction_heading(90.0, 135.0, 20.0, 0.0)

    def test_wind_tas_negative_valueerror(self):
        with self.assertRaises(ValueError):
            wind_correction_heading(90.0, 135.0, 20.0, -100.0)

    def test_wind_negative_speed_valueerror(self):
        with self.assertRaises(ValueError):
            wind_correction_heading(90.0, 135.0, -5.0, 180.0)


class TestEntryLapTime(unittest.TestCase):
    """First lap = one outbound leg plus the sector-geometry offset."""

    def test_lap_direct_240(self):
        # Worked example: 12000 ft direct entry, 60 + 3 * 60 = 240 s.
        self.assertEqual(entry_lap_time_seconds("direct", 60.0), 240.0)

    def test_lap_teardrop_300(self):
        self.assertEqual(entry_lap_time_seconds("teardrop", 60.0), 300.0)

    def test_lap_parallel_360(self):
        self.assertEqual(entry_lap_time_seconds("parallel", 60.0), 360.0)

    def test_lap_90s_outbound_offsets(self):
        # 20000 ft leg: direct 270, teardrop 330, parallel 390.
        self.assertEqual(entry_lap_time_seconds("direct", 90.0), 270.0)
        self.assertEqual(entry_lap_time_seconds("teardrop", 90.0), 330.0)
        self.assertEqual(entry_lap_time_seconds("parallel", 90.0), 390.0)

    def test_lap_bad_entry_valueerror(self):
        with self.assertRaises(ValueError):
            entry_lap_time_seconds("random", 60.0)

    def test_lap_nonpositive_outbound_valueerror(self):
        with self.assertRaises(ValueError):
            entry_lap_time_seconds("direct", 0.0)


class TestDeterminismAndTypes(unittest.TestCase):
    """Float outputs and repeat-call determinism."""

    def test_float_outputs(self):
        self.assertIsInstance(outbound_leg_seconds(12000.0), float)
        self.assertIsInstance(outbound_leg_seconds(20000.0), float)
        self.assertIsInstance(
            wind_correction_heading(90.0, 135.0, 20.0, 180.0), float
        )
        self.assertIsInstance(
            entry_lap_time_seconds("direct", 60.0), float
        )
        self.assertIsInstance(entry_type(90.0, "right"), str)

    def test_determinism(self):
        first = wind_correction_heading(90.0, 135.0, 20.0, 180.0)
        second = wind_correction_heading(90.0, 135.0, 20.0, 180.0)
        self.assertEqual(first, second)
        self.assertEqual(
            entry_lap_time_seconds("teardrop", 90.0),
            entry_lap_time_seconds("teardrop", 90.0),
        )
        # Closed-form identity: lap time minus the outbound leg equals
        # the documented offset for each entry type.
        self.assertEqual(
            entry_lap_time_seconds("direct", 90.0) - 90.0, 180.0
        )
        self.assertEqual(
            entry_lap_time_seconds("parallel", 60.0) - 60.0, 300.0
        )


if __name__ == "__main__":
    unittest.main()
