---
name: loop-transfer-recovery
description: "Use when you must run loop-transfer-recovery on the LQG loop of the two-state plant family: inflate the filter process noise weight q on the driven input channel through Qw(q) = Qw0 + q^2 B B^T, re-solve the filter Riccati equation for the error covariance and the estimator gain at every q, and compare the recovered output loop transfer function with the full-state target loop on a log-spaced frequency grid until the grid-max mismatch M(q) falls at or below the recovery tolerance. Produces the full-state target loop samples, the mismatch-versus-q recovery trace, the recovery gain q* first meeting the tolerance, the recovered filter covariance and estimator gain, and the recovery verdict that gate the loop-shaped LQG design. Trigger: loop-transfer-recovery, LTR, full-state-loop-recovery, lqg-loop-shaping, recovery-gain-tuning, target-feedback-loop."
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
  tags: [loop-transfer-recovery, full-state-loop-recovery, lqg-loop-shaping, recovery-gain-tuning, target-feedback-loop]
  version: 0.1.0
  author: AeroSkills
---

# Loop Transfer Recovery (gnc-autonomy/optimal-control/loop-transfer-recovery)

Use when the task is output-side loop-transfer recovery (LTR) on the LQG
loop of the canonical scalar-input two-state plant family: reshaping the
recovered output loop toward the full-state target loop by inflating the
filter process noise weight on the driven input channel, the Doyle-Stein
1981 recovery construction (textbook treatment Maciejowski, Multivariable
Feedback Design, 1989, chapter 5). This leaf implements the exact closed
forms of both algebraic Riccati equations of the family in pure Python,
stdlib only, and evaluates the loop transfer samples with the builtin
complex type. It pairs with gnc-autonomy/optimal-control/lqg-design,
which consumes the recovered estimator gain L(q*) as the filter gain
input of its compensator assembly, and with
gnc-autonomy/optimal-control/lqr-design, which owns the regulator gain
design trade this leaf treats as a fixed full-state target ingredient.
The adjacent gnc-autonomy/control/frequency-response-design leaf measures
the margins of a given open loop transfer function and never synthesizes
or recovers a loop; here the loop-shape match is judged by the grid-max
complex mismatch M(q), never by margin numbers.

## Domain quick reference

- Plant family: A = [[0, 1], [0, -a]] with damping a >= 0 (a = -A[1][1]),
  input B = [0, 1] (acceleration-like control on the rate state) and
  measured output C = [1, 0] (y = x1, position-like). Unit convention:
  x1 in m (or rad), x2 in m/s (or rad/s), u in m/s^2 (or rad/s^2), omega
  in rad/s, q dimensionless; the weights Q = diag(q1, q2), R = r,
  Qw = diag(w1, w2) and Rw = rv sit in the consistent squared units.
  Plant transfer G(s) = C (sI - A)^-1 B = 1 / (s (s + a)).
- Regulator algebraic Riccati equation: A'P + PA - P B R^-1 B' P + Q = 0.
  With P = [[p1, p2], [p2, p3]] the exact scalar reduction shared with
  the lqr-design and lqg-design siblings is p2 = sqrt(r q1),
  p3 = r (-a + sqrt(a^2 + (2 p2 + q2) / r)) and p1 = a p2 + p2 p3 / r;
  the full-state gain for u = -K x is K = [p2 / r, p3 / r].
- Filter (Kalman) algebraic Riccati equation: A S + S A' - S C' Rw^-1 C S +
  Qw = 0. Its entries: s2 is the root of u^2 + 2 a^2 rv u + 2 a u
  sqrt(rv (2 u + w1)) - rv w2 = 0 on (0, sqrt(rv w2)], exactly
  sqrt(rv w2) at a = 0 and bisection to 1e-15 relative otherwise, then
  s1 = sqrt(rv (2 s2 + w1)) and s3 = a s2 + s1 s2 / rv; S = [[s1, s2],
  [s2, s3]] and the estimator gain L = [s1 / rv, s2 / rv].
- Recovery inflation: Qw(q) = Qw0 + q^2 B B^T touches only the (2,2)
  entry because B B^T = [[0, 0], [0, 1]], so w2(q) = w2 + q^2: the
  fictitious noise on the driven state grows with the SQUARE of q.
- Target loop (the full-state loop at the plant output, SISO-identical to
  the input break): L_t(s) = K (sI - A)^-1 B, family closed form
  (k1 + k2 s) / (s (s + a)).
- Recovered output loop of the LQG structure with filter gain L(q):
  L_lqg(s; q) = G(s) K (sI - A + BK + L(q)C)^-1 L(q). The 2x2 matrix
  path inverts [[s + l1, -1], [k1 + l2, s + a + k2]] by its adjugate; the
  family rational closed form is K Phi_o L = num / den with
  num = (k1 l1 + k2 l2) s + k1 (a l1 + l2) and
  den = s^2 + (l1 + a + k2) s + (a + k2) l1 + k1 + l2.
