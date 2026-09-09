# Wave-49 leaf spec: active-disturbance-rejection-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/active-disturbance-rejection-control/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, feedback-linearization,
  frequency-response-design, gain-scheduling, h-infinity-control,
  h-infinity-synthesis, l1-adaptive-control, lead-lag-compensation,
  observer-design, pid-control-design, python-control-design,
  root-locus-design, sliding-mode-control, smith-predictor,
  state-space-analysis; no sibling in the pack or anywhere else in the
  tree runs a bandwidth-parameterized linear-extended-state-observer
  disturbance-rejection law: the zero-owner greps and corpus scans quoted
  verbatim under Claim fences below return ZERO hits across the whole
  skills/ tree and ZERO matching tasks in eval/hit1-corpus.yaml (1326
  tasks at wave-49 HEAD, receipt baseline), both re-verified fresh at
  spec time from the repo main branch. The only tree-wide disturbance-
  leaf neighbors, context-checked as NOT owners: space-systems/adcs/
  environmental-disturbance-torque-budget (an ADCS torque-sizing leaf,
  desc verbatim: "estimate the worst-case environmental disturbance
  torque budget for a spacecraft ... aero drag torque from the
  free-molecular relation at explicit density" - a disturbance MODELLING
  leaf with no observer and no control law) and the
  gnc-autonomy/control/sliding-mode-control matched-uncertainty prose
  (its bound F given, its disturbance d never measured, quoted under the
  claim fences below). No estimation-family leaf owns an extended or
  augmented observer state: the estimation-filtering vein is closed by
  doctrine (wave-48 reminder item 6, reaffirmed in the wave-49 receipt)
  and observer-design owns only the full-order Luenberger LTI estimator).
- Provenance: wave-49 recon receipt task-0, GO 2 of 2 (receipt lines
  187-271): "the linear-extended-state-observer (LESO) bandwidth-
  parameterized disturbance-rejection law (Gao/Han ADRC: augmented state
  observer with observer gains from the (s + omega_o)^n expansion,
  control u = (u0 - z3)/b0 canceling the total-disturbance estimate z3)
  is zero-owner tree-wide AND zero in the corpus - it is not the L1/MRAC
  adaptation family (those adapt gains against an unknown coefficient;
  this observer estimates a total disturbance and cancels it at fixed
  bandwidths), and it is fenced by no sibling". Both wordable Hit@1
  queries route to the candidate with 18.5+ point margins at wave-49
  HEAD (query 1 at 29.0 vs 10.5 for adaptive-control; query 2 at 21.0
  vs 9.5 for observer-design) with zero theft (0 of 1326 tasks
  rerouted, receipt audit). Published deterministic anchor, receipt gate
  (d) (summary-only): linear ADRC for the canonical second-order plant
  y_ddot = f(y, y_dot, w) + b0 u with f the total disturbance (internal
  dynamics plus external disturbance): run the third-order LESO with
  observer gains from the bandwidth parameterization beta = (3 omega_o,
  3 omega_o^2, omega_o^3) placing all observer poles at -omega_o; form
  the disturbance-rejection control u = (u0 - z3)/b0, and close the
  outer loop with u0 = kp (r - z1) - kd z2 where kp = omega_c^2 and
  kd = 2 omega_c place the tracking poles at -omega_c. Source: Gao,
  "Scaling and Bandwidth-Parameterization Based Controller Tuning,"
  Proceedings of the 2003 American Control Conference; Han, "From PID to
  Active Disturbance Rejection Control," IEEE Transactions on Industrial
  Electronics 56(3):900-906, 2009. Corpus tokens of the leaf (receipt
  gate (f), all hyphenated compounds): active-disturbance-rejection-
  control, linear-extended-state-observer, adrc, bandwidth-
  parameterization, total-disturbance-estimate, disturbance-rejection-
  term, observer-gain-parameterization.
