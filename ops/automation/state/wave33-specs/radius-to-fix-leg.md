# Wave-33 leaf spec: radius-to-fix-leg (avionics, flight-management pack)

- Path: skills/avionics/flight-management/radius-to-fix-leg/
- Pack: flight-management. Sibling scope check: lateral-navigation owns
  point-to-point great-circle guidance + fly-by turn ANTICIPATION (when
  to START a transition turn: d_ant before the waypoint, R_turn =
  v^2/(g tan(bank))) - no arc-center/arc-length construction;
  flight-planning = great-circle leg distances; rnp-anp-containment =
  ANP sigma -> 95% bound + margin verdict; vertical-navigation = VNAV
  path (TOD/FPA); rta-time-control = time control. Family-wide grep for
  radius.to.fix|RF leg|path.terminator|arc center|constant.radius|DME
  arc = zero hits. This leaf owns the RF-leg lateral path construction.
- Standards id: do-178c (reference-only; mirrors all four FM siblings;
  RF-leg geometry is public PBN/ARINC-424 material, FAA AC 90-105
  public - name + paraphrase only, no proprietary tables).
  Ledger Standard: do-178c.
- Family: avionics

## Claim

Construct the lateral path of a published radius-to-fix (RF) leg for
RNP AR procedures: given the entry fix, the inbound track, the published
radius and the turn direction, compute the turning center, validate that
the exit fix lies on the radius circle, and derive the swept central
angle, the along-arc length, the exit track and the chord. Produces the
RF-leg geometry dict that gates a flyable-arc check for procedure
design.

Does NOT do: fly-by waypoint turn anticipation / great-circle guidance
(lateral-navigation); ANP containment margins (rnp-anp-containment);
VNAV vertical path (vertical-navigation); holding-pattern entry
sectors (declined wave-32: no convention ambiguity here - EF tangent +
direction fix the center side, exit-on-circle + sweep direction pick
the arc).

## Model (implement exactly)

Conventions: local tangent-plane frame, x = east (NM), y = north (NM).
Entry fix EF = (x_ef, y_ef), exit fix XF = (x_xf, y_xf). Inbound track
track_deg is the true course INTO the RF leg at EF, degrees clockwise
from north. Radius R (NM). Turn direction "RIGHT" or "LEFT" (as
published). Geometry: the center C lies at distance R from EF on the
side perpendicular to the inbound track given by the turn direction;
for a RIGHT turn off inbound track t, the center is to the right of the
track direction: C = EF + R * n_right where n_right is the unit vector
90 deg clockwise from the inbound direction; for LEFT, 90 deg
counter-clockwise. Inbound direction unit vector d = (sin t, cos t)
(east, north components). Right normal n_right = (cos t, -sin t); left
normal n_left = (-cos t, sin t). Verify with the worked case: EF =
(0,0), inbound 090 (east), RIGHT, R = 15 -> center (0, -15) (south, to
the right of eastbound travel). Exit validation: |XF - C| == R within
tol. Swept central angle: the angle from the EF radius to the XF radius
along the turn direction (clockwise-positive compass convention,
0..360); arc length s = R * Delta_psi (rad); exit track = the tangent
at XF along the turn; chord = |XF - EF|.

Functions (pure stdlib):

- rf_turn_center(ef, inbound_track_deg, radius_nm, turn) -> (cx, cy)
  as above. ValueError on radius <= 0, invalid turn, EF non-finite.
- rf_exit_on_arc(center, xf, radius_nm, tol_nm=1e-6) -> bool
  (abs(|XF - C| - R) <= tol).
- rf_arc_angle_deg(center, ef, xf, turn) -> central angle swept from EF
  to XF along the turn direction, in degrees 0..360. Use the two-arg
  atan2 of the EF and XF radius vectors from the center; compute the
  CCW angle from the EF vector to the XF vector; if the turn is RIGHT
  (clockwise), the swept angle is 360 - CCW_angle. Validate against the
  worked case: EF at bearing 180 (south of center (0,-15)? EF (0,0) -
  center (0,-15) -> EF radius vector points north = bearing 000);
  XF (15,-15) - center (0,-15) -> XF radius vector points east =
  bearing 090. RIGHT turn from EF to XF sweeps 90 deg clockwise.
  Return the swept angle in degrees (0..360) and handle the 
  EF == XF (0 deg) and full-circle cases explicitly.
