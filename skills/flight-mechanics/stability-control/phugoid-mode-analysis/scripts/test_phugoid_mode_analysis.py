#!/usr/bin/env python3
"""Gate 3 contract test: phugoid-mode-analysis logic.

Exercises scripts/phugoid_mode_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the
Lanchester phugoid natural frequency and period, the drag-damping
ratio from lift-to-drag, the damped frequency, the time to half
amplitude and cycles to half amplitude with their speed-scaling and
identity properties, the small-damping L/D validity floor, the summary
dict, and ValueError rejection of non-physical and non-numeric inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phugoid_mode_analysis_logic as ph  # noqa: E402

G = 9.80665

# Worked example: V = 250 m/s, L/D = 18
V = 250.0
LD = 18.0
W_OMEGA_P = 0.05547478972578446   # rad/s
W_PERIOD = 113.26199411007748     # s
W_ZETA = 0.039283710065919304
W_OMEGA_D = 0.05543196857719903   # rad/s
W_T_HALF = 318.066038098612       # s
W_CYCLES = 2.808232722703865


class PhugoidFrequencyTest(unittest.TestCase):
    def test_worked_example_natural_frequency(self):
        self.assertAlmostEqual(ph.phugoid_frequency(V), W_OMEGA_P)

    def test_worked_example_period(self):
        self.assertAlmostEqual(ph.phugoid_period(V), W_PERIOD)

    def test_worked_example_within_one_percent_of_reference(self):
        omega = ph.phugoid_frequency(V)
        period = ph.phugoid_period(V)
        self.assertLess(abs(omega - 0.05547) / 0.05547, 0.01)
        self.assertLess(abs(period - 113.3) / 113.3, 0.01)

    def test_frequency_falls_as_speed_rises(self):
        self.assertGreater(ph.phugoid_frequency(100.0),
                           ph.phugoid_frequency(250.0))

    def test_period_frequency_round_trip(self):
        self.assertAlmostEqual(ph.phugoid_frequency(V) *
                               ph.phugoid_period(V), 2.0 * math.pi)

    def test_non_positive_speed_raises(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                ph.phugoid_frequency(bad)

    def test_non_numeric_speed_raises(self):
        for bad in ("250", None, [250.0]):
            with self.assertRaises(ValueError):
                ph.phugoid_frequency(bad)


class PhugoidDampingTest(unittest.TestCase):
    def test_worked_example_damping_ratio(self):
        self.assertAlmostEqual(ph.phugoid_damping_ratio(LD), W_ZETA)
        self.assertLess(abs(ph.phugoid_damping_ratio(LD) - 0.03928) / 0.03928,
                        0.01)

    def test_higher_ld_gives_less_damping(self):
        self.assertLess(ph.phugoid_damping_ratio(25.0),
                        ph.phugoid_damping_ratio(18.0))

    def test_ld_one_boundary_is_oscillatory(self):
        # L/D = 1 gives zeta = 1 / sqrt(2), still oscillatory
        self.assertAlmostEqual(ph.phugoid_damping_ratio(1.0),
                               1.0 / math.sqrt(2.0))

    def test_ld_below_one_raises(self):
        for bad in (0.0, 0.5, -3.0):
            with self.assertRaises(ValueError):
                ph.phugoid_damping_ratio(bad)

    def test_non_numeric_ld_raises(self):
        for bad in ("18", None):
            with self.assertRaises(ValueError):
                ph.phugoid_damping_ratio(bad)


class DampedFrequencyTest(unittest.TestCase):
    def test_worked_example_damped_frequency(self):
        self.assertAlmostEqual(ph.damped_frequency(V, LD), W_OMEGA_D)

    def test_damped_below_natural_frequency(self):
        self.assertLess(ph.damped_frequency(V, LD), ph.phugoid_frequency(V))

    def test_damped_frequency_close_to_natural_for_large_ld(self):
        # high L/D: zeta small, omega_d practically equals omega_p
        ratio = ph.damped_frequency(250.0, 40.0) / ph.phugoid_frequency(250.0)
        self.assertGreater(ratio, 0.999)

    def test_damped_frequency_validates_inputs(self):
        with self.assertRaises(ValueError):
            ph.damped_frequency(0.0, LD)
        with self.assertRaises(ValueError):
            ph.damped_frequency(V, 0.5)


class TimeToHalfTest(unittest.TestCase):
    def test_worked_example_time_to_half(self):
        self.assertAlmostEqual(ph.time_to_half_amplitude(V, LD), W_T_HALF)
        t = ph.time_to_half_amplitude(V, LD)
        self.assertLess(abs(t - 318.1) / 318.1, 0.01)

    def test_identity_zeta_omega_equals_g_over_v_ld(self):
        zeta = ph.phugoid_damping_ratio(LD)
        omega = ph.phugoid_frequency(V)
        self.assertAlmostEqual(zeta * omega, G / (V * LD))

    def test_closed_form_matches_log_form(self):
        zeta = ph.phugoid_damping_ratio(LD)
        omega = ph.phugoid_frequency(V)
        log_form = math.log(2.0) / (zeta * omega)
        self.assertAlmostEqual(ph.time_to_half_amplitude(V, LD), log_form)

    def test_time_to_half_grows_with_speed(self):
        self.assertLess(ph.time_to_half_amplitude(150.0, LD),
                        ph.time_to_half_amplitude(250.0, LD))

    def test_time_to_half_grows_with_ld(self):
        self.assertLess(ph.time_to_half_amplitude(V, 12.0),
                        ph.time_to_half_amplitude(V, LD))

    def test_time_to_half_validates_inputs(self):
        with self.assertRaises(ValueError):
            ph.time_to_half_amplitude(0.0, LD)
        with self.assertRaises(ValueError):
            ph.time_to_half_amplitude(V, 0.5)
        with self.assertRaises(ValueError):
            ph.time_to_half_amplitude("250", LD)


class CyclesToHalfTest(unittest.TestCase):
    def test_worked_example_cycles_to_half(self):
        self.assertAlmostEqual(ph.cycles_to_half_amplitude(LD), W_CYCLES)
        c = ph.cycles_to_half_amplitude(LD)
        self.assertLess(abs(c - 2.81) / 2.81, 0.01)

    def test_cycles_match_ratio_of_times(self):
        self.assertAlmostEqual(
            ph.cycles_to_half_amplitude(LD),
            ph.time_to_half_amplitude(V, LD) / ph.phugoid_period(V))

    def test_cycles_validates_ld(self):
        with self.assertRaises(ValueError):
            ph.cycles_to_half_amplitude(0.0)


class SmallDampingValidityTest(unittest.TestCase):
    def test_cruise_ld_18_is_valid(self):
        self.assertTrue(ph.ld_valid_for_small_damping(18.0))

    def test_ld_8_boundary_is_valid(self):
        self.assertTrue(ph.ld_valid_for_small_damping(8.0))

    def test_ld_below_8_is_invalid(self):
        self.assertFalse(ph.ld_valid_for_small_damping(7.9))

    def test_validity_validates_inputs(self):
        with self.assertRaises(ValueError):
            ph.ld_valid_for_small_damping(0.0)
        with self.assertRaises(ValueError):
            ph.ld_valid_for_small_damping(18.0, min_ld=0.0)


class PhugoidCharacteristicsTest(unittest.TestCase):
    def test_worked_example_summary(self):
        c = ph.phugoid_characteristics(V, LD)
        self.assertAlmostEqual(c["omega_p"], W_OMEGA_P)
        self.assertAlmostEqual(c["period"], W_PERIOD)
        self.assertAlmostEqual(c["zeta_p"], W_ZETA)
        self.assertAlmostEqual(c["omega_d"], W_OMEGA_D)
        self.assertAlmostEqual(c["t_half"], W_T_HALF)
        self.assertAlmostEqual(c["cycles_half"], W_CYCLES)
        self.assertTrue(c["small_damping_valid"])

    def test_summary_consistency_checks(self):
        c = ph.phugoid_characteristics(V, LD)
        self.assertAlmostEqual(c["cycles_half"],
                               c["t_half"] / c["period"])
        self.assertAlmostEqual(
            c["zeta_p"] * c["omega_p"], G / (V * LD))
        self.assertLessEqual(c["omega_d"], c["omega_p"])

    def test_summary_flags_low_ld(self):
        c = ph.phugoid_characteristics(V, 5.0)
        self.assertFalse(c["small_damping_valid"])
        self.assertGreater(c["zeta_p"], 0.1)

    def test_summary_states_separation_assumption(self):
        c = ph.phugoid_characteristics(V, LD)
        self.assertIn("short period frequency", c["separation_assumption"])

    def test_summary_validates_inputs(self):
        with self.assertRaises(ValueError):
            ph.phugoid_characteristics(0.0, LD)
        with self.assertRaises(ValueError):
            ph.phugoid_characteristics(V, 0.0)
        with self.assertRaises(ValueError):
            ph.phugoid_characteristics(V, "18")


if __name__ == "__main__":
    unittest.main(verbosity=2)
