#!/usr/bin/env python3
"""Gate 3 contract test for the stall characteristics testing leaf.

Stdlib unittest only, offline, no network. Run directly:
python3 scripts/test_stall_characteristics_testing.py
"""

import math
import unittest

from stall_characteristics_testing_logic import (
    DEFAULT_ENTRY_DECEL_MPS2,
    DEFAULT_WARNING_MARGIN,
    KTS_TO_MPS,
    accelerated_stall_speed,
    entry_deceleration_time,
    level_turn_load_factor,
    stall_recovery_verdict,
    stall_warning_on_time,
    stall_warning_speed,
)

# Reference 1g stall speed (m/s EAS) of the standard wing: W/S = 6000
# Pa, CL_max = 1.8, rho = 1.225 kg/m^3.
VS1G = 73.771


class AcceleratedStallSpeedTests(unittest.TestCase):
    def test_reference_case(self):
        # V = 73.771 * sqrt(1.3) ~ 84.11 m/s.
        self.assertAlmostEqual(
            accelerated_stall_speed(VS1G, 1.3), 84.11, places=2
        )

    def test_one_g_matches_vs1g(self):
        self.assertAlmostEqual(
            accelerated_stall_speed(VS1G, 1.0), VS1G, places=9
        )

    def test_scales_with_sqrt_load_factor(self):
        v13 = accelerated_stall_speed(VS1G, 1.3)
        v2 = accelerated_stall_speed(VS1G, 2.0)
        self.assertAlmostEqual(v2 / v13, math.sqrt(2.0 / 1.3), places=4)

    def test_60_degree_bank_raises_by_sqrt2(self):
        v = accelerated_stall_speed(VS1G, level_turn_load_factor(60.0))
        self.assertAlmostEqual(v / VS1G, math.sqrt(2.0), places=4)

    def test_zero_vs1g_raises(self):
        with self.assertRaises(ValueError):
            accelerated_stall_speed(0.0, 1.3)

    def test_negative_vs1g_raises(self):
        with self.assertRaises(ValueError):
            accelerated_stall_speed(-10.0, 1.3)

    def test_load_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            accelerated_stall_speed(VS1G, 0.9)


class LevelTurnLoadFactorTests(unittest.TestCase):
    def test_60_degree_bank(self):
        # n = 1/cos(60 deg) = 2.0.
        self.assertAlmostEqual(level_turn_load_factor(60.0), 2.0, places=9)

    def test_45_degree_bank(self):
        self.assertAlmostEqual(
            level_turn_load_factor(45.0), math.sqrt(2.0), places=9
        )

    def test_wings_level(self):
        self.assertAlmostEqual(level_turn_load_factor(0.0), 1.0, places=9)

    def test_negative_bank_matches_positive(self):
        self.assertAlmostEqual(
            level_turn_load_factor(-30.0),
            level_turn_load_factor(30.0),
            places=9,
        )

    def test_90_degree_bank_raises(self):
        with self.assertRaises(ValueError):
            level_turn_load_factor(90.0)
        with self.assertRaises(ValueError):
            level_turn_load_factor(-90.0)


