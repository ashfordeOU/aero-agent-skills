---
name: adaptive-backstepping
description: "Use when you must design and simulate the tuning-functions adaptive backstepping control law for a second-order strict-feedback plant x1_dot = x2 + theta f1(x1), x2_dot = u + f2(x1, x2) with the unknown constant plant parameter theta inside the recursion: update the single parameter estimate theta_hat with the second tuning function carried through the z1 z2 error recursion, assemble the adaptive virtual control and the final control, and audit the augmented Lyapunov function with the parameter-error term. Produces the error-variable and parameter-estimate histories, the tuning-function updates, the closed-loop command, and the parameter-error convergence verdict that gate an adaptive backstepping control assessment. Trigger: adaptive-backstepping, tuning-function, parameter-estimate, strict-feedback, adaptive-virtual-control, augmented-lyapunov-function, parameter-error-convergence, no-over-parameterization."
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
  tags: [adaptive-backstepping, tuning-function, parameter-estimate, strict-feedback, adaptive-virtual-control, augmented-lyapunov-function, parameter-error-convergence, no-over-parameterization]
  version: 0.1.0
  author: AeroSkills
---

# Adaptive Backstepping (gnc-autonomy/control/adaptive-backstepping)

Use when the task is a recursive strict-feedback design for a second-order
nonlinear plant whose channel-1 drift carries an unknown constant parameter
theta: build the control law one error variable at a time, the same recursion
shape as backstepping-control, but replace the known-drift term with the
online estimate theta_hat and drive that single estimate with the second
tuning function carried through the recursion. The channel-2 drift f2 and
the design gains c1, c2 and adaptation rate gamma are given inputs, never
identified or tuned; only theta is unknown, and it is estimated by ONE
parameter update, never over-parameterized. It pairs with backstepping-
control, the exact-model recursion this leaf reduces to at zero adaptation
gain, and never overlaps adaptive-control, whose first-order plant and
model-reference tracking error drive two adaptive gains, or l1-adaptive-
control, whose state predictor and low-pass-filtered adaptation law estimate
a lumped uncertainty rather than a structural drift coefficient.

## Domain quick reference

- Plant: second-order strict feedback x1_dot = x2 + theta f1(x1), x2_dot = u
  + f2(x1, x2), unit control gain, f1(x1) = x1^2 (known shape, unknown
  constant theta multiplying it), f2(x1, x2) = x1 x2 (known exactly), x1
  and x2 measured, theta not measured.
- Reference x1d(t): constant kind gives x1d = REF_SETPOINT with zero
  derivatives; sinusoidal kind gives x1d = SIN_AMP sin(SIN_OMEGA t) with the
  matching first and second derivatives.
- First error variable z1 = x1 - x1d; virtual control alpha1 = -c1 z1 +
  x1d_dot - theta_hat w1 with w1 = f1(x1), so z1_dot = -c1 z1 + z2 +
  theta_tilde w1 with theta_tilde = theta - theta_hat.
- Second error variable (mismatch) z2 = x2 - alpha1.
- Design-model derivative (theta_hat as the plant coefficient, since theta
  is unknown to the controller): alpha1_dot = -(c1 + theta_hat df1(x1))
  (x2 + theta_hat w1) + c1 x1d_dot + x1d_ddot - theta_hat_dot w1, with
  df1(x1) = 2 x1.
- Tuning functions: tau1 = gamma z1 w1 (first step), w2 = (c1 + theta_hat
  df1(x1)) w1, tau2 = gamma (z1 w1 + z2 w2) (second, the estimator update
  theta_hat_dot = tau2), the positive w2 convention that cancels the
  parameter-mismatch terms out of the z2 dynamics.
- Final control u = -f2(x1, x2) + alpha1_dot - z1 - c2 z2; substituting
  gives z2_dot = -z1 - c2 z2 + theta_tilde w2.
