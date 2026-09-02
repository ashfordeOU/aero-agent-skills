#!/usr/bin/env python3
"""Behavior contract tests for windtunnel-wall-corrections logic.

Stdlib unittest, offline, deterministic. Run:
python3 skills/aerodynamics/wind-tunnel/windtunnel-wall-corrections/scripts/test_windtunnel_wall_corrections.py

Contract: (a) internal consistency, corrections shrink as the
model-to-tunnel size ratio shrinks and eps stays non-negative, corrected
CL stays below the uncorrected value for positive blockage; (b) the
documented worked example (1.4 m by 1.0 m closed section, S_model =
0.16 m^2, model volume 0.004 m^3, span 0.9 m) reproduces the reference
values within 1%; (c) ValueError on non-positive inputs and on a model
larger than the test section.
"""

import math
import unittest

from windtunnel_wall_corrections_logic import (
    apply_wall_corrections,
    buoyancy_drag_increment,
    corrected_drag_coefficient,
    corrected_dynamic_pressure,
    corrected_lift_coefficient,
    corrected_velocity,
    correct_measured_polar,
    lift_interference_delta_alpha,
    sigma_lift_factor,
    solid_blockage,
    total_blockage,
    wake_blockage,
)

# Documented worked example (verified reference values): model with
# S_model = 0.16 m^2, volume 0.004 m^3, CDu = 0.03, CLu = 0.5, alpha_u =
# 4 deg, span 0.9 m in a closed 1.4 m by 1.0 m section (C = 1.4 m^2),
# q = 500 Pa.
S_REF = 0.16
MODEL_VOLUME = 0.004
CD_U = 0.03
CL_U = 0.5
ALPHA_U = 4.0
SPAN = 0.9
SECTION_AREA = 1.4
SECTION_HEIGHT = 1.0
Q_U = 500.0

REF_EPS_SB = 0.00125566
REF_EPS_WB = 0.000857143
REF_EPS = 0.00211280
REF_Q_C = 502.11503
REF_DELTA_ALPHA_DEG = 0.21428571
REF_ALPHA_C = 4.21428571
REF_SIGMA = 0.16654957
REF_CL_C = 0.41546956
REF_CD_C = 0.02983556
REF_BUOY = 0.0000125
REF_CD_C_BUOY = 0.02984806


def _within_1pct(actual, reference):
    return math.isclose(actual, reference, rel_tol=0.01, abs_tol=1e-12)


class TestSolidBlockage(unittest.TestCase):
    def test_worked_example_eps_sb_within_1pct(self):
        eps_sb = solid_blockage(MODEL_VOLUME, SECTION_AREA)
        self.assertTrue(_within_1pct(eps_sb, REF_EPS_SB), eps_sb)

    def test_eps_sb_linear_in_model_volume(self):
        # Halving the model volume halves the solid blockage.
        full = solid_blockage(MODEL_VOLUME, SECTION_AREA)
        half = solid_blockage(MODEL_VOLUME / 2.0, SECTION_AREA)
        self.assertAlmostEqual(half, full / 2.0, places=14)
        # A zero-volume (thin) model causes no solid blockage.
        self.assertEqual(solid_blockage(0.0, SECTION_AREA), 0.0)

    def test_eps_sb_shrinks_for_larger_test_section(self):
        small_section = solid_blockage(MODEL_VOLUME, 1.4)
        large_section = solid_blockage(MODEL_VOLUME, 4.0)
        self.assertGreater(small_section, large_section)
        self.assertGreaterEqual(small_section, 0.0)

    def test_eps_sb_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            solid_blockage(-0.001, SECTION_AREA)
        with self.assertRaises(ValueError):
            solid_blockage(MODEL_VOLUME, 0.0)
        with self.assertRaises(ValueError):
            solid_blockage(MODEL_VOLUME, -1.4)
        with self.assertRaises(ValueError):
            solid_blockage(MODEL_VOLUME, SECTION_AREA, k1=0.0)
        with self.assertRaises(ValueError):
            solid_blockage(MODEL_VOLUME, SECTION_AREA, k1=-0.52)

    def test_eps_sb_rejects_model_larger_than_test_section(self):
        # Model volume at or above the section volume scale C^1.5 fails.
        scale = SECTION_AREA ** 1.5
        with self.assertRaises(ValueError):
            solid_blockage(scale, SECTION_AREA)
        with self.assertRaises(ValueError):
            solid_blockage(scale * 2.0, SECTION_AREA)
        # A model just inside the scale is accepted.
        self.assertGreaterEqual(
            solid_blockage(scale * 0.9, SECTION_AREA), 0.0)


