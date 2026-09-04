---
name: radio-navigation-aids
description: "Use when you must compute the radio navigation geometry of conventional navaids for the aircraft navigation solution: derive the VOR radial and the bearing from the aircraft to the station from the planar station and aircraft coordinates, compute the DME slant range from the ground distance and the aircraft altitude, compute the ILS localizer deviation angle from the lateral offset and the distance to the runway threshold, and compute the ILS glideslope deviation from the height above the threshold and the distance to the threshold against the nominal glideslope angle. Produces the VOR bearing and radial, the slant range, and the localizer and glideslope deviation angles that gate radio navigation geometry checks. Trigger: VOR radial, DME slant range, ILS localizer deviation, glideslope deviation, radio navigation geometry, bearing to the navaid station, approach course offset."
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
  tags: [radio-navigation-aids, vor-radial, dme-slant-range, ils-localizer-deviation, glideslope-deviation, radio-navigation-geometry, navaid-station-bearing, approach-course-offset]
  version: 0.1.0
  author: Aero Agent Skills
---

# Radio Navigation Aids (avionics/flight-management/radio-navigation-aids)

Use when the task is the receiver level geometry of conventional radio
navigation aids for the aircraft navigation solution: turning the
planar station and aircraft coordinates into the VOR bearing and
reciprocal radial, the DME slant range that the distance measuring
equipment reports, and the ILS localizer and glideslope deviation
angles that the approach receivers display against the runway
centerline and the nominal glidepath. This leaf implements that
geometry in pure Python, stdlib only, on the local tangent plane with
x east, y north and z up. It pairs with the sibling lateral-navigation
leaf, the FMS downstream consumer of the nav geometry, with
flight-planning for the route context, and with the gnc navigation
leaf that owns the position fix feeding the coordinates.

## Domain quick reference

- Coordinate convention: local tangent plane, x east (m), y north (m),
  z up (m). The VOR/DME station sits at the origin; the aircraft is at
  (x_ac, y_ac, altitude_m). Planar geometry is a documented
  simplification for short ranges; great-circle corrections are out of
  scope.
- Bearing from the station to the aircraft, clockwise from north:
  bearing = deg(atan2(x_ac, y_ac)) normalized to [0, 360). Due east
  gives 90 deg, due north 0 deg.
- VOR radial FROM the station: radial = (bearing + 180) mod 360, the
  reciprocal of the bearing the aircraft flies toward the station.
- DME slant range: d = sqrt(x_ac^2 + y_ac^2 + altitude_m^2). The DME
  measures the straight line from the station at ground level to the
  aircraft at altitude, so the slant range always exceeds the ground
  distance once the altitude is above zero.
- Localizer deviation: dev_loc = deg(atan(lateral_offset_m /
  distance_to_threshold_m)), positive when the aircraft is right of
  the localizer centerline (lateral offset to the right of the
  approach course is positive).
- Glideslope deviation: actual = deg(atan(height_agl_m /
  distance_to_threshold_m)); dev_gs = actual - gs_angle_deg, with the
  nominal glideslope default 3.0 deg and the deviation positive above
  the glidepath.
- Units are SI throughout: m, deg.
- DO-178C frames the software context of the nav receivers; the
  relations above are standard planar trigonometry, summary-only.

## Workflow

1. Take the aircraft position (x_ac, y_ac, altitude_m) in the local
   tangent frame with the VOR/DME station at the origin; flight-
   planning and the gnc position fix leaves provide the coordinates.
2. Get the bearing from the station with bearing_deg and the radial
   FROM the station with radial_deg of that bearing.
3. Get the DME answer with dme_slant_range_m; compare it against the
   ground distance to confirm the altitude contribution.
4. For the ILS localizer, feed the lateral offset and the distance to
   the runway threshold to loc_deviation_deg; a positive result means
   the aircraft is right of the centerline.
5. For the glideslope, feed the height above the threshold, the
   distance to the threshold and the nominal path angle to
   gs_deviation_deg; positive means above the glidepath.
6. For a full solution call analyze once with all inputs and read the
   dict of bearing, radial, slant range and both deviation angles.
7. Confirm the deterministic checks with the contract test
   scripts/test_radio_navigation_aids.py.

## Worked example

Aircraft 10 km east and 17.32 km north of the VOR/DME at 1000 m.

