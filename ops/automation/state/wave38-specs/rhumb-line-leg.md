# Wave-38 leaf spec: rhumb-line-leg (avionics, flight-management pack)

- Path: skills/avionics/flight-management/rhumb-line-leg/
- Pack: flight-management. Closest siblings: lateral-navigation (great-
  circle track and distance between waypoints, cross-track error, turn
  anticipation - its SKILL.md body explicitly DISCLAIMS rhumb lines:
  "10 deg * cos(50) * R = 714.7 km would hold only for a rhumb line" and
  "a leg along a parallel is not flown [as GC]"), radius-to-fix-leg (RF
  arc), holding-pattern-entry, flight-planning, dme-arc-leg. Whole-tree
  grep: "rhumb" = exactly ONE hit, lateral-navigation, and that hit is a
  disclaimer boundary, not a function. ZERO owners of rhumb-line leg
  geometry. GENUINE AV gap (fresh probe).
- Standards id: do-178c (reference-only; flight-management sibling
  convention). Ledger Standard: do-178c.
- Family: avionics

## Claim

Compute the constant-true-course (rhumb line) leg geometry between two
waypoints on the sphere: derive the rhumb-line distance and the constant
Mercator course that connects the waypoints, compute the along-parallel
leg length at a fixed latitude, and quantify the difference between the
rhumb-line distance and the great-circle distance for the leg. Produces
the rhumb distance, the constant course, the parallel leg length, and the
rhumb-versus-great-circle delta that gate FMS long-range leg and airway
geometry checks. Does NOT do: great-circle track and distance (lateral-
navigation); RF radius-to-fix leg geometry (radius-to-fix-leg); DME arc
geometry (dme-arc-leg).

## Model (implement exactly)

Conventions: WGS-84 spherical Earth radius R_EARTH = 6371.0e3 m (documented
model constant); lat/lon in degrees in user-facing functions, radians in
the math. Rhumb-line course: the constant bearing that intersects every
meridian at the same angle. Meridional parts (isometric latitude):
psi = ln(tan(pi/4 + lat/2)) in radians.

Functions (pure stdlib):
- isometric_latitude(lat_deg) -> float: ln(tan(pi/4 + radians(lat)/2)).
- rhumb_course_deg(lat1, lon1, lat2, lon2) -> float in [0, 360): course =
  atan2(delta_lon_rad, psi2 - psi1) converted to degrees, normalized;
  when delta_lat is zero the course is 90 or 270 degrees (due east or
  west along the parallel). ValueError on out-of-range latitudes.
- rhumb_distance_m(lat1, lon1, lat2, lon2) -> float: the rhumb distance =
  R * sqrt((delta_psi)^2 + (delta_lon_rad)^2) * |delta_lat_rad| /
  |delta_psi| when delta_psi is nonzero (the spherical Mercator rhumb
  formula), or R * |delta_lon_rad| * cos(lat) for a pure parallel leg.
  ValueErrors: lat outside [-90, 90].
- parallel_leg_length_m(lat_deg, delta_lon_deg) -> float: R *
  radians(delta_lon) * cos(radians(lat)). ValueError: delta_lon outside
  [-360, 360]; lat outside [-90, 90].
- great_circle_distance_m(lat1, lon1, lat2, lon2) -> float: R *
  acos(sin(lat1) sin(lat2) + cos(lat1) cos(lat2) cos(delta_lon)).
- rhumb_vs_great_circle(lat1, lon1, lat2, lon2) -> dict {rhumb_m,
  great_circle_m, delta_m, delta_pct} with delta_pct = (rhumb - gc) / gc
  * 100.
Identity to test: a north-south leg along a meridian has rhumb distance
equal to great-circle distance and course 0 or 180; a pure parallel leg
has course 90/270 and rhumb distance equal to parallel_leg_length; the
rhumb distance is never shorter than the great-circle distance.

## Worked example

Verified at prep: leg from 50N 000E to 55N 010E:
- rhumb course = 50.56 deg.
- rhumb distance = 875.24 km.
- great-circle distance = 874.54 km (central angle 7.865 deg).
- delta = 0.70 km, delta_pct = 0.08 percent (short mid-latitude leg;
  rhumb and great-circle nearly coincide).
- Long-leg delta example (same module, 30N 030W to 55N 010E): rhumb
  4245.0 km, great-circle 4203.8 km, delta 41.2 km, delta_pct 0.98
  percent (computed at prep - a leg where the rhumb/great-circle
  difference is material for FMS route comparison).
- parallel leg at 55N over 10 deg of longitude = 637.79 km.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the spherical Mercator relations and
the great-circle formula.

## Validation list (contract test must include)

- rhumb course 50.56 deg within 0.1 deg for the anchor leg; parallel-only
  legs return 90/270.
- rhumb distance 875.24 km within 1 km of the anchor; parallel leg 637.79
  km within 1 km.
- Meridian leg: rhumb == great circle (within a small tolerance), course
  0/180.
- delta_pct positive for a diagonal leg; zero for a meridian leg.
- ValueErrors: lat outside [-90, 90], delta_lon outside [-360, 360].
- Determinism.

## Corpus fragment (eval/hit1-wave38-rhumb-line-leg.yaml)

Query 1 (copy verbatim):
  "compute the rhumb-line-leg distance and constant mercator course between two waypoints at constant track"
  intent: "avionics; rhumb line leg geometry at constant course"
  expected_skill: "avionics/flight-management/rhumb-line-leg"
Query 2 (copy verbatim):
  "find the along-parallel rhumb-line leg length at latitude 55 and the rhumb-versus-great-circle distance delta"
  intent: "avionics; parallel rhumb leg and great circle comparison"
  expected_skill: "avionics/flight-management/rhumb-line-leg"
Task ids: w38-rhumb-line-leg-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the rhumb-line leg
geometry between waypoints:" and include the outputs in the Claim. First
tag: rhumb-line-leg. Additional tags ONLY: constant-course-leg,
mercator-course, parallel-leg-length, rhumb-vs-great-circle, long-range-
leg, fms-leg-geometry. NEVER single generic words (rhumb, course, leg,
distance, waypoint, track). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): great-circle track, cross-track
error, turn anticipation (lateral-navigation); RF leg (radius-to-fix-leg);
holding entry sectors (holding-pattern-entry); DME arc (dme-arc-leg).
