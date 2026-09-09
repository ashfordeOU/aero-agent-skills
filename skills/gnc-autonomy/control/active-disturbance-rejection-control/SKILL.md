---
name: active-disturbance-rejection-control
description: "Use when you must design and simulate an active-disturbance-rejection-control law for a second-order plant with an unknown total disturbance: run the linear-extended-state-observer with bandwidth-parameterized observer gains placing every observer pole at omega_o to estimate the state and the total disturbance, cancel the estimate with the disturbance-rejection term divided by the plant-gain estimate b0, and close the outer loop with the bandwidth-parameterized PD law on the estimated states placing the tracking poles at omega_c. Produces the observer-gain triple from the (s + omega_o)^3 expansion, the disturbance-cancellation audit of the rejection term, and the tracking-error, command and total-disturbance-estimate histories that gate an active disturbance rejection control assessment. Trigger: active-disturbance-rejection-control, linear-extended-state-observer, adrc, bandwidth-parameterization, total-disturbance-estimate, disturbance-rejection-term, observer-gain-parameterization."
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
  tags: [active-disturbance-rejection-control, linear-extended-state-observer, adrc, bandwidth-parameterization, total-disturbance-estimate, disturbance-rejection-term, observer-gain-parameterization]
  version: 0.1.0
  author: AeroSkills
---

# Active Disturbance Rejection Control (gnc-autonomy/control/active-disturbance-rejection-control)

Use when the task is linear active disturbance rejection control (ADRC)
of a second-order plant whose internal dynamics and external
disturbance are both unknown and lumped together as one total
disturbance: a third-order linear extended state observer (LESO)
estimates the state and the total disturbance from the measured output
alone, and the control law cancels the disturbance estimate so the
plant channel behaves as an ideal double integrator under a
bandwidth-parameterized PD outer loop. The observer gains and the
outer-loop gains are always fixed closed forms of two bandwidths,
omega_o and omega_c, never tuned or adapted online. It pairs with
gnc-autonomy/control/observer-design, whose full-order Luenberger
estimator is designed for a known LTI plant at arbitrary poles rather
than an augmented disturbance state at a fixed bandwidth, and with
gnc-autonomy/control/adaptive-control and
gnc-autonomy/control/l1-adaptive-control, whose gains or adaptive
signals update online against an unknown plant coefficient rather than
reconstruct a total disturbance at fixed observer poles.

## Domain quick reference

- Design plant: canonical second-order y_ddot = f(y, y_dot, w) + b0 u
  with f the total disturbance (internal dynamics plus external
  disturbance, lumped and unknown to the controller) and b0 the given
  control-effectiveness estimate (b0 != 0 required).
- LESO (third order, augmented with the disturbance state z3 = f):
  z1_dot = z2 + beta1 (y - z1), z2_dot = z3 + beta2 (y - z1) + b0 u,
  z3_dot = beta3 (y - z1); only the output y is measured.
- Bandwidth parameterization (observer gains): beta1 = 3 omega_o,
  beta2 = 3 omega_o^2, beta3 = omega_o^3, making the error-dynamics
  characteristic polynomial s^3 + beta1 s^2 + beta2 s + beta3 =
  (s + omega_o)^3, all observer error poles at -omega_o.
- Disturbance-rejection control: u = (u0 - z3)/b0. With the converged
  estimate z3 = f the plant channel collapses to the exact double
  integrator y_ddot = f + b0 ((u0 - z3)/b0) = u0.
- Outer loop (bandwidth-parameterized PD on the estimated states):
  u0 = kp (r - z1) - kd z2 with kp = omega_c^2, kd = 2 omega_c, placing
  the ideal-loop tracking poles at -omega_c (double).
- Practical bandwidth ratio: omega_o = 6 omega_c in the worked design,
  inside the 4-10x band that keeps the observer fast enough to track
  the disturbance without amplifying measurement noise.
- Truth plant (simulator bookkeeping only, never a controller input):
  y_ddot = -A1 y_dot - A0 y + w(t) + b u with the true gain b, so the
  simulator-truth total disturbance is f = -A1 y_dot - A0 y + w(t).
- Units are SI throughout: rad/s for the bandwidths, dimensionless for
  b0 and the true gain b, seconds for time.

## Workflow

1. Fix the design plant and gains: pick the control-effectiveness
   estimate b0, the controller bandwidth omega_c and the observer
   bandwidth omega_o (omega_o must exceed omega_c), and confirm the
   bandwidth parameterization with observer_gains and
   controller_gains.
2. Confirm the LESO characteristic-polynomial identity with
   char_poly_residual at sample points, verifying all three observer
   error poles sit at -omega_o (the (s + omega_o)^3 expansion).
3. Run the closed-loop simulation with simulate_adrc: the third-order
   linear extended state observer estimates the state and the total
   disturbance z3 from the measured output y alone, on the truth plant
   with a disturbance step.
4. Read the disturbance-rejection control law u = (u0 - z3)/b0 and
   audit the cancellation with cancellation_residual at the phase
   fixed points, the algebraic witness that z3 = f collapses the loop
   to the ideal double integrator.
