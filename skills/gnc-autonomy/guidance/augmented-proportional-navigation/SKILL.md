---
name: augmented-proportional-navigation
description: "Use when you must compute augmented proportional navigation guidance commands for a planar intercept of a maneuvering target: line of sight rate from the relative position and velocity vectors, closing velocity, the pure proportional navigation command as the baseline, the augmented command that adds the target lateral acceleration perpendicular to the line of sight scaled by half the effective navigation ratio, the time to go estimate, and the commanded lateral acceleration in g. Produces the LOS rate, closing velocity, PN and APN commands, time to go, and the g-load verdict that gate an intercept guidance law assessment against a maneuvering target. Trigger: augmented-proportional-navigation, maneuvering-target-intercept, target-lateral-acceleration, apn-command, guidance-law-augmentation."
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
  tags: [augmented-proportional-navigation, maneuvering-target-intercept, target-lateral-acceleration, apn-command, guidance-law-augmentation]
  version: 0.1.0
  author: AeroSkills
---

# Augmented Proportional Navigation (gnc-autonomy/guidance/augmented-proportional-navigation)

Use when the task is augmented proportional navigation (APN) guidance for a
planar intercept of a maneuvering target: the augmentation term adds the
target lateral acceleration perpendicular to the line of sight to the classic
proportional navigation command, so the interceptor stays on a collision
course against a target that pulls lateral g. This leaf implements the planar
constant-speed APN law APN = N' * (Vc * lamdot + a_T_perp / 2) in pure Python,
stdlib only. It pairs with gnc-autonomy/guidance/proportional-navigation,
which owns the unaugmented law, its geometry, and its corpus tasks: this leaf
is the augmented-PN member whose distinct output is the target-lateral
acceleration term.

## Domain quick reference

- Geometry: (rx, ry) is the relative position of the target from the
  interceptor in the inertial plane (m); (vx, vy) is the relative velocity
  (m/s). Range is r = sqrt(rx^2 + ry^2).
- Line of sight rate: lamdot = (rx*vy - ry*vx) / r^2 in rad/s, the rotation
  rate of the interceptor-to-target line; zero on a pure collision course.
- Closing velocity: Vc = -(rx*vx + ry*vy) / r in m/s; positive when the
  range is decreasing, negative when the target recedes (opening geometry,
  passed through).
- Pure proportional navigation command (baseline): a_pn = N' * Vc * lamdot
  in m/s2, perpendicular to the line of sight.
- Augmented proportional navigation command: a_apn = N' * (Vc * lamdot +
  a_T_perp / 2) in m/s2, where a_T_perp is the target lateral acceleration
  perpendicular to the line of sight (any sign). The augmentation term adds
  exactly N' / 2 * a_T_perp to the pure command, so a target pulling 10 m/s2
  lateral at N' = 4 adds 20 m/s2 to the command.
- Commanded acceleration in g: a / G0, G0 = 9.80665 m/s2.
- Time to go: t_go = range / Vc in s, meaningful only while closing.
- With a_T_perp = 0 the augmented command degenerates to the pure
  proportional navigation command, which is the sibling leaf's claim.
- Units: m, m/s, rad/s, m/s2, s; angles in radians throughout.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the APN law is common guidance-theory knowledge.

## Workflow

1. Form the relative geometry: rx = xt - xi, ry = yt - yi, vx = vxt - vxi,
   vy = vyt - vyi in the inertial plane, SI units, angles in radians.
2. Estimate the target lateral acceleration a_T_perp perpendicular to the
   line of sight from the tracking filter or the target state estimate;
   it may be any sign and is a required input of the augmented law.
3. Compute closing_velocity(rx, ry, vx, vy) and confirm it is positive, so
   the range is decreasing and time to go is meaningful.
4. Compute los_rate(rx, ry, vx, vy) in rad/s; this is the rotation rate the
   guidance law acts to null.
5. Compute the baseline with pn_command(navigation_ratio, vc, lamdot) and
   the augmented command with apn_command(navigation_ratio, vc, lamdot,
   a_T_perp); the difference is exactly N' / 2 * a_T_perp.
6. Express the loads with commanded_accel_g and estimate the remaining
   flight time with time_to_go(range_m, vc).
7. Bundle the full state with apn_assessment(rx, ry, vx, vy, a_T_perp,
   navigation_ratio=4.0, range_m=None), which returns los_rate, closing
   velocity, PN and APN commands in m/s2 and g, and time to go (None when
   no range is supplied).
8. Confirm the deterministic checks with the contract test
   scripts/test_augmented_proportional_navigation.py.

## Worked example

Planar intercept: closing velocity 900 m/s, LOS rate 0.005 rad/s, target
lateral acceleration 10 m/s2, navigation ratio 4.0. Real module outputs:

