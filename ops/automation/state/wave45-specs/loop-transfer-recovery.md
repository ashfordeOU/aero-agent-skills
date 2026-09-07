# Wave-45 leaf spec: loop-transfer-recovery (gnc-autonomy, optimal-control pack)

- Path: skills/gnc-autonomy/optimal-control/loop-transfer-recovery/
- Pack: optimal-control (present siblings bang-bang-control,
  dymos-trajectory, ilqr-ddp, lqg-design, lqr-design,
  model-predictive-control; adjacent fences in
  gnc-autonomy/control/frequency-response-design, which measures
  open-loop margins of polynomial transfer functions and never
  synthesizes or recovers a loop, and gnc-autonomy/navigation/
  kalman-filter-design, which owns discrete-time scalar filter runs
  over sampled measurement streams; wave-45 whole-family probe task-6
  GO 1 at HEAD 5cc8fef3).
- Claim fences (quoted from the sibling frontmatter and body at prep;
  none of them inflates the filter noise weight to reshape the output
  loop gain toward the full-state target loop):
  - lqg-design (this pack) is the nearest owner and its own Pitfalls
    section leaves the seam open, receipt quote, lines 201-204:
    "Carrying the leaf outside its family: general n-state Riccati
    solvers, discrete-time LQG over sampled measurement streams is
    out of scope here (see kalman-filter-design), and shaping the
    loop gain toward full-state recovery is not implemented in this
    leaf." Its frontmatter (fresh verified) claims the single-shot
    synthesis: "solve the regulator algebraic Riccati equation for
    the symmetric stabilizing P and the gain K ... solve the filter
    (Kalman) algebraic Riccati equation for the error covariance S
    and the estimator gain L ... assemble the dynamic
    output-feedback compensator state-space realization, and verify
    the separation principle ... Produces the two Riccati solutions
    with their gains, the compensator matrices and transfer
    function, and the separation verdict." One fixed noise
    covariance, one compensator, no q sweep, no loop-shape
    comparison; the loop-gain recovery loop is exactly the gap.
  - lqr-design (this pack) OWNS the regulator gain design for the
    family: its frontmatter reads "design an LQR state-feedback gain
    matrix ... solve the algebraic Riccati equation ... compute the
    gain matrix, verify closed-loop stability of the regulated
    system, and assess the Q over R weighting trade. Produces the
    Riccati solution, the gain vector, and the stability verdict".
    This leaf solves the same family regulator ARE only as the fixed
    full-state target ingredient of the recovery loop; it produces no
    gain-design deliverable, no stability verdict and no weighting
    trade.
  - frequency-response-design (control pack, adjacent fence) OWNS
    margin measurement: its frontmatter claims "bode analysis,
    frequency response, gain crossover, phase crossover, gain
    margin, phase margin, or stability from the margins" for the
    canonical type-1 plant K/(s(s+1)(s+2)), and its body states
    (fresh verified): "this leaf only measures the margins of the
    given open loop transfer function and does not synthesize
    compensators". The LTR leaf evaluates loop transfer function
    samples to compare loop SHAPES; it computes no gain margin, no
    phase margin, no crossover frequency and no stability-from-
    margins verdict.
  Whole-tree greps at prep (receipt gate (a), re-verified at spec
  prep): 'loop[- ]transfer[- ]recovery|ltr design' -> 0 hits across
  all 623 skills/ SKILL.md files, 0 frontmatter owners, 0 body
  mentions; the five leaf tags below return ZERO hits in
  eval/hit1-corpus.yaml, in every wave44-specs and wave45-specs file
  written so far (grep count 0 per token). GENUINE gnc-autonomy gap
  (receipt task-6 GO 1): lqg-design's own Pitfalls sentence declares
  loop-gain shaping toward full-state recovery unimplemented, and no
  leaf in any family runs a recovery search over an inflated filter
  noise weight against a full-state target loop.
- Standards id: arp4754a (grep-verified at spec prep: standards-map
  .yaml line 38 "  - id: arp4754a"; SAE ARP4754A is proprietary,
  name + paraphrase only, never reproduced, the same reference-only
  convention every optimal-control sibling uses). Ledger Standard:
  arp4754a.
- Family: gnc-autonomy

## Claim