- Frequency grid: N_FREQ log-spaced points w_k from OMEGA_MIN to
  OMEGA_MAX, w_k = OMEGA_MIN * exp(ln(OMEGA_MAX / OMEGA_MIN) * k /
  (N_FREQ - 1)) for k = 0 .. N_FREQ - 1.
- Mismatch metrics at q (denominator the grid-max target magnitude):
  M(q) = max_k |L_lqg(j w_k; q) - L_t(j w_k)| / max_k |L_t(j w_k)| and
  Mmag(q) = max_k ||L_lqg(j w_k; q)| - |L_t(j w_k)|| / max_k |L_t(j w_k)|.
- Recovery rule: q* is the FIRST q of the geometric sweep q_min,
  q_min * step, ... (inclusive up to q_max) with M(q) <= tol; without a
  meeting point the verdict is False and q* is None. The trace strictly
  decreases in M over the sweep for the minimum-phase canonical family.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the Riccati and recovery mathematics is common control-theory
  knowledge, summary only.

## Workflow

1. Fix the plant and the weights: canonical family damping a, regulator
   weights Q = diag(q1, q2) and R = r, nominal filter noise covariances
   Qw0 = diag(w1, w2) and Rw = rv, and the frequency band; build the
   log-spaced frequency grid with frequency_grid(omega_min, omega_max,
   n_freq).
2. Solve the regulator Riccati equation for the full-state target
   ingredient with regulator_riccati(a, q1, q2, r): returns the symmetric
   P and the gain K = [k1, k2] for u = -K x.
3. Form the full-state target loop samples with target_loop(j w, a, K)
   over the grid and read off the grid-max target magnitude; the target
   band sits around the unity-magnitude crossing w_c.
4. Solve the nominal filter Riccati equation with filter_riccati(a, w1,
   w2, rv) for the error covariance S0 and the estimator gain L0 (the s2
   root is closed form sqrt(rv w2) at a = 0 and bisection at a > 0), and
   measure the nominal LQG loop mismatch at q = 0 with loop_mismatch(0,
   a, K, grid): the estimator lag and roll-off bend the loop far from the
   target.
5. Run the recovery gain sweep with recovery_sweep(a, K, grid, tol,
   q_min, q_max, step): at every q, inflate the filter process noise
   weight on the driven input channel through inflated_noise_covariance
   (q), re-solve the filter Riccati equation for S(q) and L(q), evaluate
   the recovered output loop with recovered_loop(j w, a, K, L) against
   the target samples, and record (q, M(q), Mmag(q), l1, l2).
6. Read off the recovery gain q* and the recovery verdict from
   recovery_result(...): q* first meeting the tolerance, the recovered
   filter covariance S(q*) and estimator gain L(q*), the mismatch values
   at q* and the improvement ratio over the nominal loop.
7. Confirm the deterministic checks with the contract test
   scripts/test_loop_transfer_recovery.py (stdlib-only, offline, runs
   under both /usr/bin/python3 and the pyenv 3.13.12 interpreter).

## Worked example

Worked scenario: the canonical undamped double-integrator plant a = 0
with the matched weights of the pack (the lqg-design Example A weights):
Q = diag(1, 1), R = 1, Qw0 = diag(1, 1), Rw = 1. The frequency grid
holds 41 log-spaced points over [0.1, 20] rad/s, the full-state target
loop crosses unity magnitude at w_c = 1.8173540210239707 rad/s, and the
recovery sweep runs q = 10, 100, ..., 1e8 (8 points) with the gate
RECOVERY_TOL = 1e-3. All values below are real module outputs
(scripts/loop_transfer_recovery_logic.py), bitwise identical under both
interpreters and inside the spec magnitude bounds.

- Target design (the fixed full-state ingredient): regulator ARE
  P = [[1.7320508075688772, 1], [1, 1.7320508075688772]] (= sqrt(3) on
  the diagonal), K = [1, 1.7320508075688772] = [1, sqrt(3)], ARE
  residual 4.441e-16. Target samples L_t(j w) = -(1/w^2) - j sqrt(3)/w
  with grid-max magnitude 101.48891565092218 at w = 0.1 rad/s.
- Nominal LQG loop before recovery (q = 0): S0 = P, L0 =
  [1.7320508075688772, 1] = [sqrt(3), 1]; its loop transfer is
  L_lqg(s; 0) = (1 + 2 sqrt(3) s) / (s^2 (s^2 + 2 sqrt(3) s + 5)), and
  M(0) = 0.79265793913710081, Mmag(0) = 0.79152889018535089: the nominal
  output loop is off the full-state loop by up to 79% of the target peak.
