"""Deterministic offline contract test for rta_time_control_logic.

Run with: python3 scripts/test_rta_time_control.py
Asserts the wave-28 spec worked example: leg remaining 450000 m, ground
speed 250 m/s, wind along +15 m/s, altitude 10668 m (a = 296.53 m/s from
the module constants; the spec display rounds it to 296.51), Mach envelope
[0.72, 0.84], t_now = 0. Anchor values: eta 1800 s, required ground speed
236.84 m/s, required Mach 0.74818, hold Mach 0.79257, window 1704.1 s to
1969.4 s, unfeasible fast case remaining error 504.1 s.
"""

import os
import sys
import unittest

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

import rta_time_control_logic as rta

DIST = 450000.0       # remaining distance, m (about 243 NM)
GS = 250.0            # current ground speed, m/s
WIND = 15.0           # along-track wind, m/s (tailwind positive)
ALT = 10668.0         # cruise altitude, m
MACH_MIN = 0.72
MACH_MAX = 0.84

BASE = {
    "remaining_distance_m": DIST,
    "ground_speed_m_s": GS,
    "wind_along_m_s": WIND,
    "rta_time_s": 1900.0,
    "t_now_s": 0.0,
    "altitude_m": ALT,
    "mach_min": MACH_MIN,
    "mach_max": MACH_MAX,
}


class IsaSpeedOfSoundTests(unittest.TestCase):
    """ISA speed of sound model."""

    def test_isa_speed_of_sound_sea_level(self):
        """Sea level speed of sound is about 340.29 m/s."""
        a0 = rta.isa_speed_of_sound(0.0)
        self.assertAlmostEqual(a0, 340.29, delta=0.01)

    def test_isa_speed_of_sound_at_cruise_altitude(self):
        """a(10668 m) is about 296.53 m/s, near the spec display 296.51."""
        a = rta.isa_speed_of_sound(ALT)
        self.assertAlmostEqual(a, 296.5339, delta=0.01)
        self.assertAlmostEqual(a, 296.51, delta=0.05)

    def test_isa_speed_of_sound_isothermal_stratosphere(self):
        """Above 11000 m the stratosphere is isothermal at 216.65 K."""
        a_tropo = rta.isa_speed_of_sound(11000.0)
        a_strato = rta.isa_speed_of_sound(20000.0)
        self.assertAlmostEqual(a_tropo, 295.07, delta=0.01)
        self.assertEqual(a_tropo, a_strato)

    def test_isa_speed_of_sound_rejects_negative_altitude(self):
        """A negative altitude is non-physical and raises ValueError."""
        with self.assertRaises(ValueError):
            rta.isa_speed_of_sound(-100.0)


class EtaTests(unittest.TestCase):
    """Estimated time of arrival from distance and ground speed."""

    def test_eta_s_divides_distance_by_ground_speed(self):
        """450000 m at 250 m/s gives an ETA of exactly 1800 s."""
        self.assertEqual(rta.eta_s(DIST, GS), 1800.0)

    def test_eta_s_rejects_negative_distance(self):
        """A negative remaining distance raises ValueError."""
        with self.assertRaises(ValueError):
            rta.eta_s(-1.0, GS)

    def test_eta_s_rejects_nonpositive_speed(self):
        """A zero or negative ground speed raises ValueError."""
        with self.assertRaises(ValueError):
            rta.eta_s(DIST, 0.0)
        with self.assertRaises(ValueError):
            rta.eta_s(DIST, -10.0)


class TimeErrorTests(unittest.TestCase):
    """RTA time error sign convention: positive = late."""

    def test_time_error_s_early_is_negative(self):
        """Arriving before the RTA time gives a negative (early) error."""
        self.assertEqual(rta.time_error_s(1800.0, 1900.0, 0.0), -100.0)

    def test_time_error_s_late_is_positive(self):
        """Arriving after the RTA time gives a positive (late) error."""
        self.assertEqual(rta.time_error_s(1800.0, 1200.0, 0.0), 600.0)

    def test_time_error_s_on_time_is_zero(self):
        """Arriving exactly at the RTA time gives a zero error."""
        self.assertEqual(rta.time_error_s(1800.0, 1800.0, 0.0), 0.0)

    def test_time_error_s_counts_t_now(self):
        """The error uses the arrival clock: (t_now + eta) - rta."""
        self.assertEqual(rta.time_error_s(1800.0, 2200.0, 300.0), -100.0)