Run output-side loop-transfer-recovery (LTR) on the LQG loop of the
canonical scalar-input two-state plant family of the pack, A =
[[0, 1], [0, -a]] with damping a >= 0, B = [0, 1], C = [1, 0]
(measured output y = x1, position-like): the leaf takes the
full-state regulator gain K from the family regulator algebraic
Riccati equation, forms the full-state target loop L_t(s) = K
(sI - A)^-1 B (the loop broken at the plant output, equal to the
input break for this SISO family), then searches over the recovery
gain q: at every q it inflates the filter process-noise covariance in
the driven-input direction, Qw(q) = Qw0 + q^2 B B^T (only the (2,2)
entry w2(q) = w2 + q^2 changes for B = [0, 1]), re-solves the family
filter algebraic Riccati equation for the error covariance S(q) and
the estimator gain L(q), and evaluates the recovered output loop
L_lqg(s; q) = G(s) K (sI - A + BK + L(q)C)^-1 L(q) against L_t(s)
over a log-spaced frequency grid, until the grid-max complex
mismatch M(q) = max_k |L_lqg(j w_k; q) - L_t(j w_k)| / max_k
|L_t(j w_k)| first falls at or below the recovery tolerance (the
Doyle-Stein 1981 recovery construction, textbook treatment
Maciejowski, Multivariable Feedback Design, 1989, chapter 5:
fictitious process noise on the driven channel makes the estimator
fast in the input directions and the recovered output loop converge
pointwise to the full-state loop). Produces, in SI units, the
full-state target loop samples L_t(j w_k) with the grid-max target
magnitude, the nominal (q = 0) LQG loop mismatch, the recovery trace
of (q, M(q), magnitude-only mismatch Mmag(q), L(q)) over the
geometric sweep, the recovery gain q* = smallest sweep q with
M(q*) <= tol together with the recovered filter covariance S(q*) and
estimator gain L(q*), and the recovery verdict that gates the
loop-shaped LQG design. Deterministic, offline, stdlib math only:
the two-ARE closed forms of the family plus 2x2 complex adjugate
evaluations at the 41 grid points, no numpy, no scipy, no RNG, no
external processes. Does NOT do: the single-shot linear-quadratic-
Gaussian compensator assembly, its transfer function or the
separation-principle verdict (lqg-design, which consumes this leaf's
recovered L(q*) as its filter gain input); a regulator gain-design
product with a stability verdict or a Q over R weighting trade
(lqr-design, the K here is the fixed full-state target ingredient);
gain margin, phase margin, crossover frequencies or a stability-from-
margins verdict on any loop (frequency-response-design; the leaf
reports loop transfer samples and mismatch metrics only); general
n-state Riccati solvers or discrete-time LQG over sampled
measurement streams (kalman-filter-design and the lqg-design fence);
input-side recovery for a multivariable plant or recovery for a plant
with right-half-plane zeros (the canonical family is SISO and
minimum phase, its output loop recovers completely as q -> infinity);
iteration, rollout or trajectory optimization of any kind (ilqr-ddp,
model-predictive-control, bang-bang-control); Dymos or pseudospectral
transcription (dymos-trajectory). The loop-shape match is judged by
the grid-max complex mismatch M(q), never by margins.

## Model (implement exactly)

Pure stdlib, math only plus the builtin complex type (no import
needed for complex arithmetic). No numpy, no scipy, no RNG, no
external processes. Deterministic: plain explicit arithmetic in the
pinned order below, no generator-sum float reassociation, explicit
accumulation order in every max. Module name loop_transfer_recovery.

Module constants (pin exactly; the worked scenario):
- DAMP_A = 0.0 (plant damping a, the value of -A[1][1]),
  Q1 = 1.0, Q2 = 1.0 (regulator state weights on x1, x2),
  R_W = 1.0 (regulator control weight), W1 = 1.0, W2 = 1.0 (nominal
  filter process-noise weights on x1, x2), RV = 1.0 (measurement
  noise covariance).
- OMEGA_MIN = 0.1 (rad/s), OMEGA_MAX = 20.0 (rad/s), N_FREQ = 41
  (log-spaced frequency grid points).
- RECOVERY_TOL = 1e-3 (grid-max mismatch gate), Q_MIN = 10.0,
  Q_MAX = 1e8, Q_STEP = 10.0 (geometric recovery sweep).
- B = [0.0, 1.0] (input vector of the canonical family; B B^T =
  [[0, 0], [0, 1]], so the inflation touches w2 only).

Defining relations (pin exactly; every function derives from these;
x1 in m or rad, x2 in m/s or rad/s, u in m/s^2 or rad/s^2, omega in
rad/s, q dimensionless):
- Plant: x' = A x + B u, y = C x with A = [[0, 1], [0, -a]],
  B = [0, 1], C = [1, 0]; plant transfer G(s) = C (sI - A)^-1 B =
  1 / (s (s + a)).
