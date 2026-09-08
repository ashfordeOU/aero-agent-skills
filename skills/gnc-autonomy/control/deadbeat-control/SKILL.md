---
name: deadbeat-control
description: "Use when you must design a deadbeat-control law for a discrete-time plant given by its pulse transfer function: verify admissibility for direct deadbeat synthesis (every plant pole and zero strictly inside the unit circle), solve the deadbeat design equation that places every closed loop pole at the origin of the z plane, form the finite-settling-time controller difference equation from the plant polynomials, and simulate the closed loop to confirm the output reaches and holds the reference in the minimum number of sample periods with the minimum-settling-time control sequence. Produces the admissibility verdict, the controller coefficients, the settling sample and settling time, the step response and control effort histories, the steady-state tracking check and the control effort summary that gate a deadbeat digital control assessment. Trigger: deadbeat-control, finite-settling-time, pole-placement-at-origin, minimum-settling-time, z-domain-deadbeat."
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
  tags: [deadbeat-control, finite-settling-time, pole-placement-at-origin, minimum-settling-time, z-domain-deadbeat]
  version: 0.1.0
  author: AeroSkills
---

# Deadbeat Control (gnc-autonomy/control/deadbeat-control)

Use when the task is a direct deadbeat synthesis for a discrete-time
plant: the plant is already given as a pulse transfer function G(z) =
B(z)/A(z) (no discretization is performed here), and the controller
must place every closed loop pole at the origin of the z plane so the
step response settles in a finite number of sample periods. This leaf
implements the deadbeat response design of Franklin, Powell and Workman
(Digital Control of Dynamic Systems, ch. 4-5) and Ogata (Discrete-Time
Control Systems, ch. 6) in pure Python, stdlib only, deterministic and
offline. It pairs with digital-control-design for the sampled-data
toolbox that produces a discrete plant from a continuous one, and with
pid-control-design for the continuous-plant analogue of direct pole
placement.

## Domain quick reference

- Plant: G(z) = B(z)/A(z), coefficient lists in descending powers of z;
  A is normalized monic (scaled by A[0]); the plant must be strictly
  proper (deg B < deg A) and first or second order (1 <= deg A <= 2).
- Admissibility gate: deadbeat synthesis cancels the plant modes
  exactly, so every canceled mode must be strictly stable: every root
  of A and every root of B must have modulus strictly below 1.0. A pole
  or zero on or outside the unit circle makes the design inadmissible.
  Roots come from closed forms only (degree 1 and 2); degree 3 and
  higher is out of scope.
- Deadbeat controller: unity feedback D(z) = N_c(z)/D_c(z) = A(z)/(B(z)
  *(z^d - 1)) with relative degree d = deg A - deg B, the plant's pure
  sample delay. The closed-loop characteristic polynomial is
  A*D_c + B*N_c = A*B*z^d, so after the strictly-stable cancellations
  the observable closed loop is T(z) = z^-d: a pure d-sample delay,
  every closed-loop pole at the origin.
- Controller recursion on the tracking error: u(k) = sum_i num_e[i]*
  e(k - i) + sum_j den_u[j]*u(k - 1 - j), with num_e[i] = A[i]/mu0 and
  mu0 the leading coefficient of B; den_u comes from the coefficients
  of B(z)*(1 - z^-d) shifted by the relative degree d.
- Plant recursion for the closed-loop simulation (zero initial state):
  y(k) = -sum_i A[i]*y(k - i) + sum_j B[j]*u(k - d - j), advanced from
  past samples only.
- Deadbeat response: the step response reaches the reference exactly at
  sample d and holds it (settling time d*T_s); tracking error is
  exactly r for 0 <= k < d and exactly zero for k >= d.
- Steady-state tracking: the control that holds y = r is u* = A(1)/B(1)
  (the inverse of the plant DC gain). For a plant with no numerator
  zeros the control reaches u* exactly at sample d; a plant with an
  interior zero keeps the output deadbeat while the control converges
  geometrically to u* at the plant-zero rate.
