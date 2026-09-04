---
name: canard-sizing
description: "Use when you must size the canard of a canard-configured aircraft: compute the required canard area for a target canard volume coefficient from the canard arm and the wing reference geometry, derive the trim lift share carried by the forward canard from the longitudinal geometry, resolve the canard and wing lift coefficients at the trim condition, and run the stall precedence check that the canard reaches maximum lift before the wing so the nose drops instead of pitching up. Produces the canard area, trim lift share, trim lift coefficients, and the stall precedence verdict. Trigger: canard sizing, canard volume coefficient, canard area, forward wing, stall precedence, canard configuration, trim lift share."
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
  tags: [canard-sizing, canard-volume-coefficient, trim-lift-share, stall-precedence, canard-configuration, canard-area, forward-wing]
  version: 0.1.0
  author: Aero Agent Skills
---

# Canard Sizing (vehicle-design/sizing/canard-sizing)

Use when the task is sizing the forward canard surface of a
canard-configured or three-surface aircraft: the canard area needed
for a target canard volume coefficient, the trim lift share carried
by the canard in steady level flight, the canard and wing lift
coefficients at the trim condition, and the stall precedence check
that the canard stalls before the wing so the nose drops rather than
pitches up. This leaf implements the conceptual sizing loop in pure
Python, stdlib only. It pairs with vehicle-design/sizing/tail-sizing,
which owns the conventional aft empennage volume coefficients V_h and
V_v, and with flight-mechanics/stability-control/longitudinal-stability
for the neutral point and static margin that frame canard trim.

## Domain quick reference

- Canard volume coefficient: V_c = S_c * L_c / (S * cbar), with S_c
  the canard area (m2), L_c the canard arm (m) from the wing
  aerodynamic center to the canard aerodynamic center, S the wing
  reference area (m2) and cbar the wing mean aerodynamic chord (m).
  The convention mirrors V_h for a horizontal tail, but the surface
  lies forward of the wing.
- Required canard area: S_c = V_c_target * S * cbar / L_c. A canard
  configuration that must trim at a forward center of gravity with a
  high nose-down pitching moment needs a large V_c target (0.35 to
  0.6 typical at conceptual level).
- Geometry convention: x positive aft, origin at the wing aerodynamic
  center, canard forward of the wing (x_c < x_w = 0) and the center
  of gravity between them (x_c < x_cg < x_w).
- Trim lift share: f_c = (x_w - x_cg) / (x_w - x_c), the fraction of
  weight carried by the canard from the moment balance about the
  center of gravity with lift up positive. Moving the CG aft lowers
  the canard share.
- Trim lift coefficients: L_c = f_c * weight, L_w = weight - L_c,
  then Cl_c = L_c / (q * S_c) and Cl_w = L_w / (q * S_w) at the
  dynamic pressure q.
- Stall precedence margins: margin_c = Cl_max_c / Cl_c and margin_w =
  Cl_max_w / Cl_w. The surface with the smaller margin reaches its
  maximum lift first. A canard layout is pitch-safe only when the
  canard stalls first, so the nose drops instead of pitching up.
- Units are SI throughout: m, m2, N, Pa, kg/m3, dimensionless
  coefficients.
- FAR 25 and CS 25 flight characteristics requirements frame the
  pitch-up avoidance intent; the relations above are standard
  engineering methodology, summary-only.

## Workflow

1. Fix the wing reference quantities (wing_area S, wing_mac cbar) and
   the canard arm from the layout; pick the target canard volume
   coefficient for the configuration and the CG envelope.
2. Size the surface: required_canard_area gives the canard area for
   the target coefficient, or run size_canard for the area plus the
   echoed coefficient.
3. Verify the chosen area with canard_volume_coefficient, which must
   return the target (round trip).
4. Compute the trim lift share with canard_lift_share at the CG
   station of interest; the geometry must satisfy x_c < x_cg < x_w.
5. Resolve the trim condition with trim_lift_coefficients from the
   weight and dynamic pressure to get the canard and wing lift
   forces and coefficients.
6. Run the stall precedence check with stall_precedence on the trim
   coefficients and the surface maximum lift coefficients. The
   verdict must read canard-stalls-first for the nose to drop rather
   than pitch up at the stall.
7. Sweep the CG envelope: at the aft CG the canard share falls and
   the verdict can flip to wing-stalls-first, which flags the pitch
   up risk and demands a larger V_c or a CG limit.
8. Confirm the deterministic checks with the contract test
   scripts/test_canard_sizing.py.

## Worked example

Canard-configured light aircraft: wing area S = 30 m2, wing MAC cbar
= 2.8 m, canard arm L_c = 9 m, target V_c = 0.45. Forward CG case
x_cg = -3 m, canard x_c = -9 m, wing x_w = 0 m. Weight = 1200 * g0 N
with g0 = 9.80665 m/s2; dynamic pressure q = 0.5 * 1.225 * 45^2 =
1240.3 Pa. Canard Cl_max = 1.7, wing Cl_max = 1.5.

