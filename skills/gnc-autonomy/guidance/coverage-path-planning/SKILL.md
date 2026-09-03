---
name: coverage-path-planning
description: "Use when you must plan a boustrophedon area-coverage search path for a fixed-wing UAS or rotorcraft over a rectangular survey region: compute the ground swath width from the sensor cross-track field of view and altitude, derive the track spacing from the required side overlap, lay out the alternating lawnmower passes, add the 180 degree half-circle turns at the vehicle turn radius, and sum the total path length and survey time at cruise speed. Produces the swath width, track spacing, pass count, pass headings, total path length and survey time that gate an aerial survey or search mission plan. Trigger: coverage path planning, boustrophedon, lawnmower pattern, aerial survey flight lines, swath width, side overlap, track spacing, area search pattern."
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
  tags: [coverage-path-planning, boustrophedon, lawnmower-pattern, aerial-survey-flight-lines, swath-width, side-overlap, track-spacing, area-search-pattern]
  version: 0.1.0
  author: Aero Agent Skills
---

# Coverage Path Planning (gnc-autonomy/guidance/coverage-path-planning)

Use when the task is laying out the strip pattern that covers a
rectangular area for an aerial survey or search mission: a
boustrophedon (lawnmower) set of straight passes alternated 90/270
degrees and joined by 180 degree half-circle turns at the vehicle turn
radius. This leaf implements the standard coverage geometry in pure
Python, stdlib only, in scripts/coverage_path_planning_logic.py. It
pairs with gnc-autonomy/guidance/dubins-path-planning, which plans the
shortest heading-constrained transit path to and between survey areas,
and with flight-test-operations/planning/test-point-matrix-design, whose
flight-test point grids are a different planning problem.
flight-test-operations/uas/part107-sora frames the operational rules
that decide where a survey may fly. The boundary to FMS routing is
explicit: avionics/flight-management/lateral-navigation owns airline
route legs and cross-track steering on airways, not area search strips.
ARP4754A appears reference-only as the development-assurance context for
guidance software. Model assumptions: flat terrain, constant cruise
speed, no wind, and turns flown at the given turn radius.

## Domain quick reference

- Ground swath width from altitude h and cross-track field of view
  fov: sw = 2*h*tan(pi/180*fov/2). Wider FOV or higher altitude widens
  the swath.
- Track spacing from the side overlap fraction o: d = sw*(1 - o).
  Zero overlap spaces tracks a full swath apart; 25 percent overlap
  leaves d = 0.75*sw.
- Pass count across the region width W: n = ceil(W/d). The ceiling
  means the last pass may cover less than a full spacing.
- Pass headings alternate: pass 1 at 90 degrees (along the region
  length), pass 2 at 270 degrees, and so on (boustrophedon).
- Straight legs total n*L where L is the region length along a pass.
- Each 180 degree turn is a half circle of radius r_turn with length
  pi*r_turn, flown between passes i and i+1; there are n - 1 turns for
  n >= 2 and none for a single pass.
- Total path length: L_total = n*L + pi*r_turn*max(0, n - 1).
- Survey time at cruise speed V: t = L_total/V.

## Workflow

1. Compute the swath: ground_swath(altitude, fov_cross_deg). Non-
   physical altitude or an FOV outside (0, 180) degrees raises
   ValueError.
2. Derive the spacing: track_spacing(swath, side_overlap). Side
   overlap must lie in [0, 0.95]; 1.0 would collapse the spacing to
   zero and raises ValueError.
3. Count the passes: pass_count(region_width, spacing), an integer
   ceiling of the width over the spacing.
4. Sum the path: path_length(region_length, n_passes, turn_radius),
   straight legs plus half-circle turns.
5. Estimate the flight time: survey_time(total_length, cruise_speed).
6. Run the whole chain in one call with plan_coverage(region_length,
   region_width, altitude, fov_cross_deg, side_overlap, turn_radius,
   cruise_speed), which returns the summary dict below.

plan_coverage returns swath_width, track_spacing, n_passes,
straight_length, turn_length_total, total_length, cruise_speed,
survey_time_s and pass_headings, where pass_headings is the alternating
[90.0, 270.0, ...] list of length n_passes.

## Worked example

Survey region 1200 m by 800 m (length along the pass 1200 m, width
across passes 800 m), altitude 120 m, cross-track FOV 60 degrees, side
overlap 25 percent, turn radius 60 m, cruise speed 25 m/s.

- ground_swath(120, 60) = 2*120*tan(30 deg) = 138.56 m.
- track_spacing(138.56, 0.25) = 103.92 m.
- pass_count(800, 103.92) = ceil(7.70) = 8 passes.
- path_length(1200, 8, 60) = 8*1200 + 7*pi*60 = 9600 + 1319.47 =
  10919.47 m.
- survey_time(10919.47, 25) = 436.78 s, about 7.3 minutes.
- Headings: [90, 270, 90, 270, 90, 270, 90, 270].

Ceil-boundary case: swath 120 m with 25 percent overlap gives spacing
90.0 m, and 800/90 = 8.89 rounds up to 9 passes. Then straight length
10800 m, turns 8*188.50 = 1507.96 m, total 12307.96 m, time 492.32 s
at 25 m/s, headings [90, 270, 90, 270, 90, 270, 90, 270, 90].

## Verification

Run the contract test offline and deterministically:

    python3 skills/gnc-autonomy/guidance/coverage-path-planning/scripts/test_coverage_path_planning.py

It asserts the worked-example anchors above (swath 138.56 m within
0.01, spacing 103.92 m within 0.01, 8 passes, total 10919.47 m within
0.1, time 436.78 s within 0.1, and the 9-pass ceil-boundary case
12307.96 m and 492.32 s within 0.5), FOV and overlap boundaries,
single-pass and two-pass turn accounting, alternating headings for 8
and 9 passes, the plan_coverage dict keys, and ValueError rejection of
non-physical inputs (altitude 0, FOV 180, overlap 1.0, zero spacing,
zero speed).

## Related leaves

- gnc-autonomy/guidance/dubins-path-planning (heading-constrained
  transit path to and between areas)
- gnc-autonomy/guidance/pursuit-guidance, proportional-navigation and
  command-to-line-of-sight (terminal guidance, not area planning)
- gnc-autonomy/guidance/midcourse-guidance (waypoint steering and
  handover, not strip patterns)
- flight-test-operations/planning/test-point-matrix-design (flight-test
  point grids)
- flight-test-operations/uas/part107-sora (operational rules for UAS
  surveys)
- avionics/flight-management/lateral-navigation (FMS route legs, the
  boundary this leaf does not cross)

## Contract test

scripts/test_coverage_path_planning.py is a stdlib unittest contract
test with 35 methods covering swath, spacing, pass count, path length,
survey time and the plan_coverage summary. It runs offline in under a
second and exits 0 on success.

## Compliance

STANDARDS-REF. This leaf references ARP4754A as the development
assurance context for guidance software design; the standard text is
named, not reproduced. Gated: false.
