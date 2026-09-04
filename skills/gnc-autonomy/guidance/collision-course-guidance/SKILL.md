---
name: collision-course-guidance
description: "Use when you must compute the collision-course intercept geometry for a constant-speed pursuer against a constant-velocity target: the lead angle of the pursuer velocity off the line of sight that closes the collision triangle, the closing speed along the line of sight, the time to go to the predicted intercept point, the intercept point coordinates, and the bearing error check against the current pursuer heading. Produces the lead angle, closing speed, time to go, intercept point, and the heading-error verdict that gate a constant-bearing intercept guidance assessment. Trigger: collision-course-guidance, constant-bearing-intercept, lead-angle, collision-triangle, predicted-intercept-point."
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
  tags: [collision-course-guidance, constant-bearing-intercept, lead-angle, collision-triangle, predicted-intercept-point]
  version: 0.1.0
  author: AeroSkills
---

# Collision Course Guidance (gnc-autonomy/guidance/collision-course-guidance)

Use when the task is the constant-bearing collision-course intercept geometry
of a constant-speed pursuer against a constant-velocity target in a plane:
the lead angle that points the pursuer velocity at the predicted meeting
point, the closing speed along the line of sight, the time to go, the
intercept point, and the bearing error of the current pursuer heading. This
leaf solves the collision triangle in pure Python, stdlib only, and fills the
constant-bearing gap between the two sibling steering laws: the leaf that
steers the velocity at the target's current position
(gnc-autonomy/guidance/pursuit-guidance) and the leaf that owns the rate-based
steering law (gnc-autonomy/guidance/proportional-navigation). The collision
triangle assumes constant speeds and a constant-velocity target: no
acceleration or turning dynamics are modeled.

## Domain quick reference

- Geometry: the line of sight (LOS) runs from the pursuer to the target;
  los_to_target angle and target heading are plane headings in degrees in the
  same frame. Range is r = sqrt(dx^2 + dy^2).
- Relative angle: beta = wrap180(target_heading_angle_deg -
  los_to_target_angle_deg) into [-180, 180], the signed angle between the
  target velocity vector and the LOS on the closing side of the triangle.
  beta = 0 is the head-on closing geometry where the target flies straight at
  the pursuer.
- Lead angle: sin(LA) = (Vt / Vp) * sin(beta), LA in degrees, positive toward
  the target's flight side. Equivalent constant-bearing form:
  Vp * sin(LA) = Vt * sin(beta), the null-LOS-rotation condition.
- Closing speed: Vc = Vp * cos(LA) + Vt * cos(beta) in m/s; the target
  velocity component toward the pursuer is positive when the target heads
  along the LOS toward the pursuer. Vc must be > 0 for a closing intercept.
- Time to go: t_go = r / Vc in s, valid while closing.
- Intercept point: target position extrapolated by its constant velocity,
  (tx + tvx * t_go, ty + tvy * t_go); on the collision triangle both vehicles
  arrive there at t_go.
- Bearing error: required heading = los_angle + lead_angle; the error against
  the current pursuer heading is wrapped to [-180, 180].
- Head-on degenerate: beta = 0 gives LA = 0 and Vc = Vp + Vt.
- Units: m, m/s, s; angles in degrees. Pure stdlib math, deterministic.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the collision triangle is common guidance-theory knowledge.

## Workflow

1. Fix the intercept geometry: pursuer speed Vp, target speed Vt, the LOS
   angle to the target, and the target heading angle (degrees). If you start
   from positions and velocity vectors, take the LOS angle from atan2 and the
   target heading from atan2 of its velocity components.
2. Confirm the relative angle beta = wrap180(target heading - LOS angle);
   beta = 0 is the head-on closing case, beta positive puts the target on one
   flight side.
3. Compute the lead angle with lead_angle(Vp, Vt, los, heading): the pursuer
   velocity must lead the LOS by LA toward the target's flight side to hold
   the bearing constant.
4. Compute the closing speed with collision_closing_speed(Vp, Vt, los,
   heading); a ValueError here means the geometry never closes.
5. Estimate the remaining flight time with time_to_go(range_m, closing_speed)
   and the predicted meeting point with intercept_point(pursuer_x, pursuer_y,
   target_x, target_y, target_vx, target_vy, t_go).
6. Check the current heading against the required heading los + LA with
   heading_error_deg(pursuer_heading, los, lead); a zero error is the
   constant-bearing condition.
7. Bundle the whole state with collision_course_assessment(pursuer_x,
   pursuer_y, target_x, target_y, target_vx, target_vy, pursuer_speed,
   target_speed), which returns range_m, los_angle_deg, lead_angle_deg,
   closing_speed_m_s, time_to_go_s, intercept_x, intercept_y.
8. Confirm the deterministic checks with the contract test
   scripts/test_collision_course_guidance.py.

## Worked example

Pursuer speed 600 m/s, target speed 250 m/s at 60 deg to the line of sight
(beta = 60 deg), range 10 000 m. Module frame: los_to_target_angle_deg = 0,
target_heading_angle_deg = 60. Real module outputs:

- lead_angle(600, 250, 0, 60) = 21.152 deg, inside the 18-24 deg band (about
  21.2); the pursuer heads los + LA = 21.152 deg.
