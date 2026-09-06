---
name: lqg-design
description: "Use when you must design a linear-quadratic-Gaussian output-feedback compensator for a two-state system whose state is not fully measurable: solve the regulator algebraic Riccati equation for the symmetric stabilizing P and the gain K from the quadratic cost weights, solve the filter (Kalman) algebraic Riccati equation for the error covariance S and the estimator gain L from the process and measurement noise covariances, assemble the dynamic output-feedback compensator state-space realization, and verify the separation principle that the closed-loop eigenvalues are the union of the regulator and estimator poles. Produces the two Riccati solutions with their gains, the compensator matrices and transfer function, and the separation verdict. Trigger: lqg, linear-quadratic-gaussian, output-feedback-compensator, separation-principle, regulator-riccati, filter-riccati-gain, compensator-transfer-function."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: optimal-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [lqg-design, linear-quadratic-gaussian, output-feedback-compensator, separation-principle, filter-riccati-gain, compensator-transfer-function]
  version: 0.1.0
  author: AeroSkills
---

# LQG Design (gnc-autonomy/optimal-control/lqg-design)

Use when the task is linear-quadratic-Gaussian output-feedback design for
the canonical scalar-input two-state plant whose state is not fully
measurable: composing the regulator Riccati gain with the filter (Kalman)
Riccati gain into a dynamic output-feedback compensator and verifying the
separation principle on the assembled loop. This leaf implements the exact
closed forms of both algebraic Riccati equations for the damped double
integrator family in pure Python, stdlib only. It pairs with
gnc-autonomy/optimal-control/lqr-design for the full-state regulator
ingredient and gnc-autonomy/navigation/kalman-filter-design for the
discrete-time scalar filter runs; here the two continuous-time Riccati
solutions are fused into one compensator, which neither sibling does.

## Domain quick reference

- Plant family: A = [[0, 1], [0, -a]] with damping a >= 0 (a = -A[1][1]),
  input B = [0, 1] (acceleration-like control on the rate state) and
  measured output C = [1, 0] (y = x1, position-like). Unit convention:
  x1 in m (or rad), x2 in m/s (or rad/s), u in m/s^2 (or rad/s^2); the
  weights Q = diag(q1, q2), R = r, Qw = diag(w1, w2) and Rw = rv sit in
  the consistent squared units, so both Riccati equations are
  dimensionless.
- Regulator algebraic Riccati equation: A'P + PA - P B R^-1 B' P + Q = 0.
  With P = [[p1, p2], [p2, p3]] the exact scalar reduction used by the
  lqr-design sibling is p2 = sqrt(r q1), p3 = r (-a + sqrt(a^2 + (2 p2 +
  q2) / r)) and p1 = a p2 + p2 p3 / r. The control side of the
  compensator is u = -K x_hat with K = [p2 / r, p3 / r].
- Filter (Kalman) algebraic Riccati equation: A S + S A' - S C' Rw^-1 C S +
  Qw = 0, the dual of the regulator ARE. Its three scalar entries give
  s1 = sqrt(rv (2 s2 + w1)) and s3 = a s2 + s1 s2 / rv, where s2 is the
  root of the monotone equation u^2 + 2 a^2 rv u + 2 a u sqrt(rv (2 u +
  w1)) - rv w2 = 0: exactly sqrt(rv w2) at a = 0, otherwise the unique
  root on (0, sqrt(rv w2)] found by bisection to 1e-15 relative. The
  estimator gain is L = [s1 / rv, s2 / rv].
- Compensator: x_hat' = A x_hat + B u + L (y - C x_hat) with u = -K x_hat
  closes to Ac = A - B K - L C = [[-l1, 1], [-k1 - l2, -a - k2]], Bc = L,
  Cc = -K, Dc = 0, so u = Cc x_hat + Dc y.
- Separation principle: in the (x, e = x - x_hat) coordinates the 4x4
  closed loop is block upper triangular with diagonal blocks A - B K and
  A - L C, so its characteristic polynomial factors as det(sI - (A - B K))
  times det(sI - (A - L C)) = (s^2 + (a + k2) s + k1) (s^2 + (a + l1) s +
  (a l1 + l2)). The closed-loop eigenvalues are the union, with
  multiplicity, of the regulator poles and the estimator poles.
- Compensator transfer function: G_c(s) = Cc (sI - Ac)^-1 Bc with monic
  denominator s^2 - tr(Ac) s + det(Ac); the numerator is degree <= 1.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the Riccati and separation mathematics is common control-theory
  knowledge, summary only.

## Workflow

