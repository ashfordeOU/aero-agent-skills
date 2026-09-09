# Wave-48 leaf spec: feedback-linearization (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/feedback-linearization/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, h-infinity-control, l1-adaptive-control,
  lead-lag-compensation, observer-design, pid-control-design,
  python-control-design, root-locus-design, smith-predictor,
  state-space-analysis; sliding-mode-control is the other new leaf of the
  same wave-48 nonlinear vein, being specced in parallel and not on disk
  at spec time, so its intended claim (wave-48 probe receipt GO 2 gate
  (d), quoted verbatim under Claim fences below) is fenced against here;
  no leaf in the pack or anywhere else in the tree performs a Lie-derivative
  input-output linearization: the zero-owner greps
  `feedback[- ]lineariz|dynamic[- ]inversion|lie[- ]derivative|
  zero[- ]dynamic|input[- ]output[- ]lineariz` over the whole skills/
  tree return exactly ONE hit, propulsion/rocket/thrust-vector-control,
  whose only occurrence is the "zero dynamic pressure" vacuum-regime
  prose quoted below (not a zero-dynamics claim), and the
  eval/hit1-corpus.yaml scan for the same tokens returns 0 matching
  tasks, all re-verified at spec time).
- Provenance: wave-48 recon receipt task-3 GO rank 3, lines 242-307 (GO
  3 of 3 strong, the nonlinear vein opened this wave): "apply
  feedback-linearization to the nonlinear plant: compute the
  lie-derivative of the output along the control vector field to
  establish the relative-degree, invert the decoupling-matrix for the
  linearizing-control, and verify the zero-dynamics of the
  internal-dynamics are stable". Published deterministic anchor, receipt
  gate (d) (summary-only, verbatim): "input-output feedback
  linearization of a nonlinear plant xdot = f(x) + g(x) u, y = h(x):
  compute the Lie derivatives L_f^r h and L_g L_f^{r-1} h along the
  drift and control vector fields to establish the relative degree r
  (L_g L_f^{k} h = 0 for k < r-1, nonzero at r-1), invert the decoupling
  scalar/matrix (L_g L_f^{r-1} h)^-1 to form the linearizing control u =
  (L_g L_f^{r-1}h)^-1 (v - L_f^r h) that cancels the nonlinear terms,
  apply the outer linear tracking loop on y^(r) = v, and check the
  internal dynamics (the unobservable part) are stable via their zero
  dynamics before accepting the design. Source: Slotine and Li, Applied
  Nonlinear Control (1991), chapters 4 and 6 and Isidori, Nonlinear
  Control Systems (Springer), the standard references; the aerospace
  framing is nonlinear dynamic inversion (NDI). Deterministic offline
  polynomial/Lie-derivative arithmetic given the model." The receipt
  pins the identity but no numerical plant, so the anchor realizes it on
  the module's canonical worked plant below (assumption recorded under
  Model). Corpus tokens of the leaf (receipt gate (f), all hyphenated
  compounds): feedback-linearization, lie-derivative, relative-degree,
  decoupling-matrix, linearizing-control, zero-dynamics,
  internal-dynamics-stability, input-output-linearization.