- Augmented Lyapunov function V2 = (z1^2 + z2^2)/2 + theta_tilde^2/(2
  gamma); with theta_hat_dot = tau2 the parameter-mismatch terms cancel and
  V2_dot = -c1 z1^2 - c2 z2^2 exactly in continuous time.
- Reduction identity: at gamma = 0 with theta_hat(0) = theta, theta_hat
  stays frozen and the construction reduces exactly to the backstepping-
  control exact-model recursion.

## Workflow

1. Fix the plant and the design inputs: the known drift shape f1(x1) =
   x1^2 and the known channel-2 drift f2(x1, x2) = x1 x2, the reference
   kind (constant or sinusoidal), the design gains c1, c2, the adaptation
   rate gamma and the initial state and parameter estimate. Only theta is
   unknown; c1, c2 and gamma are given, never tuned online.
2. Form the first error variable z1 = x1 - x1d with tracking_error, and the
   theta_hat-carrying virtual control with alpha1_value(z1, ref_dot,
   theta_hat, w1, c1): alpha1 = -c1 z1 + x1d_dot - theta_hat w1, where w1 =
   w1_regressor(x1).
3. Propagate the inner-state mismatch as the second error variable with
   mismatch_error(x2, alpha1): z2 = x2 - alpha1.
4. Form the design-model derivative of the virtual control with
   alpha1_dot_adaptive(x1, x2, ref_dot, ref_ddot, theta_hat, th_dot, c1),
   evaluated with theta_hat as the plant coefficient because theta is
   unknown to the controller.
5. Build the tuning functions with tau1_value(z1, w1, gamma) and
   tau2_value(z1, z2, w1, w2, gamma), using w2 = omega2_regressor(x1,
   theta_hat, c1); the single parameter estimate updates as theta_hat_dot
   = tau2, the second tuning function carried through the recursion.
6. Assemble the recursive final control with final_control(f2_value,
   alpha1_dot, z1, z2, c2): u = -f2 + alpha1_dot - z1 - c2 z2, then
   simulate the closed loop with simulate(c1, c2, gamma, kind).
7. Audit the z1-map and z2-map residual identities, the augmented-Lyapunov
   decay realized by v2_value against the design rates c1, c2, and the
   convergence of theta_hat toward theta and of z1, z2 toward zero.

## Worked example

Plant x1_dot = x2 + theta x1^2, x2_dot = u + x1 x2, theta = 1.0 the unknown
constant (the controller sees only theta_hat), unit control gain. Design
gains c1 = c2 = 2.0 (1/s), gamma = 5.0 (worked case A), c1 = c2 = 4.0,
gamma = 10.0 (rate case B), gamma = 0.0 with theta_hat(0) = theta (reduction
case C), gamma = 20.0 with a sinusoidal reference (persistent-excitation
case D). Initial state x1(0) = 0, x2(0) = 0, theta_hat(0) = 0 (cases A, B,
D) or 1.0 (case C). Forward Euler at dt = 0.001 s. All values below are
real outputs of scripts/adaptive_backstepping_logic.py:

- Worked case A (constant reference, c1 = c2 = 2.0, gamma = 5.0, horizon
  10 s): initial z1(0) = -1.0000000000, z2(0) = -2.0000000000, alpha1(0) =
  2.0000000000, u(0) = 5.0000000000, theta_tilde(0) = 1.0000000000, V2(0)
  = 2.6000000000. Audit residuals z1_map_max = 1.569160e-03, z2_map_max =
  1.101886e-02, v2_mono_viol = 0 (V2 monotone non-increasing over all
  10000 steps). Parameter transient: theta_hat dips to -0.4386805331 at t
  = 1.0 s before recovering to theta_hat(10) = 1.0000982189 (theta_tilde =
  -0.0000982189). Final sample T = 10.0 s: x1 = 0.9999809509, x2 =
  -1.0001096335, z1 = -0.0000190491, z2 = -0.0000876144, u = 1.0023303954,
  V2 = 0.0000000050. Sample points: x1(0.5) = 0.3390297388, x1(1.0) =
  0.9731049081, x1(2.0) = 1.0363587713, x1(4.0) = 0.9961053848, x1(6.0) =
  0.9988545516; theta_hat(2.0) = 0.9031981710, theta_hat(6.0) =
  0.9967713046.
