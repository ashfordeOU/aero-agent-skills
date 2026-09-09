# Wave-49 leaf spec: backstepping-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/backstepping-control/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, h-infinity-control, h-infinity-synthesis,
  l1-adaptive-control, lead-lag-compensation, observer-design,
  pid-control-design, python-control-design, root-locus-design,
  sliding-mode-control, smith-predictor, state-space-analysis; no sibling
  in the pack or anywhere else in the tree performs a recursive
  strict-feedback design: the zero-owner greps
  `rg -i -l 'backstepping|back-stepping|strict-feedback|integrator-back'`
  skills/ -g 'SKILL.md' -> 0 hits (exit 1) and the eval/hit1-corpus.yaml
  scan for the tokens backstepping, back-stepping, strict-feedback,
  virtual-control and control-lyapunov returns 0 matching tasks (exit 1),
  both re-verified fresh at spec time; the extended adaptive variants
  adaptive-backstepping and tuning-function return 0 tree hits and 0
  corpus hits; the only tree-wide 'lyapunov' owner is
  adaptive-control, whose Lyapunov reference is the single-state
  convergence analysis of its first-order gradient adaptation law (body
  lines 56-61, verbatim: "Adaptation law (discrete gradient rule, error =
  x - xm): theta_x_new = theta_x - gamma_x * e * x * dt and theta_r_new =
  theta_r - gamma_r * e * r * dt. Lyapunov motivated: with the sign of
  b_p known positive the update drives the quadratic tracking Lyapunov
  function down, e goes to zero, and the gains settle at the
  ideal-cancellation values."), NOT a control-Lyapunov recursive
  construction; no leaf anywhere owns the virtual-control recursion, so
  the wave-48 closing reminder item 2 ("sliding-mode-control and
  feedback-linearization open the nonlinear-control vein: backstepping is
  the declared next sibling only after one of them lands and proves the
  vein") is adjudicated SATISFIED at wave-49: both leaves are on disk and
  the vein is proven with two members).
- Provenance: wave-49 recon receipt task-0 GO 1 of 2 (GO 1 of 2 strong),
  lines 100-185: "One-line why: wave-48's own closing reminder declared
  backstepping the next sibling of the nonlinear-control vein 'only after
  one of them lands and proves the vein' - both sliding-mode-control and
  feedback-linearization landed at wave-48 - and the strict-feedback
  recursive design identity (error-variable change, virtual control,
  final control from the recursion plus its analytic derivative,
  quadratic-Lyapunov audit) is still zero-owner tree-wide, zero in the
  1326-task corpus, and fenced by NO sibling: the two adaptive leaves are
  first-order model-reference/L1 gain-adaptation structures, and neither
  new nonlinear sibling claims the recursion." Published deterministic
  anchor, receipt gate (d) (summary-only): integrator backstepping for a
  second-order strict-feedback plant x1_dot = x2 + f1(x1), x2_dot = u +
  f2(x1, x2) tracking a reference x1d: define the error variable z1 = x1
  - x1d and the virtual control alpha1 = -c1 z1 + x1d_dot - f1 (c1 > 0)
  so the z1-subsystem Lyapunov candidate V1 = (1/2) z1^2 decays as V1_dot
  = -c1 z1^2 + z1 z2 with the mismatch z2 = x2 - alpha1; the final
  control u = -f2 + alpha1_dot - z1 - c2 z2 (c2 > 0) makes V2 = V1 +
  (1/2) z2^2 satisfy V2_dot = -c1 z1^2 - c2 z2^2 < 0, giving asymptotic
  tracking with the closed-loop error rates set by c1, c2; alpha1_dot is
  the analytic derivative along the plant, and each recursion step adds
  one state and one virtual control. Source: Krstic, Kanellakopoulos and
  Kokotovic, Nonlinear and Adaptive Control Design (Wiley, 1995) chapters
  1-2 (the canonical reference of the recursion); Khalil, Nonlinear
  Systems (Prentice Hall, 3rd ed.) chapter 14. Deterministic offline
  closed-form evaluation given f1, f2, the reference and the gains - no
  search, no iteration, no adaptation. Corpus tokens of the leaf (receipt
  gate (f), all hyphenated compounds): backstepping-control,
  integrator-backstepping, strict-feedback, virtual-control,
  control-lyapunov-function, recursive-control-design,
  backstepping-control-law, error-variable-recursion.
