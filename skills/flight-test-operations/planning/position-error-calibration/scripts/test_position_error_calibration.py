#!/usr/bin/env python3
"""Deterministic contract test for the airspeed PEC flight test logic.

Runs offline with stdlib unittest only:

    python3 scripts/test_position_error_calibration.py

Covers the worked example contract (compressible airspeed identities,
the GPS ground speed doublet reduction, the tower fly-by height error
reduction, the piecewise linear PEC fit), boundary cases, round trips,
and ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import position_error_calibration_logic as pec


class PecContractTest(unittest.TestCase):
    """Contract tests for the position error calibration module."""

    # --- calibrated airspeed and impact pressure ---------------------------

    def test_calibrated_airspeed_identity_at_100(self):
        # The compressible pair is inverse: V(qc(V)) == V at 100 m/s.
        v = pec.calibrated_airspeed(pec.impact_pressure_from_cas(100.0))
        self.assertAlmostEqual(v, 100.0, delta=1e-6)
        # Zero speed boundary: no impact pressure, no airspeed.
        self.assertEqual(pec.calibrated_airspeed(0.0), 0.0)
        self.assertEqual(pec.impact_pressure_from_cas(0.0), 0.0)

    def test_impact_pressure_known_value(self):
        # Worked example: qc at 100 m/s CAS is about 6258 Pa.
        qc = pec.impact_pressure_from_cas(100.0)
        self.assertAlmostEqual(qc, 6258.376, delta=0.5)

    def test_impact_pressure_round_trip(self):
        for v in (30.0, 60.0, 90.0, 100.0, 140.0, 180.0):
            back = pec.calibrated_airspeed(pec.impact_pressure_from_cas(v))
            self.assertAlmostEqual(back, v, delta=1e-6)

    def test_zero_speed_zero_pressure(self):
        self.assertEqual(pec.calibrated_airspeed(0.0), 0.0)
        self.assertEqual(pec.impact_pressure_from_cas(0.0), 0.0)

    def test_calibrated_airspeed_monotonic(self):
        q1 = pec.impact_pressure_from_cas(90.0)
        q2 = pec.impact_pressure_from_cas(100.0)
        self.assertLess(
            pec.calibrated_airspeed(q1), pec.calibrated_airspeed(q2)
        )

    def test_calibrated_airspeed_rejects_negative_qc(self):
        with self.assertRaises(ValueError):
            pec.calibrated_airspeed(-5.0)

    def test_impact_pressure_rejects_negative_speed(self):
        with self.assertRaises(ValueError):
            pec.impact_pressure_from_cas(-1.0)
        with self.assertRaises(ValueError):
            pec.impact_pressure_from_cas(float("nan"))

    # --- position error -----------------------------------------------------

    def test_position_error_identity_zero_dvp(self):
        # V_cas == V_ias when the position error is zero by construction.
        v_cas = pec.calibrated_airspeed(pec.impact_pressure_from_cas(100.0))
        self.assertAlmostEqual(pec.position_error(100.0, v_cas), 0.0, delta=1e-6)
        self.assertAlmostEqual(pec.position_error(100.0, 100.0), 0.0, delta=1e-12)

    def test_position_error_sign(self):
        self.assertGreater(pec.position_error(100.0, 102.0), 0.0)
        self.assertLess(pec.position_error(100.0, 98.0), 0.0)

    def test_position_error_rejects_negative(self):
        with self.assertRaises(ValueError):
            pec.position_error(-1.0, 100.0)
        with self.assertRaises(ValueError):
            pec.position_error(100.0, -1.0)

    # --- GPS ground speed doublet -------------------------------------------

    def test_gps_doublet_worked_example(self):
        # Worked example: V1g = 98 m/s, V2g = 102 m/s gives V_tas = 100 m/s.
        self.assertEqual(pec.gps_doublet_tas(98.0, 102.0), 100.0)
        # A steady along-track wind cancels on reciprocal headings.
        self.assertEqual(pec.gps_doublet_tas(95.0, 105.0), 100.0)
        self.assertEqual(pec.gps_doublet_tas(100.0, 100.0), 100.0)

    def test_gps_doublet_rejects_negative(self):
        with self.assertRaises(ValueError):
            pec.gps_doublet_tas(-1.0, 100.0)
        with self.assertRaises(ValueError):
            pec.gps_doublet_tas(100.0, -2.0)
        with self.assertRaises(ValueError):
            pec.gps_doublet_tas(100.0, float("inf"))

    def test_tas_to_cas_worked_example(self):
        # Worked example: V_tas = 100 m/s at rho/rho0 = 0.9 gives about 94.87.
        self.assertAlmostEqual(pec.tas_to_cas(100.0, 0.9), 94.86833, delta=0.01)

    def test_tas_to_cas_density_ratio_one(self):
        self.assertAlmostEqual(pec.tas_to_cas(100.0, 1.0), 100.0, delta=1e-9)

    def test_tas_to_cas_rejects_bad_ratio(self):
        with self.assertRaises(ValueError):
            pec.tas_to_cas(100.0, 0.0)
        with self.assertRaises(ValueError):
            pec.tas_to_cas(100.0, -0.5)

    def test_tas_to_cas_rejects_negative_speed(self):
        with self.assertRaises(ValueError):
            pec.tas_to_cas(-3.0, 0.9)

    # --- tower fly-by --------------------------------------------------------

    def test_tower_flyby_sign_low_altimeter(self):
        # Altimeter reads 10 m low (H_p = 490 at H_g = 500): dVp > 0,
        # about +0.88 m/s at the reference fly-by speed.
        dvp = pec.tower_flyby_position_error(500.0, 490.0, 288.15)
        self.assertTrue(math.isfinite(dvp))
        self.assertGreater(dvp, 0.0)
        self.assertAlmostEqual(dvp, 0.882, delta=0.02)

    def test_tower_flyby_sign_high_altimeter(self):
        # Altimeter reads 10 m high: the correction is negative.
        dvp = pec.tower_flyby_position_error(500.0, 510.0, 288.15)
        self.assertTrue(math.isfinite(dvp))
        self.assertLess(dvp, 0.0)
        self.assertAlmostEqual(dvp, -0.888, delta=0.02)

    def test_tower_flyby_zero_height_error(self):
        dvp = pec.tower_flyby_position_error(500.0, 500.0, 288.15)
        self.assertAlmostEqual(dvp, 0.0, delta=1e-6)

    def test_tower_flyby_magnitude_scales_with_error(self):
        # Doubling the height error roughly doubles the correction.
        dvp1 = pec.tower_flyby_position_error(500.0, 490.0, 288.15)
        dvp2 = pec.tower_flyby_position_error(1000.0, 980.0, 288.15)
        self.assertGreater(dvp2, dvp1)
        self.assertAlmostEqual(dvp2 / dvp1, 2.0, delta=0.2)

    def test_tower_flyby_pass_speed_sensitivity(self):
        # The same height error makes a smaller correction at a faster pass.
        low = pec.tower_flyby_position_error(500.0, 490.0, 288.15, v_ias=90.0)
        high = pec.tower_flyby_position_error(500.0, 490.0, 288.15, v_ias=120.0)
        self.assertGreater(low, high)
        self.assertAlmostEqual(low, 0.987, delta=0.02)
        self.assertAlmostEqual(high, 0.722, delta=0.02)
        # The default reduced form evaluates at the reference fly-by speed.
        dflt = pec.tower_flyby_position_error(500.0, 490.0, 288.15)
        ref = pec.tower_flyby_position_error(500.0, 490.0, 288.15,
                                             v_ias=pec.FLYBY_REFERENCE_CAS)
        self.assertAlmostEqual(dflt, ref, delta=1e-9)

    def test_tower_flyby_rejects_nonphysical(self):
        with self.assertRaises(ValueError):
            pec.tower_flyby_position_error(-1.0, 490.0, 288.15)
        with self.assertRaises(ValueError):
            pec.tower_flyby_position_error(500.0, 490.0, 0.0)
        with self.assertRaises(ValueError):
            pec.tower_flyby_position_error(500.0, 490.0, -10.0)
        with self.assertRaises(ValueError):
            pec.tower_flyby_position_error(500.0, 490.0, 288.15, v_ias=-5.0)

    # --- GPS doublet through to dVp at the test point ------------------------

    def test_gps_doublet_end_to_end(self):
        # 98/102 doublet at V_ias = 100 m/s, rho/rho0 = 0.9: the doublet says
        # the true airspeed is 100 m/s, so V_cas ~ 94.87 and dVp ~ -5.13.
        v_tas = pec.gps_doublet_tas(98.0, 102.0)
        v_cas = pec.tas_to_cas(v_tas, 0.9)
        dvp = pec.position_error(100.0, v_cas)
        self.assertAlmostEqual(v_cas, 94.86833, delta=0.01)
        self.assertAlmostEqual(dvp, -5.13167, delta=0.01)

    # --- PEC curve fit and table ----------------------------------------------

    def test_fit_pec_curve_reproduces_points(self):
        pts = [(60.0, 1.2), (80.0, 0.9), (100.0, 0.6), (120.0, 0.2), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        self.assertEqual(curve["breakpoints"], [60.0, 80.0, 100.0, 120.0, 140.0])
        self.assertAlmostEqual(curve["knot_dvp"][0], 1.2, delta=1e-9)
        self.assertAlmostEqual(curve["knot_dvp"][-1], -0.3, delta=1e-9)
        self.assertLess(curve["residual_rms"], 1e-9)

    def test_fit_pec_curve_slopes(self):
        pts = [(60.0, 1.2), (80.0, 0.9), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        self.assertAlmostEqual(curve["slopes"][0], -0.015, delta=1e-9)
        self.assertAlmostEqual(curve["slopes"][1], -0.02, delta=1e-9)

    def test_fit_pec_curve_repeat_passes_averaged(self):
        # Repeats at 60 m/s collapse to the mean knot and their scatter shows
        # up in the residual RMS data quality metric.
        pts = [(60.0, 1.2), (60.0, 1.4), (100.0, 0.6), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        self.assertEqual(len(curve["breakpoints"]), 3)
        self.assertAlmostEqual(curve["knot_dvp"][0], 1.3, delta=1e-9)
        self.assertAlmostEqual(curve["residual_rms"], 0.0707107, delta=1e-6)

    def test_fit_pec_curve_sorts_unsorted_points(self):
        pts = [(140.0, -0.3), (60.0, 1.2), (100.0, 0.6)]
        curve = pec.fit_pec_curve(pts)
        self.assertEqual(curve["breakpoints"], [60.0, 100.0, 140.0])

    def test_fit_pec_curve_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            pec.fit_pec_curve([])
        with self.assertRaises(ValueError):
            pec.fit_pec_curve([(100.0, 0.6)])
        with self.assertRaises(ValueError):
            pec.fit_pec_curve([(100.0, 0.6), (100.0, 0.6)])
        with self.assertRaises(ValueError):
            pec.fit_pec_curve([(-5.0, 0.6), (100.0, 0.6)])
        with self.assertRaises(ValueError):
            pec.fit_pec_curve([(100.0, float("nan")), (120.0, 0.2)])

    def test_pec_table_midpoint_interpolation(self):
        pts = [(60.0, 1.2), (80.0, 0.9), (100.0, 0.6), (120.0, 0.2), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        rows = pec.pec_table([60.0, 70.0, 80.0, 100.0, 140.0], curve)
        self.assertEqual(rows[0], (60.0, 1.2, 61.2))
        self.assertAlmostEqual(rows[1][1], 1.05, delta=1e-9)
        self.assertAlmostEqual(rows[1][2], 71.05, delta=1e-9)
        self.assertAlmostEqual(rows[-1][2], 139.7, delta=1e-9)

    def test_pec_table_rejects_bad_input(self):
        pts = [(60.0, 1.2), (100.0, 0.6)]
        curve = pec.fit_pec_curve(pts)
        with self.assertRaises(ValueError):
            pec.pec_table([], curve)
        with self.assertRaises(ValueError):
            pec.pec_table([100.0, 90.0, 110.0], curve)
        with self.assertRaises(ValueError):
            pec.pec_table([100.0, 100.0], curve)
        with self.assertRaises(ValueError):
            pec.pec_table([-1.0, 100.0], curve)
        with self.assertRaises(ValueError):
            pec.pec_table([60.0, 100.0], {"breakpoints": [60.0, 100.0]})

    # --- data quality verdict --------------------------------------------------

    def test_pec_verdict_keys_and_coverage(self):
        pts = [(60.0, 1.2), (80.0, 0.9), (100.0, 0.6), (120.0, 0.2), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        planned = [55.0, 60.0, 80.0, 100.0, 120.0, 140.0, 145.0]
        v = pec.pec_verdict(curve, planned, ["tower-fly-by", "gps-ground-speed-doublet"])
        for key in ("residual_rms", "coverage", "methods", "verdict"):
            self.assertIn(key, v)
        self.assertAlmostEqual(v["coverage"], 5.0 / 7.0, delta=1e-9)
        self.assertEqual(v["verdict"], "review")
        self.assertEqual(len(v["methods"]), 2)

    def test_pec_verdict_adequate_when_covered(self):
        pts = [(60.0, 1.2), (80.0, 0.9), (100.0, 0.6), (120.0, 0.2), (140.0, -0.3)]
        curve = pec.fit_pec_curve(pts)
        planned = [60.0, 80.0, 100.0, 120.0, 140.0]
        v = pec.pec_verdict(curve, planned, ["trailing-cone"])
        self.assertAlmostEqual(v["coverage"], 1.0, delta=1e-9)
        self.assertEqual(v["verdict"], "adequate")

    def test_pec_verdict_rejects_empty(self):
        pts = [(60.0, 1.2), (100.0, 0.6)]
        curve = pec.fit_pec_curve(pts)
        with self.assertRaises(ValueError):
            pec.pec_verdict(curve, [], ["tower-fly-by"])
        with self.assertRaises(ValueError):
            pec.pec_verdict(curve, [60.0, 100.0], [])

    def test_pec_table_to_verdict_workflow(self):
        # Full workflow: doublet points at several IAS, fit, table, verdict.
        pts = [(80.0, -1.0), (100.0, -0.4), (120.0, 0.2), (140.0, 0.8)]
        curve = pec.fit_pec_curve(pts)
        rows = pec.pec_table([80.0, 90.0, 100.0, 120.0, 140.0], curve)
        self.assertEqual(len(rows), 5)
        for v_ias, dvp, v_cas in rows:
            self.assertAlmostEqual(v_cas, v_ias + dvp, delta=1e-9)
        planned = [80.0, 90.0, 100.0, 120.0, 140.0]
        v = pec.pec_verdict(curve, planned, ["gps-ground-speed-doublet"])
        self.assertEqual(v["verdict"], "adequate")
        self.assertAlmostEqual(v["coverage"], 1.0, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
