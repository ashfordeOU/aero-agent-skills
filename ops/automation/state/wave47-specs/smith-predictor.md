# Wave-47 leaf spec: smith-predictor (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/smith-predictor/
- Pack: control (present siblings adaptive-control, control-allocation,
  deadbeat-control, digital-control-design, frequency-response-design,
  gain-scheduling, l1-adaptive-control, lead-lag-compensation,
  observer-design, pid-control-design, python-control-design,
  root-locus-design, state-space-analysis; no sibling in the pack or
  anywhere else in the tree performs a dead-time compensation: the
  zero-owner greps `smith[- ]predictor|dead[- ]time|transport[- ]delay|
  delay[- ]compensat` over the whole skills/ tree return exactly ONE hit,
  flight-mechanics/handling-qualities/pilot-induced-oscillation, whose
  only occurrence is the MIL-STD-1797A tau_e context quoted below, and
  the eval/hit1-corpus.yaml scan for the same tokens returns 0 matching
  tasks, all re-verified at spec time).
- Provenance: wave-47 recon receipt task-3 GO rank 3, lines 178-241 (GO
  3 of 3 strong): "design the smith-predictor for the loop with dead
  time: model the delay-free plant, compute the delayed model output,
  and form the compensated feedback by subtracting the delayed
  prediction from the measured plant output before the primary
  controller." Published deterministic anchor, receipt gate (d)
  (summary-only): the Smith predictor with the primary controller
  designed for the delay-free plant model, the predictor subtracting the
  delayed model output from the measured output so the primary loop
  closes on a delay-free compensated error, with the 1 - exp(-sT)
  dead-time block and explicit predictor output computable by
  convolution over the delay line. Source: O. J. M. Smith, "Closer
  Control of Loops with Dead Time", Chemical Engineering Progress
  53(5):217-219, 1957. Deterministic offline closed-form compensation
  given the delay-free model, the dead time and the primary controller.
  Corpus tokens of the leaf (receipt gate (f), all hyphenated
  compounds): smith-predictor, dead-time-compensation,
  time-delay-compensation, delay-free-model-prediction,
  predictor-feedback-signal.
- Claim fences (quoted from the sibling SKILL.md files at prep,
  re-verified at spec time; the nearest owners fence out gain design,
  sampled-data design, estimator design and deadbeat synthesis, none of
  which is a dead-time compensation, which is the exact gap this leaf
  closes):
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
    phase margin of the loop." Its model, workflow and tags (anti-windup,
    integrator-clamp, ziegler-nichols, pole-placement, gain-margin,
    phase-margin) derive controller gains and loop verdicts; there is no
    dead time anywhere in its equations, no delay line and no predictor
    structure. The new leaf's kp and ki are GIVEN controller inputs,
    never tuned, placed or margin-checked here; those surfaces stay with
    the sibling.
  - digital-control-design (this pack) is the SAMPLED-DATA fence: its
    frontmatter description reads "Use when you must design a
    sampled-data digital control loop in the z-domain: discretize a
    continuous plant with a zero-order hold, emulate a continuous
    compensator with the Tustin bilinear transform with frequency
    prewarping, compute discrete PID coefficients in the position and
    velocity forms, check the sampled poles against the unit circle for
    stability, and select the sample rate from the closed-loop
    bandwidth." It owns z-domain discretization, emulation, discrete-PID
    coefficient forms and sample-rate selection; the new leaf simulates
    at the fixed module constant SAMPLE_DT with the exact sampled
    first-order recurrence (piecewise-constant input) and never designs
    in the z-domain, never emulates a compensator, never checks
    unit-circle stability and never selects a sample rate (dt is a
    simulation constant, not a design output).
  - deadbeat-control (this pack, wave 46) is the FINITE-SETTLING fence:
    its frontmatter description claims "solve the deadbeat design
    equation that places every closed loop pole at the origin of the z
    plane, form the finite-settling-time controller difference equation
    from the plant polynomials". Deadbeat synthesis cancels the plant
    modes and settles in a finite sample count on a delay-free discrete
    plant; no dead-time structure and no predictor block exist in its
    model. The new leaf never places poles and never claims finite-
    settling or minimum-settling behavior.
  - observer-design (this pack) is the ESTIMATOR fence: its frontmatter
    description claims "compute the estimator gain matrix by pole
    placement with the Ackermann formula so the observer error dynamics
    eigenvalues sit at the desired locations, verify the error dynamics
    are Hurwitz stable ... confirm the separation principle". Its model
    is a full-order state observer for unmeasured states; it scored as
    the corpus sim runner-up purely on the shared 'prediction' token of
    its estimator vocabulary, and it is not a compensation owner. The
    new leaf's internal model is a delay-free copy of the plant
    transfer function driven by the controller output, not a state
    observer: no observability check, no estimator gain, no error
    dynamics and no state estimate anywhere.
  - pilot-induced-oscillation (flight-mechanics/handling-qualities) is
    the TRANSPORT-DELAY-WORD fence, the single whole-tree skills/ hit
    for the dead-time grep tokens: its pitfalls (lines 135-138, verbatim)
    read "Confusing equivalent time delay with measured transport delay:
    tau_e is derived from the phase lag at one frequency and lumps all
    lag sources; the measured transport delay is one contributor, not
    the whole result." That is MIL-STD-1797A handling-qualities
    vocabulary (the pilot-in-the-loop tau_e equivalent time delay), not
    a control-loop dead-time compensator and not an ownership claim.
  - Whole-tree greps at prep (probe receipt gate (a)) and re-verified at
    spec time (this file): `rg -i -l 'smith[- ]predictor|dead[- ]time|
    transport[- ]delay|delay[- ]compensat' skills/ -g 'SKILL.md'` ->
    exactly the pilot-induced-oscillation hit above (the only other
    'Smith' in the tree is the Gordon-Salmond-Smith particle-filter
    ancestry citation in estimation-filtering/particle-filter, also not
    an owner), and `rg -ic 'smith|dead[- ]time|transport[- ]delay'`
    eval/hit1-corpus.yaml -> 0 hits. GENUINE gnc-autonomy/control gap
    (probe receipt task-3, verified zero-owner, GO rank 3): no leaf owns
    the delay-free-model predictor feedback structure that the tuning
    and sampled-data siblings cannot express.
