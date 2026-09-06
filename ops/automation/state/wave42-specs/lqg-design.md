# Wave-42 leaf spec: lqg-design (gnc-autonomy, optimal-control pack)

- Path: skills/gnc-autonomy/optimal-control/lqg-design/
- Pack: optimal-control (present siblings lqr-design, bang-bang-control,
  model-predictive-control, dymos-trajectory; adjacent fences
  gnc-autonomy/control/observer-design (deterministic Luenberger) and
  gnc-autonomy/navigation/kalman-filter-design (discrete-time single-axis
  filter)).
- Claim fences (quoted from the sibling frontmatter at prep, none owns the LQG
  composition):
  - lqr-design (this pack) designs FULL-STATE feedback only: its description reads
    "Use when you must design an LQR state-feedback gain matrix for a scalar-input
    two-state system such as spacecraft attitude control: solve the algebraic
    Riccati equation for the cost weights, compute the gain matrix, verify
    closed-loop stability of the regulated system, and assess the Q over R
    weighting trade. Produces the Riccati solution, the gain vector, and the
    stability verdict that feed the control-law design." It produces u = -K x with
    every state measured; no estimator, noise covariance or output-feedback
    compensator appears in its body (grep for lqg/output-feedback/gaussian: 0 hits
    in that SKILL.md).
  - kalman-filter-design (navigation pack) runs the estimator in the DISCRETE time
    domain over measurement sequences: its description reads "Use when you must
    design or run a discrete-time Kalman filter for single-axis state estimation
    in SI units: predict the state and its error covariance through the dynamics
    model, compute the innovation and innovation variance, calculate the Kalman
    gain, and correct the state and covariance from a noisy measurement." It
    filters a single axis with scalar predict/update recursion and never assembles
    a compensator from a steady-state filter Riccati solution.
  - observer-design (control pack) is the deterministic Luenberger estimator by
    pole placement: its description reads "Use when you must design a full-order
    Luenberger state observer for a linear time-invariant system whose states are
    not all directly measurable: ... confirm the separation principle so observer
    poles and controller poles combine by union in the closed loop, and size the
    convergence with the settling time." It explicitly routes both LQG ingredients
    away: "Routing stochastic estimation here: Kalman gain, innovation, process
    and measurement noise covariances, and the covariance recursion belong to
    gnc-autonomy/navigation/kalman-filter-design; observer design is deterministic
    pole placement with no noise statistics." and "Routing controller gain design
    here: the feedback gain K from quadratic cost belongs to
    gnc-autonomy/optimal-control/lqr-design ... this leaf designs the estimator
    side L, and u = -K x_hat combines both through the separation principle." Its
    separation check takes K and L as GIVEN (for example from lqr-design) and
    factorizes the closed-loop polynomial; it synthesizes neither gain from a
    Riccati equation.
  Whole-tree greps at prep: "lqg|linear-quadratic-gaussian|loop-transfer
  recovery|output-feedback optimal" -> 0 hits in skills/ (exact re-grep: 0
  files). GENUINE gnc-autonomy gap: no leaf composes the regulator Riccati
  gain and the filter (Kalman) Riccati gain into a dynamic output-feedback
  compensator and verifies the separation principle on the assembled loop;
  lqr-design stops at full-state u = -K x, kalman-filter-design runs discrete
  scalar cycles, observer-design places Luenberger poles with no noise
  statistics.
- Standards id: arp4754a (reference-only, present in standards-map.yaml). Ledger
  Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design a linear-quadratic-Gaussian (LQG) output-feedback compensator for the
