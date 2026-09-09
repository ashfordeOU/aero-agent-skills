#!/usr/bin/env python3
"""Gate 3 contract test: sliding-mode-control logic.

Exercises scripts/sliding_mode_control_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the
plant, the nominal model and the matched-uncertainty bound as given design
inputs, step 2 choosing the sliding surface from the tracking error and its
derivative, step 3 computing the equivalent control that holds the surface
on the nominal model, step 4 sizing the switching gain above the
uncertainty bound and forming the boundary-layer switched term, step 5
simulating the closed loop and auditing the sliding-condition margin at
every sample outside the layer, step 6 reading the finite-time reach of
the boundary layer and the boundary-layer equilibrium tracking-error
offset, and step 7 the chattering-suppression check of the boundary-layer
command against the ideal sign switching at the same gains. Also reviews
determinism across repeated runs and ValueError rejection of every
non-physical input (lambda, phi, k, F, disturbance D, dt, sim_time).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib

smc = importlib.import_module("sliding_mode_control_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Module constants match the spec's pinned worked-example configuration."""

    def test_constants(self):
        self.assertTrue(math.isclose(smc.LAMBDA, 2.0))
        self.assertTrue(math.isclose(smc.ETA, 1.5))
        self.assertTrue(math.isclose(smc.WORKED_F, 0.5))
        self.assertTrue(math.isclose(smc.WORKED_K, 2.0))
        self.assertTrue(math.isclose(smc.ROBUST_F, 0.9))
        self.assertTrue(math.isclose(smc.ROBUST_K, 2.4))
        self.assertTrue(math.isclose(smc.WORKED_PHI, 0.05))
        self.assertTrue(math.isclose(smc.SIGN_PHI, 0.0))
        self.assertTrue(math.isclose(smc.WORKED_D, 0.5))
        self.assertTrue(math.isclose(smc.ROBUST_D, 0.9))
        self.assertTrue(math.isclose(smc.DT, 0.001))
        self.assertTrue(math.isclose(smc.SIM_TIME, 6.0))
        self.assertTrue(math.isclose(smc.JUMP_THRESHOLD, 0.5))


class SlidingSurfaceSaturationTest(unittest.TestCase):
    """Step 2, closed-form surface and boundary-layer saturation."""

    def test_surface_closed_form(self):
        s0 = smc.sliding_surface(-1.0, 0.0, 2.0)
        self.assertAlmostEqual(s0, -2.0, delta=1e-12)

    def test_sat_quarter_into_layer(self):
        self.assertAlmostEqual(smc.sat_value(0.0125, 0.05), 0.25, delta=1e-12)

    def test_sat_saturates_outside_layer(self):
        self.assertAlmostEqual(smc.sat_value(0.2, 0.05), 1.0, delta=1e-12)
        self.assertAlmostEqual(smc.sat_value(-0.2, 0.05), -1.0, delta=1e-12)

    def test_sat_ideal_sign_at_zero_phi(self):
        self.assertAlmostEqual(smc.sat_value(0.1, 0.0), 1.0, delta=1e-12)
        self.assertAlmostEqual(smc.sat_value(-0.1, 0.0), -1.0, delta=1e-12)
        self.assertAlmostEqual(smc.sat_value(0.0, 0.0), 0.0, delta=1e-12)


class EquivalentControlLawTest(unittest.TestCase):
    """Step 3, the equivalent control closed form and the surface-rate identity."""

    def test_equivalent_control_worked_closed_form(self):
        v = 0.7
        u_eq = smc.equivalent_control(-v, 0.0, v, smc.LAMBDA)
        self.assertAlmostEqual(u_eq, (1.0 - smc.LAMBDA) * v, delta=1e-12)

    def test_surface_rate_law_identity(self):
        r = smc.simulate_sliding_control()
        residual = max(
            abs(r["s_dot"][i] - (smc.WORKED_D - smc.WORKED_K * smc.sat_value(r["s"][i], smc.WORKED_PHI)))
            for i in range(r["n"])
        )
        self.assertLess(residual, 1e-9)


