# Wave-47 leaf spec: h-infinity-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/h-infinity-control/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, l1-adaptive-control, lead-lag-compensation,
  observer-design, pid-control-design, python-control-design,
  root-locus-design, state-space-analysis; adjacent optimal-control pack
  lqr-design, lqg-design, loop-transfer-recovery, model-predictive-control).
  Zero-owner greps re-verified at spec time at HEAD 4e20a835:
  `rg -i -l 'h-infinity|h_inf|hinfsyn|mixed-sensitivity|gamma-iteration|
  generalized-plant' skills/ -g 'SKILL.md'` returns ZERO hits (exit 1) and
  the same tokens return 0 of 1286 matching tasks in eval/hit1-corpus.yaml:
  no leaf anywhere in the tree owns worst-case H-infinity norm analysis or
  mixed-sensitivity S/KS weighting, which is the exact gap this leaf closes.
- Provenance: wave-47 recon receipt task-3 GO rank 4, CONDITIONAL, lines
  243-268: "H-infinity synthesis (DGKF two-Riccati) is zero-owner tree-wide
  and zero in the corpus, the control pack has no robust-synthesis leaf
  (adaptive-control and l1-adaptive-control own adaptation, not worst-case
  norm-bounded synthesis), but its second Hit@1 query margin is only 1.5
  points, so it is ranked conditional: GO if the pool takes a 4th gnc leaf
  this wave AND the spec hardens the description wording." The conditional
  Hit@1 gate was re-run FRESH at spec time over the real 647-SKILL.md index
  plus the hypothetical candidate (deterministic token router replicated
  from scripts/router_eval.py: hyphen-preserving tokens, stopword filter,
  tag weight 3, name weight 2, description weight 1, body weight 0.5,
  phrase bonus 4, tie-break path asc; candidate with no body, so the
  measured margins are conservative). Both wordable corpus queries below
  Hit@1 at the candidate with margins far above the required 3 points:
  Q1 at 25.0 vs 10.0 (gnc-autonomy/control/frequency-response-design),
  margin 15.0; Q2 at 33.0 vs 12.5 (gnc-autonomy/control/deadbeat-control),
  margin 20.5. Reworded robustness variants still Hit@1 at 9.5 and 7.5
  point margins. Theft audit over all 1286 eval/hit1-corpus.yaml tasks with
  the candidate added to the index: 0 tasks reroute. GATE PASSED. The
  receipt's fragile Q2 margin (1.5 vs observer-design) is superseded by the
  hardened description, which carries gamma-iteration, s-over-ks-weighting
  and imaginary-axis-frequency-response tokens.
- Published deterministic anchor, receipt gate (d) (summary-only, with a
  SCOPE NOTE): the receipt summarized Doyle, Glover, Khargonekar and
  Francis, "State-Space Solutions to Standard H2 and H-infinity Control
  Problems", IEEE Transactions on Automatic Control 34(8):831-847, 1989
  (two algebraic Riccati equations with the spectral-radius coupling
  condition rho(X_inf Y_inf) < gamma^2 and the central-controller
  formulas). This leaf DOES NOT implement the DGKF two-Riccati synthesis:
  solving the two AREs of general state-space synthesis needs a solver the
  pure-stdlib rule cannot provide, and no such solver is claimed. The leaf
  is resooped to the deterministic analysis side of the same mixed-
  sensitivity method, which IS closed form in pure Python: assemble the
  S/KS/T channels of the SISO loop, build the standard sensitivity weight
  and control-effort weight functions from their corner parameters, and
  compute the H-infinity norms of the weighted channels by gamma iteration
  over the imaginary axis, reporting the achieved gamma of the S/KS
  weighting and the bound verdict. Public science, summary-only: the
  mixed-sensitivity formulation |S| below 1/|W1| and |KS| below 1/|W2| at
  every frequency is the standard H-infinity loop-shaping statement
  (textbook treatment Skogestad and Postlethwaite, Multivariable Feedback
  Control, Wiley, 2005, chapter 9, and the DGKF paper as the synthesis
  context); no standard text is reproduced.