- Claim fences (quoted verbatim from the sibling SKILL.md files at spec
  time, re-verified FRESH from the repo, not from the receipt; the
  nearest owners fence out first-order gain adaptation, predictor-based
  adaptation with filtering, full-order LTI Luenberger estimation,
  PID gain design and tuning, the switching-law vein and known-model
  inversion, none of which is a fixed-bandwidth observer that estimates
  a total disturbance and cancels it inside the control law, which is
  the exact gap this leaf closes):
  - adaptive-control (this pack) is the GAIN-ADAPTATION fence: its
    frontmatter description reads "Use when you must design and simulate
    a model-reference adaptive controller (MRAC) for a first-order plant
    with an unknown plant coefficient: ... update the gains online with
    the gradient (Lyapunov-motivated) adaptation law scaled by the
    tracking error, and assess convergence of the tracking error and of
    the gains toward the ideal-cancellation values. ... Trigger:
    adaptive-control, mrac, model-reference-adaptive, adaptation-law,
    tracking-error, unknown-plant." Its model updates TWO GAINS online
    against an unknown plant coefficient on a first-order plant and its
    scope line is "single input, no noise, no disturbance"; the new
    leaf's gains are FIXED closed forms of two bandwidths (kp =
    omega_c^2, kd = 2 omega_c, beta = (3 omega_o, 3 omega_o^2,
    omega_o^3)), nothing adapts, and the disturbance is the very object
    the observer estimates and the law cancels. Its related-leaves list
    (fresh) names no extended-observer law.
  - l1-adaptive-control (this pack) is the PREDICTOR-PROJECTION fence:
    its frontmatter description reads "Use when you must design and
    simulate an l1-adaptive-control law for a first-order plant with an
    unknown coefficient: run the state-predictor from the design model,
    drive the projection-based-adaptation-law with the prediction error,
    pass the adaptive signal through the low-pass filter omega_c/(s +
    omega_c) and form the control as the feedforward minus the filtered
    estimate. Produces the tracking-error and prediction-error time
    histories, the sigma_hat and filtered-signal histories, the
    projection engagement, the convergence verdict and the certified
    transient-bound check that gate an L1 adaptive control assessment.
    Trigger: l1-adaptive-control, state-predictor,
    low-pass-filtered-adaptation, projection-based-adaptation-law,
    guaranteed-transient-response." The new leaf runs no predictor, no
    projection, no low-pass filter and no adaptive signal: its
    third-order LESO is a fixed linear observer from the (s + omega_o)^3
    expansion and its control cancels the observer's
    total-disturbance estimate z3, not a filtered adaptive estimate. The
    wave-48 "recheck l1-adaptive/adaptive fences" reminder is honored:
    distinct identity, no collision.
  - observer-design (this pack) is the LUENBERGER-LTI fence: its
    frontmatter description reads "Use when you must design a full-order
    Luenberger state observer for a linear time-invariant system whose
    states are not all directly measurable: build the observability
    matrix and check observability, compute the estimator gain matrix by
    pole placement with the Ackermann formula so the observer error
    dynamics eigenvalues sit at the desired locations ... confirm the
    separation principle ... and size the convergence with the settling
    time. ... Trigger: observer design, luenberger, estimator gain,
    pole placement, separation principle, error dynamics, observability,
    ackermann, settling time, output feedback." That leaf designs the
    estimator L of a KNOWN LTI plant by Ackermann pole placement as a
    standalone output-feedback product; it has NO disturbance state and
    NO control law. The new leaf's LESO is never designed for a known
    LTI plant at arbitrary poles: the three gains are the closed form
    (3 omega_o, 3 omega_o^2, omega_o^3) of one bandwidth, the augmented
    third state estimates the total disturbance (which is why the plant
    model never needs to be known), and the observer exists only inside
    the u = (u0 - z3)/b0 law. Its own pitfalls fence the bandwidth
    convention the new leaf adopts: "4 to 10x the controller bandwidth
    is the practical band" (fresh read), consistent with omega_o =
    6 omega_c here. No Ackermann, observability matrix, separation
    factorization, Hurwitz review or settling-time product is produced.
  - pid-control-design (this pack) is the GAIN-DESIGN fence: its
    frontmatter description reads "Use when the task is PID tuning,
    proportional integral derivative terms, anti-windup, integrator
    clamping, pole placement, or gain and phase margin checks. Design
    PID controller gains for aerospace flight and GNC control loops:
    compute the controller output from the proportional, integral, and
    derivative error terms, tune the gains from the plant model with
    Ziegler-Nichols using the ultimate gain and ultimate period, or
    place closed loop poles directly for a first or second order plant,
    add integrator anti-windup clamping, and check the gain margin and
    phase margin of the loop. Trigger: pid, proportional, integral,
    derivative, ziegler-nichols, ultimate gain, ultimate period,
    anti-windup, integrator clamp, pole placement, phase margin, gain
    margin." Its law is a linear combination of the error terms with
    TUNED gains and no disturbance model. The new leaf never tunes:
    kp, kd and the beta gains are given closed forms of omega_c and
    omega_o only, no margins are computed, no integrator state is
    clamped, and the disturbance is rejected through the estimated z3
    rather than integrated away.
  - sliding-mode-control (this pack, wave 48) is the SWITCHING-LAW
    fence: its pitfalls renounce estimation outright (fresh read, lines
    212-216): "the nominal model f_nom, the uncertainty bound F and the
    disturbance d are all given inputs, d is never measured or
    reconstructed, and nothing updates online (that territory belongs to
    adaptive-control and l1-adaptive-control)." Its plant is a
    "constant matched disturbance with |d| <= F, F a given bound, d
    never measured" model sized by a switching gain. The sliding leaf
    never reconstructs its disturbance; the new leaf reconstructs the
    total disturbance with a fixed-gain linear observer and cancels it,
    with no surface, no bound F and no switching term. Its related-
    leaves list (fresh) names no observer-based law.
  - feedback-linearization (this pack, wave 48) is the KNOWN-MODEL
    CANCELLATION fence: its frontmatter description reads "Use when you
    must apply feedback linearization to a nonlinear plant with a known
    exact model: compute the Lie derivatives of the output along the
    drift and control vector fields to establish the relative degree,
    invert the decoupling scalar at the operating state, form the
    linearizing control that cancels the nonlinear terms so the output
    channel obeys the linear relation y^(r) = v ... check the internal
    dynamics via their zero dynamics before accepting the design."
    Feedback linearization cancels a KNOWN exact model; the new leaf
    never knows or inverts the plant model (the internal dynamics live
    inside the estimated total disturbance) and performs no
    Lie-derivative, relative-degree, decoupling or zero-dynamics
    analysis.
  - h-infinity-control and h-infinity-synthesis (this pack, wave 47 and
    wave 48) are the FREQUENCY-DOMAIN fences (DGKF two-Riccati synthesis,
    weighted-norm analysis). Neither runs a time-domain augmented
    observer; the new leaf does no frequency sweep, no gamma iteration
    and no norm computation.
  - Whole-tree greps at prep (probe receipt gate (a)) and re-verified at
    spec time (this file): `rg -i -l 'active-disturbance|extended-state-
    observer|adrc|leso|bandwidth-parameteriz|total-disturbance|
    disturbance-observer' skills/ -g 'SKILL.md'` -> 0 hits (exit 1), and
    `rg -ic 'active-disturbance|extended-state-observer|adrc|leso|
    bandwidth-parameteriz|total-disturbance' eval/hit1-corpus.yaml` -> 0
    hits (exit 1). GENUINE gnc-autonomy/control gap (probe receipt
    task-0, GO rank 2): no leaf owns the observer-based disturbance-
    rejection identity; placement is control, not estimation (receipt
    declines-table row: the LESO law is a CONTROL identity with fixed
    bandwidths, and in estimation-filtering it would collide with the
    closed KF-form-variant doctrine and observer-design's Luenberger
    claim).
- Standards id: arp4754a (ARP4754A, Guidelines for Development of Civil
  Aircraft and Systems, SAE; reference-only control-pack convention, the
  id every landed gnc control leaf carries, sliding-mode-control,
  feedback-linearization and h-infinity-synthesis among them; present in
  standards-map.yaml, grep 'id: arp4754a' at line 38, re-verified at
  spec time). Standards are reference-only, never reproduced verbatim.
  Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design and simulate a linear active-disturbance-rejection-control (ADRC)