- Standards id: arp4754a (ARP4754A, Guidelines for Development of Civil
  Aircraft and Systems, SAE; reference-only control-pack convention, the
  same id the pid-control-design, digital-control-design, observer-design
  and deadbeat-control leaves carry; present in standards-map.yaml, grep
  'id: arp4754a' at line 38, re-verified at spec time). Standards are
  reference-only, never reproduced verbatim. Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Compensate the dead time of a single feedback loop on a
first-order-plus-dead-time plant with the Smith predictor structure, so
the primary controller closes on a delay-free compensated error. The
plant is the FOPDT model P(s) = K exp(-theta s) / (tau s + 1) with gain
K, time constant tau and dead time theta, all given inputs; the primary
controller is a PI controller with the kp and ki gains also given
inputs, never tuned or placed by this leaf. The predictor runs an
internal delay-free model P0(s) = K / (tau s + 1) (the plant with its
dead time removed) on the controller output, holds the model output in a
pure delay line of the dead time, and forms the predictor feedback
signal by subtracting the delayed model output from the measured plant
output. The compensated error of the primary loop is therefore
e_comp = r - y_measured - (y_model - y_model_delayed): the measured
plant output, which the dead time has delayed, is corrected by the
difference between the current and the delayed model output, and the
primary loop closes on the delay-free error. Algebra of the loop with
the perfect-model assumption (the internal model equals the plant minus
its dead time) removes the dead time from the characteristic equation:
the setpoint closed loop becomes C(s) P0(s) exp(-theta s) / (1 + C(s)
P0(s)), the delay-free design denominator 1 + C P0, so the
predictor-compensated loop reproduces the delay-free closed-loop
response shifted by the dead time, while the conventional loop without
the predictor keeps the dead time in its characteristic equation 1 + C
P0 exp(-theta s) and degrades as theta grows. Produces the compensated
error signal of the primary loop each sample, the closed-loop step
response of the predictor-compensated loop and of the same loop without
compensation at the same given gains, and the step-response metrics of
both: overshoot percentage, peak time, settling time to the 2 percent
settling band (+-2 percent of the reference) and final deviation. The
delay-free companion loop (theta = 0, no predictor) is produced as the
reference response the predictor loop must reproduce after the dead
time. Does NOT do: PID gain design, Ziegler-Nichols or pole-placement
tuning, anti-windup, integrator clamping and gain/phase margin checks
(gnc-autonomy/control/pid-control-design, which is why kp and ki are
inputs here); z-domain discretization of plants, Tustin/bilinear
emulation, frequency prewarping, discrete-PID coefficient forms,
unit-circle stability and sample-rate selection
(gnc-autonomy/control/digital-control-design, which is why the sample
time dt is a fixed simulation constant); Luenberger/estimator state
observation, observability, Ackermann gain placement, error dynamics and
the separation principle (gnc-autonomy/control/observer-design);
deadbeat synthesis with closed-loop poles at the origin and
finite-settling claims (gnc-autonomy/control/deadbeat-control);
lead-lag, root-locus, frequency-response or loop-shaping compensator
synthesis (lead-lag-compensation, root-locus-design,
frequency-response-design); adaptive or model-reference control
(adaptive-control, l1-adaptive-control); process identification of any
kind (K, tau and theta are given plant-model inputs, never identified
from data); model-mismatch or robustness analysis (the perfect-model
assumption is the model; a mismatch between the internal model and the
plant is out of scope); and improved disturbance rejection (the
delay-free characteristic equation governs the setpoint path; the leaf
makes no disturbance-path claim and its worked comparison is a setpoint
step).