- Claim fences (quoted from the sibling SKILL.md frontmatter descriptions
  and bodies at spec time, FRESH reads; the nearest owners fence out gain
  design, margin measurement, Riccati optimal control, loop recovery and
  receding-horizon optimization, none of which is a worst-case norm
  computation):
  - pid-control-design (this pack) is the GAIN-DESIGN fence: its
    frontmatter description reads "Use when the task is PID tuning,
    proportional integral derivative terms, anti-windup, integrator
    clamping, pole placement, or gain and phase margin checks. Design PID
    controller gains for aerospace flight and GNC control loops: compute
    the controller output from the proportional, integral, and derivative
    error terms, tune the gains from the plant model with Ziegler-Nichols
    using the ultimate gain and ultimate period, or place closed loop poles
    directly for a first or second order plant, add integrator anti-windup
    clamping, and check the gain margin and phase margin of the loop." Gain
    synthesis and classical margins, no weighted worst-case norm anywhere.
  - frequency-response-design (this pack) is the MARGIN fence: its
    frontmatter description reads "Use when the task is bode analysis,
    frequency response, gain crossover, phase crossover, gain margin, phase
    margin, or stability from the margins. Compute the Bode frequency
    response of an open loop transfer function for flight control design:
    evaluate the magnitude and phase at a frequency from the numerator and
    denominator coefficients at s = j*w, find the gain crossover and phase
    crossover frequencies, derive the gain margin in dB and the phase
    margin in degrees, and judge closed loop stability from the margins for
    the canonical type-1 plant K/(s(s+1)(s+2))." Single-frequency magnitude
    and phase evaluation and margin verdicts; it evaluates an open loop at
    isolated frequencies and never searches a weighted closed-loop channel
    for its worst-case peak.
  - lqr-design (optimal-control pack) is the REGULATOR-ARE fence: its
    frontmatter description reads "Use when you must design an LQR
    state-feedback gain matrix for a scalar-input two-state system such as
    spacecraft attitude control: solve the algebraic Riccati equation for
    the cost weights, compute the gain matrix, verify closed-loop stability
    of the regulated system, and assess the Q over R weighting trade." Its
    model is the ARE A'P + PA - P B R^-1 B' P + Q = 0 and the gain
    K = R^-1 B' P for u = -K x; a state-feedback gain from a quadratic
    cost, no transfer-function channel norm and no gamma iteration.
  - lqg-design (optimal-control pack) is the COMPENSATOR-ARE fence: its
    frontmatter description reads "Use when you must design a
    linear-quadratic-Gaussian output-feedback compensator for a two-state
    system whose state is not fully measurable: solve the regulator
    algebraic Riccati equation for the symmetric stabilizing P and the gain
    K from the quadratic cost weights, solve the filter (Kalman) algebraic
    Riccati equation for the error covariance S and the estimator gain L
    from the process and measurement noise covariances, assemble the
    dynamic output-feedback compensator state-space realization, and verify
    the separation principle that the closed-loop eigenvalues are the union
    of the regulator and estimator poles." Two Riccati equations of optimal
    estimation and regulation, not the worst-case S/KS analysis of a given
    loop.
  - loop-transfer-recovery (optimal-control pack) is the RECOVERY fence:
    its body states "The adjacent gnc-autonomy/control/frequency-response-
    design leaf measures the margins of a given open loop transfer function
    and never synthesizes or recovers a loop; here the loop-shape match is
    judged by the grid-max complex mismatch M(q), never by margin numbers."
    LTR reshapes a recovered LQG loop toward a full-state target by
    inflating a filter noise weight and re-solving the filter Riccati
    equation; its loop comparison is the grid-max mismatch of one complex
    transfer against another, and neither it nor any other sibling computes
    an H-infinity norm or evaluates a weighted S/KS bound.
  - model-predictive-control (optimal-control pack) is the HORIZON fence:
    its frontmatter description reads "Use when you must design a model
    predictive control (MPC) receding horizon controller for a linear
    discrete time system such as a double integrator: choose the finite
    horizon quadratic cost with prediction horizon and control horizon,
    enforce input constraints and state constraints, and run a closed loop
    simulation." Discrete-time constrained optimization over a horizon, no
    frequency-domain worst-case norm.
  - observer-design (this pack) is the ESTIMATOR fence: its frontmatter
    description reads "Use when you must design a full-order Luenberger
    state observer for a linear time-invariant system whose states are not
    all directly measurable: build the observability matrix and check
    observability, compute the estimator gain matrix by pole placement with
    the Ackermann formula..." State estimation for feedback, never a
    transfer-function norm.
  The new leaf's plant and candidate controller are GIVEN inputs, never
  tuned, placed, recovered or estimated here; the loop channels are
  assembled as rational functions and judged by their worst-case weighted
  peaks only.
- Standards id: arp4754a (ARP4754A, Development of Civil Aircraft and
  Systems, reference-only and present in standards-map.yaml, grep
  'id: arp4754a' at line 38, re-verified at spec time; the control-pack
  convention shared with the smith-predictor and deadbeat-control leaves).
  Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Run the H-infinity mixed-sensitivity norm review of a SISO feedback loop:
given the plant transfer function G(s), a candidate controller transfer
function K(s) and two weighting functions (the sensitivity weight W1 and
the control-effort weight W2), assemble the closed-loop channels of
L = G K over the characteristic polynomial char = g_den k_den +
g_num k_num, verify the loop is strictly stable, and compute the H-infinity
norms of the weighted sensitivity function W1 S and the weighted control
sensitivity W2 KS by gamma iteration over the imaginary axis: |H(jw)|^2 is
a rational function of x = w^2, every interior peak sits at a real root
x >= 0 of the stationary equation P(x) = A'(x)B(x) - A(x)B'(x) = 0 on the
swept range, and the
norm is the square root of the largest of the DC magnitude, the interior
peak magnitudes and the high-frequency limit of the channel. Produces the
stability verdict of the loop, the weighted-sensitivity norm ||W1 S||_inf,
the weighted-control-sensitivity norm ||W2 KS||_inf, the achieved gamma of
the mixed-sensitivity weighting as the larger of the two norms, and the
bound verdict gamma < 1, which certifies that |S(jw)| stays below
1/|W1(jw)| and |KS(jw)| stays below 1/|W2(jw)| at every frequency on the
swept imaginary axis. The leaf also builds the two standard weight
functions from their corner parameters by closed form: W1(s) =
(s/ms + wb)/(s + wb as_) with |W1(j0)| = 1/as_ and |W1(j inf)| = 1/ms
(low-frequency sensitivity level and high-frequency peak bound), and
W2(s) = (s + wbc a2)/(s/mu2 + wbc) with |W2(j0)| = a2 and |W2(j inf)| = mu2
(control effort penalized increasingly above the corner wbc). The plant,
the controller and the weight parameters are inputs; the controller is
never synthesized. Does NOT do: controller synthesis of any kind, including
the DGKF two-Riccati H-infinity controller and its central-controller
formulas (not implemented: no algebraic Riccati equation solver lives in
this leaf; lqr-design, lqg-design and loop-transfer-recovery own the ARE
vocabulary and solutions of the family); mu-synthesis, D-K iteration,
structured singular value or any uncertainty-model analysis; linear matrix
inequality (LMI) formulations; PID gain design, pole placement, anti-windup
or integrator clamping (pid-control-design); Bode magnitude and phase
evaluation at a single frequency, gain margin, phase margin, gain crossover
or phase crossover verdicts (frequency-response-design); LQG compensator
assembly or the separation principle (lqg-design); loop-transfer recovery
or target-loop matching (loop-transfer-recovery); receding-horizon QP
control (model-predictive-control); observer or estimator gain design
(observer-design). The loop model is the continuous-time SISO rational
feedback loop with no pole-zero cancellation in L (the user must supply a
plant-controller pair without cancellation, else the non-minimal channel
representations evaluate 0/0 at the cancelled dynamics); the norm search
covers the declared imaginary-axis sweep w in [1e-4, 1e4] rad/s plus the
DC point and the high-frequency limit.

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG. Every polynomial is a list
of float coefficients in descending powers of the variable (index 0 the
highest power). Module constants, pin exactly:
- ROUTH_PIVOT_EPS = 1e-12: a Routh first-column element at or below this
  magnitude reports not-strictly-stable.
- ROUTH_ROW_EPS = 1e-14: a computed Routh row whose every element is at or
  below this magnitude is an all-zero (singular) row and reports
  not-strictly-stable.
- SWEEP_X_MIN = 1e-8 and SWEEP_X_MAX = 1e8: the stationary-point grid in
  x = w^2 spans these bounds, i.e. the imaginary-axis sweep in angular
  frequency runs w in [1e-4, 1e4] rad/s.
- SWEEP_POINTS = 801: grid points, geometrically spaced between
  SWEEP_X_MIN and SWEEP_X_MAX.
- BISECT_ITER = 200 and ROOT_TOL_REL = 1e-13: the bisection refinement of
  each stationary-point bracket runs at most BISECT_ITER passes and stops
  early when the bracket width is at most ROOT_TOL_REL times (1 + |mid|).

Defining relations (pin these exactly; every function derives from them):
- Loop: plant G = g_num/g_den, candidate controller K = k_num/k_den,
  loop transfer L = G K = (g_num k_num)/(g_den k_den). The characteristic
  polynomial is char = g_den k_den + g_num k_num (polynomial addition and
  multiplication, both coefficient lists in descending order).
- Channels over the common denominator char: S = 1/(1 + L) =
  (g_den k_den)/char, T = L/(1 + L) = (g_num k_num)/char and
  KS = K/(1 + L) = (k_num g_den)/char (the k_den factor of K cancels the
  k_den already inside S; the representations are not further reduced, so
  a loop with pole-zero cancellation in L is rejected by the caller).
  Identity: S + T = 1 exactly as polynomials, s_num + t_num = char.
- Stability: the loop is strictly stable exactly when routh_stable(char)
  is True (Routh-Hurwitz first-column test on the characteristic
  polynomial; every first-column element strictly positive).
- H-infinity norm of a stable proper channel H = num/den: write
  A(x) = hermitian square of num and B(x) = hermitian square of den,
  where |num(jw)|^2 = A(w^2) and |den(jw)|^2 = B(w^2) are polynomials in
  x = w^2 built from the coefficient pairs: for p(s) with ascending
  coefficients q[m] (coefficient of s^m), the coefficient of x^m in
  |p(jw)|^2 is (-1)^m times the alternating sum over i + j = 2m of
  q[i] q[j] (-1)^i, and all odd-power coefficients vanish. Then
  |H(jw)|^2 = A(x)/B(x) with B(x) > 0 for every x >= 0 (strict stability
  of den puts no pole on the imaginary axis). The stationary equation of
  the squared magnitude is P(x) = A'(x)B(x) - A(x)B'(x) = 0. The norm is
  the square root of the largest of: the DC value A(0)/B(0), the value at
  every real root x >= 0 of P bracketed by a sign change of P on the
  geometric grid from SWEEP_X_MIN to SWEEP_X_MAX (bracket refined by
  bisection to ROOT_TOL_REL) and the high-frequency limit (lead-ratio
  squared |num[0]/den[0]|^2 when the degrees are equal, else 0). This is
  the gamma-iteration search: bisection shrinks each frequency bracket
  around a worst-case peak of the imaginary-axis response. Deterministic
  and closed form; the DC point and the infinity limit are included
  explicitly because they can carry the worst case (example: a type-1
  loop has |T(j0)| = 1).