law that drives a second-order plant with an unknown total disturbance
onto a bandwidth-parameterized double-integrator response and holds it
there. The design plant is the canonical second-order model y_ddot =
f(y, y_dot, w) + b0 u with f the total disturbance (internal dynamics
plus external disturbance, lumped and unknown to the controller) and b0
the GIVEN control-effectiveness estimate. The law runs the third-order
linear extended state observer (LESO) z1_dot = z2 + beta1 (y - z1),
z2_dot = z3 + beta2 (y - z1) + b0 u, z3_dot = beta3 (y - z1) on the
measured output y alone, with the observer gains fixed at the bandwidth
parameterization beta = (3 omega_o, 3 omega_o^2, omega_o^3) that places
all three observer error poles at -omega_o (the characteristic
polynomial (s + omega_o)^3). The disturbance-rejection control is u =
(u0 - z3)/b0: the estimate z3 of the total disturbance is divided by the
plant gain estimate and subtracted, so that when the observer has
converged (z3 = f) the plant channel collapses to the exact double
integrator y_ddot = u0. The outer loop is the bandwidth-parameterized PD
law u0 = kp (r - z1) - kd z2 on the ESTIMATED states with kp =
omega_c^2 and kd = 2 omega_c, which places both tracking poles of the
ideal double-integrator loop at -omega_c. The LESO absorbs the internal
dynamics into the total disturbance, so the plant model itself is never
needed by the controller: only y, b0, omega_c and omega_o enter the law.
The simulator truth plant is the pinned second-order model y_ddot =
-A1 y_dot - A0 y + w(t) + b u with A1 = 0.75, A0 = 0.5, a
piecewise-constant external disturbance w stepping from 0.5 to 1.5 at
t = 3.0 s, true gain b = b0 = 1.0 in the worked case (matched) and
b = 0.8 in the robustness case (control effectiveness over-modeled by
25 percent). The closed loop returns the output to the reference
r = 1.0 after both the reference start and the disturbance step: the
worked steady state is y = 1.0 with the total disturbance estimate
z3 = 1.0 and the command u = -1.0 exactly balancing the stepped
disturbance, and under the b0 mismatch the output still settles at r
while the estimate carries the fixed bias z3 - f = (b - b0) u. Produces
the observer-gain triple from the bandwidth parameterization, the two
design gains, the disturbance-cancellation audit (the residual
f + b0 u - u0 under the law), the tracking-error, command and
total-disturbance-estimate histories, the settled-window residuals that
confirm return to the reference after the disturbance step, the
observer-lag comparison against the ideal perfect-cancellation loop, and
the verdict numbers that gate an active disturbance rejection control
assessment. Does NOT do: model-reference adaptive control, gradient or
projection adaptation laws, unknown-coefficient estimation, state
predictors, low-pass-filtered adaptive signals and online gain updates
(adaptive-control, l1-adaptive-control: the gains here are fixed closed
forms of two bandwidths, nothing adapts online); full-order Luenberger
state estimation for a known LTI plant with the Ackermann formula,
observability matrices, arbitrary pole selection, Hurwitz reviews or
separation-principle factorizations as a standalone output-feedback
product (observer-design: the three observer gains come only from the
(s + omega_o)^3 expansion and the observer exists only inside the
disturbance-rejection control law); P-I-D gain design, Ziegler-Nichols
or pole-placement tuning, anti-windup, integrator clamping, margin
checks and gain scheduling over an envelope (pid-control-design,
gain-scheduling: no tuning, no scheduling); switching surfaces, reaching
laws, equivalent controls,
matched-uncertainty bounds and chattering analysis (sliding-mode-
control: no bound F is given here, the disturbance is reconstructed by
the observer, not bounded); cancellation of a known exact nonlinear
model by Lie derivatives, relative-degree probes, decoupling matrices or
zero-dynamics analysis (feedback-linearization: the internal dynamics
are never modeled, they live inside the estimated total disturbance);
h-infinity norm analysis or robust synthesis (h-infinity-control,
h-infinity-synthesis); stochastic estimation with covariances,
innovations or noise statistics (the closed kalman-form-variant veins of
navigation and estimation-filtering: the LESO is a deterministic
fixed-gain observer); disturbance torque modelling or budgeting for
spacecraft sizing (space-systems/adcs/environmental-disturbance-torque-
budget); frequency-domain or iterative disturbance-observer designs
(DOBC variants share the same LESO total-disturbance core and are not
separate leaves per the wave-49 closing reminder); and any claim that
the leaf identifies, learns or adapts the plant model, the true gain b
or the disturbance statistics from data. The reference r is constant;
the truth-plant coefficients A1, A0, the true gain b and the disturbance
schedule are simulator bookkeeping only, never inputs to the
controller.

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG, closed form, forward
Euler discrete time. Module constants pin the worked configuration:
OMEGA_C = 5.0 (rad/s), OMEGA_O = 30.0 (rad/s, six times omega_c, inside
the 4-10x practical band the observer-design sibling states and the
3-10x Gao guidance), B0 = 1.0, PLANT_B_WORKED = 1.0,
PLANT_B_MISMATCH = 0.8, PLANT_A1 = 0.75, PLANT_A0 = 0.5, W0 = 0.5,
W1 = 1.5, T_STEP = 3.0 (s), REFERENCE_R = 1.0, INIT_Y = 0.0,
INIT_V = 0.0, INIT_Z = (0.0, 0.0, 0.0), DT = 1e-4 (s), SIM_TIME = 6.0
(s), TAIL_START = 4.5 (s), SETTLE_START = 5.5 (s),
RECOVERY_START = 3.0 (s). No imports beyond math.

Defining relations (pin these exactly; every function derives from them):
- Design plant: canonical second-order y_ddot = f(y, y_dot, w) + b0 u
  with f the total disturbance, b0 the given control-effectiveness
  estimate (b0 != 0 required).
- LESO (third order, augmented with the disturbance state z3 = f):
  z1_dot = z2 + beta1 (y - z1), z2_dot = z3 + beta2 (y - z1) + b0 u,
  z3_dot = beta3 (y - z1); only y is measured.
- Bandwidth parameterization (observer gains): beta1 = 3 omega_o,
  beta2 = 3 omega_o^2, beta3 = omega_o^3, so the error dynamics
  characteristic polynomial is s^3 + beta1 s^2 + beta2 s + beta3 =
  (s + omega_o)^3, all observer error poles at -omega_o.