- Regulator ARE: A'P + PA - P B R^-1 B' P + Q = 0 with the family
  scalar reduction p2 = sqrt(r q1), p3 = r (-a + sqrt(a^2 +
  (2 p2 + q2) / r)), p1 = a p2 + p2 p3 / r; the gain is
  K = [p2 / r, p3 / r] for u = -K x. Residual check:
  A'P + PA - P B R^-1 B' P + Q = 0 entrywise.
- Filter (Kalman) ARE: A S + S A' - S C' Rw^-1 C S + Qw = 0. Its
  entries: s2 is the root of u^2 + 2 a^2 rv u + 2 a u sqrt(rv (2u +
  w1)) - rv w2 = 0 on (0, sqrt(rv w2)] (exactly sqrt(rv w2) at
  a = 0; otherwise bisection to 1e-15 relative), then s1 =
  sqrt(rv (2 s2 + w1)) and s3 = a s2 + s1 s2 / rv; S = [[s1, s2],
  [s2, s3]] and the estimator gain L = [s1 / rv, s2 / rv] of
  xhat' = A xhat + B u + L (y - C xhat). Residual check:
  A S + S A' - S C' Rw^-1 C S + Qw = 0 entrywise.
- Recovery inflation: Qw(q) = Qw0 + q^2 B B^T, i.e. w2(q) = w2 +
  q^2; the fictitious noise on the driven state grows with the
  SQUARE of q.
- Target loop (full-state loop at the plant output, SISO-identical
  to the input break): L_t(s) = K (sI - A)^-1 B, family closed form
  (k1 + k2 s) / (s (s + a)).
- Recovered output loop of the LQG structure with filter gain L(q):
  L_lqg(s; q) = G(s) K (sI - A + BK + L(q)C)^-1 L(q). For the
  family, K (sI - A + BK + LC)^-1 L = num / den with num = (k1 l1 +
  k2 l2) s + k1 (a l1 + l2) and den = s^2 + (l1 + a + k2) s + (a +
  k2) l1 + k1 + l2, both closed forms computed against the 2x2
  complex matrix path (adjugate inverse of [[s + l1, -1], [k1 + l2,
  s + a + k2]]). The SISO loop equals G(s) times K Phi_o(s) L in
  either multiplication order (complex scalars commute; the two
  orders agree bitwise).
- Frequency grid: N_FREQ log-spaced points w_k from OMEGA_MIN to
  OMEGA_MAX, w_k = OMEGA_MIN * exp(ln(OMEGA_MAX / OMEGA_MIN) * k /
  (N_FREQ - 1)) for k = 0 .. N_FREQ - 1.
- Mismatch metrics at q (denominator the grid-max target magnitude):
  M(q) = max_k |L_lqg(j w_k; q) - L_t(j w_k)| / max_k |L_t(j w_k)|,
  Mmag(q) = max_k ||L_lqg(j w_k; q)| - |L_t(j w_k)|| / max_k
  |L_t(j w_k)|.
- Recovery rule: q* is the FIRST q of the geometric sweep q_min,
  q_min * step, ... (inclusive up to q_max) with M(q) <= tol; if no
  sweep point meets the gate the verdict is False and q* is None.
  The trace is strictly decreasing in M over the sweep for the
  minimum-phase canonical family.

Functions (public API, 10; every numeric parameter validated before
use; no imports beyond math):
- frequency_grid(omega_min=OMEGA_MIN, omega_max=OMEGA_MAX,
  n_freq=N_FREQ) -> list of n_freq floats, log-spaced as pinned.
  ValueError if any input non-finite, omega_min <= 0,
  omega_max <= omega_min, or n_freq < 2.
- regulator_riccati(a, q1, q2, r) -> (P, K), P = [[p1, p2],
  [p2, p3]], K = [k1, k2]. ValueError if a < 0, q1 < 0, q2 < 0,
  r <= 0, or any input non-finite.
- s2_root(a, w1, w2, rv) -> float s2: sqrt(rv w2) at a = 0,
  otherwise the bisection root of the monotone equation to 1e-15
  relative on (0, sqrt(rv w2)] (the lqg-design family machinery).
  Same ValueErrors as filter_riccati.
- filter_riccati(a, w1, w2, rv) -> (S, L), S = [[s1, s2], [s2,
  s3]], L = [l1, l2] as pinned. ValueError if a < 0, w1 < 0,
  w2 <= 0, rv <= 0, or any input non-finite.
- inflated_noise_covariance(q) -> float W2 + q^2 (the module's
  driven-state nominal plus the squared recovery gain). ValueError
  if q non-finite or q < 0.
- target_loop(s, a, K) -> complex L_t(s) by the 2x2 matrix path
  (adjugate inverse of [[s, -1], [0, s + a]]). No validation: pure
  evaluation.
