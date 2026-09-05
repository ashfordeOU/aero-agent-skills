---
name: dme-arc-leg
description: "Use when you must compute the geometry of a constant-DME arc leg: the arc length between two radials at a published DME radius, a point on the arc at a given radial, the bank angle that holds the arc at a true airspeed, the turn radius implied by a bank angle, the chord between two arc fixes, and the signed radial intercept for joining or leaving the arc. Produces the arc length, arc points, holding bank angle, chord and intercept angle that gate a DME-arc procedure path check around a VOR/DME station. Trigger: dme arc leg, vor dme arc, arc length between radials, dme radius, arc bank angle, radial intercept, arc chord."
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
  tags: [dme-arc-leg, vor-dme-arc, arc-length-nm, arc-bank-angle, radial-intercept, arc-chord, dme-radius]
  version: 0.1.0
  author: AeroSkills
---

# DME Arc Leg (avionics/flight-management/dme-arc-leg)

Construct the lateral geometry of a constant-DME arc procedure leg flown
around a VOR/DME station: the arc length swept between two published
radials at the published DME radius, the arc point at a given radial,
the bank angle that holds the arc at a true airspeed, the turn radius
implied by a bank angle, the chord between two arc fixes, and the signed
radial intercept for joining or leaving the arc. This leaf implements
the plane trigonometry of the arc itself in pure stdlib Python; the
measured station distance and radial context belong to
radio-navigation-aids, straight track legs to lateral-navigation, and
course-tangent radius-to-fix legs to radius-to-fix-leg.

## Domain quick reference

- Arc length: L = r * delta, with delta the radial sweep in radians and
  r the published DME radius in nm. A 360 degree sweep returns the full
  circumference 2*pi*r.
- Point on the arc: station at the origin, x east and y north,
  x = r * sin(theta), y = r * cos(theta), with theta the radial measured
  clockwise from north in degrees.
- Bank angle that holds the arc: phi = atan(V^2 / (g * r)) in degrees,
  with V = tas_kt * 0.514444 in m/s, r = r_nm * 1852.0 in m and
  g = 9.80665 m/s^2.
- Turn radius from a bank angle: R = V^2 / (g * tan(phi)) in m,
  converted to nm. This is the inverse of the bank angle relation.
- Chord between two arc fixes: c = 2 * r * sin(delta / 2). A 180 degree
  sweep gives the diameter 2*r; a full sweep gives zero.
- Radial intercept: the smaller signed angular difference from the
  current radial to the target radial, in (-180, 180] degrees. Positive
  clockwise, negative counter-clockwise.
- The arc radius is the published horizontal procedure value, so no
  altitude or slant geometry is applied inside this arc model.

## Workflow

1. Fix the arc parameters: published DME radius r_nm, and the start and
   end radials of the procedure arc.
2. Compute the arc distance to fly with arc_length_nm on the radial
   sweep, and the straight-line leg across the arc with arc_chord_nm.
3. Get the fix coordinates on the arc with point_on_arc for each radial
   of interest (entry, exit, waypoint crossings).
4. Confirm the aircraft can hold the arc: arc_bank_angle_deg at the
   planned true airspeed against the turn radius from
   arc_turn_radius_nm, and verify the inverse identity
   (turn radius at the holding bank reproduces the arc radius).
5. Compute the radial intercept with radial_intercept_deg to plan the
   join to the arc inbound or the departure outbound, checking the sign
   convention against the direction of turn.
6. For a whole procedure segment, collect arc_length_nm, chord_nm,
   turn_angle_deg, start_point, end_point and midpoint_point from
   dme_arc_geometry.
7. Gate the path check against the deterministic contract test
   scripts/test_dme_arc_leg.py.

## Worked example

Published DME radius 12 nm, arc from radial 045 to radial 100, a 55
degree turn (module outputs):

- Arc length: arc_length_nm(12, 55) = 11.5192 nm (prep anchor 11.519).
- Chord: arc_chord_nm(12, 55) = 11.0820 nm (prep anchor 11.082).
- Start point on radial 045: (8.4853, 8.4853) nm; end point on radial
  100: (11.8177, -2.0838) nm, against the prep anchors (8.485, 8.485)
  and (11.819, -2.084).
- Holding bank at 180 kt: arc_bank_angle_deg(180, 12) = 2.2531 deg
  (anchor 2.25). The turn radius at 180 kt and 20 deg bank is
  arc_turn_radius_nm(180, 20) = 1.2972 nm (anchor 1.297).
