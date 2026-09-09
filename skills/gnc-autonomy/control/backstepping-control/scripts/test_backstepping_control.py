#!/usr/bin/env python3
"""Gate 3 contract test: backstepping-control logic.

Exercises scripts/backstepping_control_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the known
plant drift terms, the reference kind and the design gains as given inputs,
step 2 forming the first error variable z1 and choosing the virtual control
alpha1 that stabilizes the z1 subsystem, step 3 propagating the inner-state
mismatch z2 as the second error variable, step 4 differentiating the
virtual control analytically along the plant to get alpha1_dot, step 5
assembling the recursive backstepping control law u from the recursion,
step 6 simulating the closed loop and auditing the z1-map and z2-map
residual identities plus the quadratic-Lyapunov decay rate, and step 7
comparing the error-coordinate history against the equal-gain closed form
and reading the zero-crossing and one-percent settle milestones. Also
reviews determinism across repeated runs and ValueError rejection of every
non-physical input (c1, c2, dt, sim_time, reference kind).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib

bc = importlib.import_module("backstepping_control_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Module constants match the spec's pinned worked-example configuration."""

    def test_constants(self):
        self.assertTrue(math.isclose(bc.C1_WORKED, 2.0))
        self.assertTrue(math.isclose(bc.C2_WORKED, 2.0))
        self.assertTrue(math.isclose(bc.C_RATE, 4.0))
        self.assertTrue(math.isclose(bc.REF_SETPOINT, 1.0))
        self.assertTrue(math.isclose(bc.DT, 0.001))
        self.assertTrue(math.isclose(bc.SIM_TIME, 6.0))
        self.assertTrue(math.isclose(bc.SETTLE_LEVEL, 0.01))
        self.assertEqual(bc.KIND_CONST, "constant")
        self.assertEqual(bc.KIND_EXP, "exponential")


class RecursionAlgebraTest(unittest.TestCase):
    """Step 2-3, the recursion algebra: virtual control, mismatch and V2 closed forms."""

    def test_virtual_control_worked_initial(self):
        alpha1_0 = bc.virtual_control(-1.0, 0.0, 0.0, 2.0)
        self.assertAlmostEqual(alpha1_0, 2.0, delta=1e-12)

    def test_mismatch_error_worked_initial(self):
        z2_0 = bc.mismatch_error(0.0, 2.0)
        self.assertAlmostEqual(z2_0, -2.0, delta=1e-12)

    def test_v2_value_worked_initial(self):
        self.assertAlmostEqual(bc.v2_value(-1.0, -2.0), 2.5, delta=1e-12)

    def test_f1_f2_df1_closed_form(self):
        self.assertAlmostEqual(bc.f1(1.5), 2.25, delta=1e-12)
        self.assertAlmostEqual(bc.df1(1.5), 3.0, delta=1e-12)
        self.assertAlmostEqual(bc.f2(1.5, -0.5), -0.75, delta=1e-12)


class ReferenceTest(unittest.TestCase):
    """Step 1, the reference model for both kinds."""

    def test_constant_reference(self):
        x1d, x1d_dot, x1d_ddot = bc.reference(3.0, bc.KIND_CONST)
        self.assertAlmostEqual(x1d, 1.0, delta=1e-12)
        self.assertAlmostEqual(x1d_dot, 0.0, delta=1e-12)
        self.assertAlmostEqual(x1d_ddot, 0.0, delta=1e-12)

    def test_exponential_reference_at_zero(self):
        x1d, x1d_dot, x1d_ddot = bc.reference(0.0, bc.KIND_EXP)
        self.assertAlmostEqual(x1d, 0.0, delta=1e-12)
        self.assertAlmostEqual(x1d_dot, 1.0, delta=1e-12)
        self.assertAlmostEqual(x1d_ddot, -1.0, delta=1e-12)

    def test_reference_rejects_bad_kind(self):
        with self.assertRaises(ValueError):
            bc.reference(0.5, "ramp")


class Z1MapExactnessTest(unittest.TestCase):
    """Step 6, the z1-map machine-exactness audit for the recursion identity."""

    def test_worked_and_rate_z1_map_near_machine_exact(self):
        r_worked = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r_rate = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        self.assertLess(r_worked["z1_map_max_res"], 1e-9)
        self.assertLess(r_rate["z1_map_max_res"], 1e-9)

    def test_feedforward_z1_map_bounded_by_reference_discretization(self):
        r_ff = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertLess(r_ff["z1_map_max_res"], 1e-5)


class Z2MapConsistencyTest(unittest.TestCase):
    """Step 6, the z2-map analytic-derivative consistency audit."""

    def test_worked_rate_feedforward_z2_map_below_bound(self):
        r_worked = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r_rate = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        r_ff = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertLess(r_worked["z2_map_max_res"], 1e-3)
        self.assertLess(r_rate["z2_map_max_res"], 1e-3)
        self.assertLess(r_ff["z2_map_max_res"], 1e-3)