- Weight functions, closed form from corner parameters:
  sensitivity_weight(ms, wb, as_): W1(s) = (s/ms + wb)/(s + wb as_) with
  |W1(j0)| = 1/as_, |W1(j wb)| = sqrt(1 + 1/ms^2)/sqrt(1 + as_^2) and
  |W1(j inf)| = 1/ms. control_weight(a2, wbc, mu2): W2(s) = (s + wbc
  a2)/(s/mu2 + wbc) with |W2(j0)| = a2 and |W2(j inf)| = mu2. All six
  parameters must be strictly positive; mu2 is the high-frequency control
  penalty level, a2 the DC level, wbc the corner.
- Weighted norms: ||W1 S||_inf = hinfinity_norm(w1_num s_num,
  w1_den char) and ||W2 KS||_inf = hinfinity_norm(w2_num ks_num,
  w2_den char). Achieved gamma = max of the two; bound verdict gamma < 1.
  Verdict meaning: |W1(jw) S(jw)| at most gamma at every swept frequency,
  so gamma < 1 certifies |S(jw)| < 1/|W1(jw)| and |KS(jw)| < 1/|W2(jw)|
  pointwise (the standard S/KS mixed-sensitivity statement).
- The norm search is over the declared sweep only (w in [1e-4, 1e4] rad/s
  plus the DC point and the infinity limit); dynamics with worst-case
  peaks beyond 1e4 rad/s are outside the declared scope and the leaf does
  not claim to find them.

Functions (signatures, return shapes, rejections):
- routh_stable(coeffs) -> bool
  Routh-Hurwitz strict stability of a real polynomial, coefficients
  descending. False for: an empty or all-zero list, a negative leading
  coefficient after sign normalization (the polynomial is multiplied by
  -1 to make the leading coefficient positive before the table), any
  first-column element at or below ROUTH_PIVOT_EPS, any all-zero computed
  row (max |entry| at most ROUTH_ROW_EPS, the marginal-stability case),
  and a constant polynomial at or below ROUTH_PIVOT_EPS. No ValueError:
  verdicts only.
- eval_transfer(num, den, s) -> complex
  Evaluate num(s)/den(s) at complex s by Horner on both coefficient lists.
  ValueError when the denominator evaluates to exactly zero at s
  (message "transfer function denominator is zero at s = ...").
- loop_channels(g_num, g_den, k_num, k_den) -> dict
  Returns {"char_poly", "s_num", "s_den", "t_num", "t_den", "ks_num",
  "ks_den"} with s_den = t_den = ks_den = char_poly and the numerators
  built by the relations above (char_poly = g_den k_den + g_num k_num,
  s_num = g_den k_den, t_num = g_num k_num, ks_num = k_num g_den).
  No rejection beyond the polynomial operations.
- sensitivity_weight(ms, wb, as_) -> (num, den)
  W1 as above. ValueError when any of ms, wb, as_ is not strictly
  positive (message names the parameter and the received value).
- control_weight(a2, wbc, mu2) -> (num, den)
  W2 as above. ValueError when any of a2, wbc, mu2 is not strictly
  positive.
- hinfinity_norm(num, den) -> float
  The H-infinity norm of the stable proper SISO transfer function num/den
  by the stationary-equation gamma-iteration search above. ValueError when
  the numerator degree exceeds the denominator degree (improper, message
  "transfer function must be proper: numerator degree N above denominator
  degree M") and when routh_stable(den) is False (message "H-infinity norm
  requires a strictly stable denominator (all poles in the open left half
  plane)").
- mixed_sensitivity_gamma(channels, w1, w2) -> dict
  channels is a loop_channels dict, w1 and w2 are (num, den) tuples.
  Returns {"w1s_norm": ||W1 S||_inf, "w2ks_norm": ||W2 KS||_inf,
  "gamma": the larger of the two, "verdict": gamma < 1.0}. Propagates the
  hinfinity_norm ValueErrors (an unstable char_poly raises through the
  first weighted-norm call, so a caller wanting the stability verdict
  checks routh_stable(channels["char_poly"]) before calling).

## Identities to test (closed form, exact; checkable without the builder
module)

- S + T = 1: s_num + t_num equals char_poly coefficient by coefficient,
  and |S(jw) + T(jw) - 1| is below 1e-9 at every sampled w. Real anchors
  on the worked loop: S + T = (1+0j) at w = 0.1 and (0.9999999999999999
  + 0j) at w = 1 and w = 5.
