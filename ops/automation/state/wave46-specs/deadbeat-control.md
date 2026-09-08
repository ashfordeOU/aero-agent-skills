# Wave-46 leaf spec: deadbeat-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/deadbeat-control/
- Pack: control (present siblings adaptive-control,
  control-allocation, digital-control-design, frequency-response-design,
  gain-scheduling, l1-adaptive-control, lead-lag-compensation,
  observer-design, pid-control-design, python-control-design,
  root-locus-design, state-space-analysis; no sibling in the pack or
  anywhere else in the tree performs a direct deadbeat synthesis:
  zero-owner greps at prep and re-verified at spec time over the whole
  skills/ tree return 0 hits for `deadbeat`, `dead[- ]beat`,
  `finite[- ]settling` and `z-domain-deadbeat`, exit 1).
- Provenance: wave-46 recon receipt task-7 GO 3, lines 212-266 (rank 3
  of 3 GO): "deadbeat digital control design for a discrete-time plant:
  finite-settling controller placing ALL closed-loop poles at z = 0,
  direct deadbeat synthesis from the plant pulse transfer function (e.g.
  for a first- or second-order discrete plant, the controller that
  yields settling in n samples), steady-state tracking check, control
  effort." Published deterministic anchor, receipt gate (d)
  (summary-only; the receipt text uses a dash this file does not): a
  deadbeat controller of a discrete-time plant chooses the controller
  so the closed-loop characteristic polynomial is z^n = 0, driving the
  output to the reference in a finite number of sample periods (settling
  in at most n samples for an n-th-order plant) with the control
  sequence obtained by direct pole placement at the origin of the
  z-plane. Source: Franklin, Powell and Workman, Digital Control of
  Dynamic Systems, 3rd ed., ch. 4-5; Ogata, Discrete-Time Control
  Systems, 2nd ed., ch. 6 (deadbeat response design). Deterministic
  offline closed-form synthesis for the first/second-order discrete
  plants the family convention already uses. Corpus tokens of the leaf
  (gate f, all hyphenated compounds): deadbeat-control,
  finite-settling-time, pole-placement-at-origin, minimum-settling-time,
  z-domain-deadbeat.
- Claim fences (quoted from the sibling SKILL.md files at prep,
  re-verified at spec time; the nearest owner, the digital-control-design
  sibling, owns the sampled-data toolbox but never a direct deadbeat
  synthesis, which is the exact gap this leaf closes):
  - digital-control-design (this pack) OWNS discretization, emulation,
    discrete PID and the loop verdicts: its frontmatter description
    reads "Use when you must design a sampled-data digital control loop
    in the z-domain: discretize a continuous plant with a zero-order
    hold, emulate a continuous compensator with the Tustin bilinear
    transform with frequency prewarping, compute discrete PID
    coefficients in the position and velocity forms, check the sampled
    poles against the unit circle for stability, and select the sample
    rate from the closed-loop bandwidth. Produces the discretized plant
    coefficients, the emulated compensator, the discrete PID gains, the
    stability verdict and the sample-rate verdict that gate a digital
    control design. Trigger: z transform, zero order hold, zoh, tustin
    bilinear emulation, frequency prewarping, discrete pid, unit circle
    stability, sample rate selection." Its body (lines 23-34) states
    "This leaf implements the sampled-data control methods in pure
    Python, stdlib only, deterministic and offline: ZOH step-invariant
    discretization with exact closed-form coefficients, Tustin bilinear
    emulation with frequency prewarping, discrete PID coefficient
    forms, unit-circle stability and the sample-rate rule." Its Related
    leaves list (lines 188-199) names pid-control-design,
    lead-lag-compensation, the signal-filter sibling
    digital-filter-design and state-space-analysis, with no deadbeat or
    finite-settling design claim anywhere. It consumes continuous
    plants and compensators; this leaf consumes plants that are ALREADY
    discrete, given as pulse transfer functions, and never discretizes.
  - pid-control-design owns continuous pole placement in the s-domain
    only: its frontmatter description reads "... or place closed loop
    poles directly for a first or second order plant ...", and its body
    pole-placement forms are the continuous plants G(s) = b/(s + a) and
    the second-order G(s). No discrete z-plane origin placement appears
    anywhere in the pack.
  - The rest of the pack owns fixed-gain or known-parameter continuous
    design, gain scheduling, allocation, observers and linear algebra
    analysis (pid-control-design, lead-lag-compensation,
    root-locus-design, frequency-response-design, python-control-design,
    gain-scheduling, control-allocation, observer-design,
    state-space-analysis), the L1 architecture with state predictor and
    projection adaptation (l1-adaptive-control, landed wave-45) and the
    first-order MRAC gradient law (adaptive-control): none solves a
    deadbeat design equation or claims a finite-settling response.
  Whole-tree greps at prep and spec time: deadbeat-control,
  finite-settling-time, pole-placement-at-origin, minimum-settling-time
  and z-domain-deadbeat each return ZERO hits in eval/hit1-corpus.yaml
  (grep count 0 per token), ZERO hits across skills/ (whole-tree count
  0, exit 1, re-verified at spec time) and NO wave46-specs file written
  so far carries the leaf name. GENUINE gnc-autonomy gap (fresh probe
  task-7 GO 3): no leaf runs a direct deadbeat synthesis, the discrete
  control method between the sampled-data toolbox of
  digital-control-design and the continuous designs of the rest of the
  pack.
