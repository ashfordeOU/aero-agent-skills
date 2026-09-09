---
name: feedback-linearization
description: "Use when you must apply feedback linearization to a nonlinear plant with a known exact model: compute the Lie derivatives of the output along the drift and control vector fields to establish the relative degree, invert the decoupling scalar at the operating state, form the linearizing control that cancels the nonlinear terms so the output channel obeys the linear relation y^(r) = v, apply the outer linear tracking loop with the assigned closed-loop pole placement, and check the internal dynamics via their zero dynamics before accepting the design. Produces the relative-degree verdict, the linearizing control with the decoupling scalar, the exactly linearized closed-loop response against the assigned closed form, and the zero-dynamics stability verdict that gates the design. Trigger: feedback linearization, input output linearization, lie derivative, relative degree, decoupling matrix, linearizing control, zero dynamics, internal dynamics stability."
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
  tags: [feedback-linearization, lie-derivative, relative-degree, decoupling-matrix, linearizing-control, zero-dynamics, internal-dynamics-stability, input-output-linearization]
  version: 0.1.0
  author: AeroSkills
---

# Feedback Linearization (gnc-autonomy/control/feedback-linearization)

Use when the task is input-output feedback linearization of a nonlinear
plant with a known, exact model: the affine single-input plant xdot =
f(x) + g(x) u, y = h(x) is linearized exactly by canceling its
nonlinear terms through the control channel, so the chosen output obeys
the linear relation y^(r) = v under an outer tracking loop, and the
design is accepted only after the unobservable internal dynamics are
checked stable through their zero dynamics. This leaf implements the
Lie-derivative relative-degree construction (Slotine and Li; Isidori)
in pure Python, stdlib only. It pairs with
gnc-autonomy/control/state-space-analysis for the linear-model
counterpart and with gnc-autonomy/control/sliding-mode-control, the
switching-law sibling of the same nonlinear vein, for a plant with
matched uncertainty instead of an exact model.

## Domain quick reference

- Plant: xdot1 = -A11 x1 + x2, xdot2 = CUBIC x1^3 + QUAD x2^2 + x1 u,
  the affine model xdot = f(x) + g(x) u with g(x) = (0, x1), a control
  effectiveness that vanishes at x1 = 0. The model is exact and given,
  never identified or adapted.
- Lie derivatives: L_f^k h(x) is the k-th derivative of the output h
  along the drift field f, computed by analytic chain rule (no finite
  differences); L_g L_f^k h(x) = <d(L_f^k h)(x), g(x)> is the
  relative-degree probe along the control field.
- Relative degree r: the first r with L_g L_f^(r-1) h nonzero at x,
  preceded by L_g L_f^k h = 0 for k = 0 .. r - 2. No finite relative
  degree exists when every probe up to the system order N vanishes.
- Decoupling scalar: a(x) = L_g L_f^(r-1) h, the quantity that must be
  inverted to form the control. It is x1 for both registered outputs
  of this plant, invertible on x1 != 0.
- Linearizing control: u = (v - L_f^r h) / a(x) cancels the nonlinear
  terms exactly, leaving y^(r) = v on the chosen channel.
- Outer tracking loop: v = -K (y - y_ref) for relative degree 1, and
  v = -K^2 (y - y_ref) - 2 K ydot for relative degree 2, placing the
  closed-loop pole at s = -K (a double pole at r = 2). K is one fixed
  given constant, never tuned, scheduled, or adapted online.
- Zero dynamics: the internal dynamics left over when the output and
  its derivatives are held at zero. For this plant's relative-degree-1
  design the internal dynamics reduce to x1dot = -A11 x1; the design is
  accepted only when that eigenvalue is strictly negative.
- Units are SI-neutral state variables; the module runs a closed-loop
  RK4 simulation with the control law recomputed fresh at every
  integration stage, so its residual against the exact closed form is
  RK4 truncation error only.
