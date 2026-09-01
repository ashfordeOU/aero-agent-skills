---
name: model-predictive-control
description: "Use when you must design a model predictive control (MPC) receding horizon controller for a linear discrete time system such as a double integrator: choose the finite horizon quadratic cost with prediction horizon and control horizon, enforce input constraints and state constraints, and run a closed loop simulation. Produces the first optimal control move from the small dense quadratic program, solved deterministically without scipy, plus the feasibility verdict. Trigger: mpc, model predictive control, receding horizon, quadratic cost, prediction horizon, control horizon, input constraints, state constraints, terminal cost, double integrator, constrained control, closed loop simulation, kkt system, active set."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: none
    reference-only: true
gated: false
domain: gnc-autonomy
pack: optimal-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [model-predictive-control, mpc, receding-horizon, quadratic-cost, constraint-handling, double-integrator]
  version: 0.1.0
  author: AeroSkills
---

# Model Predictive Control (gnc-autonomy/optimal-control/model-predictive-control)

Use when the task is MPC design for a linear discrete-time system:
formulating the finite-horizon quadratic cost, enforcing input and
state constraints, computing the first optimal control move from the
current state, and simulating the receding-horizon closed loop. The
module solves the small dense QP deterministically in pure Python
(no numpy, no scipy): the equality-constrained case through the exact
KKT system, the inequality case through a primal active-set method.

## Domain quick reference

- Plant: x[k+1] = A x[k] + B u[k], x in R^n, u in R^m. A and B must
  share one SI unit convention (seconds per step, radians, N or N m
  inputs) so that the cost below is dimensionless.
- Finite-horizon quadratic cost over prediction horizon N with control
  horizon Nc <= N and terminal cost Pf:
  J = x_N' Pf x_N + sum_{k=0}^{N-1} (x_k' Q x_k + u_k' R u_k),
  with u_k held at u_{Nc-1} for k >= Nc when Nc < N. Q is positive
  semidefinite, R positive definite, Pf positive semidefinite.
- Condensed form: stack U = [u_0; ...; u_{Nc-1}] and write the
  predicted trajectory X = [x_1; ...; x_N] = S x0 + T U, with S the
  stacked powers of A and T the block Toeplitz reachability matrix.
  The cost becomes 0.5 U' H U + f' U with H = T' Qbar T + Rbar
  (Qbar = blockdiag(Q, ..., Q, Pf), Rbar = blockdiag(R, ..., (N-Nc+1)
  R) because the held input is charged N - Nc + 1 times) and
  f = T' Qbar S x0.
- Constraints: input box umin <= u_k <= umax per component, state box
  xmin <= x_k <= xmax per component, optional terminal equality x_N = 0.
  All map to affine inequalities on U (state bounds through T_k U +
  S_k x0 in [xmin, xmax]).