- Rate case B (c1 = c2 = 4.0, gamma = 10.0, horizon 6 s): z2(0) =
  -4.0000000000, u(0) = 17.0000000000, V2(0) = 8.5500000000. Final T = 6.0
  s: theta_hat = 1.0000484342, x1 = 1.0000045989, z1 = 0.0000045989, z2 =
  0.0000212992, u = 0.9986281208, tighter than the worked case at the same
  horizon, the c1, c2, gamma rate lever.
- Reduction case C (gamma = 0.0, theta_hat(0) = 1.0, horizon 6 s): the
  exact-model limit of backstepping-control. z1(0) = -1.0000000000, z2(0)
  = -2.0000000000, u(0) = 5.0000000000; theta_hat frozen exactly (max
  deviation 0.0); z1_map_max = 1.110223e-16 (machine exact, the sibling's
  own witness); final x1 = 0.9999973792, u = 1.0000620640, matching the
  sibling's worked-case final values (x1 = 0.999997441, u = 1.000062552)
  within the discretization band; sample cross-check x1(0.5) =
  0.3244768479 vs sibling 0.324501865, x1(4.0) = 1.0007242372 vs
  1.000722845.
- PE case D (sinusoidal reference, gamma = 20.0, horizon 40 s): the
  persistently exciting reference drives theta_hat to theta: theta_hat(40)
  = 0.9996543840 (|theta_tilde| = 3.456160e-04), max |z1| over the run =
  0.2049438438, z1(40) = 0.0000904604, v2_mono_viol = 0.
- Closed-form identities: alpha1_value(-1.0, 0.0, 0.0, 0.0, 2.0) =
  2.0000000000; omega2_regressor(1.0, 1.0, 2.0) = 4.0000000000; V2(0) =
  v2_value(-1.0, -2.0, 1.0, 5.0) = 2.6000000000.
- ValueErrors (real messages): alpha1_value(0.1, 0.0, 0.0, 0.1, 0.0)
  raises "design gain c1 must be positive, got 0.0"; alpha1_dot_adaptive
  (0.1, 0.0, 0.0, 0.0, 0.1, 0.0, 0.0) raises "design gain c1 must be
  positive, got 0.0"; final_control(0.1, 0.0, 0.1, 0.1, 0.0) raises
  "design gain c2 must be positive, got 0.0"; simulate(c1=0.0) raises
  "design gain c1 must be positive, got 0.0"; simulate(c2=0.0) raises
  "design gain c2 must be positive, got 0.0"; simulate(gamma=-1.0) raises
  "adaptation gain gamma must be non-negative, got -1.0"; simulate(dt=0.0)
  raises "sample time dt must be positive, got 0.0"; simulate(sim_time=
  0.0) raises "simulation time sim_time must be positive, got 0.0";
  reference(0.5, 'ramp') raises "reference kind must be 'constant' or
  'sinusoidal', got 'ramp'"; v2_value(-1.0, -2.0, 1.0, 0.0) raises
  "adaptation gain gamma must be positive, got 0.0".

## Verification

- Confirm the recursion algebra closed forms: alpha1_value(-1.0, 0.0, 0.0,
  0.0, 2.0) = 2.0, mismatch_error(0.0, 2.0) = -2.0, v2_value(-1.0, -2.0,
  1.0, 5.0) = 2.6, omega2_regressor(1.0, 1.0, 2.0) = 4.0.
- Confirm the worked, rate, reduction and persistent-excitation cases
  converge theta_hat toward theta and z1, z2 toward zero within the
  bounds quoted in the Worked example.
