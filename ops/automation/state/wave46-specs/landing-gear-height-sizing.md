# Wave-46 leaf spec: landing-gear-height-sizing (vehicle-design,
# sizing pack)

- Path: skills/vehicle-design/sizing/landing-gear-height-sizing/
- Pack: sizing (present siblings landing-gear-layout,
  landing-gear-sizing, landing-gear-retraction-sizing, tire-sizing,
  brake-energy-sizing, propeller-sizing, nacelle-sizing,
  fuselage-sizing; adjacent fences in vehicle-design/mass-properties
  (cg-envelope, the CG travel band input source) and in
  flight-test-operations/envelope (vmu-determination, the measured
  rotation-limit-speed tail strike check; flight test only, no
  geometry ownership)).
- Claim fences (quoted from the sibling frontmatter/body at spec time;
  none owns the vertical ground line geometry: every sibling consumes
  gear heights as GIVEN inputs and no leaf derives a height or a
  static ground line from a clearance requirement):
  - skills/vehicle-design/sizing/landing-gear-layout/SKILL.md lines
    30-37: "It pairs with vehicle-design/sizing/landing-gear-sizing,
    which sizes the strut loads and landing energy once the layout is
    fixed, and takes the CG travel limits as given inputs from
    vehicle-design/mass-properties/cg-envelope."
  - skills/vehicle-design/sizing/landing-gear-layout/SKILL.md
    workflow step 1 (lines 90-95): "Fix the arrangement geometry: the
    nose gear station x_ng, the main gear station x_mg, the tail cone
    lowest point station x_tail and contact height h_tail_contact, the
    CG height h_cg, the main gear wheel track, and the CG travel
    limits with the aft limit x_cg_aft forward of x_mg (otherwise the
    module raises ValueError)." The layout leaf takes the vertical
    geometry as given: the contact height h_tail_contact is an INPUT
    and no workflow step solves for it.
  - skills/vehicle-design/sizing/landing-gear-layout/SKILL.md lines
    57-63, the tail strike identity this leaf inverts: "Tail strike
    clearance: the tail cone lowest point at station x_tail and height
    h_tail_contact above the ground descends during the rotation as
    z(theta) = h_tail_contact * cos(theta) - a * sin(theta) with the
    horizontal arm a = x_tail - x_mg, which vanishes at
    tan(theta_ts) = h_tail_contact / a." The height that makes that
    contact height adequate at the required rotation attitude is never
    solved there.
  - skills/vehicle-design/sizing/landing-gear-sizing/SKILL.md lines
    24-26 (scope): "Use when the task is sizing the landing gear at
    the conceptual level: static loads over the struts, nose and main
    gear load share from the CG and wheelbase, shock absorber stroke,
    and the tire rating margin." Lines 39-40: "FAR-25.723 / CS-25.723
    shock absorption verification is a drop test; this module provides
    the sizing-level energy check only." No vertical geometry content.
  - skills/vehicle-design/sizing/landing-gear-retraction-sizing/
    SKILL.md "Related leaves" (lines 168-171):
    "vehicle-design/sizing/landing-gear-sizing: the static strut
    demand at touchdown, the nose and main gear CG split and the shock
    absorber stroke; it sizes the gear before the mechanism, this leaf
    sizes how the gear retracts." Mechanism territory only.
  - skills/vehicle-design/sizing/propeller-sizing/SKILL.md (pitfall,
    lines 134-137): "Sizing the diameter without the ground clearance:
    a large diameter that meets the blade-tip bound can still strike
    the ground in the takeoff attitude; run ground_clearance_check
    before fixing the diameter." That check evaluates the propeller
    installation clearance at a GIVEN hub height (its worked anchor:
    0.6 m of clearance at 1.6 m hub height), not the gear height
    derivation.
  - skills/vehicle-design/SKILL.md router row (line 95) for the
    layout sibling: "| vehicle-design/sizing/landing-gear-layout |
    Landing gear layout | tipback angle, tail strike clearance,
    lateral turnover angle, nose gear load fraction band, main gear
    position |" and routing guidance (lines 116-117): "Landing gear
    questions (strut loads, gear loads, shock absorber stroke) route
    to the sizing landing-gear-sizing sub-skill." No router row or
    guidance bullet names a height or a static ground line; the
    vehicle-design family has no vertical-geometry owner.
  - Zero-owner evidence re-verified at spec time at HEAD (real
    outputs): `grep -rilE "landing[- ]gear[- ]height|static[- ]
    ground[- ]line|main[- ]gear[- ]height|nose[- ]gear[- ]height|tail
    [- ]cone[- ]clearance" skills/ eval/ --include="*.md"
    --include="*.py"` returns no files (EXIT=1); the corpus token scan
    of eval/hit1-corpus.yaml for landing-gear-height,
    static-ground-line, tail-cone-clearance, main-gear-height,
    nose-gear-height and gear-height-selection returns count 0. The
    landing-gear-layout logic inventory is exactly five functions, all
    angle or load-fraction computations with heights as inputs:
    tipback_angle, tail_strike_clearance_angle,
    lateral_turnover_angle, lateral_turnover_tricycle_angle,
    nose_gear_static_load_fraction. No function anywhere derives a
    gear height or a static ground line from a clearance requirement.
    The aft-body upsweep angle seam is separately owned (fuselage-
    sizing carries the aft-body upsweep check and does not reach the
    gear height that sets the ground clearances).
  - Merge-time notes (probe receipt gate (f), carried into this
    contract): add a fence line to landing-gear-layout reading "gear
    height selection and the static ground line from clearance
    constraints belong to the height-sizing sibling", add a router
    row in skills/vehicle-design/SKILL.md beside the landing-gear
    rows, and add 2 corpus tasks at merge with the hyphenated tokens
    below. Family spread: vehicle-design 55 to 56 after landing.