- Recovery trace (q, M(q), Mmag(q), L(q) = [l1, l2]) over the sweep:

  q = 10: M = 0.46672494862660469, Mmag = 0.46665926627057602, L =
  [4.5934465537591462, 10.04987562112089]
  q = 100: M = 0.20156746815359272, Mmag = 0.20156524575736853, L =
  [14.177799538363226, 100.00499987500625]
  q = 1000: M = 0.072062021956610434, Mmag = 0.072062015642601701, L =
  [44.732549670231741, 1000.000499999875]
  q = 1e4: M = 0.023772073268366271, Mmag = 0.023772060968471405, L =
  [141.42489208056693, 10000.000050000001]
  q = 1e5: M = 0.0076215835906494403, Mmag = 0.0076215752257677788, L =
  [447.21471354372943, 100000.00000499999]
  q = 1e6: M = 0.0024207706165423701, Mmag = 0.0024207674026657765, L =
  [1414.2139159267949, 1000000.0000005]
  q = 1e7: M = 0.00076658259948715081, Mmag = 0.0007665815223384054, L =
  [4472.1360668029884, 10000000.00000005]
  q = 1e8: M = 0.0002425216736106494, Mmag = 0.00024252132677611768, L =
  [14142.135659086289, 100000000]

  M(q) strictly decreases over the sweep and the complex and
  magnitude-only mismatches track to five digits at every q: recovery
  reshapes magnitude and phase together. The late-decay ratio
  M(1e8)/M(1e7) = 0.316367 sits within 0.02 of 1/sqrt(10): the
  M ~ c / sqrt(q) law of the recovery error.
- Recovery verdict: q* = 10000000.0 (first sweep q with M(q) <= 1e-3),
  M(q*) = 0.00076658259948715081, Mmag(q*) = 0.0007665815223384054, so
  the recovered output loop matches the full-state target loop to better
  than 7.7e-4 of the peak magnitude across the whole grid; the
  improvement over the nominal LQG loop is M(0)/M(q*) = 1034.015. At q*
  the filter solution is S(q*) = [[4472.1360668029884,
  10000000.00000005], [10000000.00000005, 44721360668.030106]] with
  L(q*) = [4472.1360668029884, 10000000.00000005]; the inflation law is
  w2(q*) = 1 + 1e14, and l2(q*) = sqrt(1 + q^2), l1(q*) =
  sqrt(2 l2(q*) + 1) exactly. The filter ARE residual at q* is 3.725e-09
  (max entry), tiny against entries of order q^2. The price of recovery
  is estimator speed: the filter characteristic polynomial s^2 + l1 s +
  l2 has roots of magnitude (1 + q^2)^(1/4) = 3162.28 rad/s at q*, about
  1740 times the target crossing, the standard LTR noise-bandwidth trade.
- Recovered loop against target at q*: at w = 0.1 rad/s |L_lqg| =
  101.41111612 against |L_t| = 101.48891565092218 (nominal 21.157506880);
  at w = 1.0, |L_lqg| = 1.9988388170 (nominal 0.68138514387); at w = 20,
  |L_lqg| = 0.086593884562 (nominal 0.00043194562704). Complex agreement
  at w = 1.0: L_lqg(q*) = -0.99999970038576613 - 1.7307100322379296j
  against L_t = -1 - 1.7320508075688772j.
- Damped cross-checks: filter_riccati(0.5, 1.0, 4.0, 1.0) reproduces the
  lqg-design Example B solution (the a > 0 bisection branch). On the
  damped plant a = 0.5 with the matched weights, K = [1,
  1.3027756377319946], and M(0) = 7.1197214039e-01 drops to M(1e5) =
  5.7834333689e-03: recovery through the bisection branch reduces the
  mismatch by a factor of 123.
- Determinism: a second identical recovery_result run is bitwise
  identical in the trace, q_star, S_star and L_star. ValueErrors: 12
  exercised rejection cases all raise (negative damping, zero or negative
  weights, negative q, degenerate frequency bands and sweep bounds).

## Verification

- Confirm the worked scenario: recovery_result() returns q_star = 1e7
  within 1e-12, M(q*) and Mmag(q*) within 1e-6 relative, S(q*) and L(q*)
  within 1e-6 relative per entry, improvement ratio 1034.02 within 1e-3
  relative and verdict True.
- Confirm the grid: 41 log-spaced points over [0.1, 20] rad/s with
  w_0 = 0.1, w_40 = 20 within 1e-12 and the consecutive-point ratio equal
  to (20/0.1)^(1/40) within 1e-12.
