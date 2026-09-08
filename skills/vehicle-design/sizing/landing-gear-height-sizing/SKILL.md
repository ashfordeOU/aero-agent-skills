---
name: landing-gear-height-sizing
description: "Use when you must select the vertical landing gear geometry of a tricycle-gear aircraft at the conceptual level: solve the static-ground-line from the tail-cone-clearance margin at the design rotation attitude about the main gear contact, compute the main-gear-height and the nose-gear-height that level the cabin waterline over the wheelbase, verify the nacelle and propeller clearances at the level and rotated attitudes, and check the nose gear static load share at the design CG. Produces the static-ground-line, the main and nose gear heights, the achieved tail cone, nacelle and propeller clearance margins at both attitudes, the tail strike margin of the solved geometry, and the height verdict that gates the gear configuration. Trigger: landing-gear-height, static-ground-line, gear-height-selection, tail-cone-clearance, rotation-clearance-margin."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [landing-gear-height-sizing, static-ground-line, main-gear-height-selection, nose-gear-height-selection, tail-cone-clearance, rotation-clearance-margin, waterline-leveling]
  version: 0.1.0
  author: AeroSkills
---

# Landing Gear Height Sizing (vehicle-design/sizing/landing-gear-height-sizing)

Use when the task is selecting the vertical landing gear geometry of a
tricycle-gear aircraft at the conceptual level: solving the static ground
line from the ground clearance constraints, setting the main and nose gear
heights that level the cabin waterline over the wheelbase, and reporting the
clearance margins and the height verdict. This leaf implements a closed-form
trigonometric model in pure Python, stdlib only. It pairs with
vehicle-design/sizing/landing-gear-layout, which takes the solved gear
heights as given inputs to its tipback, tail strike clearance angle and
lateral turnover angle checks, and with vehicle-design/mass-properties/
cg-envelope, the source of the CG travel band that fixes the design CG used
in the static load share check.

## Domain quick reference

- Body frame at the level attitude: stations x in metres aft of the fuselage
  datum, z in metres positive up from the main gear attach plane, the
  horizontal plane through the main gear attach point.
- Clearance of a hard point during a nose-up rotation theta about the main
  gear contact: c(theta) = (H_gl + z_body) * cos(theta) - (x_point - x_mg) *
  sin(theta). At the level attitude (theta = 0) the clearance is H_gl +
  z_body.
- Required ground line from one point at one attitude: H_gl >=
  clearance_req / cos(theta) + (x_point - x_mg) * tan(theta) - z_body. The
  single closed form holds at theta = 0 and at any rotation angle in the
  design band.
- Static ground line: H_gl = max over all hard points and all required
  attitudes of the required ground line. The tail cone lowest point with a
  rotation clearance is typically the aft binding case; a nacelle or
  propeller point forward of the main gear contact binds at the level
  attitude.
- Gear heights: main gear height = H_gl (the main gear is vertical, contact
  directly below the attach point); nose gear height = H_gl + z_na. The
  attach heights differ by exactly z_na, so the cabin waterline is level
  over the wheelbase.
- Tail contact height of the solved geometry: h_tail_contact = H_gl +
  z_tail. The layout sibling relation tan(theta_ts) = h_tail_contact /
  (x_tail - x_mg) gives the tail strike angle of the solved geometry and the
  rotation margin theta_ts - theta_rot.
- Propeller disc lowest point body height: z_hub - radius.
- Nose gear static load share at the design CG from the wheelbase moment
  balance: P_n / W = (x_mg - x_cg) / (x_mg - x_ng); the main gear share
  complements it to 1. Feasibility only: the design CG must sit strictly
  between the contacts.
- Units are SI: m, deg, dimensionless fractions. All angles enter through
  math.radians via the module constant DEG2RAD.
- FAR-25 and CS-25 frame the transport landing gear context; the relations
  above are standard conceptual design methodology (Raymer, Gudmundsson,
  Sadraey, Torenbeek, landing gear chapters), summary-only, never
  reproduced.

## Workflow

1. Fix the wheelbase and hard point geometry: nose gear station x_ng, main
   gear station x_mg, and the body height z_body, station and required
   clearances of every hard point (tail cone, nacelle, propeller) that
   constrains the ground line.
2. Solve the static-ground-line with static_ground_line over the hard
   points and the design rotation attitude, which returns H_gl and the
   binding point name.
3. Derive the main and nose gear heights with gear_heights from H_gl and
   the nose gear attach offset z_na.
4. Report the achieved clearance and margin of every hard point at both
   attitudes with clearance_at_attitude and clearance_margin.
5. Evaluate the tail strike margin of the solved geometry with
   tail_strike_angle_deg on the solved tail contact height h_tail_contact =
   H_gl + z_tail, and compare it against the design rotation attitude.
6. Check the nose gear static load share at the design CG with
   static_load_share, confirming the CG sits strictly inside the wheelbase.
7. Issue the height verdict: every required margin is non-negative and both
   gear heights are positive, confirmed by the contract test
   scripts/test_landing_gear_height_sizing.py.

## Worked example

Reference aircraft: twin-turboprop utility transport (King Air 350 class
scale, representative conceptual geometry). Nose gear contact at x_ng =
1.40 m, main gear contact at x_mg = 7.40 m (wheelbase 6.00 m), design CG at
x_cg = 6.80 m. Design rotation attitude 10.0 deg about the main gear
contact. Nose gear attach point 1.00 m below the main gear attach plane
(z_na = -1.00 m). Tail cone lowest point at x_tail = 12.40 m (5.00 m aft of
the main gear contact) with body height z_tail = -0.45 m and a required
rotation clearance of 0.25 m. Propeller disc lowest point from a hub center
body height of 0.10 m and a disc radius of 1.15 m (z = -1.05 m) at station
4.90 m with a required level clearance of 0.20 m. Nacelle lowest point at
z = -0.60 m, station 5.30 m, with a required level clearance of 0.15 m and a
required rotation clearance of 0.15 m.

