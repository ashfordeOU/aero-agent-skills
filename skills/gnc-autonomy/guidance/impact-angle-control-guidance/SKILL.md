---
name: impact-angle-control-guidance
description: "Use when you must compute the impact-angle-control-guidance command for a planar intercept against a stationary target with a commanded terminal flight path angle: the collision-course nulling baseline from the crossrange offset, the crossrange velocity and the time to go, the terminal crossrange velocity that realizes the commanded impact angle, the impact-angle error between the commanded terminal flight path angle and the current flight path angle, and the impact-angle-error-feedback bias that reshapes the intercept path so the interceptor meets the target at the commanded impact angle. Produces the total lateral acceleration command with its nulling baseline, bias term, time-to-go estimate and impact-angle error. Trigger: impact angle control, terminal impact angle, commanded impact angle, impact angle error feedback, terminal flight path angle constraint, angle-constrained intercept, impact angle guidance, ryoo cho tahk."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: guidance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: guidance
  tags: [impact-angle-control-guidance, terminal-impact-angle, commanded-impact-angle, impact-angle-error-feedback, terminal-flight-path-angle-constraint]
  version: 0.1.0
  author: AeroSkills
---

# Impact-Angle-Control Guidance (gnc-autonomy/guidance/impact-angle-control-guidance)

Use when the task is computing the impact-angle-control guidance command
for a planar terminal intercept against a stationary target with a
commanded terminal flight path angle: the proportional-navigation-like
collision-course nulling baseline from the crossrange offset, the
crossrange velocity and the time-to-go, the terminal crossrange velocity
that realizes the commanded impact angle, the impact-angle error between
the commanded terminal flight path angle and the current flight path
angle, and the impact-angle-error-feedback bias that reshapes the
intercept path so the interceptor meets the target at the commanded
impact angle. This is the energy-optimal impact-angle-constrained
guidance structure of the Ryoo-Cho-Tahk family (Ryoo, Cho and Tahk,
"Optimal Guidance Laws with Terminal Impact Angle Constraint," Journal of
Guidance, Control, and Dynamics 28(4):724-732, 2005, summarized by name
and paraphrase only, never reproduced). Pairing leaves:
proportional-navigation owns the unaugmented planar PN law,
augmented-proportional-navigation the maneuvering-target augmentation,
impact-time-control-guidance the time-constrained member of the same
terminal-law family; midcourse-guidance handles waypoint steering and
handover; impact-point-prediction is open-loop ballistic prediction.

## Domain quick reference

- Planar terminal intercept against a stationary target: speed V (m/s),
  current flight path angle gamma (rad), commanded terminal flight path
  angle gamma_f (rad), crossrange offset y (m), crossrange velocity
  component v_perp (m/s), time-to-go t_go (s).
- Crossrange velocity: v = V * sin(gamma); the terminal crossrange
  velocity v_f = V * sin(gamma_f) is the crossrange velocity that realizes
  the commanded impact angle.
- Time-to-go: t_go = range_to_target / closing_speed (exact on the
  collision course).
- Impact-angle error: e_g = gamma_f - gamma.
- Collision-course nulling baseline: a_base = -W_Y * (y + v_perp * t_go) /
  t_go^2, zero when the interceptor is already on the collision course (y
  + v_perp * t_go = 0). W_Y = 6.0.
- Impact-angle-error-feedback bias: a_bias = 2.0 * (v - v_f) / t_go,
  positive when the current crossrange velocity exceeds the terminal one
  (a steeper terminal dive must first be set up), negative when the
  commanded course is shallower.
- Total command: a_cmd = a_base + a_bias.

## Workflow

1. Fix the engagement state: speed V, current flight path angle gamma,
   commanded terminal flight path angle gamma_f, crossrange offset y,
   crossrange velocity v_perp and time-to-go t_go. Non-physical inputs
   are rejected with ValueError (non-positive speed, non-positive closing
   speed or negative range in the time-to-go estimate, non-positive
   time-to-go in the bias and baseline).