- Sample time T_s is reporting-only: it converts sample counts to a
  time axis (settling time = d*T_s) and is never a design rule; the
  sample-rate selection rule belongs to digital-control-design.

## Workflow

1. Fix the plant: the pulse transfer function G(z) = B(z)/A(z) as
   descending-power coefficient lists, and confirm it is strictly
   proper and first or second order.
2. Verify admissibility with admissibility_check: every pole and zero
   modulus must be strictly below 1.0, using the closed-form roots from
   roots_moduli_desc.
3. Solve the deadbeat design equation with deadbeat_design: place every
   closed loop pole at the origin of the z plane and get the controller
   coefficients num_e, den_u, the z-domain controller d_num_desc and
   d_den_desc, and the pole-placement identity char_poly_desc.
4. Form the finite-settling-time controller difference equation from
   num_e and den_u (the causal recursion on the tracking error).
5. Simulate the closed loop with simulate under the pinned per-sample
   ordering to get the step response, tracking error and control
   sequence histories.
6. Read the settling sample and settling time from settling_report and
   confirm the output has settled (settled True).
7. Check the steady-state tracking with steady_control (u* = A(1)/B(1))
   and summarize the control sequence with control_effort.
8. Confirm the pure-delay identity with closed_loop_impulse: the
   closed-loop impulse response is a d-sample delay.
9. Confirm the deterministic checks with the contract test
   scripts/test_deadbeat_control.py.

## Worked example

Scenario A (first order, no zeros): G(z) = 0.5/(z - 0.5), A =
[1.0, -0.5], B = [0.5], T_s = 0.1 s, unit step r = 1.
- admissibility_check: admissible True, pole_moduli [0.5], zero_moduli
  [].
- deadbeat_design: n = 1, m = 0, d = 1; num_e = [2.0, -1.0],
  den_u = [1.0], mu0 = 0.5; controller recursion u(k) = 2.0*e(k) -
  1.0*e(k - 1) + 1.0*u(k - 1); u_star = 1.0.
- Step response reaches y = 1.0 exactly at sample 1 (settling time
  0.1 s) and holds it; error is 1.0 at sample 0 and 0.0 from sample 1
  on; control effort u = [2.0, 1.0, 1.0, ...], peak 2.0, u* = 1.0 from
  sample 1 on.

Scenario B (second order, no zeros): G(z) = 0.2/(z^2 - 1.1*z + 0.24),
A = [1.0, -1.1, 0.24], B = [0.2], T_s = 0.02 s, unit step r = 1.
- admissibility_check: pole_moduli [0.8, 0.3] (real anchors within
  1e-9 of these values), admissible True.
- deadbeat_design: n = 2, m = 0, d = 2; num_e = [5.0, -5.5, 1.2],
  den_u = [0.0, 1.0], mu0 = 0.2; char_poly_desc = [0.2, -0.22, 0.048,
  0.0, 0.0]; u_star within 1e-9 of 0.7, plant_dc_gain within 1e-6
  relative of 10/7.
- Step response reaches y = 1.0 at sample 2 (settling time 0.04 s) and
  holds it to float precision; error area sum(e) = d = 2 within 1e-6
  relative; control u = [5.0, -0.5, 0.7, 0.7, ...], peak 5.0, u* = 0.7
  from sample 2 on; the pole-placement identity A*D_c + B*N_c equals
  char_poly_desc within 1e-12; the closed-loop impulse response is a
  pure 2-sample delay.

Scenario C (interior zero, relative-degree generality): G(z) =
(0.1*z + 0.05)/(z^2 - 1.1*z + 0.24), A = [1.0, -1.1, 0.24],
B = [0.1, 0.05], T_s = 0.02 s, unit step r = 1.
- admissibility_check: pole_moduli [0.8, 0.3], zero_moduli [0.5], all
  admissible.
- deadbeat_design: n = 2, m = 1, d = n - m = 1: the interior zero
  shortens the minimum settling time; num_e = [10.0, -11.0, 2.4],
  den_u = [0.5, 0.5], mu0 = 0.1; u_star within 1e-9 of 14/15.