class TestWakeBlockage(unittest.TestCase):
    def test_worked_example_eps_wb_within_1pct(self):
        eps_wb = wake_blockage(S_REF, SECTION_AREA, CD_U)
        self.assertTrue(_within_1pct(eps_wb, REF_EPS_WB), eps_wb)
        # Zero uncorrected drag leaves no wake to block the section.
        self.assertEqual(wake_blockage(S_REF, SECTION_AREA, 0.0), 0.0)

    def test_eps_wb_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            wake_blockage(0.0, SECTION_AREA, CD_U)
        with self.assertRaises(ValueError):
            wake_blockage(S_REF, 0.0, CD_U)
        with self.assertRaises(ValueError):
            wake_blockage(S_REF, SECTION_AREA, -0.03)

    def test_eps_wb_rejects_model_larger_than_test_section(self):
        with self.assertRaises(ValueError):
            wake_blockage(1.5, 1.4, CD_U)  # planform area >= section area


class TestTotalBlockage(unittest.TestCase):
    def test_total_is_sum_of_components(self):
        eps = total_blockage(MODEL_VOLUME, SECTION_AREA, S_REF, CD_U)
        eps_manual = solid_blockage(MODEL_VOLUME, SECTION_AREA) + \
            wake_blockage(S_REF, SECTION_AREA, CD_U)
        self.assertAlmostEqual(eps, eps_manual, places=14)
        self.assertTrue(_within_1pct(eps, REF_EPS), eps)

    def test_total_blockage_nonnegative(self):
        for vm, s in [(0.004, 0.16), (0.001, 0.05), (0.0, 0.0)]:
            eps = total_blockage(vm, SECTION_AREA, s if s else 0.16,
                                 0.03 if s else 0.0)
            self.assertGreaterEqual(eps, 0.0)


class TestDynamicPressureAndVelocity(unittest.TestCase):
    def test_worked_example_q_c_within_1pct(self):
        q_c = corrected_dynamic_pressure(Q_U, REF_EPS)
        self.assertTrue(_within_1pct(q_c, REF_Q_C), q_c)

    def test_q_c_identity_and_monotone_in_eps(self):
        self.assertEqual(corrected_dynamic_pressure(500.0, 0.0), 500.0)
        self.assertAlmostEqual(
            corrected_dynamic_pressure(500.0, 0.01),
            500.0 * 1.01 ** 2, places=9)
        # Blockage always raises the dynamic pressure.
        self.assertGreater(
            corrected_dynamic_pressure(Q_U, 0.01),
            corrected_dynamic_pressure(Q_U, 0.0))

    def test_velocity_ratio_and_identity(self):
        self.assertAlmostEqual(
            corrected_velocity(50.0, REF_EPS), 50.0 * (1.0 + REF_EPS),
            places=12)
        self.assertEqual(corrected_velocity(50.0, 0.0), 50.0)

    def test_q_v_reject_non_physical(self):
        with self.assertRaises(ValueError):
            corrected_dynamic_pressure(0.0, 0.01)
        with self.assertRaises(ValueError):
            corrected_dynamic_pressure(500.0, -0.01)
        with self.assertRaises(ValueError):
            corrected_velocity(0.0, 0.01)
        with self.assertRaises(ValueError):
            corrected_velocity(50.0, -0.01)