class SwitchedTermTest(unittest.TestCase):
    """Step 4, the switching term and the switching-gain guards."""

    def test_switched_term_worked_initial_command(self):
        s0 = -2.0
        u_sw0 = smc.switched_term(s0, smc.WORKED_K, smc.WORKED_PHI)
        self.assertAlmostEqual(u_sw0, smc.WORKED_K, delta=1e-12)

    def test_switched_term_matches_negative_k_times_sat(self):
        s, k, phi = 0.03, 2.0, 0.05
        self.assertAlmostEqual(smc.switched_term(s, k, phi), -k * smc.sat_value(s, phi), delta=1e-12)


class SlidingConditionAuditTest(unittest.TestCase):
    """Step 5, the sliding-condition margin audit over outside samples."""

    def test_worked_margin_and_violations(self):
        r = smc.simulate_sliding_control()
        self.assertEqual(r["outside"], 781)
        self.assertAlmostEqual(r["worst_margin"], 0.05, delta=1e-6)
        self.assertEqual(r["violations"], 0)

    def test_robust_margin_and_violations(self):
        r = smc.simulate_sliding_control(k=smc.ROBUST_K, bound_f=smc.ROBUST_F, disturbance_d=smc.ROBUST_D)
        self.assertEqual(r["outside"], 591)
        self.assertAlmostEqual(r["worst_margin"], 0.0954, delta=1e-6)
        self.assertEqual(r["violations"], 0)

    def test_margin_non_negative_on_every_outside_sample(self):
        r = smc.simulate_sliding_control()
        for i in range(r["n"]):
            if abs(r["s"][i]) > smc.WORKED_PHI:
                margin = smc.sliding_condition_margin(r["s"][i], r["s_dot"][i], r["eta_cert"])
                self.assertGreater(margin, -1e-6)


class FiniteTimeReachTest(unittest.TestCase):
    """Step 6, finite-time reach of the boundary layer against the closed forms."""

    def test_worked_reach_time(self):
        r = smc.simulate_sliding_control()
        closed_form = (2.0 - smc.WORKED_PHI) / (smc.WORKED_D + smc.WORKED_K)
        cert_bound = (2.0 - smc.WORKED_PHI) / r["eta_cert"]
        self.assertAlmostEqual(r["reach_t"], closed_form, delta=0.005)
        self.assertLess(r["reach_t"], cert_bound)
        self.assertAlmostEqual(r["reach_t"], 0.781, delta=0.005)

    def test_robust_reach_time(self):
        r = smc.simulate_sliding_control(k=smc.ROBUST_K, bound_f=smc.ROBUST_F, disturbance_d=smc.ROBUST_D)
        closed_form = 1.95 / (smc.ROBUST_D + smc.ROBUST_K)
        self.assertAlmostEqual(r["reach_t"], closed_form, delta=0.005)
        self.assertLess(r["reach_t"], 1.300000)


class BoundaryLayerEquilibriumTest(unittest.TestCase):
    """Step 6, the boundary-layer equilibrium and the surface-pinned tracking error."""

    def test_worked_equilibrium(self):
        r = smc.simulate_sliding_control()
        s_ss = smc.WORKED_PHI * smc.WORKED_D / smc.WORKED_K
        e_ss = s_ss / smc.LAMBDA
        self.assertAlmostEqual(r["s"][-1], s_ss, delta=1e-6)
        self.assertAlmostEqual(r["e"][-1], e_ss, delta=1e-4)
        self.assertAlmostEqual(r["x"][-1], 1.0 + e_ss, delta=1e-4)

        idx_2s = round(2.0 / smc.DT)
        max_s_dev = max(abs(r["s"][i] - s_ss) for i in range(idx_2s, r["n"]))
        self.assertLess(max_s_dev, 1e-6)

        idx_4s = round(4.0 / smc.DT)
        max_e_dev = max(abs(r["e"][i] - e_ss) for i in range(idx_4s, r["n"]))
        self.assertLess(max_e_dev, 1e-3)

    def test_error_never_overshoots_after_layer_pin(self):
        r = smc.simulate_sliding_control()
        idx_2s = round(2.0 / smc.DT)
        e_final = r["e"][-1]
        max_e_after = max(r["e"][idx_2s:])
        self.assertAlmostEqual(max_e_after, e_final, delta=1e-3)


