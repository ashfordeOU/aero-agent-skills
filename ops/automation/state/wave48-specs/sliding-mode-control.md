# Wave-48 leaf spec: sliding-mode-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/sliding-mode-control/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, h-infinity-control, l1-adaptive-control,
  lead-lag-compensation, observer-design, pid-control-design,
  python-control-design, root-locus-design, smith-predictor,
  state-space-analysis; no sibling in the pack or anywhere else in the
  tree performs a variable-structure control law: the zero-owner greps
  `sliding[- ]mode|variable[- ]structure|reaching[- ]law|equivalent[- ]control|
  chattering` over the whole skills/ tree return ZERO hits (grep exit 1)
  and the eval/hit1-corpus.yaml scan for the tokens sliding-mode,
  variable-structure, reaching-law, equivalent-control and chattering
  returns 0 matching tasks (grep exit 1), both re-verified fresh at spec
  time. The receipt's runner-up bleed on query 2,
  aerodynamics/boundary-layer/boundary-layer-theory, scores only on the
  generic 'boundary-layer' token (receipt gate (a): 6.5, all from
  desc/body overlap) and is an aerodynamics flow-physics leaf, not a
  control owner; a spec-time boundary-layer re-grep restricted to
  gnc-autonomy also exits 1).
- Provenance: wave-48 recon receipt task-3 GO rank 2 of 3 strong, lines
  176-240 (GO 2 of 3): "design the sliding-mode-control law for the
  second-order plant with matched-uncertainty: choose the sliding-surface
  from the error and its derivative, compute the equivalent-control from
  the nominal model, and add the switching-term inside the boundary-layer
  to enforce the reachability condition." Published deterministic anchor,
  receipt gate (d) (summary-only): sliding-mode control for a
  relative-degree-one (second-order canonical) plant with matched
  uncertainty |f| bounded: sliding surface s = edot + lambda e, sliding
  condition (1/2) d(s^2)/dt <= -eta |s|, equivalent control u_eq from
  setting sdot = 0 on the nominal model, control u = u_eq - k sat(s/phi)
  with the switching gain k sized above the uncertainty bound and the
  boundary-layer thickness phi suppressing chattering; finite-time
  reachability of the boundary layer follows from the
  constant-plus-proportional reaching law. Source: Slotine and Li,
  Applied Nonlinear
  Control (Prentice Hall, 1991), chapter 7 (Sliding Control); the
  switching law and reachability condition are standard closed forms
  (Utkin 1977/1992). Deterministic offline evaluation given the nominal
  model, the uncertainty bound and the surface coefficients. Corpus
  tokens of the leaf (receipt gate (f), all hyphenated compounds):
  sliding-mode-control, sliding-surface-design, equivalent-control,
  constant-plus-proportional-reaching-law, switching-term,
  chattering-suppression, matched-uncertainty, variable-structure-control,
  boundary-layer-command.