- collision_closing_speed(600, 250, 0, 60) = 684.576 m/s, inside the
  650-720 m/s band (about 685).
- time_to_go(10000.0, 684.576) = 14.608 s, inside the 13-16 s band (about
  14.6).
- Intercept point with the target at the origin moving along +x at 250 m/s:
  after t_go the target has moved 250 * 14.608 = 3651.9 m along its velocity,
  so intercept_point gives (3651.9, 0.0): the intercept lies ahead of the
  target.
- Bearing check: heading_error_deg(10.0, 0.0, 21.152) = 11.152 deg: the
  pursuer at heading 10 deg must turn 11.152 deg toward the lead heading.
- Meeting-point identity: laying the closing-side triangle out (pursuer at
  the origin, target 10 000 m down the LOS, target velocity beta off the LOS
  line back toward the pursuer), the pursuer arrival point after t_go is
  (8174.05, 3162.64) m and the module intercept point is (8174.05, 3162.64)
  m: they coincide to about 5e-13 m, far inside the 1% of range (100 m)
  tolerance.
- Convenience chain with the same geometry (pursuer at (-5000, 8660.25) m,
  target at the origin moving +x): collision_course_assessment returns range
  10 000.0 m, los_angle -60.0 deg, lead_angle 21.152 deg, closing speed
  684.576 m/s, time to go 14.608 s, intercept (3651.9, 0.0) m.

## Verification

- Confirm lead_angle(600, 250, 0, 60) = 21.152 deg and
  collision_closing_speed(600, 250, 0, 60) = 684.576 m/s; time_to_go over
  10 000 m gives 14.608 s, all inside the spec magnitude bounds.
- Confirm the head-on degenerate: a target flying straight at the pursuer
  (beta = 0, e.g. los 30 deg, heading 30 deg) gives lead angle 0 and closing
  speed exactly Vp + Vt = 850 m/s.
- Confirm the mirror: beta = -60 deg gives the opposite-sign lead angle of
  beta = +60 deg and the same closing speed.
- Confirm the consistency identity: the pursuer velocity at the lead angle
  and the target velocity meet at the intercept point at t_go (asserted
  within 1% of the range in the contract test).
- Confirm every non-physical input is rejected with ValueError: pursuer speed
  <= 0, target speed < 0, an asin argument beyond 1 in magnitude (target too
  fast for a collision course), a closing speed <= 0 (no closing intercept),
  and range < 0 or closing speed <= 0 in time_to_go.
- Confirm the convenience dict contains exactly the documented keys, and
  that the module is deterministic: no RNG anywhere, run-to-run identical
  floats.
- Run the contract test offline: python3
  scripts/test_collision_course_guidance.py (35 tests, deterministic).

## Pitfalls

- Target faster than the pursuer: the lead angle asin(Vt/Vp*sin(beta)) has
  no real solution when the argument exceeds 1 in magnitude - a target too
  fast for a collision course raises ValueError rather than returning an
  angle.
- Quoting time to go on a non-closing geometry: Vc must be positive
  (collision_closing_speed raises ValueError otherwise) and time_to_go
  rejects closing speed <= 0 or negative range.
- Reading the lead angle without the wrap: beta is wrapped into [-180, 180]
  and the required heading is los + LA; heading error is also wrapped, so an
  11.15 deg error is a turn toward the lead heading, not a 348.8 deg turn.
- Degrees throughout: LOS angle, target heading, lead angle and heading
  error are all in degrees in the same frame; mixing radians silently shifts
  every triangle output.
- Applying the triangle to accelerating vehicles: the model assumes constant
  pursuer speed and a constant-velocity target with no turning dynamics -
  the meeting point identity (both vehicles arrive at intercept at t_go
  within 1% of range) only holds under those assumptions.

## Related leaves

- gnc-autonomy/guidance/pursuit-guidance: the sibling leaf that steers the
  pursuer velocity at the target's current position; this leaf's collision
  triangle is the constant-bearing alternative.
- gnc-autonomy/guidance/proportional-navigation: the sibling leaf that owns
  the rate-based steering law; this leaf owns the lead-angle geometry.
- gnc-autonomy/guidance/augmented-proportional-navigation: the rate-based
  law augmented for a maneuvering target, built on the same planar intercept
  frame.
- gnc-autonomy/guidance/command-to-line-of-sight: steering along the LOS
  reference axis, the alternative guidance geometry.
- gnc-autonomy/guidance/midcourse-guidance: steering between intermediate
  points before the terminal homing phase this leaf supports.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_collision_course_guidance.py

The test covers the worked-example anchors (lead angle 21.152 deg within
18-24, closing speed 684.576 m/s within 650-720, time to go 14.608 s within
13-16, intercept 3651.9 m ahead of the target), the sine law and the
Vc formula identities, the head-on degenerate case (beta = 0: lead 0, closing
speed Vp + Vt), the mirror case (opposite lead sign, same closing speed),
heading wrap behavior, the meeting-point identity within 1% of the range,
the convenience assessment dict keys and values, ValueError rejection of
non-physical inputs and non-closing geometry, and determinism.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard; this leaf names it as the development-assurance frame for the
  guidance function and paraphrases the standard engineering collision-course
  method only, per standards-map.yaml (reference-only: true).
- compliance: STANDARDS-REF, gated: false.