canonical scalar-input two-state plant whose state is not fully measurable: solve
the regulator algebraic Riccati equation for the symmetric stabilizing P and the
gain K from the quadratic cost weights; solve the filter (Kalman) algebraic
Riccati equation for the error covariance S and the estimator gain L from the
process and measurement noise covariances; assemble the dynamic output-feedback
compensator x_hat' = (A - B K - L C) x_hat + L y with u = -K x_hat; verify the
separation principle, that the closed-loop eigenvalues of the plant plus
compensator are the union (with multiplicity) of the regulator poles det(sI - (A -
B K)) and the estimator poles det(sI - (A - L C)); report the compensator transfer
function G_c(s) = -K (sI
- (A - B K - L C))^-1 L. Produces the two Riccati solutions P and S
with their gains K and L, the compensator state-space realization and transfer
function, and the separation verdict with the closed-loop characteristic
polynomial, in the exact closed forms that gate an output-feedback control design.
Does NOT do: the full-state LQR gain or the Q over R weighting trade as a
standalone deliverable (lqr-design); the discrete-time predict/innovation/correct
recursion, the innovation sequence or single-axis scalar filter runs
(kalman-filter-design); Luenberger pole placement by the Ackermann formula, the
observability rank test, the settling time or the Routh-Hurwitz verdict on
deterministic error dynamics (observer-design); controllability or observability
verdicts, the state transition matrix or canonical forms as analysis ends in
themselves (state-space-analysis); loop-transfer-recovery shaping of the loop
gain. Canonical damped double-integrator family only, scalar input and
position-like measurement; general n-state Riccati solvers and discrete-time LQG
are out of scope.

## Model (implement exactly)

Pure stdlib, math only, deterministic. Canonical plant family (the
worked double integrator of the observer-design sibling with optional
damping a):
- A = [[0, 1], [0, -a]] with damping a >= 0 (a = -A[1][1]);
- input vector B = [0, 1] (scalar force/torque on the second state);
- measured output row C = [1, 0] (y = x1, position-like); (A, C) is
  observable with observability matrix I2.
Unit convention (SI, stated once): x1 a position-like state in m (or
rad), x2 its rate in m/s (or rad/s), u an acceleration-like control,
y the measured position-like state. Q = diag(q1, q2), R = r, Qw =
diag(w1, w2), Rw = rv in the consistent squared units, so both
Riccati equations are dimensionless.
Shared validation (every function raises ValueError): A canonical
[[0, 1], [0, -a]] with a >= 0; B = [0, 1]; C = [1, 0]; Q and Qw
diagonal 2x2 with q1, q2 >= 0, w1 >= 0; R and Rw > 0; w2 > 0 (noise
on the driven state; without it the double integrator has no
stabilizing filter); K and L length-2.

Functions:

- regulator_riccati(A, B, Q, R) -> (P, K)
  The exact scalar reduction of A'P + PA - P B R^-1 B' P + Q = 0 used
  by the lqr-design sibling (valid for any a >= 0):
    p2 = sqrt(r q1)
    p3 = r * (-a + sqrt(a^2 + (2 p2 + q2) / r))
    p1 = a * p2 + p2 * p3 / r
  returns P = [[p1, p2], [p2, p3]] and K = [k1, k2] = [p2 / r,
  p3 / r] with u = -K x.

- filter_riccati(A, C, Qw, Rw) -> (S, L)
  The dual scalar reduction of A S + S A' - S C' Rw^-1 C S + Qw = 0
  (C = [1, 0]):
    s2 = the positive root of the monotone scalar equation
      u^2 + 2 a^2 rv u + 2 a u sqrt(rv (2 u + w1)) - rv w2 = 0,
    exactly sqrt(rv w2) at a = 0, otherwise the unique root on
    (0, sqrt(rv w2)] (left side strictly increasing in u for u >= 0)
    found by bisection to 1e-15 relative;
    s1 = sqrt(rv (2 s2 + w1))
    s3 = a s2 + s1 s2 / rv
  returns S = [[s1, s2], [s2, s3]] and the Kalman gain L = [l1, l2] =
  [s1 / rv, s2 / rv], with error dynamics e' = (A - L C) e. The three
  scalar equations are the (1,1), (1,2) and (2,2) entries of the
  filter ARE written out for the canonical family.

- compensator_realization(A, B, C, K, L) -> (Ac, Bc, Cc, Dc)
  The compensator x_hat' = A x_hat + B u + L (y - C x_hat) with
  u = -K x_hat closes to
    Ac = A - B K - L C = [[-l1, 1], [-k1 - l2, -a - k2]]
    Bc = L = [l1, l2],  Cc = -K = [-k1, -k2],  Dc = 0
  so u = Cc x_hat + Dc y; these four matrices are what flight software
  integrates.