- recovered_loop(s, a, K, L) -> complex L_lqg(s; q) by the 2x2
  matrix path: g = 1/(s (s + a)), phi_o the adjugate inverse of
  [[s + l1, -1], [k1 + l2, s + a + k2]], then g times (k1 *
  (phi_o[0][0] l1 + phi_o[0][1] l2) + k2 * (phi_o[1][0] l1 +
  phi_o[1][1] l2)). No validation: pure evaluation.
- loop_mismatch(q, a, K, grid) -> (M, Mmag, L, S, max_t): solves
  the filter ARE at w2(q) = inflated_noise_covariance(q) with the
  module's W1 and RV and returns the two metrics, the gain, the
  covariance and the grid-max target magnitude. ValueError if q
  invalid (delegated to inflated_noise_covariance and
  filter_riccati).
- recovery_sweep(a, K, grid, tol=RECOVERY_TOL, q_min=Q_MIN,
  q_max=Q_MAX, step=Q_STEP) -> (trace, q_star): trace is the list of
  (q, M(q), Mmag(q), l1, l2) over the sweep in sweep order, q_star
  the first trace q with M(q) <= tol or None. ValueError if
  q_min <= 0, q_max < q_min, step <= 1, tol <= 0, or any of the
  sweep bounds non-finite.
- recovery_result(a=DAMP_A, q1=Q1, q2=Q2, r=R_W, w1=W1, w2=W2,
  rv=RV, tol=RECOVERY_TOL, q_min=Q_MIN, q_max=Q_MAX) -> result dict
  with keys a, q1, q2, r, w1, w2, rv, grid, P, K, S0, L0,
  max_target (grid-max |L_t|), target_samples (list of (w_k,
  L_t(j w_k))), mismatch_nominal (M at q = 0), trace (the
  recovery_sweep trace), q_star, verdict (bool: q_star is not None),
  S_star, L_star (the filter solution at q*; None when q_star is
  None), m_star, mmag_star, improvement_ratio (mismatch_nominal /
  m_star). ValueError for any invalid weight or sweep parameter as
  listed per function; the driver validates q_min <= q_max before
  sweeping.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- Worked-scenario closed forms: with a = 0, Q = diag(1, 1), R = 1
  the regulator ARE gives P = [[sqrt(3), 1], [1, sqrt(3)]] and
  K = [1, sqrt(3)]; the nominal filter ARE (w2 = 1) gives S0 = P and
  L0 = [sqrt(3), 1], and both ARE residuals are 4.441e-16 (real
  anchor).
- Target loop closed form: L_t(j w) = -(1/w^2) - j sqrt(3)/w for the
  worked scenario (from (k1 + k2 s)/(s^2) at s = j w); the 2x2
  matrix path matches the closed form at every grid point to max abs
  diff 3.553e-15 over the grid (real anchor; the worked-example
  complex samples below are the matrix-path outputs).
- Unity-magnitude crossing of the target loop: |L_t(j w_c)| = 1 at
  w_c = sqrt((3 + sqrt(13))/2) = 1.8173540210239707 rad/s (abs err
  1.110e-16, real anchor): the frequency band context of the grid.
- Recovered-loop closed form: at every grid point and any q of the
  worked scenario (a = 0, so G(s) = 1/s^2) the 2x2 matrix loop
  equals the family rational expression L_lqg = num / (s^2 den)
  with num and den as pinned, to max abs diff 9.379e-13 at q = 1000
  over the worked grid (real anchor); the two SISO multiplication
  orders of the matrix path agree bitwise (max abs diff 0.000e+00).
- Recovery convergence: M(q) strictly decreases over the worked
  sweep and the late-decay ratio M(1e8)/M(1e7) = 0.316367 sits
  within 0.02 of 1/sqrt(10) = 0.316228 (the M ~ c / sqrt(q) law of
  the recovery error); M(q) * sqrt(q) over the last four sweep
  points reads 2.410156, 2.420771, 2.424147, 2.425217 (trending to
  a constant near 2.42).
- Damped-plant cross-sibling identity: filter_riccati(0.5, 1.0,
  4.0, 1.0) reproduces the lqg-design Example B solution within 1e-12
  (S = [[1.8179960365836825, 1.1525547945169889], [1.1525547945169889,
  2.671617445635901]], L = [1.8179960365836825, 1.1525547945169889];
  real anchor, exercises the a > 0 bisection branch).
- Damped recovery works: with a = 0.5 and the matched weights of
  the worked scenario, M(0) = 7.1197214039e-01 drops to M(1e5) =
  5.7834333689e-03, ratio 8.123118e-03 (real anchor): the damped
  minimum-phase plant recovers too, through the bisection branch.
