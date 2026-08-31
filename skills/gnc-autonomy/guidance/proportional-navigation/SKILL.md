---
name: proportional-navigation
description: "Use when you must compute the proportional navigation guidance command for a planar intercept in SI units: determine the closing velocity from the relative position and velocity vectors, compute the line of sight rate, and calculate the commanded acceleration perpendicular to the line of sight from the navigation constant. Produces range, closing velocity, LOS rate, and the acceleration command that gate an intercept guidance assessment. Trigger: proportional navigation, line of sight rate, closing velocity, navigation constant, intercept guidance, pursuit guidance, terminal guidance, engagement geometry."
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
  tags: [proportional-navigation, planar-intercept, closing-velocity, line-of-sight-rate, navigation-constant, intercept-guidance, terminal-guidance, engagement-geometry]
  version: 0.1.0
  author: AeroSkills
---

# Proportional Navigation (gnc-autonomy/guidance/proportional-navigation)

Use when the task is proportional navigation guidance for a planar
intercept: closing velocity, line of sight rate, and the commanded
acceleration from the navigation constant.

## Domain quick reference

- Geometry: (rx, ry) is the relative position of the target from the
  interceptor in the inertial plane (m); (vx, vy) is the relative
  velocity (m/s). Range is r = sqrt(rx^2 + ry^2).
- Closing velocity: vc = -(rx*vx + ry*vy) / r in m/s; positive when
  the range is decreasing, negative when the target recedes.
- Line of sight rate: lam_dot = (rx*vy - ry*vx) / r^2 in rad/s; the
  rotation rate of the interceptor-to-target line.
- Commanded acceleration: a_c = N * vc * lam_dot in m/s^2,
  perpendicular to the line of sight. N is the navigation constant,
  typically 3 to 5, with 4 the common baseline.
- Pure pursuit steers straight at the target and needs a lead angle;
  proportional navigation nulls the line of sight rate and needs no
  explicit lead.
- Units: m, m/s, rad/s, m/s^2; angles are radians throughout.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the PN law is common guidance-theory knowledge.

## Workflow

1. Form the relative geometry: rx = xt - xi, ry = yt - yi,
   vx = vxt - vxi, vy = vyt - vyi in the inertial plane, SI units,
   angles in radians.
2. Compute closing_velocity(rx, ry, vx, vy) and confirm it is
   positive, so the range is decreasing.
3. Compute line_of_sight_rate(rx, ry, vx, vy) in rad/s; this is the
   rotation rate the guidance law acts to null.
4. Compute commanded_acceleration(rx, ry, vx, vy, n_nav) with N
   between 3 and 5; the result is the lateral acceleration to
   command, perpendicular to the line of sight.
5. Bundle the full state with
   guidance_command(rx, ry, vx, vy, n_nav=4.0), which returns range,
   closing velocity, LOS rate, acceleration command, and N in one
   dict.

## Pitfalls

- Reading the closing speed magnitude instead of the signed closing
  velocity; a receding target must flip the sign of the command.
- Mixing degrees and radians for the LOS rate; the formulas require
  radians.
- Feeding filtered range and range rate that are inconsistent with
  the raw relative vectors; both PN formulas must share one
  (rx, ry, vx, vy) set.
- Accepting N <= 0; the module raises ValueError, and N below 3
  typically nulls the line of sight rate too slowly.
- Commanding the acceleration without the perpendicular-to-LOS check;
  a_c is the lateral component, not the total acceleration vector.

## Behavior contract (gate 3)

The closing velocity, line of sight rate, commanded acceleration, and
bundled guidance command are exercised by the gate 3 contract test:
scripts/test_proportional_navigation.py against
scripts/proportional_navigation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_proportional_navigation.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.