- Weight closed forms: |W1(j0)| = 1/as_ (1000.0 at as_ = 1e-3),
  |W1(j inf)| = 1/ms (0.4 at ms = 2.5), |W2(j0)| = a2 (0.1),
  |W2(j inf)| = mu2 (1.0). Also |W1(j wb)| = sqrt(1 + 1/ms^2)/
  sqrt(1 + as_^2) = 1.0770329614269009 at ms = 2.5, wb = 0.3,
  as_ = 1e-3.
- Type-1 velocity asymptote: with one integrator in L and Kv = lim s L =
  K(0) = k z/(p1 p2), the sensitivity obeys S(jw) about jw/Kv at low
  frequency, so |S(jw)| Kv / w tends to 1 as w tends to 0. Real anchor on
  the worked loop: |S(jw)| Kv/w = 0.9999993828127061 at w = 1e-3 and
  0.999938283310422 at w = 1e-2, Kv = 0.5.
- Mixed-sensitivity flat band: where |W1| about wb/w (wb as_ far below w
  below wb) and S about jw/Kv, the product |W1(jw) S(jw)| is flat at
  wb/Kv. Real anchors on the worked loop (wb = 0.3, Kv = 0.5,
  wb/Kv = 0.6): |W1S(jw)| = 0.5997464724424371 at w = 0.01,
  0.6003939878705405 at w = 0.05 and 0.601583811863733 at w = 0.1, and
  the computed norm ||W1 S||_inf = 0.6210716713301313 lies above the band
  and below 1. Raising wb to 1.0 drives the band to wb/Kv = 2.0 and the
  computed gamma to 1.9979285867334802 (the fail sibling below).
- Norm identity cases that validate the stationary machinery:
  hinfinity_norm([1], [1, 1]) = 1.0 (DC carry, |1/(jw+1)| peaks at
  w = 0); hinfinity_norm([1, 2], [1, 1]) = 2.0 (|(jw+2)/(jw+1)| peaks at
  w = 0); the resonant second-order system 1/(s^2 + 0.2 s + 1) has the
  closed-form peak 1/(2 zeta sqrt(1 - zeta^2)) = 5.025189076296056 at
  zeta = 0.1, reproduced by hinfinity_norm([1], [1, 0.2, 1]) within 1e-9
  relative.
- Worst-case bound semantics: every computed norm is at least every
  |H(jw)| sampled on a 101-point geometric sweep from 1e-4 to 1e4 rad/s
  plus the DC value (the norm cannot underestimate the response). Real
  anchor: max |W1S| over the coarse sweep = 0.6210695376871158 is below
  the norm 0.6210716713301313.
- Stability verdicts: routh_stable([1, 3, 3, 1]) True ((s+1)^3),
  routh_stable([1, 0, 1]) False (jw-axis poles), routh_stable([1, 1, 1,
  1]) False (roots -1 and +/-j), routh_stable([1, 11, 26, 24, 8]) True
  (the worked loop).

## Worked example

Loop under review, all numbers real: plant G(s) = 1/(s(s+1)) (g_num [1.0],
g_den [1.0, 1.0, 0.0]), candidate controller K(s) = 8(s+1)/((s+2)(s+8))
(k_num [8.0, 8.0], k_den [1.0, 10.0, 16.0], a lead-lag with K(0) = 0.5,
strictly proper so KS rolls off at high frequency). Sensitivity weight
W1(s) = (s/2.5 + 0.3)/(s + 3e-4) (ms = 2.5, wb = 0.3 rad/s,
as_ = 1e-3), control weight W2(s) = (s + 0.2)/(s + 2) (a2 = 0.1,
wbc = 2.0 rad/s, mu2 = 1.0). The loop is strictly stable; the S/KS review
PASSES with gamma 0.7779822129233023, dominated by the control channel.

All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_h_infinity_control.py (pure stdlib, math only,
deterministic, no RNG, exit 0), run once and quoted as printed; the anchor
reproduces every number here, and a second run returns byte-identical
output under /usr/bin/python3 (3.9.6), the pyenv 3.12.9 interpreter and
the session python3 (3.12.9):

- loop_channels(G, K): char_poly [1.0, 11.0, 26.0, 24.0, 8.0]
  (s^4 + 11 s^3 + 26 s^2 + 24 s + 8), routh_stable True. The velocity
  constant of the loop is Kv = lim s L = K(0) = k z/(p1 p2) =
  8/(2*8) = 0.5 s^-1.
- Weight functions as built: sensitivity_weight(2.5, 0.3, 1e-3) returns
  ([0.4, 0.3], [1.0, 0.0003]); control_weight(0.1, 2.0, 1.0) returns
  ([1.0, 0.2], [1.0, 2.0]).
- Weight closed forms: |W1(j0)| = 1000.0 (1/as_), |W1(j inf)| = 0.4
  (1/ms), |W2(j0)| = 0.1 (a2), |W2(j inf)| = 1.0 (mu2).