- Standards id: far-25 (14 CFR Part 25, reference-only, family
  convention) and cs-25 (CS-25, reference-only), both verified present
  in standards-map.yaml at spec time (grep line 16 for far-25, line 27
  for cs-25). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Select the vertical landing gear geometry of a tricycle-gear aircraft
at the conceptual level: from the ground clearance constraints, solve
the static ground line and the corresponding main gear height, set the
nose gear height so the cabin waterline is level over the wheelbase,
and report the clearance margins and the height verdict. The airframe
is rigid at the level attitude on the ground with all three tire
contacts on the ground plane, and the design rotation is nose-up about
the main gear contact. The governing constraints are the tail cone
lowest point keeping its required ground clearance at the design
rotation attitude, and the nacelle and propeller lowest points keeping
their required clearances at the level and rotated attitudes; every
aft hard point drops during rotation while every point forward of the
main gear contact rises, so the rotation case binds aft structure and
the level case binds the forward nacelle and propeller installation.
The module solves the static ground line H_gl as the maximum over all
required ground lines (one closed-form expression per point and
attitude, trigonometric, stdlib math only), reports the achieved
clearance and margin of every hard point at both attitudes, evaluates
the tail strike margin of the solved geometry through the layout
sibling relation tan(theta_ts) = h_tail_contact / a, checks the nose
gear static load share at the design CG from the wheelbase moment
balance, and issues the height verdict: every margin non-negative and
both gear heights positive. The solved tail cone contact height
h_tail_contact = H_gl + z_tail is exactly the input the layout
sibling's tail strike identity consumes: this leaf is the inverse of
that check. Does NOT do: the tipback angle, the lateral turnover
angles, the tail strike clearance ANGLE as a primary computation, the
nose gear load fraction band across the CG travel limits, or the main
gear position check (landing-gear-layout, which takes every height as
a given input); the static strut loads, the nose and main gear CG load
split beyond the single design-CG feasibility check, the shock
absorber stroke v^2 / (2 n g) or the FAR-25.723 drop test energy
check (landing-gear-sizing); the retraction moment, actuator force and
stroke, the locks or the gear bay stowage fit
(landing-gear-retraction-sizing); propeller diameter and blade count
selection or the propeller ground_clearance_check of a given
installation (propeller-sizing); the aft-body upsweep angle check
(fuselage-sizing); tire dimensions, pressure or footprint
(tire-sizing); the CG travel band itself (cg-envelope); any lateral or
longitudinal gear POSITION sizing, track, rake, strut internals or
vendor data. The static load share check is feasibility-only: it
verifies the design CG sits strictly between the contacts so both
gears carry positive load, and never produces the layout band
verdicts.

## Model (implement exactly)

