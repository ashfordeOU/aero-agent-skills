---
name: lateral-navigation
description: "Use when you must compute the lateral navigation (LNAV) guidance quantities of a flight management system between and along the flight plan legs: derive the great-circle track angle and distance from the current position to the next waypoint, determine the cross-track error to the active leg with its sign, compute the track angle error and the intercept heading that recaptures the desired track at a fixed intercept angle, size the turn anticipation distance before the fly-by waypoint from the speed and bank angle, and judge the along-track distance remaining on the leg. Produces the leg track and distance, the cross-track error, the intercept heading, and the fly-by versus fly-over transition point that gate FMS lateral guidance. Trigger: lateral navigation, lnav, cross-track error, track angle error, great-circle track, turn anticipation, fly-by waypoint, fly-over waypoint, intercept heading, fms lateral guidance."
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
  tags: [lateral-navigation, lnav, cross-track, track-angle-error, great-circle-track, turn-anticipation, fly-by-waypoint, fly-over-waypoint, intercept-heading, fms-lateral-guidance]
  version: 0.1.0
  author: Aero Agent Skills
---

# FMS Lateral Navigation (avionics/flight-management/lateral-navigation)

Use when the task is the lateral track guidance math of a flight
management system between the flight plan legs: the great-circle
geometry from the current position to the next waypoint, the deviation
of the aircraft from the active leg, and the turn that carries it
through the waypoint onto the next leg. This leaf implements the LNAV
guidance quantities in pure Python, stdlib only: track and distance to
the waypoint, cross-track error, track angle error, intercept heading,
turn anticipation distance, and the fly-by versus fly-over transition
verdict. It is the lateral counterpart of the sibling vertical-
navigation leaf (which owns the VNAV descent path) and consumes legs
built by flight-planning; speed and cost policy come from performance-
computation.

## Domain quick reference

- Spherical earth: great-circle formulas on a sphere of radius
  R = 6371000 m, inputs in radians; all angles are radians, distances
  meters, speed m/s, bank angle degrees.
- Initial great-circle track from A to B: track = atan2(sin(dLon) *
  cos(latB), cos(latA)*sin(latB) - sin(latA)*cos(latB)*cos(dLon)),
  normalized to [0, 2*pi). The track of a leg between two points on the
  same parallel is not the parallel direction: (50N, 0E) to (50N, 10E)
  starts at 86.17 deg because the arc bulges toward the pole.
- Distance: d = R * acos(sin(latA)*sin(latB) + cos(latA)*cos(latB)*
  cos(dLon)), with the acos argument guarded to [-1, 1]; identical
  points give 0 m while the direction functions raise ValueError.
- Cross-track error: xtk = asin(sin(d_AP/R) * sin(track_AB -
  track_AP)), returned as meters with a sign element. The equation as
  specified is positive when the position bears LEFT of the outbound
  leg (bearing from the leg start to the position smaller than the leg
  track angle); a display that defines positive = right of track
  negates the value.
- Along-track: atd = acos(cos(d_AP/R) / cos(xtk)) * R measured from A,
  projected with the spherical law of cosines; the distance to go to
  the waypoint B is max(0, leg_length - atd).
- Track angle error: tke = wrap(track_desired - track_current) to
  [-pi, pi), positive when a right turn (increasing track) closes the
  error. wrap maps any angle into [-pi, pi).
- Intercept: with tke beyond the fixed intercept angle (module
  constant 30 deg), the guidance heading is track_desired -
  sign(tke) * limit, recapturing the track at the fixed intercept
  angle from the closing side; inside the limit the aircraft holds the
  desired track.
- Turn anticipation: the turn at a fly-by waypoint starts d_ant before
  the waypoint, d_ant = R_turn * tan(|delta_track| / 2) with
  R_turn = v^2 / (g * tan(bank)); module default bank 25 deg. A zero
  track change is flown fly-over: d_ant = 0, turn at the waypoint.
- DO-178C frames the FMS function development context; the relations
  above are standard spherical trigonometry, summary-only.

## Workflow

1. Take the active leg endpoints A, B and the aircraft position P from
   the flight plan (flight-planning builds the legs).
2. Get the guidance track and the leg length with
   great_circle_track and great_circle_distance.
3. Measure the deviation from the leg with cross_track_error (meters
   plus sign) and the position along it with along_track_distance
   (distance to go to the waypoint B).
