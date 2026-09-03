---
name: composite-repair
description: "Use when you must size a bonded scarf repair for a damaged composite laminate: compute the scarf length from the parent thickness and the scarf angle, the average adhesive shear stress carried by the scarf joint at the parent laminate stress, the required scarf angle for an adhesive shear allowable, and the external patch thickness that restores the parent stiffness. Produces the scarf length, adhesive shear stress, required scarf angle, and stiffness-matched patch thickness that gate a composite repair design. Trigger: composite-repair, scarf-repair, scarf-length, adhesive-shear-stress, stiffness-matched-patch, scarf angle, adhesive shear allowable, bonded repair, patch thickness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [composite-repair, scarf-repair, scarf-length, adhesive-shear-stress, stiffness-matched-patch]
  version: 0.1.0
  author: Aero Agent Skills
---

# Composite Repair (structures/composites/composite-repair)

Use when you must size a bonded scarf repair for a damaged composite
laminate: computing the scarf length from the parent thickness and the
scarf angle, the average adhesive shear stress carried by the scarf
joint when the parent laminate runs at its applied stress, the required
scarf angle for an adhesive shear allowable, and the external patch
thickness that restores the parent in-plane stiffness. This leaf
implements the standard uniform-stress scarf joint model in pure Python,
stdlib only, with no material constants so it applies to any
carbon/epoxy or glass/epoxy system. It pairs with the other composites
leaves: laminate-stiffness and failure-criteria provide the parent
layup modulus and the applied laminate stress used as inputs here, and
cmh17-allowables frames the adhesive and laminate allowables.

## Domain quick reference

- Scarf length for a full-depth scarf: L = thickness / tan(theta),
  where theta is the scarf angle measured from the laminate plane. A
  shallower angle gives a longer scarf.
- Average adhesive shear stress (uniform-stress scarf model):
  tau = sigma * sin(theta) * cos(theta), equivalently tau =
  (sigma / 2) * sin(2 * theta), with sigma the far-field parent laminate
  stress carried across the scarf plane.
- Required scarf angle for an adhesive shear allowable tau_a:
  theta_req = 0.5 * asin(2 * tau_a / sigma). When
  2 * tau_a / sigma exceeds 1.0 no real scarf angle can carry the load
  at that stress; the repair cannot be made in scarf.
- Stiffness-matched external patch: t_patch = t_parent * E_parent /
  E_patch, matching the parent in-plane stiffness when the patch runs at
  the parent strain.
- Margin: margin = tau_a / tau - 1. A negative margin means the chosen
  scarf angle does not clear the allowable, and the scarf must be made
  shallower (longer) so the adhesive shear drops to the allowable.
- Angles are degrees for callers; repair_sizing takes SI inputs (m, Pa)
  and returns scarf_length_m, adhesive_shear_Pa and patch_thickness_m.
- CMH-17 frames bonded repair practice for composite structures; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the repair inputs: parent laminate thickness, the applied
   laminate stress at the repair location, the parent modulus, the patch
   material modulus, a chosen scarf angle, and the adhesive shear
   allowable.
2. Compute the scarf length with scarf_length from the parent thickness
   and the chosen scarf angle.
3. Compute the average adhesive shear stress with
   adhesive_shear_stress from the parent stress and the chosen scarf
   angle.
4. Check the scarf angle against the allowable with
   required_scarf_angle: if the required angle differs from the chosen
   angle in the steep direction, the chosen scarf does not clear the
   allowable.
5. Size the external patch with patch_thickness_for_stiffness from the
   parent thickness and the two moduli; a stiffer patch is thinner, a
   softer patch is thicker.
6. Run repair_sizing for the full summary including the margin, and
   re-scarf at the required angle whenever the margin is negative.
7. Confirm the deterministic checks with the contract test
   scripts/test_composite_repair.py.

## Worked example

Carbon/epoxy parent: thickness 3.0 mm, applied laminate stress 300 MPa,
parent modulus 70 GPa, patch material modulus 70 GPa (same material),
scarf angle 3 degrees, adhesive shear allowable 12 MPa.

- Scarf length: L = 3.0 / tan(3 deg) = 57.24 mm (scarf_length(3.0, 3.0)
  = 57.24 mm, within the 50-65 mm band).
- Adhesive shear stress: tau = 300 * sin(3 deg) * cos(3 deg) = 15.68 MPa
  (adhesive_shear_stress(300.0, 3.0) = 15.679 MPa, within the 14-17 MPa
  band).
- Required scarf angle for the 12 MPa allowable:
  theta_req = 0.5 * asin(24 / 300) = 2.29 deg (required_scarf_angle
  gives 2.294 deg, within the 2.0-2.6 deg band).
- Patch thickness: t_patch = 3.0 * 70 / 70 = 3.0 mm exactly, the
  same-material identity.
- Margin at 3 degrees: 12 / 15.68 - 1 = -0.235. The chosen 3 deg scarf
  FAILS the 12 MPa allowable; the repair must be re-scarfed shallower.
- Passing check at 2.2 degrees: tau = 300 * sin(2.2 deg) * cos(2.2 deg)
  = 11.51 MPa, margin = 12 / 11.51 - 1 = +0.043, so a 2.2 deg scarf
  clears the allowable.

## Verification

- Confirm scarf_length(3.0, 3.0) returns 57.24 mm and sits in 50-65 mm.
- Confirm adhesive_shear_stress(300.0, 3.0) returns 15.679 MPa and sits
  in 14-17 MPa.
- Confirm required_scarf_angle(300.0, 12.0) returns 2.294 deg and sits
  in 2.0-2.6 deg.
- Confirm the margin is negative for the 3 deg case (-0.235) and
  positive for the 2.2 deg case (+0.043).
- Confirm the patch identity
  patch_thickness_for_stiffness(t, E, E) == t and the sin-cos form of
  the shear equals the (sigma / 2) * sin(2 theta) form.
- Confirm every non-positive thickness, stress, modulus or allowable,
  every angle at or beyond 90 degrees, and every required_scarf_angle
  call with 2 * tau_a / sigma > 1 (for example sigma = 100 MPa,
  tau_a = 80 MPa) raises ValueError.
- Run the contract test offline: python3
  scripts/test_composite_repair.py (34 tests, deterministic).

## Related leaves

- structures/composites/adhesive-bonded-joints: lap joint bonded
  analysis in the same pack; lap geometry analysis is not part of this
  leaf.
- structures/composites/composite-bolted-joints: mechanically fastened
  patch attachment analysis, the alternative to a bonded repair.
- structures/composites/laminate-stiffness: parent layup stiffness, an
  input to the stiffness-matched patch sizing here.
- structures/composites/cmh17-allowables: laminate and adhesive
  allowables used as inputs here.
- structures/composites/delamination-growth: fracture assessment of
  interlaminar damage growth in the parent around the repair location.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_composite_repair.py

The test covers the worked example contract (scarf length 57.24 mm,
adhesive shear 15.68 MPa, required angle 2.29 deg, patch identity 3.0
mm), the magnitude bounds from the spec (50-65 mm, 14-17 MPa, 2.0-2.6
deg), the margin signs for both the failing 3 deg case and the passing
2.2 deg case, the sin-cos closed-form identity, the
required-angle round-trip (scarfing at the required angle reproduces
the allowable), determinism, and ValueError rejection of non-physical
inputs.

## Compliance

- Standards referenced, not reproduced: CMH-17 (the Composite Materials
  Handbook) is referenced for bonded scarf repair practice; the repair
  sizing relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