class LyapunovDecayTest(unittest.TestCase):
    """Step 6, the quadratic-Lyapunov monotone decay and realized decay-rate audit."""

    def test_v2_monotone_non_increasing(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        violations = sum(
            1 for i in range(r["n"] - 1) if r["V2"][i + 1] > r["V2"][i] + bc.TOL
        )
        self.assertEqual(violations, 0)

    def test_realized_decay_rate_within_one_percent(self):
        r_worked = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r_rate = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        r_ff = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertAlmostEqual(r_worked["realized_c"], 2.0, delta=0.02)
        self.assertAlmostEqual(r_rate["realized_c"], 4.0, delta=0.04)
        self.assertAlmostEqual(r_ff["realized_c"], 2.0, delta=0.02)


class EqualGainClosedFormTest(unittest.TestCase):
    """Step 7, the equal-gain closed-form comparison in the error coordinates."""

    def test_worked_z1_z2_v2_closed_form(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        z1_0, z2_0 = r["z1"][0], r["z2"][0]
        near_bounds = {0.5: 1e-3, 1.0: 1e-3, 2.0: 1e-3}
        far_bounds = {4.0: 1e-5, 6.0: 1e-5}
        for t, bound in {**near_bounds, **far_bounds}.items():
            idx = round(t / bc.DT)
            cf_z1 = bc.z1_closed_form(t, z1_0, z2_0, bc.C1_WORKED)
            self.assertLess(abs(r["z1"][idx] - cf_z1), bound)

        for t in (0.5, 1.0, 2.0, 4.0, 6.0):
            idx = round(t / bc.DT)
            cf_z2 = bc.z2_closed_form(t, z1_0, z2_0, bc.C1_WORKED)
            self.assertLess(abs(r["z2"][idx] - cf_z2), 3e-3)

    def test_worked_v2_ratio_vs_closed_form(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        v2_0 = r["V2"][0]
        for t in (0.5, 1.0, 2.0, 4.0):
            idx = round(t / bc.DT)
            ratio = r["V2"][idx] / v2_0
            closed = math.exp(-4.0 * t)
            rel_diff = abs(ratio - closed) / closed
            self.assertLess(rel_diff, 0.05)
        idx6 = round(6.0 / bc.DT)
        ratio6 = r["V2"][idx6] / v2_0
        closed6 = math.exp(-4.0 * 6.0)
        self.assertLess(abs(ratio6 - closed6) / closed6, 0.10)


class RateCaseTest(unittest.TestCase):
    """Step 5-6, the doubled-gain rate case: steeper initial command, faster settle."""

    def test_rate_initial_conditions(self):
        r = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        self.assertAlmostEqual(r["z2"][0], -4.0, delta=1e-9)
        self.assertAlmostEqual(r["V2"][0], 8.5, delta=1e-9)
        self.assertAlmostEqual(r["u"][0], 17.0, delta=1e-9)

    def test_rate_final_sample_near_equilibrium(self):
        r = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        self.assertLess(abs(r["final"]["z1"]), 1e-9)
        self.assertAlmostEqual(r["final"]["x1"], 1.0, delta=1e-6)
        self.assertAlmostEqual(r["final"]["x2"], -1.0, delta=1e-6)
        self.assertAlmostEqual(r["final"]["u"], 1.0, delta=1e-6)

    def test_rate_settle_faster_than_worked(self):
        r_worked = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r_rate = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        self.assertLess(r_rate["settle_1pct_t"], r_worked["settle_1pct_t"])
        self.assertAlmostEqual(r_rate["settle_1pct_t"], 1.499, delta=0.05)


class EquilibriumIdentityTest(unittest.TestCase):
    """Step 6, the virtual-control and steady-command equilibrium identities."""

    def test_worked_equilibrium(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        final = r["final"]
        self.assertAlmostEqual(final["x1"], 1.0, delta=1e-4)
        self.assertAlmostEqual(final["x2"], -1.0, delta=1e-4)
        self.assertAlmostEqual(final["alpha1"], -1.0, delta=1e-4)
        u_ss = -bc.f2(1.0, -1.0)
        self.assertAlmostEqual(final["u"], u_ss, delta=1e-3)
        x1_rate = final["x2"] + bc.f1(final["x1"])
        self.assertLess(abs(x1_rate), 1e-4)


class WorkedSamplePointsTest(unittest.TestCase):
    """Step 2-5, the worked sample-point state history at fixed times."""

    def test_x1_sample_points(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        expected = {
            0.5: 0.324501865,
            1.0: 0.699648781,
            2.0: 0.974567890,
            4.0: 1.000722845,
            6.0: 0.999997441,
        }
        for t, x1_expected in expected.items():
            idx = round(t / bc.DT)
            self.assertAlmostEqual(r["x1"][idx], x1_expected, delta=1e-3)

    def test_u_sample_points(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        expected = {
            0.5: -0.980168142,
            1.0: -1.628162725,
            2.0: 0.479808221,
            4.0: 1.007435226,
            6.0: 1.000062552,
        }
        for t, u_expected in expected.items():
            idx = round(t / bc.DT)
            self.assertAlmostEqual(r["u"][idx], u_expected, delta=1e-2)


class MilestoneTest(unittest.TestCase):
    """Step 7, the first zero crossing and the one-percent tracking settle milestone."""

    def test_worked_first_zero_crossing(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        closed_form = math.pi + math.atan(0.5 / -1.0)
        self.assertAlmostEqual(r["first_zero_t"], closed_form, delta=0.02)

    def test_worked_settle_holds_after_settle_index(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        settle_k = r["settle_1pct_k"]
        self.assertIsNotNone(settle_k)
        self.assertTrue(all(abs(z1) <= bc.SETTLE_LEVEL for z1 in r["z1"][settle_k:]))

    def test_rate_and_feedforward_crossings(self):
        r_rate = bc.simulate(bc.C_RATE, bc.C_RATE, bc.KIND_CONST)
        closed_rate = math.pi + math.atan(0.25 / -1.0)
        self.assertAlmostEqual(r_rate["first_zero_t"], closed_rate, delta=0.02)

        r_ff = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertAlmostEqual(r_ff["first_zero_t"], math.pi, delta=0.05)


class FeedforwardTrackingTest(unittest.TestCase):
    """Step 1-7, the moving-reference feedforward case and its reference-independent rate."""

    def test_feedforward_initial_conditions(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertAlmostEqual(r["z1"][0], 0.0, delta=1e-12)
        self.assertAlmostEqual(r["z2"][0], -1.0, delta=1e-9)
        self.assertAlmostEqual(r["V2"][0], 0.5, delta=1e-9)

    def test_feedforward_max_z1_near_closed_form(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        max_z1 = max(abs(z1) for z1 in r["z1"])
        self.assertAlmostEqual(max_z1, 0.176927688, delta=2e-4)

    def test_feedforward_tracks_moving_reference_at_final_sample(self):
        r = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        self.assertAlmostEqual(r["final"]["x1"], r["x1d"][-1], delta=1e-4)

    def test_feedforward_realized_rate_matches_worked_within_one_percent(self):
        r_worked = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r_ff = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_EXP)
        rel_diff = abs(r_ff["realized_c"] - r_worked["realized_c"]) / r_worked["realized_c"]
        self.assertLess(rel_diff, 0.01)


class ValueErrorTest(unittest.TestCase):
    """Guard-rail rejection of every non-physical input across the module."""

    def test_virtual_control_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            bc.virtual_control(0.1, 0.0, 0.0, 0.0)

    def test_virtual_control_derivative_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            bc.virtual_control_derivative(0.1, 0.0, 0.0, 0.0, 0.0)

    def test_final_control_rejects_nonpositive_c2(self):
        with self.assertRaises(ValueError):
            bc.final_control(0.1, 0.0, 0.1, 0.1, 0.0)

    def test_simulate_rejects_nonpositive_c1(self):
        with self.assertRaises(ValueError):
            bc.simulate(c1=0.0, c2=2.0, kind=bc.KIND_CONST)

    def test_simulate_rejects_nonpositive_c2(self):
        with self.assertRaises(ValueError):
            bc.simulate(c1=2.0, c2=0.0, kind=bc.KIND_CONST)

    def test_simulate_rejects_nonpositive_dt(self):
        with self.assertRaises(ValueError):
            bc.simulate(c1=2.0, c2=2.0, kind=bc.KIND_CONST, dt=0.0)

    def test_simulate_rejects_nonpositive_sim_time(self):
        with self.assertRaises(ValueError):
            bc.simulate(c1=2.0, c2=2.0, kind=bc.KIND_CONST, sim_time=0.0)

    def test_simulate_rejects_bad_reference_kind(self):
        with self.assertRaises(ValueError):
            bc.simulate(c1=2.0, c2=2.0, kind="ramp")


class DeterminismTest(unittest.TestCase):
    """Determinism across repeated runs; no randomness anywhere in the module."""

    def test_repeated_run_identical(self):
        r1 = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        r2 = bc.simulate(bc.C1_WORKED, bc.C2_WORKED, bc.KIND_CONST)
        self.assertEqual(r1["z1"], r2["z1"])
        self.assertEqual(r1["u"], r2["u"])
        self.assertEqual(r1["first_zero_k"], r2["first_zero_k"])


if __name__ == "__main__":
    unittest.main()