class RequiredGroundSpeedTests(unittest.TestCase):
    """Ground speed needed to hit the RTA time."""

    def test_required_ground_speed_anchor(self):
        """450000 m over 1900 s needs 236.84 m/s (spec anchor)."""
        self.assertAlmostEqual(
            rta.required_ground_speed_m_s(DIST, 1900.0, 0.0), 236.84,
            delta=0.01)

    def test_required_ground_speed_faster_for_earlier_rta(self):
        """450000 m over 1200 s needs 375 m/s."""
        self.assertAlmostEqual(
            rta.required_ground_speed_m_s(DIST, 1200.0, 0.0), 375.0,
            delta=1e-9)

    def test_required_ground_speed_rejects_rta_at_or_before_now(self):
        """An RTA time not after t_now raises ValueError."""
        with self.assertRaises(ValueError):
            rta.required_ground_speed_m_s(DIST, 0.0, 0.0)
        with self.assertRaises(ValueError):
            rta.required_ground_speed_m_s(DIST, 1900.0, 1900.0)


class TasWindTests(unittest.TestCase):
    """True airspeed from ground speed and along-track wind."""

    def test_tas_from_ground_speed_tailwind(self):
        """250 m/s ground speed with +15 m/s tailwind is 235 m/s TAS."""
        self.assertEqual(rta.tas_from_ground_speed(GS, WIND), 235.0)

    def test_tas_from_ground_speed_headwind_adds(self):
        """250 m/s ground speed against 15 m/s headwind is 265 m/s TAS."""
        self.assertEqual(rta.tas_from_ground_speed(250.0, -15.0), 265.0)

    def test_tas_from_ground_speed_rejects_wind_above_speed(self):
        """A tailwind at or above the ground speed is non-physical."""
        with self.assertRaises(ValueError):
            rta.tas_from_ground_speed(100.0, 100.0)
        with self.assertRaises(ValueError):
            rta.tas_from_ground_speed(100.0, 150.0)


class MachConversionTests(unittest.TestCase):
    """Mach from true airspeed at altitude."""

    def test_mach_from_tas_required_speed_anchor(self):
        """221.84 m/s TAS at 10668 m is Mach 0.74818 (spec anchor)."""
        self.assertAlmostEqual(
            rta.mach_from_tas(221.84, ALT), 0.74818, delta=1e-4)

    def test_mach_from_tas_hold_speed_anchor(self):
        """235 m/s TAS at 10668 m is Mach 0.79257 (spec anchor)."""
        self.assertAlmostEqual(
            rta.mach_from_tas(235.0, ALT), 0.79257, delta=1e-4)

    def test_mach_from_tas_round_trip(self):
        """tas = mach * a inverts mach_from_tas at the same altitude."""
        a_sound = rta.isa_speed_of_sound(ALT)
        self.assertAlmostEqual(rta.mach_from_tas(0.8 * a_sound, ALT), 0.8,
                               delta=1e-12)

    def test_mach_from_tas_rejects_nonphysical_inputs(self):
        """A non-positive TAS or negative altitude raises ValueError."""
        with self.assertRaises(ValueError):
            rta.mach_from_tas(0.0, ALT)
        with self.assertRaises(ValueError):
            rta.mach_from_tas(235.0, -1.0)


