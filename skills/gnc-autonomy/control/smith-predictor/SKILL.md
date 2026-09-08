---
name: smith-predictor
description: "Use when you must compensate the dead time of a feedback loop with the smith-predictor structure: given a first-order-plus-dead-time plant model and given PI controller gains, run the delay-free plant model on the controller output, hold the model output in the delay line by the dead time, and subtract the delayed model output from the measured plant output to form the predictor feedback signal, so the primary controller closes on a delay-free compensated error. Produces the compensated error signal of the primary loop, the closed-loop step responses of the predictor-compensated loop, which re-emits the delay-free design response after the dead time, and of the same loop without compensation, and the step-response metrics of both loops: overshoot, settling time to the 2 percent band and final deviation. Trigger: smith predictor, dead time compensation, time delay compensation, transport delay, delay free model prediction, predictor feedback signal."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [smith-predictor, dead-time-compensation, time-delay-compensation, delay-free-model-prediction, predictor-feedback-signal]
  version: 0.1.0
  author: AeroSkills
---

# Smith Predictor (gnc-autonomy/control/smith-predictor)

Use when the task is dead-time compensation for a single feedback loop
on a first-order-plus-dead-time (FOPDT) plant: the primary PI
controller is designed for the delay-free plant model, and a Smith
predictor removes the dead time from the loop's characteristic
equation so the closed loop tracks as if the delay were not there,
re-emitting the delay-free response after the dead time. This leaf
implements the O. J. M. Smith dead-time compensator ("Closer Control
of Loops with Dead Time", Chemical Engineering Progress 53(5):217-219,
1957) in pure Python, stdlib only, deterministic and offline. It pairs
with pid-control-design for the PI gains this leaf takes as given
inputs, and with digital-control-design for the sampled-data toolbox
that would discretize a continuous plant before it reaches this leaf.

## Domain quick reference

- Plant and internal model: P(s) = P0(s) exp(-theta s) with the
  delay-free plant model P0(s) = K / (tau s + 1); the internal model
  is P0(s) driven by the controller output, never a state observer.
- Primary controller: C(s) = kp + ki / s; kp and ki are given inputs,
  never tuned or placed by this leaf.
- Predictor feedback signal: the current model output minus the model
  output delayed by theta, p(s) = P0(s) (1 - exp(-theta s)) U(s), the
  1 - exp(-s theta) dead-time block of the Smith anchor.
- Compensated error: e_comp = r - y_measured - (y_model - y_model_delayed);
  the measured plant output, delayed by the dead time, is corrected by
  the difference between the current and delayed model output so the
  primary loop closes on a delay-free error.
- Setpoint closed-loop identities: the conventional loop keeps the dead
  time in its characteristic equation, Y/R = C P0 exp(-theta s) /
  (1 + C P0 exp(-theta s)); the predictor loop with a perfect model
  removes it, Y/R = C P0 exp(-theta s) / (1 + C P0), so the
  characteristic equation 1 + C P0 is the delay-free design
  denominator and the dead time survives only as an output shift.
- Worked-case cancellation: at K = 1.0, tau = 1.0, kp = 0.5, ki = 0.5,
  C(s) P0(s) = 0.5/s exactly (the controller zero cancels the plant
  pole at s = -1), so the delay-free closed loop is CL = 0.5 / (s +
  0.5), step response g(t) = 1 - exp(-0.5 t), and the predictor loop
  settles at theta + 2 ln(50) seconds.
- Discrete simulation: exact sampled first-order recurrence
  y[k+1] = a y[k] + b u[k-D] with a = exp(-dt/tau), b = K(1-a), an
  integer pure-delay line D = round(theta/dt), and a delay-free
  internal model ym[k+1] = a ym[k] + b u[k]; the PI controller runs on
  whichever error the configuration selects, e_comp under the
  predictor or e otherwise.
- Perfect-model assumption: the internal model uses the true plant
  gain, time constant and dead time exactly; model mismatch and
  time-varying delay are out of scope.

## Workflow