- Control law (disturbance-rejection term): u = (u0 - z3)/b0. With the
  converged estimate z3 = f the plant channel reads y_ddot = f + b0
  ((u0 - z3)/b0) = u0 exactly: the disturbance-cancellation identity
  that reduces the plant to the double integrator.
- Outer loop (bandwidth-parameterized PD on the estimated states):
  u0 = kp (r - z1) - kd z2 with kp = omega_c^2, kd = 2 omega_c; the
  ideal loop y_ddot = u0 has characteristic polynomial s^2 + kd s + kp =
  (s + omega_c)^2, tracking poles at -omega_c (double).
- Truth plant (simulator bookkeeping only, never an input to the
  controller): y_ddot = -A1 y_dot - A0 y + w(t) + b u with the true gain
  b, so the simulator-truth total disturbance is f = -A1 y_dot - A0 y +
  w(t); w(t) = W0 for t < T_STEP and w(t) = W1 for t >= T_STEP.
- Reference: r constant (REFERENCE_R), so the tracking error is
  e = y - r.
- Fixed points of the cancelled loop (y = r = 1.0, v = 0, u0 = 0):
  phase 1 (w = 0.5): f = 0.0, z3 = 0.0, u = 0.0; phase 2 (w = 1.5):
  f = 1.0, z3 = 1.0, u = (0 - 1.0)/1.0 = -1.0; force balance
  -A0 y + w + b u = 0 holds at both. Under the b0 mismatch (b = 0.8 <
  b0 = 1.0) the output still settles at r = 1.0 but the steady estimate
  carries the bias z3 - f = (b - b0) u = 0.25: z3 = 1.25 while f = 1.0.
- Discrete simulation (forward Euler at the fixed dt, piecewise per
  sample): history[k] is the value at time t = k dt after k advances,
  n = int(sim_time/dt) + 1 samples, appended then advanced. At sample k
  with state (y, v, z1, z2, z3): w = w0 if t < t_step else w1;
  f = total_disturbance(y, v, w); u0 = kp (r - z1) - kd z2;
  u = (u0 - z3)/b0; append t, y, v, e = y - r, u, u0, z3, f; advance
  y = y + dt v; v = v + dt (f + plant_b u); ey = y - z1;
  z1 = z1 + dt (z2 + beta1 ey); z2 = z2 + dt (z3 + beta2 ey + b0 u);
  z3 = z3 + dt (beta3 ey). The observer correction uses the measured
  output y at the same sample; the ideal-loop comparison run uses the
  same recurrence with the perfect state (z1 = y, z2 = v) and perfect
  cancellation (u = (u0 - f)/plant_b) and no observer.
- Initial conditions zero: y(0) = 0, v(0) = 0, z(0) = (0, 0, 0), so the
  initial total disturbance f(0) = w(0) = 0.5 is entirely un-estimated
  and the observer converges from the zero estimate.