class AchievableWindowTests(unittest.TestCase):
    """Arrival window set by the minimum and maximum cruise Mach."""

    def test_achievable_window_anchors(self):
        """Window is 1704.1 s (fast) to 1969.4 s (slow) on the spec leg."""
        win = rta.achievable_window(DIST, ALT, WIND, MACH_MIN, MACH_MAX)
        self.assertAlmostEqual(win["eta_min_s"], 1704.1, delta=0.5)
        self.assertAlmostEqual(win["eta_max_s"], 1969.4, delta=0.5)
        self.assertAlmostEqual(win["gs_max"], 264.07, delta=0.05)
        self.assertAlmostEqual(win["gs_min"], 228.49, delta=0.05)

    def test_achievable_window_internal_consistency(self):
        """Ground speeds equal mach * a + wind and etas equal distance / gs."""
        a_sound = rta.isa_speed_of_sound(ALT)
        win = rta.achievable_window(DIST, ALT, WIND, MACH_MIN, MACH_MAX)
        self.assertAlmostEqual(win["gs_max"], MACH_MAX * a_sound + WIND,
                               delta=1e-9)
        self.assertAlmostEqual(win["gs_min"], MACH_MIN * a_sound + WIND,
                               delta=1e-9)
        self.assertAlmostEqual(win["eta_min_s"], DIST / win["gs_max"],
                               delta=1e-9)
        self.assertAlmostEqual(win["eta_max_s"], DIST / win["gs_min"],
                               delta=1e-9)

    def test_achievable_window_zero_distance(self):
        """At the waypoint already, the window collapses to zero."""
        win = rta.achievable_window(0.0, ALT, WIND, MACH_MIN, MACH_MAX)
        self.assertEqual(win["eta_min_s"], 0.0)
        self.assertEqual(win["eta_max_s"], 0.0)

    def test_achievable_window_rejects_bad_bounds(self):
        """Non-positive mach_min and mach_max < mach_min raise ValueError."""
        with self.assertRaises(ValueError):
            rta.achievable_window(DIST, ALT, WIND, 0.0, MACH_MAX)
        with self.assertRaises(ValueError):
            rta.achievable_window(DIST, ALT, WIND, 0.9, 0.84)

    def test_achievable_window_rejects_extreme_headwind(self):
        """A headwind above the minimum-cruise TAS is non-physical."""
        with self.assertRaises(ValueError):
            rta.achievable_window(DIST, ALT, -300.0, MACH_MIN, MACH_MAX)