1. Fix the plant and the weights: canonical plant family A = [[0, 1],
   [0, -a]] with damping a >= 0, B = [0, 1], C = [1, 0], cost weights
   Q = diag(q1, q2) and R = r, noise covariances Qw = diag(w1, w2) and
   Rw = rv in the SI unit convention (w2 must be > 0: noise on the driven
   state, without which the double integrator has no stabilizing filter).
2. Solve the regulator ARE with regulator_riccati(A, B, Q, R): returns the
   symmetric P and the gain K = [k1, k2] for u = -K x_hat.
3. Solve the filter ARE with filter_riccati(A, C, Qw, Rw): returns the
   error covariance S and the estimator gain L = [l1, l2] (the s2 root is
   closed form sqrt(rv w2) at a = 0 and bisection at a > 0).
4. Assemble the dynamic output-feedback compensator with
   compensator_realization(A, B, C, K, L): returns Ac, Bc, Cc, Dc, the four
   matrices flight software integrates.
5. Run the separation-principle verdict with separation_verdict(A, B, C,
   K, L): the Faddeev-LeVerrier characteristic polynomial of the 4x4
   plant-plus-compensator loop versus the product of the regulator and
   estimator polynomials, returned as the verdict dict with "separated".
6. Reduce the compensator to its transfer function with
   compensator_transfer_function(Ac, Bc, Cc): G_c(s) numerator and monic
   denominator for loop shaping and implementation checks.
7. Confirm the deterministic checks with the contract test
   scripts/test_lqg_design.py.

## Worked example

Example A, undamped double integrator, matched weights: a = 0,
Q = diag(1, 1), R = 1, Qw = diag(1, 1), Rw = 1 (the same "Worked, double
integrator: A = [[0, 1], [0, 0]] (position, velocity) with C = [[1, 0]]"
plant the observer-design leaf works).

- Regulator: P = [[1.73205080757, 1], [1, 1.73205080757]] (sqrt(3) on the
  diagonal), K = [1, 1.73205080757] = [1, sqrt(3)]; ARE residual
  4.440892e-16.
- Filter: S = [[1.73205080757, 1], [1, 1.73205080757]], identical to P by
  dual symmetry (matched weights on the undamped plant); L =
  [1.73205080757, 1] = [sqrt(3), 1]; s2 = sqrt(rv w2) = 1; ARE residual
  4.440892e-16.
- Pole pairs: regulator poles det(sI - (A - B K)) and estimator poles
  det(sI - (A - L C)) both at -0.866025403784 +/- 0.5j, the classic
  double-integrator LQR pair (1 rad/s, damping ratio sqrt(3)/2).
- Compensator: Ac = [[-1.73205080757, 1], [-2, -1.73205080757]], Bc = L,
  Cc = -K = [-1, -1.73205080757], Dc = 0. The compensator's own poles sit
  at -1.73205080757 +/- 1.41421356237j, NOT the closed-loop poles.
- Separation verdict: closed-loop 4x4 polynomial [1, 3.46410161514, 5,
  3.46410161514, 1] equals (s^2 + sqrt(3) s + 1)^2 to max abs diff
  4.440892e-16; verdict True. Closed-loop eigenvalues -0.866025403784 +/-
  0.5j, each with multiplicity 2.
- Transfer function: G_c(s) = (-3.46410161514 s - 1) / (s^2 + 3.46410161514
  s + 5); the denominator is s^2 - tr(Ac) s + det(Ac).

Example B, damped plant, distinct tuning (exercises the bisection branch):
a = 0.5, Q = diag(2, 1), R = 1, Qw = diag(1, 4), Rw = 1.

- Regulator: P = [[2.85602070187, 1.41421356237], [1.41421356237,
  1.5195116055]], K = [1.41421356237, 1.5195116055]; regulator poles
  -1.00975580275 +/- 0.628177348514j; ARE residual 4.440892e-16.
- Filter (s2 by bisection): S = [[1.81799603658, 1.15255479452],
  [1.15255479452, 2.67161744564]], L = [1.81799603658, 1.15255479452];
  estimator poles -1.15899801829 +/- 0.847511891601j, faster than the
  regulator pair as the heavier process noise (w2 = 4) demands; ARE
  residual 1.998401e-15 validates the bisection branch.
- Separation verdict: closed-loop polynomial [1, 4.33750764208,
  8.15698627256, 7.44147126328, 2.91547594742] equals the product of
  s^2 + 2.0195116055 s + 1.41421356237 and s^2 + 2.31799603658 s +
  2.06155281281 to max abs diff 1.776357e-15; verdict True, all four
  closed-loop eigenvalues with negative real part.
