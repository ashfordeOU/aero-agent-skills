# Wave-30 leaf spec: composite-repair (structures, composites pack)

- Path: skills/structures/composites/composite-repair/
- Pack: composites (siblings: adhesive-bonded-joints, cmh17-allowables,
  composite-bolted-joints, delamination-growth, failure-criteria,
  laminate-stiffness, sandwich-panels).
- Standards ids: cmh-17 (reference-only). Ledger Standard: cmh-17.
- Family: structures

## Claim

Size a bonded scarf repair for a damaged composite laminate: compute the scarf
length from the parent thickness and the scarf angle, the average adhesive
shear stress carried by the scarf joint at the parent laminate stress, the
required scarf angle for an adhesive shear allowable, and the external patch
thickness that restores the parent stiffness. Produces the scarf length,
adhesive shear stress, required scarf angle, and stiffness-matched patch
thickness that gate a composite repair design.

Does NOT do: analyze adhesive single-lap or double-lap bonded joints with the
Volkersen shear-lag parameter (adhesive-bonded-joints owns single-lap joint
analysis); analyze bolted joints in laminates under bearing and bypass loading
(composite-bolted-joints owns bearing, net-tension, shear-out); assess
delamination growth by fracture mechanics with DCB/ENF coupons
(delamination-growth owns G_I, G_II, mixed-mode blends); compute laminate
stiffness or failure criteria of the parent layup (laminate-stiffness and
failure-criteria own those; the parent modulus and applied stress are inputs
here); write repair station process specifications or NDT of the repair
(manufacturing-quality special-processes and ndt leaves own those). Scarf and
external-patch repair sizing only, uniform stress assumption, no bolted patch.

## Model (implement exactly)

Module constants:
- DEG2RAD = pi / 180.
- (no material constants; all inputs explicit so the leaf works for any
  carbon/epoxy or glass/epoxy system).

Functions (pure stdlib; angles in degrees for callers, converted internally):
- scarf_length(thickness, scarf_angle_deg) -> float:
  L = thickness / tan(scarf_angle_deg). ValueError if thickness <= 0 or
  scarf_angle_deg <= 0 or scarf_angle_deg >= 90.
- adhesive_shear_stress(parent_stress, scarf_angle_deg) -> float:
  tau = parent_stress * sin(theta) * cos(theta) (uniform-stress scarf
  model). ValueError if parent_stress < 0 or angle out of (0, 90).
- required_scarf_angle(parent_stress, allowable_shear) -> float (degrees):
  from tau = (sigma / 2) * sin(2 theta): theta = 0.5 * asin(2 *
  allowable_shear / parent_stress). ValueError if parent_stress <= 0,
  allowable_shear <= 0, or 2 * allowable_shear / parent_stress > 1.0
  (no real angle can carry the load; the repair cannot be made in scarf
  at that stress).
- patch_thickness_for_stiffness(parent_thickness, parent_modulus,
  patch_modulus) -> float: t_patch = parent_thickness * parent_modulus /
  patch_modulus (in-plane stiffness match for an external bonded patch).
  ValueError if any <= 0.
- repair_sizing(parent_thickness, parent_stress, parent_modulus, patch_modulus,
  scarf_angle_deg, allowable_shear) -> dict: {scarf_length_m, scarf_angle_deg,
  adhesive_shear_Pa, required_scarf_angle_deg (for the allowable; may be
  steeper than the chosen angle - report both), patch_thickness_m,
  margin (allowable_shear / adhesive_shear - 1)}. ValueErrors propagate.
  margin < 0 means the chosen scarf angle does not clear the allowable.

## Worked example

Carbon/epoxy parent: thickness 3.0 mm, applied laminate stress 300 MPa,
parent modulus 70 GPa, patch material modulus 70 GPa (same material),
scarf angle 3 degrees, adhesive shear allowable 12 MPa.

Deterministic anchors (module outputs as assert targets to 4 s.f. plus bounds):
- scarf_length ~57 mm (3.0 / tan(3 deg) = 3.0 / 0.05241 = 57.24 mm; bound
  50-65 mm).
- adhesive shear stress ~15.7 MPa (300 * sin3 * cos3 = 300 * 0.05234 *
  0.99863 = 15.68 MPa; bound 14-17 MPa) -> with a 12 MPa allowable the chosen
  3 deg scarf FAILS (margin negative).
- required scarf angle for 12 MPa: sin(2 theta) = 24/300 = 0.08,
  2 theta = 4.589 deg, theta = 2.29 deg (bound 2.0-2.6 deg).
- patch thickness same material = 3.0 mm exactly (identity).
- margin negative for the 3 deg case (value in -0.35 to -0.15), positive for
  a 2.2 deg scarf example if you add one (adhesive shear 300*sin2.2*cos2.2 =
  300*0.03839*0.99926 = 11.51 MPa < 12 -> margin +0.04). Include BOTH cases in
  the contract test.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: thickness/angle/parent_stress/allowable <= 0, angle >= 90,
  required_scarf_angle when 2*tau_a/sigma > 1 (e.g. sigma 100 MPa, tau_a
  80 MPa raises).
- patch identity: patch_thickness_for_stiffness(t, E, E) == t.
- margin sign cases above.
- Determinism.

## Corpus fragment (eval/hit1-wave30-composite-repair.yaml)

Forbidden tokens (siblings): volkersen, single-lap, overlap, bearing,
bypass, net-tension, shear-out, dcb, enf, delamination-growth, laminate
stiffness matrix, failure index. Distinctive tokens ONLY: composite-repair,
scarf-repair, scarf-length, adhesive-shear, stiffness-matched-patch.

Query 1: "Size a scarf-repair for a 3 mm composite laminate at 300 MPa parent
stress: scarf-length at 3 degrees and adhesive-shear stress" (id
w30-composite-repair-1).
Query 2: "Select a stiffness-matched-patch thickness for an external bonded
composite-repair when the patch modulus is 70 GPa and the parent is 70 GPa"
(id w30-composite-repair-2).
intent: "structures; bonded scarf composite repair sizing".

## Description/tag guidance

Description opens "Use when you must size a bonded scarf repair for a damaged
composite laminate:" and lists the outputs in the Claim. First tag:
composite-repair. Additional tags: scarf-repair, scarf-length,
adhesive-shear-stress, stiffness-matched-patch. No generic single words.
50-150 words, <=1000 chars, no em dash, no "classified".