- Claim fences (quoted from the sibling SKILL.md files at spec time,
  re-verified fresh; the nearest owners fence out first-order online
  adaptation, state-predictor filtering, the error-surface switching law
  and Lie-derivative cancellation, none of which is the strict-feedback
  recursion, which is the exact gap this leaf closes):
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
    adaptive control assessment. Trigger: adaptive-control, mrac,
    model-reference-adaptive, adaptation-law, tracking-error,
    unknown-plant." Its plant is FIRST-ORDER with an UNKNOWN coefficient
    and its gains update ONLINE by a gradient rule (body lines 56-61
    quoted in the Pack bullet); it performs no recursion, no virtual
    control and no strict-feedback construction. This leaf's plant model
    is KNOWN exactly (f1(x1) = x1^2 and f2(x1, x2) = x1 x2 given), its
    design gains c1, c2 are fixed inputs, nothing is estimated, adapted
    or identified, and its Lyapunov function is the composite V2 of the
    recursion, not a single-state convergence certificate.
  - l1-adaptive-control (this pack) is the L1-PREDICTOR fence: its
    frontmatter description reads "Use when you must design and simulate
    an l1-adaptive-control law for a first-order plant with an unknown
    coefficient: run the state-predictor from the design model, drive
    the projection-based-adaptation-law with the prediction error, pass
    the adaptive signal through the low-pass filter omega_c/(s +
    omega_c) and form the control as the feedforward minus the filtered
    estimate. Produces the tracking-error and prediction-error time
    histories, the sigma_hat and filtered-signal histories, the
    projection engagement, the convergence verdict and the certified
    transient-bound check that gate an L1 adaptive control assessment.
    Trigger: l1-adaptive-control, state-predictor,
    low-pass-filtered-adaptation, projection-based-adaptation-law,
    guaranteed-transient-response." Its related-leaves list names only
    adaptive-control, control-allocation, state-space-analysis,
    observer-design and python-control-design; its structure is a state
    predictor plus projection adaptation plus low-pass filter on a
    first-order plant. The new leaf runs no predictor, no projection, no
    filter and no adaptive signal; its recursion is a constructive
    state-feedback design for a KNOWN second-order strict-feedback
    plant.
  - sliding-mode-control (this pack, wave 48) is the SWITCHING-LAW fence:
    its frontmatter description reads "Use when you must design a
    sliding-mode-control law for a second-order plant with matched
    uncertainty: choose the sliding surface from the tracking error and
    its derivative, compute the equivalent control that holds the
    surface on the nominal model, add the switching term sized above the
    uncertainty bound inside the boundary layer to enforce the
    reachability condition, and suppress chattering with the saturation
    thickness. Produces the surface and equivalent-control histories, the
    sliding-condition audit of the reachability inequality at every
    sample, the finite-time reach of the boundary layer, the
    boundary-layer command with the chattering-suppression check, and
    the tracking-error history that gate a sliding-mode control
    assessment. Trigger: sliding-mode-control, sliding-surface-design,
    equivalent-control, constant-plus-proportional-reaching-law,
    switching-term, chattering-suppression, matched-uncertainty,
    variable-structure-control, boundary-layer-command." Its
    related-leaves list names adaptive-control, l1-adaptive-control,
    pid-control-design, gain-scheduling, h-infinity-control and
    deadbeat-control only; its plant is the pinned two-state canonical
    form x_ddot = f_nom + d + u with the given matched-uncertainty bound
    F, never a strict-feedback chain, and its control switches on the
    error surface s = e_dot + lambda e, never a recursion. The new leaf
    has no uncertainty bound, no surface, no switching term and no
    reachability condition; its control is a continuous nonlinear
    state-feedback law built one error variable at a time.
  - feedback-linearization (this pack, wave 48) is the CANCELLATION
    fence: its frontmatter description reads "Use when you must apply
    feedback linearization to a nonlinear plant with a known exact
    model: compute the Lie derivatives of the output along the drift and
    control vector fields to establish the relative degree, invert the
    decoupling scalar at the operating state, form the linearizing
    control that cancels the nonlinear terms so the output channel obeys
    the linear relation y^(r) = v, apply the outer linear tracking loop
    with the assigned closed-loop pole placement, and check the internal
    dynamics via their zero dynamics before accepting the design.
    Produces the relative-degree verdict, the linearizing control with
    the decoupling scalar, the exactly linearized closed-loop response
    against the assigned closed form, and the zero-dynamics stability
    verdict that gates the design. Trigger: feedback linearization,
    input output linearization, lie derivative, relative degree,
    decoupling matrix, linearizing control, zero dynamics, internal
    dynamics stability." Its related-leaves list names
    state-space-analysis, sliding-mode-control ("the switching-law
    sibling of the same nonlinear vein"), adaptive-control and
    gain-scheduling; its identity is the Lie-derivative, relative-degree,
    decoupling-inversion construction, disjoint from the backstepping
    recursion (receipt GO 1 (b), verbatim: "feedback-linearization owns
    the Lie-derivative/relative-degree/decoupling inversion identity,
    disjoint from the backstepping recursion"). The new leaf computes no
    Lie derivatives, no relative degree, no decoupling scalar, no
    input-output linearization and no zero dynamics; its linear closed
    loop appears in the ERROR COORDINATES (z1, z2) as a byproduct of the
    recursion, and the plant nonlinearities are never inverted, only
    compensated through the virtual control and its derivative.
  - observer-design (this pack) is the ESTIMATION fence: its
    frontmatter description reads (receipt GO 1 (b), verbatim) "design a
    full-order Luenberger state observer for a linear time-invariant
    system ... compute the estimator gain matrix by pole placement with
    the Ackermann formula ... confirm the separation principle". The new
    leaf assumes x1 and x2 are MEASURED plant states; there is no
    estimator, no observer gain and no disturbance estimate anywhere.
  - Whole-tree greps at prep (probe receipt gate (a)) and re-verified at
    spec time (this file): `rg -i -l 'backstepping|back-stepping|
    strict-feedback|integrator-back' skills/ -g 'SKILL.md'` -> 0 hits
    (exit 1), and `rg -ic 'backstepping|back-stepping|strict-feedback|
    virtual-control|control-lyapunov'` eval/hit1-corpus.yaml -> 0 hits
    (exit 1). GENUINE gnc-autonomy/control gap (probe receipt task-0,
    verified zero-owner, GO rank 1): no leaf owns the error-variable
    recursion of the strict-feedback design, the adaptive fences (quoted
    above) cover only first-order MRAC/L1 structures, and the two
    landed nonlinear siblings own the switching law and the
    Lie-derivative cancellation, leaving the recursive construction
    entirely absent from the tree.
- Standards id: arp4754a (ARP4754A, Guidelines for Development of Civil
  Aircraft and Systems, SAE; reference-only control-pack convention, the
  same id the pid-control-design, digital-control-design, observer-design,
  deadbeat-control, smith-predictor, sliding-mode-control,
  feedback-linearization and h-infinity-control leaves carry; present in
  standards-map.yaml, grep 'id: arp4754a' at line 38, re-verified at spec
  time). Standards are reference-only, never reproduced verbatim. Ledger
  Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design and simulate the backstepping control law for a second-order
strict-feedback plant by the recursive error-variable construction, and
audit the closed loop with the composite quadratic-Lyapunov function. The
plant is the strict-feedback pair x1_dot = x2 + f1(x1) with f1(x1) = x1^2
and x2_dot = u + f2(x1, x2) with f2(x1, x2) = x1 x2, both drift
nonlinearities KNOWN exactly to the controller (x1 and x2 measured), with
unit control effectiveness, tracking the reference x1d(t) (a given
constant or the given smooth exponential step REF_SETPOINT (1 - e^-t)).
The design is the error-variable change of coordinates: the tracking
error z1 = x1 - x1d is stabilized in the first step by the virtual
control alpha1 = -c1 z1 + x1d_dot - f1 (c1 > 0 a given design gain), which
makes the first candidate V1 = z1^2/2 read V1_dot = -c1 z1^2 + z1 z2 with
the inner-state mismatch z2 = x2 - alpha1 as the second error variable;
the second step differentiates the virtual control ANALYTICALLY ALONG THE
PLANT, alpha1_dot = -c1 (x1_dot - x1d_dot) + x1d_ddot - (df1/dx1) x1_dot
with x1_dot = x2 + f1(x1), and assembles the final control u = -f2 +
alpha1_dot - z1 - c2 z2 (c2 > 0 a given design gain). The construction
cancels f1 and f2 out of the error dynamics exactly: the closed loop in
the error coordinates is the LINEAR system z1_dot = -c1 z1 + z2, z2_dot =
-z1 - c2 z2, independent of the plant nonlinearities and of the reference,
and the composite candidate V2 = V1 + z2^2/2 = (z1^2 + z2^2)/2 decays as
V2_dot = -c1 z1^2 - c2 z2^2 < 0, the quadratic-Lyapunov audit. With equal
design gains c1 = c2 = c the error flow has the closed form z(t) =
exp(-c t) R(t) z(0) with the rotation R(t) (unit natural frequency from
the +z2 / -z1 coupling), so |z| decays at rate c and V2(t) = V2(0)
exp(-2 c t) exactly, giving asymptotic tracking with the error rates set
by c1, c2. Produces the error-variable histories z1 and z2, the virtual
control and its analytic derivative histories, the recursive control-law
history u, the exactly linear error-coordinate dynamics with the
closed-form decay audit, the tracking-error history with its settling and
zero-crossing milestones, and the verdict numbers that gate a
backstepping control assessment. Does NOT do: model-reference adaptive
control, gradient or projection adaptation laws, unknown-coefficient
estimation, state predictors and low-pass-filtered adaptive signals
(gnc-autonomy/control/adaptive-control and l1-adaptive-control, which is
why f1 and f2 are known inputs here and nothing adapts online); sliding
surfaces, equivalent control, switching terms, matched-uncertainty bounds
or reachability conditions (sliding-mode-control, the switching-law
sibling of the same nonlinear vein, which is why this law is continuous
and no bound F appears); Lie derivatives, relative degree, decoupling
matrices, input-output linearization, zero dynamics or any plant
inversion (feedback-linearization, the cancellation sibling of the same
vein, which is why the nonlinearities are compensated through the virtual
control and its derivative and never inverted); P-I-D gain design,
Ziegler-Nichols or pole-placement tuning, anti-windup, integrator
clamping, margin checks and linear gain scheduling over an envelope
(pid-control-design, gain-scheduling, which is why c1 and c2 are GIVEN
design inputs, never tuned, never scheduled); deadbeat or other z-domain
design (deadbeat-control, digital-control-design); state estimation or
observers (observer-design; x1 and x2 are measured plant states and there
is no estimator); tuning-function adaptive backstepping or any parameter
estimation extension of the recursion (declined at wave-49 as a separate
leaf, receipt declines table: "pool economy - build the declared
recursion core first, re-probe the adaptive variant only after
backstepping lands"); robustness to disturbances or uncertainty of any
kind (this leaf is the nominal exact-model design; robustness analysis is
neither claimed nor attempted); and any claim that the recursion
linearizes the PLANT or its output channel (only the error coordinates
are linear).

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG, closed form, forward
Euler discrete time. The module pins the worked-example configuration in
module constants: C1_WORKED = 2.0 (1/s), C2_WORKED = 2.0 (1/s), C_RATE =
4.0 (1/s), REF_SETPOINT = 1.0, INIT_X1 = 0.0, INIT_X2 = 0.0, DT = 0.001
(s), SIM_TIME = 6.0 (s), SETTLE_LEVEL = 0.01, TOL = 1e-6, KIND_CONST =
"constant", KIND_EXP = "exponential". No imports beyond math.

Defining relations (pin these exactly; every function derives from them):
- Plant: second-order strict feedback x1_dot = x2 + f1(x1), x2_dot = u +
  f2(x1, x2) with unit control gain, f1(x1) = x1^2, f2(x1, x2) = x1 x2,
  both drift terms known exactly.
- Reference: kind "constant" gives x1d = REF_SETPOINT with x1d_dot = 0,
  x1d_ddot = 0; kind "exponential" gives x1d(t) = REF_SETPOINT (1 - e^-t)
  with x1d_dot = REF_SETPOINT e^-t and x1d_ddot = -REF_SETPOINT e^-t.
- Error variable (step 1): z1 = x1 - x1d, so z1_dot = x2 + f1(x1) -
  x1d_dot.
- Virtual control (step 1): alpha1 = -c1 z1 + x1d_dot - f1(x1); with x2 =
  alpha1 the z1 subsystem obeys z1_dot = -c1 z1 and V1 = z1^2/2 decays as
  V1_dot = -c1 z1^2.
- Mismatch (step 2): z2 = x2 - alpha1, the second error variable; z1_dot
  = -c1 z1 + z2 and V1_dot = -c1 z1^2 + z1 z2 along the open chain.
- Analytic derivative along the plant: alpha1_dot = -c1 (x1_dot -
  x1d_dot) + x1d_ddot - (df1/dx1) x1_dot with x1_dot = x2 + f1(x1) taken
  from the PLANT (never from the closed loop) and df1/dx1 = 2 x1.
- Final control (step 2): u = -f2(x1, x2) + alpha1_dot - z1 - c2 z2;
  substituting into z2_dot = u + f2 - alpha1_dot gives z2_dot = -z1 - c2
  z2.
- Closed-loop error coordinates (EXACT, reference independent): z1_dot =
  -c1 z1 + z2 and z2_dot = -z1 - c2 z2, the linear system with matrix
  [[-c1, 1], [-1, -c2]]; the coupling matrix [[0, 1], [-1, 0]] is
  skew-symmetric, so V2 = (z1^2 + z2^2)/2 has V2_dot = -c1 z1^2 - c2 z2^2
  with no cross term.
- Equal-gain closed form (c1 = c2 = c): z1(t) = e^-ct (z1(0) cos t +
  z2(0) sin t), z2(t) = e^-ct (z2(0) cos t - z1(0) sin t), V2(t) = V2(0)
  e^-2ct.
- Equilibrium (constant reference x1d = 1): z1 = z2 = 0 pins x1 = 1 and
  x2 = alpha1 = -f1(1) = -1 (the virtual control at the reference IS the
  steady-state velocity that holds the drift, x1_dot = x2 + x1^2 = 0);
  the steady command is u = -f2(1, -1) = +1.
- Discrete simulation (forward Euler at the fixed dt, control recomputed
  EVERY sample from the current state): x1[k+1] = x1[k] + dt (x2[k] +
  f1(x1[k])); x2[k+1] = x2[k] + dt (u[k] + f2(x1[k], x2[k])).
- Initial conditions zero (x1(0) = 0, x2(0) = 0); worked and rate cases
  use the constant reference 1.0 so z1(0) = -1; the feedforward case
  starts on the reference, x1d(0) = 0, so z1(0) = 0.

Functions (signatures, return shapes, ValueErrors; validated identically
by every public function):
- f1(x1) -> float
  x1^2, the channel-1 drift. No guard.
- df1(x1) -> float
  2 x1, the analytic derivative of f1. No guard.
- f2(x1, x2) -> float
  x1 x2, the channel-2 drift. No guard.
- reference(t, kind) -> (float, float, float)
  (x1d, x1d_dot, x1d_ddot) at time t for the "constant" or "exponential"
  kind. ValueError: kind not in {"constant", "exponential"}
  ("reference kind must be 'constant' or 'exponential', got ...").
- tracking_error(x1, x1d) -> float
  z1 = x1 - x1d. No guard.
- virtual_control(z1, ref_dot, f1_value, c1) -> float
  alpha1 = -c1 z1 + ref_dot - f1_value. ValueError: c1 <= 0 ("design
  gain c1 must be positive, got ...").
- virtual_control_derivative(x1, x2, ref_dot, ref_ddot, c1) -> float
  alpha1_dot = -c1 (x1_rate - ref_dot) + ref_ddot - df1(x1) x1_rate with
  x1_rate = x2 + f1(x1), the analytic derivative along the plant.
  ValueError: c1 <= 0 ("design gain c1 must be positive, got ...").
- mismatch_error(x2, alpha1) -> float
  z2 = x2 - alpha1. No guard.
- final_control(f2_value, alpha1_dot, z1, z2, c2) -> float
  u = -f2_value + alpha1_dot - z1 - c2 z2. ValueError: c2 <= 0 ("design
  gain c2 must be positive, got ...").
- v2_value(z1, z2) -> float
  V2 = (z1^2 + z2^2) / 2. No guard.
- z1_closed_form(t, z1_0, z2_0, c) -> float
  e^-ct (z1_0 cos t + z2_0 sin t), the equal-gain closed form. No guard.
- z2_closed_form(t, z1_0, z2_0, c) -> float
  e^-ct (z2_0 cos t - z1_0 sin t). No guard.
- v2_closed_form(t, z1_0, z2_0, c) -> float
  V2(0) e^-2ct with V2(0) = (z1_0^2 + z2_0^2) / 2. No guard.
- simulate(c1, c2, kind, x1_0 = INIT_X1, x2_0 = INIT_X2, dt = DT,
  sim_time = SIM_TIME) -> dict
  Closed-loop forward-Euler simulation of the strict-feedback plant
  under the recursive backstepping control tracking the given reference
  kind. Returns {"t", "x1", "x2", "z1", "z2", "alpha1", "alpha1_dot",
  "u", "V2", "x1d" (series), "n", "z1_map_max_res" (max |z1[k+1] -
  (z1[k] + dt (-c1 z1[k] + z2[k]))|), "z2_map_max_res" (max |z2[k+1] -
  (z2[k] + dt (-z1[k] - c2 z2[k]))|), "v2dot_res_max" (max |(V2[k+1] -
  V2[k])/dt - (-c1 z1[k]^2 - c2 z2[k]^2)|), "first_zero_k",
  "first_zero_t" (first z1 sign change), "settle_1pct_k",
  "settle_1pct_t" (first sample from which |z1| <= SETTLE_LEVEL for ALL
  later samples, None when never), "realized_c" (-ln(V2(2.0)/V2(0)) /
  (2 * 2.0), the realized V2 decay rate over the [0, 2.0 s] window),
  "max_abs_u", "final" (dict of x1, x2, z1, z2, alpha1, alpha1_dot, u,
  V2 at the final sample)}. ValueErrors: c1 <= 0 ("design gain c1 must
  be positive, got ..."), c2 <= 0 ("design gain c2 must be positive, got
  ..."), dt <= 0 ("sample time dt must be positive, got ..."),
  sim_time <= 0 ("simulation time sim_time must be positive, got ..."),
  and the reference kind guard of reference().

Identities to test (closed form, exact where noted; checkable without
the builder module):
- Recursion definitions cancel f1 and the reference out of the z1
  update: with a CONSTANT reference the discrete z1 map z1[k+1] = z1[k] +
  dt (-c1 z1[k] + z2[k]) holds EXACTLY at every sample (float rounding
  only), because x2 + f1 - x1d_dot = z2 - c1 z1 is an algebraic identity
  of the definitions: real anchor max |z1-map residual| = 1.110223e-16
  over the 6000 worked-case steps (1.110223e-16 in the rate case), the
  machine-exact witness that z2 is the true mismatch and the
  error-coordinate construction is closed. For the exponential reference
  the same residual is bounded by the reference Euler discretization,
  real max 4.998334e-07.
- Analytic-derivative consistency of the z2 update: the one-step linear
  prediction z2[k+1] = z2[k] + dt (-z1[k] - c2 z2[k]) holds up to the
  Euler curvature residual -(dt^2/2) alpha1_ddot of the analytic
  derivative: real worked max 1.500108e-06, rate max 4.703210e-06,
  feedforward max 1.085667e-06. An O(1) error in alpha1_dot (for
  example dropping the -(df1/dx1) x1_dot term) injects an O(dt) term of
  order 1e-3 into this residual, so the check separates the exact
  derivative from any incorrect one.
- Quadratic-Lyapunov decay: V2_dot = -c1 z1^2 - c2 z2^2 exactly in
  continuous time; the realized decay rate over [0, 2.0] s is real
  2.002007924 against c = 2.0 (worked, 0.10 percent high), 4.008645719
  against c = 4.0 (rate, 0.22 percent high), and 2.004184471 against
  c = 2.0 (feedforward, 0.21 percent high), all within 1 percent; V2 is
  monotone non-increasing in every run.
- Equal-gain closed form in the error coordinates: real worked
  |z1 - closed| at t = 0.5/1.0/2.0/4.0/6.0 s = 8.805e-05, 5.322e-04,
  2.546e-04, 4.186e-06, 9.323e-08 and |z2 - closed| = 1.367e-03,
  1.005e-03, 6.298e-06, 7.062e-06, 1.927e-07; V2 ratio V2(t)/V2(0)
  against e^-4t rel diff 2.07e-03, 4.19e-03, 8.00e-03, 1.53e-02,
  2.49e-02 at the same times (the growth of the rel diff is the
  accumulated O(dt) Euler phase lag of the discretized rotation, not a
  modeling error). Real rate-case |dz2| diffs 2.991e-03, 5.850e-04,
  8.321e-06, 1.169e-08, 7.642e-12 at the five sample times (max
  2.991e-03 at t = 0.5 s); feedforward |dz1| diffs 2.643e-05,
  2.524e-04, 1.964e-04, 2.320e-06, 7.520e-08 (max 2.524e-04 at
  t = 1.0 s).
- First z1 zero crossing: real worked 2.673000 s against the closed form
  pi + atan(0.5/-1) = 2.677945 s (the sim leads by the O(dt) rotation
  phase, 4.9e-03 s); real rate 2.889000 s against pi + atan(0.25/-1) =
  2.896614 s; real feedforward 3.127000 s against pi = 3.141593 s (the
  exponential reference carries an O(dt) tracking lag; probe at dt =
  1e-4 shrinks the feedforward V2(6.0) closed-form rel diff from 4.05e-01
  to 3.71e-02, confirming the artifact is first-order in dt).
- One-percent tracking settle (|z1| <= 0.01 for all later samples): real
  worked 2.254000 s, rate 1.499000 s, feedforward 2.192000 s.
- Virtual-control equilibrium identity: at the constant reference the
  virtual control converges to alpha1(x1d) = -f1(x1d) = -1, exactly the
  steady-state velocity x2_ss needed to hold x1 = 1 against the drift:
  real worked alpha1(6.0) = -0.999989763 against x2(6.0) = -1.000003087
  and x2_ss = -1.000000000; the steady command is u_ss = -f2(1, -1) =
  +1: real worked |u(6.0) - 1| = 6.255e-05 and rate |u(6.0) - 1| =
  1.731e-09; x2(6.0) + f1(x1(6.0)) = 8.205e-06 (worked) and 1.618e-10
  (rate), the achieved x1 rate at the final sample.
- Tracking a moving reference: feedforward case z1(0) = 0, z2(0) = -1,
  the error develops purely from the reference motion and decays: max
  |z1| closed form 0.176927688 at t = 0.463648 s (d/dt of e^-2t sin t)
  against real sim 0.176976673 at the 0.464 s sample (diff 4.9e-05); at
  the final sample x1 = 0.997522889 against x1d = 0.997521248 (gap
  1.642e-06, the z1 residual).
- ValueErrors across the module and determinism: the guards enumerated in
  the Worked example raise ValueError with the real messages quoted
  there; identical outputs run to run and under both interpreters; no
  randomness; no imports beyond math; the module constants fixed as
  above.

## Worked example

Plant: x1_dot = x2 + x1^2, x2_dot = u + x1 x2, both drift terms known
exactly, x1 and x2 measured, unit control gain. Design: error variable
z1 = x1 - x1d; virtual control alpha1 = -c1 z1 + x1d_dot - x1^2; mismatch
z2 = x2 - alpha1; analytic derivative alpha1_dot = -c1 (x1_dot -
x1d_dot) + x1d_ddot - 2 x1 x1_dot with x1_dot = x2 + x1^2 (equivalently
-(c1 + 2 x1) (x2 + x1^2) + c1 x1d_dot + x1d_ddot); final control u =
-x1 x2 + alpha1_dot - z1 - c2 z2. Design gains c1 = c2 = 2.0 (1/s)
worked and feedforward, c1 = c2 = 4.0 rate case. Reference x1d = 1.0
constant (worked, rate) or x1d(t) = 1 - e^-t (feedforward); initial state
x1(0) = 0, x2(0) = 0. Simulation: forward Euler at dt = 0.001 s over a
6.0 s horizon (6001 samples).

All values below are REAL outputs of the prep anchor
anchor_backstepping.py (pure stdlib, math only, no RNG, exit 0, internal
asserts all pass, repo-relative path
ops/automation/state/wave49-specs/anchors/anchor_backstepping.py), run
once at spec time under both interpreters with byte-identical output and
quoted as printed:

- Worked case A (constant reference x1d = 1.0, c1 = c2 = 2.0, module
  output):
  - initial error variables: z1(0) = -1.000000000, z2(0) = -2.000000000
    (alpha1(0) = 2.000000000), V2(0) = 2.500000000; initial command
    u(0) = 5.000000000 (max |u| over the run = 5.000000000).
  - audit residuals: z1-map max |z1[k+1] - (z1[k] + dt (-c1 z1[k] +
    z2[k]))| = 1.110223e-16; z2-map max |z2[k+1] - (z2[k] + dt (-z1[k] -
    c2 z2[k]))| = 1.500108e-06; V2-dot max |(V2[k+1] - V2[k])/dt -
    (-c1 z1^2 - c2 z2^2)| = 1.250000e-02 (the Euler curvature (dt/2)
    |A z|^2 at k = 0).
  - realized decay rate over [0, 2.0] s = 2.002007924 vs design c = 2.0.
  - final sample T = 6.0 s: x1 = 0.999997441 (x1d = 1.000000000), x2 =
    -1.000003087, z1 = -2.559141e-06, z2 = -1.332307e-05, alpha1 =
    -0.999989763, u = 1.000062552, V2 = 9.202671e-11.
  - first z1 zero crossing at t = 2.673000 s (closed form 2.677945 s);
    1-percent settle at t = 2.254000 s.
  - V2 ratio vs closed form e^-4t: t = 0.5 s rel diff 2.07e-03, t = 1.0 s
    rel diff 4.19e-03, t = 2.0 s rel diff 8.00e-03, t = 4.0 s rel diff
    1.53e-02, t = 6.0 s rel diff 2.49e-02.
  - closed-form error-coordinate comparisons (sim vs closed, |diff|):
    t = 0.5 s: z1 -0.675498135 / -0.675586181 (8.805e-05), z2
    -0.467951252 / -0.469318366 (1.367e-03); t = 1.0 s: z1
    -0.300351219 / -0.300883394 (5.322e-04), z2 -0.031357737 /
    -0.032363217 (1.005e-03); t = 2.0 s: z1 -0.025432110 / -0.025686731
    (2.546e-04), z2 0.031892056 / 0.031898354 (6.298e-06); t = 4.0 s:
    z1 0.000722845 / 0.000727031 (4.186e-06), z2 0.000177605 /
    0.000184667 (7.062e-06); t = 6.0 s: z1 -0.000002559 / -0.000002466
    (9.323e-08), z2 -0.000013323 / -0.000013516 (1.927e-07).
  - equilibrium identity at T = 6.0 s: |x1 - x1d| = 2.559e-06, |x2 +
    f1(x1)| = 8.205e-06 (x1 rate), |u - u_ss| = 6.255e-05 (u_ss =
    1.000000000).
  - sample points (module output): t = 0.5 s: x1 0.324501865, x2
    0.777743557, z1 -0.675498135, z2 -0.467951252, alpha1 1.245694809,
    alpha1_dot -2.339189546, u -0.980168142; t = 1.0 s: x1 0.699648781,
    x2 0.079836286, z1 -0.300351219, z2 -0.031357737, alpha1
    0.111194023, alpha1_dot -1.935372058, u -1.628162725; t = 2.0 s:
    x1 0.974567890, x2 -0.867026298, z1 -0.025432110, z2 0.031892056,
    alpha1 -0.898918354, alpha1_dot -0.326815767, u 0.479808221;
    t = 4.0 s: x1 1.000722845, x2 -1.002714299, z1 0.000722845, z2
    0.000177605, alpha1 -1.002891904, alpha1_dot 0.005074176, u
    1.007435226; t = 6.0 s: x1 0.999997441, x2 -1.000003087, z1
    -0.000002559, z2 -0.000013323, alpha1 -0.999989763, alpha1_dot
    0.000032819, u 1.000062552.
- Rate case B (constant reference x1d = 1.0, c1 = c2 = 4.0, module
  output): initial error variables z1(0) = -1.000000000, z2(0) =
  -4.000000000 (alpha1(0) = 4.000000000), V2(0) = 8.500000000; initial
  command u(0) = 17.000000000 (max |u| 17.000000000); z1-map max
  1.110223e-16, z2-map max 4.703210e-06; realized decay rate over
  [0, 2.0] s = 4.008645719 vs c = 4.0; final T = 6.0 s: x1 =
  1.000000000, x2 = -1.000000000, z1 = 3.466560e-12, z2 = -1.478968e-10,
  alpha1 = -1.000000000, u = 1.000000002, V2 = 1.094274e-20; first z1
  zero crossing 2.889000 s (closed form 2.896614 s); 1-percent settle
  1.499000 s; equilibrium identity: |x1 - x1d| = 3.467e-12, |x2 +
  f1(x1)| = 1.618e-10, |u - u_ss| = 1.731e-09. Doubling the gains halves
  the decay time constant (settle 1.499 s vs 2.254 s) at four times the
  initial command (17 vs 5), the c1, c2 error-rate lever the receipt
  names.
- Feedforward case C (reference x1d(t) = 1 - e^-t, c1 = c2 = 2.0, module
  output): initial error variables z1(0) = 0.000000000, z2(0) =
  -1.000000000 (alpha1(0) = 1.000000000), V2(0) = 0.500000000; initial
  command u(0) = 3.000000000; the reference starts with x1d_dot(0) = 1
  and x1d_ddot(0) = -1, so both feedforward terms are live; max |z1|
  closed form 0.176927688 at t = 0.463648 s, sim z1(0.464 s) =
  -0.176976673; realized decay rate over [0, 2.0] s = 2.004184471 vs
  c = 2.0; audit residuals z1-map max 4.998334e-07 (reference Euler
  discretization), z2-map max 1.085667e-06; final T = 6.0 s: x1d =
  0.997521248, x1 = 0.997522889, x2 = -0.992583541, z1 = 1.641553e-06,
  z2 = -7.095415e-06, alpha1 = -0.992576446, u = 0.982754838, V2 =
  2.651980e-11; first z1 zero crossing 3.127000 s (closed form pi =
  3.141593 s); 1-percent settle 2.192000 s; max |u| 3.000000000. The
  error dynamics are reference independent: the same realized rate as
  case A within 0.1 percent while x1 tracks the moving reference to a
  1.642e-06 gap at T.
- ValueErrors with real messages (module output, quoted as printed):
  virtual_control(0.1, 0.0, 0.1, 0.0) raises "design gain c1 must be
  positive, got 0.0"; virtual_control_derivative(0.1, 0.0, 0.0, 0.0,
  0.0) raises "design gain c1 must be positive, got 0.0";
  final_control(0.1, 0.0, 0.1, 0.1, 0.0) raises "design gain c2 must be
  positive, got 0.0"; simulate(c1 = 0.0) raises "design gain c1 must be
  positive, got 0.0"; simulate(c2 = 0.0) raises "design gain c2 must be
  positive, got 0.0"; simulate(dt = 0.0) raises "sample time dt must be
  positive, got 0.0"; simulate(sim_time = 0.0) raises "simulation time
  sim_time must be positive, got 0.0"; reference(0.5, 'ramp') raises
  "reference kind must be 'constant' or 'exponential', got 'ramp'".

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of anchor_backstepping.py (stdlib math,
closed form, exit 0, no randomness, byte-identical under both
interpreters).

## Validation list (contract test must include)

1. Recursion algebra: virtual_control(-1.0, 0.0, 0.0, 2.0) = 2.0 exactly
   (alpha1(0) of the worked case); mismatch_error(0.0, 2.0) = -2.0
   exactly (z2(0)); v2_value(-1.0, -2.0) = 2.5 within 1e-12; z2 = x2 -
   alpha1 with alpha1 = -c1 z1 - f1 satisfies x2 + f1 - x1d_dot = -c1 z1
   + z2 at every sample of the worked run (assert the max |z1-map
   residual| = 1.110223e-16 < 1e-9).
2. z1-map machine-exactness: worked and rate runs have max |z1[k+1] -
   (z1[k] + dt (-c1 z1[k] + z2[k]))| = 1.110223e-16 below 1e-9;
   feedforward run 4.998334e-07 below 1e-5 (the reference Euler
   discretization bound (dt^2/2) |x1d_ddot|).
3. z2-map analytic-derivative consistency: worked max 1.500108e-06, rate
   max 4.703210e-06, feedforward max 1.085667e-06, each below 1e-3 (an
   O(1) alpha1_dot error would inject an O(dt) term near 1e-3 and fail
   the bound).
4. Quadratic-Lyapunov decay: V2 monotone non-increasing in all three
   runs (0 violations of V2[k+1] <= V2[k] + TOL); realized decay rate
   over [0, 2.0] s within 1 percent of the design gain: worked
   2.002007924 vs 2.0, rate 4.008645719 vs 4.0, feedforward 2.004184471
   vs 2.0.
5. Equal-gain closed form: worked |z1 - z1_closed_form| below 1e-3 at
   t = 0.5/1.0/2.0 s (real 8.805e-05, 5.322e-04, 2.546e-04) and below
   1e-5 at t = 4.0/6.0 s (real 4.186e-06, 9.323e-08); |z2 - closed|
   below 3e-3 at all five times (real max 1.367e-03 at t = 0.5 s); V2
   ratio V2(t)/V2(0) within 5 percent relative of e^-4t at t = 0.5/1.0/
   2.0/4.0 s (real rel diffs 2.07e-03, 4.19e-03, 8.00e-03, 1.53e-02) and
   within 10 percent at t = 6.0 s (real 2.49e-02).
6. Rate case: z2(0) = -4.0, V2(0) = 8.5, u(0) = 17.0 within 1e-9; z1(6.0)
   = 3.466560e-12 below 1e-9 in magnitude; x1(6.0) = 1.000000000 and
   x2(6.0) = -1.000000000 within 1e-6; u(6.0) = 1.000000002 within 1e-6
   of u_ss = 1; settle 1.499000 s within 0.05 s of the worked 2.254000 s
   minus the halved time constant (settle_B < settle_A).
7. Equilibrium identities: worked x1(6.0) = 0.999997441 within 1e-4 of
   1.0; x2(6.0) = -1.000003087 within 1e-4 of -f1(1.0) = -1.0;
   alpha1(6.0) = -0.999989763 within 1e-4 of x2_ss; u(6.0) =
   1.000062552 within 1e-3 of u_ss = -f2(1.0, -1.0) = 1.0; |x2(6.0) +
   f1(x1(6.0))| = 8.205e-06 below 1e-4 (achieved x1 rate).
8. Worked sample points within 1e-5: x1(0.5) = 0.324501865, x1(1.0) =
   0.699648781, x1(2.0) = 0.974567890, x1(4.0) = 1.000722845, x1(6.0) =
   0.999997441; u(0.5) = -0.980168142, u(1.0) = -1.628162725, u(2.0) =
   0.479808221, u(4.0) = 1.007435226, u(6.0) = 1.000062552; z1(0.5) =
   -0.675498135, z1(1.0) = -0.300351219, z1(2.0) = -0.025432110,
   z1(4.0) = 0.000722845, z1(6.0) = -0.000002559.
9. Milestones: worked first z1 zero crossing 2.673000 s within 0.01 s of
   the closed form pi + atan(0.5/-1) = 2.677945 s; worked 1-percent
   settle 2.254000 s (assert |z1| <= 0.01 for every sample after it);
   rate crossing 2.889000 s within 0.01 s of 2.896614 s; feedforward
   crossing 3.127000 s within 0.05 s of pi (the moving-reference O(dt)
   lag documented in the Identities section).
10. Feedforward tracking: max |z1| over the run within 2e-4 of the
    closed form 0.176927688 at t = 0.463648 s (real sim 0.176976673 at
    the 0.464 s sample); |x1(6.0) - x1d(6.0)| = 1.642e-06 below 1e-4
    with x1d(6.0) = 0.997521248; z1 closed-form diffs below 1e-3 at all
    five sample times (real max 2.524e-04 at t = 1.0 s); realized rate
    2.004184471 within 1 percent of 2.0 (reference independence of the
    error dynamics).
11. All ValueErrors enumerated in the Worked example raise from the named
    public function with the real messages quoted there: c1 guards
    (virtual_control, virtual_control_derivative, simulate), c2 guards
    (final_control, simulate), dt and sim_time guards (simulate), and
    the reference kind guard (reference).
12. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math; module
    constants fixed as C1_WORKED 2.0, C2_WORKED 2.0, C_RATE 4.0,
    REF_SETPOINT 1.0, INIT_X1 0.0, INIT_X2 0.0, DT 0.001, SIM_TIME 6.0,
    SETTLE_LEVEL 0.01. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.
13. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave49-backstepping-control.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "design the backstepping control law for the strict-feedback plant:
  choose the virtual control that stabilizes the first error variable,
  propagate the inner-state mismatch as the second error variable, and
  assemble the final control with the Lyapunov-derivative audit"
  intent: "gnc-autonomy/control; backstepping-control: the virtual
  control chosen to stabilize the first error variable, the inner-state
  mismatch propagated as the second error variable, and the final
  control assembled with the Lyapunov-derivative audit"
  expected_skill: "gnc-autonomy/control/backstepping-control"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply integrator-backstepping to the second-order strict-feedback
  nonlinear system: compute the virtual control and its analytic
  derivative, form the recursive backstepping control law and verify the
  closed-loop Lyapunov function decays"
  intent: "gnc-autonomy/control; integrator-backstepping on the
  second-order strict-feedback nonlinear system: the virtual control and
  its analytic derivative computed, the recursive backstepping control
  law formed, and the closed-loop Lyapunov decay verified"
  expected_skill: "gnc-autonomy/control/backstepping-control"
Task ids: w49-backstepping-control-1 and -2. Prep grep (run at spec time
by the probe and re-verified for this file): each of the tokens
backstepping, back-stepping, strict-feedback, virtual-control and
control-lyapunov returns ZERO matches in eval/hit1-corpus.yaml (grep exit
1) and ZERO skills/ hits, so the queries are collision-free; the sibling
corpus tasks route on adaptation-language wording (adaptive-control,
l1-adaptive-control), surface/reaching-law/boundary-layer wording
(w48-sliding-mode-control-1/-2), Lie-derivative/relative-degree/decoupling
wording (w48-feedback-linearization-1/-2) and dgkf/gamma-iteration
wording (w48-h-infinity-synthesis-1/-2), none of which carries the
error-variable recursion identity; the wave-48 receipt sims put query 1
at Hit@1 22.0 vs 11.5 (sliding-mode-control) and query 2 at Hit@1 17.0
vs 12.0 (feedback-linearization), with 0 of 1326 tasks rerouting in the
theft audit. Add one fence line to the adaptive-control and
l1-adaptive-control related-leaves lists and one router row to
skills/gnc-autonomy/SKILL.md at build time pointing the strict-feedback
recursion and virtual-control design to the new leaf (the wave-48
sliding-mode-control and deadbeat-control precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design and simulate the
backstepping control law for a second-order strict-feedback plant
x1_dot = x2 + f1(x1), x2_dot = u + f2(x1, x2) tracking a reference:" and
include the outputs in the Claim order (the virtual control chosen to
stabilize the first error variable, the inner-state mismatch propagated
as the second error variable, the analytic derivative of the virtual
control along the plant, the recursive final control, the
quadratic-Lyapunov decay audit, and the tracking-error history), then
close with the Trigger list. The drift nonlinearities f1 and f2 and the
design gains c1, c2 are given inputs, never identified, adapted or
tuned; the recursion is the exact-model nominal design with no
uncertainty bound, no switching and no plant inversion; and never
reproduce ARP4754A text (reference-only). First tag: backstepping-control.
Metadata tags EXACTLY as the probe receipt gate (f) lists them, nothing
else: backstepping-control, integrator-backstepping, strict-feedback,
virtual-control, control-lyapunov-function, recursive-control-design,
backstepping-control-law, error-variable-recursion. 50-150 words, <=1000
chars, no em dash, action verb present, never the banned sweep term of
the builder kit. Recommended wording (131 words, 987 chars, verified at
spec time):

"Use when you must design and simulate the backstepping control law for a
second-order strict-feedback plant x1_dot = x2 + f1(x1), x2_dot = u +
f2(x1, x2) tracking a reference: choose the virtual control that
stabilizes the first error variable z1 = x1 - x1d, propagate the
inner-state mismatch z2 = x2 - alpha1 as the second error variable,
differentiate the virtual control analytically along the plant, and
assemble the final control from the recursion so the composite Lyapunov
function V2 = (z1^2 + z2^2)/2 decays at the design rates set by c1 and
c2. Produces the error-variable and virtual-control histories, the
analytic virtual-control derivative, the closed-loop command, the
quadratic-Lyapunov decay audit, and the tracking-error history that gate
a backstepping control assessment. Trigger: backstepping-control,
integrator-backstepping, strict-feedback, virtual-control,
control-lyapunov-function, recursive-control-design,
backstepping-control-law, error-variable-recursion."

FORBIDDEN TOKENS (belong to siblings): mrac, model-reference-adaptive,
adaptation-law, adaptive-gain, online-gain-update, unknown-coefficient,
ideal-cancellation, state-predictor, projection-based-adaptation,
low-pass-filtered-adaptation, sigma-hat, guaranteed-transient-response
(adaptive-control, l1-adaptive-control; f1 and f2 are known inputs and
c1, c2 are fixed design gains, nothing adapts); sliding-surface,
sliding-mode, equivalent-control, reaching-law, switching-term,
matched-uncertainty, chattering, boundary-layer and any variable-
structure or disturbance-bound claim (sliding-mode-control; this law is
continuous and no uncertainty bound F exists in the model);
lie-derivative, relative-degree, decoupling-matrix, linearizing-control,
zero-dynamics, internal-dynamics and any plant-inversion or
input-output-linearization claim (feedback-linearization; the closed
loop is linear in the ERROR coordinates only, the plant is never
linearized or inverted); tuning-function, adaptive-backstepping and any
parameter-estimation extension of the recursion (the wave-49 declined
adaptive variant; build the core recursion first); ziegler-nichols,
ultimate-gain, pole-placement, anti-windup, integrator-clamp,
gain-margin, phase-margin and any PID tuning or loop-margin claim
(pid-control-design); gain-scheduling, scheduling-variable,
breakpoint-table (gain-scheduling); deadbeat-control, z-domain and any
discrete transfer-function design claim (deadbeat-control,
digital-control-design); luenberger, estimator-gain, ackermann,
observability, state-estimation (observer-design); h-infinity,
mixed-sensitivity, gamma-iteration, weighted-sensitivity (h-infinity
leaves); disturbance-estimation, system-identification and any claim
that the leaf estimates f1, f2 or a disturbance from data (all model
quantities are inputs). Never the bare single words backstepping,
recursive, lyapunov, virtual, control, plant, gain, error, feedback,
reference or derivative as standalone metadata tags.
