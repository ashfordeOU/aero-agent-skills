# Wave-38 leaf spec: dme-arc-leg (avionics, flight-management pack)

- Path: skills/avionics/flight-management/dme-arc-leg/
- Pack: flight-management. Closest siblings: radio-navigation-aids (VOR
  bearing and radial, DME SLANT RANGE, ILS localizer and glideslope
  deviations from station coordinates - it computes the distance to a
  navaid, not the arc procedure geometry), lateral-navigation (great-circle
  track guidance between flight plan legs), radius-to-fix-leg (RF leg:
  constant-radius arc with the turning center derived from the entry fix
  and the inbound track - a course-tangent RF leg, not a station-centred
  DME arc), flight-planning. Whole-tree grep: "dme-arc", "DME arc",
  "constant DME" = ZERO owning hits; radio-navigation-aids owns "DME slant
  range" only. ZERO owners of the DME-arc procedure geometry. GENUINE AV
  gap (fresh probe).
- Standards id: do-178c (reference-only; flight-management sibling
  convention). Ledger Standard: do-178c.
- Family: avionics

## Claim

Construct the lateral geometry of a constant-DME arc procedure leg around
a VOR/DME station: compute the arc length between two radials at the
published DME radius, find a point on the arc at a given radial, derive
the bank angle that holds the arc at a given true airspeed, compute the
chord between two arc fixes, and estimate the radial intercept geometry
for joining or leaving the arc. Produces the arc length, the arc points,
the holding bank angle, the chord, and the intercept angle that gate a
DME-arc procedure path check. Does NOT do: DME slant range and VOR bearing
to a station (radio-navigation-aids); great-circle lateral track guidance
(lateral-navigation); RF radius-to-fix leg construction (radius-to-fix-leg).

## Model (implement exactly)

Conventions: angles in degrees for user-facing functions, radians in
computations; nautical miles for distances; the DME radius r is the
published arc radius from the VOR/DME station (horizontal, so slant range
correction is not applied in this arc geometry - the arc radius is a
published procedure value).

Functions (pure stdlib):
- arc_length_nm(r_nm, delta_radial_deg) -> float: r_nm * radians(delta).
  ValueError: r_nm <= 0; delta outside [0, 360].
- point_on_arc(r_nm, radial_deg) -> (x_nm, y_nm): station at origin,
  x = r * sin(radians(radial)), y = r * cos(radians(radial)) (radial
  measured clockwise from north, x east, y north).
- arc_bank_angle_deg(tas_kt, r_nm) -> float: bank = atan(V**2 / (g * r))
  with V = tas_kt * 0.514444 (m/s), r = r_nm * 1852.0 (m),
  g = 9.80665. Returns degrees. ValueError: tas <= 0 or r_nm <= 0.
- arc_turn_radius_nm(tas_kt, bank_deg) -> float: V**2 / (g * tan(bank))
  converted to nm. ValueError: bank outside (0, 90).
- arc_chord_nm(r_nm, delta_radial_deg) -> float:
  2 * r * sin(radians(delta)/2).
- radial_intercept_deg(current_radial_deg, target_radial_deg) -> float:
  the smaller signed angular difference in (-180, 180] from current to
  target.
- dme_arc_geometry(r_nm, radial_start_deg, radial_end_deg) -> dict
  {arc_length_nm, chord_nm, turn_angle_deg, start_point, end_point,
  midpoint_point}.
Identity to test: arc_length over 360 degrees equals the circumference
2*pi*r; chord over 180 degrees equals 2*r; arc_bank_angle and
arc_turn_radius are inverses (radius from bank equals the input radius).

## Worked example

Verified at prep: DME radius 12 nm, arc from radial 045 to radial 100
(55 degree turn):
- arc_length_nm = 11.519 nm.
- chord_nm = 11.082 nm.
- start point = (8.485, 8.485) nm; end point = (11.819, -2.084) nm
  (x = r sin radial, y = r cos radial).
- arc_bank_angle at 180 kt on a 12 nm radius = 2.25 deg (V 92.60 m/s,
  r 22224 m: atan(92.6^2/(9.80665*22224)) = atan(8572.8/217936) =
  atan(0.03934) = 2.25 deg).
  Anchor at 180 kt, 20 deg bank: radius 1.297 nm.
- radial_intercept from 045 to 100 = +55 deg; from 100 to 045 = -55 deg.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (plane trigonometry, independently checked
at prep).

## Validation list (contract test must include)

- arc_length(12, 55) within 0.01 nm of 11.519; arc_length(12, 360) equals
  75.398 nm (2*pi*r).
- point_on_arc at radial 090 gives (r, 0); at 000 gives (0, r).
- bank/radius inverse identity for two speed-radius pairs.
- chord(12, 180) equals 24; chord(12, 55) = 11.082 within 0.01.
- radial_intercept sign truth table (positive clockwise, negative
  counter-clockwise).
- ValueErrors for non-positive radius, speed, or out-of-range bank.
- Determinism; float outputs as documented.

## Corpus fragment (eval/hit1-wave38-dme-arc-leg.yaml)

Query 1 (copy verbatim):
  "compute the dme-arc-leg arc length and chord between radial 045 and radial 100 at a 12 nm dme radius"
  intent: "avionics; DME arc procedure geometry between radials"
  expected_skill: "avionics/flight-management/dme-arc-leg"
Query 2 (copy verbatim):
  "find the bank angle to hold a dme-arc-leg at 180 kt and the point on the arc at a given radial"
  intent: "avionics; DME arc holding bank angle and arc point"
  expected_skill: "avionics/flight-management/dme-arc-leg"
Task ids: w38-dme-arc-leg-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the geometry of a
constant-DME arc leg:" and include the outputs in the Claim. First tag:
dme-arc-leg. Additional tags ONLY: vor-dme-arc, arc-length-nm,
arc-bank-angle, radial-intercept, arc-chord, dme-radius. NEVER single
generic words (arc, DME, radial, leg, radius, turn). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): slant range, VOR bearing, localizer,
glideslope (radio-navigation-aids); great-circle track, cross-track error
(lateral-navigation); RF leg, turning center from tracks, RNP AR
(radius-to-fix-leg).