- ARE residual checks: regulator residual 4.441e-16 at the worked
  weights and filter residual 4.441e-16 at q = 0, both max-entry
  (real anchor); the filter residual at q* = 1e7 is 3.725e-09, tiny
  relative to the solution entries ~1e7 and ~4.5e10.
- Determinism: two identical recovery_result runs are bitwise
  identical in the trace, q_star, S_star and L_star (real anchor
  True).
- ValueErrors across the module: regulator_riccati at a = -0.1 and
  r = 0; filter_riccati at w1 = -1, w2 = 0 and rv = -1;
  inflated_noise_covariance at q = -1; frequency_grid at
  omega_min = 0, n_freq = 1 and omega_max <= omega_min;
  recovery_sweep at q_min = 0 and q_max < q_min (12 exercised cases
  in the anchor run, all raising).
- Determinism; no imports beyond math; no RNG anywhere.

## Worked example

Scenario (all values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_loop_transfer_recovery.py, stdlib math, exit 0,
all checks passed, output bitwise identical under /usr/bin/python3
3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3): the canonical
undamped double-integrator plant a = 0 with the matched weights of
the pack (the lqg-design Example A weights): Q = diag(1, 1), R = 1,
Qw0 = diag(1, 1), Rw = 1. The frequency grid holds 41 log-spaced
points over [0.1, 20] rad/s; the full-state target loop crosses
unity magnitude at w_c = 1.8173540210239707 rad/s, so the band spans
about a decade below and a decade above the crossing. The recovery
sweep runs q = 10, 100, ..., 1e8 (8 points) and the gate is
RECOVERY_TOL = 1e-3.

- Target design (the fixed full-state ingredient): regulator ARE
  P = [[1.7320508075688772, 1], [1, 1.7320508075688772]] (= sqrt(3)
  on the diagonal) and K = [1, 1.7320508075688772] = [1, sqrt(3)];
  the target loop samples L_t(j w) = -(1/w^2) - j sqrt(3)/w with
  grid-max magnitude max_k |L_t(j w_k)| = 101.48891565092218 (at
  w = 0.1 rad/s). Target complex samples: at w = 0.1, L_t =
  -99.999999999999986 - 17.320508075688767j; at w = 1.0, L_t =
  -1 - 1.7320508075688772j; at w = 1.8, L_t =
  -0.30864197530864196 - 0.96225044864937626j.
- Nominal LQG loop before recovery (q = 0, the lqg-design Example A
  filter): S0 = [[1.7320508075688772, 1], [1, 1.7320508075688772]],
  L0 = [1.7320508075688772, 1]; its loop transfer is
  L_lqg(s; 0) = (1 + 2 sqrt(3) s) / (s^2 (s^2 + 2 sqrt(3) s + 5))
  (equals G(s) times minus the lqg Example A compensator transfer
  function). The estimator lag and roll-off bend the loop far from
  the target: M(0) = 0.79265793913710081, Mmag(0) =
  0.79152889018535089, i.e. the nominal output loop is off the
  full-state loop by up to 79% of the target's peak magnitude.
- Recovery trace (q, M(q), Mmag(q), L(q) = [l1, l2]) over the
  sweep, every entry a real anchor value:
  q = 10: M = 0.46672494862660469, Mmag = 0.46665926627057602,
  L = [4.5934465537591462, 10.04987562112089]
  q = 100: M = 0.20156746815359272, Mmag = 0.20156524575736853,
  L = [14.177799538363226, 100.00499987500625]
  q = 1000: M = 0.072062021956610434, Mmag = 0.072062015642601701,
  L = [44.732549670231741, 1000.000499999875]
  q = 1e4: M = 0.023772073268366271, Mmag = 0.023772060968471405,
  L = [141.42489208056693, 10000.000050000001]
  q = 1e5: M = 0.0076215835906494403, Mmag = 0.0076215752257677788,
  L = [447.21471354372943, 100000.00000499999]
  q = 1e6: M = 0.0024207706165423701, Mmag = 0.0024207674026657765,
  L = [1414.2139159267949, 1000000.0000005]
  q = 1e7: M = 0.00076658259948715081, Mmag = 0.0007665815223384054,
  L = [4472.1360668029884, 10000000.00000005]
  q = 1e8: M = 0.0002425216736106494, Mmag = 0.00024252132677611768,
  L = [14142.135659086289, 100000000]
  M(q) strictly decreases over the sweep (True) and the complex
  mismatch and the magnitude-only mismatch track each other to five
  digits at every q: recovery reshapes magnitude and phase together.