- Bearing: atan2(10000, 17320) = 30.0007 deg, within 0.01 of 30.0 deg.
- Radial: 30.0007 + 180 = 210.0007 deg, within 0.01 of 210.0 deg.
- Slant range: sqrt(1e8 + 2.999824e8 + 1e6) = sqrt(4.009824e8) =
  20024.5 m, within 1.0 m. The summary figure 20022.5 m in the wave-27
  spec came from rounding 17320^2 to 2.999e8 before summing; the exact
  value for the stated inputs is 20024.5 m (recorded assumption).
- Localizer: aircraft 100 m right of the centerline at 5000 m to the
  threshold gives dev = atan(100 / 5000) = 1.1458 deg.
- Glideslope against the 3 deg path at 5724 m to the threshold:
  at 300 m height the actual angle is 3.0002 deg and the deviation
  0.0002 deg; at 400 m the actual is 3.9974 deg and the deviation
  0.9974 deg, about 1 deg high.

## Verification

- Confirm bearing_deg(10000, 17320) is within 0.01 of 30.0 deg and
  radial_deg of it within 0.01 of 210.0 deg.
- Confirm dme_slant_range_m(10000, 17320, 1000) returns 20024.5 m and
  that a 3-4-5 triangle at zero altitude returns 5000.0 m exactly.
- Confirm loc_deviation_deg(100, 5000) returns 1.1458 deg and the
  zero-offset case returns 0.0 deg.
- Confirm gs_deviation_deg(300, 5724) is within 0.001 of 0.0002 deg,
  gs_deviation_deg(400, 5724) within 0.01 of 0.9974 deg, and the
  height on the nominal path returns near-zero deviation.
- Confirm the radial round trip: radial_deg applied twice returns the
  original bearing.
- Confirm ValueError rejection of negative altitude, non-positive
  distance to threshold, glideslope angle outside (0, 90) deg,
  negative height above ground, and non-finite inputs.
- Run the contract test offline: python3
  scripts/test_radio_navigation_aids.py (38 tests, deterministic).

## Related leaves

- avionics/flight-management/lateral-navigation: the FMS lateral
  guidance downstream of this nav geometry.
- avionics/flight-management/flight-planning: the route and leg
  context for the navaid geometry checks.
- avionics/flight-management/vertical-navigation: the FMS vertical
  profile that the glideslope intercept supports.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the position
  fix boundary feeding the aircraft coordinates.

## Pitfalls

- Confusing the bearing with the radial: bearing_deg is the direction
  FROM the station to the aircraft, while the VOR radial is the
  reciprocal (bearing + 180) mod 360 - a 030 bearing from the station
  puts the aircraft on the 210 radial, and applying radial_deg twice
  returns the original bearing.
- Using ground distance for the DME readout: the DME measures the
  slant range sqrt(x^2 + y^2 + altitude^2), which always exceeds the
  ground distance once the altitude is above zero (20024.5 m versus
  20000.0 m at 1000 m over the worked example) - altitude is not a
  second-order term in the DME answer.
- Reversing the deviation signs: localizer deviation is positive when
  the aircraft is RIGHT of the centerline and glideslope deviation is
  positive ABOVE the path - an aircraft below the glidepath carries a
  negative deviation and must correct up, not down.
- Comparing height to the path instead of angle: gs_deviation_deg
  computes the actual angle atan(height / distance) and subtracts the
  nominal 3.0 deg path, so 300 m at 5724 m is on-path (0.0002 deg)
  while 400 m is about 1 deg high - a fixed height error shrinks as
  the aircraft nears the threshold.
- Applying the planar model at long range: the local tangent plane
  with x east / y north is a documented simplification for short
  ranges and great-circle corrections are out of scope - do not
  stretch these station-local formulas across oceanic distances.
- Feeding non-physical geometry: negative altitude, non-positive
  distance to the threshold, glideslope angle outside (0, 90) deg,
  negative height above ground, and non-finite inputs raise ValueError
  in every entry point.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_radio_navigation_aids.py

The test covers the worked-example contract (bearing 30 deg, radial
210 deg, slant range 20024.5 m, localizer deviation 1.1458 deg,
glideslope deviations 0.0002 deg and 0.9974 deg), the cardinal
bearings and the [0, 360) normalization, the radial reciprocal round
trip, the DME slant versus ground distance behavior, zero and
symmetric deviation cases, and ValueError rejection of negative
altitude, non-positive distance, out-of-range glideslope angle,
negative height and non-finite inputs.

## Compliance

- Standards referenced, not reproduced: DO-178C frames the software
  life cycle of the nav receivers; the planar geometry above is
  standard engineering methodology, summary-only per standards-map.
- compliance: STANDARDS-REF, gated: false.
