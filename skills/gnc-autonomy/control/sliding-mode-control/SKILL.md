---
name: sliding-mode-control
description: "Use when you must design a sliding-mode-control law for a second-order plant with matched uncertainty: choose the sliding surface from the tracking error and its derivative, compute the equivalent control that holds the surface on the nominal model, add the switching term sized above the uncertainty bound inside the boundary layer to enforce the reachability condition, and suppress chattering with the saturation thickness. Produces the surface and equivalent-control histories, the sliding-condition audit of the reachability inequality at every sample, the finite-time reach of the boundary layer, the boundary-layer command with the chattering-suppression check, and the tracking-error history that gate a sliding-mode control assessment. Trigger: sliding-mode-control, sliding-surface-design, equivalent-control, constant-plus-proportional-reaching-law, switching-term, chattering-suppression, matched-uncertainty, variable-structure-control, boundary-layer-command."
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
  tags: [sliding-mode-control, sliding-surface-design, equivalent-control, constant-plus-proportional-reaching-law, switching-term, chattering-suppression, matched-uncertainty, variable-structure-control, boundary-layer-command]
  version: 0.1.0
  author: AeroSkills
---

# Sliding-Mode Control (gnc-autonomy/control/sliding-mode-control)

Use when the task is variable-structure sliding-mode control of a
second-order plant with bounded matched uncertainty: driving the
tracking error onto a sliding surface and holding it there with an
equivalent-control term plus a boundary-layer switching term. The
plant model f_nom and the uncertainty bound F are given inputs, never
identified or estimated online, and the surface coefficient lambda and
the switching gain k are given design constants (k always equals F
plus the margin ETA, never tuned by search). It pairs with
pid-control-design, which tunes a linear P-I-D gain set rather than
switching on an error surface, and it never overlaps
adaptive-control or l1-adaptive-control, whose gains or adaptive
signals update online against an unknown plant coefficient while this
leaf's plant is fully known and nothing adapts.

## Domain quick reference

- Plant: second-order canonical x_ddot = f(x, v) + u with unit control
  effectiveness, f = f_nom + d, f_nom(x, v) = -v the known nominal
  drag model, d a constant matched disturbance with |d| <= F, F a
  given bound, d never measured. Velocity form: x_dot = v,
  v_dot = -v + d + u.
- Tracking error e = x - xd against the constant reference xd, so
  e_dot = v and xd_ddot = 0.
- Sliding surface s = e_dot + lambda e = v + lambda (x - xd), lambda >
  0 given. On s = 0 the error dynamics collapse to the stable
  first-order form e_dot = -lambda e with time constant 1/lambda.
- Equivalent control u_eq = -f_nom + xd_ddot - lambda e_dot, the
  control that holds s_dot = 0 on the nominal model (d = 0); worked
  closed form u_eq = (1 - lambda) v.
- Saturation sat(s/phi): s/phi inside the boundary layer |s| <= phi,
  sign(s) outside; phi = 0 gives the ideal sign switching used only as
  the chattering comparison.
- Switched term (constant-plus-proportional reaching law):
  u_sw = -k sat(s/phi), a constant rate -k sign(s) outside the layer
  and a proportional -k s/phi inside it. Full command u = u_eq + u_sw.
- Switching gain k > F required; the certified sliding margin is
  eta_cert = k - F, and the worked configuration always sets k = F +
  ETA with ETA the named margin constant.
- Sliding condition (1/2) d(s^2)/dt = s s_dot <= -eta |s| holds on
  every point with |s| > phi because s s_dot = s d - k |s| <= |s|(F -
  k) = -eta_cert |s|; outside the layer the surface reaches it in
  finite time, t_reach <= (|s0| - phi)/eta_cert.
- Boundary-layer equilibrium (constant d): inside the layer s_dot = d
  - (k/phi) s settles at s_ss = phi d/k, pinning the error at e_ss =
  s_ss/lambda and the steady command at u = -d, the saturated term
  continuously balancing the disturbance without sign flips.

## Workflow

1. Fix the plant and the design inputs: the known nominal model f_nom
   = -v, the matched-uncertainty bound F, the constant disturbance d
   with |d| <= F, the constant reference xd and the initial state.
   None of these is identified, estimated or adapted online.
2. Choose the sliding surface from the tracking error and its
   derivative with sliding_surface(err, err_dot, lam): s = e_dot +
   lambda e.
3. Compute the equivalent control that holds the surface on the
   nominal model with equivalent_control(f_nominal, ref_ddot, err_dot,
   lam): u_eq = -f_nom + xd_ddot - lambda e_dot.
4. Size the switching gain above the uncertainty bound, k = F + ETA,
   and form the boundary-layer switched term with switched_term(s, k,
   phi): u_sw = -k sat(s/phi), using sat_value for the saturation.