Pure stdlib, math only, closed form, deterministic, no empirical
tables, no numeric integration, no vendor data. Body frame at the
level attitude: stations x in metres aft of the fuselage datum; z in
metres positive UP from the main gear attach plane, the horizontal
plane through the main gear attach point, parallel to the cabin
waterline. The static ground line H_gl is the height of that attach
plane above the ground at the level attitude. The main gear is
vertical, its contact at station x_mg directly below the attach point,
so the main gear height equals H_gl. The nose gear attach point sits
at body height z_na (negative when below the main gear attach plane);
a vertical nose strut of length H_gl + z_na reaches the ground with
the cabin waterline level over the wheelbase.

Module constants: DEG2RAD = math.pi / 180.0; MAX_ROTATION_DEG = 25.0
(the upper end of the physical band of design rotation attitudes;
typical conceptual values sit between 8 and 15 deg, and anything
outside the band (0, 25] deg raises).

Defining relations (pin these exactly; every function below derives
from them):
- Clearance of a hard point at body height z_body and station x_point
  during a nose-up rotation theta about the main gear contact:
  c(theta) = (H_gl + z_body) * cos(theta) - (x_point - x_mg) *
  sin(theta). At the level attitude (theta = 0) the clearance is
  H_gl + z_body. This is the layout sibling identity z(theta) =
  h_tail_contact * cos(theta) - a * sin(theta) evaluated with
  h_tail_contact = H_gl + z_body and a = x_point - x_mg.
- Required ground line from one point at one attitude: the point keeps
  clearance clearance_req when (H_gl + z_body) * cos(theta) -
  (x_point - x_mg) * sin(theta) >= clearance_req, so H_gl >=
  clearance_req / cos(theta) + (x_point - x_mg) * tan(theta) -
  z_body. The single closed form is valid at theta = 0 (cos 1,
  tan 0) and at any rotation angle in the band.
- Static ground line: H_gl = max over all hard points and all required
  attitudes of the required ground line. The tail cone lowest point
  with a rotation clearance is the aft binding case; a nacelle or
  propeller point forward of the main gear contact binds at the level
  attitude (its rotation requirement, when present, is weaker because
  the point rises).
- Tail contact height of the solved geometry: h_tail_contact = H_gl +
  z_tail. The layout sibling relation tan(theta_ts) = h_tail_contact /
  (x_tail - x_mg) then gives the tail strike angle of the solved
  geometry and the rotation margin theta_ts - theta_rot.
- Gear heights: main gear height = H_gl; nose gear height = H_gl +
  z_na. Leveling identity: the attach heights above the ground differ
  by exactly z_na and the gear lengths compensate, so the waterline is
  level over the wheelbase (h_mg = h_ng - z_na exactly).
- Propeller disc lowest point body height = z_hub - radius from the
  hub center body height and the disc radius.
- Nose gear static load share at the design CG from the wheelbase
  moment balance: P_n / W = (x_mg - x_cg) / (x_mg - x_ng); the main
  gear share complements it to 1. Feasibility only: the design CG must
  sit strictly between the contacts.
- Units are SI: m, deg, dimensionless fractions. All angles enter
  through math.radians via DEG2RAD.
- FAR-25 and CS-25 frame the transport landing gear context; the
  relations above are standard conceptual design methodology
  (Raymer, Aircraft Design: A Conceptual Approach, landing gear
  chapter; Gudmundsson, General Aviation Aircraft Design, landing gear
  design chapter; Sadraey, Aircraft Design: A Systems Engineering
  Approach, landing gear chapter; Torenbeek, Synthesis of Subsonic
  Airplane Design, the same book family the layout sibling
  paraphrases), summary-only, never reproduced.

Functions (signatures, returns, ValueError rejections; no imports
beyond math):
- clearance_at_attitude(z_body, x_point, x_mg, h_ground_line,
  theta_deg) -> float
  the clearance c(theta) of the point, m, at attitude theta_deg (0 =
  level attitude). ValueError if h_ground_line <= 0 or theta_deg
  outside [0, MAX_ROTATION_DEG].
- required_ground_line(z_body, x_point, x_mg, theta_deg,
  clearance_req) -> float
  the static ground line needed so the point keeps clearance_req at
  attitude theta_deg, m, from the closed form above. ValueError if
  clearance_req < 0 or theta_deg outside [0, MAX_ROTATION_DEG].