- Recovery verdict: q* = 10000000.0 (first sweep q with M(q) <=
  1e-3), M(q*) = 0.00076658259948715081, Mmag(q*) =
  0.0007665815223384054, so the recovered output loop matches the
  full-state target loop to better than 7.7e-4 of the target's peak
  magnitude across the whole grid; the improvement over the nominal
  LQG loop is M(0)/M(q*) = 1034.02. At q* the filter solution is
  S(q*) = [[4472.1360668029884, 10000000.00000005],
  [10000000.00000005, 44721360668.030106]] and L(q*) =
  [4472.1360668029884, 10000000.00000005]; the inflation law is
  w2(q*) = 1 + 1e14, and the family closed form gives l2(q) =
  sqrt(1 + q^2), l1(q) = sqrt(2 l2(q) + 1), both reproduced exactly.
  The filter ARE residual at q* is 3.725e-09 (max entry), tiny
  against entries of order q^2. The price of recovery is estimator
  speed: the filter characteristic polynomial s^2 + l1 s + l2 has
  roots of magnitude sqrt(l2) = (1 + q^2)^(1/4) = 3162.28 rad/s at
  q*, about 1740 times the target unity-magnitude crossing, which is
  the standard LTR noise-bandwidth trade.
- Recovered loop against target (loop-shape samples, real anchor):
  w = 0.1 rad/s: |L_t| = 101.48891565092218, |L_lqg(q*)| =
  101.41111612 (nominal |L_lqg(0)| = 21.157506880); w = 1.0: |L_t|
  = 2.0000000000, |L_lqg(q*)| = 1.9988388170 (nominal 0.68138514387);
  w = 1.8: |L_t| = 1.0105373792, |L_lqg(q*)| = 1.0099915251
  (nominal 0.30083181378); w = 10: |L_t| = 0.17349351573,
  |L_lqg(q*)| = 0.17340382738 (nominal 0.0034272031267); w = 20:
  |L_t| = 0.086638617256, |L_lqg(q*)| = 0.086593884562 (nominal
  0.00043194562704). Complex agreement at q*: at w = 1.0, L_lqg(q*)
  = -0.99999970038576613 - 1.7307100322379296j against L_t =
  -1 - 1.7320508075688772j; at w = 1.8, L_lqg(q*) =
  -0.30917685386734922 - 0.96150535819929006j against L_t =
  -0.30864197530864196 - 0.96225044864937626j.
- Damped cross-checks: filter_riccati(0.5, 1.0, 4.0, 1.0) returns
  S = [[1.8179960365836825, 1.1525547945169889], [1.1525547945169889,
  2.671617445635901]] and L = [1.8179960365836825, 1.1525547945169889],
  identical to the lqg-design Example B anchors to 1e-15 (the a > 0
  bisection branch). On the damped plant a = 0.5 with the matched
  weights, K = [1, 1.3027756377319946], M(0) = 7.1197214039e-01
  drops to M(1e5) = 5.7834333689e-03: recovery through the bisection
  branch reduces the mismatch by a factor of 123.
- Determinism: a second identical recovery_result run is bitwise
  identical in the trace, q_star, S_star and L_star (True).
- ValueErrors: 12 exercised rejection cases all raise (a = -0.1,
  r = 0, w1 = -1, w2 = 0, rv = -1, q = -1, frequency_grid at
  omega_min = 0, at n_freq = 1 and at omega_max = 0.05 below
  omega_min = 0.1, recovery_sweep at q_min = 0 and with q_max <
  q_min).

Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w45spec/anchor_loop_transfer_recovery.py (stdlib math, exit 0,
bitwise-identical under both interpreters).

## Validation list (contract test must include)

- frequency_grid() returns 41 log-spaced points over [0.1, 20];
  w_0 = 0.1 and w_40 = 20 within 1e-12, and the ratio of consecutive
  points equals (20/0.1)^(1/40) = 1.1416309914166938 within 1e-12.
- Target identity: at every grid point, target_loop(j w, 0, [1,
  sqrt(3)]) equals -(1/w^2) - 1j * sqrt(3)/w within 1e-12; the
  grid-max magnitude is 101.48891565092218 within 1e-6 relative;
  |L_t(j 1.8173540210239707)| = 1 within 1e-9.
- ARE residuals below 1e-8 (max entry): regulator at the worked
  weights (anchor 4.441e-16), filter at q = 0 (anchor 4.441e-16),
  filter at q* = 1e7 (anchor 3.725e-09).
