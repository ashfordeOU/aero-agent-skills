---
name: landing-gear-layout
description: "Use when you must lay out the landing gear arrangement of an aircraft against its center-of-gravity envelope: compute the tipback angle at the aft CG limit about the main gear contact, the tail strike clearance angle at rotation, the lateral turnover angle from the wheel track at the forward CG limit, and the nose gear load fraction band across the CG travel. Produces the three layout angles in degrees, the nose gear load fraction at the forward and aft CG limits with band verdicts, and the main gear position check that gate the landing gear configuration. Trigger: landing gear layout, tipback angle, tail strike clearance, lateral turnover, nose gear load fraction, main gear position, wheel track, CG travel limits."
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
  tags: [landing-gear-layout, tipback-angle, lateral-turnover-angle, tail-strike-clearance-angle, nose-gear-load-fraction, main-gear-positioning]
  version: 0.1.0
  author: Aero Agent Skills
---

# Landing Gear Layout (vehicle-design/sizing/landing-gear-layout)

Use when the task is laying out a tricycle landing gear arrangement
against the center-of-gravity envelope: the tipback angle at the aft CG
limit, the tail strike clearance angle at rotation about the main gear
contact, the lateral turnover angle from the wheel track, and the nose
gear static load fraction band across the CG travel, closing with the
main gear position check that gates the configuration. This leaf
implements the arrangement geometry with deterministic stdlib
trigonometry and statics, with fixed rotation and station conventions so
the outputs are reproducible. It pairs with
vehicle-design/sizing/landing-gear-sizing, which sizes the strut loads
and landing energy once the layout is fixed, and takes the CG travel
limits as given inputs from
vehicle-design/mass-properties/cg-envelope.

## Domain quick reference

Pinned conventions: stations x are measured in metres aft of a fuselage
datum, the ground plane is z = 0 at the tire contacts with the static
deflection, rotations are nose-up about the main gear contact point,
and all angles are returned in degrees. The aircraft is level on the
ground in the reference attitude, and the aft CG limit sits forward of
the main gear contact by the margin d = x_mg - x_cg_aft.

- Tipback angle: rotating nose-up about the main gear contact by the
  tipback angle brings the aft CG onto the vertical through the
  contact; beyond that attitude the vertical CG line passes aft of the
  contact and gravity rolls the aircraft onto its tail. The rotation
  obeys tan(theta_tip) = (x_mg - x_cg_aft) / h_cg, so theta_tip =
  atan((x_mg - x_cg_aft) / h_cg). The angle grows with the aft-CG
  margin and vanishes when the aft CG reaches the contact station.
  This is the standard tipback check from common conceptual design
  methodology (name and paraphrase only).
- Tail strike clearance: the tail cone lowest point at station x_tail
  and height h_tail_contact above the ground descends during the
  rotation as z(theta) = h_tail_contact * cos(theta) -
  a * sin(theta) with the horizontal arm a = x_tail - x_mg, which
  vanishes at tan(theta_ts) = h_tail_contact / a. The rotation attitude
  is tail-strike limited when theta_ts sits below the tipback angle,
  the transport-typical ordering.
- Lateral turnover, main gear pair: rolling about the line joining the
  two main gear contacts, tan(theta_lat) = h_cg / (track / 2) =
  2 * h_cg / track.
- Lateral turnover, tricycle diagonal: rolling about the diagonal line
  joining the nose gear contact and the nearer main gear contact, the
  perpendicular ground-plane distance from the CG vertical to the
  diagonal is d_perp = (x_cg - x_ng) * (track / 2) /
  sqrt(wheelbase^2 + (track / 2)^2) with wheelbase = x_mg - x_ng, and
  theta = atan(d_perp / h_cg). The diagonal arm is shorter than the
  half track, so the tricycle angle is the lower, binding lateral
  check at a forward CG.
- Nose gear static load fraction: the moment balance about the main
  gear contact gives P_n / W = (x_mg - x_cg) / (x_mg - x_ng); the nose
  gear carries more when the CG is forward, so the aft CG limit gives
  the lower fraction and the forward CG limit the upper one. The
  fraction is dimensionless and layout-level only; strut loads are
  never computed here.
