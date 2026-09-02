---
name: command-to-line-of-sight
description: "Use when you must compute a command to line of sight guidance command for a missile intercept: derive the tracker to target line of sight angle, the angular deviation of the missile from the tracker target line, the line of sight rotation rate, the steering acceleration proportional to the LOS error and its rate, the signed cross track offset of the missile from the line, and the on line verdict that gate a CLOS guidance assessment. Produces the LOS angle, wrapped LOS error, LOS rate, steering command, cross track offset, and the on line tracking verdict. Trigger: command to line of sight, CLOS, beam riding, LOS error, LOS rate, line of sight rate, steering command, cross track offset, tracker target line, intercept guidance."
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
  subdomain: guidance
  tags: [command-to-line-of-sight, clos-guidance, los-angle-tracking, beam-riding, los-error, steering-command, cross-track-offset, tracker-target-line]
  version: 0.1.0
  author: Aero Agent Skills
---

# Command to Line of Sight Guidance (gnc-autonomy/guidance/command-to-line-of-sight)

Use when the task is command to line of sight guidance for a
missile intercept: the tracker to target line, the LOS error of the
missile, the steering command proportional to the error and its
rate, and the cross track offset verdict.

## Domain quick reference

- Geometry: the tracker sits at the origin of the inertial plane.
  (xt, yt) is the target position (m) and (xm, ym) the missile
  position (m). The tracker to target line is the line the missile
  must ride.
- Line of sight angle: lam = atan2(y, x) in rad, the direction of
  the tracker to point line, used for the target (lam_t) and the
  missile (lam_m).
- LOS error: eps = wrap(lam_t - lam_m) in rad, wrapped into [-pi,
  pi]; the signed angular deviation of the missile from the tracker
  target line. The CLOS law commands a turn to null it.
- Line of sight rate: lam_dot = (x*vy - y*vx) / r^2 in rad/s, the
  rotation rate of the tracker to target line, with range
  r = sqrt(x^2 + y^2).
- Steering command: a_c = k_error * eps + k_rate * lam_dot in
  m/s^2, the lateral acceleration proportional to the LOS error and
  its rate. Gains are non-negative; k_error in 1/s^2 and k_rate in
  1/s. The error-only case (k_rate = 0) is the beam riding law.
- Cross track offset: d = (xt*ym - yt*xm) / r_t in m, the signed
  perpendicular offset of the missile from the tracker target line,
  positive on one side of the line. The missile is on line when
  |d| is within the tracking tolerance.
- On line verdict: on_line(d, tol) is True when |d| < tol, the
  tracking tolerance in meters.
- CLOS steers the missile onto the tracker target line directly;
  proportional navigation instead nulls the line of sight rate and
  pursuit guidance points the velocity at the target or a lead
  point. CLOS needs no target speed estimate but is sensitive to
  tracker measurement noise.
- Units: m, m/s, rad, rad/s, m/s^2; angles are radians throughout.
- ARP4754A (reference-only) frames development assurance for
  aircraft systems; CLOS guidance laws are common guidance-theory
  knowledge.

## Workflow

1. Form the geometry: the tracker at the origin, the target at
   (xt, yt) and the missile at (xm, ym), SI units, angles in
   radians.
2. Compute the target line of sight angle with los_angle(xt, yt)
   and the missile line of sight angle with los_angle(xm, ym).
3. Compute the LOS error with los_error(lam_t, lam_m), wrapped to
   [-pi, pi]; this is the angular deviation the steering law acts
   to null.
4. Compute the line of sight rotation rate with los_rate(xt, yt,
   vx, vy) using the target velocity, to track the moving target.
5. Compute the steering command with steering_command(eps, lam_dot,
   k_error, k_rate); the result is the lateral acceleration to
   command, perpendicular to the line. Use k_rate = 0 for the beam
   riding law.
6. Compute the cross track offset with cross_track_offset(xm, ym,
   xt, yt) and the on line verdict with on_line(d, tol) before
   gating the tracking assessment.

## Pitfalls

- Mixing up the target and missile line of sight angles in the LOS
  error; eps = wrap(lam_t - lam_m) is the missile deviation from
  the target line, and the sign flips if the order is reversed.
- Leaving the LOS error unwrapped; the wrapped value in [-pi, pi]
  is the angle the steering law must null.
- Using the range instead of the vector components for the line of
  sight angle; atan2(y, x) needs the signed position.
- Taking the line of sight rate at zero range; the tracker to
  target line is undefined when r = 0.
- Using negative gains in the steering command; the CLOS law is
  stabilizing only for non-negative k_error and k_rate.
- Confusing the cross track offset with the LOS error; the offset
  is a perpendicular distance in meters, the error is an angle in
  radians.
- Using a non-positive tracking tolerance; the on line verdict is
  undefined for tol <= 0.

## Behavior contract (gate 3)

The line of sight angle, wrapped LOS error, line of sight rate,
steering command, cross track offset, and on line verdict are
exercised by the gate 3 contract test:
scripts/test_command_to_line_of_sight.py against
scripts/command_to_line_of_sight_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_command_to_line_of_sight.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