- Required area: S_c = 0.45 * 30 * 2.8 / 9 = 4.2 m2. Round trip:
  V_c = 4.2 * 9 / (30 * 2.8) = 0.45.
- Forward CG trim share: f_c = (0 - (-3)) / (0 - (-9)) = 3/9 =
  0.3333.
- Trim forces and coefficients: L_c = 3922.7 N, L_w = 7845.3 N,
  Cl_c = 3922.7 / (1240.3 * 4.2) = 0.7526, Cl_w = 7845.3 / (1240.3 *
  30) = 0.2108.
- Stall precedence: margin_c = 1.7 / 0.7526 = 2.259 against
  margin_w = 1.5 / 0.2108 = 7.116, verdict canard-stalls-first.
- Aft CG case x_cg = -1 m: f_c = 1/9 = 0.1111, Cl_c = 0.2510, Cl_w =
  0.2811, margin_c = 6.77 against margin_w = 5.34, verdict
  wing-stalls-first, which demonstrates the pitch-up risk when the
  CG moves aft.


## Pitfalls

- Declaring pitch safety without the stall precedence check: a
  canard layout is only pitch-safe when the canard stalls first
  (margin_c < margin_w); in the worked example the aft CG case flips
  to wing-stalls-first, so a fixed canard area is not safe across
  the whole CG envelope.
- Sizing the area and skipping the CG sweep: the trim share f_c =
  (x_w - x_cg) / (x_w - x_c) falls as the CG moves aft (0.3333 to
  0.1111 in the worked example), so the surface must be checked at
  the aft CG where the pitch-up risk lives.
- Violating the geometry convention: the layout must satisfy
  x_c < x_cg < x_w with x positive aft; a CG station outside that
  ordering is rejected and the share formula loses meaning.
- Comparing margins across the wrong surface: the surface with the
  SMALLER margin (Cl_max / Cl) reaches its maximum lift first, so
  canard-stalls-first needs margin_c < margin_w, not the larger
  coefficient.
- Forgetting the coefficient depends on dynamic pressure: Cl_c =
  L_c / (q * S_c) and Cl_w = L_w / (q * S_w) use the trim q; the
  stall precedence verdict changes if q changes, so the check
  belongs at the actual trim condition.
- Treating the canard like a tail: the volume coefficient mirrors
  V_h but the surface lies FORWARD of the wing and carries upload
  (positive trim lift), which is the opposite of the download a
  conventional tail usually carries.
## Verification

- Confirm required_canard_area(0.45, 9, 30, 2.8) returns 4.2 m2 and
  canard_volume_coefficient(4.2, 9, 30, 2.8) recovers 0.45.
- Confirm canard_lift_share(-3, 0, -9) returns 0.3333 and
  canard_lift_share(-1, 0, -9) returns 0.1111.
- Confirm trim_lift_coefficients at the worked example returns the
  anchor values above, and that the canard and wing lift forces sum
  to the weight.
- Confirm stall_precedence returns the canard-stalls-first verdict at
  the forward CG and wing-stalls-first at the aft CG, with the
  margin ratios 2.259/7.116 and 6.77/5.34.
- Confirm every non-positive volume coefficient target, area, arm,
  wing reference quantity, dynamic pressure, weight, maximum lift
  coefficient and trim lift coefficient raises ValueError, and that
  any CG station outside x_c < x_cg < x_w is rejected.
- Run the contract test offline: python3
  scripts/test_canard_sizing.py (45 tests, deterministic).

## Related leaves

- vehicle-design/sizing/tail-sizing: conventional aft empennage
  volume coefficients V_h and V_v, the alternative layout for the
  same trim function.
- flight-mechanics/stability-control/longitudinal-stability: the
  neutral point and static margin that frame where the canard trim
  share must act.
- vehicle-design/sizing/control-surface-sizing: elevators or
  control authority on the canard when the surface carries
  controls.
- vehicle-design/sizing/wing-planform-sizing: wing reference area
  and chord inputs for the canard volume coefficient.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_canard_sizing.py

The test covers the worked example anchors (required canard area 4.2
m2 within 1e-6, volume coefficient round trip within 1e-9, trim lift
share 0.3333 at the forward CG and 0.1111 at the aft CG, trim lift
coefficients 0.7526 and 0.2108, stall precedence margin ratios and
both verdicts), the coefficient scaling laws and lift split identity,
the size_canard convenience wrapper, and ValueError rejection of
non-positive inputs and of CG stations outside x_c < x_cg < x_w.

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 flight
  characteristics requirements frame the pitch-up avoidance intent
  for canard configurations; the canard sizing relations above are
  standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
