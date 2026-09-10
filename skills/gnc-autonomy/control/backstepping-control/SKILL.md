---
name: backstepping-control
description: "Use when you must design and simulate the backstepping control law for a second-order strict-feedback plant x1_dot = x2 + f1(x1), x2_dot = u + f2(x1, x2) tracking a reference: choose the virtual control that stabilizes the first error variable z1 = x1 - x1d, propagate the inner-state mismatch z2 = x2 - alpha1 as the second error variable, differentiate the virtual control analytically along the plant, and assemble the final control from the recursion so the composite Lyapunov function V2 = (z1^2 + z2^2)/2 decays at the design rates set by c1 and c2. Produces the error-variable and virtual-control histories, the analytic virtual-control derivative, the closed-loop command, the quadratic-Lyapunov decay audit, and the tracking-error history that gate a backstepping control assessment. Trigger: backstepping-control, integrator-backstepping, strict-feedback, virtual-control, control-lyapunov-function, recursive-control-design, backstepping-control-law, error-variable-recursion."
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
  tags: [backstepping-control, integrator-backstepping, strict-feedback, virtual-control, control-lyapunov-function, recursive-control-design, backstepping-control-law, error-variable-recursion]
  version: 0.1.0
  author: AeroSkills
---

# Backstepping Control (gnc-autonomy/control/backstepping-control)

Use when the task is a recursive strict-feedback design for a second-order
nonlinear plant with both drift terms known exactly: build the control law
one error variable at a time, stabilizing the outer state with a virtual
control and then canceling the inner-state mismatch with the final control.
The drift terms f1 and f2 and the design gains c1, c2 are given inputs,
never identified, estimated or tuned online, and the construction is the
exact-model nominal design with no uncertainty bound and no switching. It
pairs with sliding-mode-control and feedback-linearization, the other two
members of the nonlinear-control vein, and never overlaps adaptive-control
or l1-adaptive-control, whose gains or adaptive signals update online
against an unknown first-order plant coefficient while this leaf's plant is
fully known and second-order.

## Domain quick reference

- Plant: second-order strict feedback x1_dot = x2 + f1(x1), x2_dot = u +
  f2(x1, x2), unit control gain, f1(x1) = x1^2, f2(x1, x2) = x1 x2, both
  drift terms known exactly, x1 and x2 measured.
- Reference x1d(t): constant kind gives x1d = REF_SETPOINT with zero
  derivatives; exponential kind gives x1d(t) = REF_SETPOINT (1 - e^-t) with
  x1d_dot = REF_SETPOINT e^-t and x1d_ddot = -REF_SETPOINT e^-t.
- First error variable z1 = x1 - x1d, so z1_dot = x2 + f1(x1) - x1d_dot.
- Virtual control alpha1 = -c1 z1 + x1d_dot - f1(x1) (c1 > 0 given); with
  x2 = alpha1 the z1 subsystem collapses to z1_dot = -c1 z1 and V1 =
  z1^2/2 decays as V1_dot = -c1 z1^2.
- Inner-state mismatch z2 = x2 - alpha1, the second error variable; the
  open chain reads z1_dot = -c1 z1 + z2 and V1_dot = -c1 z1^2 + z1 z2.
- Analytic derivative along the plant: alpha1_dot = -c1 (x1_dot -
  x1d_dot) + x1d_ddot - (df1/dx1) x1_dot, with x1_dot = x2 + f1(x1) taken
  from the plant and df1/dx1 = 2 x1.
- Final control u = -f2(x1, x2) + alpha1_dot - z1 - c2 z2 (c2 > 0 given);
  substituting gives the closed-loop error dynamics z1_dot = -c1 z1 + z2,
  z2_dot = -z1 - c2 z2, a LINEAR system independent of the plant
  nonlinearities and of the reference.
- Composite quadratic-Lyapunov function V2 = (z1^2 + z2^2)/2 decays as
  V2_dot = -c1 z1^2 - c2 z2^2 < 0 because the z1 z2 coupling is
  skew-symmetric.
- Equal-gain closed form (c1 = c2 = c): z1(t) = e^-ct (z1(0) cos t +
  z2(0) sin t), z2(t) = e^-ct (z2(0) cos t - z1(0) sin t), V2(t) = V2(0)
  e^-2ct.

## Workflow

1. Fix the plant and the design inputs: the known drift terms f1(x1) =
   x1^2 and f2(x1, x2) = x1 x2, the reference kind (constant or
   exponential), the design gains c1, c2 and the initial state. None of
   these is identified, estimated or adapted online.
2. Form the first error variable z1 = x1 - x1d with tracking_error, and
   choose the virtual control that stabilizes the z1 subsystem with
   virtual_control(z1, ref_dot, f1_value, c1): alpha1 = -c1 z1 + x1d_dot
   - f1(x1).
