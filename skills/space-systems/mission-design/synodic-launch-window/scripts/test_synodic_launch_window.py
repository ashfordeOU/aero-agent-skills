"""Contract test for the synodic-launch-window leaf.

Exercises the SKILL.md workflow end to end: step 1 fixes the two planets
through the Earth and Mars module constants, step 2 the synodic
recurrence traverse computes the synodic period of the launch
opportunity recurrence, step 3 the departure phase traverse computes the
required heliocentric departure phase angle for the Hohmann window, step
4 the window epoch traverse lists the recurrence epochs, step 5 the
phase progression traverse checks the phase advance between windows, and
step 6 the report bookkeeping bundles the window geometry. Step 7 guard
traverses reject non-physical periods, semi-major axes and window
counts. Pure stdlib unittest, offline and deterministic.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import synodic_launch_window_logic as logic


class SynodicPeriodTest(unittest.TestCase):
    def test_module_constants_earth_mars(self):
        """Step 1 of the SKILL.md workflow fixes the two planets: the
        Earth to Mars defaults are 365.25 days, 686.98 days, 1.0 AU and
        1.523679 AU."""
        self.assertEqual(logic.EARTH_YEAR_DAYS, 365.25)
        self.assertEqual(logic.MARS_YEAR_DAYS, 686.98)
        self.assertEqual(logic.EARTH_SMA_AU, 1.0)
        self.assertEqual(logic.MARS_SMA_AU, 1.523679)

    def test_synodic_period_earth_mars_anchor(self):
        """Step 2 of the SKILL.md workflow, the synodic recurrence
        traverse: the Earth to Mars synodic period of the launch
        opportunity recurrence anchors at 779.9 days within 0.5."""
        t_syn = logic.synodic_period(logic.EARTH_YEAR_DAYS, logic.MARS_YEAR_DAYS)
        self.assertAlmostEqual(t_syn, 779.9, delta=0.5)
        self.assertAlmostEqual(t_syn, 779.9068939794237, places=6)

    def test_synodic_period_exceeds_both_orbital_periods(self):
        """Step 2 of the SKILL.md workflow: the synodic recurrence is
        slower than either planet, so the synodic period exceeds both
        orbital periods."""
        t_syn = logic.synodic_period(365.25, 686.98)
        self.assertGreater(t_syn, 686.98)
        self.assertGreater(686.98, 365.25)

    def test_synodic_period_beat_identity(self):
        """Step 2 of the SKILL.md workflow: the synodic period equals
        the beat period of the two orbital frequencies, 1/(1/T_in -
        1/T_out)."""
        t_syn = logic.synodic_period(365.25, 686.98)
        beat = 1.0 / (1.0 / 365.25 - 1.0 / 686.98)
        self.assertAlmostEqual(t_syn, beat, delta=1e-9)

    def test_synodic_period_outer_equal_inner_raises(self):
        """Step 7 guard traverse: equal orbital periods leave no
        recurrence, so the synodic period function raises ValueError."""
        with self.assertRaises(ValueError):
            logic.synodic_period(365.25, 365.25)

    def test_synodic_period_reversed_order_raises(self):
        """Step 7 guard traverse: the synodic period needs the outer
        orbital period to exceed the inner one, and reversed periods
        raise ValueError."""
        with self.assertRaises(ValueError):
            logic.synodic_period(686.98, 365.25)

    def test_synodic_period_nonpositive_period_raises(self):
        """Step 7 guard traverse: non-positive orbital periods are
        non-physical and raise ValueError in the synodic recurrence
        traverse."""
        with self.assertRaises(ValueError):
            logic.synodic_period(0.0, 686.98)
        with self.assertRaises(ValueError):
            logic.synodic_period(365.25, -10.0)


class DeparturePhaseTest(unittest.TestCase):
    def test_departure_phase_angle_earth_mars_radians_anchor(self):
        """Step 3 of the SKILL.md workflow, the departure phase
        traverse: the Hohmann window departure phase angle for the
        Earth to Mars transfer anchors at 0.7739 rad within 0.002."""
        alpha = logic.hohmann_departure_phase_angle(1.0, 1.523679)
        self.assertAlmostEqual(alpha, 0.7739, delta=0.002)
        self.assertAlmostEqual(alpha, 0.7739517891620696, places=6)

    def test_departure_phase_angle_earth_mars_degrees_anchor(self):
        """Step 3 of the SKILL.md workflow: the departure phase angle
        in degrees is about 44 degrees, anchoring at 44.34 degrees
        within 0.1 for the Earth to Mars window."""
        alpha_deg = math.degrees(
            logic.hohmann_departure_phase_angle(1.0, 1.523679)
        )
        self.assertAlmostEqual(alpha_deg, 44.34, delta=0.1)
        self.assertAlmostEqual(alpha_deg, 44.34417106558552, places=6)

    def test_departure_phase_angle_between_zero_and_pi(self):
        """Step 3 of the SKILL.md workflow: the Hohmann window phase
        angle lies strictly between zero and pi for an outward
        heliocentric transfer."""
        alpha = logic.hohmann_departure_phase_angle(1.0, 1.523679)
        self.assertGreater(alpha, 0.0)
        self.assertLess(alpha, math.pi)

    def test_departure_phase_angle_reversed_order_raises(self):
        """Step 7 guard traverse: an inward heliocentric transfer is
        out of scope for the departure phase traverse, so an outer
        semi-major axis below the inner one raises ValueError."""
        with self.assertRaises(ValueError):
            logic.hohmann_departure_phase_angle(1.523679, 1.0)

    def test_departure_phase_angle_nonpositive_sma_raises(self):
        """Step 7 guard traverse: non-positive semi-major axes are
        non-physical and raise ValueError in the departure phase
        traverse."""
        with self.assertRaises(ValueError):
            logic.hohmann_departure_phase_angle(0.0, 1.523679)
        with self.assertRaises(ValueError):
            logic.hohmann_departure_phase_angle(1.0, -1.0)


class WindowEpochsTest(unittest.TestCase):
    def test_window_epochs_earth_mars_anchor(self):
        """Step 4 of the SKILL.md workflow, the window epoch traverse:
        recurrence epochs from t0 = 0 days anchor at 0, 779.9 and
        1559.8 days within 0.1."""
        epochs = logic.window_epochs(0.0, 779.9, 3)
        self.assertEqual(len(epochs), 3)
        for got, want in zip(epochs, [0.0, 779.9, 1559.8]):
            self.assertAlmostEqual(got, want, delta=0.1)

    def test_window_epochs_real_synodic_recurrence(self):
        """Step 4 of the SKILL.md workflow: window epochs built on the
        real Earth to Mars synodic period are evenly spaced by that
        synodic period, 779.9068939794237 days."""
        t_syn = logic.synodic_period(365.25, 686.98)
        epochs = logic.window_epochs(0.0, t_syn, 3)
        self.assertEqual(epochs[0], 0.0)
        self.assertAlmostEqual(epochs[1], t_syn, places=9)
        self.assertAlmostEqual(epochs[2], 2.0 * t_syn, places=9)

    def test_window_epochs_offset_t0(self):
        """Step 4 of the SKILL.md workflow: an offset launch epoch t0
        shifts every recurrence epoch by the same offset."""
        epochs = logic.window_epochs(100.0, 779.9, 3)
        self.assertAlmostEqual(epochs[0], 100.0, places=9)
        self.assertAlmostEqual(epochs[1], 879.9, delta=1e-9)
        self.assertAlmostEqual(epochs[2], 1659.8, delta=1e-9)

    def test_window_epochs_single_window(self):
        """Step 4 of the SKILL.md workflow: a single-window request
        returns only the launch epoch t0."""
        self.assertEqual(logic.window_epochs(5.0, 779.9, 1), [5.0])

    def test_window_epochs_zero_count_raises(self):
        """Step 7 guard traverse: a window count of zero requests no
        recurrence epochs and raises ValueError."""
        with self.assertRaises(ValueError):
            logic.window_epochs(0.0, 779.9, 0)

    def test_window_epochs_negative_count_raises(self):
        """Step 7 guard traverse: a negative window count is
        non-physical and raises ValueError in the window epoch
        traverse."""
        with self.assertRaises(ValueError):
            logic.window_epochs(0.0, 779.9, -3)

    def test_window_epochs_nonpositive_synodic_raises(self):
        """Step 7 guard traverse: a non-positive synodic period cannot
        space any recurrence epochs and raises ValueError."""
        with self.assertRaises(ValueError):
            logic.window_epochs(0.0, 0.0, 3)
        with self.assertRaises(ValueError):
            logic.window_epochs(0.0, -779.9, 3)


class PhaseProgressionTest(unittest.TestCase):
    def test_phase_progression_at_recurrence_epoch_zero(self):
        """Step 5 of the SKILL.md workflow, the phase progression
        traverse: after one synodic period the phase returns to its
        start, zero modulo 2*pi at t0 + T_syn."""
        t_syn = logic.synodic_period(365.25, 686.98)
        phase = logic.phase_progression(t_syn, 0.0, t_syn)
        self.assertAlmostEqual(phase % logic.TWO_PI, 0.0, places=9)

    def test_phase_progression_all_epochs_zero_mod_2pi(self):
        """Step 5 of the SKILL.md workflow: every recurrence epoch
        sits on a zero phase crossing, so the phase progression is
        zero modulo 2*pi at each window."""
        t_syn = logic.synodic_period(365.25, 686.98)
        for k in range(5):
            phase = logic.phase_progression(k * t_syn, 0.0, t_syn)
            self.assertAlmostEqual(phase % logic.TWO_PI, 0.0, places=8)

    def test_phase_progression_half_synodic_is_pi(self):
        """Step 5 of the SKILL.md workflow: halfway between windows
        the phase progression reaches pi, the anti-phase point."""
        t_syn = logic.synodic_period(365.25, 686.98)
        phase = logic.phase_progression(0.5 * t_syn, 0.0, t_syn)
        self.assertAlmostEqual(phase, math.pi, places=9)

    def test_phase_progression_range_and_monotone(self):
        """Step 5 of the SKILL.md workflow: the phase progression
        stays in [0, 2*pi) and rises monotonically between one
        recurrence epoch and the next."""
        t_syn = logic.synodic_period(365.25, 686.98)
        samples = [0.1, 0.3, 0.5, 0.7, 0.9]
        values = [logic.phase_progression(f * t_syn, 0.0, t_syn) for f in samples]
        for value in values:
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, logic.TWO_PI)
        for lower, upper in zip(values, values[1:]):
            self.assertGreater(upper, lower)

    def test_phase_progression_nonpositive_synodic_raises(self):
        """Step 7 guard traverse: the phase progression traverse
        rejects a non-positive synodic period with ValueError."""
        with self.assertRaises(ValueError):
            logic.phase_progression(100.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            logic.phase_progression(100.0, 0.0, -779.9)


class SynodicReportTest(unittest.TestCase):
    def test_synodic_report_keys_exact(self):
        """Step 6 of the SKILL.md workflow, the report bookkeeping:
        the window summary dict exposes exactly the four documented
        keys."""
        report = logic.synodic_report(365.25, 686.98, 1.0, 1.523679)
        self.assertEqual(
            list(report.keys()),
            [
                "synodic_period_days",
                "departure_phase_angle_deg",
                "window_epochs",
                "phase_at_first_window",
            ],
        )

    def test_synodic_report_matches_individual_calls(self):
        """Step 6 of the SKILL.md workflow: the report bookkeeping
        reproduces the synodic period, departure phase angle and
        window epochs of the separate traverses."""
        report = logic.synodic_report(365.25, 686.98, 1.0, 1.523679)
        t_syn = logic.synodic_period(365.25, 686.98)
        alpha_deg = math.degrees(logic.hohmann_departure_phase_angle(1.0, 1.523679))
        self.assertAlmostEqual(report["synodic_period_days"], t_syn, places=9)
        self.assertAlmostEqual(report["departure_phase_angle_deg"], alpha_deg, places=9)
        self.assertEqual(report["window_epochs"], logic.window_epochs(0.0, t_syn, 3))

    def test_synodic_report_phase_first_window_near_zero(self):
        """Step 6 of the SKILL.md workflow: the phase at the first
        recurrence epoch is checked near zero modulo 2*pi, confirming
        the window sits on a zero phase crossing."""
        report = logic.synodic_report(365.25, 686.98, 1.0, 1.523679)
        self.assertAlmostEqual(report["phase_at_first_window"] % logic.TWO_PI, 0.0, places=9)

    def test_synodic_report_nonphysical_inputs_raise(self):
        """Step 7 guard traverse: the report bookkeeping forwards the
        non-physical input checks of the underlying traverses."""
        with self.assertRaises(ValueError):
            logic.synodic_report(686.98, 365.25, 1.0, 1.523679)
        with self.assertRaises(ValueError):
            logic.synodic_report(365.25, 686.98, 1.523679, 1.0)
        with self.assertRaises(ValueError):
            logic.synodic_report(365.25, 686.98, 1.0, 1.523679, count=0)


class DeterminismTest(unittest.TestCase):
    def test_determinism_repeatable(self):
        """Step 7 of the SKILL.md workflow, the determinism traverse:
        repeated runs of the report bookkeeping return identical
        synodic period and phase values."""
        first = logic.synodic_report(365.25, 686.98, 1.0, 1.523679)
        second = logic.synodic_report(365.25, 686.98, 1.0, 1.523679)
        self.assertEqual(first["synodic_period_days"], second["synodic_period_days"])
        self.assertEqual(first["departure_phase_angle_deg"], second["departure_phase_angle_deg"])
        self.assertEqual(first["window_epochs"], second["window_epochs"])
        self.assertEqual(first["phase_at_first_window"], second["phase_at_first_window"])


if __name__ == "__main__":
    unittest.main()