- Compensator: Ac = [[-1.81799603658, 1], [-2.56676835689, -2.0195116055]],
  G_c(s) = (-4.32235503752 s - 2.91547594742) / (s^2 + 3.83750764208 s +
  6.23823245152).

## Verification

- Confirm Example A: regulator_riccati and filter_riccati return P = S =
  [[1.73205080757, 1], [1, 1.73205080757]] within 1e-6, K = [1,
  1.73205080757] and L = [1.73205080757, 1], both ARE residuals below 1e-9
  and the closed-form s2 root equal to the forced bisection branch within
  1e-12.
- Confirm Example A verdict: closed-loop polynomial within 1e-6 of (s^2 +
  sqrt(3) s + 1)^2, max abs diff below 1e-9, separated True, and the
  compensator transfer function numerator [-3.46410161514, -1] with
  denominator [1, 3.46410161514, 5].
- Confirm Example B: K, L, both pole pairs and the separation verdict
  within 1e-6 of the anchor values, both ARE residuals below 1e-9.
- Confirm dual symmetry: on the undamped plant with weights invariant
  under the state-index swap (q1 = q2 = w1 = w2 = r = rv), S equals P and
  the regulator and estimator pole pairs are identical.
- Confirm every non-physical input raises ValueError: A not of the
  canonical family, damping a < 0, B not [0, 1], C not [1, 0],
  non-diagonal Q or Qw, q1 or q2 < 0, w1 < 0, w2 <= 0, R <= 0, Rw <= 0,
  K or L not length-2.
- Run the contract test offline: python3 scripts/test_lqg_design.py (34
  tests, deterministic, stdlib only).

## Related leaves

- gnc-autonomy/optimal-control/lqr-design: the full-state regulator
  ingredient, u = -K x with every state measured; this leaf composes that
  gain with the estimator.
- gnc-autonomy/control/observer-design: the deterministic full-order
  estimator for this plant family, whose separation check takes K and L as
  given; this leaf synthesizes both gains from Riccati equations.
- gnc-autonomy/navigation/kalman-filter-design: discrete-time scalar
  predict/update filter runs over sampled measurement streams.
- gnc-autonomy/optimal-control/bang-bang-control and
  gnc-autonomy/optimal-control/model-predictive-control: the alternative
  time-domain control laws for the same plant family.

## Pitfalls

- Reporting the compensator's own poles as the closed-loop poles: the
  eigenvalues of Ac = A - B K - L C sit at -1.73205080757 +/- 1.41421356237j
  in Example A, while the true closed-loop eigenvalues are the union at
  -0.866025403784 +/- 0.5j, each with multiplicity 2; only the 4x4
  assembly carries the union, which is why the verdict runs there.
- Checking stability on the 2x2 regulator loop alone: the output-feedback
  loop adds the estimator poles, so a separated verdict needs the product
  polynomial of both factors compared with the full-loop polynomial.
- Assuming S = P for arbitrary matched weights: the dual symmetry holds on
  the undamped plant when the weights are invariant under the state-index
  swap (Example A weights); with Q = Qw = diag(3, 2) the filter solution
  equals the index-swapped regulator solution, not P itself.
- Dropping the noise on the driven state (w2 = 0): the double integrator
  then has no stabilizing filter solution, and the module raises
  ValueError rather than returning a meaningless gain.
- Tuning the estimator slower than the regulator: with light process noise
  the estimator poles sit inside the regulator pair and dominate the
  response; raise w2 (Example B) to push the estimator error poles at or
  inside the regulator bandwidth.
- Carrying the leaf outside its family: general n-state Riccati solvers,
  discrete-time LQG over sampled measurement streams is out of scope here
  (see kalman-filter-design), and shaping the loop gain toward full-state
  recovery is not implemented in this leaf.
- Accepting negative weights or nonpositive covariances; the shared
  validation raises ValueError on every non-physical input.

## Behavior contract (gate 3)

The two Riccati solves, the compensator realization, the separation
verdict and the transfer function are exercised by the gate 3 contract
test: scripts/test_lqg_design.py against scripts/lqg_design_logic.py
(stdlib unittest, offline, deterministic). Run:

python3 scripts/test_lqg_design.py

The test covers the Example A and Example B anchors within 1e-6, both ARE
residuals below 1e-9, the closed-form and bisection s2 agreement within
1e-12, dual symmetry on the undamped plant, the Faddeev-LeVerrier product
identity of the separation verdict on and off the anchors, the transfer
function denominator identity, determinism on repeat runs, stdlib-only
imports, and ValueError rejection of every non-physical input listed in
Verification.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
