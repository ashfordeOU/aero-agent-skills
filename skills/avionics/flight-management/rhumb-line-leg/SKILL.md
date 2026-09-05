---
name: rhumb-line-leg
description: "Use when you must compute the rhumb-line leg geometry between waypoints: derive the constant Mercator course and rhumb-line distance that connect two fixes, the along-parallel leg length at a fixed latitude, and the rhumb-versus-great-circle distance delta that gates long-range FMS leg and airway geometry checks. Produces the constant course in degrees, the rhumb distance in metres, the parallel leg length, and the comparison delta in metres and percent. Trigger: rhumb line leg, constant course leg, mercator course, parallel leg length, rhumb versus great circle, long range leg, fms leg geometry, waypoint leg distance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: do-178c
    reference-only: true
gated: false
domain: avionics
pack: flight-management
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: avionics
  subdomain: flight-management
  tags: [rhumb-line-leg, constant-course-leg, mercator-course, parallel-leg-length, rhumb-vs-great-circle, long-range-leg, fms-leg-geometry]
  version: 0.1.0
  author: AeroSkills
---

# Rhumb-Line Leg (avionics/flight-management/rhumb-line-leg)

Use when the task is the constant-true-course leg geometry between two
waypoints on the sphere: a rhumb line crosses every meridian at the
same angle, so it is the constant-heading segment an FMS compares
against the great-circle route when validating a long-range leg or an
airway. This leaf implements the spherical Mercator rhumb model in pure
Python, stdlib only: the isometric latitude, the constant Mercator
course, the rhumb-line distance, the along-parallel leg length, and the
rhumb-versus-great-circle distance delta for the same leg. It pairs
with the great-circle leg side handled by lateral-navigation and feeds
route geometry checks alongside flight-planning. It does NOT size
radius-to-fix arcs, holding patterns or DME geometry, which belong to
sibling leaves.

## Domain quick reference

- Model: spherical Earth radius R_EARTH = 6371.0e3 m (WGS-84 mean
  radius, documented module constant). Lat/lon in decimal degrees at
  the call boundary, radians in the math.
- Isometric latitude (meridional part): psi = ln(tan(pi/4 + lat/2)),
  radians. It diverges at the poles, so |lat| must stay below 90 for
  any leg that needs it.
- Rhumb course: course = degrees(atan2(delta_lon_rad, psi2 - psi1)),
  normalized to [0, 360). A pure parallel leg returns 90 (east) or 270
  (west); a meridian leg returns 0 (north) or 180 (south).
- Rhumb distance, diagonal leg: d = R * sqrt(dpsi^2 + dlon^2) *
  |dlat_rad| / |dpsi|. Pure parallel leg (dpsi ~ 0): d = R * |dlon_rad|
  * cos(lat).
- Along-parallel leg length: L = R * radians(delta_lon) *
  cos(radians(lat)), metres, signed along delta_lon.
- Great-circle distance: R * acos(sin(lat1) sin(lat2) + cos(lat1)
  cos(lat2) cos(delta_lon)), argument clamped to [-1, 1].
- Rhumb-versus-great-circle delta: delta_m = rhumb - gc, delta_pct =
  delta_m / gc * 100. The rhumb distance is never shorter than the
  great-circle distance, so delta_pct is >= 0 for every valid leg.

## Workflow

1. Read the leg endpoints as (lat1, lon1, lat2, lon2) in decimal
   degrees, all values validated to [-90, 90] latitude.
2. Form the meridional parts with isometric_latitude for each endpoint;
   a polar endpoint raises ValueError because psi is undefined there.
3. Get the constant bearing with rhumb_course_deg; expect 90 or 270 on
   a parallel leg and 0 or 180 on a meridian leg.
4. Get the flown distance with rhumb_distance_m; the pure-parallel
   branch is chosen automatically when the latitudes match.
5. For a leg published along a parallel, cross-check with
   parallel_leg_length_m(lat, delta_lon) against the rhumb distance.
6. For a long-range leg, run great_circle_distance_m and
   rhumb_vs_great_circle to quantify how far the constant-course leg
   departs from the great-circle route.
7. Apply the identities: meridian leg rhumb equals great circle; a
   parallel leg course is 90 or 270; delta is zero only on a meridian.
8. Confirm the deterministic checks with the contract test
   scripts/test_rhumb_line_leg.py before quoting numbers.

## Worked example