5. Simulate the closed loop with simulate_sliding_control and audit the
   sliding-condition margin with sliding_condition_margin(s, s_dot,
   eta) at every sample outside the layer: non-negative margin
   confirms the reachability inequality holds.
6. Read the finite-time reach of the boundary layer (reach_idx,
   reach_t) against the certified upper bound, and the boundary-layer
   equilibrium and surface-pinned tracking-error offset once the
   surface settles.
7. Check chattering suppression: compare the boundary-layer command
   (phi > 0) against the ideal sign switching (phi = 0) at the SAME
   gains, counting control jumps, the maximum step-to-step command
   change and surface sign changes after the reach.

## Worked example

Plant x_ddot = f + u, f = f_nom + d, f_nom = -v; constant matched
disturbance d = D at its bound (worked D = F = 0.5, robustness case D
= F = 0.9), |d| <= F, never measured. Design: lambda = 2.0 (1/s),
u_eq = (1 - lambda) v = -v, switching gain k = F + ETA with ETA = 1.5
(worked k = 2.0, robust k = 2.4, certified margin eta_cert = k - F =
1.5 in both), boundary-layer thickness phi = 0.05 (worked and
robust), ideal sign phi = 0.0 as the chattering comparison at the SAME
gains. Reference xd = 1.0, initial state x(0) = 0, v(0) = 0, so e(0)
= -1.0 and s(0) = -2.0. Forward Euler at dt = 0.001 s over 6.0 s
(6001 samples). All values below are real outputs of
scripts/sliding_mode_control_logic.py:

- Worked case (D = F = 0.5, k = 2.0, phi = 0.05): sliding_surface(-1.0,
  0.0, 2.0) = -2.0; initial command u(0) = u_eq(0) + k = 0 + 2.0 =
  2.0 because s(0) = -2.0 saturates the layer.
- Finite-time reach: first |s| <= phi at sample 781, t_reach =
  0.781000 s, against the constant-rate closed form (|s0| -
  phi)/(D + k) = 0.780000 s and inside the certified bound (|s0| -
  phi)/eta_cert = 1.300000 s.
- Surface-rate law identity: max |s_dot - (D - k sat(s/phi))| =
  4.441e-16 over the 6001 samples, the float witness that the
  equivalent control cancels the (lambda - 1) v term exactly.
- Sliding-condition audit: 781 samples with |s| > phi, worst margin
  0.050000000, 0 violations.
- Boundary-layer equilibrium: s(6.0) = 0.012500000 against phi D/k =
  0.012500000; e(6.0) = 0.006234758 against phi D/(k lambda) =
  0.006250000; x(6.0) = 1.006234758; u(6.0) = -0.500030484 against
  -D = -0.500000000. Post-transient: max |s - s_ss| for t >= 2.0 s
  is 0.000000000; max |e - e_ss| for t >= 4.0 s is 0.000835525; the
  steady-command identity max |u + D + v| for t >= 4.0 s is 7.675e-14.
- Surface error-dynamics identity: (e(1.2) - e_ss)/(e(0.9) - e_ss) =
  0.548498 and (e(1.5) - e_ss)/(e(1.2) - e_ss) = 0.548482, both
  against exp(-lambda 0.3) = 0.548812: once the surface pins the
  layer, the error approaches e_ss at rate lambda with no overshoot.
- Chattering suppression: worked saturation case has 0 control jumps
  (|du| > 0.5 after reach), max |du| = 0.100524520, and 1 s sign
  change after reach. The SAME gains with phi = 0 (ideal sign) chatter:
  3690 control jumps, max |du| = 4.002601733, 3668 sign changes, mean
  |u| over [4.0, 6.0] s = 2.001024 against 0.500410 for the worked
  saturation.
- Robustness case (D = F = 0.9, k = 2.4, phi = 0.05): eta_cert =
  1.500000000, t_reach = 0.591000 s inside the certified bound
  1.300000 s, 591 outside samples with worst margin 0.095400000 and 0
  violations, s(6.0) = 0.018750000, e(6.0) = 0.009362949, u(6.0) =
  -0.900024101, 0 control jumps and max |du| = 0.158705197.
- ValueErrors (real messages): sliding_surface(0.1, 0.0, 0.0) raises
  "surface coefficient lambda must be positive, got 0.0";
  sat_value(0.1, -0.05) raises "boundary-layer thickness phi must be
  non-negative, got -0.05"; switched_term(0.1, 0.0, 0.05) raises
  "switching gain k must be positive, got 0.0";
  simulate_sliding_control(k=0.5, bound_f=0.5) raises "switching gain
  k must exceed the matched-uncertainty bound F, got k 0.5 <= F 0.5";
  simulate_sliding_control(disturbance_d=0.6) raises "disturbance
  magnitude D must not exceed the matched-uncertainty bound F, got D
  0.6 > F 0.5".