- Claim fences (quoted from the sibling SKILL.md files at spec time,
  re-verified fresh from the wave-48 probe receipt quotes; the nearest
  owners fence out first-order online adaptation, frequency-domain norm
  analysis, linear gain design and z-domain synthesis, none of which is a
  time-domain variable-structure switching law, which is the exact gap
  this leaf closes):
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
    unknown-plant." Its model is a first-order plant with an unknown
    coefficient whose gains are updated ONLINE by the adaptation law; it
    has no switching surface, no equivalent control and no
    variable-structure claim anywhere (receipt gate (b), verbatim).
    The new leaf's plant model is KNOWN (nominal drag model f_nom and
    the matched-uncertainty bound F are given inputs), nothing is
    estimated or adapted online, and the control switches on the error
    surface rather than updating gains.
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
    adaptive-control, control-allocation, state-space-analysis and
    observer-design; the structure is a state predictor plus projection
    adaptation plus low-pass filter, not a switching law. The new leaf
    runs no predictor, no projection, no filter and no adaptive signal:
    its matched uncertainty enters only through the bound F that sizes
    the switching gain.
  - h-infinity-control (this pack, wave 47) is the FREQUENCY-DOMAIN
    fence: its frontmatter description reads "Use when you must run the
    h-infinity mixed-sensitivity norm analysis of a feedback loop: given
    the plant transfer function, a candidate controller, the sensitivity
    weight and the control-effort weight, verify the closed loop is
    stable and compute the h-infinity norms of the weighted sensitivity
    functions by gamma iteration over the imaginary-axis frequency
    response, locating the worst-case peak magnitude of each channel.
    Produces the weighted-sensitivity norm, the weighted
    control-sensitivity norm, the achieved gamma of the mixed-sensitivity
    weighting as the larger of the two norms, and the bound verdict when
    both weighted norms stay below one so the s-over-ks sensitivity
    bounds hold at every frequency. Trigger: h infinity norm, gamma
    iteration, mixed sensitivity weighting, s ks weighted bounds,
    sensitivity weight, control weight, worst case peak gain, weighted
    loop analysis." That leaf is a SISO linear norm-analysis review with
    the controller given; the new leaf synthesizes a nonlinear
    time-domain switching command and performs no frequency sweep, no
    norm computation and no weight selection. The receipt's
    robust-synthesis GO 1 (h-infinity-synthesis, dgkf-two-riccati) is a
    separate planned leaf and owns no sliding identity.
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
    TUNED gains; the new leaf never tunes: lambda, k, phi and F are
    given design inputs (k = F + ETA only, no search), no margins are
    computed, and the control is the switched term u_sw = -k sat(s/phi)
    on the sliding surface, not a P-I-D output.
  - gain-scheduling (this pack) is the SCHEDULED-GAINS fence: its
    frontmatter description reads "Use when you must design and schedule
    controller gains against dynamic-pressure across nonlinear flight
    envelope, interpolate gain schedule breakpoint table across
    Mach-number operating points, and select the scheduling variable
    (dynamic-pressure, Mach number, angle of attack, or altitude).
    Choose nearest, linear, or spline interpolation, apply
    scheduling-variable rate limiting, and distinguish gain scheduling
    from gain updating. Verify stability between operating points and
    handle anti-windup interaction when scheduling autopilot and flight
    control gains across the envelope. Produces the interpolated gain at
    the current operating point and the rate-limited scheduling variable
    value. Trigger: gain scheduling, gain-scheduling, scheduling
    variable, dynamic pressure, Mach number, angle of attack, altitude,
    breakpoint table, schedule table, interpolation, rate limiting, gain
    updating, anti-windup, flight envelope." The sliding law is not a
    family of linear controllers scheduled over an envelope point: the
    surface coefficients and switching gain are fixed design constants
    and the discontinuity is a function of the error state, not of a
    scheduling variable.
  - deadbeat-control (this pack, wave 46) is the Z-DOMAIN fence: its
    frontmatter description claims "solve the deadbeat design equation
    that places every closed loop pole at the origin of the z plane,
    form the finite-settling-time controller difference equation from
    the plant polynomials." Its occurrence of 'relative degree' (lines
    48/56 of its SKILL.md, d = deg A - deg B) is pulse-transfer
    z-domain vocabulary, not the sliding-surface identity (receipt GO 3
    (a) note). The new leaf designs no discrete transfer function, no
    pole placement and no finite-settling sequence; its simulation is
    forward Euler in continuous time and its surface is on the error and
    its derivative.
  - Whole-tree greps at prep (probe receipt gate (a)) and re-verified at
    spec time (this file): `rg -i -l 'sliding[- ]mode|variable[- ]
    structure|reaching[- ]law|equivalent[- ]control|chattering' skills/
    -g 'SKILL.md'` -> 0 hits (exit 1), and `rg -ic 'sliding-mode|
    variable-structure|reaching-law|equivalent-control|chattering'`
    eval/hit1-corpus.yaml -> 0 hits (exit 1). GENUINE gnc-autonomy/
    control gap (probe receipt task-3, verified zero-owner, GO rank 2):
    no leaf owns the error-surface switching law of variable-structure
    control, and the receipt's adaptive fences (quoted above) explicitly
    cover only first-order MRAC/L1 structures, leaving the nonlinear
    variable-structure vein entirely absent from the tree.
- Standards id: arp4754a (ARP4754A, Guidelines for Development of Civil
  Aircraft and Systems, SAE; reference-only control-pack convention, the
  same id the pid-control-design, digital-control-design, observer-design,
  deadbeat-control, smith-predictor and h-infinity-control leaves carry;
  present in standards-map.yaml, grep 'id: arp4754a' at line 38,
  re-verified at spec time). Standards are reference-only, never
  reproduced verbatim. Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design and simulate a variable-structure sliding-mode control law that