1. Fix the plant and controller: the FOPDT plant P(s) = P0(s)
   exp(-theta s) with given K, tau and theta, and the given PI gains
   kp and ki (never tuned or placed here).
2. Compute the sampled first-order lag recurrence with
   first_order_lag_recurrence and the integer delay line length with
   delay_steps.
3. Run the delay-free companion simulation (theta = 0, no predictor)
   with simulate_closed_loop to get the design response the predictor
   loop must reproduce after the dead time.
4. Run the predictor-compensated loop with simulate_closed_loop
   (predictor=True): the delay-free plant model runs on the controller
   output, its output is held in the delay line by the dead time, and
   the predictor feedback signal is formed by subtracting the delayed
   model output from the measured plant output to close the primary
   loop on the compensated error.
5. Run the conventional loop without compensation at the SAME given
   gains with simulate_closed_loop(predictor=False) for the
   comparison.
6. Read the step-response metrics of both loops with step_metrics:
   overshoot percentage, peak time, settling time to the 2 percent
   band and final deviation.
7. Confirm the predictor delay-shift identity with
   delay_shift_max_error: the predictor loop output equals the
   delay-free companion output shifted by the dead time, the discrete
   witness that the dead time left the characteristic equation.
8. Confirm the deterministic checks with the contract test
   scripts/test_smith_predictor.py.

## Worked example

Plant: FOPDT K = 1.0, tau = 1.0 s (P0 = 1/(s+1)), worked dead time
theta = 2.0 s, robustness case theta = 5.0 s. Primary controller: PI
with the given gains kp = 0.5, ki = 0.5. Simulation: dt = 0.01 s, 60 s
horizon, unit step reference.

- Recurrence and delay line: first_order_lag_recurrence(1.0, 1.0, 0.01)
  gives a = 0.990049834, b = 0.009950166, a + b = 1.0; delay_steps
  gives D = 200 at theta = 2.0 s and D = 500 at theta = 5.0 s.
- Delay-free companion: matches the continuous closed form
  1 - exp(-0.5 t) with max abs error 0.001655 over the horizon (the
  forward-integral discretization residual), overshoot 0.000 and
  settling 7.83 s against the continuous 2 ln(50) = 7.824 s.
- Worked case theta = 2.0 s, predictor loop: overshoot_pct 0.000,
  settling_time 9.83 s, final_deviation about 0. Monotone response:
  y(4.0) = 0.633527, y(8.0) = 0.950313, y(12.0) = 0.993245,
  y(20.0) = 0.999875, the delay-free response re-emitted 2.0 s later.
  Predictor delay-shift identity: max |y_sp[k] - y_df[k-200]| =
  2.220e-16.
- Worked case theta = 2.0 s, conventional loop, same gains:
  overshoot_pct 50.212 (peak 1.502 at 6.00 s), settling_time 25.82 s,
  final_deviation about 0.000022: y(4.0) = 1.002158, y(8.0) = 1.165740,
  y(12.0) = 0.841161, y(20.0) = 0.946013, oscillating through the
  delayed characteristic equation.
- Robustness case theta = 5.0 s, predictor loop: overshoot_pct 0.000,
  settling_time 12.83 s; y(6.0) = 0.395100, y(10.0) = 0.918155,
  y(20.0) = 0.999442, y(40.0) = 1.000000; delay-shift identity max
  |y_sp[k] - y_df[k-500]| = 0.000e+00.
- Robustness case theta = 5.0 s, conventional loop, same gains:
  overshoot_pct 2182.315, settling_time None (the oscillation never
  holds the band; still growing at the final sample), final_deviation
  11.909619: y(6.0) = 0.501578, y(10.0) = 2.502479, y(20.0) =
  -2.403046, y(40.0) = -10.009273. The 5.0 s delay pushes the loop past
  stability at the same gains that were stable with the predictor.