class TestBuoyancyDrag(unittest.TestCase):
    def test_worked_example_buoyancy_increment(self):
        # dP/dx = -0.25 Pa/m: pressure falls streamwise, drag is added.
        buoy = buoyancy_drag_increment(-0.25, MODEL_VOLUME, Q_U, S_REF)
        self.assertTrue(_within_1pct(buoy, REF_BUOY), buoy)

    def test_buoyancy_sign_convention(self):
        # Negative gradient (closed solid-wall tunnel) adds drag.
        self.assertGreater(
            buoyancy_drag_increment(-0.25, MODEL_VOLUME, Q_U, S_REF), 0.0)
        # Positive gradient subtracts drag.
        self.assertLess(
            buoyancy_drag_increment(0.25, MODEL_VOLUME, Q_U, S_REF), 0.0)
        # Zero gradient gives zero increment.
        self.assertEqual(
            buoyancy_drag_increment(0.0, MODEL_VOLUME, Q_U, S_REF), 0.0)

    def test_buoyancy_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            buoyancy_drag_increment(float("nan"), MODEL_VOLUME, Q_U, S_REF)
        with self.assertRaises(ValueError):
            buoyancy_drag_increment(-0.25, MODEL_VOLUME, 0.0, S_REF)
        with self.assertRaises(ValueError):
            buoyancy_drag_increment(-0.25, MODEL_VOLUME, Q_U, 0.0)
        with self.assertRaises(ValueError):
            buoyancy_drag_increment(-0.25, -0.004, Q_U, S_REF)


class TestSigmaLiftFactor(unittest.TestCase):
    def test_worked_example_sigma_within_1pct(self):
        sigma = sigma_lift_factor(SPAN, SECTION_HEIGHT)
        self.assertTrue(_within_1pct(sigma, REF_SIGMA), sigma)

    def test_sigma_monotonic_in_span(self):
        small = sigma_lift_factor(0.45, SECTION_HEIGHT)
        large = sigma_lift_factor(SPAN, SECTION_HEIGHT)
        self.assertLess(small, large)
        # A vanishing span leaves only the classical closed-wall lift.
        self.assertAlmostEqual(
            sigma_lift_factor(1e-9, SECTION_HEIGHT), 0.0, places=9)

    def test_sigma_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            sigma_lift_factor(0.0, SECTION_HEIGHT)
        with self.assertRaises(ValueError):
            sigma_lift_factor(SPAN, 0.0)
        with self.assertRaises(ValueError):
            sigma_lift_factor(SPAN, SECTION_HEIGHT, coefficient=0.0)
        # The span must stay below the section height for the closed
        # wall image model to hold.
        with self.assertRaises(ValueError):
            sigma_lift_factor(1.0, 1.0)
        with self.assertRaises(ValueError):
            sigma_lift_factor(1.2, 1.0)


class TestLiftInterferenceAlpha(unittest.TestCase):
    def test_worked_example_alpha_within_1pct(self):
        d_deg, alpha_c = lift_interference_delta_alpha(
            ALPHA_U, S_REF, SECTION_AREA, CL_U)
        self.assertTrue(_within_1pct(d_deg, REF_DELTA_ALPHA_DEG), d_deg)
        self.assertTrue(_within_1pct(alpha_c, REF_ALPHA_C), alpha_c)
        self.assertAlmostEqual(alpha_c, ALPHA_U + d_deg, places=12)

    def test_alpha_correction_scales_with_lift(self):
        zero_cl, _ = lift_interference_delta_alpha(
            ALPHA_U, S_REF, SECTION_AREA, 0.0)
        high_cl, _ = lift_interference_delta_alpha(
            ALPHA_U, S_REF, SECTION_AREA, 1.0)
        self.assertEqual(zero_cl, 0.0)
        self.assertAlmostEqual(high_cl, 2.0 * REF_DELTA_ALPHA_DEG,
                               places=6)

    def test_alpha_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            lift_interference_delta_alpha(ALPHA_U, S_REF, SECTION_AREA,
                                          float("nan"))
        with self.assertRaises(ValueError):
            lift_interference_delta_alpha(ALPHA_U, 0.0, SECTION_AREA, CL_U)
        with self.assertRaises(ValueError):
            lift_interference_delta_alpha(ALPHA_U, S_REF, 0.0, CL_U)
        with self.assertRaises(ValueError):
            lift_interference_delta_alpha(ALPHA_U, S_REF, SECTION_AREA,
                                          CL_U, delta=0.0)


