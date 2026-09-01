#!/usr/bin/env python3
"""Gate 3 contract test: centrifugal compressor stage logic.

stdlib unittest, offline, deterministic. Exercises
scripts/centrifugal_compressor_logic.py against hand-computed
analytic references (SI units):

  tip speed:    N = 15000 rpm, d = 0.3 m gives
                U = pi*0.3*15000/60 = 75*pi = 235.6194 m/s
  Wiesner:      z = 10 radial blades gives
                sigma = 1 - 10**-0.7 = 0.8005
  Stanitz:      z = 20 gives sigma = 1 - 1.98/20 = 0.901
  Euler work:   sigma = 1, no prewhirl gives w = u2**2 = 160000 J/kg
                and psi = 1 (the slip-free Euler work relation)
  Back sweep:   u2 = 400, sigma = 0.9, cm2 = 100, beta2b = atan(1/4)
                gives w = 400*(360 - 25) = 134000 J/kg,
                psi = 134000/160000 = 0.8375
  Pressure ratio: w = 160000 J/kg, t01 = 288 K, eta = 0.85 gives
                pi = (1 + 0.85*160000/(1005*288))**3.5 = 3.8501
  Isentropic:   delta_t0 = 100 K with eta = 1 gives
                pi = (1 + 100/288)**3.5 = 2.8382
  Diffusion:    ca1 = 150, u1 = 250, cm2 = 100 gives
                w1 = sqrt(85000) = 291.5476 m/s, w2 = 100 m/s,
                dr = 2.9155 (diffusion_ok False); cm2 = 200 gives
                dr = 1.4577 (diffusion_ok True)

Run: python3 scripts/test_centrifugal_compressor.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from centrifugal_compressor_logic import (  # noqa: E402
    tip_speed,
    wiesner_slip,
    stanitz_slip,
    euler_work,
    work_input_coefficient,
    total_temperature_rise,
    stage_pressure_ratio,
    relative_velocities,
    diffusion_ratio,
    design_point,
)


class TestCentrifugalCompressor(unittest.TestCase):
    def test_tip_speed_analytic(self):
        """N = 15000 rpm, d = 0.3 m gives U = pi*d*N/60 = 75*pi m/s."""
        self.assertAlmostEqual(tip_speed(15000.0, 0.3), 75.0 * math.pi,
                               places=4)
        self.assertAlmostEqual(tip_speed(15000.0, 0.3), 235.6194, places=3)

    def test_tip_speed_scales_with_diameter(self):
        """Halving the diameter halves the tip speed at fixed rpm."""
        self.assertAlmostEqual(tip_speed(15000.0, 0.15),
                               tip_speed(15000.0, 0.3) / 2.0, places=9)

    def test_wiesner_slip_analytic(self):
        """z = 10 radial blades gives sigma = 1 - 10**-0.7 = 0.8005."""
        self.assertAlmostEqual(wiesner_slip(10), 0.8005, places=4)
        self.assertAlmostEqual(
            wiesner_slip(10), 1.0 - 1.0 / (10.0 ** 0.7), places=9)

    def test_wiesner_slip_backsweep_relation(self):
        """cos(beta2b) enters as sqrt(cos): beta2b = pi/3 halves the
        correction numerator; back sweep slightly raises sigma."""
        self.assertAlmostEqual(
            wiesner_slip(22, math.pi / 3.0),
            1.0 - math.sqrt(0.5) / (22.0 ** 0.7), places=9)
        self.assertGreater(wiesner_slip(22, 0.5), wiesner_slip(22, 0.0))

    def test_stanitz_slip_analytic(self):
        """z = 20 radial vanes gives sigma = 1 - 1.98/20 = 0.901."""
        self.assertAlmostEqual(stanitz_slip(20), 0.901, places=4)
        self.assertAlmostEqual(stanitz_slip(20), 1.0 - 1.98 / 20.0, places=9)

    def test_euler_work_slip_free(self):
        """sigma = 1 with radial vanes and no prewhirl gives the
        slip-free Euler work relation w = u2**2 regardless of cm2."""
        self.assertAlmostEqual(euler_work(400.0, 1.0, 100.0), 160000.0,
                               places=4)
        self.assertAlmostEqual(euler_work(400.0, 1.0, 250.0), 160000.0,
                               places=4)
        self.assertAlmostEqual(work_input_coefficient(400.0, 1.0, 100.0),
                               1.0, places=6)

    def test_euler_work_backsweep(self):
        """beta2b = atan(1/4), cm2 = 100: w = 400*(360 - 25) = 134000."""
        beta = math.atan(0.25)
        self.assertAlmostEqual(euler_work(400.0, 0.9, 100.0, beta),
                               134000.0, places=4)
        self.assertAlmostEqual(work_input_coefficient(400.0, 0.9, 100.0,
                                                      beta), 0.8375, places=4)
        # Backward sweep reduces the work input below the radial case.
        self.assertLess(euler_work(400.0, 0.9, 100.0, 0.3),
                        euler_work(400.0, 0.9, 100.0, 0.0))

    def test_euler_work_prewhirl(self):
        """Inducer prewhirl subtracts u1*ctheta1 from the rotor work."""
        self.assertAlmostEqual(euler_work(400.0, 1.0, 100.0,
                                          u1=200.0, ctheta1=50.0),
                               150000.0, places=4)

    def test_total_temperature_rise_analytic(self):
        """w = 160000 J/kg with cp = 1005 gives delta_t0 = 159.204 K."""
        self.assertAlmostEqual(total_temperature_rise(160000.0),
                               160000.0 / 1005.0, places=9)
        self.assertAlmostEqual(total_temperature_rise(160000.0), 159.204,
                               places=3)

    def test_stage_pressure_ratio_analytic(self):
        """pi = (1 + 0.85*160000/(1005*288))**3.5 = 3.8501."""
        ref = (1.0 + 0.85 * 160000.0 / (1005.0 * 288.0)) ** 3.5
        self.assertAlmostEqual(stage_pressure_ratio(160000.0, 288.0,
                                                    eta=0.85), ref, places=6)
        self.assertAlmostEqual(stage_pressure_ratio(160000.0, 288.0,
                                                    eta=0.85), 3.8501,
                               places=3)

    def test_stage_pressure_ratio_isentropic(self):
        """eta = 1 and delta_t0 = 100 K gives
        pi = (1 + 100/288)**3.5 = 2.8382 (isentropic relation)."""
        ref = (1.0 + 100.0 / 288.0) ** 3.5
        self.assertAlmostEqual(stage_pressure_ratio(100500.0, 288.0,
                                                    eta=1.0), ref, places=6)
        self.assertAlmostEqual(stage_pressure_ratio(100500.0, 288.0,
                                                    eta=1.0), 2.8382,
                               places=3)

    def test_relative_velocities_analytic(self):
        """ca1 = 150, u1 = 250 gives w1 = sqrt(85000) = 291.5476 m/s."""
        w1, w2 = relative_velocities(150.0, 250.0, 0.0, 100.0, 0.0)
        self.assertAlmostEqual(w1, math.sqrt(85000.0), places=9)
        self.assertAlmostEqual(w1, 291.5476, places=3)
        self.assertAlmostEqual(w2, 100.0, places=9)

    def test_diffusion_ratio_check(self):
        """dr = 2.9155 with cm2 = 100 flags over-diffusion; cm2 = 200
        gives dr = 1.4577 and passes the 1.6 limit."""
        d = diffusion_ratio(150.0, 250.0, 0.0, 100.0, 0.0)
        self.assertAlmostEqual(d["dr"], 2.9155, places=3)
        self.assertAlmostEqual(d["de_haller"], 0.3430, places=3)
        self.assertFalse(d["diffusion_ok"])
        d2 = diffusion_ratio(150.0, 250.0, 0.0, 200.0, 0.0)
        self.assertAlmostEqual(d2["dr"], 1.4577, places=3)
        self.assertTrue(d2["diffusion_ok"])

    def test_design_point_consistency(self):
        """design_point assembles the stage from the same relations."""
        dp = design_point(15000.0, 0.3, 0.18, 22, 90.0, 140.0, 288.0)
        self.assertEqual(
            set(dp.keys()),
            {"u2", "u1", "sigma", "work", "psi", "delta_t0",
             "pressure_ratio", "w1", "w2", "dr", "de_haller",
             "diffusion_ok"},
        )
        self.assertAlmostEqual(dp["u2"], tip_speed(15000.0, 0.3), places=9)
        self.assertAlmostEqual(dp["u1"], tip_speed(15000.0, 0.18), places=9)
        self.assertAlmostEqual(dp["sigma"], wiesner_slip(22), places=9)
        self.assertAlmostEqual(dp["work"],
                               euler_work(dp["u2"], dp["sigma"], 90.0),
                               places=6)
        self.assertAlmostEqual(dp["psi"], dp["work"] / dp["u2"] ** 2,
                               places=9)
        self.assertAlmostEqual(dp["delta_t0"],
                               total_temperature_rise(dp["work"]), places=9)
        self.assertAlmostEqual(dp["pressure_ratio"],
                               stage_pressure_ratio(dp["work"], 288.0,
                                                    eta=0.85), places=9)
        self.assertAlmostEqual(dp["dr"], dp["w1"] / dp["w2"], places=9)
        # Anchored literals for the 15000 rpm / 0.3 m design point.
        self.assertAlmostEqual(dp["u2"], 235.6194, places=3)
        self.assertAlmostEqual(dp["sigma"], 0.8851, places=4)
        self.assertAlmostEqual(dp["pressure_ratio"], 1.6028, places=3)
        self.assertFalse(dp["diffusion_ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tip_speed(0.0, 0.3)
        with self.assertRaises(ValueError):
            tip_speed(15000.0, 0.0)
        with self.assertRaises(ValueError):
            wiesner_slip(0)
        with self.assertRaises(ValueError):
            wiesner_slip(22, math.pi / 2.0)
        with self.assertRaises(ValueError):
            stanitz_slip(1)
        with self.assertRaises(ValueError):
            euler_work(0.0, 0.9, 100.0)
        with self.assertRaises(ValueError):
            euler_work(400.0, 0.0, 100.0)
        with self.assertRaises(ValueError):
            stage_pressure_ratio(160000.0, 0.0)
        with self.assertRaises(ValueError):
            stage_pressure_ratio(160000.0, 288.0, eta=1.5)
        with self.assertRaises(ValueError):
            relative_velocities(0.0, 250.0, 0.0, 100.0, 0.0)
        with self.assertRaises(ValueError):
            diffusion_ratio(150.0, 250.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            design_point(15000.0, 0.3, 0.18, 22, 90.0, 140.0, 0.0)
        with self.assertRaises(ValueError):
            design_point(15000.0, 0.3, 0.18, 22, 90.0, 140.0, 288.0,
                         slip="bogus")


if __name__ == "__main__":
    unittest.main()