- static_ground_line(points, theta_rot_deg, x_mg, x_ng) -> (float,
  str)
  solves H_gl as the maximum required ground line over the points and
  returns it with the binding point name. Each point dict:
  {"station", "z_body", "clearance_level" (default 0.0),
  "clearance_rotation" (default None = no rotation-attitude
  requirement), "name" (label for reports)}. Every point keeps its
  level-attitude clearance; a point with a clearance_rotation set
  also keeps that clearance at the design rotation attitude (the tail
  cone case). ValueError if x_mg <= x_ng (wheelbase not positive), if
  theta_rot_deg outside (0, MAX_ROTATION_DEG], if points is empty, or
  if any required clearance is negative.
- gear_heights(h_ground_line, nose_attach_z_body) -> dict
  {"main_gear_height", "nose_gear_height", "height_difference"} in m.
  ValueError if h_ground_line <= 0 or the nose gear height (H_gl +
  nose_attach_z_body) is not positive.
- propeller_low_point(z_hub_body, radius) -> float
  the propeller disc lowest point body height z_hub - radius, m.
  ValueError if radius <= 0.
- static_load_share(x_cg, x_mg, x_ng) -> float
  the nose gear static load share (x_mg - x_cg) / (x_mg - x_ng) at
  the design CG, dimensionless. ValueError if x_mg <= x_ng or the
  design CG is not strictly inside the wheelbase (x_ng < x_cg < x_mg).
- clearance_margin(z_body, x_point, x_mg, h_ground_line, theta_deg,
  clearance_req) -> float
  achieved clearance minus the required clearance at one attitude, m.
  ValueError if clearance_req < 0 (all other arguments validated by
  clearance_at_attitude).
- tail_strike_angle_deg(h_tail_contact, tail_arm) -> float
  the tail strike angle of the SOLVED geometry, deg, from the layout
  sibling relation theta_ts = atan(h_tail_contact / tail_arm), used
  only to report the rotation margin of the solved heights. This is
  not the layout leaf's primary angle computation (which takes the
  contact height as a given input); here the contact height is the
  output of this module. ValueError if h_tail_contact <= 0 or
  tail_arm <= 0.

Identities to test (closed form, exact):
- I1 Binding rotation round trip: with the solved H_gl,
  (H_gl + z_tail) * cos(theta_rot) - (x_tail - x_mg) *
  sin(theta_rot) equals the required tail rotation clearance exactly
  (real anchor 0.250000000000, residual 1.11e-16).
- I2 Exact tangent algebra: h_tail_contact - c_tail /
  cos(theta_rot) equals (x_tail - x_mg) * tan(theta_rot) exactly
  (real anchor 0.881634903542 on both sides, residual 1.11e-16).
- I3 Small-angle consistency: the difference between the exact rise
  (h_tail_contact - c_tail) and the tangent rise a * tan(theta_rot)
  equals c_tail * (1 / cos(theta_rot) - 1) exactly (real anchor
  0.003856652971 on both sides, residual 5.55e-17); the tangent rise
  picture is within 1% of the exact rise at 10 deg rotation.
- I4 Sibling contact identity: at theta_ts = atan(h_tail_contact /
  a), the rotation clearance of the tail point is zero to machine
  precision, and theta_ts exceeds theta_rot.
- I5 Leveling identity: h_mg equals h_ng - z_na exactly (both equal
  the solved H_gl), so the waterline is level over the wheelbase.
- I6 Forward-point rise: a hard point forward of the main gear
  contact has a larger clearance at the rotation attitude than at the
  level attitude.
- Load share complement: the nose share and the main share sum to 1.
- Level-attitude round trip: the achieved level clearance of every
  point computed from the solved H_gl equals H_gl + z_body and meets
  its required level clearance; margins at every required attitude
  are non-negative, the governing constraint margin is zero, and all
  others are strictly positive.

## Worked example

Reference aircraft: twin-turboprop utility transport (King Air 350
class scale, representative conceptual geometry). Nose gear contact at
x_ng = 1.40 m, main gear contact at x_mg = 7.40 m (wheelbase 6.00 m),
design CG at x_cg = 6.80 m. Design rotation attitude 10.0 deg about
the main gear contact. Nose gear attach point 1.00 m below the main
gear attach plane (z_na = -1.00 m). Tail cone lowest point at
x_tail = 12.40 m (5.00 m aft of the main gear contact) with body
height z_tail = -0.45 m and a required rotation clearance of 0.25 m.
Propeller disc lowest point derived from a hub center body height of
0.10 m and a disc radius of 1.15 m (propeller_low_point gives
z = -1.05 m) at station 4.90 m, with a required level clearance of
0.20 m. Nacelle lowest point at z = -0.60 m, station 5.30 m, with a
required level clearance of 0.15 m and a required rotation clearance
of 0.15 m. All values below are REAL outputs of the spec anchor
anchor_landing_gear_height.py (stdlib math, closed form, exit 0,
deterministic).