class TestCorrectedCoefficients(unittest.TestCase):
    def test_worked_example_cl_c_within_1pct(self):
        cl_c = corrected_lift_coefficient(CL_U, REF_SIGMA, REF_EPS_SB)
        self.assertTrue(_within_1pct(cl_c, REF_CL_C), cl_c)

    def test_worked_example_cd_c_within_1pct(self):
        cd_c = corrected_drag_coefficient(CD_U, REF_EPS_SB, REF_EPS_WB)
        self.assertTrue(_within_1pct(cd_c, REF_CD_C), cd_c)

    def test_corrected_cl_below_uncorrected_for_positive_blockage(self):
        cl_c = corrected_lift_coefficient(CL_U, REF_SIGMA, REF_EPS_SB)
        self.assertLess(cl_c, CL_U)
        self.assertGreater(cl_c, 0.0)

    def test_corrected_cd_below_uncorrected_without_buoyancy(self):
        cd_c = corrected_drag_coefficient(CD_U, REF_EPS_SB, REF_EPS_WB)
        self.assertLess(cd_c, CD_U)
        self.assertGreater(cd_c, 0.0)

    def test_corrected_cd_with_buoyancy_increment(self):
        cd_c = corrected_drag_coefficient(CD_U, REF_EPS_SB, REF_EPS_WB,
                                          REF_BUOY)
        self.assertTrue(_within_1pct(cd_c, REF_CD_C_BUOY), cd_c)
        # The negative streamwise gradient adds drag on top of the
        # blockage correction.
        self.assertGreater(cd_c,
                           corrected_drag_coefficient(CD_U, REF_EPS_SB,
                                                      REF_EPS_WB))

    def test_identity_without_any_correction(self):
        self.assertEqual(corrected_lift_coefficient(0.5, 0.0, 0.0), 0.5)
        self.assertEqual(corrected_drag_coefficient(0.03, 0.0, 0.0), 0.03)

    def test_coefficients_reject_bad_inputs(self):
        with self.assertRaises(ValueError):
            corrected_lift_coefficient(CL_U, -0.01, REF_EPS_SB)
        with self.assertRaises(ValueError):
            corrected_lift_coefficient(CL_U, REF_SIGMA, -REF_EPS_SB)
        with self.assertRaises(ValueError):
            corrected_drag_coefficient(-0.03, REF_EPS_SB, REF_EPS_WB)
        with self.assertRaises(ValueError):
            corrected_drag_coefficient(CD_U, -REF_EPS_SB, REF_EPS_WB)
        with self.assertRaises(ValueError):
            corrected_drag_coefficient(CD_U, REF_EPS_SB, -REF_EPS_WB)


