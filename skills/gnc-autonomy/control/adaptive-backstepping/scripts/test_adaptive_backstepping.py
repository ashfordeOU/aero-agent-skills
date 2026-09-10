#!/usr/bin/env python3
"""Gate 3 contract test: adaptive-backstepping logic.

Exercises scripts/adaptive_backstepping_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the plant,
reference kind and design gains, step 2 forming z1 and the theta_hat-carrying
virtual control alpha1, step 3 propagating the mismatch z2, step 4 the
design-model derivative alpha1_dot evaluated with theta_hat as the plant
coefficient, step 5 the tuning functions tau1 and tau2 that drive the single
parameter estimate theta_hat, step 6 assembling the final control u and
simulating the closed loop, and step 7 auditing the map residuals and the
augmented Lyapunov function V2 with the parameter-error term. Also covers
the rate case, the zero-adaptation-gain reduction to the backstepping-control
exact model, the persistent-excitation case, determinism and ValueError
rejection of every non-physical input.
"""

import importlib
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ab = importlib.import_module("adaptive_backstepping_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Module constants match the spec's pinned worked-example configuration."""

    def test_constants(self):
        self.assertTrue(math.isclose(ab.THETA_TRUE, 1.0))
        self.assertTrue(math.isclose(ab.C1_WORKED, 2.0))
        self.assertTrue(math.isclose(ab.C2_WORKED, 2.0))
        self.assertTrue(math.isclose(ab.C_RATE, 4.0))
        self.assertTrue(math.isclose(ab.GAMMA_WORKED, 5.0))
        self.assertTrue(math.isclose(ab.GAMMA_RATE, 10.0))
        self.assertTrue(math.isclose(ab.GAMMA_ZERO, 0.0))
        self.assertTrue(math.isclose(ab.GAMMA_PE, 20.0))
        self.assertTrue(math.isclose(ab.DT, 0.001))
        self.assertTrue(math.isclose(ab.SIM_TIME, 10.0))
        self.assertTrue(math.isclose(ab.RATE_TIME, 6.0))
        self.assertTrue(math.isclose(ab.PE_TIME, 40.0))
        self.assertEqual(ab.KIND_CONST, "constant")
        self.assertEqual(ab.KIND_SIN, "sinusoidal")


class RecursionAlgebraTest(unittest.TestCase):
    """Step 2-5, the recursion algebra closed forms at the worked initial point."""

    def test_alpha1_value_worked_initial(self):
        alpha1_0 = ab.alpha1_value(-1.0, 0.0, 0.0, 0.0, 2.0)
        self.assertAlmostEqual(alpha1_0, 2.0, delta=1e-12)

    def test_mismatch_error_worked_initial(self):
        z2_0 = ab.mismatch_error(0.0, 2.0)
        self.assertAlmostEqual(z2_0, -2.0, delta=1e-12)

    def test_v2_value_worked_initial(self):
        v2_0 = ab.v2_value(-1.0, -2.0, 1.0, 5.0)
        self.assertAlmostEqual(v2_0, 2.6, delta=1e-12)

    def test_tau2_value_zero_at_origin(self):
        tau2_0 = ab.tau2_value(-1.0, -2.0, 0.0, 0.0, 5.0)
        self.assertAlmostEqual(tau2_0, 0.0, delta=1e-12)

    def test_omega2_regressor_closed_form(self):
        w2 = ab.omega2_regressor(1.0, 1.0, 2.0)
        self.assertAlmostEqual(w2, 4.0, delta=1e-12)

    def test_f1_df1_f2_closed_form(self):
        self.assertAlmostEqual(ab.f1(1.5), 2.25, delta=1e-12)
        self.assertAlmostEqual(ab.df1(1.5), 3.0, delta=1e-12)
        self.assertAlmostEqual(ab.f2(1.5, -0.5), -0.75, delta=1e-12)

    def test_w1_regressor_is_f1(self):
        self.assertAlmostEqual(ab.w1_regressor(2.0), ab.f1(2.0), delta=1e-12)


class ReferenceTest(unittest.TestCase):
    """Step 1, the reference model for both kinds."""

    def test_constant_reference(self):
        x1d, x1d_dot, x1d_ddot = ab.reference(3.0, ab.KIND_CONST)
        self.assertAlmostEqual(x1d, 1.0, delta=1e-12)
        self.assertAlmostEqual(x1d_dot, 0.0, delta=1e-12)
        self.assertAlmostEqual(x1d_ddot, 0.0, delta=1e-12)

    def test_sinusoidal_reference_at_zero(self):
        x1d, x1d_dot, x1d_ddot = ab.reference(0.0, ab.KIND_SIN)
        self.assertAlmostEqual(x1d, 0.0, delta=1e-12)
        self.assertAlmostEqual(x1d_dot, 1.0, delta=1e-12)
        self.assertAlmostEqual(x1d_ddot, 0.0, delta=1e-12)

    def test_reference_rejects_bad_kind(self):
        with self.assertRaises(ValueError):
            ab.reference(0.5, "ramp")


class WorkedCaseAInitialTest(unittest.TestCase):
    """Step 2-6, worked case A initial conditions (c1=c2=2.0, gamma=5.0)."""

    def test_initial_conditions(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        s0 = ab.sample(r, 0.0)
        self.assertAlmostEqual(s0["z1"], -1.0, delta=1e-9)
        self.assertAlmostEqual(s0["z2"], -2.0, delta=1e-9)
        self.assertAlmostEqual(s0["alpha1"], 2.0, delta=1e-9)
        self.assertAlmostEqual(s0["u"], 5.0, delta=1e-9)
        self.assertAlmostEqual(ab.THETA_TRUE - s0["th"], 1.0, delta=1e-9)
        self.assertAlmostEqual(s0["v2"], 2.6, delta=1e-9)


class WorkedCaseAConvergenceTest(unittest.TestCase):
    """Step 5-7, worked case A parameter and tracking convergence at T=10 s."""

    def setUp(self):
        self.r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        self.sT = ab.sample(self.r, 10.0)

    def test_theta_hat_converges(self):
        self.assertAlmostEqual(self.sT["th"], 1.0000982189, delta=1e-3)
        self.assertLess(abs(ab.THETA_TRUE - self.sT["th"]), 1e-3)

    def test_state_converges(self):
        self.assertAlmostEqual(self.sT["x1"], 1.0, delta=1e-3)
        self.assertAlmostEqual(self.sT["x2"], -1.0, delta=1e-3)

    def test_error_variables_converge(self):
        self.assertLess(abs(self.sT["z1"]), 1e-3)
        self.assertLess(abs(self.sT["z2"]), 1e-3)

    def test_equilibrium_rate_identity(self):
        achieved_rate = self.sT["x2"] + ab.f1(self.sT["x1"])
        self.assertLess(abs(achieved_rate), 1e-2)


class WorkedCaseASamplesTest(unittest.TestCase):
    """Step 2-6, worked case A sample-point state and parameter-estimate history."""

    def test_x1_sample_points(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        expected = {
            0.5: 0.3390297388,
            1.0: 0.9731049081,
            2.0: 1.0363587713,
            4.0: 0.9961053848,
            6.0: 0.9988545516,
        }
        for t, x1_expected in expected.items():
            s = ab.sample(r, t)
            self.assertAlmostEqual(s["x1"], x1_expected, delta=1e-4)

    def test_theta_hat_sample_points(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        s2 = ab.sample(r, 2.0)
        s6 = ab.sample(r, 6.0)
        self.assertAlmostEqual(s2["th"], 0.9031981710, delta=1e-4)
        self.assertAlmostEqual(s6["th"], 0.9967713046, delta=1e-4)


class WorkedCaseAAuditTest(unittest.TestCase):
    """Step 7, worked case A map-residual and augmented-Lyapunov audit."""

    def test_v2_monotone_non_increasing(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        self.assertEqual(r["v2_mono_viol"], 0)

    def test_map_residuals_within_euler_band(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        self.assertLess(r["z1_map_max"], 1e-2)
        self.assertLess(r["z2_map_max"], 0.1)


class RateCaseTest(unittest.TestCase):
    """Step 5-7, rate case B: doubled gains and adaptation rate settle tighter."""

    def test_initial_conditions(self):
        r = ab.simulate(ab.C_RATE, ab.C_RATE, ab.GAMMA_RATE, ab.KIND_CONST, sim_time=ab.RATE_TIME)
        s0 = ab.sample(r, 0.0)
        self.assertAlmostEqual(s0["z2"], -4.0, delta=1e-6)
        self.assertAlmostEqual(s0["u"], 17.0, delta=1e-6)
        self.assertAlmostEqual(s0["v2"], 8.55, delta=1e-6)

    def test_final_sample_tighter_than_worked(self):
        r = ab.simulate(ab.C_RATE, ab.C_RATE, ab.GAMMA_RATE, ab.KIND_CONST, sim_time=ab.RATE_TIME)
        sT = ab.sample(r, ab.RATE_TIME)
        self.assertAlmostEqual(sT["th"], 1.0000484342, delta=1e-3)
        self.assertAlmostEqual(sT["x1"], 1.0, delta=1e-5)
        self.assertLess(abs(sT["z1"]), 1e-4)
        self.assertLess(abs(sT["z2"]), 1e-4)
        self.assertLess(abs(sT["u"] - 1.0), 1e-2)

    def test_rate_settle_tighter_than_worked_at_shared_horizon(self):
        r_worked = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST,
                               sim_time=ab.RATE_TIME)
        r_rate = ab.simulate(ab.C_RATE, ab.C_RATE, ab.GAMMA_RATE, ab.KIND_CONST,
                             sim_time=ab.RATE_TIME)
        sw = ab.sample(r_worked, ab.RATE_TIME)
        sr = ab.sample(r_rate, ab.RATE_TIME)
        self.assertLess(abs(sr["z1"]), abs(sw["z1"]))
        self.assertLess(abs(sr["z2"]), abs(sw["z2"]))


class ReductionCaseTest(unittest.TestCase):
    """Step 5, reduction case C (gamma=0, theta_hat(0)=theta): the exact-model limit."""

    def setUp(self):
        self.r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_ZERO, ab.KIND_CONST,
                             th_0=ab.INIT_TH_KNOWN, sim_time=ab.RATE_TIME)

    def test_theta_hat_frozen(self):
        max_dev = max(abs(v - ab.INIT_TH_KNOWN) for v in self.r["th"])
        self.assertEqual(max_dev, 0.0)

    def test_z1_map_machine_exact(self):
        self.assertLess(self.r["z1_map_max"], 1e-9)

    def test_final_matches_sibling_worked_case(self):
        sT = ab.sample(self.r, ab.RATE_TIME)
        self.assertAlmostEqual(sT["x1"], 0.999997441, delta=1e-4)
        self.assertAlmostEqual(sT["u"], 1.000062552, delta=1e-4)

    def test_sample_cross_check_against_sibling(self):
        sibling = {0.5: 0.324501865, 1.0: 0.699648781, 2.0: 0.974567890, 4.0: 1.000722845}
        for t, target in sibling.items():
            s = ab.sample(self.r, t)
            self.assertLess(abs(s["x1"] - target), 1e-4)


class PersistentExcitationCaseTest(unittest.TestCase):
    """Step 5-7, PE case D: the moving reference drives theta_hat to theta."""

    def setUp(self):
        self.r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_PE, ab.KIND_SIN,
                             sim_time=ab.PE_TIME)

    def test_theta_hat_converges_under_pe(self):
        sT = ab.sample(self.r, ab.PE_TIME)
        self.assertAlmostEqual(sT["th"], 0.9996543840, delta=2e-2)
        self.assertLess(abs(ab.THETA_TRUE - sT["th"]), 2e-2)

    def test_bounded_tracking_against_moving_reference(self):
        max_z1 = max(abs(v) for v in self.r["z1"])
        self.assertAlmostEqual(max_z1, 0.2049438438, delta=1e-3)
        sT = ab.sample(self.r, ab.PE_TIME)
        self.assertLess(abs(sT["z1"]), 1e-3)

    def test_v2_monotone_non_increasing_under_pe(self):
        self.assertEqual(self.r["v2_mono_viol"], 0)


class ParameterTransientTest(unittest.TestCase):
    """Step 5, the non-PE drift transient: theta_hat leaves and returns, V2 still decays."""

    def test_transient_dip_and_recovery(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        s1 = ab.sample(r, 1.0)
        sT = ab.sample(r, 10.0)
        self.assertAlmostEqual(s1["th"], -0.4386805331, delta=1e-3)
        self.assertAlmostEqual(sT["th"], 1.0000982189, delta=1e-3)
        self.assertGreater(abs(sT["th"] - s1["th"]), 1.0)

    def test_v2_stays_monotone_through_transient(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        self.assertEqual(r["v2_mono_viol"], 0)


class ValueErrorTest(unittest.TestCase):
    """Guard-rail rejection of every non-physical input across the module."""

    def test_alpha1_value_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            ab.alpha1_value(0.1, 0.0, 0.0, 0.1, 0.0)

    def test_alpha1_dot_adaptive_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            ab.alpha1_dot_adaptive(0.1, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0)

    def test_final_control_rejects_nonpositive_c2(self):
        with self.assertRaises(ValueError):
            ab.final_control(0.1, 0.0, 0.1, 0.1, 0.0)

    def test_v2_value_rejects_nonpositive_gamma(self):
        with self.assertRaises(ValueError):
            ab.v2_value(-1.0, -2.0, 1.0, 0.0)

    def test_simulate_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            ab.simulate(0.0, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)

    def test_simulate_rejects_nonpositive_c2(self):
        with self.assertRaises(ValueError):
            ab.simulate(ab.C1_WORKED, 0.0, ab.GAMMA_WORKED, ab.KIND_CONST)

    def test_simulate_rejects_negative_gamma(self):
        with self.assertRaises(ValueError):
            ab.simulate(ab.C1_WORKED, ab.C2_WORKED, -1.0, ab.KIND_CONST)

    def test_simulate_rejects_nonpositive_dt(self):
        with self.assertRaises(ValueError):
            ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST, dt=0.0)

    def test_simulate_rejects_nonpositive_sim_time(self):
        with self.assertRaises(ValueError):
            ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST, sim_time=0.0)

    def test_simulate_rejects_bad_reference_kind(self):
        with self.assertRaises(ValueError):
            ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, "ramp")

    def test_simulate_accepts_zero_gamma(self):
        r = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, 0.0, ab.KIND_CONST, sim_time=1.0)
        self.assertEqual(r["n"], 1001)


class DeterminismTest(unittest.TestCase):
    """Determinism across repeated runs; no randomness anywhere in the module."""

    def test_repeated_run_identical(self):
        r1 = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        r2 = ab.simulate(ab.C1_WORKED, ab.C2_WORKED, ab.GAMMA_WORKED, ab.KIND_CONST)
        self.assertEqual(r1["z1"], r2["z1"])
        self.assertEqual(r1["u"], r2["u"])
        self.assertEqual(r1["th"], r2["th"])


if __name__ == "__main__":
    unittest.main()