- Nominal loop: L0 = [1.7320508075688772, 1] within 1e-6 and
  M(0) = 0.79265793913710081 within 1e-6 relative; the nominal
  loop-transfer closed form (1 + 2 sqrt(3) s)/(s^2 (s^2 + 2 sqrt(3)
  s + 5)) matches recovered_loop at q = 0 at every grid point within
  1e-9.
- Recovery sweep: the 8 trace entries (q, M(q), Mmag(q)) match the
  worked example table within 1e-6 relative per entry (assert with
  isclose or delta, NEVER exact equality); M(q) strictly decreasing;
  M(1e8)/M(1e7) = 0.316367 within 2% of 1/sqrt(10) = 0.316228;
  M(q) * sqrt(q) at q = 1e8 within 0.02 of 2.425217.
- Recovery verdict: q_star = 1e7 (within 1e-12), M(q*) =
  0.00076658259948715081 within 1e-6 relative, Mmag(q*) =
  0.0007665815223384054 within 1e-6 relative, verdict True,
  improvement_ratio 1034.02 within 1e-3 relative, L(q*) =
  [4472.1360668029884, 10000000.00000005] within 1e-6 relative per
  entry and S(q*) = [[4472.1360668029884, 10000000.00000005],
  [10000000.00000005, 44721360668.030106]] within 1e-6 relative per
  entry.
- Recovered loop samples: at w = 0.1, 1.0, 1.8, 10, 20 the complex
  samples L_lqg(j w; q*) match the anchor magnitudes within 1e-6
  relative and the complex samples at w = 0.1, 1.0, 1.8 match
  (-99.923364097491799 - 17.30710203489846j, -0.99999970038576613 -
  1.7307100322379296j, -0.30917685386734922 - 0.96150535819929006j)
  within 1e-6 relative per part.
- Matrix-versus-closed-form identities: at q = 1000 the 2x2 matrix
  loop equals the family rational closed form at every grid point
  within 1e-9 (anchor max abs diff 9.379e-13); the two SISO
  multiplication orders are bitwise equal; the target loop matrix
  path matches its closed form within 1e-9 (anchor 3.553e-15).
- Cross-sibling filter identity: filter_riccati(0.5, 1.0, 4.0, 1.0)
  returns S and L matching the lqg-design Example B anchors
  (1.8179960365836825, 1.1525547945169889, 2.671617445635901)
  within 1e-12.
- Damped recovery: with a = 0.5 and the matched weights,
  M(0) = 7.1197214039e-01 within 1e-3 relative and M(1e5) =
  5.7834333689e-03 within 1e-3 relative (ratio 8.123118e-03), and
  K = [1, 1.3027756377319946] within 1e-9.
- Determinism: two identical recovery_result runs bitwise identical
  in trace, q_star, S_star, L_star; no imports beyond math; no RNG.
- ValueErrors: regulator_riccati at a = -0.1 and r = 0.0;
  filter_riccati at w1 = -1.0, w2 = 0.0 and rv = -1.0;
  inflated_noise_covariance at q = -1.0; frequency_grid at
  omega_min = 0.0, at n_freq = 1 and at omega_max = 0.05 below
  omega_min = 0.1; recovery_sweep at q_min = 0.0 and with q_max <
  q_min (all 12 anchor-exercised cases raise).
- Run the contract test under BOTH interpreters
  (/usr/bin/python3 3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3);
  all asserts above are tolerance-based and must hold on both (the
  prep anchor output is bitwise identical on both).

## Corpus fragment (eval/hit1-wave45-loop-transfer-recovery.yaml)

Query 1 (copy verbatim):
  "design a loop-transfer-recovery controller for the lqg
  compensator: inflate the process noise weight q on the driven input
  channel and recover the full-state loop transfer function at the
  plant output"
  intent: "gnc-autonomy; output-side loop-transfer-recovery of the
  lqg compensator: inflate the filter process noise weight q on the
  driven input channel and recover the full-state loop transfer
  function at the plant output against the target feedback loop"
  expected_skill: "gnc-autonomy/optimal-control/loop-transfer-recovery"
Query 2 (copy verbatim):
  "run loop-transfer-recovery on the lqg design: increase the
  recovery gain until the recovered output loop singular values match
  the target-feedback-loop full-state loop"
  intent: "gnc-autonomy; run the loop-transfer-recovery recovery-gain
  sweep: increase the recovery gain q until the recovered output loop
  singular values match the target-feedback-loop full-state loop on
  the frequency grid"
  expected_skill: "gnc-autonomy/optimal-control/loop-transfer-recovery"