class RtaSpeedCommandTests(unittest.TestCase):
    """The full RTA speed command decision law."""

    def test_command_feasible_slow_down(self):
        """RTA 1900 s: slow to Mach 0.748, feasible, zero remaining error."""
        res = rta.rta_speed_command(BASE)
        self.assertEqual(res["eta_rel_s"], 1800.0)
        self.assertEqual(res["time_error_s"], -100.0)
        self.assertAlmostEqual(res["required_gs_m_s"], 236.84, delta=0.01)
        self.assertAlmostEqual(res["required_mach"], 0.74818, delta=1e-4)
        self.assertEqual(res["command_mach"], res["required_mach"])
        self.assertTrue(res["feasible"])
        self.assertEqual(res["predicted_eta_s"], 1900.0)
        self.assertEqual(res["remaining_error_s"], 0.0)
        self.assertEqual(res["verdict"], "rta-feasible")

    def test_command_hold_on_time(self):
        """RTA 1800 s equals the ETA: hold the current speed command."""
        inputs = dict(BASE, rta_time_s=1800.0)
        res = rta.rta_speed_command(inputs)
        self.assertEqual(res["time_error_s"], 0.0)
        self.assertAlmostEqual(res["command_mach"], 0.79257, delta=1e-4)
        self.assertEqual(res["required_mach"], None)
        self.assertEqual(res["required_gs_m_s"], GS)
        self.assertTrue(res["feasible"])
        self.assertEqual(res["verdict"], "rta-feasible")

    def test_command_hold_within_tolerance(self):
        """RTA 1803 s is 3 s early: within tolerance, speed is held."""
        inputs = dict(BASE, rta_time_s=1803.0)
        res = rta.rta_speed_command(inputs)
        self.assertEqual(res["time_error_s"], -3.0)
        self.assertEqual(res["remaining_error_s"], -3.0)
        self.assertAlmostEqual(res["command_mach"], 0.79257, delta=1e-4)
        self.assertTrue(res["feasible"])

    def test_command_unfeasible_speed_up(self):
        """RTA 1200 s needs Mach 1.21, above mach_max: command 0.84."""
        inputs = dict(BASE, rta_time_s=1200.0)
        res = rta.rta_speed_command(inputs)
        self.assertEqual(res["time_error_s"], 600.0)
        self.assertAlmostEqual(res["required_gs_m_s"], 375.0, delta=1e-9)
        self.assertGreater(res["required_mach"], MACH_MAX)
        self.assertEqual(res["command_mach"], MACH_MAX)
        self.assertFalse(res["feasible"])
        self.assertAlmostEqual(res["predicted_eta_s"], 1704.1, delta=0.5)
        self.assertAlmostEqual(res["remaining_error_s"], 504.1, delta=0.5)
        self.assertEqual(res["verdict"], "rta-unfeasible")

    def test_command_unfeasible_too_slow(self):
        """RTA 2000 s is beyond eta_max: command mach_min, arrive early."""
        inputs = dict(BASE, rta_time_s=2000.0)
        res = rta.rta_speed_command(inputs)
        self.assertEqual(res["command_mach"], MACH_MIN)
        self.assertFalse(res["feasible"])
        self.assertAlmostEqual(res["predicted_eta_s"], 1969.4, delta=0.5)
        self.assertAlmostEqual(res["remaining_error_s"], -30.67, delta=0.5)
        self.assertEqual(res["verdict"], "rta-unfeasible")

    def test_command_feasible_mid_envelope(self):
        """RTA 1750 s needs Mach 0.817, inside the envelope: feasible."""
        inputs = dict(BASE, rta_time_s=1750.0)
        res = rta.rta_speed_command(inputs)
        self.assertTrue(res["feasible"])
        self.assertTrue(MACH_MIN <= res["command_mach"] <= MACH_MAX)
        self.assertEqual(res["remaining_error_s"], 0.0)
        self.assertEqual(res["verdict"], "rta-feasible")

    def test_command_near_window_fast_boundary(self):
        """Inside the fast boundary the RTA is feasible, outside it is not."""
        win = rta.achievable_window(DIST, ALT, WIND, MACH_MIN, MACH_MAX)
        inside = dict(BASE, rta_time_s=win["eta_min_s"] + 1.0)
        res_in = rta.rta_speed_command(inside)
        self.assertTrue(res_in["feasible"])
        self.assertLess(res_in["command_mach"], MACH_MAX)
        self.assertEqual(res_in["remaining_error_s"], 0.0)
        outside = dict(BASE, rta_time_s=win["eta_min_s"] - 1.0)
        res_out = rta.rta_speed_command(outside)
        self.assertFalse(res_out["feasible"])
        self.assertEqual(res_out["command_mach"], MACH_MAX)
        self.assertEqual(res_out["verdict"], "rta-unfeasible")

    def test_command_nonzero_t_now_absolute_clock(self):
        """t_now 300 s with RTA 2200 s matches the 1900 s-from-now case."""
        inputs = dict(BASE, t_now_s=300.0, rta_time_s=2200.0)
        res = rta.rta_speed_command(inputs)
        self.assertEqual(res["eta_rel_s"], 1800.0)
        self.assertEqual(res["time_error_s"], -100.0)
        self.assertAlmostEqual(res["required_gs_m_s"], 236.84, delta=0.01)
        self.assertTrue(res["feasible"])
        self.assertEqual(res["predicted_eta_s"], 2200.0)
        self.assertEqual(res["remaining_error_s"], 0.0)

    def test_command_accepts_cas_speed_mode(self):
        """speed_mode 'cas' is accepted and echoed in the output."""
        res = rta.rta_speed_command(dict(BASE, speed_mode="cas"))
        self.assertEqual(res["speed_mode"], "cas")
        self.assertAlmostEqual(res["command_mach"], 0.74818, delta=1e-4)

    def test_command_rejects_invalid_speed_mode(self):
        """An unknown speed_mode raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, speed_mode="ias"))

    def test_command_rejects_negative_distance(self):
        """A negative remaining distance raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, remaining_distance_m=-1.0))

    def test_command_rejects_nonpositive_ground_speed(self):
        """A zero ground speed raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, ground_speed_m_s=0.0))

    def test_command_rejects_rta_not_after_t_now(self):
        """An RTA time equal to t_now raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, rta_time_s=0.0))

    def test_command_rejects_inverted_envelope(self):
        """mach_max below mach_min raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, mach_max=0.7))

    def test_command_rejects_negative_altitude(self):
        """A negative altitude raises ValueError."""
        with self.assertRaises(ValueError):
            rta.rta_speed_command(dict(BASE, altitude_m=-1.0))

    def test_command_rejects_missing_required_key(self):
        """A missing required input key raises ValueError."""
        incomplete = {k: v for k, v in BASE.items() if k != "rta_time_s"}
        with self.assertRaises(ValueError):
            rta.rta_speed_command(incomplete)


if __name__ == "__main__":
    unittest.main()
