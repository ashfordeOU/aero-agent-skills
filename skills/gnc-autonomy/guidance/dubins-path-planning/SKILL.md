---
name: dubins-path-planning
description: "Use when you must plan the shortest fixed wing path between two heading constrained poses with Dubins curves: compute the left and right arc centers for the minimum turn radius, find the outer or inner tangent points between the turn circles, form the six CSC and CCC path families (RSR, LSL, RSL, LSR, RLR, LRL), and select the minimum length path. Produces the Dubins path type, total length, segment lengths, arc centers, and waypoints that gate UAS path planning and waypoint guidance. Trigger: dubins path planning, minimum turn radius path, shortest path with heading constraints, CSC and CCC path families, arc tangent path, fixed wing turn radius, path length between poses."
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
  tags: [dubins-path-planning, minimum-turn-radius-path, dubins-curves, heading-constrained-path, csc-path-families, ccc-path-families, arc-tangent-path, fixed-wing-turn-radius, path-length-between-poses]
  version: 0.1.0
  author: Aero Agent Skills
---

# Dubins Path Planning (gnc-autonomy/guidance/dubins-path-planning)

Use when the task is planning the shortest feasible path for a
constant-speed, fixed wing UAS between two heading-constrained poses
under a minimum turn radius: geometry from Dubins curve families (CSC:
RSR, LSL, RSL, LSR and CCC: RLR, LRL), where each path is a sequence of
minimum radius arcs and straight segments that respects the start and
goal headings. This leaf implements the classic Dubins construction in
pure Python, stdlib only, in scripts/dubins_path_planning_logic.py. It
pairs with gnc-autonomy/guidance/pursuit-guidance and
proportional-navigation, which execute the resulting path against a
target, with avionics/flight-management/lateral-navigation for the FMS
waypoint steering counterpart, and with
flight-test-operations/uas/part107-sora for the operational context.
The model assumes constant speed and no wind; clothoid and
Reeds-Shepp (reversing) extensions are out of scope.

## Domain quick reference

- Pose convention: (x, y, heading) with heading in radians measured
  from the +x axis, counterclockwise positive; rho is the minimum turn
  radius (m).
- Left turn center (direction +1): (x - rho*sin(h), y + rho*cos(h)).
- Right turn center (direction -1): (x + rho*sin(h), y - rho*cos(h)).
- Outer (external) tangent: joins two same-sign turn circles; the
  straight segment is parallel to the center line and the tangent
  points sit rho from the centers, straight length equals the center
  separation d.
- Inner (internal) tangent: joins opposite-sign turn circles; exists
  only for center separation d >= 2*rho; straight length
  sqrt(d^2 - (2*rho)^2).
- CCC families (RLR, LRL): three arcs with an intermediate circle of
  radius rho externally tangent to both end circles; needed when the
  turn circles are too close for an inner tangent (d < 2*rho).
- Arc length: rho * |heading change|, with the change in [0, 2*pi)
  and sweep direction set by the turn sign (left increases heading,
  right decreases it).
- dubins_path returns the minimum length over all six families.

## Workflow

1. Fix the poses and the minimum turn radius: start and goal dicts with
   x, y and heading_rad keys plus rho in meters.
2. Get the arc centers with arc_center for both turn directions on the
   start and goal poses.
3. Find the tangent geometry with tangent_points (outer for same-sign
   turns, inner for opposite-sign turns); the inner tangent raises
   ValueError when the center separation is below 2*rho.
4. Assemble the CSC and CCC candidates with dubins_candidates, which
   returns each of the six families with its length or None when that
   family is infeasible.
5. Select the shortest with dubins_path, which returns the type, total
   length, segments, arc_centers and waypoints of the minimum path.
6. Confirm the deterministic checks with the contract test
   scripts/test_dubins_path_planning.py.

## Worked example

Start (0, 0, 0 rad), goal (100, 0, 0 rad), rho = 10 m.

- The straight run is feasible with two zero length arcs: dubins_path
  returns type LSL with total 100.0 m and a straight segment of 100.0 m
  (within 1e-6).

Start (0, 0, 0 rad), goal (0, 40, pi rad), rho = 10 m.

- The two opposite-heading turn circles sit 4*rho apart: type LSL with
  two 90 deg arcs (15.707963 m each) and a 20 m straight, total
  51.415927 m; the segment sum equals the total. RLR is infeasible
  (right-hand centers are 60 m apart, beyond 4*rho), LRL is feasible
  at 52.359878 m, and the RSL/LSR and RSR variants run longer.

Start (0, 0, 0 rad), goal (0, 10, pi/2 rad), rho = 10 m (d = 10 m
below 2*rho = 20 m).

- The LSR inner tangent does not exist at this spacing, so the CCC
  families supply the intermediate-circle paths: RLR is feasible at
  70.851881 m and LRL at 88.647027 m. The planner still returns the
  global minimum over all six families, type RSL at 69.993912 m
  (right arc 53.558901 m, straight 10.0 m, left arc 6.435011 m),
  because its RSL circle pair is 22.36 m apart and admits an inner
  tangent. All asserted checks hold on the feasible CCC candidates.

## Verification

- Confirm arc_center(0, 0, 0, 10, +1) returns (0, 10) and direction -1
  returns (0, -10); both centers sit exactly rho from the pose.
- Confirm tangent_points keeps every tangent point rho from its center
  within 1e-9 and raises ValueError when an opposite-sign pair is
  closer than 2*rho.
- Confirm the straight 100 m case returns 100.0 m (within 1e-6) with a
  100.0 m straight segment and the total matches the sum of segments.
- Confirm the d = 40 m opposite-heading case exceeds 20 m and that the
  segment lengths sum to the total.
- Confirm the d = 10 m close-pose case keeps the CCC candidates (RLR
  and LRL) feasible and finite above 10 m.
- Confirm the path length is invariant under reversing both poses with
  headings shifted by pi (within 1e-9).
- Confirm ValueError on rho <= 0, missing pose keys, and non-finite
  x, y, heading or rho values.
- Run the contract test offline: python3
  scripts/test_dubins_path_planning.py (32 tests, deterministic).

## Related leaves

- gnc-autonomy/guidance/pursuit-guidance: pure and lead pursuit
  steering that executes toward a moving target once a route exists.
- gnc-autonomy/guidance/proportional-navigation: terminal homing
  acceleration perpendicular to the line of sight.
- gnc-autonomy/guidance/midcourse-guidance: turn-rate-limited waypoint
  steering and handover shaping along a planned route.
- avionics/flight-management/lateral-navigation: FMS cross-track
  waypoint lateral navigation that follows a defined path.
- flight-test-operations/uas/part107-sora: operational context for the
  UAS that flies the planned path.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_dubins_path_planning.py

The test covers arc centers for both turn directions and arbitrary
headings, outer and inner tangents with the radius-distance invariant,
the inner tangent ValueError, the straight 100 m degenerate LSL path,
the d = 40 m opposite-heading total and segment-sum identity, the
d < 2*rho CCC feasibility case, family presence over all six names,
reversal symmetry, identical-pose zero length, segment positivity,
analytical stitching of every segment from the start pose to the goal
pose for every feasible family, and ValueError rejection of non-positive
rho, missing keys and non-finite values.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the guidance
  system development context for the UAS mission planner (reference
  only per standards-map.yaml).
- compliance: STANDARDS-REF, gated: false.