Anchor leg from 50N 000E to 55N 010E (module outputs):

- Constant course: 50.563 deg (spec anchor 50.56 within 0.1 deg).
- Rhumb distance: 875.236 km (spec anchor 875.24 within 1 km).
- Great-circle distance: 874.536 km, central angle 7.865 deg.
- Delta: 0.700 km at 0.080 percent; short mid-latitude leg, rhumb and
  great circle nearly coincide.
- Parallel leg at 55N over 10 deg of longitude: 637.788 km, identical
  to rhumb_distance_m(55, 0, 55, 10) for the pure-parallel case.

Long leg from 30N 030W to 55N 010E (same module):

- Rhumb distance: 4245.008 km against great circle 4203.796 km.
- Delta: 41.213 km at 0.980 percent, a leg where the constant-course
  difference is material for FMS route comparison.

Meridian leg 40N 020E to 60N 020E: rhumb equals great circle at
2223.899 km (R * 20 deg) with course 0.0; reversing gives course 180.0.

## Verification

- Confirm rhumb_course_deg(50, 0, 55, 10) returns 50.563 deg, within
  0.1 deg of the 50.56 anchor, and that parallel-only legs return
  exactly 90 and 270.
- Confirm rhumb_distance_m(50, 0, 55, 10) returns 875.236 km within
  1 km of the anchor and parallel_leg_length_m(55, 10) returns
  637.788 km within 1 km.
- Confirm the meridian identity holds to machine precision and that
  rhumb_distance_m is never below great_circle_distance_m.
- Confirm every latitude outside [-90, 90] and every delta_lon outside
  [-360, 360] raises ValueError, including polar endpoints for the
  isometric latitude.
- Confirm two runs of rhumb_vs_great_circle on the same leg return
  identical dicts (determinism).
- Run the contract test offline: python3
  scripts/test_rhumb_line_leg.py (35 tests, deterministic).

## Related leaves

- avionics/flight-management/lateral-navigation: the great-circle
  route geometry counterpart for waypoint-to-waypoint legs; this leaf
  is the constant-course side of the same comparison.
- avionics/flight-management/radius-to-fix-leg: the constant-radius
  arc leg geometry used in RNP AR procedures.
- avionics/flight-management/holding-pattern-entry: holding pattern
  entry geometry at the holding fix.
- avionics/flight-management/flight-planning: the route build that
  consumes leg distances for fuel and time along the plan.

## Pitfalls

- Quoting the great-circle distance for a constant-course leg: a
  heading-held leg follows the rhumb line, which is longer than the
  great-circle route (0.70 km over the anchor leg, 41.2 km over the
  long leg), so use rhumb_distance_m for the flown distance estimate.
- Forgetting the parallel branch: the diagonal rhumb formula divides
  by delta_psi, which is zero on a pure parallel leg; the module
  switches to R * |dlon| * cos(lat), and the course is exactly 90 or
  270, never a small angle.
- Sending a polar endpoint into a rhumb computation: psi is undefined
  at lat = +/-90, so the module raises ValueError; route legs that
  touch a pole need a different representation.
- Misreading parallel_leg_length_m sign: the result follows the sign
  of delta_lon (westward spans return negative), so take the absolute
  value when reporting a length, as rhumb_distance_m already does.
- Treating delta_pct as a constant: it grows with leg length and
  latitude span (0.08 percent at the anchor, 0.98 percent for the long
  leg), so the same tolerance cannot be reused across legs.
- Reading a course near 0 as small error: rhumb courses normalize to
  [0, 360), so a bearing just west of north reports near 360, not near
  0.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rhumb_line_leg.py

The test covers the anchor leg course 50.563 deg, rhumb distance
875.236 km and great-circle distance 874.536 km with central angle
7.865 deg, delta 0.700 km at 0.080 percent, the 637.788 km parallel
leg at 55N over 10 deg, the long leg delta 41.213 km at 0.980 percent,
the meridian identity rhumb equals great circle with courses 0 and
180, parallel courses 90 and 270, the rhumb-never-shorter bound,
isometric latitude reference values, ValueError rejection of
out-of-range latitudes and longitude spans, and run-to-run
determinism. All 35 tests pass offline in well under a second.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA/EUROCAE,
  reference-only per standards-map.yaml) frames the flight software
  context; the rhumb relations above are standard spherical Mercator
  engineering methodology, summary-only. compliance: STANDARDS-REF,
  gated: false.