- Step response reaches y = 1.0 at sample 1 (settling time 0.02 s) and
  holds it; the OUTPUT is deadbeat from sample 1 while the CONTROL
  converges geometrically to u* at the plant-zero rate (control effort
  u(0) = 10.0, u(1) = -6.0, u(39) within 1e-6 relative of 14/15).

A complex-pole guard plant G(z) = 0.1/(z^2 - 1.6*z + 0.65) has pole
pair 0.8 +/- j*0.1, pole_moduli sqrt(0.65) approx 0.8062257748298549
(both entries), admissible True: the closed-form quadratic branch
covers complex poles.

## Verification

- Confirm admissibility_check returns the exact dict keys
  {'admissible', 'pole_moduli', 'zero_moduli', 'reason'} and matches
  the pole and zero moduli of scenarios A, B, C and the complex-pole
  guard plant.
- Confirm deadbeat_design on scenarios A, B and C matches the worked
  num_e, den_u, mu0 and u_star values within tolerance, and that the
  pole-placement identity A*D_c + B*N_c equals char_poly_desc = A*B*z^d
  within 1e-12.
- Confirm simulate reproduces the step response, error and control
  histories of the worked examples within tolerance, and that
  closed_loop_impulse gives a pure d-sample delay.
- Confirm deadbeat_design raises ValueError for an unstable plant, a
  pole or zero on the unit circle, a non-minimum-phase zero, a degree-3
  plant, a non-strictly-proper plant, an empty plant list and a zero
  leading A coefficient.
- Confirm simulate raises ValueError for a non-positive sample time, an
  unknown reference string, too few steps, and an inadmissible plant.
- Run the contract test offline: python3
  scripts/test_deadbeat_control.py (deterministic, no imports beyond
  math).

## Related leaves

- gnc-autonomy/control/digital-control-design: the sampled-data toolbox
  that discretizes a continuous plant with a zero-order hold and
  emulates a continuous compensator, the source of a discrete plant
  this leaf can then consume.
- gnc-autonomy/control/pid-control-design: continuous s-domain pole
  placement for a first or second order plant, the continuous analogue
  of the direct pole-placement idea used here in the z-domain.
- gnc-autonomy/control/state-space-analysis: eigenvalue and
  controllability context for the state-space view of a discrete plant.

## Pitfalls

- Feeding a continuous plant directly: this leaf never discretizes; the
  plant coefficients A and B must already be the pulse transfer
  function coefficients of a discrete-time plant (use
  digital-control-design first if the plant starts continuous).
- Skipping the admissibility gate: a plant with a pole or zero outside
  or on the unit circle cannot be canceled safely; deadbeat_design
  raises ValueError rather than returning a marginal design, since an
  uncanceled unstable mode would appear unbounded in the closed loop.
- Assuming the settling sample always equals the plant order: with an
  interior plant zero (scenario C) the settling sample is d = n - m,
  strictly less than n; only a plant with no numerator zeros settles at
  exactly n samples.
- Reading the control sequence as deadbeat too: only the OUTPUT is
  guaranteed to reach and hold the reference in d samples; when the
  plant has a zero, the control sequence itself converges geometrically
  to u* at the plant-zero rate rather than jumping to it.
- Treating T_s as part of the design: sample time only converts sample
  counts to a time axis (settling time = d*T_s); it never changes the
  controller coefficients and it is not a sample-rate selection rule.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_deadbeat_control.py

The test covers the admissibility truth table for scenarios A, B, C and
the complex-pole guard plant, the deadbeat design coefficients and the
pole-placement identity, the closed-loop step, error and control
histories of all three worked scenarios within tolerance, the
steady-state tracking identity, the pure-delay impulse identity,
determinism of repeated simulate runs, and ValueError rejection of
unstable, boundary, non-minimum-phase, degree-3 and non-strictly-proper
plants and of invalid simulate arguments.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard (name plus paraphrase only, per standards-map.yaml); the
  deadbeat design relations above are standard engineering methodology
  from Franklin, Powell and Workman and from Ogata, summary-only.
- compliance: STANDARDS-REF, gated: false.