- separation_verdict(A, B, C, K, L) -> dict
  Assembles the (x, x_hat) plant-plus-compensator closed loop
  Acl = [[A, -B K], [L C, A - B K - L C]] (4x4), computes its
  characteristic polynomial by the Faddeev-LeVerrier trace recursion,
  and compares it coefficient by coefficient with the product of the
  regulator polynomial det(sI - (A - B K)) = s^2 + (a + k2) s + k1
  and the estimator polynomial det(sI - (A - L C)) = s^2 + (a + l1)
  s + (a l1 + l2). Returns {"regulator_polynomial": [1, a + k2, k1],
  "estimator_polynomial": [1, a + l1, a l1 + l2],
  "closed_loop_polynomial": [4 coeffs], "product_polynomial":
  [4 coeffs], "max_abs_diff": float, "separated": bool}. The identity
  is exact in real arithmetic (in (x, e = x - x_hat) coordinates Acl
  is block upper triangular with diagonal blocks A - B K and A - L C);
  "separated" is True when max_abs_diff < 1e-9. Both quadratic factors
  have positive coefficients for valid inputs (k1 > 0, a + k2 > 0,
  a l1 + l2 > 0), so a separated verdict implies all four
  closed-loop eigenvalues lie in the open left half plane.

- compensator_transfer_function(Ac, Bc, Cc) -> (num, den)
  G_c(s) = Cc (sI - Ac)^-1 Bc from the 2x2 adjugate: den = [1,
  -tr(Ac), det(Ac)] (monic) and num = -K adj(sI - Ac) L, degree <= 1
  [num_1, num_0] (num_1 = l1 (-k1) + l2 (-k2), num_0 = l1 (-k1
  (-m11) - k2 m10) + l2 (-k1 m01 + k2 m00), m_ij the entries of Ac).

## Identities to test (closed form, exact)

- Regulator ARE residual: max abs entry of A'P + PA - P B R^-1 B' P + Q below 1e-9
  (anchor measured 4.44e-16 in both worked examples).
- Filter ARE residual: max abs entry of A S + S A' - S C' Rw^-1 C S + Qw below
  1e-9 (anchor measured 4.44e-16 and 2.00e-15), which also validates the bisection
  branch of the s2 root at a > 0.
- Closed-form/bisection agreement: at a = 0 the s2 root is exactly sqrt(rv w2);
  the forced bisection branch returns the same value (anchor diff 0).
