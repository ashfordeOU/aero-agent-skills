#!/usr/bin/env python3
"""Contract test for the rotorcraft-autorotation-flight-test leaf
(flight-test-operations/performance). Exercises the SKILL.md workflow end
to end: step 2 fits the steady autorotative descent with lsq_fit, step 3
reads the measured sink rate from the fitted slope, step 4 runs the entry
rotor-RPM floor check against the declared floor, step 5 runs the steady
rotor-RPM band check, step 6 runs the flare rotor-RPM recovery check
against the recovery target, step 7 computes the altitude lost to the
recovery and judges it against the declared limit, and step 8 chains the
checks into the demonstration summary with the overall verdict. The
telemetered worked-example record is fixed (no RNG, offline,
deterministic); every verdict boundary is inclusive and every numeric
assert is order-safe (assertAlmostEqual / math.isclose, never exact
float equality on computed sums)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rotorcraft_autorotation_flight_test_logic import (
    ALTITUDE_LOSS_LIMIT_M,
    ENTRY_RPM_FLOOR_PCT,
    FLARE_RPM_RECOVERY_TARGET_PCT,
    MIN_SAMPLES,
    STEADY_RPM_BAND_HIGH_PCT,
    STEADY_RPM_BAND_LOW_PCT,
    altitude_loss_verdict,
    altitude_lost_to_recovery,
    entry_rpm_decay_check,
    flare_rpm_recovery_check,
    lsq_fit,
    reduce_autorotation_demonstration,
    sink_rate,
    steady_rpm_band_check,
)

# Fixed telemetered demonstration record from the spec worked example.
ENTRY_RPM = [100.0, 94.6, 91.2, 91.6, 95.4, 96.7]
STEADY_TIME_S = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0,
                 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
STEADY_ALT_M = [620.4, 599.7, 578.6, 557.2, 535.9, 514.8, 493.6,
                472.3, 451.0, 429.8, 408.5, 387.1, 366.0, 344.7, 323.2]
STEADY_RPM = [96.8, 97.4, 97.1, 97.6, 96.9, 97.5, 97.2, 97.7,
              96.7, 97.5, 97.3, 97.0, 97.6, 96.9, 97.4]
FLARE_RPM = [96.5, 99.4, 102.1, 103.6, 103.9, 103.1]
H_FLARE_START_M = 458.0
H_RECOVERY_M = 412.6


class LsqFitTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the least-squares fit of the
    steady autorotative descent, is exercised by these tests."""

    def test_worked_window_slope_and_keys(self):
        fit = lsq_fit(STEADY_ALT_M, STEADY_TIME_S)
        self.assertEqual(list(fit.keys()), ["slope", "intercept",
                                            "r_squared"])
        self.assertAlmostEqual(fit["slope"], -10.6225, delta=1e-4)

    def test_worked_window_intercept(self):
        fit = lsq_fit(STEADY_ALT_M, STEADY_TIME_S)
        self.assertAlmostEqual(fit["intercept"], 620.9016666667, delta=1e-6)

    def test_worked_window_r_squared(self):
        fit = lsq_fit(STEADY_ALT_M, STEADY_TIME_S)
        self.assertAlmostEqual(fit["r_squared"], 0.9999964366, delta=1e-9)

    def test_regression_identity_recovers_generating_line(self):
        # Perfectly linear data: the step 2 fit recovers the generating
        # slope and intercept at any point count of MIN_SAMPLES or more.
        for n in (MIN_SAMPLES, 7):
            times = [float(2 * i) for i in range(n)]
            alts = [620.0 - 10.5 * t for t in times]
            fit = lsq_fit(alts, times)
            self.assertAlmostEqual(fit["slope"], -10.5, delta=1e-12)
            self.assertAlmostEqual(fit["intercept"], 620.0, delta=1e-12)
            self.assertAlmostEqual(fit["r_squared"], 1.0, delta=1e-12)

    def test_constant_altitude_samples_report_r_squared_one(self):
        # A flat pressure-altitude record has no variation to explain, so
        # r_squared is defined as 1.0 and the fitted slope is zero.
        fit = lsq_fit([600.0, 600.0, 600.0], [0.0, 2.0, 4.0])
        self.assertAlmostEqual(fit["slope"], 0.0, delta=1e-12)
        self.assertAlmostEqual(fit["r_squared"], 1.0, delta=1e-12)

    def test_lsq_fit_rejects_bad_inputs(self):
        # Unequal lengths, fewer than MIN_SAMPLES points, and a zero fit
        # denominator (all x equal) all raise ValueError.
        with self.assertRaises(ValueError):
            lsq_fit([600.0, 590.0], [0.0])
        with self.assertRaises(ValueError):
            lsq_fit([600.0], [0.0])
        with self.assertRaises(ValueError):
            lsq_fit([600.0, 590.0, 580.0], [10.0, 10.0, 10.0])


class SinkRateTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow, reading the measured sink rate
    from the fitted slope of the steady autorotative descent, is
    exercised by these tests."""

    def test_worked_window_sink_rate_in_realistic_band(self):
        rate = sink_rate(STEADY_ALT_M, STEADY_TIME_S)
        self.assertAlmostEqual(rate, 10.6225, delta=1e-4)
        # The measured rate sits inside the realistic 8 to 15 m/s
        # steady autorotative sink band.
        self.assertGreaterEqual(rate, 8.0)
        self.assertLessEqual(rate, 15.0)

    def test_sink_rate_equals_negated_fit_slope_identity(self):
        # By construction the measured sink rate is -lsq_fit slope.
        rate = sink_rate(STEADY_ALT_M, STEADY_TIME_S)
        slope = lsq_fit(STEADY_ALT_M, STEADY_TIME_S)["slope"]
        self.assertTrue(math.isclose(rate, -slope, rel_tol=1e-12,
                                     abs_tol=1e-12))

    def test_sink_rate_rejects_windows_without_descent(self):
        # Step 3 rejects records where the fitted slope is not negative:
        # a flat record and a rising record both show no autorotative
        # descent in the window.
        with self.assertRaises(ValueError):
            sink_rate([600.0, 600.0, 600.0], [0.0, 2.0, 4.0])
        with self.assertRaises(ValueError):
            sink_rate([600.0, 610.0, 620.0], [0.0, 2.0, 4.0])


class EntryRpmFloorCheckTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the entry rotor-RPM floor check
    of the power-off decay against the declared floor, is exercised by
    these tests."""

    def test_worked_entry_history_passes(self):
        check = entry_rpm_decay_check(ENTRY_RPM)
        self.assertAlmostEqual(check["min_rpm_pct"], 91.2, delta=1e-12)
        self.assertAlmostEqual(check["floor_pct"], ENTRY_RPM_FLOOR_PCT,
                               delta=1e-12)
        self.assertEqual(check["verdict"], "PASS")

    def test_floor_boundary_is_inclusive(self):
        # Minimum exactly at the declared floor PASSes, just below FAILs.
        self.assertEqual(
            entry_rpm_decay_check([91.0, 90.0, 92.0])["verdict"], "PASS")
        self.assertAlmostEqual(
            entry_rpm_decay_check([91.0, 90.0, 92.0])["min_rpm_pct"], 90.0,
            delta=1e-12)
        self.assertEqual(
            entry_rpm_decay_check([91.0, 89.9, 92.0])["verdict"], "FAIL")

    def test_verdict_tracks_minimum_sample_not_mean(self):
        # Mean 92.95 sits above the floor but the minimum 89.9 does not.
        self.assertEqual(
            entry_rpm_decay_check([96.0, 89.9])["verdict"], "FAIL")
        self.assertEqual(
            entry_rpm_decay_check([90.0, 96.0])["verdict"], "PASS")

    def test_entry_check_rejects_empty_and_negative_samples(self):
        with self.assertRaises(ValueError):
            entry_rpm_decay_check([])
        with self.assertRaises(ValueError):
            entry_rpm_decay_check([95.0, -1.0])

    def test_entry_check_rejects_non_positive_floor(self):
        with self.assertRaises(ValueError):
            entry_rpm_decay_check([95.0], floor_pct=0.0)
        with self.assertRaises(ValueError):
            entry_rpm_decay_check([95.0], floor_pct=-5.0)


class SteadyRpmBandCheckTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the steady rotor-RPM band check
    of the steady-descent samples against the declared band, is exercised
    by these tests."""

    def test_worked_steady_samples_pass(self):
        check = steady_rpm_band_check(STEADY_RPM)
        self.assertAlmostEqual(check["mean_rpm_pct"], 97.24, delta=1e-6)
        self.assertAlmostEqual(check["min_rpm_pct"], 96.7, delta=1e-12)
        self.assertAlmostEqual(check["max_rpm_pct"], 97.7, delta=1e-12)
        self.assertAlmostEqual(check["band_low_pct"], STEADY_RPM_BAND_LOW_PCT,
                               delta=1e-12)
        self.assertAlmostEqual(check["band_high_pct"],
                               STEADY_RPM_BAND_HIGH_PCT, delta=1e-12)
        self.assertEqual(check["verdict"], "PASS")

    def test_band_edges_are_inclusive(self):
        # Samples exactly at both declared band edges PASS (inclusive).
        self.assertEqual(
            steady_rpm_band_check([95.0, 100.0, 105.0])["verdict"], "PASS")

    def test_samples_outside_band_fail(self):
        # A sample above the high edge and one below the low edge FAIL.
        self.assertEqual(
            steady_rpm_band_check([95.0, 100.0, 105.1])["verdict"], "FAIL")
        self.assertEqual(
            steady_rpm_band_check([94.9, 100.0, 105.0])["verdict"], "FAIL")

    def test_verdict_tracks_extreme_samples_not_mean(self):
        # Mean 101.5 lies inside the band but the 106.0 sample does not.
        self.assertEqual(
            steady_rpm_band_check([97.0, 106.0])["verdict"], "FAIL")
        self.assertEqual(
            steady_rpm_band_check([95.0, 105.0])["verdict"], "PASS")

    def test_steady_check_rejects_empty_and_negative_samples(self):
        with self.assertRaises(ValueError):
            steady_rpm_band_check([])
        with self.assertRaises(ValueError):
            steady_rpm_band_check([97.0, -2.0])

    def test_steady_check_rejects_invalid_declared_band(self):
        with self.assertRaises(ValueError):
            steady_rpm_band_check([97.0], low_pct=0.0)
        with self.assertRaises(ValueError):
            steady_rpm_band_check([97.0], low_pct=105.0, high_pct=95.0)


class FlareRpmRecoveryCheckTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the flare rotor-RPM recovery
    check of the flare peak against the declared recovery target, is
    exercised by these tests."""

    def test_worked_flare_history_passes(self):
        check = flare_rpm_recovery_check(FLARE_RPM)
        self.assertAlmostEqual(check["peak_rpm_pct"], 103.9, delta=1e-12)
        self.assertAlmostEqual(check["recovery_target_pct"],
                               FLARE_RPM_RECOVERY_TARGET_PCT, delta=1e-12)
        self.assertEqual(check["verdict"], "PASS")

    def test_recovery_target_boundary_is_inclusive(self):
        # Peak exactly at the recovery target PASSes, just below FAILs.
        self.assertEqual(
            flare_rpm_recovery_check([99.0, 100.0])["verdict"], "PASS")
        self.assertEqual(
            flare_rpm_recovery_check([99.0, 99.9])["verdict"], "FAIL")

    def test_flare_check_rejects_empty_negative_and_bad_target(self):
        with self.assertRaises(ValueError):
            flare_rpm_recovery_check([])
        with self.assertRaises(ValueError):
            flare_rpm_recovery_check([100.0, -1.0])
        with self.assertRaises(ValueError):
            flare_rpm_recovery_check([100.0], target_pct=0.0)


class AltitudeLossTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the altitude lost to the recovery
    and its verdict and margin against the declared limit, is exercised
    by these tests."""

    def test_worked_altitude_loss_and_verdict_margin(self):
        loss = altitude_lost_to_recovery(H_FLARE_START_M, H_RECOVERY_M)
        self.assertAlmostEqual(loss, 45.4, delta=1e-9)
        verdict = altitude_loss_verdict(loss)
        self.assertAlmostEqual(verdict["loss_m"], 45.4, delta=1e-9)
        self.assertAlmostEqual(verdict["limit_m"], ALTITUDE_LOSS_LIMIT_M,
                               delta=1e-12)
        self.assertEqual(verdict["verdict"], "PASS")
        self.assertAlmostEqual(verdict["margin_m"], 14.6, delta=1e-9)

    def test_altitude_loss_identity(self):
        # The loss is flare-initiation minus recovery altitude by
        # construction at any valid input pair.
        self.assertAlmostEqual(
            altitude_lost_to_recovery(500.0, 430.0), 70.0, delta=1e-12)

    def test_loss_limit_boundary_is_inclusive(self):
        # Loss exactly at the declared limit PASSes with zero margin,
        # just over FAILs with a negative margin.
        at_limit = altitude_loss_verdict(60.0)
        self.assertEqual(at_limit["verdict"], "PASS")
        self.assertAlmostEqual(at_limit["margin_m"], 0.0, delta=1e-12)
        over_limit = altitude_loss_verdict(60.1)
        self.assertEqual(over_limit["verdict"], "FAIL")
        self.assertAlmostEqual(over_limit["margin_m"], -0.1, delta=1e-9)

    def test_altitude_loss_rejects_bad_altitudes(self):
        # Non-positive altitudes and a recovery that gained altitude
        # (recovery above flare initiation) raise ValueError.
        with self.assertRaises(ValueError):
            altitude_lost_to_recovery(0.0, 400.0)
        with self.assertRaises(ValueError):
            altitude_lost_to_recovery(458.0, -1.0)
        with self.assertRaises(ValueError):
            altitude_lost_to_recovery(400.0, 430.0)

    def test_loss_verdict_rejects_negative_loss_and_bad_limit(self):
        with self.assertRaises(ValueError):
            altitude_loss_verdict(-1.0)
        with self.assertRaises(ValueError):
            altitude_loss_verdict(45.4, limit_m=0.0)


class DemonstrationSummaryTests(unittest.TestCase):
    """Step 8 of the SKILL.md workflow, chaining the four checks into the
    demonstration summary with the overall verdict, is exercised by these
    tests."""

    def test_worked_demonstration_summary_passes(self):
        summary = reduce_autorotation_demonstration(
            ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, H_RECOVERY_M)
        self.assertEqual(
            list(summary.keys()),
            ["sink_rate_mps", "r_squared", "entry_verdict", "steady_verdict",
             "flare_verdict", "altitude_verdict", "altitude_loss_m",
             "overall_verdict"])
        self.assertAlmostEqual(summary["sink_rate_mps"], 10.6225, delta=1e-4)
        self.assertAlmostEqual(summary["r_squared"], 0.9999964366,
                               delta=1e-9)
        self.assertEqual(summary["entry_verdict"], "PASS")
        self.assertEqual(summary["steady_verdict"], "PASS")
        self.assertEqual(summary["flare_verdict"], "PASS")
        self.assertEqual(summary["altitude_verdict"], "PASS")
        self.assertAlmostEqual(summary["altitude_loss_m"], 45.4, delta=1e-6)
        self.assertEqual(summary["overall_verdict"], "PASS")

    def test_overall_fails_when_only_entry_check_fails(self):
        bad_entry = [100.0, 94.6, 89.9, 91.6, 95.4, 96.7]
        summary = reduce_autorotation_demonstration(
            bad_entry, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, H_RECOVERY_M)
        self.assertEqual(summary["entry_verdict"], "FAIL")
        self.assertEqual(summary["steady_verdict"], "PASS")
        self.assertEqual(summary["flare_verdict"], "PASS")
        self.assertEqual(summary["altitude_verdict"], "PASS")
        self.assertEqual(summary["overall_verdict"], "FAIL")

    def test_overall_fails_when_only_steady_check_fails(self):
        bad_steady = STEADY_RPM[:-1] + [105.1]
        summary = reduce_autorotation_demonstration(
            ENTRY_RPM, bad_steady, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, H_RECOVERY_M)
        self.assertEqual(summary["steady_verdict"], "FAIL")
        self.assertEqual(summary["overall_verdict"], "FAIL")

    def test_overall_fails_when_only_flare_check_fails(self):
        # Peak 99.9 stays below the 100.0 recovery target.
        bad_flare = [96.5, 99.4, 98.5, 99.9, 98.8, 96.0]
        summary = reduce_autorotation_demonstration(
            ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, bad_flare,
            H_FLARE_START_M, H_RECOVERY_M)
        self.assertEqual(summary["flare_verdict"], "FAIL")
        self.assertEqual(summary["overall_verdict"], "FAIL")

    def test_overall_fails_when_only_altitude_check_fails(self):
        # Recovery at 397.9 m leaves 60.1 m lost, over the 60 m limit.
        summary = reduce_autorotation_demonstration(
            ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, 397.9)
        self.assertEqual(summary["altitude_verdict"], "FAIL")
        self.assertAlmostEqual(summary["altitude_loss_m"], 60.1, delta=1e-9)
        self.assertEqual(summary["overall_verdict"], "FAIL")

    def test_summary_agrees_with_chained_calls(self):
        summary = reduce_autorotation_demonstration(
            ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, H_RECOVERY_M)
        fit = lsq_fit(STEADY_ALT_M, STEADY_TIME_S)
        self.assertTrue(math.isclose(summary["sink_rate_mps"],
                                     sink_rate(STEADY_ALT_M, STEADY_TIME_S),
                                     rel_tol=1e-12, abs_tol=1e-12))
        self.assertTrue(math.isclose(summary["r_squared"], fit["r_squared"],
                                     rel_tol=1e-12, abs_tol=1e-12))
        self.assertEqual(
            summary["entry_verdict"],
            entry_rpm_decay_check(ENTRY_RPM)["verdict"])
        self.assertEqual(
            summary["steady_verdict"],
            steady_rpm_band_check(STEADY_RPM)["verdict"])
        self.assertEqual(
            summary["flare_verdict"],
            flare_rpm_recovery_check(FLARE_RPM)["verdict"])
        self.assertEqual(
            summary["altitude_verdict"],
            altitude_loss_verdict(
                altitude_lost_to_recovery(H_FLARE_START_M, H_RECOVERY_M))
            ["verdict"])

    def test_determinism_across_repeated_calls(self):
        first = reduce_autorotation_demonstration(
            ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S, FLARE_RPM,
            H_FLARE_START_M, H_RECOVERY_M)
        for _ in range(3):
            again = reduce_autorotation_demonstration(
                ENTRY_RPM, STEADY_RPM, STEADY_ALT_M, STEADY_TIME_S,
                FLARE_RPM, H_FLARE_START_M, H_RECOVERY_M)
            self.assertTrue(math.isclose(
                first["sink_rate_mps"], again["sink_rate_mps"],
                rel_tol=1e-15, abs_tol=1e-15))
            self.assertEqual(first["overall_verdict"],
                             again["overall_verdict"])


if __name__ == "__main__":
    unittest.main()