- Typical bands used by the verdicts: nose gear fraction 5-20 % of the
  total weight (NOSE_FRACTION_MIN to NOSE_FRACTION_MAX), lateral
  turnover 40-50 deg for transports, and ROTATION_REF_DEG = 10.0 deg
  as the typical transport unstick rotation reference.
- FAR-25 and CS-25 frame the transport landing gear arrangement
  context; the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Fix the arrangement geometry: the nose gear station x_ng, the main
   gear station x_mg, the tail cone lowest point station x_tail and
   contact height h_tail_contact, the CG height h_cg, the main gear
   wheel track, and the CG travel limits with the aft limit x_cg_aft
   forward of x_mg (otherwise the module raises ValueError).
2. Tipback angle check at the aft CG limit: run tipback_angle(h_cg,
   x_mg, x_cg_aft) and read the nose-up rotation about the main gear
   contact at which the aircraft would tip onto its tail.
3. Tail strike clearance at rotation: run
   tail_strike_clearance_angle(h_tail_contact, x_tail, x_mg) and
   compare it with the tipback angle; when the tail strike angle sits
   below the tipback angle the rotation attitude is tail-strike
   limited. Reference ROTATION_REF_DEG for the rotation margin print.
4. Lateral turnover checks from the wheel track: run
   lateral_turnover_angle(h_cg, track) for the simplified main gear
   pair check, then lateral_turnover_tricycle_angle(h_cg, x_cg, x_mg,
   x_ng, track) at the forward CG limit for the nose-to-main diagonal
   refinement, which binds when it sits below the main-pair value.
5. Nose gear load fraction band across the CG travel: run
   nose_gear_static_load_fraction(x_cg, x_mg, x_ng) at the forward and
   aft CG limits and compare each limit fraction against
   NOSE_FRACTION_MIN and NOSE_FRACTION_MAX for the band verdicts.
6. Main gear position check and close: confirm both CG travel limits
   sit inside the nose-to-main station pair with a positive aft
   margin, carry the angles and the fraction band verdicts into the
   layout gate, and run the deterministic contract test
   scripts/test_landing_gear_layout.py.

## Worked example

Transport-class aircraft: W = 60000 kg, wheelbase 15 m with the nose
gear at x_ng = 3 m and the main gear at x_mg = 18 m from the datum, CG
travel from the forward limit x_cg_fwd = 14 m to the aft limit
x_cg_aft = 16.5 m, CG height h_cg = 2.8 m, main gear track = 6.5 m,
tail cone lowest point at x_tail = 30 m at h_tail_contact = 3.5 m
above the ground.

- Nose fractions: fwd = (18 - 14) / 15 = 0.266667 (26.6667 %) and aft
  = (18 - 16.5) / 15 = 0.1 (10.0 %); on the 60000 kg weight the nose
  gear carries 16000 kg at the forward CG limit and 6000 kg at the aft
  CG limit.
- Tipback angle: the aft CG sits d = 1.5 m forward of the main gear
  contact, so theta_tip = atan(1.5 / 2.8) = 28.1786 deg
  (tipback_angle(2.8, 18.0, 16.5)).
- Tail strike clearance: arm a = 12 m, theta_ts = atan(3.5 / 12) =
  16.2602 deg (tail_strike_clearance_angle(3.5, 30.0, 18.0)), giving a
  6.2602 deg margin against the 10.0 deg unstick rotation reference.
  Tail strike precedes tipback (16.2602 < 28.1786), so rotation is
  tail-strike limited, matching transport practice.
- Lateral turnover: the simplified main gear pair check gives
  theta_lat = atan(2 * 2.8 / 6.5) = 40.7462 deg
  (lateral_turnover_angle(2.8, 6.5)), inside the 40-50 deg transport
  band. The tricycle diagonal check at the forward CG gives d_perp =
  11 * 3.25 / sqrt(15^2 + 3.25^2) = 2.32908 m and theta =
  atan(2.32908 / 2.8) = 39.7567 deg
  (lateral_turnover_tricycle_angle(2.8, 14.0, 18.0, 3.0, 6.5)),
  marginally below the main-pair value as the binding lateral case.