- Claim fences (quoted from the sibling SKILL.md files at prep,
  re-verified at spec time; the nearest owners fence out gain
  adaptation, switching laws, gain scheduling, norm/robust synthesis and
  the linear LTI toolbox, none of which is an exact
  nonlinearity-cancelling linearization of a known model, which is the
  exact gap this leaf closes):
  - adaptive-control (this pack) is the MODEL-REFERENCE fence: its
    frontmatter description reads "Use when you must design and simulate
    a model-reference adaptive controller (MRAC) for a first-order plant
    with an unknown plant coefficient: run the reference model from the
    command, form the control as the sum of a state-feedback term and a
    feedforward term with adaptive gains, update the gains online with
    the gradient (Lyapunov-motivated) adaptation law scaled by the
    tracking error, and assess convergence of the tracking error and of
    the gains toward the ideal-cancellation values. Produces the error
    history, the gain histories and the convergence verdict that gate an
    adaptive control assessment." The adaptive pair assumes an UNKNOWN
    plant coefficient and adapts gains online from the tracking or
    prediction error; there is no exact model, no Lie-derivative
    construction and no cancellation of a known nonlinearity anywhere in
    its equations. The new leaf's model is exact and given, so its
    cancellation is algebraic, never adapted: the unknown-coefficient,
    adaptation-law and ideal-cancellation surfaces stay with the
    sibling.
  - l1-adaptive-control (this pack) is the STATE-PREDICTOR fence: its
    frontmatter description reads "Use when you must design and simulate
    an l1-adaptive-control law for a first-order plant with an unknown
    coefficient: run the state-predictor from the design model, drive
    the projection-based-adaptation-law with the prediction error, pass
    the adaptive signal through the low-pass filter omega_c/(s +
    omega_c) and form the control as the feedforward minus the filtered
    estimate." Its structure is a predictor plus a projection-based law
    plus a low-pass filter on the adaptation signal, all for a
    first-order plant with an unknown coefficient; the new leaf never
    runs a state predictor, never projects or filters an adaptation
    signal and never estimates anything (the model is exact).
  - sliding-mode-control (same wave-48 batch, parallel spec; intended
    claim quoted verbatim from the probe receipt GO 2 gate (d)) is the
    SWITCHING-LAW fence of the same new nonlinear vein: "sliding-mode
    control for a relative-degree-one (second-order canonical) plant
    with matched uncertainty |f| bounded: sliding surface s = edot +
    lambda e, sliding condition (1/2) d(s^2)/dt <= -eta |s|, equivalent
    control u_eq from setting sdot = 0 on the nominal model, control u =
    u_eq - k sat(s/phi) with the switching gain k sized above the
    uncertainty bound and the boundary-layer thickness phi suppressing
    chattering; finite-time reachability of the boundary layer follows
    from the constant-plus-proportional reaching law." It is a
    discontinuous variable-structure law sized against a matched-
    uncertainty bound; the new leaf's control is the smooth exact
    cancellation u = (v - L_f^r h) / a of the known model and carries no
    switching term, no sliding surface, no boundary layer and no
    uncertainty bound.
  - gain-scheduling (this pack) is the GAIN-SCHEDULE fence: its
    frontmatter description reads "Use when you must design and schedule
    controller gains against dynamic-pressure across nonlinear flight
    envelope, interpolate gain schedule breakpoint table across
    Mach-number operating points, and select the scheduling variable
    (dynamic-pressure, Mach number, angle of attack, or altitude). Choose
    nearest, linear, or spline interpolation, apply scheduling-variable
    rate limiting, and distinguish gain scheduling from gain updating."
    It schedules EXISTING linear gains across the envelope; the new leaf
    never interpolates, never selects a scheduling variable and never
    schedules anything: the closed-loop rate K is one fixed given
    constant, the same for every operating point.
  - deadbeat-control (this pack) is the Z-DOMAIN-RELATIVE-DEGREE word
    fence: its body (lines 47-49, verbatim) reads "Deadbeat controller:
    unity feedback D(z) = N_c(z)/D_c(z) = A(z)/(B(z)
    *(z^d - 1)) with relative degree d = deg A - deg B, the plant's pure
    sample delay."
    That "relative degree" is the z-domain pulse-transfer delay deg A -
    deg B of a linear discrete plant, a different object from the
    Lie-derivative relative degree of this leaf (the probe receipt noted
    deadbeat-control scored as the Q2 corpus sim runner-up at 9.5 on
    that single shared body token at weight 0.5, transfer-function usage,
    not a fence or an owner). The new leaf never works in the z-domain,
    never forms pulse-transfer polynomials and never cancels plant modes.
  - state-space-analysis (this pack) is the LINEAR-LTI fence: its
    frontmatter description reads "Use when you must analyze a linear
    time-invariant system in state space: form the controllability and
    observability matrices, decide controllability and observability
    from their ranks, compute the 2x2 eigenvalue stability verdict,
    build the state transition matrix by the Cayley-Hamilton method, and
    produce the controller or observer canonical forms. Applies to
    flight control and GNC state-space models written as x_dot = A x +
    B u with output y = C x." It analyzes LINEAR LTI models; the new
    leaf's plant is genuinely nonlinear and stays nonlinear, and the
    feedback itself cancels the nonlinear terms: no linearization of the
    model, no A/B/C matrices, no controllability or observability
    ranks, no transition matrix and no canonical forms anywhere.
  - magnetorquer-control (space-systems/adcs) is the ADCS-RUNNER-UP
    fence: its frontmatter description reads "Use when the task is
    magnetorquer control, dipole moment calculation, B-dot detumbling,
    cross-product torque steering, detumbling rate damping, or torque
    authority limits. Compute the magnetic dipole moment for spacecraft
    magnetic attitude control with magnetorquers: solve torque = m x B
    for the required dipole from a torque demand and the local magnetic
    field vector, apply the B-dot detumbling law to damp body rates,
    check the achievable torque against the magnetorquer torque
    authority limit, warn when the torque demand lies along the field,
    and size the torque rod coils." It scored as the Q1 corpus sim
    runner-up at 12.0 purely on generic nonlinear/control tokens (tag
    weight 3 / name 2 / desc 1 scoring on shared vocabulary), and
    reaction-wheel-control (quaternion error feedback with PD gains) is
    the same class; ADCS control laws are dipole/PD attitude laws, not
    the plant-inversion identity, and own no decoupling-matrix or
    zero-dynamics construction.
  - thrust-vector-control (propulsion/rocket) is the WORD fence, the
    single whole-tree skills/ hit for the zero-owner grep tokens: its
    body (lines 47-50, verbatim) reads "TVC produces control force only
    while the engine thrusts, but it works at zero dynamic pressure and
    in vacuum; aerodynamic control surfaces produce force from q * S *
    CN and lose authority as dynamic pressure falls, so upper stages
    rely on TVC alone." That is vacuum-regime actuator prose; the match
    is 'zero[- ]dynamic' inside "zero dynamic pressure", not a
    zero-dynamics claim and not an ownership statement.
  - Whole-tree greps at prep (probe receipt gate (a)) and re-verified at
    spec time (this file): `rg -i -l 'feedback[- ]lineariz|dynamic[-
    ]inversion|lie[- ]derivative|zero[- ]dynamic|input[- ]output[-
    ]lineariz' skills/ -g 'SKILL.md'` -> exactly the thrust-vector-
    control hit above, and `rg -ic 'feedback-linearization|dynamic-
    inversion|lie-derivative|zero-dynamics' eval/hit1-corpus.yaml` -> 0
    hits. GENUINE gnc-autonomy/control gap (probe receipt task-3,
    verified zero-owner, GO rank 3): no leaf owns the Lie-derivative
    relative-degree / decoupling-inversion / zero-dynamics identity that
    the adaptive, switching, scheduling and linear siblings cannot
    express.
- Standards id: arp4754a (ARP4754A, Guidelines for Development of Civil
  Aircraft and Systems, SAE; reference-only control-pack convention, the
  same id the pid-control-design, digital-control-design, observer-design
  and deadbeat-control leaves carry; present in standards-map.yaml, grep
  'id: arp4754a' at line 38, re-verified at spec time). Standards are
  reference-only, never reproduced verbatim. Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Linearize the input-output response of a known nonlinear plant exactly