- Weighted sensitivity norm: ||W1 S||_inf = 0.6210716713301313, worst
  case at w = 0.571775 rad/s. The flat band |W1S| about wb/Kv = 0.6
  carries the pass: |W1S(jw)| = 0.5997464724424371 at w = 0.01,
  0.6003939878705405 at w = 0.05, 0.601583811863733 at w = 0.1, and the
  worst-case peak 0.6210716713301313 sits just above the band near
  w = 0.571775 where the low-frequency asymptote bends over.
- Weighted control norm: ||W2 KS||_inf = 0.7779822129233023, worst case
  at w = 4.198892 rad/s: the control-sensitivity peak where the strictly
  proper controller rolls off against the rising control weight (W2 rises
  from 0.1 at DC toward mu2 = 1.0 above the corner wbc = 2 rad/s).
- Achieved gamma = max(0.6210716713301313, 0.7779822129233023) =
  0.7779822129233023 with verdict True (pass): the loop satisfies
  |S(jw)| < 1/|W1(jw)| and |KS(jw)| < 1/|W2(jw)| at every frequency of
  the swept imaginary axis.
- Unweighted channels for context: ||S||_inf = 1.2187761291690518 at
  w = 1.287314 rad/s (the classical sensitivity peak above 1 near the
  crossover region) and ||T||_inf = 1.0 at w = 0 (the type-1 tracking
  identity |T(j0)| = 1); the S + T = 1 identity holds exactly at the
  polynomial level and pointwise at the sampled frequencies.
- Low-frequency asymptote check: |S(jw)| Kv/w = 0.9999993828127061 at
  w = 1e-3, confirming S about jw/Kv with Kv = 0.5.
- Fail sibling (the verdict False path): the same loop with the same W2
  but the demanding sensitivity weight W1(s) = (s/2.5 + 1)/(s + 1e-3)
  (wb raised from 0.3 to 1.0 rad/s) drives the flat band to
  wb/Kv = 2.0: ||W1 S||_inf = 1.9979285867334802, ||W2 KS||_inf =
  0.7779822129233023 (unchanged), gamma = 1.9979285867334802, verdict
  False: the tracking requirement wb = 1 rad/s exceeds the loop's
  velocity constant Kv = 0.5 s^-1, so the weighted sensitivity violates
  the unit bound and the candidate controller does not meet the S/KS
  specification. The reviewer reports the achieved gamma and the verdict;
  the controller itself is not altered.
- Determinism: mixed_sensitivity_gamma on the worked loop returns
  identical dicts run to run (gamma and both norms bit-identical).
- ValueErrors with real messages (module output, quoted as printed):
  hinfinity_norm([1.0, 0.0, 0.0], [1.0, 1.0]) raises "transfer function
  must be proper: numerator degree 2 above denominator degree 1";
  hinfinity_norm([1.0], [1.0, 0.0, -1.0]) raises "H-infinity norm
  requires a strictly stable denominator (all poles in the open left half
  plane)"; eval_transfer([1.0], [1.0, -1.0], complex(1.0, 0.0)) raises
  "transfer function denominator is zero at s = (1+0j)".

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of /tmp/w47spec/anchor_h_infinity_control.py
(stdlib math only, deterministic, exit 0, identical under both
interpreters, no exact-float equality anywhere).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative: loop_channels(G, K)
   gives char_poly [1.0, 11.0, 26.0, 24.0, 8.0] and routh_stable is True;
   sensitivity_weight(2.5, 0.3, 1e-3) returns ([0.4, 0.3],
   [1.0, 0.0003]) within 1e-12; control_weight(0.1, 2.0, 1.0) returns
   ([1.0, 0.2], [1.0, 2.0]) within 1e-12; ||W1 S||_inf =
   0.6210716713301313, ||W2 KS||_inf = 0.7779822129233023, gamma =
   0.7779822129233023 and verdict True.
2. Fail sibling within 1e-6 relative: with sensitivity_weight(2.5, 1.0,
   1e-3), ||W1 S||_inf = 1.9979285867334802, ||W2 KS||_inf =
   0.7779822129233023, gamma = 1.9979285867334802, verdict False; the
   flat-band bound wb/Kv = 2.0 (Kv = 0.5) exceeds the computed gamma by
   less than 0.005 in absolute terms.
3. S + T = 1 identity: s_num + t_num equals char_poly coefficient by
   coefficient within 1e-12, and |S(jw) + T(jw) - 1| below 1e-9 at
   w = 0.1, 1.0 and 5.0; ||T||_inf = 1.0 within 1e-9 (the type-1 DC
   carry) and ||S||_inf = 1.2187761291690518 within 1e-6 relative.
4. Weight closed forms within 1e-9 relative: |W1(j0)| = 1000.0,
   |W1(j inf)| = 0.4, |W2(j0)| = 0.1, |W2(j inf)| = 1.0, and
   |W1(j wb)| = sqrt(1 + 1/ms^2)/sqrt(1 + as_^2) = 1.0770329614269009.
5. Velocity asymptote: |S(jw)| Kv/w with Kv = k z/(p1 p2) = 0.5 equals
   0.9999993828127061 at w = 1e-3 and 0.999938283310422 at w = 1e-2,
   both within 1e-6 relative (S about jw/Kv as w tends to 0).
