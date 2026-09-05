---
name: midcourse-guidance
description: "Use when a task asks how to reach an intermediate condition before final intercept, how much speed remains to be gained, or when to hand off to terminal guidance. Shape the midcourse flight of an interceptor or guided vehicle between launch and terminal handover: steer through a planned waypoint with a turn-rate-limited heading law, compute the velocity-to-be-gained speed deficit along the desired course, evaluate the zero-effort-miss of the closing geometry, size the handover condition that passes control to terminal guidance such as proportional navigation, and shape ascent trajectories with gravity-compensated commands. Trigger: midcourse guidance, waypoint steering, trajectory shaping, velocity-to-be-gained, zero-effort-miss, handover condition, turn-rate limit, gravity-compensated ascent."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: guidance
  tags: [midcourse-guidance, waypoint-steering, trajectory-shaping, velocity-to-be-gained, zero-effort-miss, handover-condition, turn-rate-limit, gravity-compensated-ascent, intercept-guidance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Midcourse Guidance (gnc-autonomy/guidance/midcourse-guidance)

Use when the task is steering a guided vehicle or interceptor through
the midcourse phase between launch and terminal handover: reaching a
planned waypoint or constraint geometry, shaping the trajectory, sizing
the speed deficit and the miss distance of the closing geometry, and
deciding when terminal guidance takes over.

## Domain quick reference

Midcourse guidance steers to a planned intermediate condition (a
waypoint, a constraint corridor, a handover geometry) rather than to
the target directly; a terminal law (proportional navigation, pursuit,
command-to-line-of-sight) then owns the final intercept. Planar model:
vehicle at position p = (px, py) with speed V and heading psi, waypoint
w = (wx, wy), turn-rate limit omega_max, guidance step dt. Angles are
radians; units are m, s, m/s, rad, rad/s, m/s^2.

- Desired course: psi_d = atan2(wy - py, wx - px). Worked anchor:
  p = (0, 0), w = (1000, 500) gives psi_d = 26.565 deg.
- Course error: e = wrap(psi_d - psi) into (-pi, pi]. Same anchor with
  psi = 0 gives e = +26.565 deg; with psi = 45 deg gives e = -18.435
  deg (the wrap keeps the short way around).
- Turn-rate-limited steering:
  psi_c = psi + clamp(e, -omega_max * dt, +omega_max * dt). Anchor:
  omega_max = 5 deg/s, dt = 1 s clamps the commanded turn to 5 deg per
  step although e = 26.565 deg; omega_max = 30 deg/s lets the full
  error through and psi_c = psi_d in one step.
- Velocity-to-be-gained: vgo = max(0, V_target - V * cos(e)), the
  speed deficit along the desired course after the heading error is
  removed. Anchor: V = 250 m/s, e = 20 deg, V_target = 300 m/s gives
  vgo = 300 - 234.92 = 65.08 m/s; at e = 0 the same anchor gives
  vgo = 50 m/s.
- Zero-effort-miss for a constant-velocity closing geometry: relative
  position rho = r_t - r_i, relative velocity v_rel = v_t - v_i,
  time-to-go t_go = -(rho . v_rel) / |v_rel|^2 clamped to >= 0, and
  ZEM = |rho + v_rel * t_go|, the miss distance at closest approach if
  nothing changes. Anchor: interceptor at (0, 0) at 300 m/s along +x,
  stationary target at (6000, 150) gives t_go = 20 s and ZEM = 150 m;
  target at (9000, 0) at 100 m/s along +x gives t_go = 45 s and
  ZEM = 0 (perfect intercept geometry).
- Handover condition: hand off to terminal guidance when the closing
  range reaches the handoff range R_ho, or when t_go falls below the
  terminal acquisition time. Anchor: closing speed Vc = 1000 m/s and
  seeker acquisition at 8 km gives handover at t_go = 8 s; the
  midcourse law must have driven ZEM inside the seeker capture radius
  by then.
- Gravity-compensated ascent shaping: normal acceleration to track a
  flight path angle program,
  a_c = V * gamma_dot_c + g * cos(gamma), the second term holding the
  climb up against gravity. Anchor: V = 300 m/s,
  gamma_dot_c = 0.5 deg/s, gamma = 30 deg, g = 9.81 m/s^2 gives
  a_c = 2.62 + 8.50 = 11.11 m/s^2.
- FAR-25 and CS-25 (reference-only) frame flight control system
  certification context for transport airplanes; the shaping laws
  themselves are common guidance knowledge.

## Workflow

1. Confirm the phase: midcourse steers to a planned intermediate
   condition. If the task is direct target capture, use the terminal
   law leaves (proportional-navigation, pursuit-guidance,
   command-to-line-of-sight) instead.
2. Define the geometry: waypoint or constraint positions in meters,
   headings in radians.
3. Compute desired_heading(position, waypoint) and
   course_error(position, waypoint, heading); the error is wrapped to
   (-pi, pi].
4. Apply the turn-rate limit with commanded_heading(position, waypoint,
   heading, omega_max, dt); while the error exceeds omega_max * dt the
   vehicle banks at the limit and the error shrinks step by step.
5. Compute velocity_to_be_gained(speed, course_error_angle,
   speed_target) for the speed deficit along the course, and
   zero_effort_miss(interceptor_pos, interceptor_vel, target_pos,
   target_vel) to check the intercept line before handover.
6. Check handover_check(interceptor_pos, target_pos, handoff_range);
   hand off only when ZEM is already inside the terminal capture
   radius, otherwise the terminal law starts with a large miss.
7. For ascent phases add the gravity compensation term
   gravity_compensated_accel(speed, flight_path_rate,
   flight_path_angle, g) and state the model limits: flat earth, no
   drag, no wind; real trajectories need a 3-DOF or 6-DOF simulation.

## Pitfalls

- Confusing midcourse guidance with proportional-navigation: PN is the
  terminal law commanding acceleration from closing velocity and
  line-of-sight rate at the target; midcourse steers to a planned
  intermediate condition and hands off before PN takes over.
- Confusing with pursuit-guidance: pursuit aims the interceptor
  velocity at the target with a capture condition; midcourse never
  aims at the target during the shaping phase.
- Confusing with command-to-line-of-sight: CLOS holds the missile on
  the tracker-to-target line; midcourse steering has no tracker line.
- Confusing with impact-point-prediction: that leaf is open-loop
  ballistic geometry for where an unguided round lands; midcourse
  guidance is closed-loop steering of a guided vehicle.
- Confusing with lqr-design: LQR derives an optimal state-feedback
  gain from cost weights over a linear model; midcourse shaping laws
  are simple explicit steering and energy functions, not optimal
  controllers.
- Forgetting the wrap: the course error must be wrapped to (-pi, pi],
  or a small geometric error turns the vehicle the long way around.
- Mixing degrees and radians: atan2, the turn clamp, and the wrap all
  work in radians.
- Negative velocity-to-be-gained: clamp vgo at zero; a vehicle already
  faster than the speed target has nothing to gain.
- t_go sign in ZEM: for a receding geometry (rho . v_rel > 0) the
  closest approach is in the past; clamp t_go to >= 0 and report the
  ZEM at the current point.
- Handing off too early or too late: handover before ZEM is inside the
  capture radius gives the terminal law a large initial miss; handover
  after the acquisition time wastes seeker tracking.
- Dropping gravity compensation in ascent: without the g * cos(gamma)
  term the shaped climb droops under gravity.

## Behavior contract (gate 3)

The waypoint steering law, velocity-to-be-gained, zero-effort-miss,
turn-rate clamping, gravity-compensated ascent acceleration, handover
check, and the demonstration are exercised by the gate 3 contract test:
scripts/test_midcourse_guidance.py against
scripts/midcourse_guidance_logic.py (stdlib unittest, offline). Run:
python3 skills/gnc-autonomy/guidance/midcourse-guidance/scripts/test_midcourse_guidance.py

## Compliance

- FAR-25 (US government work, public domain) and CS-25 (EASA,
  free-download) are referenced by id only per standards-map.yaml,
  reference-only: true; no text is copied.
- compliance: STANDARDS-REF, gated: false.