- ARP4754A frames the development assurance context for the airborne
  or space function that hosts the linearizing loop; the relations
  above are standard nonlinear control methodology, summary-only.

## Workflow

1. Fix the plant and the operating state x, and register the output
   channel (x1 or x2) whose relative degree you need.
2. Compute the Lie derivatives L_f^k h along the drift field with
   Lf_power_h, and probe the control channel with Lg_Lf_power_h.
3. Establish the relative degree r with relative_degree: the defining
   property L_g L_f^k h = 0 for k < r - 1 with a nonzero probe at
   r - 1; a ValueError signals no finite relative degree exists at
   that state.
4. Read the decoupling scalar a(x) with decoupling_scalar and invert
   it, either directly with linearizing_control_from or at the state
   level with linearizing_control, to form the linearizing control
   u = (v - L_f^r h) / a that cancels the nonlinear terms.
5. Set the outer linear command v with outer_command at the assigned
   closed-loop pole rate K.
6. Run the closed-loop RK4 simulation with closed_loop_sim and compare
   the output against the exact closed form (closed_form_r1 or
   closed_form_r2) with series_max_abs_error, and confirm the pole
   placement with measured_decay_rate.
7. Check the internal dynamics of the relative-degree-1 design against
   the zero-dynamics stability verdict with zero_dynamics_analysis
   before accepting the design.
8. Confirm the deterministic checks with the contract test
   scripts/test_feedback_linearization.py.

## Worked example

Plant: xdot1 = -x1 + x2, xdot2 = x1^3 + x2^2 + x1 u (A11 = CUBIC =
QUAD = 1.0). Worked initial state x0 = (0.5, 0.0), unit-step reference
y_ref = 1.0, assigned closed-loop rate K = 2.0.

- Relative degree at x0: output x2 gives r = 1 with probe table
  [(0, 0.5)] (L_g h2 = x1 = 0.5, nonzero at r - 1 = 0); output x1
  gives r = 2 with table [(0, 0.0), (1, 0.5)] (L_g h1 = 0 for k = 0 <
  r - 1 = 1, L_g L_f h1 = x1 = 0.5 nonzero at r - 1). The decoupling
  scalar a(x0) = 0.5 for both outputs, and a(1.0, 0.75) = 1.0.
- Lie terms and controls: L_f h2 = f2 = 0.125 and L_f^2 h1 = x1 - x2 +
  x1^3 + x2^2 = 0.625. Outer commands v = 2.0 (r = 1) and v = 4.0
  (r = 2) give linearizing controls u = 3.75 (r = 1) and u = 6.75
  (r = 2). The cancellation residual f2 + a u - v is 0.000e+00 at x0
  and at (1.0, 0.75), so the nonlinear terms leave the channel exactly.
- r = 1 closed loop: the simulated output matches the assigned linear
  dynamics 1 - exp(-2 t) with max abs error 4.929e-14 over 10001 RK4
  samples (truncation only); y(0.5) = 0.632120558829, y(1) =
  0.864664716763, y(2) = 0.981684361111, y(5) = 0.999954600070;
  settling to the 1e-3 band at 3.454 s; measured decay rate between
  t = 0.5 and t = 1.0 is 2.000000, the pole witness for s = -K.
- Internal state of the r = 1 design: x1 matches the closed form
  1 - 1.5 exp(-t) + exp(-2 t) with max abs error 4.552e-14, dipping to
  0.437500056838 at t = 0.288 s (theory ln(4/3) = 0.287682 s) before
  rising to x1(10) = 0.999931902167, approaching y_ref while staying
  bounded.
- r = 2 companion loop: the fully linearized output matches the
  double-pole closed form 1 - (0.5 + 1.5 t) exp(-2 t) with max abs
  error 1.275e-13; the coefficient B = -1.5 is nonzero, the surviving
  t exp(-2 t) signature of the repeated pole (s + 2)^2.
