#!/usr/bin/env python3
"""Behavior contract tests for windtunnel-data-reduction logic (gate 3).

Stdlib unittest, offline, deterministic. Run:
python3 skills/aerodynamics/wind-tunnel/windtunnel-data-reduction/scripts/test_windtunnel_data_reduction.py
"""

import math
import unittest

from windtunnel_data_reduction_logic import (
    corrected_dynamic_pressure,
    corrected_velocity,
    force_coefficients,
    interpolate_tare,
    mach_dynamic_pressure,
    prandtl_glauert_cp,
    pressure_coefficient,
    pressure_coefficients,
    reduce_wind_tunnel_run,
    repeat_run_uncertainty,
    reynolds_scale_cd,
    solid_blockage_eps,
    streamline_curvature_corrections,
    tare_correct_forces,
    tare_corrected_drag_offset,
    total_blockage_eps,
    wake_blockage_eps,
    wall_interference_alpha,
)


class TestTare(unittest.TestCase):
    def test_tare_subtraction_removes_drag_offset(self):
        # Zero angle of attack: the raw drag reading is pure support
        # tare, so the corrected drag offset must vanish.
        offset = tare_corrected_drag_offset(raw_drag=2.0, tare_drag=2.0)
        self.assertAlmostEqual(offset, 0.0, places=12)
        # A tare mismatch leaves the residual drag offset.
        self.assertAlmostEqual(
            tare_corrected_drag_offset(2.5, 2.0), 0.5, places=12
        )

    def test_tare_correct_forces(self):
        corr = tare_correct_forces(
            {"lift": 510.0, "drag": 32.0, "moment": 12.5},
            {"lift": 0.0, "drag": 2.08, "moment": 0.0},
        )
        self.assertAlmostEqual(corr["lift"], 510.0, places=12)
        self.assertAlmostEqual(corr["drag"], 29.92, places=12)
        self.assertAlmostEqual(corr["moment"], 12.5, places=12)

    def test_tareshift_linear_interpolation(self):
        # Tare runs at alpha 0 and 10 deg; tare at 4 deg is 20% up the
        # bracket: 2.0 + 0.4 * 0.2 = 2.08.
        tare = interpolate_tare(2.0, 2.2, 0.0, 10.0, 4.0)
        self.assertAlmostEqual(tare, 2.08, places=12)
        self.assertAlmostEqual(
            interpolate_tare(2.0, 2.2, 0.0, 10.0, 0.0), 2.0, places=12
        )
        self.assertAlmostEqual(
            interpolate_tare(2.0, 2.2, 0.0, 10.0, 10.0), 2.2, places=12
        )

    def test_tare_edges_invalid(self):
        with self.assertRaises(ValueError):
            interpolate_tare(2.0, 2.2, 5.0, 5.0, 5.0)  # degenerate bracket
        with self.assertRaises(ValueError):
            interpolate_tare(2.0, 2.2, 0.0, 10.0, -1.0)  # outside bracket
        with self.assertRaises(ValueError):
            tare_correct_forces(
                {"lift": 1.0, "drag": 1.0}, {"lift": 1.0, "drag": 1.0}
            )  # missing moment
        with self.assertRaises(ValueError):
            tare_corrected_drag_offset(-1.0, 2.0)


class TestBlockage(unittest.TestCase):
    def test_solid_blockage_numeric(self):
        # Model volume 0.004 m^3 in a 6 m^3 test section:
        # eps_sb = 0.96 * 0.004 / 6 = 0.00064.
        self.assertAlmostEqual(
            solid_blockage_eps(0.004, 6.0), 0.00064, places=12
        )

    def test_wake_blockage_numeric(self):
        # S = 0.4, C = 8.0, CDu = 0.0763265...:
        # eps_wb = 0.25 * (0.4 / 8.0) * CDu.
        eps_wb = wake_blockage_eps(0.4, 8.0, 0.0763265306122449)
        self.assertAlmostEqual(eps_wb, 0.0009540816326530612, places=12)

    def test_blockage_correction_increases_dynamic_pressure(self):
        # Any positive blockage raises q: q_corr = q_u (1 + eps)^2 > q_u.
        q = 980.0
        eps = 0.0015940816326530612
        q_corr = corrected_dynamic_pressure(q, eps)
        self.assertGreater(q_corr, q)
        self.assertAlmostEqual(
            q_corr, 980.0 * (1.0 + eps) ** 2, places=10
        )
        # Velocity correction keeps the same factor once.
        self.assertAlmostEqual(
            corrected_velocity(50.0, eps), 50.0 * (1.0 + eps), places=12
        )
        # Total blockage is the sum of the two parts.
        eps_total = total_blockage_eps(
            0.004, 6.0, 0.4, 8.0, 0.0763265306122449
        )
        self.assertAlmostEqual(eps_total, 0.0015940816326530612, places=12)

    def test_blockage_edges_invalid(self):
        with self.assertRaises(ValueError):
            solid_blockage_eps(-0.004, 6.0)
        with self.assertRaises(ValueError):
            solid_blockage_eps(0.004, 0.0)
        with self.assertRaises(ValueError):
            wake_blockage_eps(0.0, 8.0, 0.1)
        with self.assertRaises(ValueError):
            corrected_dynamic_pressure(0.0, 0.01)
        with self.assertRaises(ValueError):
            corrected_dynamic_pressure(980.0, -0.01)