by feedback, so the chosen output channel obeys the linear relation
y^(r) = v under an outer tracking loop, and gate the design on the
stability of the unobservable internal dynamics. The plant is the affine
single-input model xdot = f(x) + g(x) u with the module's canonical
worked structure (assumption: the receipt anchor pins the identity, not
a numerical plant): xdot1 = -A11 x1 + x2 and xdot2 = CUBIC x1^3 + QUAD
x2^2 + x1 u with module constants A11 = CUBIC = QUAD = 1.0, all given
inputs, plus two registered outputs: y2 = x2 (relative degree r = 1,
with x1 as the unobservable internal state) and y1 = x1 (relative degree
r = 2 = n, the fully linearizable channel). For the chosen output the
leaf computes the Lie derivatives L_f^k h along the drift field and the
probes L_g L_f^k h = <d(L_f^k h), g> along the control field to
establish the relative degree r: the defining property L_g L_f^k h = 0
for k < r - 1 with L_g L_f^(r-1) h nonzero at the operating state, so
the decoupling scalar a(x) = L_g L_f^(r-1) h = x1 for both outputs,
invertible on x1 != 0. The linearizing control u = (v - L_f^r h) / a
cancels the nonlinear terms exactly and leaves ydot = v (r = 1) or
yddot = v (r = 2). The outer loop is a linear command law on the
linearized channel with the assigned closed-loop pole placement: for the
r = 1 design v = -K (y - y_ref) with K = CL_RATE_K = 2.0 a fixed given
constant, placing the closed-loop pole at s = -K so the tracking error
e = y - y_ref obeys edot = -K e and the closed loop follows y(t) =
y_ref + (y(0) - y_ref) exp(-K t) exactly; for the r = 2 design v =
-K^2 (y - y_ref) - 2 K ydot, the double pole (s + K)^2, whose response
carries the t exp(-K t) mode. The internal dynamics of the r = 1 design
are x1dot = -A11 x1 + x2 (the part unobservable from y2); their zero
dynamics force y2 = x2 = 0 exactly, sustained by the control u = -x1^2
(f2/g2 at x2 = 0), leaving the linear x1dot = -A11 x1 with eigenvalue
-A11 = -1.0, and the leaf reports the verdict "asymptotically stable"
from that eigenvalue, which is the internal-dynamics stability check
that gates acceptance of the design. Produces the relative-degree
verdict with the Lie-derivative table at the operating state, the
decoupling scalar and the linearizing control value, the exactly
linearized closed-loop response of the r = 1 design against its closed
form 1 - exp(-2 t) (unit step from the worked initial state) with the
internal-state history x1(t) = 1 - 1.5 exp(-t) + exp(-2 t), the
fully linearized r = 2 companion response 1 - (0.5 + 1.5 t) exp(-2 t)
against its closed form, the zero-dynamics verdict with its constrained
decay samples, and the control history. Does NOT do: model-reference
adaptive control, adaptation of gains from a tracking error, an unknown
plant coefficient and ideal-cancellation gain convergence
(gnc-autonomy/control/adaptive-control, which is why the plant model
here is exact and never adapted); L1 adaptive control with a state
predictor, a projection-based adaptation law and a low-pass filtered
adaptive signal (gnc-autonomy/control/l1-adaptive-control); sliding-mode
or variable-structure control with a sliding surface from the error, an
equivalent control, a switching term inside a boundary layer, a
constant-plus-proportional reaching law, chattering suppression or a
matched-uncertainty bound (the parallel sibling
gnc-autonomy/control/sliding-mode-control, which is why the linearizing
control here is the smooth exact cancellation of a known model, never a
switched or discontinuous law); gain scheduling, breakpoint-table
interpolation across the envelope and scheduling-variable selection
(gnc-autonomy/control/gain-scheduling, which is why K is one fixed given
constant); worst-case norm analysis and state-space robust synthesis
(h-infinity-control and the wave-48 h-infinity-synthesis sibling), and
any robustness, model-mismatch or uncertainty claim (the exact-model
assumption is the model); z-domain pulse-transfer design and the
deadbeat finite-settling synthesis whose "relative degree d = deg A -
deg B" is a different object (deadbeat-control); the linear LTI analysis
toolbox of controllability, observability, transition matrices and
canonical forms (state-space-analysis); recursive backstepping
(strict-feedback Lyapunov design, the deferred next sibling of this
vein); and identification or model learning of any kind (f, g and h are
given, and the relative degree, decoupling scalar and zero dynamics are
computed from them, never measured or estimated from data).

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG, closed form. The module
pins the worked-example configuration in module constants: A11 = 1.0
(the internal-dynamics decay coefficient), CUBIC = 1.0 and QUAD = 1.0
(the cubic-spring and quadratic-damping coefficients of f2), X1_0 = 0.5
and X2_0 = 0.0 (the worked initial state), Y_REF = 1.0 (the unit-step
reference), CL_RATE_K = 2.0 (1/s, the assigned closed-loop pole rate),
SIM_DT = 0.001 (s), SIM_TIME = 10.0 (s), INV_EPS = 1e-12 (the
decoupling invertibility tolerance), N = 2 (system order) and OUTPUTS =
("x1", "x2", "const"). No imports beyond math.

Defining relations (pin these exactly; every function derives from
them):
- Plant vector fields: f(x) = (f1, f2) with f1 = -A11 x1 + x2 and f2 =
  CUBIC x1^3 + QUAD x2^2; g(x) = (0, x1), a state-dependent control
  effectiveness that vanishes at x1 = 0. The plant model is exact and
  given; nothing is identified, adapted or estimated.
- Outputs: h2 = x2 and h1 = x1, plus the synthetic registered output
  "const" (h = 1.0, every Lie derivative zero) used to exercise the
  no-relative-degree rejection.