- Standards id: arp4754a (reference-only, present in standards-map.yaml
  at line 38, grep-verified at spec time; SAE ARP is proprietary, name
  plus paraphrase only, no reproduced text; arp4754a is the control
  pack convention of gnc-autonomy). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design a deadbeat-control law for a discrete-time plant given by its
pulse transfer function G(z) = B(z)/A(z), after Franklin, Powell and
Workman (Digital Control of Dynamic Systems, ch. 4-5) and Ogata
(Discrete-Time Control Systems, ch. 6, deadbeat response design):
given a first- or second-order strictly proper plant with every pole
and every zero strictly inside the unit circle (the admissibility of
the direct synthesis: the controller cancels exactly those modes, so a
canceled mode must be strictly stable), form the unity-feedback
controller D(z) = A(z)/(B(z)*(z^d - 1)) with d = deg A - deg B, whose
closed-loop characteristic polynomial A*D_c + B*N_c = A*B*z^d leaves,
after the strictly-stable cancellations, the observable closed loop
T(z) = z^-d with ALL closed-loop poles at z = 0. The step response
reaches and holds the reference in exactly d sample periods (d = n for
a plant with no numerator zeros, matching the receipt's "settling in n
samples" phrasing; d < n when the plant has interior zeros), the
tracking error is exactly zero from sample d on, and the control
sequence is reported sample by sample with the steady control u* =
A(1)/B(1) that holds the output at the reference. Produces the
admissibility verdict (pole and zero moduli against the unit circle by
closed-form roots only), the deadbeat controller as a causal
difference equation on the tracking error, the settling sample and
settling time, the closed-loop step response and control effort
histories, the steady-state tracking check and the control effort
summary that gate a deadbeat digital control assessment. Does NOT do:
discretizing a continuous plant with a zero-order hold, emulating a
continuous compensator with the Tustin bilinear transform, frequency
prewarping, computing discrete PID coefficients in the position or
velocity forms, a general unit-circle stability verdict on sampled
poles, or the sample-rate selection rule (digital-control-design);
continuous s-domain pole placement for a first or second order plant,
PID tuning or margin checks (pid-control-design,
frequency-response-design, python-control-design); phase lead/lag
compensation or root-locus design (lead-lag-compensation,
root-locus-design); gain scheduling over operating points
(gain-scheduling); actuator distribution (control-allocation);
observer or estimator gain design (observer-design); eigenvalue,
controllability or observability analysis (state-space-analysis); the
L1 architecture or the MRAC gradient adaptation law
(l1-adaptive-control, adaptive-control). Deterministic, offline, stdlib
math only: fixed-order polynomial arithmetic and closed-form root
checks, no numpy, no scipy, no generic numeric root finding, no RNG, no
external processes. Sample time T_s is an input used to convert sample
counts to a time axis (settling time = d*T_s); it is never a design
rule, the sample-rate selection rule belongs to digital-control-design.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes, no external solvers. Deterministic: plain fixed-order
arithmetic in the pinned order below. Module name deadbeat_control.
Coefficient lists are in descending powers of z (A(z) = A[0]*z^n +
A[1]*z^(n-1) + ... + A[n]); A must be monic after normalization (the
module scales both lists by the leading A coefficient A[0]). Histories
y, e, u are lists of length steps; index k is sample k.

Module constants (pin exactly; the worked scenarios and guards):
- FIRST_ORDER_A = [1.0, -0.5], FIRST_ORDER_B = [0.5],
  FIRST_ORDER_TS = 0.1 (scenario A: G(z) = 0.5/(z - 0.5), a first-order
  plant with no zeros, sample time 0.1 s).
- SECOND_ORDER_A = [1.0, -1.1, 0.24], SECOND_ORDER_B = [0.2],
  SECOND_ORDER_TS = 0.02 (scenario B: G(z) = 0.2/(z^2 - 1.1*z + 0.24),
  poles z = 0.8 and z = 0.3, no zeros, sample time 0.02 s).
- ZERO_A = [1.0, -1.1, 0.24], ZERO_B = [0.1, 0.05],
  ZERO_TS = 0.02 (scenario C: same denominator with an interior zero at
  z = -0.5, G(z) = (0.1*z + 0.05)/(z^2 - 1.1*z + 0.24), so d = n - m =
  1 < n).
- COMPLEX_POLE_A = [1.0, -1.6, 0.65], COMPLEX_POLE_B = [0.1]
  (complex-pole guard plant: pole pair 0.8 +/- j*0.1, modulus
  sqrt(0.65) = 0.8062257748298549, admissible).
- UNSTABLE_A = [1.0, -2.5, 1.0] (poles 2.0 and 0.5), BOUNDARY_A =
  [1.0, -2.1, 1.1] (poles 1.1 and 1.0), NONMINIMUM_PHASE_B = [1.0, 2.0]
  (zero at z = -2.0), BOUNDARY_ZERO_B = [1.0, -1.0] (zero at z = 1.0),
  DEG3_A = [1.0, -1.1, 0.24, 0.1] (degree 3, out of scope), NOT_STRICTLY_
  PROPER = ([1.0, -0.5], [1.0, 1.0]).
- N_STEPS = 40 (default run length), SETTLE_TOL = 1e-9 (default
  settling tolerance).

Defining relations (pin exactly; every function below derives from
these). With w = z^-1 the plant reads G(w) = w^d * Bt(w)/At(w) where
At(w) = A (ascending w coefficients equal the descending z list,
At(0) = 1 for monic A), Bt(w) = B (ascending, Bt(0) = b_m, the leading
numerator coefficient) and d = n - m = deg A - deg B is the relative
degree, the pure sample delay of the plant:
- Deadbeat controller (unity feedback, reference r applied as a step at
  k = 0): D(z) = N_c(z)/D_c(z) = A(z)/(B(z)*(z^d - 1)), i.e. N_c = A,
  D_c = B*(z^d - 1).
- Pole-placement equation: the closed-loop characteristic polynomial is
  A(z)*D_c(z) + B(z)*N_c(z) = A(z)*B(z)*z^d (verified coefficient-wise
  in the anchor with trailing alignment: A*D_c has degree 2n and B*N_c
  has degree n + m, so the two products are added constant-end aligned,
  the B*N_c product shifted right by d). The canceled factors A and B
  are strictly stable by admissibility, so the observable closed loop
  is T(z) = z^-d: a pure d-sample delay with all closed-loop poles at
  z = 0.
- Deadbeat response: y(k) = r for every k >= d (settling in d samples,
  settling time d*T_s); tracking error e(k) = r(k) - y(k) is e(k) = r
  for 0 <= k < d and e(k) = 0 for every k >= d.
- Controller difference equation (causal recursion on the error):
  with mu(w) = conv(Bt(w), [1, 0, ..., 0, -1]) the ascending
  coefficients of Bt(w)*(1 - w^d), mu_j = beta_j - beta_(j-d), and
  mu0 = b_m:
  u(k) = sum_{i=0..n} num_e[i]*e(k - i) + sum_{j=1..m+d} den_u[j-1]*u(k - j),
  num_e[i] = alpha_i/mu0 (alpha = A, alpha_0 = 1), den_u[j-1] = -mu_j/mu0.
- Plant recursion for the closed-loop simulation (zero initial state):
  y(k) = -sum_{i=1..n} A[i]*y(k - i) + sum_{j=0..m} B[j]*u(k - d - j).
- Pinned per-sample ordering (what makes the identities exact): at
  sample k, (1) advance the plant to y(k) from past samples only,
  (2) append y(k), (3) form e(k) = r(k) - y(k) and append it, (4)
  compute u(k) from the error history (which now includes e(k) at its
  current index) and the past control history, (5) append u(k). All
  reads before k = 0 return 0.0.
- Steady-state tracking: the control that holds y = r is u* = A(1)/B(1)
  (the inverse of the plant DC gain; u* * G(1) = 1). For m = 0 the
  control reaches u(k) = u* exactly at sample k = d; for m = 1 the
  control converges geometrically to u* at the plant-zero rate while
  the output is still deadbeat (scenario C).
- Admissibility (the design gate): deadbeat synthesis cancels the
  plant modes, so the plant must be stable AND minimum phase: every
  root of A and every root of B strictly inside the unit circle
  (|root| < 1). Roots come from exact closed forms only (degree 1 and
  2; the numerically stable q-form for real quadratics, the exact
  conjugate-pair form for complex quadratics), mirroring the family
  rule that digital-control-design applies to unit_circle_poles;
  degree 3 and higher raises ValueError, generic numeric root finding
  is out of scope everywhere. A pole or zero ON the unit circle is
  inadmissible (strict rule).
- Sample time is reporting-only: non-positive T_s raises ValueError;
  T_s converts sample counts to seconds, it never enters a design or
  a rate-selection rule.

Functions (public API, 10):
- polyval_desc(coeffs, z) -> float. Horner evaluation of the
  descending-power polynomial at z. ValueError for an empty list.
- poly_mul_desc(p, q) -> list. Descending-power polynomial product.
  ValueError for empty lists.
- roots_moduli_desc(coeffs) -> list. Closed-form root moduli, degree 1
  or 2 only (degree 0 returns []); ValueError for degree 3 and higher.
- admissibility_check(A, B) -> dict with exact keys
  {'admissible': bool, 'pole_moduli': list, 'zero_moduli': list,
  'reason': str}. pole_moduli and zero_moduli are the closed-form root
  moduli of A and B; admissible is True iff every modulus is strictly
  below 1.0 (no plant zeros gives zero_moduli = [] and a vacuous
  zero check); reason describes any violation. Raises ValueError for
  structurally invalid input (empty lists, zero leading coefficients,
  n < 1, n > 2, m >= n: not strictly proper).
- deadbeat_design(A, B) -> dict with exact keys {n, m, d, a_desc,
  b_desc, num_e, den_u, mu0, d_num_desc, d_den_desc, char_poly_desc,
  u_star, plant_dc_gain}. Normalizes A monic (both lists scaled by
  A[0]), runs the admissibility gate, and returns the controller:
  d = n - m; num_e and den_u are the recursion coefficients above
  (den_u[j] multiplies u(k - 1 - j)); mu0 = b_m; d_num_desc = a_desc
  and d_den_desc = conv(b_desc, [1, 0, ..., 0, -1]) are the z-domain
  controller numerator and denominator (D(z) = N_c/D_c);
  char_poly_desc is A*B*z^d in descending powers; u_star = A(1)/B(1);
  plant_dc_gain = B(1)/A(1) = 1/u_star. Raises ValueError for
  structurally invalid input (same checks as admissibility_check) and
  for an inadmissible plant, ValueError with the verdict reason
  (unstable poles, non-minimum-phase or unit-circle zeros).
- simulate(A, B, ts=1.0, steps=N_STEPS, r=1.0,
  reference="step") -> dict with exact keys {'y', 'e', 'u', 'k'}.
  Closed-loop run under the deadbeat controller with the pinned
  ordering above; y, e, u are lists of length steps, k is
  list(range(steps)); r(k) = r for every k (reference="step") or
  r(0) = r and r(k) = 0 for k >= 1 (reference="impulse"). Raises
  ValueError for ts <= 0, steps < 2, an unknown reference string, any
  structural plant error, or an inadmissible plant (the deadbeat
  closed loop does not exist for an inadmissible plant).
- settling_report(res, d, ts, r=1.0, tol=SETTLE_TOL) -> dict with
  exact keys {'settling_sample', 'settling_time_s', 'y_at_settling',
  'max_dev_after_settling', 'settled'}. settled is True iff
  |y(k) - r| <= tol and |e(k)| <= tol for every k in [d, steps-1];
  y_at_settling = res['y'][d]; settling_time_s = float(d*ts). Raises
  ValueError when the history is too short to cover sample d or ts <= 0.
- steady_control(A, B) -> float. u* = A(1)/B(1). Raises ValueError
  for structural errors and for B(1) == 0 (infinite plant DC gain).
- control_effort(u) -> dict with exact keys {'u0', 'max_abs_u',
  'u_final'}: the initial control sample, max |u| over the run and the
  final control sample.
- closed_loop_impulse(A, B, steps=N_STEPS) -> dict. simulate with
  reference="impulse": the closed-loop impulse response, used for the
  pure-delay identity.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums; math.isclose / assertAlmostEqual
everywhere):
- Deadbeat step identity: for every admissible plant the step response
  satisfies y(k) = r within 1e-9 for every k in [d, steps-1], and
  |y(d) - r| within 1e-9 (settling exactly at the settling sample d).