class TestWallInterference(unittest.TestCase):
    def test_closed_section_alpha_correction(self):
        # S/C = 0.05, CL = 1.3010204...: delta_alpha =
        # 0.82 * 0.05 * CL rad = 3.05626... deg, alpha 4 -> 7.05626...
        d_alpha, alpha_corr = wall_interference_alpha(
            4.0, 0.4, 8.0, 1.3010204081632653
        )
        self.assertAlmostEqual(d_alpha, 3.0562621163738557, places=10)
        self.assertAlmostEqual(alpha_corr, 7.056262116373856, places=10)

    def test_open_section_smaller_correction(self):
        d_alpha, _ = wall_interference_alpha(
            4.0, 0.4, 8.0, 1.0, delta=0.125
        )
        self.assertAlmostEqual(d_alpha, math.degrees(0.125 * 0.05), places=10)

    def test_negative_lift_flips_sign(self):
        # Downward lift gives a negative correction (signed CL allowed).
        d_alpha, alpha_corr = wall_interference_alpha(
            4.0, 0.4, 8.0, -1.0
        )
        self.assertLess(d_alpha, 0.0)
        self.assertLess(alpha_corr, 4.0)

    def test_streamline_curvature(self):
        d_alpha_curv, d_cm = streamline_curvature_corrections(
            0.4, 8.0, 0.25, 1.5, 1.3010204081632653, 0.12755102040816327
        )
        self.assertAlmostEqual(d_alpha_curv, 0.1552978717669642, places=10)
        self.assertAlmostEqual(d_cm, -0.0013552295918367347, places=10)

    def test_wall_edges_invalid(self):
        with self.assertRaises(ValueError):
            wall_interference_alpha(4.0, 0.0, 8.0, 1.0)
        with self.assertRaises(ValueError):
            wall_interference_alpha(4.0, 0.4, 8.0, float("nan"))


class TestReynoldsAndMach(unittest.TestCase):
    def test_reynolds_scaling(self):
        # Turbulent flat plate: CD(3e6) = 0.008 * (6e6/3e6)^0.2.
        cd = reynolds_scale_cd(0.008, 6e6, 3e6, exponent=0.2)
        self.assertAlmostEqual(cd, 0.00918958683997628, places=10)
        # Laminar exponent is steeper.
        cd_lam = reynolds_scale_cd(0.008, 6e6, 3e6, exponent=0.5)
        self.assertGreater(cd_lam, cd)

    def test_mach_dynamic_pressure(self):
        q = mach_dynamic_pressure(101325.0, 0.3)
        self.assertAlmostEqual(q, 0.5 * 1.4 * 101325.0 * 0.09, places=10)

    def test_prandtl_glauert(self):
        # At M = 0.6 the factor is 1 / sqrt(1 - 0.36) = 1.25.
        self.assertAlmostEqual(
            prandtl_glauert_cp(-0.5, 0.6), -0.625, places=12
        )
        with self.assertRaises(ValueError):
            prandtl_glauert_cp(-0.5, 1.0)
        with self.assertRaises(ValueError):
            mach_dynamic_pressure(0.0, 0.3)