2. Compute the crossrange velocity with crossrange_velocity(speed,
   gamma): v = speed * sin(gamma). The same function gives the terminal
   crossrange velocity v_f from the commanded terminal flight path angle.
3. Estimate the time-to-go with tgo_estimate(closing_speed,
   range_to_target): t_go = range_to_target / closing_speed.
4. Form the impact-angle error with impact_angle_error(commanded_gamma,
   gamma): e_g = commanded_gamma - gamma.
5. Compute the impact-angle-error-feedback bias with
   impact_angle_bias(speed, tgo, gamma, commanded_gamma): a_bias = 2.0 *
   (v - v_f) / tgo.
6. Compute the collision-course nulling baseline with
   collision_nulling_baseline(tgo, crossrange_offset, v_perp): a_base =
   -W_Y * (crossrange_offset + v_perp * tgo) / tgo^2.
7. Sum the baseline and the bias with impact_angle_guidance_command(tgo,
   crossrange_offset, v_perp, speed, gamma, commanded_gamma), which
   returns (a_cmd, a_base, a_bias, t_go, e_g): the total lateral
   acceleration command, its collision-course nulling baseline, the
   impact-angle-error bias, the time-to-go estimate and the impact-angle
   error.
8. Confirm the deterministic checks with the contract test
   scripts/test_impact_angle_control_guidance.py.

## Worked example

All values are REAL outputs of the logic module at the spec anchor state
(stationary target at the origin, interceptor at range R = 10000.0 m,
line of sight 30 deg below the horizontal, V = 300.0 m/s, gamma_0 = -30
deg, commanded terminal flight path angle gamma_f = -60 deg, crossrange
offset y_0 = +5000.0 m, closing speed V_c = 300.0 m/s on the collision
course):

- tgo_estimate(300.0, 10000.0) = 33.333333333333 s
- crossrange_velocity(300.0, -30 deg) = -150.000000000000 m/s
- crossrange_velocity(300.0, -60 deg) = -259.807621135332 m/s
- impact_angle_error(-60 deg, -30 deg) = -0.523598775598 rad
  (-30.000000000000 deg)
- collision_nulling_baseline(33.333333333333, 5000.0, -150.0) =
  -0.000000000000 m/s^2 (the interceptor starts on the collision course:
  y_0 + v_0 * t_go0 = 0)
- impact_angle_bias(300.0, 33.333333333333, -30 deg, -60 deg) =
  6.588457268120 m/s^2
- impact_angle_guidance_command(33.333333333333, 5000.0, -150.0, 300.0,
  -30 deg, -60 deg) = (6.588457268120, -0.000000000000, 6.588457268120,
  33.333333333333, -0.523598775598)

Zero-error identity: at gamma equal to the commanded terminal flight path
angle the bias is exactly 0 and the command collapses to the
collision-course nulling baseline alone. Terminal straight course: at
t_go = 10 s with v = v_f and the crossrange offset set to -v_f * t_go
(2598.076211353 m), both the baseline and the bias vanish and the total
command is 0.000000000000 m/s^2. Bias linearity: doubling the speed at
the worked-example geometry doubles the bias magnitude to
13.176914536240 m/s^2. Shallowing-command bias (gamma = -60 deg,
commanded -10 deg) = -12.462790070115 m/s^2.

## Verification

- Deterministic stdlib math only; no RNG, no network, no numeric
  integration in the leaf (the fixed-step Euler checks live in the
  contract test as test-side identity probes, not as a leaf capability).
- ValueErrors: non-positive speed in crossrange_velocity, impact_angle_bias
  and impact_angle_guidance_command; non-positive closing speed or
  negative range in tgo_estimate; non-positive time-to-go in
  impact_angle_bias, collision_nulling_baseline and
  impact_angle_guidance_command.
- Identities: zero impact-angle error gives zero bias and the command
  equal to the collision-course baseline alone; the collision-course
  offset gives a zero baseline; the terminal straight course gives a zero
  total command; doubling the speed at fixed geometry and angles doubles
  the bias magnitude; two identical calls return bit-identical results.