- Equality-constrained case (terminal equality, or unconstrained):
  solve the KKT system [H Aeq'; Aeq 0][U; lam] = [-f; beq] exactly by
  dense Gaussian elimination with partial pivoting (solve_kkt).
- Inequality case: primal active-set method on the same KKT system,
  warm-started from the unconstrained minimizer clipped to the input
  box. Each iteration adds the most violated inactive constraint or
  drops the active constraint with the most negative multiplier.
  Deterministic, bounded iteration count (max 400).
- Receding horizon: solve the N-step problem from the current state,
  apply only u0, step the plant, repeat. This is the standard MPC
  feedback law; the closed loop inherits stability properties from the
  stage cost and horizon when the terminal cost is chosen well.
- Unconstrained MPC equals finite-horizon LQR: u_k = -K_k x_k with K_k
  from the Riccati recursion P_{k+1} -> P_k (terminal_cost_solution),
  which is the independent analytic cross-check for this leaf.
- Feasibility: dimensions, symmetry, definiteness (principal minors),
  horizon bounds, and empty feasible sets (umin > umax, xmin > xmax)
  are checked up front; violations raise ValueError.

## Workflow

1. Write the plant as a discrete-time LTI pair (A, B) and confirm
   controllability for the working state/input dimensions (2-3 states,
   1-2 inputs for this leaf).
2. Choose Q (state penalty, PSD), R (input penalty, PD), terminal cost
   Pf (zero for plain finite-horizon, or the LQR Riccati solution for
   stability), prediction horizon N >= 1, and control horizon Nc <= N
   (Nc = N is the default; shrinking Nc reduces the QP size at the cost
   of optimality).
3. State the input bounds umin/umax and state bounds xmin/xmax in the
   same unit convention; None means unconstrained on that side.
4. From the current state x0, compute the first move with
   mpc_controller(A, B, Q, R, N, umin=..., umax=..., x0=x0); inspect
   the full plan with mpc_solve (returns u_seq, x_seq, info with the
   solver method, active set, and multipliers).
5. Simulate the receding-horizon closed loop with
   simulate_closed_loop(DiscreteSystem(A, B), controller, x0, steps)
   and verify the state reaches the origin region and every applied
   input respects the bounds.
6. Check feasibility with feasible(...) before trusting a solve; treat
   ValueError as the deterministic infeasibility signal.

## Worked example

Double integrator A = [[1,1],[0,1]], B = [[0.5],[1]], Q = I2, R = 1,
N = 10, x0 = [1, 0], unconstrained (or wide bounds):

- mpc_controller returns u0 = -0.4344828571172731, which matches the
  finite-horizon LQR Riccati recursion to 1e-15 (see scripts/test_mpc.py).
- simulate_closed_loop for 40 steps drives the state to norm below
  1e-14; the first five steps already cut the state norm below ||x0||.
- With umin = -0.5, umax = 0.5 the same closed loop converges (norm
  below 1e-28 after 80 steps) with every input inside the box; from
  x0 = [5, 2] the first move saturates at u0 = -0.5 exactly.
- With xmax = [0.5, 10] the predicted x_1 is pinned to 0.5 (u0 = -1)
  and the active-set multiplier for that row is nonnegative.
- With terminal_eq = True the KKT path drives x_N to zero to 1e-16.

Run the contract test from the skill directory:
python3 scripts/test_mpc.py

## Pitfalls

- Solving the QP with a generic iterative method that depends on
  initial guesses or random tie-breaks; this leaf's active-set and KKT
  paths are fully deterministic (fixed pivoting, fixed iteration cap).
- Forgetting that the held input u_{Nc-1} is charged N - Nc + 1 times;
  Rbar's last block carries that factor, otherwise the control horizon
  cost is wrong.
- Checking PSD only on leading principal minors; Q = [[0,0],[0,-1]]
  passes that test but is indefinite. This leaf checks all principal
  minors (n small), so invalid Q raises ValueError.
- Treating x0 as a constrained variable: state bounds apply to the
  predicted x_1 .. x_N, not to the measured current state.
- Mixing units across A, B, Q, R and the bounds; the cost and the
  optimal trajectory change with the convention.
- Expecting the open-loop plan to hold; MPC re-solves at every step,
  only u0 is applied. Use simulate_closed_loop for trajectory claims.

## Behavior contract (gate 3)

The condensed QP, KKT equality path, active-set inequality path,
receding-horizon closed loop, and validation are exercised by the
contract test scripts/test_mpc.py against scripts/mpc_logic.py
(stdlib unittest, offline, deterministic, ~0.2 s). It asserts the
analytic first move for the double integrator configuration, origin
convergence with and without input bounds, input saturation, state
constraint satisfaction, terminal equality, control horizon holding,
and ValueError on invalid dimensions and impossible weights.

## Compliance

- No external standard applies; the mathematics is common
  control-theory knowledge (finite-horizon LQR, quadratic programming,
  KKT conditions). standards: none, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

## Related skills

- gnc-autonomy/optimal-control/lqr-design: infinite-horizon state
  feedback from the Riccati equation; its gain is the natural terminal
  cost Pf for a stabilizing MPC formulation.
- gnc-autonomy/optimal-control/dymos-trajectory: trajectory
  optimization over a full mission; MPC is the feedback counterpart
  for the same cost structure.
- gnc-autonomy/control/pid-control-design and
  gnc-autonomy/control/python-control-design: simpler feedback laws
  when constraints are loose and the horizon-1 computation is enough.