6. Mixed-sensitivity flat band: |W1S(jw)| = 0.5997464724424371 at
   w = 0.01, 0.6003939878705405 at w = 0.05 and 0.601583811863733 at
   w = 0.1, each within 1e-4 relative, and each within 5e-3 relative of
   wb/Kv = 0.6; the computed norm 0.6210716713301313 lies above all three
   band samples.
7. Norm machinery identity cases within 1e-9 relative:
   hinfinity_norm([1.0], [1.0, 1.0]) = 1.0 (DC carry);
   hinfinity_norm([1.0, 2.0], [1.0, 1.0]) = 2.0 (DC carry);
   hinfinity_norm([1.0], [1.0, 0.2, 1.0]) = 5.025189076296056, the
   closed-form resonant peak 1/(2 zeta sqrt(1 - zeta^2)) at zeta = 0.1.
8. Worst-case bound: on a 101-point geometric sweep of |W1S(jw)| from
   1e-4 to 1e4 rad/s the sweep maximum 0.6210695376871158 is at most the
   computed norm 0.6210716713301313 (times 1 + 1e-9), and the same
   inequality holds at w = 0 and for the fail sibling.
9. Routh verdicts: routh_stable([1.0, 3.0, 3.0, 1.0]) True;
   routh_stable([1.0, 1.0, 1.0, 1.0]) False; routh_stable([1.0, 0.0,
   1.0]) False; routh_stable([1.0, 11.0, 26.0, 24.0, 8.0]) True; a
   constant polynomial with a positive coefficient True and with a
   non-positive one False; an empty list False.
10. ValueErrors with the real messages quoted in the Worked example:
    improper transfer (hinfinity_norm numerator degree above denominator
    degree), unstable denominator (hinfinity_norm), denominator zero at s
    (eval_transfer), and non-positive weight parameters from
    sensitivity_weight and control_weight (ms, wb, as_, a2, wbc, mu2 each
    raise a ValueError naming the parameter).
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math; the
    module constants ROUTH_PIVOT_EPS = 1e-12, ROUTH_ROW_EPS = 1e-14,
    SWEEP_X_MIN = 1e-8, SWEEP_X_MAX = 1e8, SWEEP_POINTS = 801,
    BISECT_ITER = 200 and ROOT_TOL_REL = 1e-13 fixed as above. No
    exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it exits 0.
    Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.12.9/bin/python3). The prep anchor output was
    verified byte-identical under 3.9.6, 3.12.9 (pyenv) and 3.12.9
    (session python3) at spec time.

## Corpus fragment (eval/hit1-wave47-h-infinity-control.yaml)

Query 1 (copy verbatim, the gate-passing text sim-verified at spec time):
  "compute the h-infinity-norm of the weighted sensitivity function of the
  loop: given the sensitivity-weight and the control-effort-weight on the
  generalized plant, run the gamma-iteration over the imaginary-axis
  frequency response and report the worst-case-peak-gain of the weighted
  mixed-sensitivity channel"
  intent: "gnc-autonomy/control; h-infinity-control: the H-infinity norm
  of the weighted sensitivity function of the loop by gamma iteration over
  the imaginary-axis frequency response with the sensitivity weight and
  the control-effort weight of the generalized plant, reporting the
  worst-case-peak-gain of the weighted mixed-sensitivity channel"
  expected_skill: "gnc-autonomy/control/h-infinity-control"
Query 2 (copy verbatim):
  "verify the s-over-ks-weighting bounds of the candidate controller on
  the mixed-sensitivity loop: compute the h-infinity norm of the weighted
  sensitivity function and of the weighted control sensitivity by
  gamma-iteration frequency sweep, and check both weighted norms stay
  below one so the sensitivity bound holds"
  intent: "gnc-autonomy/control; h-infinity-control: the s-over-ks-
  weighting bounds of the candidate controller on the mixed-sensitivity
  loop, the H-infinity norms of the weighted sensitivity function and the
  weighted control sensitivity by gamma-iteration frequency sweep, and the
  check that both weighted norms stay below one so the sensitivity bound
  holds at every frequency"
  expected_skill: "gnc-autonomy/control/h-infinity-control"