class StallWarningTests(unittest.TestCase):
    def test_warning_speed_five_percent(self):
        # 73.771 * 1.05 ~ 77.46 m/s.
        self.assertAlmostEqual(
            stall_warning_speed(VS1G, DEFAULT_WARNING_MARGIN), 77.46, places=2
        )

    def test_warning_speed_default_margin(self):
        self.assertAlmostEqual(
            stall_warning_speed(VS1G), 77.46, places=2
        )

    def test_zero_margin_warning_at_stall_speed(self):
        self.assertAlmostEqual(
            stall_warning_speed(VS1G, 0.0), VS1G, places=9
        )

    def test_warning_on_time_at_exact_margin(self):
        v = stall_warning_on_time(77.46, VS1G, DEFAULT_WARNING_MARGIN)
        self.assertTrue(v["warning_in_time"])
        self.assertTrue(v["ok"])
        self.assertAlmostEqual(v["achieved_margin"], 0.05, places=2)

    def test_warning_below_margin_fails(self):
        v = stall_warning_on_time(75.0, VS1G, DEFAULT_WARNING_MARGIN)
        self.assertFalse(v["warning_in_time"])
        self.assertFalse(v["ok"])
        self.assertAlmostEqual(v["achieved_margin"], 75.0 / VS1G - 1.0, places=9)

    def test_larger_required_margin_fails(self):
        # 77.46 m/s meets 5 percent but not 10 percent.
        v = stall_warning_on_time(77.46, VS1G, 0.10)
        self.assertFalse(v["warning_in_time"])
        self.assertFalse(v["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            stall_warning_speed(0.0, 0.05)
        with self.assertRaises(ValueError):
            stall_warning_speed(VS1G, -0.01)
        with self.assertRaises(ValueError):
            stall_warning_on_time(0.0, VS1G, 0.05)
        with self.assertRaises(ValueError):
            stall_warning_on_time(77.46, 0.0, 0.05)
        with self.assertRaises(ValueError):
            stall_warning_on_time(77.46, VS1G, -0.01)


class EntryDecelerationTimeTests(unittest.TestCase):
    def test_one_knot_per_second_entry(self):
        # (100 - 73.771) / 0.514444 ~ 50.99 s.
        self.assertAlmostEqual(
            entry_deceleration_time(100.0, VS1G), 50.99, places=2
        )

    def test_default_rate_is_one_knot_per_second(self):
        self.assertAlmostEqual(
            DEFAULT_ENTRY_DECEL_MPS2, KTS_TO_MPS, places=9
        )

    def test_half_deceleration_doubles_time(self):
        t_full = entry_deceleration_time(100.0, VS1G,
                                         DEFAULT_ENTRY_DECEL_MPS2)
        t_half = entry_deceleration_time(100.0, VS1G,
                                         0.5 * DEFAULT_ENTRY_DECEL_MPS2)
        self.assertAlmostEqual(t_half / t_full, 2.0, places=9)

    def test_longer_segment_takes_longer(self):
        t1 = entry_deceleration_time(100.0, VS1G)
        t2 = entry_deceleration_time(120.0, VS1G)
        self.assertGreater(t2, t1)

    def test_entry_at_stall_speed_raises(self):
        with self.assertRaises(ValueError):
            entry_deceleration_time(VS1G, VS1G)
        with self.assertRaises(ValueError):
            entry_deceleration_time(60.0, VS1G)

    def test_zero_stall_speed_raises(self):
        with self.assertRaises(ValueError):
            entry_deceleration_time(100.0, 0.0)

    def test_zero_deceleration_raises(self):
        with self.assertRaises(ValueError):
            entry_deceleration_time(100.0, VS1G, 0.0)


class StallRecoveryVerdictTests(unittest.TestCase):
    def test_nominal_recovery_passes(self):
        # 80 m loss < 150 limit, 5 deg pitch-up < 10, 15 deg roll < 20.
        v = stall_recovery_verdict(80.0, 150.0, 5.0, 10.0, 15.0, 20.0)
        self.assertTrue(v["altitude_loss_ok"])
        self.assertTrue(v["pitch_up_ok"])
        self.assertTrue(v["roll_off_ok"])
        self.assertTrue(v["ok"])

    def test_excessive_altitude_loss_fails(self):
        v = stall_recovery_verdict(200.0, 150.0, 5.0, 10.0, 15.0, 20.0)
        self.assertFalse(v["altitude_loss_ok"])
        self.assertFalse(v["ok"])

    def test_excessive_pitch_up_fails(self):
        v = stall_recovery_verdict(80.0, 150.0, 12.0, 10.0, 15.0, 20.0)
        self.assertFalse(v["pitch_up_ok"])
        self.assertFalse(v["ok"])

    def test_excessive_roll_off_fails(self):
        v = stall_recovery_verdict(80.0, 150.0, 5.0, 10.0, 25.0, 20.0)
        self.assertFalse(v["roll_off_ok"])
        self.assertFalse(v["ok"])

    def test_boundary_values_pass(self):
        v = stall_recovery_verdict(150.0, 150.0, 10.0, 10.0, 20.0, 20.0)
        self.assertTrue(v["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            stall_recovery_verdict(-1.0, 150.0, 5.0, 10.0, 15.0, 20.0)
        with self.assertRaises(ValueError):
            stall_recovery_verdict(80.0, 0.0, 5.0, 10.0, 15.0, 20.0)
        with self.assertRaises(ValueError):
            stall_recovery_verdict(80.0, 150.0, 5.0, 0.0, 15.0, 20.0)
        with self.assertRaises(ValueError):
            stall_recovery_verdict(80.0, 150.0, 5.0, 10.0, -1.0, 20.0)
        with self.assertRaises(ValueError):
            stall_recovery_verdict(80.0, 150.0, 5.0, 10.0, 15.0, 0.0)


if __name__ == "__main__":
    unittest.main()