class ErrorDynamicsIdentityTest(unittest.TestCase):
    """Step 6, the layer-pinned error approaching e_ss at the surface rate lambda."""

    def test_decay_ratio_matches_exp_lambda(self):
        r = smc.simulate_sliding_control()
        s_ss = smc.WORKED_PHI * smc.WORKED_D / smc.WORKED_K
        e_ss = s_ss / smc.LAMBDA
        e09 = r["e"][round(0.9 / smc.DT)]
        e12 = r["e"][round(1.2 / smc.DT)]
        e15 = r["e"][round(1.5 / smc.DT)]
        ratio1 = (e12 - e_ss) / (e09 - e_ss)
        ratio2 = (e15 - e_ss) / (e12 - e_ss)
        theory = math.exp(-smc.LAMBDA * 0.3)
        self.assertAlmostEqual(ratio1, theory, delta=0.01)
        self.assertAlmostEqual(ratio2, theory, delta=0.01)


class ChatteringSuppressionTest(unittest.TestCase):
    """Step 7, boundary-layer command versus ideal sign switching at the same gains."""

    def test_worked_saturation_suppresses_chattering(self):
        r = smc.simulate_sliding_control()
        self.assertEqual(r["jumps"], 0)
        self.assertLess(r["max_du"], 0.5)
        self.assertEqual(r["sign_changes"], 1)

    def test_sign_case_chatters_at_same_gains(self):
        r_sign = smc.simulate_sliding_control(phi=smc.SIGN_PHI)
        self.assertGreater(r_sign["jumps"], 1000)
        self.assertGreater(r_sign["max_du"], 2.0)
        self.assertGreater(r_sign["sign_changes"], 1000)

    def test_mean_command_worked_vs_sign(self):
        r_worked = smc.simulate_sliding_control()
        r_sign = smc.simulate_sliding_control(phi=smc.SIGN_PHI)
        idx_4s = round(4.0 / smc.DT)

        def mean_abs_u(res):
            window = res["u"][idx_4s:]
            return sum(abs(u) for u in window) / len(window)

        self.assertAlmostEqual(mean_abs_u(r_worked), 0.5, delta=1e-2)
        self.assertAlmostEqual(mean_abs_u(r_sign), 2.0, delta=1e-2)


class SteadyCommandIdentityTest(unittest.TestCase):
    """Step 6, the switched term alone balancing the matched disturbance at equilibrium."""

    def test_worked_steady_command(self):
        r = smc.simulate_sliding_control()
        idx_4s = round(4.0 / smc.DT)
        max_res = max(abs(r["u"][i] + smc.WORKED_D + r["v"][i]) for i in range(idx_4s, r["n"]))
        self.assertLess(max_res, 1e-9)
        self.assertAlmostEqual(r["u"][-1], -smc.WORKED_D - r["v"][-1], delta=1e-9)


class RobustCaseTest(unittest.TestCase):
    """Step 5-6, the larger uncertainty bound at the same certified margin."""

    def test_robust_case_end_state(self):
        r = smc.simulate_sliding_control(k=smc.ROBUST_K, bound_f=smc.ROBUST_F, disturbance_d=smc.ROBUST_D)
        e_ss = smc.WORKED_PHI * smc.ROBUST_D / (smc.ROBUST_K * smc.LAMBDA)
        s_ss = smc.WORKED_PHI * smc.ROBUST_D / smc.ROBUST_K

        self.assertAlmostEqual(r["e"][-1], e_ss, delta=1e-4)
        self.assertAlmostEqual(r["s"][-1], s_ss, delta=1e-6)
        self.assertAlmostEqual(r["u"][-1], -smc.ROBUST_D - r["v"][-1], delta=1e-9)
        self.assertEqual(r["violations"], 0)
        self.assertEqual(r["jumps"], 0)
        self.assertLess(r["max_du"], 0.5)

        idx_4s = round(4.0 / smc.DT)
        max_e_dev = max(abs(r["e"][i] - e_ss) for i in range(idx_4s, r["n"]))
        self.assertLess(max_e_dev, 1e-3)

    def test_robust_certified_margin_matches_worked(self):
        r_worked = smc.simulate_sliding_control()
        r_robust = smc.simulate_sliding_control(k=smc.ROBUST_K, bound_f=smc.ROBUST_F, disturbance_d=smc.ROBUST_D)
        self.assertAlmostEqual(r_worked["eta_cert"], smc.ETA, delta=1e-12)
        self.assertAlmostEqual(r_robust["eta_cert"], smc.ETA, delta=1e-12)