- Error identity: e(k) = r within 1e-9 for 0 <= k < d and |e(k)| <=
  1e-9 for every k >= d.
- Error area identity: sum(e) = d*r within 1e-6 relative (scenario B
  real anchor 1.9999999999999982 against d*r = 2).
- Pole-placement identity: A*D_c + B*N_c equals A*B*z^d coefficient
  wise within 1e-12 (products added constant-end aligned; scenario B
  real anchor max coefficient diff 1.3877787807814457e-17).
- Pure-delay identity: the closed-loop impulse response is exactly a
  d-sample delay, y(k) = r at k = d and 0 elsewhere within 1e-9
  (scenario B real anchor y(2) = 1, all other samples 0).
- Steady-state tracking identity: u* * G(1) = 1 within 1e-9 (real
  anchors exactly 0 residual) and, for m = 0 plants, u(k) = u* within
  1e-9 for every k >= d (scenario B real anchor True from k = 2).
- Admissibility boundary: |root| strictly below 1 is required; a pole
  or zero on or outside the unit circle makes deadbeat_design raise
  ValueError, never a marginal design.
- Determinism: two identical simulate runs are bitwise identical in y,
  e and u (real anchor True); no imports beyond math; no RNG.

## Worked example

All values below are REAL outputs of the prep anchor
anchor_deadbeat_control.py (pure stdlib math, exit 0, every identity
check True, byte-identical output under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3). Every step response reaches the
reference at the settling sample and holds it: settling sample = d, the
multiplicity of the closed-loop pole at the origin.

