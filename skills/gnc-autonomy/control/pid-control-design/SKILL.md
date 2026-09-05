---
name: pid-control-design
description: "Use when the task is PID tuning, proportional integral derivative terms, anti-windup, integrator clamping, pole placement, or gain and phase margin checks. Design PID controller gains for aerospace flight and GNC control loops: compute the controller output from the proportional, integral, and derivative error terms, tune the gains from the plant model with Ziegler-Nichols using the ultimate gain and ultimate period, or place closed loop poles directly for a first or second order plant, add integrator anti-windup clamping, and check the gain margin and phase margin of the loop. Trigger: pid, proportional, integral, derivative, ziegler-nichols, ultimate gain, ultimate period, anti-windup, integrator clamp, pole placement, phase margin, gain margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [pid-control-design, pid, controller-tuning, proportional, integral, derivative, ziegler-nichols, ultimate-gain, ultimate-period, pole-placement, anti-windup, integrator-clamp, phase-margin, gain-margin, discrete-derivative]
  version: 0.1.0
  author: Aero Agent Skills
---

# PID Control Design (gnc-autonomy/control/pid-control-design)

Use when the task is PID controller design for an aerospace flight or
GNC loop: computing the output from the proportional, integral, and
derivative error terms, deriving gains from the plant model (first or
second order) by Ziegler-Nichols tuning or pole placement, protecting
the integrator with anti-windup clamping, or checking the loop's gain
and phase margins.

## Domain quick reference

- The PID output is u = kp*e + ki*int(e) + kd*de/dt where e is the
  error, int(e) its accumulated integral, and de/dt its derivative.
  kp acts on the error magnitude, ki removes steady-state error by
  integrating it, kd anticipates the error trend and adds damping.
- Ziegler-Nichols continuous-cycling tuning uses the ultimate gain ku
  and ultimate period tu measured at the stability boundary. Classic
  rules: P gives kp = 0.5*ku; PI gives kp = 0.45*ku with
  Ti = tu/1.2; PID gives kp = 0.6*ku with Ti = tu/2 and Td = tu/8.
- Pole placement for the first-order plant G(s) = b/(s + a) with a PI
  controller: matching the closed loop to s^2 + 2*zeta*wn*s + wn^2
  gives kp = (2*zeta*wn - a)/b and ki = wn^2/b.
- Pole placement for the second-order plant
  G(s) = b/(s^2 + a1*s + a0) with a PID controller: matching to
  (s^2 + 2*zeta*wn*s + wn^2)(s + p3) gives kd = (2*zeta*wn + p3 - a1)/b,
  kp = (wn^2 + 2*zeta*wn*p3 - a0)/b, and ki = wn^2*p3/b.
- Anti-windup: when the actuator saturates, the integrator keeps
  accumulating and drives the loop into a long overshoot. Conditional
  integration clamps the accumulated integral to +/-limit each step,
  so the integrator cannot wind up beyond the actuator's authority.
- Margins for the type-1 open loop K/(s(s + a)): crossover where
  K^2 = wc^2(wc^2 + a^2), phase margin 90 - atan(wc/a) in degrees.
  The phase reaches -180 deg only at infinite frequency, so the gain
  margin is infinite for this loop.
- Discrete implementation: on a sampled flight computer the derivative
  term uses the backward difference (e_k - e_{k-1})/dt at sample time
  dt, and the integral accumulates ki*e*dt; dt must be positive and
  the sample rate consistent with the loop bandwidth.

## Workflow

1. Write the error equation: e = command - measured state in plant
   units (angle, rate, position).
2. Model the plant: first order b/(s + a) or second order
   b/(s^2 + a1*s + a0) from the flight dynamics (see the
   flight-mechanics stability and control leaves).
3. Choose a tuning route: Ziegler-Nichols from a measured ku/tu
   (scripts/pid_control_design_logic.py: ziegler_nichols) or pole
   placement from a target wn/zeta (pole_placement_first_order,
   pole_placement_second_order).
4. Add anti-windup with integrator_clamp on the accumulated integral.
5. Verify the margins of the loop (stability_margins_type1) and
   sanity-check the gains (kp > 0, ki >= 0, kd >= 0).
6. Implement in discrete time with discrete_derivative and the sample
   time dt; recompute the gains if dt changes materially.

## Pitfalls

- Tuning with Ziegler-Nichols from an unvalidated ku/tu: the ultimate
  values come from the stability boundary, not from any operating
  point.
- Placing poles without checking that the resulting gains are
  physically sane; negative integral or derivative gains are a red
  flag.
- Omitting anti-windup on an actuator-limited loop: the integrator
  winds up during saturation and the loop overshoots on release.
- Reading the gain margin as finite for a type-1 loop; its phase only
  reaches -180 deg at infinite frequency.
- Using a continuous derivative on a sampled computer; the backward
  difference needs dt and produces a gain that changes with sample
  rate.
- Mixing units across error, integral, and derivative terms; the
  gains must be dimensioned per term.

## Behavior contract (gate 3)

The PID output, Ziegler-Nichols, pole placement, anti-windup, margin,
and discrete-derivative logic is exercised by the gate 3 contract
test: scripts/test_pid_control_design.py against
scripts/pid_control_design_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_pid_control_design.py

## Compliance

- ARP4754A is proprietary (SAE); name + paraphrase only per
  standards-map.yaml and brief 06 (revision note: ARP4754B
  supersedes; this skill keys to A, the certification-baseline
  revision).
- compliance: STANDARDS-REF, gated: false.