- ValueErrors: first_order_lag_recurrence(0.0, 1.0, 0.01) raises
  "plant gain K must be positive, got 0.0"; first_order_lag_recurrence
  (1.0, 1.0, 0.0) raises "sample time dt must be positive, got 0.0";
  delay_steps(-0.1, 0.01) raises "dead time theta must be
  non-negative, got -0.1"; delay_steps(2.5, 1.0) raises "dead time
  theta must be an integer multiple of dt, got theta 2.5 at dt 1.0";
  delay_steps(0.0, 0.0) raises "sample time dt must be positive, got
  0.0"; pi_output(0.1, 0.0, 0.01, 0.0, 0.5) raises "proportional gain
  kp must be positive, got 0.0"; pi_output(0.1, 0.0, 0.01, 0.5, -0.1)
  raises "integral gain ki must be non-negative, got -0.1";
  simulate_closed_loop(sim_time=0.0) raises "simulation time sim_time
  must be positive, got 0.0".

## Verification

- Confirm first_order_lag_recurrence and delay_steps match the
  recurrence and delay-line anchors within tight tolerance, with the
  a + b = K and b/(1-a) = K identities holding.
- Confirm the delay-free companion simulation matches the continuous
  closed form 1 - exp(-0.5 t) within the discretization residual.
- Confirm the predictor loop at theta = 2.0 s and theta = 5.0 s matches
  the worked overshoot, settling time, final deviation and sample
  values, and that delay_shift_max_error confirms the delay-shift
  identity against the delay-free companion.
- Confirm the conventional loop at the SAME given gains degrades as
  theta grows: theta = 2.0 s overshoots and settles late; theta = 5.0
  s diverges (settling_time None), the isolated effect of removing the
  predictor structure.
- Confirm ValueError rejection of a non-positive plant gain, time
  constant or sample time, a negative or non-multiple dead time, a
  non-positive proportional gain, a negative integral gain, a
  non-positive simulation time, and mismatched or out-of-window inputs
  to delay_shift_max_error.
- Run the contract test offline: python3 scripts/test_smith_predictor.py
  (deterministic, no imports beyond math).

## Related leaves

- gnc-autonomy/control/pid-control-design: tunes and places the PI
  gains kp and ki this leaf takes as given inputs; this leaf never
  tunes, places or margin-checks a controller.
- gnc-autonomy/control/digital-control-design: the sampled-data toolbox
  that discretizes a continuous plant with a zero-order hold; this leaf
  simulates at a fixed sample time constant and never designs in the
  z-domain.
- gnc-autonomy/control/observer-design: a full-order state observer for
  unmeasured states; this leaf's internal model is a delay-free copy of
  the plant driven by the controller output, not a state estimate.

## Pitfalls

- Treating the internal model as a state estimator: the delay-free
  plant model P0(s) run on the controller output is not a Luenberger
  or Kalman state estimate; it carries no estimator gain and no error
  dynamics.
- Tuning kp and ki here: this leaf never derives, places or
  margin-checks the PI gains; a change in the predictor loop's
  behavior at fixed gains comes only from the dead time theta, never
  from a gain change.
- Assuming the predictor helps disturbance rejection: the delay-free
  characteristic equation 1 + C P0 governs the setpoint path only; the
  worked comparison is a setpoint step and makes no disturbance-path
  claim.
- Feeding a non-multiple dead time: delay_steps requires theta to be an
  integer multiple of dt within STEPS_EPS; a fractional number of
  samples has no exact pure-delay line and raises ValueError instead
  of rounding silently.
- Expecting the predictor to fix an unstable model mismatch: the
  perfect-model assumption is the model itself; a mismatch between the
  internal model and the true plant is out of scope and not simulated.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_smith_predictor.py

The test covers the recurrence and delay-line identities (workflow
step 2), the delay-free companion collapse (step 3), the predictor
loop worked values at theta = 2.0 s and theta = 5.0 s (step 4), the
conventional-loop comparison at the same given gains (step 5), the
step-response metrics of both loops (step 6), the predictor
delay-shift identity (step 7), the zero-delay collapse, determinism
across repeated runs, and ValueError rejection of every non-physical
input enumerated in the Worked example.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard (name plus paraphrase only, per standards-map.yaml); the
  Smith predictor relations above are standard control engineering
  methodology from O. J. M. Smith (1957), summary-only.
- compliance: STANDARDS-REF, gated: false.
