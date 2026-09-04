---
name: optimization-algorithms
description: "Use when you must minimize a scalar or multivariate design objective numerically: bracket a smooth one-variable objective and locate the minimum with golden-section search, or apply Newton's method on the derivative; run gradient descent with an Armijo backtracking line search or the derivative-free Nelder-Mead simplex for multivariate problems, and report the converged minimizer, the objective value, and the iteration count at a specified tolerance. Produces the unconstrained minimum, the converged objective value, the iteration count, and the verdict on brackets, learning rates, and tolerances. Trigger: optimization, minimize, golden section search, gradient descent, Nelder-Mead simplex, Newton method, line search, unconstrained minimum."
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
  tags: [optimization-algorithms, golden-section-search, gradient-descent, nelder-mead, newton-method, line-search, unconstrained-minimum]
  version: 0.1.0
  author: Aero Agent Skills
---

# Optimization Algorithms (cross-cutting/numerics/optimization-algorithms)

Use when the task is unconstrained numerical minimization: given an
objective function f, find the x that makes f smallest, for a smooth
scalar objective or a multivariate one, with or without derivatives.
This leaf complements cross-cutting/numerics/root-finding (which
solves f(x) = 0 for a root) with true minimization, and it closes the
numerics toolbox that engineering design loops use: sizing and
performance iterations converge a scalar objective (fuel burn, drag,
mass) to its unconstrained optimum before constraints are imposed.

## Domain quick reference

All worked numbers below are verified by
scripts/test_optimization_algorithms.py (stdlib unittest, offline).

- Golden-section search: for a unimodal f on [a, b] with the minimum
  strictly inside, the trial points c = b - (b - a)/phi and
  d = a + (b - a)/phi split the bracket with
  phi = (1 + sqrt(5)) / 2 = 1.6180339887. Each step evaluates f(c)
  and f(d) and discards the interval end adjacent to the larger
  value, shrinking the bracket by 1/phi = 0.618 per step, so N steps
  reduce the width from (b - a) to (b - a)/phi**N. From [0, 10] to
  tol = 1e-6 takes 34 steps. Derivative-free, robust, one minimum
  per bracket.
- Bracketing contract: the midpoint m = (a + b)/2 must satisfy
  f(m) < f(a) and f(m) < f(b); a monotonic f or a minimum sitting on
  an endpoint is not a valid bracket and raises ValueError. For
  tol tighter than about 1e-7 the function values at the trial
  points round to the same double near a flat minimum, so x accuracy
  floors near 1e-8 even though the interval keeps shrinking.
- Gradient descent: x_{k+1} = x_k - s_k * grad f(x_k) with the
  negative gradient as the descent direction. Each step starts from
  the learning rate lr and backtracks (halving s) until the Armijo
  sufficient-decrease condition f(x - s*g) <= f(x) - c1 * s * ||g||**2
  holds with c1 = 1e-4, up to 60 halvings. Convergence is declared on
  the gradient tolerance ||grad(x)|| < tol. Linear convergence whose
  rate depends on the Hessian condition number: the Rosenbrock
  valley is so curved that from (0, 0) about 14800 steps are needed
  at tol = 1e-6, against 2 steps for a well-scaled quadratic.
- Nelder-Mead simplex: keeps n + 1 vertices (a segment for 1D
  problems) and replaces the worst vertex by reflection (rho = 1),
  expansion (chi = 2) when the reflection is a new best, and inside
  or outside contraction (gamma = 0.5); when no contraction helps,
  the simplex shrinks toward the best vertex (sigma = 0.5). No
  derivatives are needed. The initial simplex is deterministic
  (coordinate i perturbed by 0.05 * abs(x0_i), or 0.00025 when
  x0_i = 0), so results are identical across runs and the seed
  argument is ignored. Convergence is declared when the spread of the
  vertex objective values, max(f) - min(f), drops below tol; for a
  smooth quadratic that puts x accuracy near sqrt(tol).