drives a second-order canonical plant with bounded matched uncertainty
onto a sliding surface in the tracking error and holds it there, with the
boundary-layer saturation suppressing chattering. The plant is the
second-order canonical model x_ddot = f(x, x_dot) + u with unit control
effectiveness, f = f_nom + d, the nominal model f_nom(x, v) = -v (unit
mass with unit linear drag) known to the controller and d a constant
matched disturbance of magnitude |d| <= F with F a GIVEN bound, never
measured and never estimated. The reference xd is a given constant; the
tracking error is e = x - xd. The sliding surface is s = e_dot + lambda e
with the surface coefficient lambda > 0 given; on s = 0 the error
dynamics collapse to the first-order stable form e_dot = -lambda e. The
equivalent control is u_eq = -f_nom + xd_ddot - lambda e_dot, the control
that holds s_dot = 0 on the NOMINAL model (d = 0), which for the worked
model reads u_eq = (1 - lambda) v. The switching term is u_sw = -k
sat(s/phi), the constant-plus-proportional reaching-law realization:
outside the boundary layer |s| > phi it is the constant rate -k sign(s),
inside it is the proportional -k s/phi; phi = 0 reduces it to the ideal
sign switching used only as the chattering comparison. The full command
is u = u_eq + u_sw with the switching gain k = F + ETA sized strictly
above the uncertainty bound, so the sliding condition (1/2) d(s^2)/dt =
s s_dot <= -eta |s| holds on every point with |s| > phi (s_dot = d - k
sat(s/phi), s s_dot = s d - k |s| <= |s| (F - k) = -eta |s|) and the
surface reaches the boundary layer in finite time, t_reach <= (|s0| -
phi)/eta. Inside the layer the motion is the linear system s_dot = d -
(k/phi) s, stable with the layer time constant phi/k, and with the
constant disturbance it settles at the boundary-layer equilibrium s_ss =
phi d/k with the tracking error pinned at e_ss = phi d/(k lambda) and the
command at u = -d, where the saturated switching term continuously
balances the matched disturbance without sign flips. Produces the sliding
surface, equivalent-control, switched-term and command histories, the
finite-time reach of the boundary layer, the sliding-condition audit of
the reachability inequality over every sample outside the layer, the
boundary-layer command with the chattering-suppression check (control
jump count and maximum step-to-step command change versus the ideal-sign
comparison at the same gains), the tracking-error history with its
equilibrium offset, and the verdict numbers that gate a sliding-mode
control assessment. Does NOT do: model-reference adaptive control,
gradient or projection adaptation laws, unknown-coefficient estimation,
state predictors and low-pass-filtered adaptive signals
(gnc-autonomy/control/adaptive-control and l1-adaptive-control, which is
why the plant model f_nom and the bound F are known inputs here and
nothing adapts online); P-I-D gain design, Ziegler-Nichols or
pole-placement tuning, anti-windup, integrator clamping, margin checks
and linear gain scheduling over an envelope (pid-control-design,
gain-scheduling, which is why lambda and k are given design inputs,
never tuned, and k only ever takes the closed form F + ETA); h-infinity
norm analysis or robust synthesis (h-infinity-control owns the
weighted-sensitivity review; the dgkf-two-riccati synthesis is a planned
sibling leaf and neither computes a switching law); deadbeat or other
z-domain design (deadbeat-control, digital-control-design, which is why
the simulation is forward Euler with a fixed dt and no z-transform);
state estimation or observers (observer-design; x and v are measured
plant states, there is no estimator and no state estimate); cancellation
of plant nonlinearities by inversion, Lie derivatives, decoupling
matrices or zero-dynamics analysis (feedback-linearization territory,
the receipt's GO 3 sibling candidate of the same nonlinear vein, not
owned here: the switching law acts on the ERROR SURFACE and never
inverts f); disturbance estimation or identification of any kind (d is
never measured or reconstructed, only its bound F is used); recursive
Lyapunov backstepping or other constructive nonlinear designs; and any
claim of ideal sliding exactly on s = 0 or of chattering elimination
(the boundary layer suppresses chattering, motion is guaranteed in the
layer |s| <= phi after reach, and the layer is what trades the ideal
surface for the continuous command).

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG, closed form, forward
Euler discrete time. The module pins the worked-example configuration in
module constants: LAMBDA = 2.0 (1/s), ETA = 1.5 (1/s), WORKED_F = 0.5,
WORKED_K = 2.0 (WORKED_F + ETA), ROBUST_F = 0.9, ROBUST_K = 2.4
(ROBUST_F + ETA), WORKED_PHI = 0.05, SIGN_PHI = 0.0, WORKED_D = 0.5,
ROBUST_D = 0.9, REFERENCE_XD = 1.0, INIT_X = 0.0, INIT_V = 0.0, DT =
0.001 (s), SIM_TIME = 6.0 (s), JUMP_THRESHOLD = 0.5, and the audit
tolerance TOL = 1e-6. No imports beyond math.

Defining relations (pin these exactly; every function derives from them):
- Plant: second-order canonical with unit control gain, x_ddot = f(x,
  v) + u, f = f_nom + d, f_nom(x, v) = -v the nominal drag model, d the
  constant matched disturbance with |d| <= F. Velocity form: x_dot = v,
  v_dot = -v + d + u.
- Tracking error: e = x - xd with the constant reference xd, so e_dot =
  v and xd_ddot = 0.
- Sliding surface: s = e_dot + lambda e = v + lambda (x - xd). On s = 0
  the error dynamics are e_dot = -lambda e, time constant 1/lambda.
- Equivalent control (s_dot = 0 on the nominal model, d = 0): s_dot =
  x_ddot - xd_ddot + lambda e_dot = f_nom + u + d - xd_ddot + lambda
  e_dot, hence u_eq = -f_nom + xd_ddot - lambda e_dot; worked closed
  form u_eq = -(-v) + 0 - lambda v = (1 - lambda) v.
- Saturation: sat(s/phi) = s/phi for |s| <= phi (boundary layer), sign(s)
  outside; phi = 0 gives sign(s) (0 at s = 0), the ideal sign switching
  used ONLY as the chattering comparison.
- Switched term (constant-plus-proportional reaching law): u_sw = -k
  sat(s/phi), constant rate -k sign(s) outside the layer, proportional
  -k s/phi inside. Full command u = u_eq + u_sw.
- Switching gain: k > F required; the certified sliding margin is eta_cert
  = k - F, and the worked configuration uses k = F + ETA with ETA the
  named margin constant.
- Sliding condition: with s_dot = d + u + (lambda - 1) v = d - k
  sat(s/phi) (u_eq cancels the (lambda - 1) v term exactly), the
  condition (1/2) d(s^2)/dt = s s_dot <= -eta |s| holds on every point
  with |s| > phi because s s_dot = s d - k |s| <= |s| (F - k) = -eta_cert
  |s|.
- Finite-time reach: outside the layer |s| decreases at constant rate at
  least eta_cert, so the boundary layer is reached at t_reach <= (|s0| -
  phi)/eta_cert with |s0| = lambda |x0 - xd| (v0 = 0).
