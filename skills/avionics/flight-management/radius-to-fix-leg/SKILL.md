---
name: radius-to-fix-leg
description: "Use when you must construct the lateral path of a radius-to-fix leg: compute the turning center of the constant-radius RF leg for an RNP AR procedure from the entry fix, the inbound track, the published radius and the turn direction, validate that the exit fix lies on the radius circle, and derive the swept central angle, the along-arc length, the exit track and the chord. Produces the RF-leg geometry dict that gates a flyable-arc check for procedure design. Trigger: radius to fix, RF leg, turn center, arc length, path terminator, rnp ar procedure, constant radius arc, flyable arc check."
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
  tags: [radius-to-fix-leg, rnp-ar-procedure, rf-leg-geometry, turn-center, arc-length, path-terminator, flyable-arc-check]
  version: 0.1.0
  author: AeroSkills
---

# Radius-to-Fix Leg (avionics/flight-management/radius-to-fix-leg)

Use when the task is the lateral path construction of a published
radius-to-fix (RF) leg for an RNP AR procedure: a constant-radius arc
flown from an entry fix to an exit fix around a turning center that is
fixed by the inbound track and the turn direction. This leaf implements
the RF-leg geometry in pure Python, stdlib only: the turning center,
the exit-fix-on-circle check, and the swept central angle, along-arc
length, exit track and chord that gate the flyable-arc check for
procedure design. It is the constant-radius arc companion of the
lateral-navigation leaf (which sizes the transition turns between
legs) and feeds procedure legs checked against containment by
rnp-anp-containment.

## Domain quick reference

- Frame and units: local tangent plane with x = east (NM), y = north
  (NM); entry fix EF = (x_ef, y_ef), exit fix XF = (x_xf, y_xf).
  The inbound track is the true course INTO the RF leg at EF, degrees
  clockwise from north. Radius R in NM, turn direction RIGHT or LEFT.
- Center side: for inbound track t, the inbound unit vector is
  d = (sin t, cos t). The center lies at distance R from EF on the
  turn side: C = EF + R * n_right for RIGHT with n_right = (cos t,
  -sin t), C = EF + R * n_left for LEFT with n_left = (-cos t, sin t).
  Eastbound (090) RIGHT travel with R = 15 NM centers at (0, -15),
  south of the track; LEFT centers at (0, +15).
- Exit validation: |XF - C| == R within tolerance tol_nm (default
  1e-6 NM); rf_exit_on_arc reports the boolean verdict.
- Swept central angle: the angle from the EF radius to the XF radius
  along the turn direction, computed with the two-argument atan2 of the
  radius vectors (counter-clockwise angle for LEFT, 360 minus that
  angle for RIGHT), reported in degrees 0..360. EF == XF is a
  degenerate zero-length arc, 0 deg; distinct points always sweep
  strictly inside (0, 360), so a near-full-circle arc never wraps to 0.
- Arc length: s = R * Delta_psi with Delta_psi in radians.
- Exit track: the flight tangent at XF continuing the turn. With
  bearing_radial = atan2(x_xf - cx, y_xf - cy) in compass degrees,
  RIGHT adds 90 deg and LEFT subtracts 90 deg, normalized to 0..360.
- Chord: |XF - EF|, the straight distance between the two fixes.
- DO-178C frames the flight management function development context;
  RF-leg geometry is public PBN and ARINC-424 material (FAA AC 90-105
  frames RNP AR procedure design), summary-only here.

## Workflow

1. Take the EF and XF coordinates, the inbound track at EF, the
   published radius R and the turn direction from the procedure
   (ARINC-424 RF record).
2. Locate the turning center with rf_turn_center: EF offset by R on
   the right or left normal of the inbound direction.
3. Verify the published exit fix lies on the radius circle with
   rf_exit_on_arc (default tolerance 1e-6 NM).
4. Sweep the arc: rf_arc_angle_deg gives the central angle from the EF
   radius to the XF radius along the turn, and rf_arc_length_nm turns
   it into the along-arc distance s = R * radians(angle).
5. Derive the tangent at the exit with rf_exit_track_deg (radial
   bearing plus 90 deg for RIGHT, minus 90 deg for LEFT) and the
   straight distance with rf_chord_nm.
6. Collect everything with rf_leg_construct, which returns the
   geometry dict {center_nm, exit_on_arc, sweep_deg, arc_length_nm,
   exit_track_deg, chord_nm, valid}, where valid = exit_on_arc and
   sweep_deg > 0. Feed valid into the flyable-arc check for the
   procedure design.
7. Confirm the deterministic checks with the contract test
   scripts/test_radius_to_fix_leg.py.

## Worked example

Case 1: EF (0, 0), XF (15, -15), inbound track 090, RIGHT, R = 15 NM
(the quarter-circle arc south of the eastbound track).

- rf_turn_center: center (0.000, -15.000), the point 15 NM south of
  the eastbound entry.
- rf_exit_on_arc: True, |XF - C| = 15.000 NM equals R.
- rf_arc_angle_deg: 90.000 deg. The EF radius points north (bearing
  000) and the XF radius points east (bearing 090) of the center.
- rf_arc_length_nm: 23.562 NM (15 * pi / 2), matching the magnitude
  bound of the spec.