class WorkedSamplePointsTest(unittest.TestCase):
    """Step 1-5, the worked sample-point state history at fixed times."""

    def test_x_sample_points(self):
        r = smc.simulate_sliding_control()
        expected = {
            0.5: 0.229694534,
            1.0: 0.667144001,
            2.0: 0.960448782,
            4.0: 1.005414475,
            6.0: 1.006234758,
        }
        for t, x_expected in expected.items():
            idx = round(t / smc.DT)
            self.assertAlmostEqual(r["x"][idx], x_expected, delta=1e-5)

    def test_s_sample_points(self):
        r = smc.simulate_sliding_control()
        self.assertAlmostEqual(r["s"][round(0.5 / smc.DT)], -0.750000000, delta=1e-6)
        self.assertAlmostEqual(r["s"][round(1.0 / smc.DT)], 0.012492138, delta=1e-5)
        for t in (2.0, 4.0, 6.0):
            self.assertAlmostEqual(r["s"][round(t / smc.DT)], 0.012500000, delta=1e-6)


class ValueErrorTest(unittest.TestCase):
    """Guard-rail rejection of every non-physical input across the module."""

    def test_sliding_surface_rejects_nonpositive_lambda(self):
        with self.assertRaises(ValueError):
            smc.sliding_surface(0.1, 0.0, 0.0)

    def test_sat_value_rejects_negative_phi(self):
        with self.assertRaises(ValueError):
            smc.sat_value(0.1, -0.05)

    def test_equivalent_control_rejects_nonpositive_lambda(self):
        with self.assertRaises(ValueError):
            smc.equivalent_control(0.1, 0.0, 0.1, 0.0)

    def test_switched_term_rejects_negative_phi(self):
        with self.assertRaises(ValueError):
            smc.switched_term(0.1, 2.0, -0.05)

    def test_switched_term_rejects_nonpositive_k(self):
        with self.assertRaises(ValueError):
            smc.switched_term(0.1, 0.0, 0.05)

    def test_simulate_rejects_negative_bound(self):
        with self.assertRaises(ValueError):
            smc.simulate_sliding_control(bound_f=-0.1)

    def test_simulate_rejects_gain_below_bound(self):
        with self.assertRaises(ValueError):
            smc.simulate_sliding_control(k=0.5, bound_f=0.5)

    def test_simulate_rejects_disturbance_above_bound(self):
        with self.assertRaises(ValueError):
            smc.simulate_sliding_control(disturbance_d=0.6)

    def test_simulate_rejects_nonpositive_dt(self):
        with self.assertRaises(ValueError):
            smc.simulate_sliding_control(dt=0.0)

    def test_simulate_rejects_nonpositive_sim_time(self):
        with self.assertRaises(ValueError):
            smc.simulate_sliding_control(sim_time=0.0)


class DeterminismTest(unittest.TestCase):
    """Repeated runs return identical time histories; no randomness anywhere."""

    def test_repeated_run_identical(self):
        r1 = smc.simulate_sliding_control()
        r2 = smc.simulate_sliding_control()
        self.assertEqual(r1["s"], r2["s"])
        self.assertEqual(r1["u"], r2["u"])
        self.assertEqual(r1["reach_idx"], r2["reach_idx"])


if __name__ == "__main__":
    unittest.main()