- Confirm the identities: the target loop matrix path equals -(1/w^2) -
  j sqrt(3)/w at every grid point within 1e-12 (anchor max abs diff
  3.553e-15); the recovered loop matrix path equals num / (s^2 den)
  within 1e-9 (anchor 9.379e-13 at q = 1000); the two SISO multiplication
  orders of the matrix path agree bitwise; |L_t(j w_c)| = 1 within 1e-9.
- Confirm the residuals: regulator ARE residual 4.441e-16 at the worked
  weights, filter ARE residual 4.441e-16 at q = 0 and 3.725e-09 at
  q* = 1e7, all below the 1e-8 max-entry gate.
- Confirm every non-physical input raises ValueError: a < 0, q1 < 0,
  q2 < 0, r <= 0, w1 < 0, w2 <= 0, rv <= 0, q < 0, omega_min <= 0,
  omega_max <= omega_min, n_freq < 2, q_min <= 0, q_max < q_min,
  step <= 1, tol <= 0, and any non-finite parameter.
- Run the contract test offline under both interpreters:
  python3 scripts/test_loop_transfer_recovery.py (31 tests,
  deterministic, stdlib only).

## Related leaves

- gnc-autonomy/optimal-control/lqg-design: the compensator assembly that
  consumes this leaf's recovered estimator gain L(q*) as its filter gain
  input; its Pitfalls section declares loop-gain shaping toward
  full-state recovery unimplemented, the gap this leaf closes.
- gnc-autonomy/optimal-control/lqr-design: owns the regulator gain design
  trade; the K used here is the fixed full-state target ingredient, with
  no weighting trade product.
- gnc-autonomy/control/frequency-response-design: measures the margins of
  polynomial open loop transfer functions; this leaf evaluates loop
  transfer samples only to compare loop shapes and reports no margin
  numbers.
- gnc-autonomy/navigation/kalman-filter-design: discrete-time scalar
  filter runs over sampled measurement streams; the recovery loop here is
  continuous-time over the two-state family.
- gnc-autonomy/optimal-control/bang-bang-control,
  model-predictive-control, ilqr-ddp and dymos-trajectory: the
  time-domain and transcription alternatives; recovery runs no iteration
  or trajectory optimization.

## Pitfalls

- Judging the match by margin numbers: the LTR loop-shape comparison is
  the grid-max complex mismatch M(q), never a gain or phase margin of the
  recovered loop; margin measurement is the adjacent control leaf's
  product.
- Reporting the nominal loop as the deliverable: q = 0 (the lqg-design
  Example A filter) leaves the output loop up to 79% of the target peak
  off the full-state loop; only the recovered q* loop meets the tolerance
  gate.
- Forgetting that the inflation is quadratic: the fictitious process
  noise grows as q^2, so l2(q) = sqrt(w2 + q^2) and the estimator roots
  sit at magnitude (w2 + q^2)^(1/4); sweeping q linearly moves the filter
  bandwidth by the square root only.
- Expecting full recovery on non-minimum-phase plants: the canonical
  family is SISO and minimum phase, so M(q) -> 0 as q -> infinity; a
  plant with right-half-plane zeros or a multivariable input breaks the
  guarantee, and input-side recovery is out of scope.
- Assuming the module designs the regulator or assembles the compensator:
  recovery_result returns the recovery verdict and the recovered filter
  gain, not a gain-design product with a weighting trade, and not a
  compensator realization or a separation verdict, which the lqg-design
  sibling owns.
- Accepting negative weights or nonpositive covariances; the shared
  validation raises ValueError on every non-physical input, including the
  w2 = 0 case that leaves the double integrator without a stabilizing
  filter.
- Recomputing the nominal loop as the target: the target is the full-state
  loop K (sI - A)^-1 B, not the q = 0 output loop of the LQG structure.

## Behavior contract (gate 3)

The grid construction, both Riccati solves, the target and recovered loop
evaluations, the mismatch metrics and the recovery verdict are exercised
by the gate 3 contract test: scripts/test_loop_transfer_recovery.py
against scripts/loop_transfer_recovery_logic.py (stdlib unittest,
offline, deterministic). Run:

python3 scripts/test_loop_transfer_recovery.py

The test covers the worked-scenario anchors within 1e-6 relative per
entry, the grid log-spacing identity, the target and recovered loop
matrix-versus-closed-form identities, the two SISO multiplication orders,
the ARE residuals below 1e-8 at the worked weights, at q = 0 and at
q* = 1e7, the recovery decay law, the damped-plant recovery through the
bisection branch, the cross-sibling filter identity with the lqg-design
Example B anchors within 1e-12, bitwise determinism on repeat runs,
stdlib-only imports, and ValueError rejection of every non-physical input
listed in Verification.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