- Boundary-layer equilibrium (constant d): inside the layer s_dot = d -
  (k/phi) s = 0 at s_ss = phi d/k, and the surface pins the error at
  e_ss = s_ss/lambda = phi d/(k lambda); the steady command is u = -d,
  the saturated term balancing the disturbance (u_sw = -k s_ss/phi = -d,
  u_eq = -(lambda - 1) v -> 0 as v -> 0).
- Discrete simulation (forward Euler at the fixed dt, piecewise per
  sample): x[k+1] = x[k] + dt v[k]; v[k+1] = v[k] + dt (-v[k] + d +
  u[k]); the per-sample surface rate consistent with the update is
  s_dot[k] = d + u[k] + (lambda - 1) v[k].
- Initial conditions zero (x0 = 0, v0 = 0) with xd = 1: e(0) = -1,
  s(0) = -lambda = -2.0.

Functions (signatures, return shapes, ValueErrors; validated
identically by every public function):
- sliding_surface(err, err_dot, lam) -> float
  s = err_dot + lam * err. ValueError: lam <= 0 ("surface coefficient
  lambda must be positive, got ...").
- sat_value(s, phi) -> float
  sat(s/phi) in [-1, 1]: s/phi for |s| <= phi, sign(s) outside; phi = 0
  returns sign(s) with 0.0 at s = 0. ValueError: phi < 0
  ("boundary-layer thickness phi must be non-negative, got ...").
- equivalent_control(f_nominal, ref_ddot, err_dot, lam) -> float
  u_eq = -f_nominal + ref_ddot - lam * err_dot, the s_dot = 0 condition
  on the nominal model. ValueError: lam <= 0 ("surface coefficient
  lambda must be positive, got ...").
- switched_term(s, k, phi) -> float
  u_sw = -k * sat_value(s, phi). ValueError: phi < 0 ("boundary-layer
  thickness phi must be non-negative, got ..."), k <= 0 ("switching
  gain k must be positive, got ...").
- sliding_condition_margin(s, s_dot, eta) -> float
  -(s * s_dot) - eta * abs(s); non-negative exactly when s s_dot <= -eta
  |s|, the sliding condition (1/2) d(s^2)/dt <= -eta |s|.
- simulate_sliding_control(lam = LAMBDA, k = WORKED_K, phi = WORKED_PHI,
  bound_f = WORKED_F, disturbance_d = WORKED_D, x0 = INIT_X, v0 = INIT_V,
  xd = REFERENCE_XD, dt = DT, sim_time = SIM_TIME) -> dict
  Closed-loop forward-Euler simulation of the plant under the sliding
  control with the constant matched disturbance disturbance_d. Returns
  {"t" (sample times), "x", "v", "e", "s", "u_eq", "u_sw", "u",
  "s_dot" (series), "eta_cert" (k - bound_f), "reach_idx" and
  "reach_t" (first sample with |s| <= phi, None when never reached),
  "outside" (count of samples with |s| > phi), "worst_margin" (minimum
  sliding_condition_margin over those samples), "violations" (count of
  outside samples whose margin is below -TOL), "law_max_res" (max
  |s_dot[k] - (d - k sat(s[k]/phi))| over the run), "jumps" (count of
  samples after reach_t with |u[k] - u[k-1]| > JUMP_THRESHOLD),
  "max_du" (max step-to-step |u| change after reach_t), "sign_changes"
  (count of s sign changes after reach_t), "n"}. ValueErrors: lam <= 0,
  phi < 0, bound_f < 0 (messages as above plus "matched-uncertainty
  bound F must be non-negative, got ..."), k <= bound_f ("switching
  gain k must exceed the matched-uncertainty bound F, got k ... <= F
  ..."), abs(disturbance_d) > bound_f ("disturbance magnitude D must not
  exceed the matched-uncertainty bound F, got D ... > F ..."), dt <= 0
  ("sample time dt must be positive, got ..."), sim_time <= 0
  ("simulation time sim_time must be positive, got ...").

Identities to test (closed form, exact where noted; checkable without
the builder module):
- Surface and saturation closed forms: sliding_surface(-1.0, 0.0, 2.0)
  = -2.0 exactly (s0 = -lambda for the worked e(0) = -1); sat_value
  returns s/phi inside the layer and +/-1 outside; sat_value(s, 0.0)
  returns sign(s); the worked initial command is u(0) = u_eq(0) - k
  sat(s0/phi) = 0 + k = +2.0 because s0 = -2.0 saturates the layer.
- Equivalent-control and surface-rate law: at every sample u_eq[k] =
  (1 - lambda) v[k] (worked lambda = 2.0 gives u_eq = -v) and s_dot[k] =
  d - k sat(s[k]/phi): real anchor max residual |s_dot - (D - k
  sat(s/phi))| = 4.441e-16 over the 6001 samples of the worked run, the
  closed-form float witness that the equivalent control cancels the
  (lambda - 1) v term exactly and the switched term alone shapes s_dot.
- Sliding-condition inequality: on every sample with |s| > phi,
  (1/2) d(s^2)/dt = s s_dot <= -eta_cert |s|, i.e. the margin -(s s_dot)
  - eta_cert |s| is non-negative: real anchors 781 outside samples with
  worst margin 0.050000000 (worked, equality at the layer edge on the
  s < 0 side where the margin is |s|) and 591 outside samples with worst
  margin 0.095400000 (robust), 0 violations in both runs.
- Finite-time reachability: worked case real t_reach = 0.781000 s against
  the constant-rate closed form (|s0| - phi)/(D + k) = 0.780000000 and
  the certified upper bound (|s0| - phi)/eta_cert = 1.300000000 s;
  robust case real t_reach = 0.591000 s against 1.95/(D + k) = 0.590909
  s, both strictly inside the certified bound.
- Boundary-layer equilibrium and surface-pinned error dynamics: after
  reach the surface settles at s_ss = phi D/k (real s(6.0) =
  0.012500000 against 0.012500000 worked) and the error converges to
  e_ss = phi D/(k lambda) at rate lambda with no overshoot of e_ss: real
  worked e(6.0) = 0.006234758 against 0.006250000, real decay ratios
  (e(1.2) - e_ss)/(e(0.9) - e_ss) = 0.548498 and (e(1.5) - e_ss)/(e(1.2)
  - e_ss) = 0.548482 against exp(-lambda * 0.3) = 0.548812, max |s -
  s_ss| over t >= 2.0 s = 0.000000000, max |e - e_ss| over t >= 4.0 s =
  0.000835525.
- Boundary-layer stability and chattering suppression: with the
  saturation layer the command is continuous after reach: 0 control
  jumps above 0.5, max step-to-step |du| 0.100524520, 1 s sign change
  after reach (the single crossing into the layer), mean |u| over
  [4.0, 6.0] s = 0.500410; the SAME gains with phi = 0 (ideal sign)
  chatter: 3690 control jumps, max |du| 4.002601733, 3668 s sign
  changes, mean |u| 2.001024. Steady command identity: u(6.0) =
  -0.500030484 = -D - v(6.0), the switched term balancing the
  disturbance; max |u + D + v| over t >= 4.0 s = 7.675e-14 (worked) and
  6.380e-14 (robust).
- ValueErrors across the module and determinism: the ten guards
  enumerated in the Worked example raise ValueError with the real
  messages quoted there; identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; the module
  constants fixed as above.

## Worked example

Plant: second-order canonical x_ddot = f + u, f = f_nom + d, f_nom = -v,
nominal drag model known to the controller; constant matched disturbance
d = D at its bound (worked D = F = 0.5, robustness case D = F = 0.9),
|d| <= F, never measured. Design: sliding surface s = e_dot + lambda e
with lambda = 2.0 (1/s); equivalent control u_eq = (1 - lambda) v = -v;
switching gain k = F + ETA with ETA = 1.5, so worked k = 2.0 and robust
k = 2.4 and the certified margin eta_cert = k - F = 1.5 in both;
boundary-layer thickness phi = 0.05 (worked and robust), ideal sign
switching phi = 0.0 as the chattering comparison at the SAME gains.
Reference xd = 1.0 constant, initial state x(0) = 0, v(0) = 0, so e(0) =
-1.0 and s(0) = -2.0. Simulation: forward Euler at dt = 0.001 s over a
6.0 s horizon (6001 samples).

All values below are REAL outputs of the prep anchor anchor_sliding_mode.py
(pure stdlib, math only, no RNG, exit 0, internal asserts all pass), run
once at spec time under both interpreters with byte-identical output and
quoted as printed:

- Worked case D = F = 0.5, k = 2.0, phi = 0.05 (module output):
  - equilibrium targets: s_ss* = phi*D/k = 0.012500000 and e_ss* =
    phi*D/(k*lam) = 0.006250000.
  - finite-time reach: first |s| <= phi at t_reach = 0.781000 s (sample
    781), against the constant-rate closed form (|s0| - phi)/(D + k) =
    0.780000000 s and inside the certified upper bound (|s0| -
    phi)/eta_cert = 1.300000000 s.
  - surface-rate law identity: max |s_dot - (D - k*sat(s/phi))| =
    4.441e-16 over the 6001 samples.
  - sliding-condition audit: 781 samples with |s| > phi, worst margin
    0.050000000 (non-negative, so (1/2) d(s^2)/dt <= -eta |s| holds on
    every outside sample), 0 violations.
  - boundary-layer equilibrium: s(6.0) = 0.012500000 vs s_ss* 0.012500000,
    e(6.0) = 0.006234758 vs e_ss* 0.006250000, x(6.0) = 1.006234758,
    u(6.0) = -0.500030484 vs -D -0.500000000 (the switched term balances
    the disturbance, u = -D - v at the layer equilibrium).
  - post-transient windows: max |s - s_ss*| for t >= 2.0 s =
    0.000000000 (layer phi 0.05); max |e - e_ss*| for t >= 4.0 s =
    0.000835525; steady command identity max |u + D + v| for t >= 4.0 s
    = 7.675e-14.
  - chattering suppression: control jumps |du| > 0.5 after t_reach: 0;
    max |du| after t_reach 0.100524520; s sign changes after t_reach: 1.
  - sample points (module output): t = 0.5 s: x 0.229694534, v
    0.790610931, e -0.770305466, s -0.750000000 (still reaching, |s| >
    phi), u 1.209389069; t = 1.0 s: x 0.667144001, v 0.678204135, e
    -0.332855999, s 0.012492138 (inside the layer), u -1.177889642;
    t = 2.0 s: x 0.960448782, v 0.091602435, e -0.039551218, s
    0.012500000, u -0.591602435; t = 4.0 s: x 1.005414475, v
    0.001671051, e 0.005414475, s 0.012500000, u -0.501671051;
    t = 6.0 s: x 1.006234758, v 0.000030484, e 0.006234758, s
    0.012500000, u -0.500030484.
  - surface error-dynamics identity (module output): (e(1.2) -
    e_ss*)/(e(0.9) - e_ss*) = 0.548498 and (e(1.5) - e_ss*)/(e(1.2) -
    e_ss*) = 0.548482 against the theory exp(-lam*0.3) = 0.548812: once
    the surface pins the layer, the error approaches e_ss* at the rate
    lambda, no overshoot of the offset.
- Sign case phi = 0.0, SAME gains D = 0.5, k = 2.0 (module output):
  chattering contrast: first |s| = 0 crossing at t = 1.096000 s (sample
  1096), then 3690 control jumps |du| > 0.5 with max |du| 4.002601733,
  3668 s sign changes after t_reach, and mean |u| over [4.0, 6.0] s =
  2.001024 against 0.500410 for the worked saturation at the same k.
  Sample t = 5.0 s: u -2.001473930, s 0.002000000, e 0.000263035 (sign)
  versus u -0.500225700, s 0.012500000, e 0.006137150 (worked). The
  ideal sign command alternates between approximately +k and -k at the
  sample rate while the saturation layer holds the continuous command
  near -D.
- Robustness case D = F = 0.9, k = 2.4, phi = 0.05 (module output):
  eta_cert = 1.500000000; equilibrium targets s_ss* = phi*D/k =
  0.018750000 and e_ss* = phi*D/(k*lam) = 0.009375000; t_reach =
  0.591000 s (sample 591) inside the certified bound 1.300000000 s;
  sliding-condition audit: 591 samples with |s| > phi, worst margin
  0.095400000, 0 violations; s(6.0) = 0.018750000, e(6.0) = 0.009362949,
  x(6.0) = 1.009362949, u(6.0) = -0.900024101; max |s - s_ss*| for
  t >= 2.0 s = 0.000000000; max |e - e_ss*| for t >= 4.0 s =
  0.000660585; max |u + D + v| for t >= 4.0 s = 6.380e-14; control jumps
  after t_reach: 0, max |du| 0.158705197. Samples: t = 0.5 s: x
  0.303196785, v 1.043606429, e -0.696803215, s -0.350000000, u
  1.356393571; t = 1.0 s: x 0.741270032, v 0.536209936, e -0.258729968,
  s 0.018750000, u -1.436209930; t = 2.0 s: x 0.973163531, v
  0.072422939, e -0.026836469, s 0.018750000, u -0.972422939;
  t = 4.0 s: x 1.008714415, v 0.001321170, e 0.008714415, s 0.018750000,
  u -0.901321170; t = 6.0 s: x 1.009362949, v 0.000024101, e
  0.009362949, s 0.018750000, u -0.900024101. The larger bound F = 0.9
  with the same eta gives a proportionally larger layer offset and a
  faster reach, and the sliding condition still holds with zero
  violations at the same certified margin.
- ValueErrors with real messages (module output, quoted as printed):
  sliding_surface(0.1, 0.0, 0.0) raises "surface coefficient lambda must
  be positive, got 0.0"; sat_value(0.1, -0.05) raises "boundary-layer
  thickness phi must be non-negative, got -0.05"; equivalent_control(0.1,
  0.0, 0.1, 0.0) raises "surface coefficient lambda must be positive,
  got 0.0"; switched_term(0.1, 2.0, -0.05) raises "boundary-layer
  thickness phi must be non-negative, got -0.05"; switched_term(0.1, 0.0,
  0.05) raises "switching gain k must be positive, got 0.0";
  simulate_sliding_control(bound_f = -0.1) raises "matched-uncertainty
  bound F must be non-negative, got -0.1";
  simulate_sliding_control(k = 0.5, bound_f = 0.5) raises "switching
  gain k must exceed the matched-uncertainty bound F, got k 0.5 <= F
  0.5"; simulate_sliding_control(disturbance_d = 0.6) raises
  "disturbance magnitude D must not exceed the matched-uncertainty bound
  F, got D 0.6 > F 0.5"; simulate_sliding_control(dt = 0.0) raises
  "sample time dt must be positive, got 0.0";
  simulate_sliding_control(sim_time = 0.0) raises "simulation time
  sim_time must be positive, got 0.0".

Run your module and take the real outputs as assert targets; the anchors
above are real prep outputs of anchor_sliding_mode.py (stdlib math,
closed form, exit 0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Closed-form surface and saturation: sliding_surface(-1.0, 0.0, 2.0)
   equals -2.0 within 1e-12; sat_value(0.0125, 0.05) equals 0.25 within
   1e-12 (the worked equilibrium point sits one quarter into the layer);
   sat_value(0.2, 0.05) = 1.0 and sat_value(-0.2, 0.05) = -1.0 exactly
   (saturation); sat_value(0.1, 0.0) = 1.0, sat_value(-0.1, 0.0) = -1.0
   and sat_value(0.0, 0.0) = 0.0 (ideal sign).
2. Surface-rate law identity: over the worked run, max |s_dot - (D - k
   sat(s/phi))| below 1e-9 (real anchor 4.441e-16); equivalently u_eq
   cancels the (lambda - 1) v term to float noise at every sample.
3. Sliding-condition inequality: for every sample with |s| > phi the
   margin -(s s_dot) - eta_cert |s| is above -1e-6 (real worked worst
   margin 0.050000000 over 781 samples, robust 0.095400000 over 591
   samples, 0 violations in both runs; assert count of violations == 0).
4. Finite-time reach: worked reach_t = 0.781000 within 0.005 s of the
   closed form (|s0| - phi)/(D + k) = 0.780000 and strictly below the
   certified bound (|s0| - phi)/eta_cert = 1.300000; robust reach_t =
   0.591000 within 0.005 s of 1.95/(D + k) = 0.590909 and below the same
   1.300000 bound.
5. Boundary-layer equilibrium: worked s(6.0) = 0.012500000 within 1e-6
   of phi*D/k; e(6.0) = 0.006234758 within 1e-4 of phi*D/(k*lam) =
   0.006250000 (real deviation 1.524e-05); x(6.0) = 1.006234758 within
   1e-4 of 1 + e_ss; max |s - s_ss| over t >= 2.0 s below 1e-6 (real
   0.000000000); max |e - e_ss| over t >= 4.0 s below 1e-3 (real
   0.000835525).
6. Surface error-dynamics identity: (e(1.2) - e_ss)/(e(0.9) - e_ss) =
   0.548498 and (e(1.5) - e_ss)/(e(1.2) - e_ss) = 0.548482, each within
   0.01 of exp(-lam*0.3) = 0.548812; e never overshoots e_ss after the
   layer pins (max e after t = 2.0 s equals e(6.0) within 1e-3).
7. Chattering suppression: worked saturation case control jumps (|du| >
   0.5 after t_reach) == 0 with max |du| 0.100524520 below 0.5 and s
   sign changes == 1; sign case at the SAME k and D (phi = 0.0): jumps
   3690 (assert > 1000), max |du| 4.002601733 (assert > 2.0), s sign
   changes 3668; mean |u| over [4.0, 6.0] s is 0.500410 (worked) within
   1e-3 of 0.5 and 2.001024 (sign) within 1e-2 of 2.0.
8. Steady command identity: max |u + D + v| over t >= 4.0 s below 1e-9
   (real worked 7.675e-14); u(6.0) = -0.500030484 equals -D - v(6.0)
   within 1e-9; the switched term alone balances the matched disturbance
   at the layer equilibrium.
9. Robust case D = F = 0.9, k = 2.4: e(6.0) = 0.009362949 within 1e-4
   of e_ss = 0.009375000; s(6.0) = 0.018750000 within 1e-6 of phi*D/k;
   u(6.0) = -0.900024101 equals -D - v(6.0) within 1e-9; max |e - e_ss|
   over t >= 4.0 s within 1e-3 (real 0.000660585); violations == 0;
   control jumps == 0; max |du| 0.158705197 below 0.5.
10. Worked sample points within 1e-5: x(0.5) = 0.229694534, x(1.0) =
    0.667144001, x(2.0) = 0.960448782, x(4.0) = 1.005414475, x(6.0) =
    1.006234758; s(0.5) = -0.750000000 (reaching phase, outside the
    layer), s(1.0) = 0.012492138 (inside the layer), s(2.0) = s(4.0) =
    s(6.0) = 0.012500000 within 1e-6.
11. All ValueErrors enumerated in the Worked example raise from the named
    public function with the real messages quoted there: lambda guards
    (sliding_surface, equivalent_control), phi guards (sat_value,
    switched_term, simulate_sliding_control), k guards (switched_term,
    simulate_sliding_control), bound and disturbance guards
    (simulate_sliding_control), dt and sim_time guards
    (simulate_sliding_control).
12. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math; module
    constants fixed as LAMBDA 2.0, ETA 1.5, WORKED_F 0.5, WORKED_K 2.0,
    ROBUST_F 0.9, ROBUST_K 2.4, WORKED_PHI 0.05, SIGN_PHI 0.0, WORKED_D
    0.5, ROBUST_D 0.9, REFERENCE_XD 1.0, INIT_X 0.0, INIT_V 0.0, DT
    0.001, SIM_TIME 6.0, JUMP_THRESHOLD 0.5. No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.
13. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave48-sliding-mode-control.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "design the sliding-mode-control law for the second-order plant with
  matched-uncertainty: choose the sliding-surface from the error and its
  derivative, compute the equivalent-control from the nominal model, and
  add the switching-term inside the boundary-layer to enforce the
  reachability condition"
  intent: "gnc-autonomy/control; sliding-mode-control: the
  sliding-surface chosen from the tracking error and its derivative, the
  equivalent-control computed from the nominal model, and the
  switching-term added inside the boundary-layer to enforce the
  reachability condition"
  expected_skill: "gnc-autonomy/control/sliding-mode-control"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply sliding-mode-control with the constant-plus-proportional-
  reaching-law: evaluate the equivalent-control, size the
  switching-gain from the matched-uncertainty bound and report the
  boundary-layer command with the chattering-suppression check"
  intent: "gnc-autonomy/control; sliding-mode-control with the
  constant-plus-proportional-reaching-law: the equivalent-control
  evaluated from the nominal model, the switching-gain sized from the
  matched-uncertainty bound, and the boundary-layer command reported
  with the chattering-suppression check"
  expected_skill: "gnc-autonomy/control/sliding-mode-control"
Task ids: w48-sliding-mode-control-1 and -2. Prep grep (run at spec time
by the probe and re-verified for this file): each of the tokens
sliding-mode, variable-structure, reaching-law, equivalent-control and
chattering returns ZERO matches in eval/hit1-corpus.yaml (grep exit 1)
and ZERO skills/ hits, so the queries are collision-free; the sibling
corpus tasks route on adaptation-language wording (adaptive-control,
l1-adaptive-control), z-domain deadbeat language (deadbeat-control),
tuning and margin language (pid-control-design), weighted-norm language
(h-infinity-control) and delay-compensation language (smith-predictor),
none of which carries a sliding-surface switching identity. Add one fence
line to the adaptive-control and l1-adaptive-control related-leaves lists
and one router row to skills/gnc-autonomy/SKILL.md at build time pointing
variable-structure control to the new leaf (the deadbeat-control and
smith-predictor precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design a sliding-mode-control
law for a second-order plant with matched uncertainty:" and include the
outputs in the Claim order (the sliding surface chosen from the error and
its derivative, the equivalent control computed from the nominal model,
the switching term sized above the uncertainty bound inside the boundary
layer, the reachability condition and its audit, the boundary-layer
command with the chattering-suppression check, and the tracking-error
history), then close with the Trigger list. The plant model f_nom and the
uncertainty bound F are given inputs, never identified or estimated; the
matched disturbance is never measured, only bounded; k always equals F +
ETA, never tuned; and never reproduce ARP4754A text (reference-only).
First tag: sliding-mode-control. Metadata tags EXACTLY as the probe
receipt gate (f) lists them, nothing else: sliding-mode-control,
sliding-surface-design, equivalent-control,
constant-plus-proportional-reaching-law, switching-term,
chattering-suppression, matched-uncertainty, variable-structure-control,
boundary-layer-command. 50-150 words, <=1000 chars, no em dash, action
verb present, never the banned sweep term of the builder kit. Recommended
wording (113 words, 973 chars, verified at spec time):

"Use when you must design a sliding-mode-control law for a second-order
plant with matched uncertainty: choose the sliding surface from the
tracking error and its derivative, compute the equivalent control that
holds the surface on the nominal model, add the switching term sized
above the uncertainty bound inside the boundary layer to enforce the
reachability condition, and suppress chattering with the saturation
thickness. Produces the surface and equivalent-control histories, the
sliding-condition audit of the reachability inequality at every sample,
the finite-time reach of the boundary layer, the boundary-layer command
with the chattering-suppression check, and the tracking-error history
that gate a sliding-mode control assessment. Trigger:
sliding-mode-control, sliding-surface-design, equivalent-control,
constant-plus-proportional-reaching-law, switching-term,
chattering-suppression, matched-uncertainty, variable-structure-control,
boundary-layer-command."

FORBIDDEN TOKENS (belong to siblings): mrac, model-reference-adaptive,
adaptation-law, adaptive-gain, online-gain-update, unknown-coefficient,
ideal-cancellation, state-predictor, projection-based-adaptation,
low-pass-filtered-adaptation, sigma-hat, guaranteed-transient-response
(adaptive-control, l1-adaptive-control); ziegler-nichols, ultimate-gain,
ultimate-period, controller-gain-tuning, pole-placement, anti-windup,
integrator-clamp, gain-margin, phase-margin and any PID gain design or
loop-margin claim (pid-control-design; lambda and k are given design
inputs, k = F + ETA only, no margins computed); gain-scheduling,
scheduling-variable, breakpoint-table, gain-updating (gain-scheduling);
deadbeat-control, finite-settling-time, pole-placement-at-origin,
minimum-settling-time, z-domain-deadbeat and any z-domain or
pulse-transfer design claim (deadbeat-control); z-transform,
tustin-bilinear, discrete-pid-coefficients, unit-circle-stability,
sample-rate-selection (digital-control-design); h-infinity,
mixed-sensitivity, gamma-iteration, worst-case-peak-gain,
weighted-sensitivity, s-over-ks (h-infinity-control); luenberger,
estimator-gain, ackermann, observability, state-estimation
(observer-design); linearizing-control, decoupling-matrix, lie-derivative,
zero-dynamics, dynamic-inversion and any plant-inversion or
nonlinear-cancellation claim (feedback-linearization territory, the
receipt's GO 3 sibling candidate of the same nonlinear vein, not owned
here); smith-predictor, dead-time-compensation, transport-delay
(smith-predictor); system-identification, disturbance-estimation and any
claim that the leaf identifies f_nom, F, d or the plant from data (the
nominal model, the bound and the disturbance are inputs; d is never
measured or reconstructed); backstepping and any recursive Lyapunov
design. Never the bare single words sliding, surface, control, switch,
layer, plant, gain, error, command or disturbance as standalone metadata
tags.