5. Inspect the tracking-error, command and total-disturbance-estimate
   histories across the reference start and the disturbance step,
   checking the settled-window residuals (max_abs_e_settle,
   max_z3_res_settle).
6. Compare against the ideal perfect-cancellation loop with
   simulate_ideal to isolate the observer-lag cost of the finite
   bandwidth from the plant response itself.
7. Run the mismatch robustness case (plant_b != b0) and confirm the
   output still settles at the reference while the estimate carries
   the fixed bias (b - b0) u.
8. Confirm the deterministic checks with the contract test
   scripts/test_active_disturbance_rejection_control.py.

## Worked example

Plant: second-order y_ddot = f(y, y_dot, w) + b0 u with the design gain
estimate b0 = 1.0; simulator truth y_ddot = -0.75 y_dot - 0.5 y + w(t)
+ b u with the external disturbance w = 0.5 for t < 3.0 s and w = 1.5
for t >= 3.0 s (a +1.0 step at 3.0 s) and the true gain b = 1.0
(worked, matched) or b = 0.8 (robustness, a 25 percent over-modeled
control effectiveness). Design: controller bandwidth omega_c = 5.0
rad/s, observer bandwidth omega_o = 30.0 rad/s (six times omega_c), so
kp = 25.0 and kd = 10.0 place the tracking poles at -5 (double) and
beta = (90.0, 2700.0, 27000.0) place the observer error poles at -30
(triple). Reference r = 1.0 constant, initial state y(0) = 0, v(0) =
0, LESO from the zero estimate z(0) = (0, 0, 0). Forward Euler at
dt = 1e-4 s over a 6.0 s horizon (60001 samples). All values below are
real outputs of scripts/active_disturbance_rejection_control_logic.py:

- Bandwidth parameterization: observer_gains(30.0) = (90.0, 2700.0,
  27000.0); controller_gains(5.0) = (25.0, 10.0); char_poly_residual
  is 0.000e+00 at s = -30, -3, -1 and 0.5.
- Fixed points of the cancelled loop (y = r = 1.0, v = 0, u0 = 0):
  phase 1 (w = 0.5) f = 0.0, z3 = 0.0, u = 0.0; phase 2 (w = 1.5)
  f = 1.0, z3 = 1.0, u = -1.0; cancellation_residual is 0.000e+00 at
  both.
- Worked run (b = b0 = 1.0): y(0.2) = 0.259669337601, y(0.5) =
  0.705882336870, y(1.0) = 0.963564880347, y(2.0) = 1.000073982338,
  y(3.0) = 1.000006249016 (settled on r before the step); after the
  step y(3.05) = 1.001168788483, y(3.25) = 1.008944174201 (peak
  excursion), y(4.0) = 1.001300603879, y(6.0) = 0.999999797512.
- Worked metrics: e(6.0) = -2.025e-07; max |e| over [3.0, 6.0] =
  9.161e-03 (the disturbance-step excursion); max |e| over
  [5.5, 6.0] = 8.016e-07 and max |z3 - f_truth| over [5.5, 6.0] =
  1.403e-06 (the settled band); u(6.0) = -1.000001803850 against the
  exact -1.0; z3(6.0) = 0.999999402193 against f_truth(6.0) =
  0.999999537946.
- Ideal closed form: the double integrator step response y(t) =
  1 - (1 + omega_c t) exp(-omega_c t) gives 0.264241117657 at t = 0.2 s
  and 0.959572318005 at t = 1.0 s; the ideal Euler run reproduces the
  t = 1.0 s value to 3.369e-05 (Euler truncation at dt = 1e-4).
- Ideal-loop comparison: max |y_adrc - y_ideal| over [0.0, 6.0] =
  9.172e-03, over [5.5, 6.0] = 8.015e-07; observer-lag deficit
  y_adrc(1.0) - y_ideal(1.0) = 0.003958874713 (the observer trails the
  perfect-cancellation loop during the fast reference transient).
- Mismatch robustness run (b = 0.8, b0 = 1.0): y(6.0) =
  1.000000346701 (still settles at r); u(6.0) = -1.249993763548,
  z3(6.0) = 1.249999451753; the estimate carries the fixed bias
  z3 - f = (b - b0) u = 0.25, real max |z3 - f| over [5.5, 6.0] =
  2.500e-01.
- ValueErrors (real messages): observer_gains(0.0) raises "observer
  bandwidth omega_o must be positive, got 0.0"; controller_gains(0.0)
  raises "controller bandwidth omega_c must be positive, got 0.0";
  control_law and cancellation_residual with b0 = 0.0 raise
  "control-effectiveness estimate b0 must be nonzero, got 0.0";
  simulate_adrc(omega_c=5.0, omega_o=5.0) raises "observer bandwidth
  omega_o must exceed the controller bandwidth omega_c, got omega_o
  5.0 <= omega_c 5.0"; simulate_adrc(t_step=6.0) raises "disturbance
  step time t_step must lie strictly inside (0, sim_time), got t_step
  6.0 for sim_time 6.0".

## Verification