Task ids: w45-loop-transfer-recovery-1 and -2. Prep grep:
loop-transfer-recovery, full-state-loop-recovery, lqg-loop-shaping,
recovery-gain-tuning and target-feedback-loop appear in NO existing
eval/hit1-corpus.yaml task (grep count 0 per token), in NO skill
file (whole-tree count 0 for the gate-a pattern) and in NO
wave44-specs or wave45-specs file written so far; the lqg-design
tasks route on the two-ARE compensator assembly and the separation
principle verdict, the lqr-design tasks route on the gain vector and
the stability verdict, and the frequency-response-design tasks route
on gain and phase margin computation, so the queries above are
collision-free (receipt gate (e): Hit@1 at 19.0 vs 14.0 for query 1
and 18.0 vs 7.5 for query 2, theft audit 0 of 1238 existing tasks).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run loop-transfer-recovery
on the LQG loop of the two-state plant family:" and include the
outputs in the Claim. First tag: loop-transfer-recovery. Additional
tags ONLY, exactly as the receipt gate (f) lists them:
full-state-loop-recovery, lqg-loop-shaping, recovery-gain-tuning,
target-feedback-loop. NEVER single generic words (loop, recovery,
lqg, filter, gain, riccati, plant, output, compensator, margin,
bode, singular, frequency alone) and NEVER the sibling-owned
compounds: linear-quadratic-regulator, riccati as a tag,
gain-matrix, state-feedback, closed-loop-stability, control-effort,
spacecraft-attitude-control (lqr-design, which owns the plain riccati
tag); linear-quadratic-gaussian, output-feedback-compensator,
separation-principle, regulator-riccati, filter-riccati-gain,
compensator-transfer-function (lqg-design); frequency-response,
bode-analysis, gain-margin, phase-margin, gain-crossover-frequency,
phase-crossover-frequency, crossover-frequency, stability-margins
(frequency-response-design); model-predictive-control, mpc,
receding-horizon, quadratic-program, double-integrator
(model-predictive-control); ilqr-ddp, differential-dynamic-
programming, backward-riccati-pass (ilqr-ddp); bang-bang-control,
switching-curve, minimum-time-maneuver (bang-bang-control); dymos,
pseudospectral, collocation (dymos-trajectory); kalman-filter-design,
discrete-time (kalman-filter-design). 50-150 words, <=1000 chars, no
em dash, no content-policy sweep term, action verb present.
Recommended wording (outputs in Claim order): "Use when you must run
loop-transfer-recovery on the LQG loop of the two-state plant family:
inflate the filter process noise weight q on the driven input
channel through Qw(q) = Qw0 + q^2 B B^T, re-solve the filter Riccati
equation for the error covariance and the estimator gain at every q,
and compare the recovered output loop transfer function with the
full-state target loop on a log-spaced frequency grid until the
grid-max mismatch M(q) falls at or below the recovery tolerance.
Produces the full-state target loop samples, the mismatch-versus-q
recovery trace, the recovery gain q* first meeting the tolerance, the
recovered filter covariance and estimator gain, and the recovery
verdict that gate the loop-shaped LQG design. Trigger:
loop-transfer-recovery, LTR, full-state-loop-recovery,
lqg-loop-shaping, recovery-gain-tuning, target-feedback-loop." The
sibling phrase triggers "gain vector", "stability verdict",
"weighting trade", "separation principle", "compensator transfer
function", "gain margin", "phase margin", "crossover frequency",
"bode", "receding horizon" and "pseudospectral" must not appear as
routing keywords; "filter Riccati equation" stays as the leaf's own
description of the per-q re-solve and never refers to the lqg-design
single-shot synthesis or the plain-riccati regulator gain product.

FORBIDDEN TOKENS (belong to siblings): gain matrix, state feedback,
closed loop stability, control effort, weighting trade (lqr-design);
output feedback compensator, separation principle, compensator
transfer function, regulator Riccati, filter Riccati gain
(lqg-design); gain margin, phase margin, gain crossover, phase
crossover, bode analysis, stability margins (frequency-response-
design); receding horizon, quadratic program, prediction horizon,
model predictive control (model-predictive-control); iterative LQR,
differential dynamic programming, backward Riccati pass (ilqr-ddp);
switching curve, minimum time (bang-bang-control); pseudospectral,
collocation, Dymos (dymos-trajectory); Kalman filter over sampled
measurements, discrete-time Riccati (kalman-filter-design). The
outputs of this leaf are the target loop samples, the recovery trace
of mismatch versus q, the recovery gain q* with the recovered filter
covariance and estimator gain, and the recovery verdict; no output
is a compensator realization, a separation verdict, a margin number,
a gain vector product or a discrete-time filter run, and no output
claims loop shaping of a general n-state plant.
