---
name: root-finding
description: "Determine the root of a nonlinear scalar equation f(x) = 0 numerically with the bisection method, Newton-Raphson, the secant method, or fixed-point iteration: bracket the root or supply an initial guess, apply the iteration, and produce the root to a specified tolerance under function tolerance, step tolerance, and max iteration convergence criteria. Use when a task asks for a root finder, zero finding, nonlinear equation solving, compressible flow Mach number solution, or implicit performance equation inversion in aerospace analysis. Produces the root, the method, and the iteration count. Trigger: root-finding, bisection, newton-raphson, secant-method, fixed-point iteration, mach number root, nonlinear equation, zero finding."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [root-finding, bisection, newton-raphson, secant-method, secant, fixed-point-iteration, mach-number, nonlinear-equation, zero-finding, convergence-criteria, initial-guess, bracket]
  version: 0.1.0
  author: Aero Agent Skills
---

# Root Finding (cross-cutting/numerics/root-finding)

Use when the task is solving a nonlinear scalar equation f(x) = 0
numerically: choosing the bracketing or iteration method, supplying
the bracket or initial guess, and reporting the root to a specified
tolerance.

## Domain quick reference

All worked numbers are for f(x) = x**2 - 2, whose positive root is
sqrt(2) = 1.4142135623730951.

- Bisection: with f(a) * f(b) < 0 (a sign change is bracketed),
  evaluate the midpoint c = (a + b) / 2 and halve the interval on
  the side that keeps the sign change. Linear convergence: one
  binary digit per step, error bounded by the interval half-width,
  so about 34 steps take [1, 2] to sqrt(2) at tol = 1e-10. Robust
  and derivative-free; needs only sign information.
- Newton-Raphson: x_{k+1} = x_k - f(x_k) / f'(x_k). Quadratic
  convergence for a simple root when the initial guess is close
  enough; needs the derivative f'. From x0 = 1.5 on x**2 - 2 the
  iterate reaches 1.41421356237 in three steps. Fails when f'(x) is
  zero at a step (the update is undefined).
- Secant method: x_{k+1} = x_k - f(x_k) * (x_k - x_{k-1}) /
  (f(x_k) - f(x_{k-1})). Approximates the derivative with the secant
  slope, so no analytic derivative is needed; superlinear convergence
  of order about 1.618 for a simple root. Fails when the two function
  values are equal (the slope is zero).
- Fixed-point iteration: rewrite f(x) = 0 as x = g(x) and iterate
  x_{k+1} = g(x_k). Converges when g is a contraction at the fixed
  point, in practice when abs(g'(x*)) < 1; a repelling fixed point
  with abs(g'(x*)) > 1 diverges.
- Bracketing and initial guess requirements: bisection needs a
  bracket whose endpoints straddle zero; Newton-Raphson and the
  secant method need initial guesses near the root; fixed-point
  iteration needs a contractive rewrite. There is no global method
  for arbitrary nonlinear equations.
- Convergence criteria: the function tolerance abs(f(x)) < tol
  declares convergence for Newton-Raphson and the secant method; the
  step tolerance (interval half-width, or abs(x_{k+1} - x_k) for
  fixed-point iteration) declares convergence for bisection and
  fixed-point iteration; every method stops with an error after
  max_iter iterations.
- Non-monotonic and ill-conditioned behavior: bisection still
  converges on a non-monotonic function as long as the endpoints
  straddle zero, but a double root (f touches zero without a sign
  change, e.g. x**2 = 0) has no straddle; Newton-Raphson can
  overshoot on non-convex functions or converge to a different root;
  a near-zero derivative amplifies function error and makes the
  problem ill-conditioned; the secant method can blow up when
  f(x_k) is close to f(x_{k-1}).
- Aerospace application: the isentropic area-Mach relation
  A/A* = (1/M) * ((2/(gamma+1)) * (1 + (gamma-1)/2 * M**2)) **
  ((gamma+1)/(2*(gamma-1))) with gamma = 1.4 is solved for M given
  A/A*; A/A* = 1.2 gives the subsonic root M = 0.59024876099 and the
  supersonic root M = 1.53414976720. Implicit performance equations
  (range, climb, thrust balance) are inverted the same way.
- All functions are deterministic and stdlib-only; no network, no
  third-party numerical libraries.

## Workflow

1. Write the problem as f(x) = 0 and record the tolerance and the
   max iteration budget.
2. Bracket the root when possible: find a and b with f(a) * f(b) < 0
   and call bisection(f, a, b, tol, max_iter); otherwise pick initial
   guesses for the derivative-based methods.
3. Pick the method: bisection for robustness and guaranteed
   convergence on a bracket, newton_raphson when the derivative is
   cheap, secant when it is not, fixed_point_iteration when a
   contractive rewrite x = g(x) is natural.
4. Call the method; a ValueError means the bracket did not straddle
   zero, the derivative or secant slope was zero, or the iteration
   did not converge within max_iter.
5. Verify the result: evaluate f(root) and confirm it is below the
   function tolerance, and report the root, the method, and the
   iteration count together.

## Pitfalls

- Confusing root finding with ODE solving: ode-solvers marches a
  state y(t) forward in time from an initial condition; root finding
  solves f(x) = 0 for a single scalar. A task that says "solve the
  equation" without time marching is a root-finding problem and
  routes here, not to ode-solvers.
- Confusing root finding with numerical integration: quadrature
  returns a definite integral, a single number, in one pass; root
  finding locates where a function vanishes. Integrals route to
  numerical-integration.
- Confusing root finding with interpolation: interpolation fits a
  curve through given data points; root finding locates zeros of a
  given function. Fitting questions route to interpolation.
- Confusing root finding with convergence verification: that leaf
  estimates discretization error with Richardson extrapolation, it
  does not locate zeros. Error estimation routes to
  convergence-verification.
- Calling bisection without a straddle: f(a) * f(b) >= 0 raises
  ValueError, never silently searches. A double root (x**2 = 0)
  touches zero without changing sign and cannot be bracketed by
  bisection alone.
- Calling newton_raphson where the derivative vanishes: f'(x) = 0 at
  a step raises ValueError; the update x - f/f' is undefined there.
- Trusting a root without the residual check: always evaluate f(root)
  against the function tolerance; a non-converged or wrong-branch
  root is caught by the residual, not by the iteration count.
- Using a loose max_iter with a tight tol: bisection needs about
  log2((b - a) / tol) steps; a max_iter below that raises
  ValueError on convergence failure, which is the contract, not a
  bug.
- Expecting one method to work everywhere: no method is global.
  Newton-Raphson and the secant method converge locally and can
  diverge or land on a different root; fixed-point iteration needs a
  contractive rewrite. Report the bracket or initial guess so the
  result is reproducible.
- Routing compressible-flow Mach table lookups here: closed-form
  property tables and airfoil data stay with their data leaves; the
  inversion of a compressible-flow relation for a Mach root is the
  root-finding task and routes here.

## Behavior contract (gate 3)

The bisection, Newton-Raphson, secant, and fixed-point iteration
logic, the bracket and initial guess requirements, the convergence
criteria, and the ValueError contracts (non-straddling bracket, zero
derivative or secant slope, convergence failure) are exercised by the
gate 3 contract test: scripts/test_root_finding_logic.py against
scripts/root_finding_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_root_finding_logic.py

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  compressible-flow tables and isentropic area-Mach relations that
  these root-finding methods invert; the numerical methods themselves
  are classical numerical-analysis methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