- Dual symmetry: on the undamped double integrator (a = 0, A symmetric, C = B')
  with matched weights Q = Qw, R = Rw the two Riccati solutions coincide, S = P,
  and the regulator and estimator pole pairs are identical.
- Separation: the Faddeev-LeVerrier polynomial of the assembled 4x4 loop equals
  the product of the two 2x2 polynomials coefficient by coefficient (anchor max
  abs diff 4.44e-16 and 1.78e-15), so the closed-loop eigenvalues are the union,
  with multiplicity, of the regulator and estimator poles, all with negative real
  part.
- Compensator transfer function: den equals s^2 - tr(Ac) s + det(Ac) exactly. The
  compensator's own poles, the eigenvalues of Ac = A - B K - L C, are NOT the
  closed-loop poles (they sit at -1.73205080757 +/- 1.41421356237j in Example A
  below); only the full loop carries the union, which is why the verdict runs on
  the 4x4 assembly.
- ValueErrors across the module: A not canonical, damping a < 0, B not [0, 1], C
  not [1, 0], non-diagonal Q or Qw, q1 or q2 < 0, w1 < 0, w2 <= 0, R <= 0, Rw <=
  0, K or L not length-2.

## Worked example

Canonical double integrator with position measurement, the same "Worked, double
integrator: A = [[0, 1], [0, 0]] (position, velocity) with C = [[1, 0]]" plant the
observer-design leaf works. All values below are REAL outputs of the prep anchor
/tmp/w42spec/anchor_lqg_design.py (stdlib math, closed form, identical on
repeat runs).

Example A, matched weights: a = 0, Q = diag(1, 1), R = 1, Qw = diag(1, 1), Rw = 1.
- Regulator Riccati: P = [[1.73205080757, 1], [1, 1.73205080757]] (sqrt(3) on the
  diagonal), K = [1, 1.73205080757] = [1, sqrt(3)] by the lqr-design equations;
  ARE residual 4.440892e-16.
- Filter Riccati: S = [[1.73205080757, 1], [1, 1.73205080757]], identical to P by
  dual symmetry (matched weights, undamped plant); L = [1.73205080757, 1] =
  [sqrt(3), 1]; s2 = sqrt(rv w2) = 1, the bisection branch returns 1 with diff 0;
  ARE residual 4.440892e-16.
- Pole pairs: regulator closed-loop poles (A - B K) and estimator error poles (A -
  L C) both at -0.866025403784 +/- 0.5j (classic double-integrator LQR pair,
  natural frequency 1 rad/s, damping ratio sqrt(3)/2).
- Compensator: Ac = A - B K - L C = [[-1.73205080757, 1], [-2, -1.73205080757]],
  Bc = L = [1.73205080757, 1], Cc = -K = [-1, -1.73205080757], Dc = 0. Its own
  poles sit at -1.73205080757 +/- 1.41421356237j, NOT the closed-loop poles.
- Separation verdict: closed-loop 4x4 polynomial (Faddeev-LeVerrier) [1,
  3.46410161514, 5, 3.46410161514, 1] equals the product (s^2 + sqrt(3) s + 1)^2
  to max abs diff 4.440892e-16; verdict True. Closed-loop eigenvalues:
  -0.866025403784 +/- 0.5j, each with multiplicity 2 (the union of the pole
  pairs).
- Compensator transfer function: G_c(s) = (-3.46410161514 s - 1) / (s^2 +
  3.46410161514 s + 5); the denominator is s^2 - tr(Ac) s + det(Ac).

Example B, damped plant, distinct tuning (exercises the bisection branch): a =
0.5, Q = diag(2, 1), R = 1, Qw = diag(1, 4), Rw = 1.
- Regulator Riccati: P = [[2.85602070187, 1.41421356237], [1.41421356237,
  1.5195116055]], K = [1.41421356237, 1.5195116055]; regulator poles
  -1.00975580275 +/- 0.628177348514j; ARE residual 4.440892e-16.
- Filter Riccati (s2 by bisection): S = [[1.81799603658, 1.15255479452],
  [1.15255479452, 2.67161744564]], L = [1.81799603658, 1.15255479452]; estimator
  poles -1.15899801829 +/- 0.847511891601j, faster than the regulator pair as the
  heavier process noise (w2 = 4) demands; ARE residual 1.998401e-15 validates the
  bisection branch.
- Separation verdict: closed-loop 4x4 polynomial [1, 4.33750764208, 8.15698627256,
  7.44147126328, 2.91547594742] equals the product of s^2 + 2.0195116055 s +
  1.41421356237 and s^2 + 2.31799603658 s + 2.06155281281 to max abs diff
  1.776357e-15; verdict True. All four eigenvalues have negative real part
  (regulator pair -1.00975580275, estimator pair -1.15899801829), so the
  compensated loop is stable.
- Compensator: Ac = [[-1.81799603658, 1], [-2.56676835689, -2.0195116055]],
  transfer function G_c(s) = (-4.32235503752 s - 2.91547594742) / (s^2 +
  3.83750764208 s + 6.23823245152).

Run your module and take the real outputs as assert targets; the anchors above are
prep-verified, computed by running the prep anchor script
/tmp/w42spec/anchor_lqg_design.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- Example A: P = S = [[1.73205080757, 1], [1, 1.73205080757]] within 1e-6; K = [1,
  1.73205080757] and L = [1.73205080757, 1] within 1e-6; both ARE residuals below
  1e-9; s2 closed form equals the bisection branch within 1e-12.
- Example A poles and separation: regulator and estimator pairs both
  -0.866025403784 +/- 0.5j within 1e-6; closed-loop polynomial [1, 3.46410161514,
  5, 3.46410161514, 1] within 1e-6 of (s^2 + sqrt(3) s + 1)^2; max abs diff below
  1e-9; verdict True.
- Example A compensator: Ac = [[-1.73205080757, 1], [-2, -1.73205080757]] within
  1e-6; transfer numerator [-3.46410161514, -1] and denominator [1, 3.46410161514,
  5] within 1e-6; compensator's own poles -1.73205080757 +/- 1.41421356237j.
- Example B: K = [1.41421356237, 1.5195116055] within 1e-6; regulator poles
  -1.00975580275 +/- 0.628177348514j within 1e-6; L = [1.81799603658,
  1.15255479452] within 1e-6; estimator poles -1.15899801829 +/- 0.847511891601j
  within 1e-6; both ARE residuals below 1e-9.
- Example B separation: closed-loop polynomial [1, 4.33750764208, 8.15698627256,
  7.44147126328, 2.91547594742] within 1e-6; max abs diff below 1e-9; verdict
  True.
- ValueErrors: A with a = -0.1, A = [[0, 1], [1, 0]], B = [1, 0], C = [0, 1], Q
  non-diagonal, q2 = -1, R = 0, w1 = -1, w2 = 0, Rw = -1, K of length 1, L of
  length 3.
- Determinism; no imports beyond math; identical outputs on repeat runs; damping a
  read from A[1][1] (a = 0 is the double integrator of the worked examples).

## Corpus fragment (eval/hit1-wave42-lqg-design.yaml)

Query 1 (copy verbatim):
  "design the linear-quadratic-gaussian compensator for the double integrator: solve the regulator-riccati and the filter-riccati gains, assemble the dynamic output-feedback compensator, verify the separation-principle closed-loop eigenvalues as the union of the regulator and estimator poles"
  intent: "gnc-autonomy; LQG output-feedback compensator from the regulator and filter Riccati gains, separation-principle eigenvalue union"
  expected_skill: "gnc-autonomy/optimal-control/lqg-design"
Query 2 (copy verbatim):
  "lqg controller from the kalman-filter state estimate: compensator state-space realization and transfer function, closed-loop poles as the union of the lqr and the estimator eigenvalues"
  intent: "gnc-autonomy; LQG compensator state-space realization and transfer function, closed-loop poles as union of regulator and estimator eigenvalues"
  expected_skill: "gnc-autonomy/optimal-control/lqg-design"
Task ids: w42-lqg-design-1 and -2. Prep grep: none of the distinctive
phrases (lqg, linear-quadratic-gaussian, loop-transfer recovery,
output-feedback optimal, regulator-riccati, filter-riccati, dynamic
output-feedback compensator) appears in any existing hit1-corpus.yaml
task or in skills/ frontmatter or body (zero-owner grep at prep, 0
files); the lqr task routes on the full-state gain wording, the
observer task on Luenberger observer-gain wording, the kalman task on
innovation-sequence wording, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a linear-quadratic-Gaussian
output-feedback compensator for a two-state system whose state is not fully
measurable:" and include the outputs in the Claim (the two Riccati solutions and
gains, the compensator state-space realization and transfer function, the
separation verdict). First tag: lqg-design. Additional tags ONLY:
linear-quadratic-gaussian, output-feedback-compensator, separation-principle,
filter-riccati-gain, compensator-transfer-function. NEVER single generic words
(lqr, kalman, riccati, gaussian, observer, estimator, compensator, controller,
control, design, optimal, filter, gain, eigenvalue, stability, separation,
transfer, feedback, state, noise). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term (the banned word from the builder kit), action verb
present.

FORBIDDEN TOKENS (belong to siblings): full-state-gain, gain-matrix,
state-feedback, q-over-r-weighting, control-effort, spacecraft-attitude-control,
closed-loop-stability-of-the-regulated-system (lqr-design); discrete-time-filter,
single-axis-estimation, innovation, innovation-variance, predict-update,
measurement-sequence, recursive-least-squares, process-noise-tuning (as a filter
run deliverable) (kalman-filter-design); luenberger, ackermann, pole-placement,
observability-matrix, error-dynamics, settling-time, routh-hurwitz,
hurwitz-verdict, deterministic-observer, characteristic-polynomial-as-standalone
(observer-design); controllability, observability, state-transition-matrix,
canonical-form, eigenvalue-stability-verdict (state-space-analysis);
receding-horizon, prediction-horizon, constraints (model-predictive-control);
time-optimal-switching, bang-bang (bang-bang-control); trajectory-optimization,
collocation, transcription (dymos-trajectory); loop-transfer-recovery (not
implemented in this leaf; the probe greps it as unclaimed, but the canonical
closed-form leaf performs no recovery shaping).