- Newton on the derivative: applies Newton iteration to the
  stationary-point equation f'(x) = 0,
  x_{k+1} = x_k - f'(x_k)/f''(x_k). Quadratic convergence near a
  stationary point; one step is exact for a quadratic. It finds a
  stationary point of f, which is a minimum only where f'' > 0, so
  evaluate f'' at the solution to confirm the curvature. Raises
  ValueError when f''(x) = 0 at a step (the update is undefined).
- Convergence and error contracts: every method raises ValueError
  when tol <= 0, max_iter < 1, an input is not finite, or the
  tolerance is not reached within max_iter (the iteration budget is
  a contract, not a suggestion). Return shape is (x_min, f_min,
  iterations) everywhere: a float x for the scalar methods and for
  gradient_descent or nelder_mead with a scalar x0, a tuple of
  coordinates when x0 is a sequence.

## Workflow

1. Classify the problem: is f scalar with a natural bracket, or
   multivariate? Do analytic derivatives exist?
2. For a 1D objective, bracket a minimum (a < b with f(mid) below
   both endpoints) and call golden_section_minimize(f, a, b, tol,
   max_iter) for a derivative-free result, or newton_1d_minimize(f,
   fp, fpp, x0, tol, max_iter) when f' and f'' are cheap and smooth.
3. For a multivariate objective with an analytic gradient, call
   gradient_descent(f, grad, x0, lr, tol, max_iter); the Armijo
   backtracking line search inside each step makes the result robust
   to the learning rate choice.
4. Without derivatives, call nelder_mead(f, x0, tol, max_iter) with
   a scalar or sequence start; the deterministic simplex gives the
   same result on every run, so the optional seed needs no value.
5. Read the return tuple (x_min, f_min, iterations) and check the
   convergence criterion of the method: interval width for golden
   section, gradient norm for descent, vertex spread for Nelder-Mead,
   derivative magnitude for Newton. A ValueError means the bracket,
   the start, the tolerance, or the iteration budget was invalid.
6. Verify curvature for derivative-based results where it matters:
   f'' > 0 at the Newton solution confirms a minimum rather than a
   maximum or saddle.

## Worked example

Minimize the scalar design objective f(x) = (x - 3)**2 + 2, whose
minimum is f = 2 at x = 3.

- Golden-section search on the bracket [0, 10] at tol = 1e-6 returns
  x = 2.9999999515 (within 1e-4 of 3), f = 2.000000000000002 (within
  1e-6 of 2), after 34 interval updates. The bracket check evaluates
  f(0) = 11, f(5) = 6, f(10) = 51 and confirms 6 < 11 and 6 < 51.
- Newton on the derivative from x0 = 10 with f' = 2*(x - 3) and
  f'' = 2 lands exactly on x = 3 in one step: x1 = 10 - 14/2 = 3.
- Nelder-Mead on the shifted anchor f(x) = (x - 2)**2 + 1 from
  x0 = 0 at tol = 1e-6 returns x = 1.99975, f = 1.0000001 in 22
  iterations (x within 1e-3 of 2).

Multivariate example: minimize f(x, y) = x**2 + 2*y**2 with minimum
0 at (0, 0).

- Gradient descent from (1, 1) with lr = 1.0 returns ((0.0, 0.0),
  0.0, 2): the Armijo backtracking finds the exact quadratic steps.
- Nelder-Mead from (1, 1) at tol = 1e-6 returns a point within 2e-3
  of (0, 0) with f = 5.0e-7 in 34 iterations.
- Rosenbrock f(x, y) = (x - 1)**2 + 100*(y - x**2)**2 from (0, 0)
  exercises the curved valley: Nelder-Mead reaches f = 7.2e-7 near
  (1.0005, 1.0011) in 68 iterations, while gradient descent with
  backtracking needs about 14800 iterations at tol = 1e-6 (raise
  max_iter to 20000 for the comparison).

## Pitfalls

- Confusing minimization with root finding: root-finding solves
  f(x) = 0 for a crossing; minimization returns the x where f is
  smallest. A task that asks to make an objective small routes here,
  not to cross-cutting/numerics/root-finding.