## Model (implement exactly)

Pure stdlib (math only), deterministic, no RNG, closed form. The module
pins the worked-example configuration in module constants: PLANT_GAIN_K
= 1.0, PLANT_TAU = 1.0 (s), WORKED_THETA = 2.0 (s), ROBUST_THETA = 5.0
(s), CONTROLLER_KP = 0.5, CONTROLLER_KI = 0.5 (1/s), SAMPLE_DT = 0.01
(s), SIM_TIME = 60.0 (s), REFERENCE = 1.0, SETTLE_BAND = 0.02,
STEPS_EPS = 1e-6, CL_POLE_RATE = 0.5 (1/s) and CL_TAU = 2.0 (s). No
imports beyond math.

Defining relations (pin these exactly; every function derives from
them):
- Plant and model: P(s) = P0(s) exp(-theta s) with P0(s) = K / (tau s +
  1); the internal delay-free model is P0(s), driven by the undelayed
  controller output.
- Primary controller: C(s) = kp + ki / s, kp and ki given inputs.
- Predictor transfer (the 1 - exp(-s theta) dead-time block of the
  receipt's anchor): the predictor output is the current model output
  minus the model output delayed by theta, p(s) = P0(s) (1 - exp(-theta
  s)) U(s).
- Compensated error: E_comp = R - Y - P0 (1 - exp(-theta s)) U.
- Setpoint closed-loop identities (derived by substituting U = C
  E_comp and Y = P0 exp(-theta s) U and eliminating U):
  - conventional loop, no predictor: Y/R = C P0 exp(-theta s) / (1 + C
    P0 exp(-theta s)); the dead time sits in the characteristic
    equation 1 + C P0 exp(-theta s).
  - predictor loop, perfect model: Y/R = C P0 exp(-theta s) / (1 + C
    P0); the dead time is removed from the denominator and survives
    only as the output shift exp(-theta s) in the numerator. The
    characteristic equation 1 + C P0 is the delay-free design
    denominator, so the predictor loop response is the delay-free
    closed-loop response re-emitted theta later.
  - Worked-case cancellation: with the worked constants K = 1.0, tau =
    1.0, kp = 0.5, ki = 0.5 the product C(s) P0(s) = (0.5 + 0.5/s) /
    (s + 1) = 0.5/s exactly (the controller zero cancels the plant
    pole at s = -1), so the delay-free closed loop is the first-order
    CL = 0.5 / (s + 0.5) = 1 / (2 s + 1) with pole at s = -CL_POLE_RATE
    = -0.5, time constant CL_TAU = 2.0 s, step response g(t) = 1 -
    exp(-0.5 t), and 2 percent settling time t_settle = theta + 2 ln(50)
    = theta + 7.824046 s for the predictor loop.
- Discrete simulation (exact sampled first-order recurrence,
  piecewise-constant controller output, pure integer delay line):
  - D = delay_steps(theta, dt), the integer delay line length; the
    worked theta = 2.0 s gives D = 200 at dt = 0.01 s and the
    robustness theta = 5.0 s gives D = 500.
  - a = exp(-dt / tau), b = K (1 - a); with K = 1.0 the identity a + b
    = 1.0 holds, and the DC gain identity b / (1 - a) = K holds.
  - Plant: y[k + 1] = a y[k] + b u[k - D] with u[j] = 0 for j < 0 (the
    controller output reaches the plant D samples late).
  - Internal model: ym[k + 1] = a ym[k] + b u[k] (no delay).
  - Loop errors: conventional e[k] = r - y[k]; predictor e_comp[k] = r
    - y[k] - ym[k] + ym[k - D] with ym[j] = 0 for j < 0.
  - PI controller: integral I[k + 1] = I[k] + e[k] dt and u[k] = kp
    e[k] + ki I[k + 1], where e is the loop error the configuration
    uses (e_comp under the predictor, e otherwise). kp and ki are
    given, never derived.
  - Initial conditions zero; unit step reference r = REFERENCE applied
    from sample 0.
- Perfect-model assumption: the internal model uses the plant
  parameters K and tau exactly and the true dead time theta; model
  mismatch, parameter error and time-varying delay are out of scope.
- Step metrics on a response series y sampled at t: overshoot_pct =
  max(0, (max(y) - r) / r) * 100; settling_time is the first sample
  time from which |y - r| <= SETTLE_BAND * r holds to the end of the
  run (equivalently (k_viol + 1) * dt where k_viol is the LAST index
  with |y - r| > band * r, and None when k_viol is the final index, so
  a diverging oscillation whose final sample is out of band reports
  None); peak_time is the first sample time of the maximum; final
  deviation is |y[-1] - r|.

Functions (signatures, return shapes, ValueErrors; validated
identically by every public function):
- first_order_lag_recurrence(gain, tau, dt) -> (a, b)
  Returns the exact sampled recurrence coefficients (a, b) of the
  first-order lag gain / (tau s + 1) at sample time dt. ValueError:
  gain <= 0 ("plant gain K must be positive, got ..."), tau <= 0
  ("plant time constant tau must be positive, got ..."), dt <= 0
  ("sample time dt must be positive, got ...").
- delay_steps(dead_time, dt) -> int
  Returns D = round(dead_time / dt), the integer pure-delay line
  length. ValueError: dead_time < 0 ("dead time theta must be
  non-negative, got ..."), dt <= 0 ("sample time dt must be positive,
  got ..."), or dead_time / dt not within STEPS_EPS = 1e-6 of an
  integer ("dead time theta must be an integer multiple of dt, got
  theta ... at dt ..."). The worked examples are exact multiples:
  theta 2.0 at dt 0.01 gives D = 200 and theta 5.0 gives D = 500.
- pi_output(error, integral, dt, kp, ki) -> (u, integral_next)
  One PI step with forward integral accumulation: integral_next =
  integral + error * dt and u = kp * error + ki * integral_next.
  ValueError: kp <= 0 ("proportional gain kp must be positive, got
  ..."), ki < 0 ("integral gain ki must be non-negative, got ..."),
  dt <= 0 ("sample time dt must be positive, got ...").
- step_metrics(t, y, reference = REFERENCE, band = SETTLE_BAND) -> dict
  Returns {"overshoot_pct", "peak_time", "settling_time",
  "final_deviation"} with the definitions above; settling_time is None
  exactly when the series never holds the band to the end of the run.
  ValueError on an empty response series ("response series is empty").
- simulate_closed_loop(gain = PLANT_GAIN_K, tau = PLANT_TAU,
  dead_time = WORKED_THETA, kp = CONTROLLER_KP, ki = CONTROLLER_KI,
  dt = SAMPLE_DT, sim_time = SIM_TIME, predictor = True,
  reference = REFERENCE) -> dict
  Discrete closed-loop step simulation of the FOPDT plant under the
  PI controller, with the predictor structure when predictor is True
  and the conventional loop when False; dead_time = 0.0 with
  predictor False is the delay-free companion loop. Returns
  {"t" (sample times), "y" (measured plant output series),
  "controller_error" (the error series the PI acted on, e_comp under
  the predictor), "metrics" (step_metrics dict), "d_steps"}. ValueErrors
  of the component functions and sim_time <= 0 ("simulation time
  sim_time must be positive, got ...").
- delay_shift_max_error(y_predictor, y_delay_free, d_steps) -> float
  The predictor identity check: max over k in [d_steps, len(y)) of
  abs(y_predictor[k] - y_delay_free[k - d_steps]). With a perfect
  model the predictor loop is algebraically the delay-free loop whose
  output is re-emitted D samples later, so this maximum is float-level
  noise. ValueError on length mismatch ("response series lengths
  differ") and d_steps outside the window ("d_steps outside the
  alignment window").

Identities to test (closed form, exact where noted; checkable without
the builder module):
- DC-gain / coefficient sum: first_order_lag_recurrence(1.0, 1.0,
  0.01) returns a + b = 1.0 exactly (real anchor a = 0.990049834,
  b = 0.009950166, a + b = 1.000000000000000) and b / (1 - a) = K =
  1.0.
- Delay-free design collapse: at the worked constants the delay-free
  closed loop is exactly CL = 0.5 / (s + 0.5) (pole-zero cancellation
  C P0 = 0.5/s), so the discrete delay-free companion simulation
  tracks the continuous closed form g(t) = 1 - exp(-0.5 t): real
  anchor max abs error 0.001655 over the 60 s horizon (the forward
  integral discretization residual), delay-free overshoot 0.000 and
  delay-free settling 7.83 s against the continuous 2 ln(50) = 7.824 s.
- Predictor delay-shift identity: with the perfect model the predictor
  loop output equals the delay-free companion output shifted by D
  samples, y_sp[k] = y_df[k - D] for every k >= D: real anchors max
  |y_sp[k] - y_df[k - 200]| = 2.220e-16 at theta = 2.0 and max
  |y_sp[k] - y_df[k - 500]| = 0.000e+00 at theta = 5.0. This is the
  discrete witness that the dead time left the characteristic
  equation.
- Settling-time identity: the predictor loop settles at theta + 2
  ln(50): real anchors 9.83 s at theta = 2.0 (theory 2.0 + 7.824046 =
  9.824046, next grid sample) and 12.83 s at theta = 5.0 (theory
  12.824046), with overshoot 0.000 in both cases; the predictor
  response is the monotone first-order g(t - theta).
- Conventional-loop degradation at the same gains: at theta = 2.0 the
  no-predictor loop overshoots 50.212 percent (peak 1.502 at 6.00 s)
  and settles at 25.82 s, versus 0.000 percent and 9.83 s with the
  predictor; at theta = 5.0 the no-predictor loop diverges (settling
  None, overshoot 2182.315, final deviation 11.909619 at 60 s with the
  oscillation still growing), versus 0.000 percent and 12.83 s with
  the predictor. The contrast at the SAME given gains isolates the
  predictor structure; no gain was changed between the two loops.
- Steady state: the integral action drives both theta = 2.0 loops to
  the reference: final deviation 0.000000 (predictor) and 0.000022
  (no predictor) after 60 s.
- ValueErrors across the module: the eight guards enumerated in the
  Worked example raise ValueError with the messages quoted there.
- Determinism: identical outputs run to run and under both
  interpreters; no randomness; no imports beyond math; the module
  constants fixed as above.

## Worked example

Plant: FOPDT K = 1.0, tau = 1.0 s (P0 = 1 / (s + 1)), worked dead time
theta = 2.0 s, robustness case theta = 5.0 s. Primary controller: PI
with the GIVEN gains kp = 0.5, ki = 0.5 (no tuning; at these gains the
product C P0 = 0.5/s cancels the plant pole at s = -1, so the delay-free
closed loop is the first-order CL = 0.5 / (s + 0.5), response g(t) = 1 -
exp(-0.5 t), and the theory values below are exact closed forms).
Simulation: dt = 0.01 s, 60 s horizon (6001 samples), unit step
reference.

All values below are REAL outputs of the prep anchor
/tmp/w47spec/anchor_smith_predictor.py (pure stdlib, math only, no RNG,
exit 0, internal asserts all pass), run once at spec time and quoted as
printed:

- Recurrence and delay line (module output): first_order_lag_recurrence
  (1.0, 1.0, 0.01) gives a = 0.990049834 and b = 0.009950166 with a + b
  = 1.000000000000000; delay_steps gives D = 200 samples at theta =
  2.0 s and D = 500 samples at theta = 5.0 s.
- Delay-free companion (module output): the theta = 0, no-predictor
  simulation matches the continuous closed form 1 - exp(-0.5 t) with
  max abs error 0.001655 over the horizon (the forward-integral
  discretization residual of the digital PI), overshoot 0.000 and
  settling 7.83 s against the continuous 2 ln(50) = 7.824 s. This is
  the design response the predictor loop must reproduce after the dead
  time.
- Worked case theta = 2.0 s (module output):
  - with the predictor: overshoot_pct 0.000, settling_time 9.83 s,
    final_deviation 0.000000. The response is the delay-free response
    re-emitted after the dead time: y(4.0 s) = 0.633527 against the
    closed form 1 - exp(-0.5 * 2.0) = 0.632121 (the 0.0014 gap is the
    discretization residual measured above), y(8.0 s) = 0.950313
    against 1 - exp(-3.0) = 0.950213, y(12.0 s) = 0.993245, y(20.0 s)
    = 0.999875, monotone up, zero overshoot, settled at 2.0 +
    7.824046 = 9.824 s on the 0.01 s grid (9.83).
  - without the predictor, same gains: overshoot_pct 50.212 (peak
    1.502 at 6.00 s), settling_time 25.82 s, final_deviation 0.000022.
    The response oscillates through the delayed characteristic
    equation 1 + C P0 exp(-2 s): y(4.0 s) = 1.002158, y(8.0 s) =
    1.165740 (still climbing through the first overshoot), y(12.0 s)
    = 0.841161 (undershoot), y(20.0 s) = 0.946013, settling only at
    25.82 s.
  - predictor delay-shift identity (module output): max |y_sp[k] -
    y_df[k - 200]| = 2.220e-16, the discrete witness that the
    predictor loop IS the delay-free loop re-emitted 200 samples (2.0
    s) later.
- Robustness case theta = 5.0 s (module output):
  - with the predictor: overshoot_pct 0.000, settling_time 12.83 s
    (5.0 + 7.824046 = 12.824 s on the grid): y(6.0 s) = 0.395100,
    y(10.0 s) = 0.918155, y(20.0 s) = 0.999442, y(40.0 s) = 1.000000;
    predictor delay-shift identity max |y_sp[k] - y_df[k - 500]| =
    0.000e+00.
  - without the predictor, same gains: overshoot_pct 2182.315,
    settling_time None (the oscillation never holds the band; at the
    final sample it is still growing: y(6.0 s) = 0.501578, y(10.0 s)
    = 2.502479, y(20.0 s) = -2.403046, y(40.0 s) = -10.009273),
    final_deviation 11.909619. The delay 5.0 s pushes the loop past
    stability: the phase margin of the 0.5/s design loop falls from
    +32.7 deg at theta = 2.0 to negative at theta = 5.0.
- ValueErrors with real messages (module output, quoted as printed):
  first_order_lag_recurrence(0.0, 1.0, 0.01) raises "plant gain K must
  be positive, got 0.0"; first_order_lag_recurrence(1.0, 1.0, 0.0)
  raises "sample time dt must be positive, got 0.0"; delay_steps(-0.1,
  0.01) raises "dead time theta must be non-negative, got -0.1";
  delay_steps(2.5, 1.0) raises "dead time theta must be an integer
  multiple of dt, got theta 2.5 at dt 1.0"; delay_steps(0.0, 0.0)
  raises "sample time dt must be positive, got 0.0"; pi_output(0.1,
  0.0, 0.01, 0.0, 0.5) raises "proportional gain kp must be positive,
  got 0.0"; pi_output(0.1, 0.0, 0.01, 0.5, -0.1) raises "integral gain
  ki must be non-negative, got -0.1"; simulate_closed_loop(sim_time =
  0.0) raises "simulation time sim_time must be positive, got 0.0".

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of /tmp/w47spec/anchor_smith_
predictor.py (stdlib math, closed form, exit 0, no randomness, identical
under both interpreters).

## Validation list (contract test must include)

1. Recurrence identities within 1e-9: first_order_lag_recurrence(1.0,
   1.0, 0.01) returns a = 0.990049834 and b = 0.009950166 within 1e-9
   with a + b = 1.0 within 1e-12 and b / (1 - a) = 1.0 within 1e-9;
   delay_steps(2.0, 0.01) = 200 and delay_steps(5.0, 0.01) = 500.
2. Delay-free design collapse: the theta = 0, no-predictor simulation
   matches the closed form 1 - exp(-0.5 t) at every grid sample with
   max abs error below 5e-3 (real anchor 0.001655), overshoot_pct 0.0
   within 1e-6, settling_time 7.83 within 0.02 (theory 7.824).
3. Worked case theta = 2.0 s, predictor loop: overshoot_pct 0.0 within
   1e-6, settling_time 9.83 within 0.02, final_deviation below 1e-9,
   and the samples y(4.0) = 0.633527, y(8.0) = 0.950313, y(12.0) =
   0.993245, y(20.0) = 0.999875 each within 1e-5 (monotone, zero
   overshoot).
4. Predictor delay-shift identity: delay_shift_max_error(y_sp,
   y_delay_free, 200) below 1e-9 (real anchor 2.220e-16); at theta =
   5.0, delay_shift_max_error(y_sp, y_delay_free, 500) below 1e-9
   (real anchor 0.000e+00); the controller_error series of the
   predictor loop is the delay-free loop error, |e_comp - e_df| below
   1e-9 at every sample.
5. Conventional loop theta = 2.0 s, same gains: overshoot_pct 50.212
   within 0.01, peak_time 6.00 within 0.02, settling_time 25.82 within
   0.02, samples y(4.0) = 1.002158, y(8.0) = 1.165740, y(12.0) =
   0.841161, y(20.0) = 0.946013 each within 1e-5; the overshoot and
   settling contrast against the predictor loop (50.212 vs 0.000, 25.82
   vs 9.83) at IDENTICAL given gains.
6. Robustness case theta = 5.0 s: predictor loop overshoot_pct 0.0
   within 1e-6 and settling_time 12.83 within 0.02 (theory 12.824);
   conventional loop overshoot_pct 2182.315 within 0.01, settling_time
   None (the last out-of-band sample IS the final sample of the run),
   final_deviation 11.909619 within 1e-3, and the oscillation grows:
   y(40.0) = -10.009273 is below y(20.0) = -2.403046 and y(10.0) =
   2.502479 exceeds y(6.0) = 0.501578 in magnitude.
7. Settling identity: each predictor settling time equals theta + 2
   ln(50) to the grid: 9.83 at theta = 2.0 and 12.83 at theta = 5.0,
   each within 0.02; the no-predictor theta = 2.0 loop settles at
   25.82, strictly later than the 7.83 s delay-free response plus the
   2.0 s delay.
8. Steady state: final_deviation below 1e-6 for the predictor loops at
   both thetas (real anchor 0.000000) and below 1e-4 for the
   conventional theta = 2.0 loop (real anchor 0.000022).
9. Zero-delay collapse: simulate_closed_loop(dead_time = 0.0,
   predictor = True) equals the delay-free companion simulation,
   |y_sp - y_df| below 1e-9 sample by sample (D = 0, the predictor
   feedback signal vanishes).
10. All ValueErrors enumerated in the Worked example raise from the
    named public function with the real messages quoted there: gain,
    tau and dt guards (first_order_lag_recurrence), negative theta,
    zero dt and non-integer theta/dt guards (delay_steps), kp and ki
    guards (pi_output), sim_time guard (simulate_closed_loop); the
    delay_shift_max_error length and window guards also raise.
11. Determinism: identical outputs run to run and under both
    interpreters; no randomness anywhere; no imports beyond math;
    module constants fixed as PLANT_GAIN_K 1.0, PLANT_TAU 1.0,
    WORKED_THETA 2.0, ROBUST_THETA 5.0, CONTROLLER_KP 0.5,
    CONTROLLER_KI 0.5, SAMPLE_DT 0.01, SIM_TIME 60.0, REFERENCE 1.0,
    SETTLE_BAND 0.02, STEPS_EPS 1e-6, CL_POLE_RATE 0.5, CL_TAU 2.0.
    No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere.
12. Run the deterministic contract test offline (no network); it exits
    0. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).

## Corpus fragment (eval/hit1-wave47-smith-predictor.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "design the smith-predictor for the loop with dead time: model the
  delay-free plant, compute the delayed model output, and form the
  compensated feedback by subtracting the delayed prediction from the
  measured plant output before the primary controller"
  intent: "gnc-autonomy/control; smith-predictor dead-time compensation:
  the delay-free FOPDT plant model, the delayed model output held in
  the delay line, and the compensated feedback formed by subtracting
  the delayed prediction from the measured plant output before the
  primary controller closes on the delay-free error"
  expected_skill: "gnc-autonomy/control/smith-predictor"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply dead-time-compensation with the smith predictor structure:
  build the predictor output from the delay-free plant model and the
  transport delay and report the compensated error signal for the
  primary loop"
  intent: "gnc-autonomy/control; dead-time-compensation with the
  smith-predictor structure: the predictor output built from the
  delay-free plant model and the transport delay, and the compensated
  error signal reported for the primary loop"
  expected_skill: "gnc-autonomy/control/smith-predictor"
Task ids: w47-smith-predictor-1 and -2. Prep grep (run at spec time by
the probe and re-verified for this file): each of the tokens
smith-predictor, dead-time, transport-delay and delay-compensat returns
ZERO matches in eval/hit1-corpus.yaml (grep exit 1) and exactly ONE
skills/ hit, the pilot-induced-oscillation handling-qualities tau_e
context quoted in the Claim fences, so the queries are collision-free;
the sibling corpus tasks route on tuning and margin language
(pid-control-design, pid-control-design-w8-1/-2), z-domain sampled-data
language (digital-control-design, w32-*), deadbeat synthesis language
(deadbeat-control, w46-deadbeat-control-1/-2) and estimator language
(observer-design), none of which carries a delay-free predictor
feedback structure. Add one fence line to pid-control-design and one
router row to skills/gnc-autonomy/SKILL.md at build time pointing
dead-time compensation to the new leaf (the deadbeat-control and
digital-control-design precedents).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compensate the dead time of a
feedback loop with the smith-predictor structure:" and include the
outputs in the Claim order (the compensated error signal of the primary
loop, the closed-loop step response of the predictor-compensated loop,
which re-emits the delay-free design response after the dead time, and
of the same loop without compensation, and the step-response metrics of
both loops), then close with the Trigger list. The PI gains kp and ki
are given controller inputs, never tuned, placed or margin-checked;
refer to the delay-free internal model as the delay-free plant model
run on the controller output, never as a state estimate; and never
reproduce ARP4754A text (reference-only). First tag: smith-predictor.
Metadata tags EXACTLY as the probe receipt gate (f) lists them, nothing
else: smith-predictor, dead-time-compensation, time-delay-compensation,
delay-free-model-prediction, predictor-feedback-signal. 50-150 words,
<=1000 chars, no em dash, never the banned sweep term of the builder
kit, action verb
present. Recommended wording (144 words, 962 chars, verified at spec
time):

"Use when you must compensate the dead time of a feedback loop with the
smith-predictor structure: given a first-order-plus-dead-time plant
model and given PI controller gains, run the delay-free plant model on
the controller output, hold the model output in the delay line by the
dead time, and subtract the delayed model output from the measured
plant output to form the predictor feedback signal, so the primary
controller closes on a delay-free compensated error. Produces the
compensated error signal of the primary loop, the closed-loop step
responses of the predictor-compensated loop, which re-emits the
delay-free design response after the dead time, and of the same loop
without compensation, and the step-response metrics of both loops:
overshoot, settling time to the 2 percent band and final deviation.
Trigger: smith predictor, dead time compensation, time delay
compensation, transport delay, delay free model prediction, predictor
feedback signal."

FORBIDDEN TOKENS (belong to siblings): ziegler-nichols,
ultimate-gain, ultimate-period, controller-gain-tuning, pole-placement,
anti-windup, integrator-clamp, gain-margin, phase-margin and any PID
gain design or loop-margin claim (pid-control-design; kp and ki are
given inputs, never tuned or placed, and no margin is computed here);
z-transform, zero-order-hold plant discretization as a design claim,
tustin-bilinear-emulation, frequency-prewarping, discrete-pid-
coefficients, position-form, velocity-form, unit-circle-stability,
sample-rate-selection and any z-domain design claim (digital-control-
design; dt is the fixed simulation constant SAMPLE_DT, never a selected
design output); full-order-observer, luenberger, estimator-gain,
ackermann, observability, error-dynamics, separation-principle,
state-estimation and any claim that the internal model estimates plant
states (observer-design); deadbeat-control, finite-settling-time,
pole-placement-at-origin, minimum-settling-time, z-domain-deadbeat
(deadbeat-control); lead-lag, root-locus, bode-design, nyquist,
loop-shaping (lead-lag-compensation, root-locus-design,
frequency-response-design); mrac, model-reference-adaptive, l1-adaptive
(adaptive-control, l1-adaptive-control); system-identification,
process-identification, plant-identification and any claim that the
leaf identifies K, tau or theta from data (the FOPDT parameters and the
dead time are inputs); model-mismatch, robustness-analysis,
uncertainty-analysis (out of scope; the perfect-model assumption is
the model); pid-gain-tuning in any form. Never the bare single words
predictor, prediction, delay, dead, controller, plant, model, gain,
loop or response as standalone metadata tags.
