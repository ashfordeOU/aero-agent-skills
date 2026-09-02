---
name: pursuit-guidance
description: "Use when you must compute pursuit guidance commands for a planar intercept: derive the line of sight angle, the pure pursuit heading that points the interceptor velocity at the target, the wrapped guidance error between the current heading and the aim heading, the lead angle for a lead pursuit collision course, and the capture condition from the interceptor to target speed ratio. Produces the pursuit aim heading, guidance error, lead angle, capture feasibility, intercept time, and the proportional navigation acceleration command for comparison that gate a pursuit guidance assessment. Trigger: pursuit guidance, pure pursuit, lead pursuit, lead angle, guidance error, heading error, capture condition, collision course, intercept time, terminal homing."
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
  tags: [pursuit-guidance, pure-pursuit, lead-pursuit, lead-angle, guidance-error, heading-error, capture-condition, collision-course, intercept-time, terminal-homing]
  version: 0.1.0
  author: Aero Agent Skills
---

# Pursuit Guidance (gnc-autonomy/guidance/pursuit-guidance)

Use when the task is pursuit guidance for a planar intercept: the
pure pursuit or lead pursuit aim heading, the guidance error, the
capture condition, and comparison with proportional navigation.

## Domain quick reference

- Geometry: (rx, ry) is the relative position of the target from the
  interceptor in the inertial plane (m); (vx, vy) is the relative
  velocity (m/s). Range is r = sqrt(rx^2 + ry^2).
- Line of sight angle: lam = atan2(ry, rx) in rad; the direction of
  the interceptor-to-target line.
- Pure pursuit: the interceptor velocity points at the target's
  current position, so the commanded heading equals the line of sight
  angle: psi_cmd = atan2(ry, rx).
- Guidance error (heading error): eta = wrap(psi_cmd - psi) into
  [-pi, pi]; the pursuit law turns to null eta, so the velocity
  aligns with the line of sight.
- Capture condition: with constant speeds, pure pursuit captures a
  non-maneuvering target on a straight course only when the
  interceptor is faster, Vi > Vt; at Vi <= Vt a receding target
  cannot be caught.
- Tail chase intercept time: t_i = r / (Vi - Vt) in s when the target
  is directly ahead and receding; valid only for Vi > Vt.
- Lead pursuit: aim at a point ahead of the target. For a constant
  velocity collision course the lead angle is
  lam_lead = asin((Vt / Vi) * sin(beta)) in rad, where beta is the
  angle between the line of sight and the target velocity vector.
  The aim heading is psi_cmd = lam + lam_lead. The arcsin argument
  must lie in [-1, 1]; otherwise the interceptor is too slow and no
  collision course exists.
- On a perfect collision course the line of sight does not rotate
  (lam_dot = 0), the same steady state proportional navigation seeks.
- Comparison with PN: proportional navigation commands lateral
  acceleration a_c = N * Vc * lam_dot perpendicular to the line of
  sight; pure pursuit commands a turn toward the line of sight and
  keeps lam_dot nonzero until intercept. PN nulls the line of sight
  rate directly and needs no explicit lead; pure pursuit is simpler
  but less efficient and more sensitive to target maneuvers.
- Units: m, m/s, rad, rad/s, m/s^2; angles are radians throughout.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; pursuit guidance laws are common guidance-theory knowledge.

## Workflow

1. Form the relative geometry: rx = xt - xi, ry = yt - yi,
   vx = vxt - vxi, vy = vyt - vyi in the inertial plane, SI units,
   angles in radians.
2. Compute line_of_sight_angle(rx, ry); this is the pure pursuit aim
   heading.
3. Compute heading_error(psi, rx, ry) between the current heading and
   the aim heading, wrapped to [-pi, pi]; the pursuit law turns to
   null it.
4. For lead pursuit, compute lead_angle(v_target, v_interceptor,
   beta) and add it to the line of sight angle for the aim heading.
   Confirm the arcsin argument is within [-1, 1], or the interceptor
   is too slow for a collision course.
5. Check capture_possible(v_interceptor, v_target): pure pursuit
   captures only when Vi > Vt.
6. For a tail chase, compute intercept_time(r, v_interceptor,
   v_target) as r / (Vi - Vt).
7. For comparison, compute pn_acceleration(rx, ry, vx, vy, n_nav=4.0)
   with N between 3 and 5; the result is the lateral acceleration
   proportional navigation would command.

## Pitfalls

- Using the range instead of the vector components for the aim
  heading; atan2(ry, rx) needs the signed relative position.
- Leaving the heading error unwrapped; the wrapped value in [-pi, pi]
  is the angle the turn must null, not the raw difference.
- Taking a lead angle arcsin outside [-1, 1]; that geometry has no
  collision course at the given speed ratio.
- Forgetting the speed condition Vi > Vt; a slower interceptor never
  captures a receding straight-course target in pure pursuit.
- Confusing the lead angle with the line of sight angle; the aim
  heading is their sum, not either alone.
- Mixing degrees and radians; all formulas require radians.

## Behavior contract (gate 3)

The line of sight angle, wrapped heading error, lead angle, capture
condition, intercept time, and the proportional navigation
comparison command are exercised by the gate 3 contract test:
scripts/test_pursuit_guidance.py against
scripts/pursuit_guidance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_pursuit_guidance.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
