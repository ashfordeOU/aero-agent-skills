# Wave-29 leaf spec: coverage-path-planning (gnc-autonomy, guidance pack)

- Path: skills/gnc-autonomy/guidance/coverage-path-planning/
- Pack: guidance (existing siblings: command-to-line-of-sight,
  dubins-path-planning, impact-point-prediction, midcourse-guidance,
  proportional-navigation, pursuit-guidance)
- Standards ids: arp4754a (reference-only; the GNC guidance pack
  convention). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Plan an area-coverage search path for a fixed-wing UAS or rotorcraft
over a rectangular survey region: compute the ground swath width from
the sensor field of view and altitude, derive the track spacing from
the side-overlap requirement, lay out the boustrophedon (lawnmower)
passes with alternating direction, add the 180 degree turn segments
with the minimum turn radius, and sum the total path length and
estimated survey time at the cruise speed. Produces the swath width,
track spacing, pass count, pass headings, total path length, and
survey time that gate an aerial survey or search mission plan.

Does NOT do: plan a shortest path between two heading-constrained poses
(dubins-path-planning owns the Dubins CSC/CCC families); steer to a
moving target or intercept (proportional-navigation and
command-to-line-of-sight own terminal guidance); plan midcourse waypoint
routes (midcourse-guidance owns waypoint steering and velocity-to-be-
gained); compute flight-test point matrices
(flight-test-operations test-point-matrix-design owns the flight-test
point grid). This leaf plans the strip pattern that covers an area,
not the transit path to it.

## Model (implement exactly)

Module constants: none beyond math. All SI except where noted.

Functions (pure stdlib, floats):
- ground_swath(altitude, fov_cross_deg) -> float:
  sw = 2 * altitude * tan(pi/180 * fov_cross_deg / 2). ValueError on
  altitude <= 0 or fov not in (0, 180).
- track_spacing(swath, side_overlap) -> float:
  d = swath * (1 - side_overlap). ValueError on swath <= 0 or
  side_overlap outside [0, 0.95].
- pass_count(region_width, spacing) -> int:
  n = ceil(region_width / spacing). ValueError on region_width <= 0 or
  spacing <= 0.
- path_length(region_length, n_passes, turn_radius) -> float:
  straight = n_passes * region_length; each 180 degree turn is a
  half-circle of radius turn_radius: turn_len = pi * turn_radius;
  total = straight + turn_len * max(0, n_passes - 1). ValueError on
  negative inputs or turn_radius <= 0.
- survey_time(total_length, cruise_speed) -> float:
  t = total_length / cruise_speed. ValueError on cruise_speed <= 0.
- plan_coverage(region_length, region_width, altitude, fov_cross_deg,
  side_overlap, turn_radius, cruise_speed) -> dict: runs the chain and
  returns {swath_width, track_spacing, n_passes, straight_length,
  turn_length_total, total_length, cruise_speed, survey_time_s,
  pass_headings: [90.0, 270.0 alternating list length n_passes]}.
  pass 1 heading 90 deg (along region_length), every other pass 270
  deg (alternating boustrophedon). ValueErrors propagate.

## Worked example

Region 1200 m (length along the pass) by 800 m (width across passes);
altitude 120 m; cross-track FOV 60 deg; side overlap 25%; turn radius
60 m; cruise speed 25 m/s.

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- ground_swath(120, 60) = 138.56 m (within 0.01).
- track_spacing(138.56, 0.25) = 103.92 m (within 0.01).
- pass_count(800, 103.92) = 8 (800 / 103.92 = 7.70).
- path_length(1200, 8, 60) = 8*1200 + 7*pi*60 = 9600 + 1319.47 =
  10919.47 m (within 0.1).
- survey_time(10919.47, 25) = 436.78 s (within 0.1).
- A second worked case: swath 120 m with 25% overlap (spacing 90.0),
  800 m wide region gives 9 passes, straight 10800 m, turns 8*188.50 =
  1507.96 m, total 12307.96 m, time 492.32 s at 25 m/s (assert within
  0.5). This case exercises the ceil boundary: 800/90 = 8.89 -> 9.
- pass_headings for 9 passes start [90, 270, 90, 270, 90, 270, 90,
  270, 90].
- ValueErrors: altitude 0, fov 180, overlap 1.0, spacing 0, speed 0.

Keep at least 16 test methods: swath at 0/90/60 deg FOV, spacing
boundaries, ceil pass counts (exact-divide and over), path length with
1 pass (no turns) and 2 passes (one turn), alternating headings,
survey time, dict keys of plan_coverage, ValueErrors.

## Corpus tasks (ids w29-coverage-path-planning-1/2)

Distinctive tokens: coverage path planning, boustrophedon, lawnmower
pattern, aerial survey flight lines, swath width, side overlap, track
spacing, area search pattern. Avoid: Dubins path, minimum turn radius
path between poses, CSC CCC path families (dubins-path-planning);
waypoint steering, velocity-to-be-gained, midcourse (midcourse-
guidance); proportional navigation, LOS rate (proportional-navigation);
test point matrix, flight test grid (test-point-matrix-design).

1. "plan a boustrophedon coverage path for a 1200 by 800 m aerial
   survey at 120 m altitude with 60 degree cross-track FOV and 25
   percent side overlap: swath, track spacing, pass count, total
   length and survey time"
2. "lay out lawnmower search lines for a fixed-wing UAS over a
   rectangular region with 60 m turn radius and compute the flight
   time at 25 m/s"

## SKILL body notes

Pair with dubins-path-planning (transit to and between areas),
flight-test-operations test-point-matrix-design (test grids are a
different planning problem), part107-sora (operational rules frame
where a survey may fly). State the boundary to FMS lateral navigation
(avionics lateral-navigation owns airline route legs and cross-track
steering on airways, not area search strips). arp4754a is
reference-only for the development-assurance context of guidance
software. Mirror the guidance pack SKILL body style (SI units, stdlib
only, deterministic offline).
