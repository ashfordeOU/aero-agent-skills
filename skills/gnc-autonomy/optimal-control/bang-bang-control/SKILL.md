---
name: bang-bang-control
description: "Use when you must compute the time-optimal bang-bang control of a double integrator: the switching curve s = x + v|v|/(2a), the bang-bang command u = -a*sign(s) under a hard input limit |u| <= a, the exact rest-to-rest maneuver time T* = 2*sqrt(d/a), the switch point at half distance with velocity -sqrt(a*d), and the general minimum-time trajectory for nonzero initial velocity. Produces the switch point, the command profile and the maneuver time for single-axis attitude slew and translation bang-bang assessments under torque or rate limits. Trigger: bang bang control, time optimal control, switching curve, minimum time maneuver, rest to rest slew, double integrator, bounded input, torque limit, rate limit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: optimal-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [bang-bang-control, time-optimal-control, switching-curve, minimum-time-maneuver, double-integrator, rest-to-rest-slew, bounded-input-control]
  version: 0.1.0
  author: AeroSkills
---

# Bang-Bang Control (gnc-autonomy/optimal-control/bang-bang-control)

Use when the task is minimum-time (time-optimal) control of a double
integrator under a hard input limit: deriving the bang-bang switching
curve, evaluating the bang-bang command from the switching function,
and sizing the exact rest-to-rest maneuver time, switch point and
general two-leg minimum-time profile. This leaf implements the
Pontryagin-style bang-bang law in pure Python, stdlib only. It pairs
with the gnc-autonomy optimal-control siblings: lqr-design for the
quadratic full-state feedback law without limits, and
model-predictive-control for the receding-horizon formulation.

## Domain quick reference

- Plant and limit: x_ddot = u with |u| <= a, a > 0 the acceleration
  (angular acceleration) limit. A maneuver drives (x, v) to rest at
  the origin in minimum time; a rest-to-rest move over distance d
  starts at x = d with v = 0.
- Switching function: s(x, v) = x + v*|v|/(2a). The switching curve
  s = 0 separates the plane; from any point on it one constant
  command rides the double integrator to rest at the origin.
- Bang-bang law: u = -a*sign(s), returning -a, 0.0 or +a. Convention:
  sign(0) = 0, so a state exactly on the curve commands 0.0; the
  curve crossing is a single instant and does not change the
  maneuver time. s > 0 commands -a (steer toward the origin), s < 0
  commands +a.
- Rest-to-rest over distance d: T* = 2*sqrt(d/a), switch at
  t_s = sqrt(d/a) with x_s = d/2 and v_s = -sqrt(a*d): accelerate
  toward the origin for half the distance, then ride the curve.
- General minimum time from (x0, v0): analytic two-leg solution with
  at most one switch. Above the curve (s > 0): command -a for
  t1 = (v0 + sqrt(a*x0 + v0^2/2))/a onto the lower branch
  (x_s = x0/2 + v0^2/(4a), v_s = -sqrt(a*x0 + v0^2/2)), then +a to
  the origin. Below the curve (s < 0): the mirror image with +a then
  -a. A state on the curve rides it to the origin in one leg.
- Braking-waypoint reading: with v0 > 0 above the curve the first leg
  passes through rest (brake to rest, then return), so the total time
  is v0/a plus the rest-to-rest time from the waypoint.
- Units are SI: m, m/s, m/s^2 (or rad, rad/s, rad/s^2 for a slew).
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the bang-bang relations above are standard
  control-theory knowledge, summary-only.

## Workflow

1. State the plant in double-integrator form: distance d (or angular
   error theta0 for a slew) and the hard limit a from the torque or
   rate constraint.
2. For a rest-to-rest move, get the maneuver time with
   min_time_rest_to_rest(d, a) and the switch point with
   switch_state(d, a): switch_time_s, switch_position and
   switch_velocity.
3. For a general start state (x0, v0), run min_time_state(x0, v0, a)
   for the analytic two-leg profile: total_time, switch_time,
   switch_position, switch_velocity and command_phases, each leg a
   (command, duration) pair whose durations sum to total_time.
4. Evaluate the sampled feedback law with bang_bang_command(x, v, a)
   when you must step the profile (the law is -a above the curve, +a
   below, 0.0 on it).
5. Check the switching function with switch_curve(x, v, a) to confirm
   which side of the curve a state is on.
6. For the complete maneuver record, run bang_bang_summary(x0, v0, a)
   for x0, v0, accel_limit, switching_function_0 plus all
   min_time_state fields.
7. Confirm the deterministic checks with the contract test
   scripts/test_bang_bang_control.py.

## Worked example

Rest-to-rest, d = 100 m, a = 1 m/s^2:

- min_time_rest_to_rest(100.0, 1.0) = 20.0 s exactly.
- switch_state(100.0, 1.0) = {switch_time_s: 10.0,
  switch_position: 50.0, switch_velocity: -10.0}, exactly T*/2,
  d/2 and -sqrt(a*d). The first leg commands -1.0 m/s^2, the second
  rides the switching curve with +1.0 m/s^2 to rest.

Slew frame, theta0 = 2 rad, alpha = 0.05 rad/s^2:

- min_time_rest_to_rest(2.0, 0.05) = 12.6491106 s, about 12.649111 s
  (2*sqrt(2/0.05)).

Generic start, x0 = 50 m, v0 = +5 m/s, a = 1 m/s^2:

- min_time_state(50.0, 5.0, 1.0): total_time = 20.8113883 s, the
  analytic value 5 + 2*sqrt(62.5) about 20.810 s. The first leg
  commands -1.0 for 12.905694 s, braking through rest at 62.5 m at
  t = 5 s (the waypoint) and accelerating back, switching at
  x = 31.25 m with v = -7.905694 m/s on the lower branch; the second
  leg commands +1.0 for 7.905694 s, riding the curve into the origin.
- A stepping simulation of bang_bang_command sampled at 1e-4 s lands
  at the origin within 1e-2 s of position and speed at the analytic
  total time, and within 1e-3 when started from the switch point.

## Verification

- Confirm min_time_rest_to_rest(100, 1) returns 20.0 exactly and that
  d = 0 returns 0.0; negative d and non-positive a raise ValueError.
- Confirm switch_state(100, 1) returns exactly (10.0, 50.0, -10.0).
- Confirm the slew time 2*sqrt(2/0.05) about 12.649111 s and the
  generic total about 20.810 s = 5 + 2*sqrt(62.5).
- Confirm bang_bang_command is -a on one side of the switching curve,
  +a on the other, and 0.0 exactly on it (sign(0) = 0 convention).
- Confirm min_time_state(d, 0, a) reproduces min_time_rest_to_rest
  and switch_state for the same d, and that the command-leg durations
  sum to total_time.
- Confirm every convenience dict exposes exactly its documented keys
  and that repeated calls are identical (deterministic).
- Run the contract test offline: python3
  scripts/test_bang_bang_control.py (27 tests, deterministic).

## Pitfalls

- Reading the sign of the law backwards: s(x, v) = x + v*|v|/(2a) with s > 0
  commands -a and s < 0 commands +a; the convention sign(0) = 0 returns 0.0
  exactly on the curve (a single instant that does not change maneuver
  time).
- Quoting the rest-to-rest time with the wrong limit: T* = 2*sqrt(d/a) with
  the switch at exactly d/2 and v_s = -sqrt(a*d) (20 s, 10 s switch, -10 m/s
  at d = 100, a = 1); the acceleration limit a is the hard input bound, not
  a tuned gain.
- Expecting one leg from every start: a generic state above the curve needs
  a first leg that can pass through rest (brake to rest at the waypoint,
  then return) before the second leg rides the curve; at most one switch
  total.
- Using the slew frame numbers in the translational frame: the same law
  sizes angular slews with theta0 and alpha (2*sqrt(2/0.05) = 12.649 s for
  theta0 = 2 rad, alpha = 0.05 rad/s2) - keep rad and rad/s2 straight.
- The stepping simulation is the check: bang_bang_command sampled at 1e-4 s
  lands within 1e-2 s of the analytic total time (1e-3 when started from the
  switch point); min_time_state(d, 0, a) must reproduce
  min_time_rest_to_rest.
- Negative d and non-positive a raise ValueError; the convenience dicts
  expose exactly their documented keys deterministically.

## Related leaves

- gnc-autonomy/optimal-control/lqr-design: quadratic full-state
  feedback sibling; this leaf owns the hard-limit time-optimal law.
- gnc-autonomy/optimal-control/model-predictive-control: the
  receding-horizon formulation for constrained plants.
- gnc-autonomy/control/pid-control-design: feedback loops with
  integrator anti-windup, the non-optimal alternative.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_bang_bang_control.py

The test covers the 100 m rest-to-rest anchor (20.0 s exact, switch at
(10.0 s, 50.0 m, -10.0 m/s)), the 2 rad slew anchor (about 12.649111
s), the generic (50 m, +5 m/s) anchor (about 20.810 s = 5 +
2*sqrt(62.5)), stepping-simulation cross-checks of the sampled
bang-bang command against the analytics (origin within 1e-3 from the
switch state, within 1e-2 from the generic start), command polarity
across the switching curve, the sign(0) = 0 convention, exact
convenience-dict key sets, determinism, and ValueError rejection of
non-positive a and negative d.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true. The double-integrator
  bang-bang relations above are standard control-theory methodology,
  summary-only.
- compliance: STANDARDS-REF, gated: false.