Scenario A (first order, the receipt's example plant): G(z) =
0.5/(z - 0.5), A = [1.0, -0.5], B = [0.5], T_s = 0.1 s, unit step
r = 1.
- admissibility_check: admissible True, pole_moduli [0.5],
  zero_moduli [].
- deadbeat_design: n = 1, m = 0, d = 1; num_e = [2.0, -1.0],
  den_u = [1.0], mu0 = 0.5; D(z) = (z - 0.5)/(0.5*(z - 1)) with
  d_num_desc = [1.0, -0.5], d_den_desc = [0.5, -0.5]; char_poly_desc =
  [0.5, -0.25, 0.0]; u_star = 1.0, plant_dc_gain = 1.0. Controller
  recursion: u(k) = 2.0*e(k) - 1.0*e(k - 1) + 1.0*u(k - 1).
- Step response: y = [0, 1, 1, 1, 1, 1, 1, 1, ...]: the output reaches
  1.0 exactly at sample 1 (settling sample 1, settling time 0.1 s,
  y_at_settling = 1.0) and holds it with max_dev_after_settling = 0.0.
  Error: e = [1, 0, 0, 0, ...], zero from sample 1 on.
- Control effort: u = [2.0, 1.0, 1.0, 1.0, ...]: u(0) = 2.0 (peak,
  max_abs_u = 2.0, u0 = 2.0), u(k) = 1.0 = u* for every k >= 1, the
  steady control holds the output at the reference (u_final = 1.0).
- settling_report: {'settling_sample': 1, 'settling_time_s': 0.1,
  'y_at_settling': 1.0, 'max_dev_after_settling': 0.0,
  'settled': True}.

Scenario B (second order, no zeros): G(z) = 0.2/(z^2 - 1.1*z + 0.24),
A = [1.0, -1.1, 0.24], B = [0.2], T_s = 0.02 s, unit step r = 1.
- admissibility_check: admissible True, pole_moduli [0.8, 0.3]
  (real anchors 0.80000000000000016 and 0.29999999999999993),
  zero_moduli [].
- deadbeat_design: n = 2, m = 0, d = 2; num_e = [5.0, -5.5, 1.2],
  den_u = [0.0, 1.0], mu0 = 0.2; D(z) = A(z)/(0.2*(z^2 - 1)) with
  d_den_desc = [0.2, 0.0, -0.2]; char_poly_desc = [0.2, -0.22, 0.048,
  0.0, 0.0] (0.2*z^4 - 0.22*z^3 + 0.048*z^2 = A*B*z^2, coefficient
  check max diff 1.3877787807814457e-17); u_star = 0.6999999999999995,
  plant_dc_gain = 1.4285714285714295 (10/7, so u* * G(1) = 1 exactly).
  Controller recursion: u(k) = 5.0*e(k) - 5.5*e(k - 1) + 1.2*e(k - 2)
  + 1.0*u(k - 2).
- Step response: y = [0, 0, 1, 1, 1.0000000000000002,
  1.0000000000000002, 1.0000000000000002, 1.0000000000000004, ...]:
  y(0) = 0, y(1) = 0 (the second-order plant cannot move before sample
  2), y(2) = 1.0 exactly (settling sample 2, settling time 0.04 s,
  y_at_settling = 1.0); the residual drift at samples 4-7 is float
  noise at the 1e-16 level, max_dev_after_settling = 8.881784197001252
  e-16, settled True.
- Error: e = [1, 1, 0, 0, -2.2204460492503131e-16,
  -2.2204460492503131e-16, -2.2204460492503131e-16,
  -4.4408920985006262e-16, ...]: two unit error samples, then zero to
  float precision; error area sum(e) = 1.9999999999999982 = d within
  1e-15.
- Control effort: u = [5.0, -0.5, 0.70000000000000018,
  0.69999999999999996, ...]: u(0) = 5.0 (peak, max_abs_u = 5.0),
  u(1) = -0.5, and u(k) = 0.7 = u* within 3e-16 for every k >= 2
  (the control is at steady state exactly when the output settles);
  u_final = 0.6999999999999994.
- settling_report: {'settling_sample': 2, 'settling_time_s': 0.04,
  'y_at_settling': 1.0, 'max_dev_after_settling': 8.881784197001252e-16,
  'settled': True}.

Scenario C (relative-degree generality, interior zero): G(z) =
(0.1*z + 0.05)/(z^2 - 1.1*z + 0.24), A = [1.0, -1.1, 0.24],
B = [0.1, 0.05], T_s = 0.02 s, unit step r = 1.
- admissibility_check: admissible True, pole_moduli [0.8, 0.3],
  zero_moduli [0.5] (the zero at z = -0.5 is strictly inside).
- deadbeat_design: n = 2, m = 1, d = 1 (settling sample d = n - m = 1
  < n: an interior zero shortens the minimum settling time);
  num_e = [10.0, -11.0, 2.4], den_u = [0.5, 0.5], mu0 = 0.1;
  d_den_desc = [0.1, -0.05, -0.05]; u_star = 0.9333333333333326
  (14/15 to float precision), plant_dc_gain = 1.0714285714285723.
- Step response: y = [0, 1, 1, 1.0000000000000002, ...]: y(1) = 1.0
  (settling sample 1, settling time 0.02 s),
  max_dev_after_settling = 4.440892098500626e-16, settled True;
  e = [1, 0, 0, ...], error area sum(e) = 0.99999999999999911 = d.
- Control effort: u = [10.0, -6.0, 4.4, -0.8, 1.8, 0.5, 1.15, 0.825,
  ...]: u(0) = 10.0 (peak, max_abs_u = 10.0), u(1) = -6.0, and the
  control then converges geometrically to u* at the plant-zero rate
  (alternating decay, factor -0.5): u(39) = 0.9333333333081093 with
  |u(39) - 14/15| = 2.52e-11. The OUTPUT is deadbeat from sample 1
  while the CONTROL converges: with a plant zero the recursion holds y
  at the reference with a geometrically settling effort.
- Guard identity (complex-pole admissibility): G(z) = 0.1/(z^2 - 1.6*z
  + 0.65) has pole pair 0.8 +/- j*0.1, pole_moduli [0.8062257748298549,
  0.8062257748298549] (sqrt(0.65)), admissible True, d = 2, and the
  step response still settles with y(2) = 1.0: the closed-form
  quadratic branch covers complex poles.
- Impulse identity (scenario B): the closed-loop impulse response is
  y(2) = 1 and every other sample 0: the closed loop is exactly the
  pure delay z^-2, all closed-loop poles at z = 0.
- Determinism: a second identical simulate run is bitwise identical in
  y, e and u (True).

Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
anchor_deadbeat_control.py (stdlib math, exit 0, byte-identical on both
interpreters).

## Validation list (contract test must include)

- Admissibility truth table: scenario A pole_moduli [0.5] (admissible
  True); scenario B pole_moduli [0.8, 0.3] within 1e-9 (True); scenario
  C zero_moduli [0.5] (True); complex-pole plant pole_moduli
  [0.8062257748298549, 0.8062257748298549] within 1e-9 (True);
  admissibility_check returns the exact dict keys {'admissible',
  'pole_moduli', 'zero_moduli', 'reason'}.
- Scenario A asserts (isclose, never exact equality on computed sums):
  y(1) = 1.0 within 1e-9 and y(k) = 1.0 for every k in [1, 39] within
  1e-9; e(0) = 1.0 and |e(k)| <= 1e-9 for k >= 1; u(0) = 2.0,
  u(k) = 1.0 for every k >= 1 within 1e-9; settling_report gives
  settling_sample 1, settling_time_s 0.1, y_at_settling 1.0,
  max_dev_after_settling 0.0, settled True; u_star = 1.0 within 1e-9;
  control_effort u0 = 2.0, max_abs_u = 2.0, u_final = 1.0.
- Scenario B asserts: y(2) = 1.0 within 1e-9 and y(k) = 1.0 for every
  k in [2, 39] within 1e-9 (real drift 1.0000000000000002 to
  1.0000000000000004 at samples 4-7, well inside 1e-9);
  e(0) = e(1) = 1.0 and |e(k)| <= 1e-9 for k >= 2 (real anchors
  -2.2204460492503131e-16 and -4.4408920985006262e-16); sum(e) =
  1.9999999999999982 within 1e-6 relative of 2; u(0) = 5.0, u(1) =
  -0.5, u(k) = 0.7 for every k >= 2 within 1e-9 (real anchors within
  3e-16 of 0.7); settling_report settling_sample 2, settling_time_s
  0.04, y_at_settling 1.0, max_dev_after_settling 8.881784197001252e-16
  (below SETTLE_TOL), settled True; u_star within 1e-9 of 0.7 and
  plant_dc_gain = 1.4285714285714295 within 1e-6 relative (10/7);
  u_final 0.6999999999999994 within 1e-6 relative of 0.7;
  char_poly_desc equals [0.2, -0.22, 0.048, 0.0, 0.0] coefficient wise
  within 1e-9.
- Pole-placement identity: for scenario B, A*D_c + B*N_c (constant-end
  aligned sum of the degree-2n and degree-(n + m) products) equals
  char_poly_desc = A*B*z^2 within 1e-12 (real anchor max diff
  1.3877787807814457e-17).
- Pure-delay identity: closed_loop_impulse on scenario B gives y(2) =
  1.0 within 1e-9 and |y(k)| <= 1e-9 for every k != 2 in [0, 39].
- Scenario C asserts: y(1) = 1.0 within 1e-9 and y(k) = 1.0 for k in
  [1, 39] within 1e-9; u(0) = 10.0, u(1) = -6.0 within 1e-9; u(39) =
  0.9333333333081093 within 1e-6 relative of 14/15 = 0.9333333333333334
  (real |u(39) - 14/15| = 2.52e-11), the geometric convergence of the
  control at the plant-zero rate; settling_report settling_sample 1,
  settling_time_s 0.02, settled True; error area sum(e) =
  0.99999999999999911 within 1e-6 relative of 1.
- Steady-state tracking identity: for scenarios A, B and C,
  steady_control(A, B) * (B(1)/A(1)) = 1 within 1e-9 (real anchors
  residual exactly 0), and scenario B satisfies u(k) = u* for every
  k >= 2 within 1e-9.
- Error identities: for each scenario, |e(k) - 1.0| <= 1e-9 for
  0 <= k < d and |e(k)| <= 1e-9 for k >= d; sum(e) = d within 1e-6
  relative.
- Exact dict key sets for deadbeat_design ({n, m, d, a_desc, b_desc,
  num_e, den_u, mu0, d_num_desc, d_den_desc, char_poly_desc, u_star,
  plant_dc_gain}), settling_report ({settling_sample,
  settling_time_s, y_at_settling, max_dev_after_settling, settled}),
  control_effort ({u0, max_abs_u, u_final}), simulate ({y, e, u, k})
  and admissibility_check.
- ValueErrors: deadbeat_design with UNSTABLE_A, BOUNDARY_A (pole on the
  unit circle), NONMINIMUM_PHASE_B (zero at z = -2), BOUNDARY_ZERO_B
  (zero on the unit circle), DEG3_A (degree 3), a non-strictly-proper
  plant, an empty A, and a zero leading A coefficient; simulate with
  ts = 0.0, ts = -0.01, reference = "ramp", steps = 1, and an
  inadmissible plant (UNSTABLE_A); settling_report on a history too
  short to cover sample d (real guard raised True on every case).
  Every inadmissible-plant ValueError carries the verdict reason.
- Determinism: two identical simulate(A, B) runs are bitwise identical
  in y, e and u; the module imports nothing beyond math; no RNG.
- Run the contract test under BOTH interpreters (/usr/bin/python3
  3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3). All asserts above
  are tolerance-based (assertAlmostEqual/math.isclose) and must hold
  on both; the prep anchor output is byte-identical on both
  interpreters.

## Corpus fragment (eval/hit1-wave46-deadbeat-control.yaml)

Query 1 (copy verbatim from the receipt gate e):
  "design the deadbeat-control law for the discretized plant: place
  all closed loop poles at the origin of the z plane so the output
  settles in a finite number of sample periods and compute the
  minimum-settling-time control sequence"
  intent: "gnc-autonomy; deadbeat-control law for a discretized plant
  with all closed loop poles at the origin of the z plane
  (pole-placement-at-origin), the finite-settling-time output settling
  in a finite number of sample periods, computing the
  minimum-settling-time control sequence"
  expected_skill: "gnc-autonomy/control/deadbeat-control"
Query 2 (copy verbatim from the receipt gate e):
  "compute the z-domain deadbeat controller for the digital loop:
  solve the deadbeat design equation so the finite-settling-time
  response reaches the reference in N samples and report the control
  sequence"
  intent: "gnc-autonomy; z-domain-deadbeat controller for the digital
  loop solving the deadbeat design equation so the
  finite-settling-time response reaches the reference in N samples,
  reporting the control sequence"
  expected_skill: "gnc-autonomy/control/deadbeat-control"
Task ids: w46-deadbeat-control-1 and -2. Prep grep (re-verified at
spec time): deadbeat-control, finite-settling-time,
pole-placement-at-origin, minimum-settling-time and z-domain-deadbeat
appear in NO existing eval/hit1-corpus.yaml task (grep count 0 per
token), in NO skill file (whole-tree count 0, exit 1, receipt gate a)
and in NO wave46-specs file written so far; the digital-control-design
corpus tasks route on the zoh / tustin / discrete-pid / sample-rate
tokens and the existing corpus theft audit is 0 of 1266 reroutes
(receipt gate e: sim Hit@1 27.5 vs 15.0 and 18.0 vs 11.0 against
digital-control-design), so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a deadbeat-control law
for a discrete-time plant" and include the outputs in the Claim. First
tag: deadbeat-control. Additional tags EXACTLY as the receipt gate (f)
lists them: finite-settling-time, pole-placement-at-origin,
minimum-settling-time, z-domain-deadbeat. NEVER single generic words
(control, controller, deadbeat alone as a bare word, settling, pole,
origin, digital, loop, plant, discrete, sample, response, sequence
alone) and NEVER the sibling-owned compounds: zero-order-hold, zoh,
z-transform, tustin, tustin-bilinear-emulation, bilinear,
frequency-prewarping, prewarping, discrete-pid, sample-rate-selection,
unit-circle-stability, sampled-data-control and the sibling's own name
tag digital-control-design (digital-control-design owns ZOH
discretization, Tustin emulation, discrete PID coefficient forms, the
unit-circle stability verdict and the sample-rate rule; this leaf
consumes already-discrete plants and never claims those verbs); and
none of the rest of the pack's vocabulary: pid, ziegler-nichols,
ultimate gain, anti-windup, lead-lag, root-locus, bode, nyquist,
gain-margin, phase-margin, gain-scheduling, control-allocation,
observer-gain, luenberger, controllability, observability, mrac,
model-reference-adaptive, l1-adaptive-control, state-predictor,
projection-based-adaptation-law (the fixed-gain, analysis, MRAC and L1
siblings). 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term, action verb present. Recommended wording (outputs in Claim
order): "Use when you must design a deadbeat-control law for a
discrete-time plant given by its pulse transfer function: verify
admissibility for direct deadbeat synthesis (every plant pole and zero
strictly inside the unit circle), solve the deadbeat design equation
that places every closed loop pole at the origin of the z plane, form
the finite-settling-time controller difference equation from the plant
polynomials, and simulate the closed loop to confirm the output reaches
and holds the reference in the minimum number of sample periods with
the minimum-settling-time control sequence. Produces the admissibility
verdict, the controller coefficients, the settling sample and settling
time, the step response and control effort histories, the steady-state
tracking check and the control effort summary that gate a deadbeat
digital control assessment. Trigger: deadbeat-control,
finite-settling-time, pole-placement-at-origin, minimum-settling-time,
z-domain-deadbeat." The sibling phrase triggers "zero order hold",
"zoh", "z transform", "tustin bilinear emulation", "frequency
prewarping", "discrete pid", "unit circle stability" and "sample rate
selection" must not appear as routing keywords (the quoted fence text
above is documentation, not routing vocabulary); the deadbeat design
equation, the pole-placement-at-origin and the minimum-settling-time
control sequence are this leaf's own identity and must stay, always
referring to the direct deadbeat synthesis of a plant pulse transfer
function, never to a discretization, an emulation or a discrete PID
coefficient computation. The admissibility gate (pole and zero moduli
strictly inside the unit circle) is a design prerequisite of the
deadbeat synthesis and must never be presented as a general stability
verdict on sampled poles, which is the sibling's unit-circle check.

FORBIDDEN TOKENS (belong to siblings): zero-order-hold, zoh,
z-transform, tustin, bilinear, frequency-prewarping, discrete-pid,
sample-rate-selection, unit-circle-stability, sampled-data-control,
digital-control-design (digital-control-design); pid, ziegler-
nichols, anti-windup, gain margin, phase margin, s-domain pole
placement for a first or second order plant (pid-control-design,
frequency-response-design, python-control-design); lead-lag,
root locus (lead-lag-compensation, root-locus-design); gain
scheduling, scheduling variable (gain-scheduling); control
allocation, redundancy (control-allocation); observer gain,
Luenberger, Kalman filter gain (observer-design); controllability,
observability, eigenvalues (state-space-analysis); mrac,
model-reference adaptive, adaptive gains (adaptive-control); L1
adaptive, state predictor, projection adaptation (l1-adaptive-
control). The outputs of this leaf are the admissibility verdict, the
deadbeat controller difference-equation coefficients, the settling
sample and settling time, the closed-loop step and control effort
histories and the steady-state tracking check of the direct deadbeat
synthesis; no output is a discretized plant, an emulated compensator,
a discrete PID gain set, a general stability verdict, a sample-rate
verdict, a scheduled gain, an observer gain or an adaptive gain.