Functions (signatures, return shapes, ValueErrors; validated
identically by every public function):
- observer_gains(omega_o) -> (beta1, beta2, beta3)
  beta = (3 omega_o, 3 omega_o^2, omega_o^3), the bandwidth
  parameterization placing all LESO error poles at -omega_o.
  ValueError: omega_o <= 0 ("observer bandwidth omega_o must be
  positive, got ...").
- controller_gains(omega_c) -> (kp, kd)
  kp = omega_c^2, kd = 2 omega_c, the bandwidth parameterization placing
  the ideal-loop tracking poles at -omega_c (double). ValueError:
  omega_c <= 0 ("controller bandwidth omega_c must be positive,
  got ...").
- control_law(r, z1, z2, z3, b0, kp, kd) -> float
  u0 = kp (r - z1) - kd z2; returns u = (u0 - z3)/b0, the disturbance-
  rejection command. ValueError: b0 == 0 ("control-effectiveness
  estimate b0 must be nonzero, got 0.0").
- cancellation_residual(f, u0, z3, b0) -> float
  f + b0 ((u0 - z3)/b0) - u0, the plant acceleration under the law minus
  u0: float-zero (to rounding) whenever z3 = f, the algebraic witness of
  the disturbance-cancellation identity y_ddot = u0. ValueError: b0 == 0
  (message as above).
- total_disturbance(y, v, w) -> float
  Simulator-truth f = -PLANT_A1 v - PLANT_A0 y + w of the pinned plant.
  Bookkeeping only, never an input to the controller.
- char_poly_residual(lam, omega_o) -> float
  (lam^3 + beta1 lam^2 + beta2 lam + beta3) - (lam + omega_o)^3, the
  LESO characteristic-polynomial identity residual at a sample lam; 0.0
  to float noise (exactly 0.0 at lam = -omega_o by integer float
  arithmetic). ValueError: omega_o <= 0 (message as above).
- simulate_adrc(plant_b = PLANT_B_WORKED, b0 = B0, omega_c = OMEGA_C,
  omega_o = OMEGA_O, r = REFERENCE_R, w0 = W0, w1 = W1, t_step =
  T_STEP, y0 = INIT_Y, v0 = INIT_V, dt = DT, sim_time = SIM_TIME)
  -> dict
  Closed-loop forward-Euler simulation of the ADRC law on the truth
  plant with the disturbance step at t_step. Returns {"t", "y", "v",
  "e", "u", "u0", "z3", "f" (series), "n", "dt", "kp", "kd", "beta",
  "max_abs_e_rec" (max |y - r| over [RECOVERY_START, sim_time]),
  "max_abs_e_tail" (max |e| over [TAIL_START, sim_time]),
  "max_z3_res_tail" (max |z3 - f| over [TAIL_START, sim_time]),
  "max_abs_e_settle" (max |e| over [SETTLE_START, sim_time]),
  "max_z3_res_settle" (max |z3 - f| over [SETTLE_START, sim_time])}.
  ValueErrors: b0 == 0; omega_c <= 0; omega_o <= 0; omega_o <= omega_c
  ("observer bandwidth omega_o must exceed the controller bandwidth
  omega_c, got omega_o ... <= omega_c ..."); dt <= 0 ("sample time dt
  must be positive, got ..."); sim_time <= 0 ("simulation time sim_time
  must be positive, got ..."); t_step outside (0, sim_time)
  ("disturbance step time t_step must lie strictly inside (0,
  sim_time), got t_step ... for sim_time ...").
- simulate_ideal(plant_b = PLANT_B_WORKED, omega_c = OMEGA_C, r =
  REFERENCE_R, y0 = INIT_Y, v0 = INIT_V, dt = DT, sim_time = SIM_TIME)
  -> dict
  Ideal-loop comparison run: same truth plant and same outer PD law with
  perfect state knowledge and perfect disturbance cancellation at every
  sample (u = (u0 - f)/plant_b), so the plant channel is the exact
  double integrator y_ddot = u0 regardless of f. Same Euler and dt, so
  the difference against the ADRC run isolates observer error only.
  Returns {"t", "y", "e", "n", "dt"}. ValueErrors: omega_c, dt,
  sim_time guards as above.

Identities to test (closed form, exact where noted; checkable without
the builder module):
- Bandwidth parameterization closed forms: observer_gains(30.0) =
  (90.0, 2700.0, 27000.0) exactly and the expansion (s + 30)^3 = s^3 +
  90 s^2 + 2700 s + 27000: char_poly_residual(lam, 30.0) is 0.000e+00 at
  every sample lam (real anchor residuals at lam = -30, -3, -1 and 0.5
  all 0.000e+00); controller_gains(5.0) = (25.0, 10.0) exactly with
  (s + 5)^2 = s^2 + 10 s + 25.
- Disturbance-cancellation identity: with z3 = f the law gives plant
  acceleration f + b0 ((u0 - z3)/b0) = u0: cancellation_residual(f, u0,
  f, b0) is 0.000e+00 for any f, u0, b0 (real anchor residuals 0.000e+00
  at both phase fixed points). At the worked fixed points the arithmetic
  closes exactly: phase 1 (w = 0.5) f = 0.000000000, u = -0.000000000,
  f + b0 u = 0.000e+00; phase 2 (w = 1.5) f = 1.000000000, u =
  -1.000000000, f + b0 u = 0.000e+00.
- Ideal closed-loop response closed form: the double integrator y_ddot =
  u0 = omega_c^2 (r - y) - 2 omega_c y_dot is critically damped at
  -omega_c and its unit-step response is y(t) = 1 - (1 + omega_c t)
  exp(-omega_c t); exact values 1 - 2 exp(-1) = 0.264241117657 at
  t = 1/omega_c = 0.2 s, 1 - 3.5 exp(-2.5) = 0.712702504816 at t = 0.5 s
  and 1 - 6 exp(-5) = 0.959572318005 at t = 1.0 s. The ideal Euler run
  at dt = 1e-4 reproduces the t = 1.0 s value to real 3.369e-05 (the
  Euler truncation error at this dt).
- Reference and disturbance DC tracking: the worked loop returns to y =
  r = 1.0 after the reference start AND after the +1.0 disturbance step
  at t = 3.0 s (real e(6.0) = -2.025e-07, max |e| over [5.5, 6.0] =
  8.016e-07); the steady command and estimate carry the disturbance
  exactly (real u(6.0) = -1.000001803850 against -1.0 and z3(6.0) =
  0.999999402193 against the truth f(6.0) = 0.999999537946, with max
  |z3 - f| over [5.5, 6.0] = 1.403e-06).
- Observer-lag structure: during fast transients the finite-bandwidth
  observer makes the loop trail the ideal perfect-cancellation loop (real
  y_adrc(1.0) - y_ideal(1.0) = 0.003958874713), and the disturbance step
  excites a deviation that decays at the OUTER rate (real max |y_adrc -
  y_ideal| = 9.172e-03 over [0, 6], 1.305e-04 over [4.5, 6] and 8.015e-07
  over [5.5, 6]); once both loops sit at the same fixed point the
  difference vanishes with the transient, not at the observer rate.
- b0-mismatch bias closed form: with b = 0.8 and b0 = 1.0 the output
  still settles at r (real y(6.0) = 1.000000346701, e(6.0) = 3.467e-07)
  while the estimate carries the fixed bias z3 - f = (b - b0) u = 0.25
  (real z3(6.0) = 1.249999451753, u(6.0) = -1.249993763548, z3 =
  -b0 u = 1.249993764 vs f_truth = 1.000000898).
- ValueErrors across the module and determinism: the guards enumerated
  in the Worked example raise ValueError with the real messages quoted
  there; identical outputs run to run and under both interpreters; no
  randomness; no imports beyond math; the module constants fixed as
  above.

## Worked example

Plant: second-order y_ddot = f(y, y_dot, w) + b0 u with f the total
disturbance and the design gain estimate b0 = 1.0; simulator truth
y_ddot = -0.75 y_dot - 0.5 y + w(t) + b u with the external disturbance
w = 0.5 for t < 3.0 s and w = 1.5 for t >= 3.0 s (a +1.0 step at 3.0 s)
and the true gain b = 1.0 (worked, matched) or b = 0.8 (robustness, the
b0 = 1.0 design over-models the control effectiveness by 25 percent).
The controller knows none of this: only y is measured and only b0,
omega_c and omega_o enter the law. Design: controller bandwidth
omega_c = 5.0 rad/s, observer bandwidth omega_o = 30.0 rad/s (six times
omega_c), so kp = omega_c^2 = 25.0 and kd = 2 omega_c = 10.0 place the
tracking poles at -5 (double) and beta = (3 omega_o, 3 omega_o^2,
omega_o^3) = (90.0, 2700.0, 27000.0) place the observer error poles at
-30 (triple). Reference r = 1.0 constant, initial state y(0) = 0,
v(0) = 0, LESO from the zero estimate z(0) = (0, 0, 0). Simulation:
forward Euler at dt = 1e-4 s over a 6.0 s horizon (60001 samples).

All values below are REAL outputs of the prep anchor
anchor_active-disturbance-rejection-control.py (pure stdlib, math only,
no RNG, exit 0, internal asserts all pass), run once at spec time under
both interpreters with byte-identical output and quoted as printed:

- Design (module output): omega_c = 5.0 rad/s, omega_o = 30.0 rad/s,
  ratio omega_o/omega_c = 6.0; b0 = 1.0; observer_gains(30.0) =
  (90.000000000, 2700.000000000, 27000.000000000); controller_gains(5.0)
  = (25.000000000, 10.000000000); char-poly residuals
  det(sI - (A - beta C)) - (s + w_o)^3 are 0.000e+00 at s = -30, -3, -1
  and 0.5.
- Fixed points of the cancelled loop and the exact ideal closed-form
  step response are quoted in the Identities section above (all real
  anchor output).
- Worked run (b = b0 = 1.0), Euler dt = 1.0e-04 s, 60001 samples
  (module output):
  - phase 1 (reference step at t = 0, w = 0.5): t = 0.2 s: y
    0.259669337601, e -0.740330662399, u 1.055029927517, z3
    -0.606612712863; t = 0.5 s: y 0.705882336870, e -0.294117663130,
    u -2.331654381193, z3 -0.807418249668; t = 1.0 s: y 0.963564880347,
    e -0.036435119653, u -0.621028567703, z3 -0.170149298106;
    t = 2.0 s: y 1.000073982338, e 0.000073982338, u -0.004564715564,
    z3 -0.000884341434; t = 3.0 s: y 1.000006249016, e 0.000006249016,
    u 0.000091278219, z3 0.000025966299 (settled on r to 6.2e-06 before
    the step).
  - phase 2 (disturbance step w: 0.5 -> 1.5 at t = 3.0 s): t = 3.05 s:
    y 1.001168788483, e 0.001168788483, u -0.371692817243, z3
    0.189469788386; t = 3.10 s: y 1.003773162466, e 0.003773162466,
    u -1.018085819223, z3 0.562952036680; t = 3.25 s: y 1.008944174201,
    e 0.008944174201, u -1.257204635966, z3 0.948952916380;
    t = 3.50 s: y 1.006876632387, e 0.006876632387, u -1.014347135043,
    z3 1.004353568806; t = 4.00 s: y 1.001300603879, e 0.001300603879,
    u -0.984995817700, z3 1.004561307340; t = 5.00 s: y 1.000005228706,
    e 0.000005228706, u -0.999736202905, z3 1.000061292219;
    t = 6.00 s: y 0.999999797512, e -0.000000202488, u -1.000001803850,
    z3 0.999999402193.
  - worked metrics (module output): e(6.0) = -2.025e-07; max |e| over
    [3.0, 6.0] = 9.161e-03 (peak at about t = 3.25 s, the loop returns
    the output to the reference after the step); max |e| over
    [4.5, 6.0] = 1.305e-04 (decay tail at the outer pole rate -w_c);
    max |e| over [5.5, 6.0] = 8.016e-07 and max |z3 - f_truth| over
    [5.5, 6.0] = 1.403e-06 (the settled band); z3(6.0) =
    0.999999402193 vs f_truth(6.0) = 0.999999537946; u(6.0) =
    -1.000001803850 (against the exact -1.0); u0(6.0) = -2.402e-06 (the
    PD outer loop rests at zero once y = r).
- Ideal-loop comparison (module output, same Euler with perfect
  cancellation): max |y_adrc - y_ideal| over [0.0, 6.0] = 9.172e-03;
  over [4.5, 6.0] = 1.305e-04; over [5.5, 6.0] = 8.015e-07 (the
  observer-lag cost of the disturbance step, decaying with the outer
  pole); observer-lag deficit y_adrc(1.0) - y_ideal(1.0) =
  0.003958874713 (during the fast reference transient the observer
  trails the perfect-cancellation loop); |y_ideal(1.0) - exact
  1 - 6 e^-5| = 3.369e-05 (Euler truncation witness at dt = 1e-4).
- Mismatch robustness run (module output, b = 0.8, b0 = 1.0, 25 percent
  over-modeled): y(3.0) = 0.999991137772, y(6.0) = 1.000000346701,
  e(6.0) = 3.467e-07, z3(6.0) = 1.249999451753, u(6.0) =
  -1.249993763548; max |z3 - f_truth| over [4.5, 6.0] = 2.500e-01 (the
  fixed estimate bias) and over [5.5, 6.0] = 2.500e-01; max |e| over
  [3.0, 6.0] = 1.191e-02 and over [5.5, 6.0] = 2.722e-06. Fixed point
  under mismatch: z3 = -b0 u = 1.249993764 vs f_truth = 1.000000898:
  the output still settles at r = 1.0 while the estimate carries the
  bias (b - b0) u = 0.25, the signed price of over-modeling the control
  effectiveness.
- ValueErrors with real messages (module output, quoted as printed):
  observer_gains(0.0) raises "observer bandwidth omega_o must be
  positive, got 0.0"; controller_gains(0.0) raises "controller
  bandwidth omega_c must be positive, got 0.0"; control_law(1.0, 0.0,
  0.0, 0.0, 0.0, 25.0, 10.0) raises "control-effectiveness estimate b0
  must be nonzero, got 0.0"; cancellation_residual(0.5, 0.0, 0.5, 0.0)
  raises the same b0 message; simulate_adrc(b0 = 0.0) raises the b0
  message; simulate_adrc(omega_c = 0.0) raises "controller bandwidth
  omega_c must be positive, got 0.0"; simulate_adrc(omega_o = 0.0)
  raises "observer bandwidth omega_o must be positive, got 0.0";
  simulate_adrc(omega_c = 5.0, omega_o = 5.0) raises "observer
  bandwidth omega_o must exceed the controller bandwidth omega_c, got
  omega_o 5.0 <= omega_c 5.0"; simulate_adrc(dt = 0.0) raises "sample
  time dt must be positive, got 0.0"; simulate_adrc(sim_time = 0.0)
  raises "simulation time sim_time must be positive, got 0.0";
  simulate_adrc(t_step = 6.0) raises "disturbance step time t_step must
  lie strictly inside (0, sim_time), got t_step 6.0 for sim_time 6.0".

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of anchor_active-disturbance-rejection-
control.py (stdlib math, closed form, exit 0, no randomness, identical
under both interpreters).

## Validation list (contract test must include)

1. Bandwidth parameterization: observer_gains(30.0) equals (90.0,
   2700.0, 27000.0) within 1e-12; controller_gains(5.0) equals (25.0,
   10.0) within 1e-12; char_poly_residual(lam, 30.0) below 1e-9 at
   lam = -30, -3, -1 and 0.5 (real all 0.000e+00); (s + 30)^3 = s^3 +
   90 s^2 + 2700 s + 27000.
2. Disturbance-cancellation identity: cancellation_residual(f, u0, f,
   b0) below 1e-12 for f in (0.0, 1.0) and u0 in (-1.0, 25.0) at
   b0 = 1.0 (real 0.000e+00); the law with z3 = f makes the plant
   channel the double integrator y_ddot = u0.
3. Fixed-point arithmetic: total_disturbance(1.0, 0.0, 0.5) = 0.0 and
   total_disturbance(1.0, 0.0, 1.5) = 1.0 within 1e-12; the cancelled
   loop balances at (u, z3) = (0.0, 0.0) in phase 1 and (-1.0, 1.0) in
   phase 2 with f + b0 u = 0 within 1e-12.
4. Exact ideal closed form: 1 - 2/e = 0.264241117657 (t = 0.2 s),
   1 - 3.5 e^-2.5 = 0.712702504816 (t = 0.5 s) and 1 - 6 e^-5 =
   0.959572318005 (t = 1.0 s) are reproduced by the ideal Euler run
   within 1e-3 (real |y_ideal(1.0) - exact| = 3.369e-05 at dt = 1e-4).
5. Worked reference tracking (phase 1): y(3.0) = 1.000006249016 within
   1e-4 of 1.0 and e(3.0) below 1e-4; the y samples at 0.2, 0.5, 1.0
   and 2.0 s match the quoted anchor values within 1e-6 relative.
6. Worked disturbance rejection (phase 2): e(6.0) = -2.025e-07 below
   1e-5 (return to r after the +1.0 step); u(6.0) = -1.000001803850
   within 1e-4 of -1.0; z3(6.0) = 0.999999402193 within 1e-4 of 1.0 and
   within 1e-4 of f_truth(6.0) = 0.999999537946; peak step excursion
   max |e| over [3.0, 6.0] = 9.161e-03 (assert within 1e-3 relative);
   settled band max |e| over [5.5, 6.0] = 8.016e-07 below 1e-5.
7. Settled-window residual metrics: max |e| over [5.5, 6.0] below 1e-5
   (real 8.016e-07) and max |z3 - f| over [5.5, 6.0] below 1e-4 (real
   1.403e-06): the estimate tracks the truth total disturbance in the
   settled band.
8. Ideal-loop comparison: max |y_adrc - y_ideal| over [0.0, 6.0] =
   9.172e-03 below 2e-2; over [5.5, 6.0] = 8.015e-07 below 1e-5;
   observer-lag deficit y_adrc(1.0) - y_ideal(1.0) = 0.003958874713
   (positive, assert within 1e-3 of the anchor value).
9. Mismatch robustness run (plant_b = 0.8, b0 = 1.0): y(6.0) =
   1.000000346701 within 1e-4 of 1.0 (output still tracks r);
   u(6.0) = -1.249993763548 within 1e-3 of -1.25; z3(6.0) =
   1.249999451753 within 1e-3 of 1.25; estimate bias z3 - f settles at
   (b - b0) u = 0.25 (real max |z3 - f| over [5.5, 6.0] = 2.500e-01
   within 1e-3 of 0.25); max |e| over [5.5, 6.0] = 2.722e-06 below
   1e-4.
10. Worked sample points within 1e-6 relative of the anchor-quoted
    values: y(0.2) = 0.259669337601, y(0.5) = 0.705882336870, y(1.0) =
    0.963564880347, y(2.0) = 1.000073982338, y(3.0) = 1.000006249016,
    y(3.05) = 1.001168788483, y(3.25) = 1.008944174201, y(3.5) =
    1.006876632387, y(4.0) = 1.001300603879, y(5.0) = 1.000005228706,
    y(6.0) = 0.999999797512; u(6.0) = -1.000001803850; z3(6.0) =
    0.999999402193.
11. All ValueErrors enumerated in the Worked example raise from the named
    public function with the real messages quoted there: the omega_o
    guard (observer_gains, char_poly_residual), the omega_c guard
    (controller_gains), the b0 guards (control_law, cancellation_residual,
    simulate_adrc), the omega_o <= omega_c guard (simulate_adrc), and
    the dt, sim_time and t_step guards (simulate_adrc).
12. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math; module
    constants fixed as OMEGA_C 5.0, OMEGA_O 30.0, B0 1.0,
    PLANT_B_WORKED 1.0, PLANT_B_MISMATCH 0.8, PLANT_A1 0.75,
    PLANT_A0 0.5, W0 0.5, W1 1.5, T_STEP 3.0, REFERENCE_R 1.0,
    INIT_Y 0.0, INIT_V 0.0, INIT_Z (0, 0, 0), DT 1e-4, SIM_TIME 6.0,
    TAIL_START 4.5, SETTLE_START 5.5, RECOVERY_START 3.0. No exact-float
    equality on computed sums; use assertAlmostEqual/math.isclose
    everywhere.
13. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (python3 3.11.16 and
    ~/.pyenv/versions/3.13.12/bin/python3 3.13.12); the prep anchor was
    verified byte-identical under both.

## Corpus fragment (eval/hit1-wave49-active-disturbance-rejection-control.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "design the active-disturbance-rejection-control law for the second-order
  plant: run the linear-extended-state-observer with bandwidth-
  parameterized observer gains to estimate the total disturbance and cancel
  it with the disturbance-rejection term before the bandwidth-parameterized
  outer loop"
  intent: "gnc-autonomy/control; active-disturbance-rejection-control: the
  linear-extended-state-observer run with bandwidth-parameterized observer
  gains to estimate the total disturbance, canceled by the disturbance-
  rejection term before the bandwidth-parameterized outer loop"
  expected_skill: "gnc-autonomy/control/active-disturbance-rejection-control"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply the linear-extended-state-observer in the adrc loop: estimate the
  state and the total disturbance from the plant output, divide the
  estimated disturbance by the plant gain for the rejection term, and close
  the controller on the estimated states"
  intent: "gnc-autonomy/control; active-disturbance-rejection-control with
  the linear-extended-state-observer in the adrc loop: the state and the
  total disturbance estimated from the plant output, the estimated
  disturbance divided by the plant gain for the rejection term, and the
  controller closed on the estimated states"
  expected_skill: "gnc-autonomy/control/active-disturbance-rejection-control"
Task ids: w49-active-disturbance-rejection-control-1 and -2. Prep grep
(run at spec time by the probe and re-verified for this file): each of
the tokens active-disturbance, extended-state-observer, adrc, leso,
bandwidth-parameteriz and total-disturbance returns ZERO matches in
eval/hit1-corpus.yaml (grep exit 1) and ZERO skills/ hits, so the
queries are collision-free; the sibling corpus tasks route on
adaptation-language wording (adaptive-control, l1-adaptive-control),
Luenberger/Ackermann wording (observer-design), tuning and margin
language (pid-control-design), switching-surface wording
(w48-sliding-mode-control-1/-2), Lie-derivative wording
(w48-feedback-linearization-1/-2) and DGKF wording
(w48-h-infinity-synthesis-1/-2), none of which carries a
total-disturbance-estimate identity. The theft audit in the receipt
(0 of 1326 tasks rerouted with the candidate added) covers every
existing corpus task. Add one fence line to the adaptive-control,
l1-adaptive-control and observer-design related-leaves lists and one
router row to skills/gnc-autonomy/SKILL.md at build time pointing the
bandwidth-parameterized extended-state disturbance-rejection law to the
new leaf (the sliding-mode-control wave-48 precedent).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design and simulate an
active-disturbance-rejection-control law for a second-order plant with
an unknown total disturbance:" and include the outputs in the Claim
order (the linear-extended-state-observer run with the bandwidth-
parameterized observer gains from the (s + omega_o)^3 expansion, the
total disturbance estimated and canceled by the disturbance-rejection
term u = (u0 - z3)/b0, the bandwidth-parameterized PD outer loop on the
estimated states, the disturbance-cancellation audit, and the tracking-
error, command and total-disturbance-estimate histories), then close
with the Trigger list. b0, omega_c and omega_o are given design inputs
and the gains always take the closed forms kp = omega_c^2, kd =
2 omega_c and beta = (3 omega_o, 3 omega_o^2, omega_o^3), never tuned or
adapted; the internal plant dynamics and the external disturbance are
never modeled, only estimated as one lumped total disturbance; never
reproduce ARP4754A text (reference-only). First tag:
active-disturbance-rejection-control. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else:
active-disturbance-rejection-control, linear-extended-state-observer,
adrc, bandwidth-parameterization, total-disturbance-estimate,
disturbance-rejection-term, observer-gain-parameterization. 50-150
words, <=1000 chars, no em dash, action verb present, never the banned
sweep term of the builder kit. Recommended wording (113 words, 999
chars, verified at spec time):

"Use when you must design and simulate an active-disturbance-rejection-
control law for a second-order plant with an unknown total disturbance:
run the linear-extended-state-observer with bandwidth-parameterized
observer gains placing every observer pole at omega_o to estimate the
state and the total disturbance, cancel the estimate with the
disturbance-rejection term divided by the plant-gain estimate b0, and
close the outer loop with the bandwidth-parameterized PD law on the
estimated states placing the tracking poles at omega_c. Produces the
observer-gain triple from the (s + omega_o)^3 expansion, the
disturbance-cancellation audit of the rejection term, and the tracking-
error, command and total-disturbance-estimate histories that gate an
active disturbance rejection control assessment. Trigger:
active-disturbance-rejection-control, linear-extended-state-observer,
adrc, bandwidth-parameterization, total-disturbance-estimate,
disturbance-rejection-term, observer-gain-parameterization."

FORBIDDEN TOKENS (belong to siblings): mrac, model-reference-adaptive,
adaptation-law, adaptive-gain, online-gain-update, unknown-coefficient,
ideal-cancellation, state-predictor, projection-based-adaptation,
low-pass-filtered-adaptation, sigma-hat, guaranteed-transient-response
(adaptive-control, l1-adaptive-control; gains here are fixed closed
forms, never updated online); ziegler-nichols, ultimate-gain,
ultimate-period, controller-gain-tuning, anti-windup, integrator-clamp,
gain-margin, phase-margin and any PID gain design or loop-margin claim
(pid-control-design; no tuning, no margins); luenberger, ackermann,
observability-matrix, separation-principle, hurwitz, settling-time and
any standalone full-order state-estimation claim for a known LTI plant
(observer-design; the LESO is bandwidth-parameterized, augmented with
the disturbance state and used only inside the control law);
sliding-mode, sliding-surface, reaching-law, equivalent-control,
switching-term, chattering, matched-uncertainty, uncertainty-bound and
any claim that the disturbance is bounded but never measured
(sliding-mode-control; here the disturbance is reconstructed by the
observer); lie-derivative, relative-degree, decoupling-matrix,
zero-dynamics, linearizing-control and any known-model inversion claim
(feedback-linearization; the plant model is never known or inverted);
h-infinity, gamma-iteration, mixed-sensitivity, worst-case-peak-gain
(h-infinity-control, h-infinity-synthesis); kalman, innovation,
covariance, process-noise, measurement-noise and any
stochastic-estimation claim (the closed estimation-filtering veins);
gain-scheduling, scheduling-variable, breakpoint-table
(gain-scheduling); deadbeat-control, z-domain, tustin-bilinear
(deadbeat-control, digital-control-design); smith-predictor,
dead-time-compensation (smith-predictor);
environmental-disturbance-torque, gravity-gradient-torque,
solar-pressure-torque and any disturbance torque budgeting claim
(space-systems/adcs/environmental-disturbance-torque-budget);
disturbance-observer-based-control, dobc and any claim of a separate
disturbance-observer design identity (the wave-49 closing reminder:
further members of the LESO total-disturbance family are not separate
leaves); system-identification and any claim that the leaf identifies
the plant, b, b0 or the disturbance statistics from data (b0 is a given
design input, f is estimated at fixed bandwidths). Never the bare single
words observer, disturbance, control, plant, gain, estimate, bandwidth,
state or error as standalone metadata tags.