- Radial intercept: radial_intercept_deg(45, 100) = +55 deg and
  radial_intercept_deg(100, 45) = -55 deg.
- Full geometry dict: arc length 11.5192 nm, chord 11.0820 nm, turn
  +55 deg, midpoint point on radial 072.5 at (11.4446, 3.6085) nm.

## Verification

- Confirm arc_length_nm(12, 360) = 75.3982 nm equals 2*pi*r and that
  arc_length_nm(12, 55) lands within 0.01 nm of 11.519.
- Confirm point_on_arc at radial 090 gives (12, 0) and at radial 000
  gives (0, 12).
- Confirm the bank/radius inverse identity for two speed-radius pairs:
  the turn radius at the holding bank recovers the input radius.
- Confirm arc_chord_nm(12, 180) = 24 nm and arc_chord_nm(12, 55) lands
  within 0.01 nm of 11.082.
- Confirm the radial intercept sign truth table: positive clockwise,
  negative counter-clockwise, including crossings of the 360/000
  radial.
- Confirm ValueError rejection of non-positive radius or airspeed, of
  bank angles outside (0, 90) degrees, and of radials or sweeps outside
  the published bands. Outputs are deterministic floats.
- Run the contract test offline: python3 scripts/test_dme_arc_leg.py
  (28 tests, deterministic).

## Related leaves

- avionics/flight-management/radio-navigation-aids: distance and
  radial measurement from station coordinates; it resolves the
  station-to-aircraft geometry that surrounds the published arc.
- avionics/flight-management/lateral-navigation: lateral track
  guidance between the straight flight plan legs that the arc joins.
- avionics/flight-management/radius-to-fix-leg: constant-radius
  radius-to-fix legs anchored on the entry fix and the inbound course,
  the course-tangent alternative to a station-centred arc.
- avionics/flight-management/flight-planning: route construction that
  carries the published DME arcs between waypoints.
- avionics/flight-management/holding-pattern-entry: holding entry
  geometry on the radial legs that meet the arc procedures.

## Pitfalls

- Treating the published DME radius as a measured distance: the arc
  radius is the horizontal procedure value (12 nm in the example), and
  the measured station distance carries altitude geometry that belongs
  to radio-navigation-aids, not to this arc model.
- Reading the radial backwards: a radial is the bearing from the
  station to the aircraft measured clockwise from north, so radial 090
  places the aircraft east of the station at (r, 0), not at (0, r).
- Slipping radians into a degrees interface: arc_length_nm expects the
  radial sweep in degrees and converts internally; feeding a radians
  value scales every length by about 57.3.
- Taking the long way around: radial_intercept_deg and
  dme_arc_geometry always return the smaller signed separation, so an
  arc planned the long way around the station is read as the opposite
  short-way turn.
- Mixing units in the bank checks: the inverse identity
  (arc_turn_radius_nm at the arc_bank_angle_deg output recovers the
  input radius) only holds with knots and nm on both sides.
- Ignoring wind on the arc: the holding bank angle is computed for the
  given true airspeed on a windless circular path; wind requires a
  corrected heading, and the radius at a fixed bank grows with the
  square of the speed.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_dme_arc_leg.py

The test covers the worked-example contract (arc length 11.519 nm,
chord 11.082 nm, start and end point anchors, 2.25 deg bank, 1.297 nm
turn radius), the arc length over 360 degrees equalling the
circumference 2*pi*r, the chord over 180 degrees equalling 2*r, the
bank/radius inverse identity for two speed-radius pairs, the radial
intercept sign truth table including 360/000 crossings, the
dme_arc_geometry dict fields and midpoint, and ValueError rejection of
non-positive radius, airspeed and out-of-range bank, radial and sweep
inputs. Exit 0 with 28 passing tests.

## Contract test

Run from the leaf directory: python3 scripts/test_dme_arc_leg.py. The
test imports the sibling logic module dme_arc_leg_logic (no network,
no third-party packages), asserts the worked-example module outputs
within the prep-verified bounds, checks the closed-form identities and
the error contract, and is fully deterministic, completing in well
under a second.

## Compliance

- Standards referenced, not reproduced: DO-178C frames the software
  lifecycle context for flight-management functions in the avionics
  family; this leaf provides standard engineering methodology
  (plane trigonometry) as summary guidance only, per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
