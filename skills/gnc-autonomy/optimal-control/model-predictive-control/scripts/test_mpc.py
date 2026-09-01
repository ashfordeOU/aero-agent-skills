#!/usr/bin/env python3
"""Gate 3 contract test: model predictive control for linear discrete
time systems.

Exercises scripts/mpc_logic.py (stdlib unittest, offline, deterministic).
Contract: docs/harness-contract.md gate 3 - the condensed finite-horizon
QP for x[k+1] = A x[k] + B u[k] with quadratic cost over prediction
horizon N, input bounds and state bounds, solved without scipy (KKT
system solved exactly for equality-constrained cases, deterministic
active-set for inequalities), the receding-horizon closed-loop
simulation phase of the design workflow, and ValueError on invalid
dimensions.

Reference configuration (analytic receding-horizon solution):
double integrator A = [[1,1],[0,1]], B = [[0.5],[1]], Q = eye(2), R = 1,
N = 10.  With Pf = 0 the first move for x0 = [1, 0] from the
finite-horizon LQR Riccati recursion is

  u0 = -0.4344828571172731

(computed by the independent dynamic-programming recursion in
terminal_cost_solution, cross-checked against the condensed QP to
1e-15).  The closed loop from x0 = [1, 0] drives the state to the
origin; with input bounds +-0.5 the same holds with |u| <= 0.5.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mpc_logic as mpc  # noqa: E402

# Contract configuration: double integrator, Q = I, R = 1, N = 10.
A_DI = [[1.0, 1.0], [0.0, 1.0]]
B_DI = [[0.5], [1.0]]
Q_I = [[1.0, 0.0], [0.0, 1.0]]
R_1 = 1.0
N_10 = 10
X0 = [1.0, 0.0]

# Analytic first move (finite-horizon Riccati recursion, Pf = 0).
U0_ANALYTIC = -0.4344828571172731


def norm(v):
    return math.sqrt(sum(x * x for x in v))


class FirstMoveTest(unittest.TestCase):
    def test_first_move_matches_analytic_recursion(self):
        # Independent derivation path: dynamic-programming Riccati
        # recursion (terminal_cost_solution) vs the condensed QP.
        K0, _P0 = mpc.terminal_cost_solution(A_DI, B_DI, Q_I, R_1, N_10, X0)
        self.assertIsNotNone(K0)
        u0_dp = -K0[0][0] * X0[0] - K0[0][1] * X0[1]
        u0 = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                                umin=[-10.0], umax=[10.0], x0=X0)
        self.assertAlmostEqual(u0[0], u0_dp, delta=1e-6)
        self.assertAlmostEqual(u0[0], U0_ANALYTIC, delta=1e-6)

    def test_first_move_matches_literal_no_bounds(self):
        u0 = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=X0)
        self.assertAlmostEqual(u0[0], U0_ANALYTIC, delta=1e-6)
        self.assertEqual(len(u0), 1)

    def test_first_move_loose_bounds_equals_unconstrained(self):
        # Wide bounds must not change the unconstrained optimum.
        u0_free = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=X0)
        u0_loose = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                                      umin=[-100.0], umax=[100.0], x0=X0)
        self.assertAlmostEqual(u0_free[0], u0_loose[0], delta=1e-9)

    def test_deterministic_repeat(self):
        a = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                               umin=[-0.5], umax=[0.5], x0=X0)
        b = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                               umin=[-0.5], umax=[0.5], x0=X0)
        self.assertEqual(a, b)


class ClosedLoopTest(unittest.TestCase):
    def test_closed_loop_drives_state_to_origin(self):
        system = mpc.DiscreteSystem(A_DI, B_DI)
        controller = lambda x: mpc.mpc_controller(  # noqa: E731
            A_DI, B_DI, Q_I, R_1, N_10, umin=[-10.0], umax=[10.0], x0=x)
        traj = mpc.simulate_closed_loop(system, controller, X0, 40)
        self.assertEqual(len(traj), 41)
        self.assertLess(norm(traj[-1]), 1e-6)
        # Monotone energy decay on the first steps: the receding plan
        # must strictly improve the state norm early on.
        self.assertLess(norm(traj[5]), norm(X0))

    def test_closed_loop_bounded_input_converges(self):
        system = mpc.DiscreteSystem(A_DI, B_DI)
        controller = lambda x: mpc.mpc_controller(  # noqa: E731
            A_DI, B_DI, Q_I, R_1, N_10, umin=[-0.5], umax=[0.5], x0=x)
        traj = mpc.simulate_closed_loop(system, controller, X0, 80)
        self.assertLess(norm(traj[-1]), 1e-6)
        # Every applied input respects the bounds.
        x = list(X0)
        for k in range(80):
            u = controller(x)
            self.assertGreaterEqual(u[0], -0.5 - 1e-9)
            self.assertLessEqual(u[0], 0.5 + 1e-9)
            x = system.step(x, u)

    def test_two_input_system(self):
        # 2-input sanity: per-component bounds and convergence.
        B2 = [[0.5, 0.1], [1.0, 0.2]]
        R2 = [[1.0, 0.0], [0.0, 2.0]]
        system = mpc.DiscreteSystem(A_DI, B2)
        controller = lambda x: mpc.mpc_controller(  # noqa: E731
            A_DI, B2, Q_I, R2, N_10, umin=[-1.0, -2.0], umax=[1.0, 2.0], x0=x)
        traj = mpc.simulate_closed_loop(system, controller, X0, 40)
        self.assertLess(norm(traj[-1]), 1e-6)
        u0 = controller(X0)
        self.assertEqual(len(u0), 2)


class ConstraintHandlingTest(unittest.TestCase):
    def test_input_saturation_at_bound(self):
        # Large state, tight bounds: the first move sits on the bound.
        u0 = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                                umin=[-0.5], umax=[0.5], x0=[5.0, 2.0])
        self.assertAlmostEqual(u0[0], -0.5, delta=1e-9)

    def test_kkt_stationarity_bounded(self):
        # KKT residual of the box-constrained solution must vanish.
        data = mpc.build_qp(A_DI, B_DI, Q_I, R_1, N_10, X0,
                            umin=[-0.5], umax=[0.5])
        U, _qpinfo = mpc.solve_qp(data["H"], data["f"], data["rows"],
                                  data["bs"], box_idx=data["box_idx"])
        res = mpc.kkt_residual(data["H"], data["f"], data["rows"],
                               data["bs"], U, [])
        self.assertLess(res, 1e-6)
        # Bounds are inactive at x0 = [1, 0] with +-0.5: the solution
        # equals the unconstrained one, and the inequality path reports
        # the active-set method through mpc_solve.
        u_free = mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=X0)
        self.assertAlmostEqual(U[0], u_free[0], delta=1e-6)
        _us, _xs, info = mpc.mpc_solve(A_DI, B_DI, Q_I, R_1, N_10,
                                       umin=[-0.5], umax=[0.5], x0=X0)
        self.assertEqual(info["method"], "active-set")

    def test_state_constraints_respected(self):
        # x1 component capped at 0.5 over the prediction; x_0 is the
        # current state and is not constrained.
        u_seq, x_seq, info = mpc.mpc_solve(
            A_DI, B_DI, Q_I, R_1, N_10, umin=[-10.0], umax=[10.0], x0=X0,
            xmin=[-10.0, -10.0], xmax=[0.5, 10.0])
        for x in x_seq[1:]:
            self.assertLessEqual(x[0], 0.5 + 1e-9)
        # The constraint is active: u0 = -1 drives x_1 to exactly 0.5.
        self.assertAlmostEqual(u_seq[0][0], -1.0, delta=1e-9)
        self.assertAlmostEqual(x_seq[1][0], 0.5, delta=1e-9)
        # Active-set multiplier for the active state row is nonnegative.
        self.assertGreaterEqual(min(info["multipliers"]), -1e-9)

    def test_terminal_equality_kkt_path(self):
        # Terminal equality x_N = 0 solved through the KKT system.
        u_seq, x_seq, info = mpc.mpc_solve(
            A_DI, B_DI, Q_I, R_1, 4, umin=[-10.0], umax=[10.0], x0=X0,
            terminal_eq=True)
        self.assertEqual(info["method"], "kkt")
        self.assertLess(norm(x_seq[-1]), 1e-8)

    def test_control_horizon_holds_tail(self):
        # Nc = 3: inputs u_3 .. u_9 are held at u_2.
        u_seq, x_seq, info = mpc.mpc_solve(
            A_DI, B_DI, Q_I, R_1, N_10, umin=[-10.0], umax=[10.0], x0=X0,
            Nc=3)
        for k in range(3, 10):
            self.assertAlmostEqual(u_seq[k][0], u_seq[2][0], delta=1e-9)
        self.assertLess(norm(x_seq[-1]), 1.0)  # sane open-loop plan


class ValidationTest(unittest.TestCase):
    def test_bad_dimensions_raise_value_error(self):
        # Non-square A.
        with self.assertRaises(ValueError):
            mpc.mpc_controller([[1.0, 1.0], [0.0, 1.0], [0.0, 0.0]],
                               B_DI, Q_I, R_1, N_10, x0=X0)
        # B rows do not match A.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, [[0.5], [1.0], [0.5]],
                               Q_I, R_1, N_10, x0=X0)
        # Q wrong shape.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
                               R_1, N_10, x0=X0)
        # R wrong shape (2x2 with a single input).
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I,
                               [[1.0, 0.0], [0.0, 1.0]], N_10, x0=X0)
        # x0 wrong length.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=[1.0, 2.0, 3.0])
        # umin/umax wrong length.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                               umin=[-0.5, -0.5], umax=[0.5], x0=X0)

    def test_invalid_weights_and_horizons_raise(self):
        # R <= 0.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, 0.0, N_10, x0=X0)
        # Q indefinite.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, [[1.0, 0.0], [0.0, -1.0]],
                               R_1, N_10, x0=X0)
        # N < 1.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, 0, x0=X0)
        # Nc > N.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=X0, Nc=11)
        # Empty input feasible set.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                               umin=[0.5], umax=[-0.5], x0=X0)
        # Empty state feasible set.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10, x0=X0,
                               xmin=[1.0, 0.0], xmax=[0.0, 1.0])
        # Non-numeric entries.
        with self.assertRaises(ValueError):
            mpc.mpc_controller(A_DI, B_DI, Q_I, R_1, N_10,
                               umin=["a"], x0=X0)

    def test_feasibility_check(self):
        self.assertTrue(mpc.feasible(A_DI, B_DI, Q_I, R_1, N_10,
                                     umin=[-0.5], umax=[0.5], x0=X0))
        self.assertFalse(mpc.feasible(A_DI, B_DI, Q_I, R_1, N_10,
                                      umin=[1.0], umax=[-1.0], x0=X0))
        self.assertFalse(mpc.feasible([[1.0, 1.0]], B_DI, Q_I, R_1, N_10))

    def test_discrete_system_step(self):
        system = mpc.DiscreteSystem(A_DI, B_DI)
        # x[k+1] = A x + B u: with u = 0 the velocity integrates.
        self.assertEqual(system.step([1.0, 0.0], [0.0]), [1.0, 0.0])
        # With u = 1: x1 += 0.5, velocity += 1.
        x_next = system.step([1.0, 0.0], [1.0])
        self.assertAlmostEqual(x_next[0], 1.5, delta=1e-12)
        self.assertAlmostEqual(x_next[1], 1.0, delta=1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