- Confirm the augmented Lyapunov function V2 is monotone non-increasing
  (v2_mono_viol = 0) in every case, absorbing the non-PE parameter-
  transient dip without a stability violation.
- Confirm the zero-adaptation-gain reduction case matches the
  backstepping-control sibling worked case within the discretization
  band, and that theta_hat stays exactly frozen when gamma = 0.
- Confirm ValueError rejection of non-positive c1, non-positive c2, a
  negative gamma, a non-positive dt or sim_time, and an unrecognized
  reference kind, with the real messages quoted in the Worked example.
- Run the contract test offline: python3 scripts/test_adaptive_backstepping.py
  (deterministic, no imports beyond math, no exact-float equality on any
  computed sum).

## Related leaves

- gnc-autonomy/control/backstepping-control: the exact-model recursion for
  the same second-order strict-feedback plant with both drift terms known
  exactly and no estimator; this leaf reduces to it exactly at zero
  adaptation gain with theta_hat(0) = theta.
- gnc-autonomy/control/adaptive-control: a model-reference adaptive
  controller for a first-order plant with two adaptive gains updated by a
  gradient law on a reference-model tracking error; this leaf's plant is
  second-order strict feedback, carries one estimator, and its update is
  the tuning-function combination z1 w1 + z2 w2, not a model-reference
  error.
- gnc-autonomy/control/l1-adaptive-control: runs a state predictor and a
  projection-based adaptation law through a low-pass filter for a
  first-order plant with a lumped-uncertainty estimate; this leaf runs no
  predictor, no projection and no filter, and its estimator targets a
  single structural drift coefficient.
- gnc-autonomy/control/sliding-mode-control: switches on an error surface
  with an equivalent control plus a boundary-layer term; this leaf has no
  surface, no switching term, and its control is continuous.
- gnc-autonomy/control/feedback-linearization: cancels the plant
  nonlinearities by Lie-derivative decoupling; this leaf never inverts the
  plant, its linear closed-loop behavior appears only in the error
  coordinates.
- gnc-autonomy/control/observer-design: designs a Luenberger state
  observer; this leaf assumes x1 and x2 are measured and estimates only
  the scalar parameter theta, never the states.

## Pitfalls

- Reading this leaf as the exact-model recursion: f2, c1, c2 and gamma are
  given inputs, but theta is genuinely unknown and estimated online (that
  distinction is what separates this leaf from backstepping-control).
- Confusing the tuning-function update with a model-reference gradient
  law: theta_hat_dot = tau2 = gamma (z1 w1 + z2 w2) is carried through the
  second-order recursion, not a gradient on a reference-model tracking
  error (adaptive-control territory).
- Getting the w2 sign wrong: omega2_regressor must use the POSITIVE
  convention (c1 + theta_hat df1(x1)) w1; the negative-sign variant makes
  the closed loop diverge to NaN inside 2 s, which the contract test's
  audit bounds catch immediately.
- Differentiating alpha1 with the TRUE parameter theta instead of
  theta_hat: the design-model derivative alpha1_dot_adaptive must use
  theta_hat as the plant coefficient in x1_rate, since theta is unknown to
  the controller; using theta breaks the tuning-function cancellation.
- Adding a second adaptive gain or over-parameterizing the estimator: the
  construction carries exactly ONE parameter estimate theta_hat, never a
  vector of estimates.

## Behavior contract (gate 3)

The reference, error-variable, adaptive virtual-control, mismatch,
design-model derivative, tuning-function, final-control and closed-loop
simulation logic is exercised by the gate 3 contract test:
scripts/test_adaptive_backstepping.py against
scripts/adaptive_backstepping_logic.py (stdlib unittest, offline,
deterministic, 44 test methods). Run:

    python3 scripts/test_adaptive_backstepping.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only, per
  standards-map.yaml, as the reference-only control-pack convention shared
  with backstepping-control, adaptive-control, l1-adaptive-control,
  pid-control-design, observer-design and sliding-mode-control.
- compliance: STANDARDS-REF, gated: false.