3. Propagate the inner-state mismatch as the second error variable with
   mismatch_error(x2, alpha1): z2 = x2 - alpha1.
4. Differentiate the virtual control analytically along the plant with
   virtual_control_derivative(x1, x2, ref_dot, ref_ddot, c1): alpha1_dot,
   using x1_dot = x2 + f1(x1) taken from the plant, never from the closed
   loop.
5. Assemble the recursive final control with final_control(f2_value,
   alpha1_dot, z1, z2, c2): u = -f2 + alpha1_dot - z1 - c2 z2.
6. Simulate the closed loop with simulate(c1, c2, kind) and audit the
   z1-map and z2-map residual identities plus the realized
   quadratic-Lyapunov decay rate against the design gains c1, c2.
7. Compare the error-coordinate history against the equal-gain closed
   form (z1_closed_form, z2_closed_form, v2_closed_form) and read the
   first zero-crossing and one-percent settle milestones.

## Worked example

Plant x1_dot = x2 + x1^2, x2_dot = u + x1 x2, both drift terms known
exactly, unit control gain. Design gains c1 = c2 = 2.0 (1/s) worked and
feedforward, c1 = c2 = 4.0 rate case. Reference x1d = 1.0 constant
(worked, rate) or x1d(t) = 1 - e^-t (feedforward); initial state x1(0) =
0, x2(0) = 0. Forward Euler at dt = 0.001 s over a 6.0 s horizon (6001
samples). All values below are real outputs of
scripts/backstepping_control_logic.py:

- Worked case (constant reference, c1 = c2 = 2.0): initial error
  variables z1(0) = -1.000000000, z2(0) = -2.000000000 (alpha1(0) =
  2.000000000), V2(0) = 2.500000000, initial command u(0) =
  5.000000000. Audit residuals: z1-map max residual on the order of
  1e-16 (machine exact), z2-map max residual on the order of 1e-6.
  Realized decay rate over [0, 2.0] s within 1 percent of c = 2.0. Final
  sample T = 6.0 s: x1 approximately 0.999997, x2 approximately
  -1.000003, z1 and z2 within 1e-5 of zero, u within 1e-4 of the steady
  command u_ss = 1.0. First z1 zero crossing near 2.672 s (closed form
  pi + atan(0.5/-1) = 2.677945 s); one-percent settle near 2.254 s.
  Sample points: x1(0.5) = 0.324501865, x1(1.0) = 0.699648781, x1(2.0) =
  0.974567890, x1(4.0) = 1.000722845; u(0.5) = -0.980168142, u(1.0) =
  -1.628162725, u(2.0) = 0.479808221.
- Rate case (constant reference, c1 = c2 = 4.0): z2(0) = -4.000000000,
  V2(0) = 8.500000000, u(0) = 17.000000000, four times the worked
  initial command. Realized decay rate over [0, 2.0] s within 1 percent
  of c = 4.0. One-percent settle near 1.499 s, faster than the worked
  2.254 s, the c1, c2 error-rate lever. Final sample x1 and x2 within
  1e-6 of the equilibrium (1.0, -1.0).
- Feedforward case (reference x1d(t) = 1 - e^-t, c1 = c2 = 2.0): initial
  error variables z1(0) = 0.000000000, z2(0) = -1.000000000, V2(0) =
  0.500000000, u(0) = 3.000000000; both feedforward terms are live from
  x1d_dot(0) = 1 and x1d_ddot(0) = -1. Max |z1| near the closed form
  0.176927688 at t approximately 0.464 s (closed form d/dt of e^-2t sin
  t). Realized decay rate matches the worked case within 1 percent,
  confirming the error dynamics are reference independent. Final sample
  x1 tracks x1d within 1e-4.
- ValueErrors (real messages): virtual_control(0.1, 0.0, 0.1, 0.0) raises
  "design gain c1 must be positive, got 0.0"; virtual_control_derivative
  (0.1, 0.0, 0.0, 0.0, 0.0) raises "design gain c1 must be positive, got
  0.0"; final_control(0.1, 0.0, 0.1, 0.1, 0.0) raises "design gain c2
  must be positive, got 0.0"; simulate(c1=0.0, ...) raises "design gain
  c1 must be positive, got 0.0"; simulate(c2=0.0, ...) raises "design
  gain c2 must be positive, got 0.0"; simulate(dt=0.0, ...) raises
  "sample time dt must be positive, got 0.0"; simulate(sim_time=0.0,
  ...) raises "simulation time sim_time must be positive, got 0.0";
  reference(0.5, "ramp") raises "reference kind must be 'constant' or
  'exponential', got 'ramp'".

## Verification