## Verification

- Confirm the closed-form surface and saturation anchors:
  sliding_surface(-1.0, 0.0, 2.0) = -2.0, sat_value(0.0125, 0.05) =
  0.25 (a quarter into the layer), sat_value saturates at +/-1 outside
  the layer and returns the ideal sign at phi = 0.
- Confirm the surface-rate law identity holds to float noise over the
  whole worked run, and that the sliding-condition margin is
  non-negative on every sample outside the layer with zero violations
  in both the worked and robustness cases.
- Confirm the finite-time reach against the constant-rate closed form
  and the certified upper bound in both cases, and the boundary-layer
  equilibrium and surface-pinned error offset at the worked sample
  points.
- Confirm the chattering-suppression contrast between the
  boundary-layer command and the ideal sign switching at the SAME
  gains: zero jumps and one sign change for the saturated case against
  thousands of jumps and sign changes for the ideal sign case.
- Confirm ValueError rejection of a non-positive lambda, a negative
  phi, a non-positive k, a negative bound F, a switching gain at or
  below F, a disturbance beyond the bound F, and a non-positive dt or
  sim_time, with the real messages quoted in the Worked example.
- Run the contract test offline:
  python3 scripts/test_sliding_mode_control.py (deterministic, no
  imports beyond math, no exact-float equality on any computed sum).

## Related leaves

- gnc-autonomy/control/adaptive-control: designs a model-reference
  adaptive controller whose gains update online against an unknown
  plant coefficient; this leaf's plant model and uncertainty bound are
  known inputs and nothing adapts online.
- gnc-autonomy/control/l1-adaptive-control: runs a state predictor and
  a projection-based adaptation law through a low-pass filter; this
  leaf runs no predictor, no projection and no filter, and its bound F
  only sizes the switching gain.
- gnc-autonomy/control/pid-control-design: tunes P-I-D gains by
  Ziegler-Nichols or pole placement with anti-windup and margin
  checks; this leaf never tunes, its lambda, k and phi are given
  design inputs and k only ever takes the closed form F + ETA.
- gnc-autonomy/control/gain-scheduling: interpolates a family of
  linear gains across a flight-envelope scheduling variable; this
  leaf's surface coefficients and switching gain are fixed constants
  and the discontinuity is a function of the error state, not of a
  scheduling variable.
- gnc-autonomy/control/h-infinity-control: reviews the worst-case
  H-infinity norm of a linear feedback loop with the controller given;
  this leaf synthesizes a nonlinear time-domain switching command and
  runs no frequency sweep or norm computation.
- gnc-autonomy/control/deadbeat-control: places every closed-loop pole
  at the origin of the z plane from a discrete pulse-transfer model;
  this leaf runs a forward-Euler continuous-time simulation with a
  surface on the error and its derivative, never a z-domain design.

## Pitfalls

- Reading this leaf as an estimator or an adaptive law: the nominal
  model f_nom, the uncertainty bound F and the disturbance d are all
  given inputs, d is never measured or reconstructed, and nothing
  updates online (that territory belongs to adaptive-control and
  l1-adaptive-control).
- Tuning lambda or k by search: both are given design constants, and k
  always takes the closed form F + ETA above the uncertainty bound,
  never a margin-based or Ziegler-Nichols search (pid-control-design
  territory).
- Setting phi = 0 in production: the ideal sign switching is the
  chattering comparison only; it produces thousands of control jumps
  at the sample rate on the same gains that the boundary layer holds
  continuous.
- Sizing k at or below F: the switching gain must strictly exceed the
  uncertainty bound (k > F) or the sliding condition and the
  finite-time reach guarantee both fail; simulate_sliding_control
  rejects k <= F with a ValueError.
- Expecting exact sliding on s = 0: the boundary layer trades the
  ideal surface for a continuous command, and motion is only
  guaranteed inside |s| <= phi after the finite-time reach, not
  exactly on s = 0.
- Feeding a disturbance magnitude larger than the declared bound F:
  the switching gain is only certified against |d| <= F, and
  simulate_sliding_control rejects |disturbance_d| > bound_f with a
  ValueError.

## Behavior contract (gate 3)

The sliding-surface, equivalent-control, switched-term, sliding-
condition-margin and closed-loop simulation logic is exercised by the
gate 3 contract test: scripts/test_sliding_mode_control.py against
scripts/sliding_mode_control_logic.py (stdlib unittest, offline,
deterministic, 36 test methods). Run:

    python3 scripts/test_sliding_mode_control.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only, per
  standards-map.yaml, as the reference-only control-pack convention
  shared with pid-control-design, digital-control-design,
  observer-design, deadbeat-control, smith-predictor and
  h-infinity-control.
- compliance: STANDARDS-REF, gated: false.