class TestPipeline(unittest.TestCase):
    def _run_worked_example(self, **kw):
        params = {"q_uncorrected": Q_U}
        params.update(kw)
        return apply_wall_corrections(
            ALPHA_U, CL_U, CD_U, S_REF, MODEL_VOLUME, SECTION_AREA,
            SECTION_HEIGHT, SPAN, **params)

    def test_full_run_matches_individual_calls(self):
        res = self._run_worked_example(v_uncorrected=50.0,
                                       dpdx=-0.25)
        self.assertAlmostEqual(res["eps_sb"], REF_EPS_SB, delta=1e-6)
        self.assertAlmostEqual(res["eps_wb"], REF_EPS_WB, delta=1e-6)
        self.assertAlmostEqual(res["eps"], REF_EPS, delta=1e-6)
        self.assertAlmostEqual(res["sigma"], REF_SIGMA, delta=1e-6)
        self.assertAlmostEqual(res["q_corrected"], REF_Q_C, delta=1.0)
        self.assertAlmostEqual(res["alpha_corrected_deg"], REF_ALPHA_C,
                               places=6)
        self.assertAlmostEqual(res["cl_corrected"], REF_CL_C, delta=1e-5)
        self.assertAlmostEqual(res["cd_corrected"], REF_CD_C_BUOY,
                               delta=1e-5)
        self.assertAlmostEqual(res["v_corrected"],
                               50.0 * (1.0 + REF_EPS), delta=1e-6)
        self.assertAlmostEqual(res["buoyancy_increment"], REF_BUOY,
                               places=12)
        self.assertEqual(len(res["ledger"]), 8)

    def test_pipeline_without_buoyancy_gradient(self):
        res = self._run_worked_example()
        self.assertEqual(res["buoyancy_increment"], 0.0)
        self.assertAlmostEqual(res["cd_corrected"], REF_CD_C, delta=1e-5)
        self.assertIsNone(res["v_corrected"])

    def test_pipeline_rejects_model_larger_than_test_section(self):
        # Model volume at the section volume scale C^1.5 fails.
        with self.assertRaises(ValueError):
            apply_wall_corrections(ALPHA_U, CL_U, CD_U, S_REF,
                                   SECTION_AREA ** 1.5, SECTION_AREA,
                                   SECTION_HEIGHT, SPAN, Q_U)
        # Planform area not smaller than the section area fails.
        with self.assertRaises(ValueError):
            apply_wall_corrections(ALPHA_U, CL_U, CD_U, 1.5, MODEL_VOLUME,
                                   SECTION_AREA, SECTION_HEIGHT, SPAN, Q_U)
        # Span not smaller than the section height fails.
        with self.assertRaises(ValueError):
            apply_wall_corrections(ALPHA_U, CL_U, CD_U, S_REF, MODEL_VOLUME,
                                   SECTION_AREA, SECTION_HEIGHT, 1.1, Q_U)
        # A non-positive dynamic pressure fails.
        with self.assertRaises(ValueError):
            self._run_worked_example(q_uncorrected=-500.0)

    def test_polar_matches_per_point_correction(self):
        points = [
            {"alpha_deg": 0.0, "cl": 0.0, "cd": 0.02},
            {"alpha_deg": 4.0, "cl": 0.5, "cd": 0.03},
            {"alpha_deg": 8.0, "cl": 0.95, "cd": 0.055},
        ]
        corr = correct_measured_polar(points, S_REF, MODEL_VOLUME,
                                      SECTION_AREA, SECTION_HEIGHT, SPAN,
                                      Q_U, dpdx=-0.25)
        self.assertEqual(len(corr), 3)
        for p, r in zip(points, corr):
            single = apply_wall_corrections(
                p["alpha_deg"], p["cl"], p["cd"], S_REF, MODEL_VOLUME,
                SECTION_AREA, SECTION_HEIGHT, SPAN, Q_U, dpdx=-0.25)
            self.assertAlmostEqual(r["alpha_corrected_deg"],
                                   single["alpha_corrected_deg"], places=9)
            self.assertAlmostEqual(r["cl_corrected"],
                                   single["cl_corrected"], places=12)
            self.assertAlmostEqual(r["cd_corrected"],
                                   single["cd_corrected"], places=12)
        # Zero-lift points keep their geometric angle; positive-lift
        # points shift up, and every corrected CL stays below CLu.
        for r in corr:
            self.assertLessEqual(r["cl_corrected"], r["cl_uncorrected"])
            if r["cl_uncorrected"] == 0.0:
                self.assertEqual(r["alpha_corrected_deg"],
                                 r["alpha_uncorrected_deg"])
                self.assertEqual(r["cl_corrected"], 0.0)
            else:
                self.assertLess(r["cl_corrected"], r["cl_uncorrected"])
                self.assertGreater(r["alpha_corrected_deg"],
                                   r["alpha_uncorrected_deg"])

    def test_polar_rejects_empty(self):
        with self.assertRaises(ValueError):
            correct_measured_polar([], S_REF, MODEL_VOLUME, SECTION_AREA,
                                   SECTION_HEIGHT, SPAN, Q_U)


if __name__ == "__main__":
    unittest.main()