- rf_arc_length_nm(radius_nm, arc_angle_deg) -> R * radians(angle).
- rf_exit_track_deg(center, xf, turn) -> the tangent direction at XF
  continuing the turn (degrees true). Derive: the radial direction from
  center to XF, bearing_radial = atan2(x_xf - cx, y_xf - cy) in the
  compass convention used; the flight direction at XF is perpendicular
  to the radius, on the turn side: RIGHT => direction = radial bearing
  + 90 deg; LEFT => radial bearing - 90 deg. Verify: worked case XF
  (15,-15), center (0,-15): radial bearing 090 (east), RIGHT => exit
  track 180 (south) - matches the hand check. Normalize to 0..360.
- rf_chord_nm(ef, xf) -> |XF - EF|.
- rf_leg_construct(ef, xf, inbound_track_deg, radius_nm, turn,
  tol_nm=1e-6) -> dict {center_nm, exit_on_arc: bool, sweep_deg,
  arc_length_nm, exit_track_deg, chord_nm, valid}. valid = exit_on_arc
  and sweep_deg > 0.

## Worked example

Case 1: EF = (0,0), XF = (15,-15), inbound track 090, RIGHT, R = 15 NM.
- rf_turn_center -> (0,-15).
- rf_exit_on_arc -> True (|XF - C| = 15.000).
- rf_arc_angle_deg -> 90.000 deg.
- rf_arc_length_nm -> 15 * pi/2 about 23.562 NM.
- rf_exit_track_deg -> 180.0 deg.
- rf_chord_nm -> |(15,-15)| = 21.213 NM.

Case 2: R = 8 NM, 60 deg arc -> arc length about 8.3776 NM.
Case 3: XF = (15,15) with center (0,-15): dist about 33.54 != 15 ->
rejected (exit_on_arc False, valid False).
Case 4: LEFT turn -> center (0, +15).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: radius <= 0; invalid turn direction; non-finite EF/XF.
- Case-1 anchors: center (0,-15); exit True; sweep 90.000 deg; arc
  length 23.562; exit track 180.0; chord 21.213.
- Case-2 anchor: 8 NM, 60 deg -> 8.3776 NM.
- Case-3 rejection: exit_on_arc False and valid False.
- Case-4: LEFT gives center (0, +15) with the same EF/track.
- Direction consistency: RIGHT vs LEFT with the same EF/XF/radius give
  complementary sweeps that sum to the full turn geometry; a 180-deg
  RIGHT arc exit track is inbound + 180.
- Determinism: identical outputs run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-radius-to-fix-leg.yaml)

Query 1 (copy verbatim):
  "radius to fix leg turning center arc length construction for an rnp ar procedure flyable arc check"
  intent: "avionics; radius-to-fix RF leg turn center and arc-length construction"
  expected_skill: "avionics/flight-management/radius-to-fix-leg"
Query 2 (copy verbatim):
  "constant radius path terminator rf leg exit fix validation and exit track derivation from the turn direction geometry"
  intent: "avionics; RF-leg exit-fix validation and exit track geometry"
  expected_skill: "avionics/flight-management/radius-to-fix-leg"
Task ids: w33-radius-to-fix-leg-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must construct the lateral path of a
radius-to-fix leg:" and include the outputs in the Claim. First tag:
radius-to-fix-leg. Additional tags ONLY: rnp-ar-procedure,
rf-leg-geometry, turn-center, arc-length, path-terminator,
flyable-arc-check. NEVER single generic words (radius, fix, leg, arc,
turn, track, path, navigation). 50-150 words, <=1000 chars, no em dash,
no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): fly-by, turn anticipation,
great circle, intercept heading (lateral-navigation); containment,
ANP, sigma, 95 percent (rnp-anp-containment); vertical, TOD, flight
path angle (vertical-navigation); holding pattern, teardrop, parallel
entry (declined topic; do not claim); cost index, ECON
(performance-computation). The tokens "radius to fix", "RF leg", "turn
center", "arc length", "path terminator" are this leaf's own.

Tags: [radius-to-fix-leg, rnp-ar-procedure, rf-leg-geometry,
turn-center, arc-length, path-terminator, flyable-arc-check]

Sibling-citation lines for Related leaves:
avionics/flight-management/lateral-navigation (fly-by anticipation
sibling; this leaf owns the constant-radius arc itself),
avionics/flight-management/rnp-anp-containment,
avionics/flight-management/vertical-navigation.

Ledger Standard: do-178c.