- Required ground lines per constraint (H_gl must reach each): tail
  cone at the level attitude 0.450000000000 m and at the rotation
  attitude 1.585491556514 m; propeller at the level attitude
  1.250000000000 m; nacelle at the level attitude 0.750000000000 m
  and at the rotation attitude 0.382027332295 m. The tail cone
  rotation constraint governs: the static ground line H_gl =
  1.585491556514 m (binding point: tail cone lowest point). The
  propeller level requirement is close behind at 1.250000000000 m
  and the nacelle constraints sit well below, as expected for the
  forward installation on a low-wing twin.
- Main gear height: h_mg = H_gl = 1.585491556514 m (vertical main
  gear, attach point to ground). Nose gear height: h_ng = H_gl +
  z_na = 0.585491556514 m. Height difference h_mg - h_ng =
  1.000000000000 m, exactly -z_na: the nose strut is the shorter gear
  and the cabin waterline is level over the wheelbase (identity I5).
- Tail geometry of the solved ground line: tail cone contact height
  h_tail_contact = H_gl + z_tail = 1.135491556514 m at the arm a_t =
  5.00 m. Tail strike angle theta_ts = atan(1.135491556514 / 5.00) =
  12.794763238232 deg, giving a rotation margin of 2.794763238232 deg
  over the 10.0 deg design rotation attitude.
- Achieved clearances and margins (margin = achieved minus required):
  tail cone at rotation 0.250000000000 m with margin 0.000000000000
  (the governing constraint binds exactly); tail cone at the level
  attitude 1.135491556514 m (no level requirement); propeller disc
  lowest point at the level attitude 0.535491556514 m with margin
  0.335491556514 m and at the rotation attitude 0.961476680695 m
  (reported only: the forward point rises during rotation); nacelle
  at the level attitude 0.985491556514 m with margin 0.835491556514 m
  and at the rotation attitude 1.335180898483 m with margin
  1.185180898483 m.
- Static load share at the design CG: nose share (7.40 - 6.80) /
  6.00 = 0.100000000000 (10% of the weight on the nose gear), main
  share 0.900000000000, sum 1.000000000000. Both gears carry positive
  load, so the tricycle arrangement is feasible at the design CG.
- Height verdict: every required margin is non-negative and both gear
  heights are positive, so the height verdict is clearance-ok: a
  1.585491556514 m static ground line (main gear height) with the
  0.585491556514 m nose gear satisfies the 0.25 m tail cone rotation
  clearance at 10 deg, the 0.20 m propeller level clearance and the
  0.15 m nacelle clearances with margins of 0.000000000000,
  0.335491556514, 0.835491556514 and 1.185180898483 m respectively.
- Read-off: the tail cone rotation case sets this installation; the
  propeller and nacelle constraints of the forward engine installation
  are met with comfortable margins, and the solved contact height
  1.135491556514 m is the value the layout sibling takes as its given
  h_tail_contact input to confirm the 12.7948 deg tail strike angle
  against the tipback arrangement.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of the spec anchor
anchor_landing_gear_height.py (stdlib math, closed form, exit 0).

## Validation list (contract test must include)

1. static_ground_line on the worked points at theta_rot 10.0, x_mg
   7.40, x_ng 1.40 returns H_gl = 1.585491556514 within 1e-9 with the
   binding name "tail cone lowest point"; the per-constraint required
   ground lines equal 0.450000000000 (tail level), 1.585491556514
   (tail rotation), 1.250000000000 (propeller level),
   0.750000000000 (nacelle level) and 0.382027332295 (nacelle
   rotation) within 1e-9 each.
2. gear_heights(1.585491556514, -1.00) returns main_gear_height
   1.585491556514, nose_gear_height 0.585491556514 and
   height_difference 1.000000000000 within 1e-9.