- rf_exit_track_deg: 180.0 deg, the east radius tangent continuing the
  clockwise turn points south.
- rf_chord_nm: 21.213 NM, the straight distance |(15, -15)|.
- rf_leg_construct dict: center (0.000, -15.000), exit_on_arc True,
  sweep_deg 90.000, arc_length_nm 23.562, exit_track_deg 180.0,
  chord_nm 21.213, valid True.

Case 2: R = 8 NM with a 60 deg sweep gives rf_arc_length_nm 8.3776 NM
(8 * pi / 3).

Case 3: XF (15, 15) against the case-1 center: |XF - C| = 33.541 NM,
not 15, so rf_exit_on_arc is False and the rf_leg_construct dict has
valid False. The exit fix does not lie on the published arc.

Case 4: the same EF and track flown LEFT centers at (0.000, +15.000),
the mirror of case 1; an XF of (15, 15) closes a valid 90 deg arc
about that center with exit track 0.0 deg.

## Verification

- Confirm rf_turn_center((0, 0), 90, 15, "RIGHT") returns center
  (0.000, -15.000) and the LEFT mirror (0.000, +15.000).
- Confirm rf_exit_on_arc((0, -15), (15, -15), 15) is True and that a
  point 33.541 NM from the center is rejected.
- Confirm rf_arc_angle_deg returns 90.000 deg for case 1, that LEFT
  and RIGHT sweeps of one geometry are complementary (sum 360 deg),
  that a 180 deg RIGHT arc exits at inbound + 180, and that EF == XF
  yields the degenerate 0 deg sweep.
- Confirm rf_arc_length_nm(15, 90) returns 23.562 NM and
  rf_arc_length_nm(8, 60) returns 8.3776 NM.
- Confirm rf_exit_track_deg returns 180.0 deg for case 1 and stays
  normalized to 0..360 across the north wrap.
- Confirm every radius <= 0, every invalid turn direction, and every
  non-finite EF or XF coordinate raises ValueError in every entry
  point.
- Run the contract test offline: python3
  scripts/test_radius_to_fix_leg.py (33 tests, deterministic).

## Related leaves

- avionics/flight-management/lateral-navigation: the fly-by
  anticipation sibling that sizes when to start transition turns; this
  leaf owns the constant-radius arc itself.
- avionics/flight-management/rnp-anp-containment: the containment
  verdict around the procedure path this leaf constructs.
- avionics/flight-management/vertical-navigation: the VNAV descent
  path paired with the RF legs on the procedure.

## Pitfalls

- Flipping the center side: RIGHT offsets the center by R on
  n_right = (cos t, -sin t) and LEFT on n_left = (-cos t, sin t), so
  an eastbound RIGHT arc centers at (0, -15) and the LEFT mirror at
  (0, +15) - a swapped direction puts the center on the wrong side
  and every downstream quantity is wrong by twice the radius.
- Mixing degrees into the arc length: s = R * radians(sweep), so the
  case-1 quarter circle is 15 * pi / 2 = 23.562 NM, not 15 * 90 -
  compute the central angle in degrees but convert to radians before
  multiplying.
- Trusting an exit fix without the on-arc check: the published XF must
  satisfy |XF - C| == R within tol_nm (default 1e-6 NM); an XF
  33.541 NM from the case-1 center fails rf_exit_on_arc and the
  rf_leg_construct dict carries valid False - valid = exit_on_arc and
  sweep_deg > 0.
- Reading a zero sweep as a wrap: EF == XF is the degenerate 0 deg
  zero-length arc, while distinct points always sweep strictly inside
  (0, 360) - a near-full-circle arc never wraps to 0, so do not treat
  a 359 deg arc as a 1 deg arc in the other direction.
- Adding instead of subtracting the exit tangent: the exit track is
  the radial bearing plus 90 deg for RIGHT and minus 90 deg for LEFT,
  normalized to 0..360 - the case-1 east radius tangent points south
  (180.0 deg), and normalization matters across the north wrap.
- Flying the chord instead of the arc: the aircraft follows the
  constant-radius arc (23.562 NM in case 1), not the straight
  |XF - EF| chord of 21.213 NM - the downstream flyable-arc and
  containment checks consume the swept geometry, not the chord.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_radius_to_fix_leg.py

The test covers the case-1 anchors (center (0, -15), exit on arc, sweep
90.000 deg, arc 23.562 NM, exit track 180.0 deg, chord 21.213 NM), the
case-2 arc length 8.3776 NM at R = 8 NM, the case-3 rejection of an
exit fix 33.54 NM from the center, the case-4 LEFT mirror center
(0, +15) and its valid 90 deg arc, cardinal-direction center sides,
the exit-on-arc tolerance band, complementary RIGHT versus LEFT
sweeps summing to 360 deg, the near-full-circle sweep that never wraps
to 0, exit-track normalization across 0 deg, the exactly documented
geometry-dict keys, run-to-run determinism, and ValueError rejection
of non-positive radius, invalid turn directions and non-finite
coordinates.

## Compliance

- Standards referenced, not reproduced: DO-178C (RTCA) frames the
  development of flight management functions; RF-leg geometry is public
  PBN and ARINC-424 material and FAA AC 90-105 is a public advisory
  circular, so only names and paraphrases appear here, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