- Zero-dynamics verdict: eigenvalue -1.0, verdict "asymptotically
  stable"; the constrained samples x1 = 0.5 exp(-t) at t = 1, 2, 5 s
  are 0.183939721, 0.067667642, 0.003368973, so the design is accepted.

## Verification

- Confirm relative_degree('x2', (0.5, 0.0)) returns (1, [(0, 0.5)]) and
  relative_degree('x1', (0.5, 0.0)) returns (2, [(0, 0.0), (1, 0.5)]).
- Confirm the cancellation identity f2 + a u - v = 0 within 1e-12 at
  the worked state and at (1.0, 0.75).
- Confirm the r = 1 closed loop matches 1 - exp(-2 t) within 1e-9 and
  the measured decay rate matches K = 2.0 within 1e-3.
- Confirm the r = 2 closed loop matches the double-pole closed form
  within 1e-9 and carries a nonzero double-root coefficient B.
- Confirm the zero-dynamics verdict is "asymptotically stable" with
  eigenvalue -1.0, and that relative_degree raises ValueError at
  x1 = 0 (the decoupling scalar vanishes) and for the constant output.
- Run the contract test offline: python3
  scripts/test_feedback_linearization.py (29 tests, deterministic).

## Related leaves

- gnc-autonomy/control/state-space-analysis: linear-model eigenvalue
  and controllability analysis, the fixed-linear counterpart when the
  plant needs no nonlinear cancellation.
- gnc-autonomy/control/sliding-mode-control: the switching-law sibling
  of the same nonlinear vein, sizing a discontinuous control against a
  matched-uncertainty bound instead of canceling a known model exactly.
- gnc-autonomy/control/adaptive-control: model-reference adaptation of
  gains for an unknown plant coefficient, the case where no exact model
  is available to cancel.
- gnc-autonomy/control/gain-scheduling: interpolating existing linear
  gains across the envelope, the alternative when K should vary with
  the operating point instead of staying fixed.

## Pitfalls

- Holding the control fixed across an integration step: the linearizing
  control must be recomputed at every RK4 stage from that stage's
  state, not sampled once per step and held; a held control introduces
  first-order-in-dt error instead of the RK4 truncation residual near
  1e-13 that the worked example reports.
- Evaluating the relative-degree probe at a singular state: the
  decoupling scalar a(x) = x1 vanishes at x1 = 0, so no finite relative
  degree exists there and the linearizing control is undefined; check
  x1 != 0 before inverting.
- Reading the internal state against the reference instead of its own
  closed form: x1 trails y_ref by the 1.5 exp(-t) mode of the internal
  dynamics (a 6.81e-5 gap at t = 10 s), so assert against
  1 - 1.5 exp(-t) + exp(-2 t), not against y_ref directly.
- Treating K as tunable online: K is one fixed given closed-loop rate
  in this leaf; scheduling or adapting it belongs to
  gnc-autonomy/control/gain-scheduling or the adaptive-control siblings.
- Skipping the zero-dynamics check: canceling the output dynamics
  exactly says nothing about the unobservable internal state; the
  relative-degree-1 design is accepted only after its zero-dynamics
  eigenvalue is confirmed strictly negative.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_feedback_linearization.py

The test covers the Lie-derivative and relative-degree identities at
the worked state and at a probe state, the decoupling-scalar inversion
and the cancellation identity, the linearizing control values for both
the relative-degree-1 and relative-degree-2 designs, the RK4
closed-loop simulation against both exact closed forms with the
measured pole-placement witness, the internal-dynamics closed form and
its minimum, the zero-dynamics stability verdict and its constrained
samples, the relative-degree rejection cases (a singular state, the
constant output, an unknown output), the decoupling-inversion guard,
and ValueError rejection of non-positive closed-loop rate, sample time,
simulation time, reference, and non-physical state inputs.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames development
  assurance for the airborne or space functions that host a
  feedback-linearizing control loop; the Lie-derivative relative-degree
  construction above is standard nonlinear control methodology
  (Slotine and Li; Isidori), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