- pn_command(4.0, 900.0, 0.005) = 18.0 m/s2 (about 1.8355 g), within the
  15-21 m/s2 band.
- apn_command(4.0, 900.0, 0.005, 10.0) = 38.0 m/s2 (about 3.8749 g), within
  the 34-42 m/s2 band.
- The augmentation term adds N' / 2 * a_T = 2.0 * 10.0 = 20 m/s2 to the
  pure proportional navigation command (38.0 - 18.0 = 20.0).

Geometry check with rel_pos = (8000, 6000) m and rel_vel = (-600, -300) m/s:

- Range = sqrt(8000^2 + 6000^2) = 10,000 m.
- closing_velocity = -(8000*(-600) + 6000*(-300)) / 10000 = 660.0 m/s.
- los_rate = (8000*(-300) - 6000*(-600)) / 10000^2 = 0.012 rad/s: this
  relative velocity is 10.3 degrees off the head-on course, so the LOS
  rotates at 0.012 rad/s. On the near-head-on course closing at 660 m/s
  (rel_vel about (-527.3, -396.9) m/s) the same formulas give a LOS rate
  of about -1.15e-4 rad/s, i.e. the small negative value inside the
  -2e-4..0 band that characterizes an almost perfect collision course.
- time_to_go(10000.0, 660.0) = 15.15 s, within the 13-17 s band.

## Verification

- Confirm pn_command(4.0, 900.0, 0.005) returns 18.0 m/s2 and
  apn_command(4.0, 900.0, 0.005, 10.0) returns 38.0 m/s2; their difference
  equals N' / 2 * a_T_perp = 20.0 exactly.
- Confirm apn_command with target_lateral_accel = 0 equals pn_command for
  the same inputs (degenerate check).
- Confirm doubling the target lateral acceleration from 10 to 20 m/s2 grows
  the augmented command by exactly N' / 2 * 10 = 20 m/s2.
- Confirm a crossing target mirrored about the LOS (rel_vel_y sign flip)
  flips the sign of the LOS rate.
- Confirm every invalid input is rejected: navigation_ratio <= 0, zero
  relative position, range < 0, and closing velocity <= 0 in time_to_go all
  raise ValueError.
- Confirm run-to-run identical floats: the module uses no stochastic draws.
- Run the contract test offline: python3
  scripts/test_augmented_proportional_navigation.py (33 tests,
  deterministic).

## Pitfalls

- Running the augmented law without the target acceleration estimate:
  a_T_perp is a required input from the tracking filter or target state
  estimate (any sign); with it zeroed the augmented command degenerates to
  the pure PN command and the leaf adds nothing.
- Time-to-go on opening geometry: Vc is negative when the target recedes and
  time_to_go raises ValueError for closing velocity <= 0 or negative range;
  confirm Vc > 0 first.
- Reading the command in the wrong units: the commands come out in m/s2 (pn
  18.0, apn 38.0 on the worked example) and commanded_accel_g divides by
  9.80665; g loads are the pilot/airframe-relevant read.
- Expecting a linear scaling in N': the augmentation adds exactly
  N'/2*a_T_perp (N' = 4 with a 10 m/s2 target adds 20 m/s2), so raising the
  navigation ratio raises both the PN term and the augmentation term.
- Zero relative position (range 0) and navigation_ratio <= 0 raise
  ValueError; the module is deterministic with no stochastic draws.

## Related leaves

- gnc-autonomy/guidance/proportional-navigation: the unaugmented
  proportional navigation law, its geometry, and its corpus tasks; this
  leaf adds the target-lateral-acceleration augmentation term on top.
- gnc-autonomy/guidance/pursuit-guidance: pure pursuit steering, the
  alternative terminal guidance law for non-maneuvering targets.
- gnc-autonomy/guidance/command-to-line-of-sight: line-of-sight steering,
  the alternative guidance geometry.
- gnc-autonomy/guidance/midcourse-guidance: waypoint steering before the
  terminal homing phase that APN commands.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_augmented_proportional_navigation.py

The test covers the worked-example anchors (PN command 18.0 m/s2 within
15-21, APN command 38.0 m/s2 within 34-42, augmentation term 20 m/s2, LOS
rate sign and near-head-on small-value regime, closing velocity 660 m/s,
time to go 15.15 s within 13-17), the degenerate case (zero target lateral
acceleration collapses APN to PN), the scaling identity (doubled target
lateral acceleration grows the command by exactly N' / 2 times the
increment), g-load conversion, ValueError rejection of non-physical inputs,
the convenience assessment dict keys and values, and determinism.

## Compliance

- Standards referenced, not reproduced: ARP4754A is a proprietary SAE
  standard; this leaf names it as the development-assurance frame for the
  guidance function and paraphrases the standard engineering APN method
  only, per standards-map.yaml (reference-only: true).
- compliance: STANDARDS-REF, gated: false.