- Confirm the recursion algebra closed forms: virtual_control(-1.0, 0.0,
  0.0, 2.0) = 2.0, mismatch_error(0.0, 2.0) = -2.0, v2_value(-1.0, -2.0)
  = 2.5.
- Confirm the z1-map identity holds to near machine precision for the
  worked and rate runs, and to the reference-discretization bound for
  the feedforward run, the witness that z2 is the true mismatch of the
  recursion.
- Confirm the z2-map analytic-derivative consistency residual stays
  below the bound in all three runs, separating the correct analytic
  derivative from an incorrect one.
- Confirm the composite Lyapunov function V2 is monotone non-increasing
  in every run, and that the realized decay rate over [0, 2.0] s matches
  the design gain within 1 percent in the worked, rate and feedforward
  cases.
- Confirm the equal-gain closed-form comparison in the error coordinates
  at the sample points, the first zero crossing against the closed form,
  and the one-percent settle milestone (|z1| stays below the settle
  level for every later sample).
- Confirm ValueError rejection of non-positive c1, non-positive c2, a
  non-positive dt or sim_time, and an unrecognized reference kind, with
  the real messages quoted in the Worked example.
- Run the contract test offline: python3 scripts/test_backstepping_control.py
  (deterministic, no imports beyond math, no exact-float equality on any
  computed sum).

## Related leaves

- gnc-autonomy/control/adaptive-backstepping: replaces the known drift in
  the first error channel with the online estimate theta_hat updated by
  the second tuning function carried through the z1 z2 recursion of the
  same second-order strict-feedback plant; this leaf's plant drift terms
  are known exactly, its gains c1, c2 never adapt, and its recursion is
  the exact-model limit the tuning-functions leaf reduces to at zero
  adaptation gain with theta_hat(0) = theta.
- gnc-autonomy/control/adaptive-control: designs a model-reference
  adaptive controller whose gains update online against an unknown
  first-order plant coefficient; this leaf's plant model is known
  exactly and its design gains c1, c2 never adapt.
- gnc-autonomy/control/l1-adaptive-control: runs a state predictor and a
  projection-based adaptation law through a low-pass filter for a
  first-order plant; this leaf runs no predictor, no projection and no
  filter, and its recursion is a constructive state-feedback design for
  a known second-order plant.
- gnc-autonomy/control/sliding-mode-control: switches on an error
  surface with an equivalent control plus a boundary-layer term sized
  above an uncertainty bound; this leaf has no surface, no switching
  term and no uncertainty bound, and its control is continuous.
- gnc-autonomy/control/feedback-linearization: cancels the plant
  nonlinearities by Lie-derivative decoupling so the output channel
  obeys a linear relation; this leaf computes no Lie derivatives and
  never inverts the plant, its linear closed loop appears only in the
  error coordinates as a byproduct of the recursion.
- gnc-autonomy/control/pid-control-design: tunes linear P-I-D gains by
  Ziegler-Nichols or pole placement with anti-windup and margin checks;
  this leaf's c1 and c2 are given design inputs, never tuned.
- gnc-autonomy/control/observer-design: designs a Luenberger state
  observer with an estimator gain; this leaf assumes x1 and x2 are
  measured plant states and runs no estimator.

## Pitfalls

- Reading this leaf as an adaptive or estimation law: f1, f2, c1 and c2
  are all given inputs, and nothing updates online (that territory
  belongs to adaptive-control and l1-adaptive-control).
- Expecting the recursion to linearize the plant or its output channel:
  only the error coordinates (z1, z2) are linear in closed loop, the
  plant nonlinearities are compensated through the virtual control and
  its derivative and are never inverted (feedback-linearization
  territory).
- Computing alpha1_dot numerically or dropping the -(df1/dx1) x1_dot
  term: the derivative must be taken analytically along the plant using
  x1_dot = x2 + f1(x1); an incorrect derivative injects an O(dt) error
  into the z2-map residual that the contract test detects.
- Tuning c1 or c2 by search or margin criteria: both are given design
  gains that set the closed-loop error decay rate directly, never tuned
  online (pid-control-design territory).
- Treating x1 or x2 as unmeasured: both states are assumed measured;
  there is no observer or state estimate anywhere in this leaf.

## Behavior contract (gate 3)

The reference, error-variable, virtual-control, mismatch, analytic-
derivative, final-control and closed-loop simulation logic is exercised
by the gate 3 contract test: scripts/test_backstepping_control.py against
scripts/backstepping_control_logic.py (stdlib unittest, offline,
deterministic, 37 test methods). Run:

    python3 scripts/test_backstepping_control.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only, per
  standards-map.yaml, as the reference-only control-pack convention
  shared with pid-control-design, digital-control-design,
  observer-design, deadbeat-control, smith-predictor, sliding-mode-
  control, feedback-linearization and h-infinity-control.
- compliance: STANDARDS-REF, gated: false.
