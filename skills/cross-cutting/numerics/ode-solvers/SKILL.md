---
name: ode-solvers
description: "Solve first-order ordinary differential equations numerically with explicit Euler, Heun's method (RK2), and classical RK4: step the initial-value problem forward from y(t0), tabulate the solution, compare it against a closed-form reference, and check step-size convergence of the global error. Use when a task asks for an ODE solver, differential-equation time marching, an initial-value problem, a decay or response trajectory, or an error-versus-exact comparison. Produces the solution table, the chosen method, and the max absolute error. Trigger: ode solver, initial value problem, explicit euler, runge kutta, heun method, step size convergence."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [ode-solvers, explicit-euler, runge-kutta, heun-method, initial-value-problem, step-size-convergence, closed-form-solution, differential-equation]
  version: 0.1.0
  author: AeroSkills
---

# ODE Solvers (cross-cutting/numerics/ode-solvers)

Use when the task is solving a first-order ordinary differential
equation numerically: stepping the initial-value problem
dy/dt = f(t, y), y(t0) = y0 forward with explicit Euler, Heun's
method (RK2), or classical RK4, tabulating the solution, and
comparing it against a closed-form exact solution with a
step-size convergence check.

## Domain quick reference

All worked numbers are for dy/dt = -y, y(0) = 1, whose closed-form
solution is y(t) = e**(-t); at t = 0.5 the exact value is 0.60653066.

- Explicit Euler: y_{k+1} = y_k + h * f(t_k, y_k). Global error is
  O(h). With h = 0.1 and 5 steps, y(0.5) = (0.9)**5 = 0.59049
  (error 1.60e-2). Halving h to 0.05 cuts the max error to 7.79e-3,
  a ratio of 2.06: order 1.
- Heun's method (RK2): predictor y_p = y_k + h * f(t_k, y_k),
  corrector y_{k+1} = y_k + (h/2) * (f(t_k, y_k) + f(t_k + h, y_p)).
  Global error is O(h**2). With h = 0.1, y(0.5) = 0.60708 (error
  5.5e-4); halving h gives 1.31e-4, ratio 4.15: order 2. The slope
  average makes it exact for RHS linear in t, e.g. dy/dt = t on
  [0, 1] gives y(1) = 0.5 exactly.
- Classical RK4: k1 = f(t_k, y_k), k2 = f(t_k + h/2, y_k + h*k1/2),
  k3 = f(t_k + h/2, y_k + h*k2/2), k4 = f(t_k + h, y_k + h*k3),
  y_{k+1} = y_k + (h/6) * (k1 + 2*k2 + 2*k3 + k4). Global error is
  O(h**4). With h = 0.1, y(0.5) = 0.606531 (error 2.7e-7); halving h
  gives 1.65e-8, ratio 16.7: order 4. This is the default accurate
  choice.
- Error comparison: max_abs_error(sol, exact) returns the maximum
  of abs(y_k - exact(t_k)) over every tabulated point, so one number
  summarizes the whole trajectory.
- Convergence check: run the same problem at h and h/2 and form the
  error ratio. A ratio near 2 confirms order 1, near 4 order 2, near
  16 order 4. If the error does not shrink as expected, the step is
  too large or the method does not match the problem.
- Method choice: Euler for a cheap first look, Heun when order 2
  suffices, RK4 as the default for smooth right-hand sides.
- All functions are deterministic and stdlib-only; no network, no
  third-party numerical libraries.

## Workflow

1. Write the problem as dy/dt = f(t, y) and record t0, y0, the
   target time, and the closed-form solution when one exists.
2. Pick the method: euler for a quick first look, heun for order 2,
   rk4 for the default accurate result.
3. Choose the step size h so that n = (t_target - t0) / h steps
   reach the target time; call euler(f, t0, y0, h, n) or the
   equivalent heun/rk4 call.
4. Compare against the closed form with max_abs_error(sol, exact)
   when the exact solution is available.
5. Halve h and re-run; confirm the error ratio matches the expected
   order (2, 4, 16). Report the solution table, the method, and the
   error together.

## Pitfalls

- Confusing ODE solving with numerical integration (quadrature):
  quadrature computes a definite integral, a single number, in one
  pass over the integrand; ODE solvers march a state y forward from
  an initial condition. A task that says "integrate the differential
  equation" is still an ODE problem and routes to ode-solvers, not
  to numerical-integration.
- Confusing ODE solving with finite-difference-derivatives: those
  estimate f'(t) at a point from samples of the function f; ODE
  solvers advance y given the rate f(t, y). One reads derivatives,
  the other propagates states.
- Using h <= 0: the step size must be strictly positive; zero,
  negative, or non-numeric h raises ValueError, never silently
  returns.
- Using a non-integer or non-positive step count: n must be a
  positive int; 2.5 or 0 raises instead of truncating or looping
  forever.
- Trusting Euler without a convergence check: Euler is order 1, so
  on a fast-decaying or stiff problem it needs very small h; halve h
  and confirm the error ratio before accepting the result.
- Mixing up local and global error: each step carries error
  O(h**(p+1)) but the accumulated global error over the trajectory
  is O(h**p), one order lower.
- Expecting adaptive step control: these are fixed-step solvers;
  there is no automatic step refinement inside one call.
- Dropping the t dependence of f: dy/dt = -y and dy/dt = -t*y are
  different problems; pass f(t, y), not f(y).

## Behavior contract (gate 3)

The explicit Euler, Heun (RK2), and classical RK4 stepping, the
step-size convergence trend, and the closed-form error comparison
are exercised by the gate 3 contract test:
scripts/test_ode_solvers.py against scripts/ode_solvers_logic.py
(stdlib unittest, offline). Run: python3 scripts/test_ode_solvers.py

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 25 (FAR-25)
  anchors the certification analyses, such as flight-dynamics
  response and trajectory time-marching, that these solvers support;
  the numerical methods themselves are classical numerical-analysis
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