- Verdicts: the aft CG fraction of 10.0 % sits inside the 5-20 %
  typical band (True); the forward CG fraction of 26.6667 % sits above
  it (False) and flags the arrangement, because with the forward CG
  limit 4 m ahead of the main gear the nose gear is over-weighted and
  the main gear station or the forward CG limit must move before the
  layout closes. The lateral turnover angle sits inside the 40-50 deg
  band (True).

## Verification

- Confirm tipback_angle(2.8, 18.0, 16.5) returns 28.1786 deg and that
  doubling the aft-CG margin at fixed h_cg doubles tan(theta_tip).
- Confirm tail_strike_clearance_angle(3.5, 30.0, 18.0) returns
  16.2602 deg and that the rotation margin against ROTATION_REF_DEG is
  6.2602 deg.
- Confirm lateral_turnover_angle(2.8, 6.5) returns 40.7462 deg and
  lateral_turnover_tricycle_angle(2.8, 14.0, 18.0, 3.0, 6.5) returns
  39.7567 deg, below the main-pair value.
- Confirm nose_gear_static_load_fraction returns 0.266667 at the
  forward CG limit and 0.1 at the aft CG limit, that the two fractions
  complement the main gear share to 1, and that the aft CG limit sits
  inside the 5-20 % typical band while the forward CG limit sits above
  it.
- Confirm repeated calls return identical scalars and that every
  non-positive height, non-positive track, aft CG limit at or behind
  the main gear station, tail station at or forward of the main gear
  station, and CG station outside the nose-to-main pair raises
  ValueError rather than returning a plausible number.

## Pitfalls

- Using the aft CG at or behind the main gear station: the nose gear
  fraction goes to zero or negative and the tipback arrangement is
  statically tipped; the logic raises ValueError on x_cg_aft >= x_mg.
- Reading the simplified main-pair lateral angle as the binding check:
  the tricycle diagonal arm is shorter than the half track, so at a
  forward CG the diagonal angle (39.7567 deg in the worked example)
  sits below the main-pair value (40.7462 deg) and is the binding
  lateral case.
- Taking the mid-wheelbase fraction as the band check: the nose gear
  carries more when the CG is forward, so the band verdict must be
  taken at the forward and aft CG limits, not at a single station.
- Treating the layout geometry as the strut load split: the nose
  fraction here is dimensionless and layout-level only; the strut
  loads and landing energy for a given wheelbase belong to
  vehicle-design/sizing/landing-gear-sizing.
- Using exact float equality on computed sums: tan and atan round-trip
  only to machine precision, so verification uses tolerances
  (assertAlmostEqual with a delta or math.isclose).

## Related leaves

- vehicle-design/sizing/landing-gear-sizing: the strut weight split
  and landing energy demand for a given wheelbase once the layout is
  fixed.
- vehicle-design/sizing/landing-gear-retraction-sizing: the retraction
  mechanism sized after the arrangement exists.
- vehicle-design/sizing/tire-sizing: tire selection from the per-tire
  load.
- vehicle-design/mass-properties/cg-envelope: the CG travel band from
  longitudinal stability, taken as a given input here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_landing_gear_layout.py

The test covers the worked-example layout contract (tipback 28.1786
deg, tail strike 16.2602 deg with a 6.2602 deg rotation margin, lateral
40.7462 deg, tricycle diagonal 39.7567 deg at the forward CG limit,
nose gear load fraction 0.266667 forward and 0.1 aft), the tangent
doubling identities for the aft-CG margin, the tail contact height and
the wheel track, the vanishing-angle limits at the contact stations,
the nose fraction complement to 1 and the mid-wheelbase 0.5 identity,
the band verdicts against NOSE_FRACTION_MIN and NOSE_FRACTION_MAX, the
main gear position check, determinism of repeated calls, degree and
dimensionless return types, and ValueError rejection of every
non-physical input class.

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 are transport
  airworthiness standards (ecfr.gov and easa.europa.eu); the
  arrangement relations above are standard conceptual design
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
