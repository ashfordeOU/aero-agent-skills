# Wave-27 leaf spec: dubins-path-planning (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/dubins-path-planning/
- Pack: guidance (existing siblings: pursuit-guidance,
  midcourse-guidance, impact-point-prediction, proportional-navigation,
  command-to-line-of-sight)
- Standards ids: arp4754a  (Ledger Standard: arp4754a)
- Family: gnc-autonomy

## Claim

Plan the shortest fixed-wing (constant-speed, minimum-turn-radius)
path between two heading-constrained poses with Dubins curves: from
the start pose (x, y, heading) and the goal pose with a minimum turn
radius, determine the path type among the six CSC/CCC families
(RSR, LSL, RSL, LSR, RLR, LRL), compute the path length, and output
the straight and arc segments with their turn directions. Produces the
Dubins path type, total length, segment lengths, and the arc centers
and endpoints that gate UAS path planning and waypoint guidance.

Does NOT do: compute pursuit, proportional-navigation, or
command-to-line-of-sight steering commands to intercept a moving
target (the sibling guidance leaves own intercept homing); solve
kinematic car-like motion with reversing (that is a Reeds-Shepp path,
out of scope); or compute the cross-track error and FMS waypoint
lateral navigation (avionics flight-management lateral-navigation).

## Model (implement exactly)

Geometry conventions:
- Pose is (x, y, heading) with heading in radians measured from the
  +x axis, counterclockwise positive.
- Minimum turn radius rho > 0. Left turn arcs are counterclockwise
  about a center offset by rho in the heading-normal direction;
  right turns are clockwise.

Inputs:
- start: dict {x, y, heading_rad},
- goal: dict {x, y, heading_rad},
- rho (float, minimum turn radius).

Functions:
- arc_center(x, y, heading_rad, rho, direction) -> (cx, cy):
  direction +1 = left (center at heading + 90 deg side),
  direction -1 = right (center at heading - 90 deg side):
  nx = -sin(heading), ny = cos(heading) (left normal);
  cx = x + rho * nx * direction? Implement exactly:
  left center = (x - rho*sin(heading), y + rho*cos(heading));
  right center = (x + rho*sin(heading), y - rho*cos(heading)).
- tangent_points(c1, c2, turn1, turn2) -> (p1, p2): external
  (same-direction) or internal (opposite-direction) tangents between
  the two circles of radius rho. For CSC paths: same-sign turns use the
  outer tangent; opposite-sign turns use the inner tangent (separation
  d >= 2*rho for inner tangents; the CCC paths handle the d < 2*rho
  case via an intermediate circle tangent to both).
  Standard construction (implement with atan2; assert the tangent
  points are at distance rho from their centers within 1e-9).
- path_length(type, pts...) -> float: sum of arc lengths (rho *
  |angle change|) plus the straight segment length.
- dubins_path(start, goal, rho) -> dict:
  {type, length, segments: [{kind: 'arc'|'straight', length,
  direction}], arc_centers, waypoints: [start_pt, tangent pts,
  goal_pt]}.
  Evaluate all six families and pick the minimum length. Return also
  {feasible: bool} always True for rho > 0 (the RLR/LRL families are
  always feasible for d >= 2*rho; for d < 2*rho the CCC family with
  an intermediate circle at rho handles it).

ValueError on: rho <= 0, missing start/goal keys, non-finite values.

## Worked example

start = (0, 0, 0 rad), goal = (100, 0, 0 rad), rho = 10.
- The straight-line path along +x is feasible: two zero-length arcs
  plus a 100 m straight, type LSL or RSL degenerates; the exact
  returned type may be LSL with length 100.0 (assert the total length
  is within 1e-6 of 100.0 and the straight segment is 100.0).
- start = (0, 0, 0), goal = (0, 40, pi), rho = 10: two circles tangent
  at distance 40 with opposite headings, d = 40 = 4*rho: the path is
  two arcs with a straight between them; assert total length > 20 and
  the segment sum equals the total.
- start = (0, 0, 0), goal = (0, 10, pi/2), rho = 10 (d = 10 < 2*rho):
  no inner tangent exists; assert the CCC family (RLR or LRL) yields a
  feasible path and total length is finite and > 10.
- Symmetry: path(start, goal, rho).length equals
  path(reverse(goal), reverse(start), rho).length (assert within 1e-9).
- ValueErrors on rho 0.
Keep at least 16 test methods (centers, tangents, six families,
degenerate straight, d<2rho, symmetry, ValueErrors). Use tolerance
1e-6 for lengths and 1e-9 for tangency geometry where noted.

## Corpus tasks (ids w27-dubins-path-planning-1/2)

Distinctive tokens: dubins path, minimum turn radius path, shortest
path with heading constraints, CSC and CCC path families, arc tangent
path, fixed wing turn radius, path length between poses. Avoid:
pursuit guidance, proportional navigation, line of sight, interception
(guidance siblings); cross track error, fly-by waypoint, FMS
(avionics lateral-navigation).

1. "plan the shortest dubins path for the fixed wing uas from the
   runway heading at the origin to the loiter entry pose 100 m ahead
   with the same heading and a 10 m minimum turn radius"
2. "compute the dubins path length and the arc and straight segments
   between the two heading constrained poses that are closer than two
   minimum turn radii apart, using the CCC path family"

## SKILL body notes

Pair with pursuit-guidance / proportional-navigation (path execution
contrast), avionics flight-management lateral-navigation (FMS
counterpart), and the UAS flight-test-operations part107-sora leaf
(operational context). Math is the standard Dubins set (CSC and CCC);
document that the leaf assumes constant speed and no wind and that
clothoid or Reeds-Shepp extensions are out of scope. Standards
referenced (ARP4754A guidance-system development context) not
reproduced.