Task ids: w47-h-infinity-control-1 and -2. Sim-verified margins at spec
time (deterministic router over the 647-SKILL.md index plus the candidate
with no body): Q1 25.0 vs 10.0 (frequency-response-design), margin 15.0;
Q2 33.0 vs 12.5 (deadbeat-control), margin 20.5; reworded variants 9.5
and 7.5. Theft audit with the candidate added to the index over all 1286
existing corpus tasks: 0 tasks reroute; zero existing task carries the
tokens h-infinity, gamma-iteration, mixed-sensitivity or s-over-ks
(re-verified by corpus grep at spec time). The sibling corpus tasks route
on tuning and margin language (pid-control-design), bode and
gain-margin/phase-margin language (frequency-response-design), Riccati
and gain-matrix language (lqr-design, w2 lqr1/lqr2), compensator and
separation-principle language (lqg-design), recovery and target-loop
language (loop-transfer-recovery), receding-horizon and QP language
(model-predictive-control), and deadbeat z-domain language (deadbeat-
control, w46-deadbeat-control-1/-2), none of which carries a worst-case
weighted norm search. Add one fence line to frequency-response-design and
one router row to skills/gnc-autonomy/SKILL.md at build time pointing
worst-case H-infinity norm analysis and mixed-sensitivity S/KS weighting
to the new leaf (the smith-predictor and deadbeat-control precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run the h-infinity mixed-
sensitivity norm analysis of a feedback loop:" and include the outputs in
the Claim order (the stability verdict of the loop, the weighted-
sensitivity norm ||W1 S||_inf, the weighted-control-sensitivity norm
||W2 KS||_inf, the achieved gamma as the larger of the two, and the bound
verdict when both weighted norms stay below one), then close with the
Trigger list. The plant, the candidate controller and the weight
parameters are given inputs, never synthesized, tuned, placed or
recovered; refer to the search as gamma iteration over the imaginary-axis
frequency response and to the channels as the weighted sensitivity and
the weighted control sensitivity, never as a state-space synthesis and
never as a Riccati solution; never reproduce ARP4754A or any textbook
text (reference-only). First tag: h-infinity-control. Metadata tags
EXACTLY the sim-verified set used to pass the conditional gate (nothing
else): h-infinity-control, h-infinity-norm, h-infinity, gamma-iteration,
mixed-sensitivity, s-over-ks-weighting, sensitivity-weighting,
control-effort-weighting, generalized-plant-weighting,
worst-case-peak-gain, imaginary-axis-frequency-response. Note the
deviation from the receipt gate (f) list on purpose: the receipt tags
h-infinity-control-synthesis, dgkf-two-riccati and central-h-infinity-
controller belong to the DGKF two-Riccati synthesis scope that this leaf
does not implement under the pure-stdlib rule, so they are excluded and
must never appear in tags, description or body (see FORBIDDEN TOKENS).
50-150 words, <=1000 chars, no em dash, never the banned sweep term of
the builder kit, action verb present. Recommended wording (127 words, 888
chars, verified at spec time, identical to the gate-sim candidate
description):

"Use when you must run the h-infinity mixed-sensitivity norm analysis of a
feedback loop: given the plant transfer function, a candidate controller,
the sensitivity weight and the control-effort weight, verify the closed
loop is stable and compute the h-infinity norms of the weighted
sensitivity functions by gamma iteration over the imaginary-axis
frequency response, locating the worst-case peak magnitude of each
channel. Produces the weighted-sensitivity norm, the weighted
control-sensitivity norm, the achieved gamma of the mixed-sensitivity
weighting as the larger of the two norms, and the bound verdict when both
weighted norms stay below one so the s-over-ks sensitivity bounds hold at
every frequency. Trigger: h infinity norm, gamma iteration, mixed
sensitivity weighting, s ks weighted bounds, sensitivity weight, control
weight, worst case peak gain, weighted loop analysis."

FORBIDDEN TOKENS (belong to siblings or the unimplemented synthesis
side): dgkf-two-riccati, h-infinity-control-synthesis, central-h-
infinity-controller, spectral-radius-coupling, two-riccati-solver,
hinfsyn and any claim that the leaf synthesizes an H-infinity controller
or solves an algebraic Riccati equation (no ARE solver is implemented;
lqr-design, lqg-design and loop-transfer-recovery own the Riccati
vocabulary and solutions of the family); mu-synthesis, d-k-iteration,
structured-singular-value, robust-stability-with-uncertainty,
uncertainty-model and any norm-bounded uncertainty analysis (out of
scope); lmi, linear-matrix-inequality, semidefinite-program and any LMI
formulation (out of scope); ziegler-nichols, ultimate-gain,
ultimate-period, pole-placement, anti-windup, integrator-clamp,
controller-gain-tuning and any PID gain design claim (pid-control-design;
the controller is a given input, never tuned or placed); bode-analysis,
gain-margin, phase-margin, gain-crossover, phase-crossover,
stability-from-the-margins and any single-frequency magnitude and phase
verdict (frequency-response-design); linear-quadratic-regulator,
linear-quadratic-gaussian, regulator-riccati, filter-riccati-gain,
kalman-filter, compensator-transfer-function, separation-principle,
output-feedback-compensator (lqr-design, lqg-design); loop-transfer-
recovery, full-state-loop-recovery, lqg-loop-shaping, recovery-gain-
tuning, target-feedback-loop, grid-max-mismatch (loop-transfer-recovery);
mpc, receding-horizon, prediction-horizon, quadratic-program, kkt-system,
active-set, constraint-handling (model-predictive-control); luenberger,
estimator-gain, ackermann, observability, error-dynamics,
state-estimation (observer-design); deadbeat-control, finite-settling-
time, z-domain-deadbeat (deadbeat-control). Never the bare single words
norm, gamma, weight, loop, control, sensitivity, stability, plant,
controller, frequency, peak or bound as standalone metadata tags, and
never claim that the norm search covers frequencies beyond the declared
imaginary-axis sweep w in [1e-4, 1e4] rad/s.
