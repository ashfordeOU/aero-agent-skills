# Wave-31 leaf spec: collision-course-guidance (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/collision-course-guidance/
- Pack: guidance (siblings listed in the augmented-proportional-navigation
  spec). pursuit-guidance owns the PURE PURSUIT law (velocity pointed at the
  target's current position, tail-chase LOS rotation). proportional-navigation
  owns the rate-based law. The constant-bearing COLLISION COURSE (lead-angle
  intercept at the predicted meeting point) is absent from the library: no leaf
  solves the collision triangle for the lead angle, the intercept time, or the
  predicted intercept point. This leaf fills that gap.
- Standards ids: arp4754a (reference-only, gnc convention). Ledger Standard:
  arp4754a.
- Family: gnc-autonomy

## Claim

Compute the collision-course intercept geometry for a constant-speed pursuer
against a constant-velocity target in a plane: the lead angle of the pursuer
velocity vector from the line of sight that puts the pursuer on a collision
triangle with the target, the closing speed along the line of sight, the time
to go to the predicted intercept point, the intercept point coordinates, and
the bearing error check against a current pursuer heading. Produces the lead
angle, closing speed, time to go, intercept point, and heading-error verdict
that gate a constant-bearing intercept guidance assessment.

Does NOT do: pure pursuit (pursuit-guidance owns tail-chase steering to the
target's current position); proportional navigation or its augmentation
(proportional-navigation, augmented-proportional-navigation own rate-based
commands); command-to-line-of-sight (command-to-line-of-sight); midcourse
waypoint steering (midcourse-guidance); path planning (dubins-path-planning,
coverage-path-planning). The collision triangle assumes constant speeds and a
constant-velocity target; no acceleration or turning dynamics are modeled.

## Model (implement exactly)

Module constants:
- PI = math.pi.

Functions (pure stdlib):
- lead_angle(pursuer_speed, target_speed, los_to_target_angle_deg,
  target_heading_angle_deg) -> float: the lead angle LA (deg) satisfies
  sin(LA) = (target_speed / pursuer_speed) * sin(beta) where beta is the
  angle between the target velocity vector and the line of sight (compute
  beta from the two heading angles, wrapped to [-180, 180]). Return LA in
  degrees, positive toward the target's flight side. ValueError if
  pursuer_speed <= 0, target_speed < 0; ValueError (no collision possible)
  when target_speed > pursuer_speed and the argument of asin exceeds 1 in
  magnitude.
- collision_closing_speed(pursuer_speed, target_speed,
  los_to_target_angle_deg, target_heading_angle_deg) -> float: the closing
  speed along the line of sight Vc = pursuer_speed * cos(LA) + target_speed *
  cos(beta), where LA and beta come from the same triangle (target velocity
  component toward the pursuer is positive when the target heads along the
  line of sight toward the pursuer; use the wrapped beta so that beta = 0
  means the target flies straight at the pursuer). ValueError if the result
  is <= 0 (no closing intercept).
- time_to_go(range_m, closing_speed) -> float: t_go = range / closing_speed.
  ValueError if range < 0 or closing_speed <= 0.
- intercept_point(pursuer_x, pursuer_y, target_x, target_y, target_vx,
  target_vy, time_to_go) -> tuple[float, float]: (target_x + target_vx *
  t_go, target_y + target_vy * t_go).
- heading_error_deg(pursuer_heading_deg, los_angle_deg, lead_angle_deg) ->
  float: the difference between the required heading (los + lead) and the
  current pursuer heading, wrapped to [-180, 180].
- collision_course_assessment(pursuer_x, pursuer_y, target_x, target_y,
  target_vx, target_vy, pursuer_speed, target_speed) -> dict: convenience
  chain computing the range, LOS angle, lead angle, closing speed, time to
  go, intercept point, and a geometry summary; returns {range_m, los_angle_deg,
  lead_angle_deg, closing_speed_m_s, time_to_go_s, intercept_x, intercept_y}.

## Worked example

Pursuer speed 600 m/s. Target speed 250 m/s flying at 60 deg to the line of
sight (beta = 60 deg). Range 10 000 m. Target velocity components in the
example geometry: put the target at the origin moving along +x at 250 m/s and
the LOS from pursuer to target along a line 60 deg from the target velocity.

Simpler fixed geometry for the module check: target at (0, 0) with velocity
(250, 0) m/s (target heading 0 deg along +x); pursuer at (-5000, 8660.25) m
so the LOS from pursuer to target points along the +x-ish direction at -60
deg elevation; take los_to_target_angle_deg = 0 and target_heading_angle_deg
= 60 (target velocity 60 deg off the LOS).

Deterministic anchors (run your module, take the printed values as the assert
targets, then CHECK the magnitude bounds):
- lead angle in 18-24 deg (about 21.2).
- closing speed in 650-720 m/s (about 685).
- time to go at 10 000 m in 13-16 s (about 14.6).
- intercept point lies ahead of the target: after t_go the target has moved
  about 3650 m along its velocity.
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: pursuer_speed <= 0, target_speed < 0, non-closing geometry
  (closing speed <= 0), range < 0, asin argument out of range (target too
  fast for a collision course).
- Degenerate: a target flying straight at the pursuer (beta = 0) gives
  lead_angle 0 and closing speed = pursuer_speed + target_speed.
- Mirror: beta = -60 deg gives the opposite-sign lead angle of beta = +60 deg.
- Consistency: the pursuer velocity at the lead angle and the target velocity
  meet at the intercept point at t_go (assert within 1% of the range).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-collision-course-guidance.yaml)

Query 1 (copy verbatim):
  "compute the lead angle and time-to-go for a constant-bearing-intercept collision course of a constant-velocity target by a constant-speed pursuer"
  intent: "gnc-autonomy; collision-course lead angle intercept geometry"
  expected_skill: "gnc-autonomy/guidance/collision-course-guidance"
Query 2 (copy verbatim):
  "determine the predicted-intercept-point and the closing speed along the line of sight for a collision-triangle guidance solution"
  intent: "gnc-autonomy; collision triangle intercept point and closing speed"
  expected_skill: "gnc-autonomy/guidance/collision-course-guidance"
Task ids: w31-collision-course-guidance-1 and -2.

Forbidden tokens that belong to siblings: do NOT use pure pursuit, tail chase,
proportional navigation, line of sight rate, augmented navigation, CLOS, beam
rider, waypoint, Dubins, coverage path. The phrase line of sight appears only
as the reference axis for the angles; corpus queries MUST carry the
collision-course, lead angle, constant-bearing, or intercept-point tokens.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the collision-course intercept
geometry for a constant-speed pursuer against a constant-velocity target:" and
include the outputs listed in the Claim. First tag: collision-course-guidance.
Additional tags only: constant-bearing-intercept, lead-angle, collision-triangle,
predicted-intercept-point. NEVER single generic words (guidance, intercept,
geometry, target, pursuit, angle). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.