- Confirm observer_gains(30.0) equals (90.0, 2700.0, 27000.0) and
  controller_gains(5.0) equals (25.0, 10.0) within 1e-9, and that
  char_poly_residual is below 1e-9 at s = -30, -3, -1 and 0.5.
- Confirm cancellation_residual(f, u0, f, b0) is below 1e-12 for any
  f, u0, b0, the algebraic witness that z3 = f collapses the plant
  channel to the double integrator y_ddot = u0.
- Confirm the worked-run sample points at 0.2, 0.5, 1.0, 2.0, 3.0,
  3.05, 3.25, 3.5, 4.0, 5.0 and 6.0 s match the quoted anchor values
  within 1e-6 relative, and that the settled-window residuals
  max_abs_e_settle and max_z3_res_settle stay below 1e-5 and 1e-4.
- Confirm the ideal-loop comparison bounds max |y_adrc - y_ideal| and
  the observer-lag deficit at t = 1.0 s against the quoted anchor.
- Confirm the mismatch robustness run still settles at the reference
  while the estimate bias matches (b - b0) u to within 1e-3.
- Confirm ValueError rejection of a non-positive omega_o or omega_c, a
  zero b0, omega_o not exceeding omega_c, a non-positive dt or
  sim_time, and a t_step outside (0, sim_time), with the real messages
  quoted in the Worked example.
- Run the contract test offline:
  python3 scripts/test_active_disturbance_rejection_control.py
  (deterministic, no imports beyond math, no exact-float equality on
  any computed sum).

## Related leaves

- gnc-autonomy/control/observer-design: designs a full-order Luenberger
  state observer for a known LTI plant by Ackermann pole placement at
  arbitrary locations; this leaf's three observer gains come only from
  the (s + omega_o)^3 expansion, augment the disturbance state, and
  exist only inside the disturbance-rejection control law.
- gnc-autonomy/control/adaptive-control: updates two gains online
  against an unknown plant coefficient with a gradient adaptation law;
  this leaf's gains are fixed closed forms of two bandwidths and
  nothing adapts, and the disturbance is the object the observer
  estimates and the law cancels.
- gnc-autonomy/control/l1-adaptive-control: runs a state predictor and
  a projection-based adaptation law through a low-pass filter; this
  leaf runs no predictor, no projection and no adaptive signal, and its
  observer is a fixed linear estimator, not a filtered adaptive
  estimate.
- gnc-autonomy/control/pid-control-design: tunes P-I-D gains by
  Ziegler-Nichols or pole placement with anti-windup and margin checks;
  this leaf never tunes, its kp, kd and beta gains are given closed
  forms of omega_c and omega_o, and the disturbance is rejected through
  the estimated z3 rather than integrated away.
- gnc-autonomy/control/sliding-mode-control: reconstructs no
  disturbance and instead bounds a constant matched disturbance with a
  switching term sized above the bound; this leaf reconstructs the
  total disturbance with a fixed-gain linear observer and cancels it,
  with no switching term.

## Pitfalls

- Treating this leaf as an adaptive or predictor-based law: the
  observer gains and the outer-loop gains are always fixed closed
  forms of omega_o and omega_c, nothing updates online, and there is
  no state predictor, projection or low-pass adaptive filter
  (adaptive-control, l1-adaptive-control territory).
- Designing the observer for a known plant model: the LESO never needs
  the plant model, because the augmented third state z3 absorbs the
  internal dynamics into the total disturbance; feeding a known model
  through an Ackermann pole-placement design belongs to
  observer-design, not here.
- Choosing omega_o too close to omega_c: the spec's practical band is
  4 to 10 times the controller bandwidth (the worked ratio is 6); a
  narrower ratio slows the disturbance estimate and widens the
  step-response excursion after a disturbance change.
- Ignoring the b0-mismatch bias: when the true gain b differs from the
  design estimate b0, the output still settles at the reference but
  the total-disturbance estimate carries a fixed bias (b - b0) u
  forever, not a transient that decays away.
- Reading the observer-lag deficit as a design defect: the finite-
  bandwidth LESO always trails the ideal perfect-cancellation loop
  during fast transients (the worked deficit is 0.003958874713 at
  t = 1.0 s), and this cost only vanishes once both loops reach the
  same fixed point.
- Reproducing ARP4754A text verbatim: the standard is reference-only,
  summary-only per standards-map.yaml.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_active_disturbance_rejection_control.py

The test covers the bandwidth-parameterization closed forms and the
LESO characteristic-polynomial identity, the disturbance-cancellation
residual identity, the exact ideal double-integrator closed form
reproduced by the Euler run, the worked-run sample points and settled-
window residuals, the ideal-loop comparison and observer-lag deficit,
the mismatch robustness run and its fixed estimate bias, ValueError
rejection of every non-physical input, and determinism across repeated
runs (40 test methods).

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only, per
  standards-map.yaml, as the reference-only control-pack convention
  shared with pid-control-design, observer-design, sliding-mode-control,
  feedback-linearization and h-infinity-synthesis.
- compliance: STANDARDS-REF, gated: false.