3. Achieved clearances of the worked geometry: tail at rotation
   0.250000000000 within 1e-9, tail at level 1.135491556514 within
   1e-9, propeller at level 0.535491556514 within 1e-9, propeller at
   rotation 0.961476680695 within 1e-9, nacelle at level
   0.985491556514 within 1e-9, nacelle at rotation 1.335180898483
   within 1e-9.
4. Margins: tail rotation margin 0.000000000000 within 1e-12 (the
   governing constraint binds), propeller level margin 0.335491556514
   within 1e-9, nacelle level margin 0.835491556514 within 1e-9,
   nacelle rotation margin 1.185180898483 within 1e-9; every margin
   at every required attitude is non-negative.
5. tail_strike_angle_deg(1.135491556514, 5.00) = 12.794763238232 deg
   within 1e-6 deg; the rotation margin theta_ts - theta_rot =
   2.794763238232 deg within 1e-6 deg and is positive.
6. Identity I1: recompute (H_gl + z_tail) * cos(10 deg) - (x_tail -
   x_mg) * sin(10 deg) from the outputs and assert it equals 0.25
   within 1e-9 (round trip of the binding constraint).
7. Identity I2: h_tail_contact - 0.25 / cos(10 deg) equals (x_tail -
   x_mg) * tan(10 deg) within 1e-9 (real anchor 0.881634903542 both
   sides).
8. Identity I3: (h_tail_contact - 0.25) - (x_tail - x_mg) *
   tan(10 deg) equals 0.25 * (1 / cos(10 deg) - 1) within 1e-12
   (real anchor 0.003856652971 both sides); the small-angle rise
   a * tan(theta_rot) sits within 1% of the exact rise h_tail_contact
   - c_tail.
9. Identity I4: the rotation clearance of the tail point evaluated at
   the tail strike angle is zero within 1e-9, and theta_ts exceeds
   theta_rot. Identity I5: h_mg equals h_ng - nose_attach_z_body
   within 1e-9. Identity I6: the propeller clearance at the rotation
   attitude exceeds its level-attitude clearance.
10. static_load_share(6.80, 7.40, 1.40) = 0.100000000000 within
    1e-12; the main share 0.900000000000 complements it to
    1.000000000000 within 1e-12; propeller_low_point(0.10, 1.15) =
    -1.050000000000 within 1e-12.
11. Level-attitude round trip: for every worked point the achieved
    level clearance computed by clearance_at_attitude at theta 0
    equals H_gl + z_body within 1e-9 and meets the required level
    clearance.
12. ValueErrors: required_ground_line at clearance_req -0.1;
    static_ground_line at theta_rot 0.0 and 25.5 (band edges
    excluded), at x_mg == x_ng (wheelbase not positive), on an empty
    point list, and on a point dict with a negative clearance_level
    or a negative clearance_rotation; static_load_share at x_cg ==
    x_mg, x_cg == x_ng and x_cg forward of the nose gear;
    gear_heights at a nose attach offset at or below -H_gl (nose gear
    height not positive) and at a non-positive ground line;
    clearance_at_attitude at h_ground_line 0; propeller_low_point at
    radius -1.0; clearance_margin at clearance_req -0.1.
13. Determinism: two full solves of the worked scenario produce
    identical (H_gl, binding) tuples and identical clearance values;
    the module imports math only; module constants are fixed
    (DEG2RAD = math.pi / 180.0, MAX_ROTATION_DEG = 25.0).
14. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality
    on computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (eval/hit1-wave46-landing-gear-height-sizing.yaml)

Query 1 (copy verbatim):
  "check the landing-gear-height of the tricycle transport at the
  conceptual level: solve the static-ground-line from the tail-cone
  clearance at the design rotation attitude and compute the
  main-gear-height and the nose-gear-height that level the cabin
  waterline over the wheelbase"
  intent: "vehicle-design; solve the static-ground-line of the
  tricycle transport from the tail-cone-clearance at the design
  rotation attitude about the main gear contact, compute the
  main-gear-height and the nose-gear-height that level the cabin
  waterline over the wheelbase, and report the clearance margins and
  the height verdict"
  expected_skill: "vehicle-design/sizing/landing-gear-height-sizing"