- Calling golden-section search without a genuine bracket: f(mid)
  must be below both f(a) and f(b). A monotonic objective or a
  minimum at an endpoint raises ValueError, never silently searches.
- Expecting a global minimum from a local method: golden-section
  search, gradient descent, Nelder-Mead, and Newton on the derivative
  all locate a local minimum near the bracket or start; a multimodal
  objective needs multiple starts or a bracket per mode.
- Using a loose max_iter with a tight tol: gradient descent on the
  Rosenbrock valley needs tens of thousands of steps at tol = 1e-6;
  the ValueError on budget exhaustion is the contract, not a bug.
- Trusting Newton on the derivative without a curvature check: it
  converges to a stationary point, which is a maximum where
  f'' < 0 (the anchor x**3/3 - x from x0 = -2 converges to the
  maximum x = -1). Confirm f'' > 0 at the solution.
- Reading too much into the Nelder-Mead x accuracy: the convergence
  test is on the vertex objective spread, so x error near a smooth
  minimum scales like sqrt(tol), about 1e-3 at tol = 1e-6.
- Expecting the flat-minimum accuracy of the golden-section search to
  follow the tolerance: near x = 3 of (x - 3)**2 + 2 the trial values
  tie at double precision below tol ~ 1e-7, flooring x accuracy near
  1e-8.
- Routing constrained or coupled design questions here:
  multidisciplinary optimization with coupling variables, design
  variables, and constraints is the vehicle-design mdo leaf, not this
  numerics method leaf.

## Verification

- Confirm golden_section_minimize(f, 0.0, 10.0) on (x - 3)**2 + 2
  returns x = 3.0 within 1e-4, f = 2.0 within 1e-6, in 34
  iterations.
- Confirm gradient_descent on x**2 + 2*y**2 from (1, 1) returns
  (0.0, 0.0) with f = 0.0, and that the Rosenbrock run with
  max_iter = 20000 converges near (1, 1) with f below 1e-6.
- Confirm nelder_mead on (x - 2)**2 + 1 from 0.0 returns x within
  1e-3 of 2, and that two calls and a seeded call return identical
  results (deterministic, seed ignored).
- Confirm newton_1d_minimize on (x - 3)**2 + 2 from x0 = 10.0
  returns x = 3.0 in one iteration.
- Confirm ValueError rejection of an empty or non-unimodal bracket, a
  non-positive learning rate or tolerance, a zero second derivative
  at a Newton step, non-finite inputs, and convergence failure within
  max_iter.
- Run the contract test offline: python3
  scripts/test_optimization_algorithms.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/root-finding: solves f(x) = 0; Newton on
  the derivative here is root finding applied to f'.
- cross-cutting/numerics/finite-difference-derivatives: supplies
  gradient and second-derivative estimates when analytic derivatives
  are not available.
- cross-cutting/numerics/least-squares-regression: the closed-form
  minimizer of a residual sum of squares, the linear special case of
  this leaf.
- cross-cutting/numerics/numerical-integration: quadrature supplies
  objective terms (energy, work, integrals) inside design loops that
  this leaf then optimizes.
- cross-cutting/numerics/ode-solvers: time-marching the state of a
  dynamic design problem before its scalar cost is minimized.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_optimization_algorithms.py

The 35 tests cover the golden-section bracket contract and the
34-iteration anchor, gradient descent with Armijo backtracking on a
quadratic and the Rosenbrock function, deterministic Nelder-Mead on
1D and 2D anchors, Newton on the derivative from several starts and
its curvature caveat, the scalar and vector calling conventions, and
ValueError rejection of empty or non-unimodal brackets, non-positive
learning rates and tolerances, zero second derivatives, non-finite
inputs, and convergence failure within max_iter.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  engineering context that these classical numerical-analysis methods
  serve (compressible-flow relations and performance tables); the
  algorithms themselves are standard numerical methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