- Lie derivatives (analytic chain-rule evaluation, no finite
  differences): L_f^k h(x) is the k-th Lie derivative of h along f, and
  L_g L_f^k h(x) = <d(L_f^k h)(x), g(x)> the probe along g. The exact
  per-output results for the worked plant: for h2 = x2, L_f h2 = f2
  with gradient (3 CUBIC x1^2, 2 QUAD x2); for h1 = x1, L_f h1 = f1
  with gradient (-A11, 1) and L_f^2 h1 = -f1 + f2 = x1 - x2 + x1^3 +
  x2^2.
- Relative degree: r at state x is the first r with L_g L_f^(r-1) h
  nonzero, preceded by L_g L_f^k h = 0 for k = 0 .. r - 2; r <= N. For
  h2: r = 1 with L_g h2 = x1. For h1: r = 2 with L_g h1 = 0 (k = 0 < r
  - 1) and L_g L_f h1 = x1. When every probe up to N - 1 vanishes at x
  (the control channel never reaches the output there, as at x1 = 0 for
  h2 or everywhere for "const"), no finite relative degree exists and
  the function raises ValueError.
- Decoupling scalar: a(x) = L_g L_f^(r-1) h = x1 for both real outputs,
  invertible on x1 != 0. The linearizing control u = (v - L_f^r h) / a
  cancels the nonlinear terms: substitution gives y^(r) = v with the
  residual f2 + a u - v = 0 exactly at every state.
- Outer linear loops on y^(r) = v: r = 1 (output x2), v = -K (y -
  Y_REF), pole at s = -K; r = 2 (output x1), v = -K^2 (y - Y_REF) - 2 K
  ydot with ydot = L_f h1 = f1, characteristic polynomial (s + K)^2.
  K is a given constant, never tuned, placed by a design procedure or
  scheduled.
- Closed-form responses (unit step from the worked initial state x0 =
  (0.5, 0.0), Y_REF = 1.0, K = 2.0):
  - r = 1 loop: y(t) = 1 - exp(-2 t) exactly (e(0) = -1, pole s = -2),
    and the internal state under that loop x1(t) = 1 - 1.5 exp(-t) +
    exp(-2 t) (x1dot = -x1 + x2 driven by x2 = 1 - exp(-2 t)), which
    dips to a minimum 0.4375 = 1 - 1.5 (3/4) + (3/4)^2 at t = ln(4/3) =
    0.287682 s and rises to y_ref; the settling time to the 1e-3 band
    is -0.5 ln(1e-3) = 3.453878 s.
  - r = 2 loop: y(t) = 1 + (A + B t) exp(-2 t) with A = y(0) - y_ref =
    -0.5 and B = ydot(0) + K (y(0) - y_ref) = -1.5, the double-root
    response 1 - (0.5 + 1.5 t) exp(-2 t) whose surviving t exp(-2 t)
    mode (B nonzero) is the double-pole signature.
- Zero dynamics of the r = 1 design: force y2 = x2 = 0 and hold it with
  u = -f2/g2 = -(CUBIC x1^3)/x1 = -x1^2 (g2 = x1, x2 = 0), leaving the
  linear internal dynamics x1dot = -A11 x1 with eigenvalue -A11 = -1.0;
  verdict "asymptotically stable" exactly when the eigenvalue is
  strictly negative. The internal dynamics have dimension n - r = 1.
- Discrete closed-loop simulation: classical RK4 at SIM_DT over
  SIM_TIME (10001 samples), state x = (x1, x2) under the active
  linearizing law; the y and u series are sampled at the states
  (y[k] = x2[k] or x1[k], u[k] = u(x[k])), and RK4 is the only
  discretization, with its truncation residual measured below at the
  1e-13 level.