- Linear-model closed-loop check: fixed-step Euler integration of the
  linearized crossrange kinematics under the closed-form law drives the
  crossrange velocity to within 0.05 m/s of the terminal crossrange
  velocity and the offset to within 1.0 m of zero as the time-to-go
  approaches zero.
- Nonlinear planar engagement check: fixed-step Euler integration of the
  point-mass kinematics under the law (dt = 0.005, speed 300 m/s,
  stationary target, stop at range <= 0.5 m) reaches the target at
  flight time 33.885000 s with miss range 0.096219 m and a terminal
  flight path angle of -60.037102 deg against the -60.000000 deg
  command (terminal-angle error -0.037 deg); the terminal angle stays
  in the [-61.0, -59.0] deg band from dt = 0.005 down to dt = 0.001.
  The max sampled command 1436.184250 m/s^2 occurs in the final
  tgo -> 0 step at range ~1.4 m, the terminal singularity of the
  time-to-go polynomial command (commands stay below ~55 m/s^2 while
  the range is >= 50 m); the identity asserted is the terminal flight
  path angle, not the singular command.

## Related leaves

- gnc-autonomy/guidance/proportional-navigation (the unaugmented planar
  PN law whose collision-course structure this baseline mirrors)
- gnc-autonomy/guidance/augmented-proportional-navigation
  (maneuvering-target augmentation of the PN baseline)
- gnc-autonomy/guidance/impact-time-control-guidance (the time-constrained
  member of the same terminal-law family, salvo and simultaneous-impact
  arrival)
- gnc-autonomy/guidance/midcourse-guidance (waypoint steering, handover,
  trajectory shaping)
- gnc-autonomy/guidance/impact-point-prediction (open-loop unguided
  ballistic impact prediction)

## Pitfalls

- Do not claim the standalone proportional-navigation law itself: this
  leaf forms a collision-course nulling baseline from the given
  engagement geometry, but the PN law, its capture conditions and its
  variants belong to the proportional-navigation sibling.
- Do not add impact-time or salvo control: impact-time-control-guidance
  owns the time-constrained member of the terminal-law family; this leaf
  is angle-only.
- The bias and baseline are deterministic at the given engagement state;
  this is not a trajectory propagator. The fixed-step Euler checks in the
  contract test are test-side identity probes, not a leaf capability, and
  the time-to-go polynomial command has a terminal singularity as t_go
  approaches zero that a real implementation would saturate at an
  actuator limit.
- Keep the speed and the time-to-go strictly positive; both are enforced
  with ValueError.
- Do not use single-word generic tags (guidance, control, navigation,
  intercept): they would steal corpus tasks from the family router rows.

## Behavior contract (gate 3)

The contract test
scripts/test_impact_angle_control_guidance.py (stdlib unittest, offline,
deterministic) verifies: the worked-example crossrange velocities,
time-to-go, impact-angle error, baseline, bias and total command within
1e-9 relative; the zero-error identity (bias zero, command equal to the
baseline); the collision-course identity (baseline zero); the terminal
straight-course identity (total command zero); the ValueError rejections
(non-positive speed, non-positive closing speed, negative range,
non-positive time-to-go); boundary behavior (zero range gives zero
time-to-go); the sign physics of the bias for steeper and shallower
commanded angles; the linearity of the bias in speed; determinism of
repeated calls; the linear-model closed-loop convergence to the terminal
crossrange velocity and offset; and the nonlinear planar engagement
identity probe showing the terminal flight path angle lands within the
anchor's band of the commanded angle. The test passes under both
/usr/bin/python3 and the pyenv 3.13 interpreter; no exact-float equality
is asserted on computed sums.

## Compliance

STANDARDS-REF, gated false. ARP4754A (reference-only) frames development
assurance for guided systems; the impact-angle-control law itself is
paraphrased public guidance-theory literature (Ryoo, Cho and Tahk 2005)
and is never reproduced verbatim.