class TestCoefficientReduction(unittest.TestCase):
    def test_force_coefficients_known_case(self):
        # L = 500 N, D = 30 N, M = 12 N m at q = 1000 Pa, S = 0.5 m^2,
        # c = 0.25 m: CL = 1.0, CD = 0.06, Cm = 0.096.
        coef = force_coefficients(500.0, 30.0, 12.0, 1000.0, 0.5, 0.25)
        self.assertAlmostEqual(coef["cl"], 1.0, places=12)
        self.assertAlmostEqual(coef["cd"], 0.06, places=12)
        self.assertAlmostEqual(coef["cm"], 0.096, places=12)

    def test_pressure_coefficients(self):
        cp = pressure_coefficient(101325.0 - 500.0, 101325.0, 500.0)
        self.assertAlmostEqual(cp, -1.0, places=12)
        cps = pressure_coefficients(
            [101325.0, 101325.0 - 500.0], 101325.0, 500.0
        )
        self.assertEqual(len(cps), 2)
        self.assertAlmostEqual(cps[0], 0.0, places=12)
        self.assertAlmostEqual(cps[1], -1.0, places=12)

    def test_reduction_edges_invalid(self):
        with self.assertRaises(ValueError):
            force_coefficients(1.0, 1.0, 1.0, 0.0, 0.5, 0.25)
        with self.assertRaises(ValueError):
            force_coefficients(1.0, 1.0, 1.0, 1000.0, 0.0, 0.25)
        with self.assertRaises(ValueError):
            pressure_coefficient(1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            pressure_coefficients([], 101325.0, 500.0)


class TestUncertainty(unittest.TestCase):
    def test_repeat_run_uncertainty_bounds(self):
        # Five repeat drag coefficient runs with mean 0.03012 and sample
        # std 0.00025884... The expanded uncertainty at coverage 2 is
        # 2 * std / sqrt(5) = 0.0002315...
        runs = [0.0300, 0.0305, 0.0298, 0.0302, 0.0301]
        u = repeat_run_uncertainty(runs, coverage=2.0)
        self.assertEqual(u["n"], 5)
        self.assertAlmostEqual(u["mean"], 0.03012, places=6)
        self.assertAlmostEqual(u["std"], 0.00025884358211089565, places=12)
        self.assertAlmostEqual(u["standard_error"], 0.00011575836902790223, places=12)
        self.assertAlmostEqual(u["expanded"], 0.00023151673805580446, places=12)
        # The uncertainty bounds bracket the reported mean.
        self.assertGreater(u["expanded"], 0.0)
        self.assertLess(u["expanded"], u["std"])
        self.assertAlmostEqual(
            u["expanded"], 2.0 * u["standard_error"], places=12
        )

    def test_uncertainty_edges_invalid(self):
        with self.assertRaises(ValueError):
            repeat_run_uncertainty([0.03])  # need at least two runs
        with self.assertRaises(ValueError):
            repeat_run_uncertainty([0.03, 0.031], coverage=0.0)


class TestFullPipeline(unittest.TestCase):
    """End to end reduction: tare, tareshift, blockage, wall
    interference, streamline curvature, coefficient reduction."""

    def test_pipeline_known_case(self):
        res = reduce_wind_tunnel_run(
            raw_lift=510.0, raw_drag=32.0, raw_moment=12.5, alpha_deg=4.0,
            tare_low={"lift": 0.0, "drag": 2.0, "moment": 0.0},
            tare_high={"lift": 0.0, "drag": 2.2, "moment": 0.0},
            tare_alpha_low=0.0, tare_alpha_high=10.0,
            q_uncorrected=980.0, s_ref=0.4, c_ref=0.25,
            model_volume=0.004, test_section_volume=6.0,
            test_section_area=8.0, test_section_height=1.5, chord=0.25,
        )
        # Tare at 4 deg is 2.08 N of drag.
        self.assertAlmostEqual(res["tare_at_alpha"]["drag"], 2.08, places=12)
        self.assertAlmostEqual(res["forces_corrected"]["drag"], 29.92, places=12)
        # Blockage raises the dynamic pressure.
        self.assertGreater(res["q_corrected"], res["q_uncorrected"])
        self.assertAlmostEqual(res["eps"], 0.0015940816326530612, places=12)
        # Wall interference and curvature move alpha up.
        self.assertAlmostEqual(
            res["alpha_corrected_deg"], 7.21155998814082, places=8
        )
        # Final coefficients on the corrected dynamic pressure.
        self.assertAlmostEqual(res["coefficients_corrected"]["cl"], 1.2968824397064664, places=8)
        self.assertAlmostEqual(res["coefficients_corrected"]["cd"], 0.0760837697961127, places=8)
        self.assertAlmostEqual(res["coefficients_corrected"]["cm"], 0.12579010763428744, places=8)

    def test_pipeline_ledger_records_corrections(self):
        res = reduce_wind_tunnel_run(
            raw_lift=510.0, raw_drag=32.0, raw_moment=12.5, alpha_deg=4.0,
            tare_low={"lift": 0.0, "drag": 2.0, "moment": 0.0},
            tare_high={"lift": 0.0, "drag": 2.2, "moment": 0.0},
            tare_alpha_low=0.0, tare_alpha_high=10.0,
            q_uncorrected=980.0, s_ref=0.4, c_ref=0.25,
            model_volume=0.004, test_section_volume=6.0,
            test_section_area=8.0, test_section_height=1.5, chord=0.25,
        )
        steps = [entry["step"] for entry in res["ledger"]]
        for expected in ("tare", "coefficients-uncorrected", "blockage",
                         "wall-interference", "streamline-curvature",
                         "coefficients-corrected"):
            self.assertIn(expected, steps)

    def test_pipeline_compressible_dynamic_pressure(self):
        # At M = 0.4 the reference dynamic pressure comes from the
        # compressible form before blockage is applied.
        res = reduce_wind_tunnel_run(
            raw_lift=510.0, raw_drag=32.0, raw_moment=12.5, alpha_deg=4.0,
            tare_low={"lift": 0.0, "drag": 2.0, "moment": 0.0},
            tare_high={"lift": 0.0, "drag": 2.2, "moment": 0.0},
            tare_alpha_low=0.0, tare_alpha_high=10.0,
            q_uncorrected=980.0, s_ref=0.4, c_ref=0.25,
            model_volume=0.004, test_section_volume=6.0,
            test_section_area=8.0, test_section_height=1.5, chord=0.25,
            mach=0.4, p_static=101325.0,
        )
        q_comp = 0.5 * 1.4 * 101325.0 * 0.16
        self.assertAlmostEqual(res["q_uncorrected"], q_comp, places=8)
        self.assertGreater(res["q_corrected"], q_comp)


if __name__ == "__main__":
    unittest.main()