Query 2 (copy verbatim):
  "select the landing-gear-height-sizing for the nosewheel aircraft:
  derive the required static-ground-line from the tail-cone-clearance
  margin at the rotation reference, then verify the nacelle ground
  clearance at the level and rotated attitudes and report the height
  verdict"
  intent: "vehicle-design; select the landing-gear-height-sizing for
  the nosewheel aircraft: derive the required static-ground-line from
  the tail-cone-clearance margin at the rotation reference, verify
  the nacelle and propeller clearances at the level and rotated
  attitudes, check the nose gear static load share at the design CG,
  and report the height verdict"
  expected_skill: "vehicle-design/sizing/landing-gear-height-sizing"
Task ids: w46-landing-gear-height-sizing-1 and -2. Prep grep (run at
spec time, real outputs): the tokens landing-gear-height,
static-ground-line, tail-cone-clearance, main-gear-height,
nose-gear-height and gear-height-selection return count 0 in
eval/hit1-corpus.yaml and no matching files across eval/*.yaml, and
the whole-tree zero-owner grep over skills/ and eval/ returns no
files (EXIT=1), so the queries above are collision-free. The sibling
vehicle-design tasks route on the tipback-angle, lateral-turnover and
tail-strike-clearance-angle tokens (landing-gear-layout), the
strut-load, shock-absorber-stroke and sink-speed tokens
(landing-gear-sizing), the retraction-actuator-force and
linkage-geometry tokens (landing-gear-retraction-sizing), the
propeller-diameter, blade-tip and ground-clearance tokens
(propeller-sizing) and the aft-body upsweep tokens (fuselage-sizing),
none of which carry the height-selection tokens, so no existing task
is stolen. The queries deliberately carry only the hyphenated tokens
above; a bare landing-gear, nose-gear, main-gear, wheelbase or
ground-clearance query routes to the siblings and must never be used
here.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must select the vertical landing
gear geometry of a tricycle-gear aircraft at the conceptual level:"
and include the outputs in the Claim. First tag:
landing-gear-height-sizing. Additional tags ONLY:
static-ground-line, main-gear-height-selection,
nose-gear-height-selection, tail-cone-clearance,
rotation-clearance-margin, waterline-leveling. NEVER single generic
words (gear, height, landing, clearance, nacelle, propeller,
wheelbase, nose, main, tail, rotation, strut, tire, retraction) and
NEVER ground-clearance, the live tag of the propeller-sizing sibling
(its ground_clearance_check content), nor any sibling token below.
50-150 words, <=1000 chars, no em dash, no content-policy sweep term
(the banned word from the builder kit), action verb present.
Recommended wording (outputs and verdict in Claim order, 117 words,
857 chars, verified at spec time):
"Use when you must select the vertical landing gear geometry of a
tricycle-gear aircraft at the conceptual level: solve the
static-ground-line from the tail-cone-clearance margin at the design
rotation attitude about the main gear contact, compute the
main-gear-height and the nose-gear-height that level the cabin
waterline over the wheelbase, verify the nacelle and propeller
clearances at the level and rotated attitudes, and check the nose
gear static load share at the design CG. Produces the
static-ground-line, the main and nose gear heights, the achieved
tail cone, nacelle and propeller clearance margins at both attitudes,
the tail strike margin of the solved geometry, and the height verdict
that gates the gear configuration. Trigger: landing-gear-height,
static-ground-line, gear-height-selection, tail-cone-clearance,
rotation-clearance-margin."

FORBIDDEN TOKENS (belong to siblings): tipback-angle,
lateral-turnover-angle, tail-strike-clearance-angle,
nose-gear-load-fraction, main-gear-positioning, landing-gear-layout,
wheel-track, tipback arrangement, CG travel limits as a band verdict
(landing-gear-layout); strut-load, shock-absorber-stroke,
sink-speed, tire-rating-margin, landing-load-factor,
landing-gear-sizing (landing-gear-sizing); retraction-actuator-
sizing, retraction-moment, actuator-force-and-stroke,
up-lock-down-lock, gear-stowage-check, linkage-geometry
(landing-gear-retraction-sizing); propeller-diameter, blade-count,
blade-tip, activity-factor, disk-loading, ground-clearance,
ground_clearance_check (propeller-sizing); aft-body-upsweep,
cargo-door upsweep check (fuselage-sizing); tire-diameter,
tire-pressure, footprint (tire-sizing); rejected-takeoff-energy,
brake-temperature-rise (brake-energy-sizing). The layout sibling
takes every height as a given input and computes angles; this leaf
computes the heights from the required clearances and never claims
the layout tokens above.