- Required ground lines: tail cone level 0.450000000000 m, tail cone
  rotation 1.585491556514 m, propeller level 1.250000000000 m, nacelle
  level 0.750000000000 m, nacelle rotation 0.382027332295 m. The tail cone
  rotation constraint governs: H_gl = 1.585491556514 m.
- Main gear height h_mg = H_gl = 1.585491556514 m. Nose gear height h_ng =
  H_gl + z_na = 0.585491556514 m. Height difference h_mg - h_ng =
  1.000000000000 m, exactly -z_na.
- Tail contact height h_tail_contact = H_gl + z_tail = 1.135491556514 m at
  arm a_t = 5.00 m. Tail strike angle theta_ts = 12.794763238232 deg, a
  rotation margin of 2.794763238232 deg over the 10.0 deg design rotation.
- Margins: tail rotation margin 0.000000000000 m (the governing constraint
  binds exactly), propeller level margin 0.335491556514 m, nacelle level
  margin 0.835491556514 m, nacelle rotation margin 1.185180898483 m.
- Static load share: nose share (7.40 - 6.80) / 6.00 = 0.100000000000, main
  share 0.900000000000, sum 1.000000000000. Both gears carry positive load.
- Height verdict: every required margin is non-negative and both gear
  heights are positive, so the height verdict is clearance-ok.

## Verification

- Confirm static_ground_line on the worked points returns H_gl =
  1.585491556514 within 1e-9 with binding point "tail cone lowest point".
- Confirm gear_heights(1.585491556514, -1.00) returns main_gear_height
  1.585491556514, nose_gear_height 0.585491556514 and height_difference
  1.000000000000 within 1e-9.
- Confirm the tail rotation clearance recomputed from H_gl equals 0.25 m
  within 1e-9 (identity I1, the binding constraint round trip), and that
  the tangent algebra identities I2 and I3 hold within tolerance.
- Confirm tail_strike_angle_deg(1.135491556514, 5.00) returns
  12.794763238232 deg within 1e-6 and the rotation margin is positive.
- Confirm static_load_share(6.80, 7.40, 1.40) returns 0.100000000000 within
  1e-12 and complements the main share to 1.
- Confirm every ValueError rejection: negative clearance requirements,
  rotation angle outside (0, 25] deg, wheelbase not positive, empty point
  list, non-positive ground line, non-positive nose gear height, and
  non-positive propeller radius.
- Run the contract test offline: python3
  scripts/test_landing_gear_height_sizing.py (34 tests, deterministic).

## Related leaves

- vehicle-design/sizing/landing-gear-layout: takes the solved gear heights
  as given inputs to the tipback angle, tail strike clearance angle and
  lateral turnover angle checks; this leaf is the inverse of its tail
  strike identity.
- vehicle-design/sizing/landing-gear-sizing: sizes the static strut loads,
  the nose and main gear CG load split and the shock absorber stroke once
  the heights and layout are fixed.
- vehicle-design/mass-properties/cg-envelope: the CG travel band source for
  the design CG used in the static load share feasibility check.
- vehicle-design/sizing/propeller-sizing: the propeller diameter and blade
  count selection, and the installation clearance check of a given hub
  height, downstream of the height this leaf solves.

## Pitfalls

- Solving the ground line from the level attitude only: a point clear at
  the level attitude can still strike the ground during rotation, since
  every aft hard point drops as (H_gl + z_body) * cos(theta) - (x_point -
  x_mg) * sin(theta); the tail cone rotation requirement governs the worked
  example at 1.585491556514 m against its 0.450000000000 m level
  requirement.
- Treating a forward point's rotation clearance as binding: a point forward
  of the main gear contact (arm x_point - x_mg negative) rises during
  rotation, so its level-attitude clearance is the binding case, not its
  rotation clearance (identity I6 in the contract test).
- Confusing the small-angle rise with the exact rise: the tangent rise
  (x_tail - x_mg) * tan(theta_rot) understates the exact rise
  h_tail_contact - c_tail by c_tail * (1/cos(theta_rot) - 1), about 1.5% of
  the exact rise at 10 deg in the worked example (identity I3); use the
  exact cosine and sine form for the ground line solve, not the tangent
  approximation.
- Feeding the layout sibling's tail strike angle formula the wrong contact
  height: this leaf solves h_tail_contact = H_gl + z_tail as an output; the
  layout sibling's tail_strike_clearance_angle takes h_tail_contact as a
  given input. Do not reuse a contact height from another aircraft
  configuration.
- Skipping the static load share feasibility check: a solved geometry with
  positive gear heights and clearance margins can still be infeasible if
  the design CG does not sit strictly between the nose and main gear
  contacts; static_load_share raises ValueError in that case rather than
  returning a share outside [0, 1].

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_landing_gear_height_sizing.py

The test covers the worked static-ground-line solve and its per-constraint
required ground lines, the gear height derivation and the leveling
identity, the achieved clearance and margin of every hard point at both
attitudes, the tail strike angle and rotation margin of the solved
geometry, the static load share and its complement, the propeller low
point, the closed-form identities I1 through I6, the level-attitude round
trip, determinism of repeated solves, module constant fixity, and
ValueError rejection of every non-physical input listed in the spec
validation list.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 25 and CS-25 frame the
  transport landing gear context; the height-selection relations above are
  standard conceptual design methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