4. Compare the aircraft track against the leg with track_angle_error
   and get the capture course with intercept_heading when the aircraft
   has drifted off the leg.
5. Size the turn into the next leg with turn_anticipation_distance
   from the true airspeed and the track change at the waypoint, then
   classify the transition with waypoint_transition (fly-by versus
   fly-over and the turn start point).
6. Collect the quantities in the lnav_guidance summary dict for the
   guidance consumer.
7. Confirm the deterministic checks with the contract test
   scripts/test_lateral_navigation.py.

## Worked example

Leg from A (50N, 0E) to B (50N, 10E), aircraft at P (51N, 5E) tracking
040 deg at 90 m/s, track change 30 deg at B, bank 25 deg.

- great_circle_track(A, B) = 1.5039 rad = 86.166 deg. The leg is not
  flown along the 50N parallel: the great circle bulges north, so the
  initial course is 3.83 deg north of east (the parallel shortcut
  10 deg * cos(50) * R = 714.7 km would hold only for a rhumb line).
- great_circle_distance(A, B) = 714,214 m (714.2 km).
- cross_track_error at P: +99,239 m with sign +1. P bears left of the
  outbound leg (bearing A to P is 70.7 deg, less than the 86.2 deg leg
  track), and the specified equation is positive there. The mirror
  point (49N, 5E) on the right side gives -123,151 m, sign -1; the
  magnitudes differ because the great-circle arc runs north of the
  50N parallel, closer to 51N than to 49N.
- along_track_distance to B from P: 357,107 m (357.1 km).
- track_angle_error: tke = wrap(86.166 - 40) = +46.166 deg, a right
  turn of 46.2 deg onto the leg. intercept_heading returns 56.166 deg
  (86.166 - 30), the fixed-angle capture course.
- turn_anticipation_distance(90, 30 deg, 25 deg): turn radius
  90^2 / (9.80665 * tan 25 deg) = 1771.3 m and d_ant = 1771.3 *
  tan(15 deg) = 474.6 m. waypoint_transition classifies the leg as
  fly_by with the turn starting 474.6 m before B; a straight
  continuation (0 deg change) would be fly_over with the turn at B.

## Verification

- Confirm great_circle_distance(A, B) returns 714,214 m and
  great_circle_track(A, B) returns 1.5039 rad (86.166 deg).
- Confirm cross_track_error at (51N, 5E) returns +99,239 m with sign
  +1 and the mirror (49N, 5E) the opposite sign, and that on-track
  points (the waypoint B, points on the same meridian) return zero.
- Confirm along_track_distance returns 357,107 m at P, the full leg
  length at A, and zero at or beyond B.
- Confirm intercept_heading steers toward the leg: 56.166 deg from a
  40 deg current track, 116.166 deg from 140 deg, and the desired
  track itself when the error is within the 30 deg limit.
- Confirm turn_anticipation_distance(90, 30 deg, 25 deg) equals
  474.6 m and scales with the square of speed.
- Confirm every out-of-range latitude, non-finite value, non-positive
  speed, bank outside (0, 90) deg, |delta_track| at or beyond pi, and
  identical leg endpoint raises ValueError.
- Run the contract test offline: python3
  scripts/test_lateral_navigation.py (33 tests, deterministic).

## Related leaves

- avionics/flight-management/flight-planning: builds and checks the
  flight plan legs this leaf guides along.
- avionics/flight-management/vertical-navigation: the VNAV descent
  path, the vertical counterpart of this lateral leaf.
- avionics/flight-management/performance-computation: ECON speed and
  cost policy that set the speed input for the turn anticipation.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_lateral_navigation.py

The test covers the worked great-circle leg (track 86.166 deg, 714.2
km), track normalization and reversal on symmetric legs, known
distances (quarter and half equator, meridian degrees), the cross-track
sign and magnitude at (51N, 5E) and its mirror, zero cross-track on
leg, the along-track distance to go at the leg start, midpoint and
beyond the waypoint, track angle error wrapping, the fixed-angle
intercept capture both sides of the track and across 0 deg, the turn
anticipation contract at 90 m/s with a 30 deg change at 25 deg bank,
the fly-by versus fly-over classification, the lnav_guidance summary
consistency, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA) frames the
  development of flight management functions; the great-circle
  relations above are standard spherical trigonometry, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