Functions (signatures, return shapes, ValueErrors; validated
identically by every public function):
- f(x) -> (f1, f2); g(x) -> (0, x1). State validation: x must have
  length N = 2 with real components (ValueError "state x must have
  length 2, got length ..." / "state components must be real numbers,
  got ...").
- Lf_power_h(output_key, x, k) -> float: value of L_f^k h at x, k in
  {0, 1, 2}; ValueError for an unknown output ("unknown output '...':
  registered outputs are x1, x2, const") and k outside the ladder
  range.
- Lg_Lf_power_h(output_key, x, k) -> float: value of L_g L_f^k h =
  <d(L_f^k h), g> at x, the k-th relative-degree probe.
- relative_degree(output_key, x) -> (r, table): r in {1, ..., N} and
  table the list of (k, L_g L_f^k h) pairs for k = 0 .. r - 1, the
  defining property L_g L_f^k h = 0 for k < r - 1 and L_g L_f^(r-1) h
  nonzero at x. ValueError when every probe up to N - 1 vanishes at x
  (real message quoted in the Worked example): no finite relative
  degree exists at that state for that output.
- decoupling_scalar(output_key, x) -> float: a(x) = L_g L_f^(r-1) h,
  the last table entry; reuses relative_degree and inherits its
  ValueErrors.
- linearizing_control_from(Lf_r_h, decoupling, v) -> float: the pure
  algebra of the linearizing control u = (v - L_f^r h) / a. ValueError
  when |decoupling| <= INV_EPS: "decoupling scalar a(x) = ... is zero
  (|a| <= INV_EPS = 1e-12): the linearizing control u = (v - L_f^r h) /
  a(x) is not defined".
- linearizing_control(output_key, x, v) -> float: state-level wrapper
  that computes L_f^r h and the decoupling scalar at x from the
  Lie-derivative machinery and calls linearizing_control_from.
- outer_command(output_key, x) -> float: v = -K (y - Y_REF) for output
  "x2" and v = -K^2 (y - Y_REF) - 2 K ydot for output "x1"; ValueError
  for unknown outputs.
- closed_loop_sim(output_key, x0 = None, y_ref = Y_REF, k =
  CL_RATE_K, dt = SIM_DT, sim_time = SIM_TIME) -> dict: RK4 closed-loop
  simulation under the active linearizing law, returning {"t", "y",
  "x1", "x2", "u"} arrays over 10001 samples. ValueErrors: y_ref <= 0
  ("reference y_ref must be positive, got ..."), k <= 0 ("closed-loop
  rate k must be positive, got ..."), dt <= 0 ("sample time dt must be
  positive, got ..."), sim_time <= 0 ("simulation time sim_time must be
  positive, got ...") and the state and output guards above.
- closed_form_r1(t, x0 = None, y_ref = Y_REF, k = CL_RATE_K) -> float
  and closed_form_r2(t, x0 = None, y_ref = Y_REF, k = CL_RATE_K) ->
  float: the closed forms above (single-pole and double-pole responses
  of the exactly linearized loops).
- series_max_abs_error(series, closed_form, t) -> float: max over
  samples of |series[i] - closed_form(t[i])|.
- measured_decay_rate(y, t, t1, t2) -> float: the closed-loop pole
  witness -(ln|e(t2)| - ln|e(t1)|) / (t2 - t1) on the error e = y -
  y_ref of the r = 1 loop, which tends to the assigned rate K.
- zero_dynamics_analysis(x0 = None) -> dict: {"eigenvalue" (-A11 =
  -1.0), "verdict" ("asymptotically stable" when the eigenvalue is
  strictly negative), "t", "x1"} with the constrained zero-dynamics
  samples x1(t) = x1(0) exp(-A11 t).
- sample_series(t, series, times) -> list: helper returning the series
  value at each requested sample time.

Identities to test (closed form, exact where noted; checkable without
the builder module):
- Relative-degree defining property at the worked state x0 = (0.5, 0.0):
  output "x2" gives r = 1 with the table [(0, 0.5)] (L_g h2 = x1 = 0.5,
  nonzero at r - 1 = 0), and output "x1" gives r = 2 with the table
  [(0, 0.0), (1, 0.5)] (L_g h1 = 0 for k = 0 < r - 1 = 1, L_g L_f h1 =
  x1 = 0.5 nonzero at r - 1). Decoupling scalar a(x0) = 0.5 for both
  outputs and a((1.0, 0.75)) = 1.0.
- Cancellation identity: f2 + a u - v = 0 exactly at every state (real
  anchors 0.000e+00 at x0 and at (1.0, 0.75)), so the nonlinear terms
  leave the output channel and ydot = v (r = 1) exactly.
- Linearized closed loop equals the assigned linear dynamics: the r = 1
  loop output matches 1 - exp(-2 t) with real max abs error 4.929e-14
  over the 10001 samples, and the measured decay rate between t = 0.5
  and t = 1.0 is 2.000000, the pole witness for s = -K = -2.
- Double-pole r = 2 placement: the fully linearized output matches 1 -
  (0.5 + 1.5 t) exp(-2 t) with real max abs error 1.275e-13; the
  double-root mode coefficient B = -1.5 is nonzero, the t exp(-2 t)
  signature of the repeated pole (s + 2)^2.
- Internal-state closed form of the r = 1 design: x1(t) = 1 - 1.5
  exp(-t) + exp(-2 t), real max abs error 4.552e-14, minimum
  0.437500056838 at t = 0.288000 s against the theory 0.4375 at ln(4/3)
  = 0.287682 s, final value 0.999931902167 approaching y_ref: the
  unobservable state stays bounded and converges.
- Zero-dynamics verdict: eigenvalue -A11 = -1.0 exactly, verdict
  "asymptotically stable", so the internal dynamics are stable and the
  r = 1 design is accepted; the constrained samples x1 = 0.5 exp(-t) at
  t = 1, 2, 5 s are 0.18393972058572117, 0.067667641618306351,
  0.0033689734995427335.
- Decoupling singularity: at x1 = 0 the decoupling scalar a = x1
  vanishes, so no finite relative degree exists there (ValueError), and
  the pure-algebra linearizing_control_from rejects a zero decoupling.
- Steady state: the r = 1 loop drives y to the reference and the control
  to u = -2.0 exactly (the equilibrium x1 = x2 = 1 cancels f2(1, 1) = 2
  against a(1, 1) = 1 with v = 0); real anchors y final 0.999999997939
  (the closed form 1 - exp(-2 t) at t = 10 s), u final -1.999931903196
  and x1 final 0.999931902167, with x1 converging on the slower
  internal-dynamics rate (its 6.81e-5 gap from the reference at t = 10 s
  is the 1.5 exp(-t) mode of x1(t) = 1 - 1.5 exp(-t) + exp(-2 t)).
- ValueErrors across the module: the eight guards enumerated in the
  Worked example raise ValueError with the messages quoted there.
- Determinism: identical outputs run to run and under both interpreters;
  no randomness; no imports beyond math; the module constants fixed as
  above.

## Worked example

Plant: the module's canonical nonlinear plant xdot1 = -x1 + x2, xdot2 =
x1^3 + x2^2 + x1 u (A11 = CUBIC = QUAD = 1.0), worked output y = x2
(relative degree r = 1, internal state x1) with the companion output
y = x1 (relative degree r = 2 = n) for the fully linearized case.
Worked initial state x0 = (0.5, 0.0); unit step reference y_ref = 1.0;
assigned closed-loop rate K = 2.0 (pole at s = -2, double pole for the
r = 2 companion). Simulation: RK4 at dt = 0.001 s over a 10 s horizon
(10001 samples). The theory values below are exact closed forms of the
linearized channels; the difference between the simulated and closed
forms is the RK4 truncation residual only.

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_feedback_linearization.py (pure stdlib, math only,
no RNG, exit 0, internal asserts all pass), run once at spec time under
both interpreters with byte-identical transcripts, and quoted as
printed:

- Relative-degree establishment at x0 (module output):
  relative_degree('x2', (0.5, 0.0)) -> r = 1, table [(0, 0.5)] with
  L_g h2 = 0.5 (nonzero at r - 1 = 0); relative_degree('x1', (0.5, 0.0))
  -> r = 2, table [(0, 0.0), (1, 0.5)] with L_g h1 = 0 (k = 0 < r - 1 =
  1) and L_g L_f h1 = 0.5 (nonzero at r - 1 = 1). The defining property
  L_g L_f^k h = 0 for k < r - 1 with the nonzero probe at r - 1 holds
  for both outputs; at the probe state (1.0, 0.75) the decoupling scalar
  is 1.0.
- Lie terms and controls at x0 (module output): L_f^r h = 0.125 for
  output 'x2' (L_f h2 = f2 = 0.125) and 0.625 for output 'x1' (L_f^2 h1
  = x1 - x2 + x1^3 + x2^2); decoupling scalar a(x0) = 0.5 in both cases.
  Outer commands v = 2.0 (r = 1) and v = 4.0 (r = 2); linearizing
  controls u = (v - L_f^r h) / a give u = 3.75 (r = 1) and u = 6.75
  (r = 2) at x0. Cancellation residual f2 + a u - v = 0.000e+00 at x0
  and at (1.0, 0.75): the nonlinear terms are canceled exactly and the
  channel is ydot = v.
- r = 1 closed loop (module output): the output matches the assigned
  linear dynamics 1 - exp(-2 t) with max abs error 4.929e-14 over the
  10001 samples (RK4 truncation). Samples y(0.5) = 0.632120558829, y(1)
  = 0.864664716763, y(2) = 0.981684361111, y(3) = 0.997521247823, y(5)
  = 0.999954600070 against the closed form 1 - exp(-2 t) at the same
  times; settling to the 1e-3 band at 3.454000 s (theory -0.5 ln(1e-3)
  = 3.453878 s); measured decay rate between t = 0.5 and t = 1.0 =
  2.000000, the pole witness for s = -K = -2.0. Control samples u(0) =
  3.75, u(0.5) = 0.524048715609, u(1) = -1.15790550792, u(2) =
  -1.80181129688, u(10) = -1.999931903196 (the equilibrium control
  -2.0, cancelling f2(1, 1) = 2 with a(1, 1) = 1 at v = 0).
- Internal state of the r = 1 design (module output): x1 matches the
  closed form 1 - 1.5 exp(-t) + exp(-2 t) with max abs error 4.552e-14;
  x1 dips to its minimum 0.437500056838 at t = 0.288000 s (theory 0.4375
  at ln(4/3) = 0.287682 s) and rises to x1(10) = 0.999931902167,
  approaching y_ref: the unobservable state stays bounded and converges
  during the maneuver.
- r = 2 companion loop (module output): the fully linearized output
  matches the double-pole closed form 1 - (0.5 + 1.5 t) exp(-2 t) with
  max abs error 1.275e-13; samples y(1) = 0.72932943352683755, y(3) =
  0.98760623911666501, y(6) = 0.9999416299826438; settling to the 1e-3
  band at 4.438000 s. The double-root mode coefficient B = -1.5 is
  nonzero, so the response carries the t exp(-2 t) mode of the repeated
  pole (s + 2)^2.
- Zero-dynamics stability check of the r = 1 design (module output):
  eigenvalue -1.0, verdict "asymptotically stable", internal-dynamics
  dimension n - r = 1. The constrained samples x1 = 0.5 exp(-t) at t =
  1, 2, 5 s read 0.18393972058572117, 0.067667641618306351,
  0.0033689734995427335. The design is accepted on this verdict.
- ValueErrors with real messages (module output, quoted as printed):
  relative_degree('x2', (0.0, 0.5)) raises "no finite relative degree
  at state x = (0.0, 0.5) for output 'x2': L_g L_f^k h = 0 for every k
  up to the system order N = 2, so the control channel never reaches
  the output at this state" (the decoupling scalar x1 vanishes at x1 =
  0); relative_degree('const', (0.5, 0.0)) raises the same message with
  output 'const' (a constant output has no relative degree);
  relative_degree('bogus', (0.5, 0.0)) raises "unknown output 'bogus':
  registered outputs are x1, x2, const"; linearizing_control_from(Lf_r_h
  = 1.0, decoupling = 0.0, v = 1.0) raises "decoupling scalar a(x) =
  0.0 is zero (|a| <= INV_EPS = 1e-12): the linearizing control u = (v
  - L_f^r h) / a(x) is not defined"; closed_loop_sim('x2', k = 0.0)
  raises "closed-loop rate k must be positive, got 0.0";
  closed_loop_sim('x2', dt = 0.0) raises "sample time dt must be
  positive, got 0.0"; closed_loop_sim('x2', sim_time = 0.0) raises
  "simulation time sim_time must be positive, got 0.0";
  closed_loop_sim('x2', y_ref = 0.0) raises "reference y_ref must be
  positive, got 0.0".

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w48spec/anchor_feedback_
linearization.py (stdlib math, closed form, exit 0, no randomness,
byte-identical under both interpreters).

## Validation list (contract test must include)

1. Relative-degree identities within 1e-12: relative_degree('x2', (0.5,
   0.0)) returns (1, [(0, 0.5)]); relative_degree('x1', (0.5, 0.0))
   returns (2, [(0, 0.0), (1, 0.5)]); Lg_Lf_power_h('x1', (0.5, 0.0), 0)
   == 0.0 exactly (the k = 0 < r - 1 probe); decoupling_scalar('x2',
   (0.5, 0.0)) = 0.5 and decoupling_scalar('x1', (0.5, 0.0)) = 0.5
   within 1e-12; decoupling_scalar('x2', (1.0, 0.75)) = 1.0 within
   1e-12.
2. Lie terms and linearizing control at x0: Lf_power_h('x2', (0.5,
   0.0), 1) = 0.125 within 1e-12; Lf_power_h('x1', (0.5, 0.0), 2) =
   0.625 within 1e-12; linearizing_control('x2', (0.5, 0.0), 2.0) =
   3.75 and linearizing_control('x1', (0.5, 0.0), 4.0) = 6.75 within
   1e-9 (the outer commands v = 2.0 and v = 4.0 come from
   outer_command at x0).
3. Cancellation identity: f2 + a u - v = 0 within 1e-12 at x0 and at
   (1.0, 0.75) (real anchors 0.000e+00), for every probe state used in
   the contract test.
4. r = 1 closed loop matches the assigned linear dynamics: max |y - (1 -
   exp(-2 t))| below 1e-9 over all 10001 samples (real anchor 4.929e-14,
   the RK4 truncation residual); samples y(0.5) = 0.632120558829, y(1)
   = 0.864664716763, y(2) = 0.981684361111, y(3) = 0.997521247823,
   y(5) = 0.999954600070 each within 1e-9 of the closed form; settling
   time to the 1e-3 band 3.454 within 0.02 (theory 3.453878).
5. Closed-loop pole placement witness: measured_decay_rate between t =
   0.5 and t = 1.0 = 2.000000 within 1e-3 of CL_RATE_K = 2.0 (the pole
   of the linearized loop sits at s = -K); the r = 2 loop carries the
   double-pole signature: max |y - (1 - (0.5 + 1.5 t) exp(-2 t))| below
   1e-9 (real anchor 1.275e-13), samples y(1) = 0.72932943352683755,
   y(3) = 0.98760623911666501, y(6) = 0.9999416299826438 each within
   1e-9, and the double-root coefficient B = -1.5 within 1e-12 (nonzero
   t exp(-2 t) mode of (s + K)^2).
6. Internal-state identity of the r = 1 design: max |x1 - (1 - 1.5
   exp(-t) + exp(-2 t))| below 1e-9 (real anchor 4.552e-14); minimum
   0.437500056838 within 1e-6 of 0.4375 at a sample time within 0.01 of
   ln(4/3) = 0.287682 s; final x1 0.999931902167 within 1e-9 of the
   closed form at t = SIM_TIME = 10 s (x1 trails y_ref by the
   internal-dynamics 1.5 exp(-t) mode, a 6.81e-5 gap at the final
   sample, so assert against the closed form, not against Y_REF).
7. Zero-dynamics verdict: zero_dynamics_analysis() returns eigenvalue
   -1.0 exactly and verdict "asymptotically stable" (the internal
   dynamics are stable, so the r = 1 design is accepted); the
   constrained samples at t = 1, 2, 5 s (0.18393972058572117,
   0.067667641618306351, 0.0033689734995427335) each within 1e-12 of
   0.5 exp(-t).
8. Steady state: r = 1 loop y final 0.999999997939 within 1e-9 of the
   closed form 1 - exp(-2 t) at t = SIM_TIME = 10 s (the 2.06e-9 gap
   from the reference is exp(-2 t) at t = 10 s, so assert against the
   closed form, not against Y_REF); u final -1.999931903196 within 1e-6
   of the equilibrium control -2.0; u at t = 0 is 3.75 within 1e-9.
9. Relative-degree failure cases: relative_degree('x2', (0.0, 0.5))
   raises ValueError (the decoupling scalar x1 vanishes at x1 = 0, so
   no finite relative degree exists at that state); relative_degree(
   'const', (0.5, 0.0)) raises ValueError (constant output, every probe
   zero); relative_degree('bogus', (0.5, 0.0)) raises ValueError;
   linearizing_control_from(1.0, 0.0, 1.0) raises ValueError (zero
   decoupling cannot be inverted).
10. All ValueErrors enumerated in the Worked example raise from the
    named public function with the real messages quoted there: the two
    no-relative-degree cases and the unknown-output case
    (relative_degree), the decoupling-inversion guard
    (linearizing_control_from), and the k, dt, sim_time and y_ref
    guards (closed_loop_sim); the state-length and component guards of
    the field and ladder functions also raise.
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constants fixed as A11 1.0, CUBIC 1.0, QUAD 1.0, X1_0 0.5,
    X2_0 0.0, Y_REF 1.0, CL_RATE_K 2.0, SIM_DT 0.001, SIM_TIME 10.0,
    INV_EPS 1e-12, N 2. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave48-feedback-linearization.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "apply feedback-linearization to the nonlinear plant: compute the
  lie-derivative of the output along the control vector field to
  establish the relative-degree, invert the decoupling-matrix for the
  linearizing-control, and verify the zero-dynamics of the
  internal-dynamics are stable"
  intent: "gnc-autonomy/control; feedback-linearization: the
  Lie-derivative of the output along the control vector field that
  establishes the relative-degree, the inversion of the
  decoupling-matrix for the linearizing-control, and the zero-dynamics
  stability verification of the internal-dynamics that gates the
  design"
  expected_skill: "gnc-autonomy/control/feedback-linearization"
Query 2 (copy verbatim from the receipt gate (e)):
  "linearize the input-output response of the nonlinear plant by
  feedback-linearization: compute the lie-derivatives up to the
  relative-degree, form the linearizing-control from the
  decoupling-matrix and apply the outer tracking loop with the
  zero-dynamics stability check"
  intent: "gnc-autonomy/control; input-output linearization of the
  nonlinear plant: the lie-derivatives computed up to the
  relative-degree, the linearizing-control formed from the
  decoupling-matrix, and the outer tracking loop applied on the
  linearized channel with the zero-dynamics stability check"
  expected_skill: "gnc-autonomy/control/feedback-linearization"
Task ids: w48-feedback-linearization-1 and -2. Prep grep (run at spec
time by the probe and re-verified for this file): each of the tokens
feedback-lineariz, dynamic-inversion, lie-derivative, zero-dynamics,
input-output-lineariz and decoupling-matrix returns ZERO matches in
eval/hit1-corpus.yaml (grep exit 1) and exactly ONE skills/ hit, the
thrust-vector-control "zero dynamic pressure" vacuum prose quoted under
Claim fences (context-checked as not an owner), so the queries are
collision-free; the sibling corpus tasks route on gain-tuning and
margin language (pid-control-design), z-domain sampled-data and deadbeat
language (digital-control-design, deadbeat-control, w46-deadbeat-
control-1/-2), estimator language (observer-design), norm-analysis
language (h-infinity-control, w47-h-infinity-control-1/-2), delay-
compensation language (smith-predictor, w47-smith-predictor-1/-2),
adaptation-law language (adaptive-control, l1-adaptive-control) and
scheduling-variable language (gain-scheduling), none of which carries a
Lie-derivative relative-degree construction, a decoupling inversion or a
zero-dynamics verdict; the theft audit in the probe receipt found 0 of
1306 tasks reroute with the candidate added. The corpus tasks never
reuse the sibling-owned phrases "adaptation law", "state predictor",
"sliding surface", "equivalent control", "boundary layer", "switching
gain", "gain schedule", "breakpoint table", "scheduling variable" or
"deadbeat"; they refer to the construction as the "linearizing-control"
formed by "inverting the decoupling-matrix" after "computing the
lie-derivatives", and to the acceptance gate as the "zero-dynamics"
stability check. Add one fence line to sliding-mode-control at build
time (its switching law is the sibling of this exact-cancellation leaf,
each naming the other in related-leaves) and one router row to
skills/gnc-autonomy/SKILL.md pointing feedback-linearization,
zero-dynamics and input-output-linearization questions to the new leaf
(the h-infinity-control and deadbeat-control precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must apply feedback linearization
to a nonlinear plant with a known exact model:" (or the equivalent
action-verb opening in the Claim language) and include the outputs in
the Claim order (the relative-degree verdict with the Lie-derivative
table at the operating state, the linearizing control with the
decoupling scalar, the exactly linearized closed-loop response against
the assigned closed form, and the zero-dynamics stability verdict that
gates the design), then close with the Trigger list. K is a fixed given
closed-loop rate, never tuned, scheduled or adapted; the plant model is
exact and known, never identified or estimated; refer to the control as
the linearizing control that cancels the nonlinear terms, never as a
switching or adaptive law; and never reproduce ARP4754A text
(reference-only). First tag: feedback-linearization. Metadata tags
EXACTLY as the probe receipt gate (f) lists them, nothing else:
feedback-linearization, lie-derivative, relative-degree,
decoupling-matrix, linearizing-control, zero-dynamics,
internal-dynamics-stability, input-output-linearization. 50-150 words,
<=1000 chars, no em dash, never the banned sweep term of the builder
kit, action verb present. Recommended wording (137 words, 962 chars,
verified at spec time):

"Use when you must apply feedback linearization to a nonlinear plant
with a known exact model: compute the Lie derivatives of the output
along the drift and control vector fields to establish the relative
degree, invert the decoupling scalar at the operating state, form the
linearizing control that cancels the nonlinear terms so the output
channel obeys the linear relation y^(r) = v, apply the outer linear
tracking loop with the assigned closed-loop pole placement, and check
the internal dynamics via their zero dynamics before accepting the
design. Produces the relative-degree verdict, the linearizing control
with the decoupling scalar, the exactly linearized closed-loop response
against the assigned closed form, and the zero-dynamics stability
verdict that gates the design. Trigger: feedback linearization, input
output linearization, lie derivative, relative degree, decoupling
matrix, linearizing control, zero dynamics, internal dynamics
stability."

FORBIDDEN TOKENS (belong to siblings): mrac, model-reference-adaptive,
adaptation-law, reference-model, unknown-plant-coefficient,
unknown-plant, gain-convergence and any claim that gains adapt online
from a tracking or prediction error (adaptive-control,
l1-adaptive-control; the model is exact and nothing adapts);
state-predictor, projection-based-adaptation-law, low-pass-filtered-
adaptation, sigma_hat, transient-bound and any L1 structure
(l1-adaptive-control); sliding-mode-control, sliding-surface,
sliding-surface-design, equivalent-control, switching-term,
reaching-law, constant-plus-proportional-reaching-law, boundary-layer,
boundary-layer-command, chattering, chattering-suppression,
matched-uncertainty, variable-structure-control and any switching or
discontinuous-law claim (sliding-mode-control, the parallel sibling of
the same vein); gain-scheduling, scheduling-variable, breakpoint-table,
gain-updating, interpolation, dynamic-pressure-scheduling and any claim
that the closed-loop rate is scheduled or interpolated
(gain-scheduling); h-infinity, mixed-sensitivity, worst-case-gain,
gamma-iteration, riccati and any robustness or model-mismatch claim
(h-infinity-control and the h-infinity-synthesis sibling; the
exact-model assumption is the model and no uncertainty is analyzed);
deadbeat-control, finite-settling-time, pole-placement-at-origin and
any z-domain pulse-transfer claim, including the z-domain "relative
degree d = deg A - deg B" of deadbeat-control (the Lie-derivative
relative degree here is a different object); controllability,
observability, state-transition-matrix, cayley-hamilton, canonical-form
and any linear LTI analysis claim (state-space-analysis);
backstepping and any recursive Lyapunov design of the deferred sibling;
system-identification, model-identification and any claim that the leaf
learns f, g or h from data. Never the bare single words feedback,
linearization, nonlinear, plant, model, control, derivative, output,
input, stability or dynamics as standalone metadata tags.
