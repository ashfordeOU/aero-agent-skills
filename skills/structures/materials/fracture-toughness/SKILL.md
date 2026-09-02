---
name: fracture-toughness
description: "Use when you must apply the plane-strain fracture toughness K_IC of an aerospace material: compute the applied stress intensity K = Y * sigma * sqrt(pi * a) for a crack of size a under remote stress sigma with geometry factor Y, check the failure criterion K >= K_IC, size the critical crack at which fast fracture starts, and judge whether a test specimen meets the ASTM E399 plane-strain validity requirement that thickness and crack size both exceed 2.5 * (K_IC / sigma_ys)^2. Connects fracture toughness data to damage tolerance analysis and MMPDS material allowables. Trigger: fracture-toughness, kic, stress-intensity-factor, critical-crack-size, plane-strain, fast-fracture, damage-tolerance, mmpds."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: materials
  tags: [fracture-toughness, kic, stress-intensity-factor, critical-crack-size, plane-strain, fast-fracture, damage-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fracture Toughness (structures/materials/fracture-toughness)

Use when the task is the fracture toughness of an aerospace material:
applied stress intensity K from stress, crack size, and geometry factor,
the failure criterion K >= K_IC, the critical crack size at fast
fracture, and the plane-strain validity of the K_IC test specimen, as
the materials property that gates damage tolerance sizing.

## Domain quick reference

- Plane-strain fracture toughness K_IC: the material property measuring
  resistance to unstable mode I crack extension under a triaxial
  plane-strain constraint at the crack tip. Units MPa sqrt(m) or
  ksi sqrt(in). A valid K_IC is a size-independent lower-bound
  toughness; thin sections show higher, geometry-dependent toughness.
- Applied stress intensity: K = Y * sigma * sqrt(pi * a), with sigma
  the remote stress in MPa, a the crack size (half length of a
  through-crack, depth of an edge crack) in meters, and Y the
  dimensionless geometry factor (1.0 for a crack in an infinite plate,
  1.12 for an edge crack). K has units of stress times sqrt(length):
  MPa sqrt(m).
- Worked anchor: sigma = 200 MPa, a = 5 mm = 0.005 m, edge crack
  Y = 1.12 gives K = 1.12 * 200 * sqrt(pi * 0.005) = 28.07 MPa sqrt(m).
- Failure criterion: fast fracture initiates when K >= K_IC. At
  K_IC = 26 MPa sqrt(m) the anchor crack fails; the applied K of
  28.07 MPa sqrt(m) exceeds the toughness.
- Critical crack size: a_c = (K_IC / (Y * sigma)) ** 2 / pi. At
  K_IC = 30 MPa sqrt(m), sigma = 200 MPa, Y = 1.12 the critical crack
  is a_c = (30 / 224) ** 2 / pi = 5.71 mm. It scales with 1 / sigma^2:
  doubling the stress quarters the tolerable crack size.
- Plane-strain validity (ASTM E399 test context): a valid K_IC test
  requires specimen thickness B and crack size a both >=
  2.5 * (K_IC / sigma_ys) ** 2, with sigma_ys the 0.2 percent offset
  yield strength. Anchor: K_IC = 30 MPa sqrt(m), sigma_ys = 500 MPa
  gives 2.5 * (30 / 500) ** 2 = 9 mm; thinner specimens measure a
  plane-stress or transitional toughness, not K_IC.
- Damage tolerance link: K_IC is the material property that gates
  damage tolerance sizing; residual-strength analysis evaluates the
  remaining strength of the cracked part against K_IC, fatigue growth
  governs the life between inspections, and MMPDS compiles the
  statistically based A-basis and B-basis allowables from which design
  toughness values are taken. The formula and validity rule are common
  materials-engineering methodology, summary-only.

## Workflow

1. Identify the material K_IC and its source: MMPDS allowables or test
   data for the correct product form, heat treatment, thickness, and
   loading orientation (LT versus TL), and confirm the section meets
   the plane-strain validity requirement.
2. Define the crack scenario: crack size a in meters, remote stress
   sigma in MPa, and the geometry factor Y for the crack configuration
   (edge crack 1.12, embedded crack 1.0, or the configuration-specific
   value).
3. Compute the applied stress intensity with stress_intensity:
   K = Y * sigma * sqrt(pi * a).
4. Check the failure criterion with is_fracture: K >= K_IC means fast
   fracture initiates at this crack size and stress; otherwise the
   crack is stable at this load level.
5. Size the critical crack with critical_crack_size:
   a_c = (K_IC / (Y * sigma)) ** 2 / pi, and compare it with the NDI
   detectable crack size to set inspection intervals (damage tolerance
   link).
6. Verify plane strain with plane_strain_valid: thickness and crack
   size must both exceed 2.5 * (K_IC / sigma_ys) ** 2; if not, the
   measured toughness is thickness dependent and the analysis needs the
   thickness-corrected toughness or a full ASTM E399 test program.

## Pitfalls

- Confusing K_IC with the Ramberg-Osgood yield point
  (ramberg-osgood): K_IC is a crack-resistance property in
  MPa sqrt(m), not a stress; sigma_0.2 is a plain-specimen strength in
  MPa. High yield strength does not imply high toughness, and many
  alloys trade the two against each other in heat treatment, so never
  infer toughness from the stress-strain curve.
- Reading K_IC from the wrong MMPDS table (mmpsd-allowables): MMPDS
  A-basis and B-basis tables cover static mechanical properties; plane
  strain fracture toughness values are reported for specific product
  forms, thickness ranges, and orientations and are not in every
  allowable table. Match the test condition before using a number.
- Using K_IC where crack growth rate is the gate (crack-growth): K_IC
  gates the final unstable extension; the life between inspections is
  governed by da/dN versus delta K (Paris-type growth). Do not size
  inspection intervals from K_IC alone.
- Confusing critical crack size with residual strength
  (residual-strength): a_c from K = K_IC is the crack size at final
  fracture under the applied stress; residual-strength analysis gives
  the remaining load capability of the cracked part versus crack size,
  and K_IC is the property that sets that curve at the instability
  point. They answer different questions about the same cracked part.
- Reaching for fracture toughness when the task is material selection
  on strength or stiffness (material-selection): material-selection
  screens on density-normalized strength and modulus; fracture
  toughness is a separate screening property with its own test
  validity conditions, and toughness and strength often trade against
  each other.
- Mixing units: K in MPa sqrt(m) requires sigma in MPa and a in
  meters. A crack size in millimeters with stress in MPa gives K in
  MPa sqrt(mm), which is smaller by sqrt(1000) than the MPa sqrt(m)
  value; convert a to meters first.
- Dropping the geometry factor: an edge crack (Y = 1.12) runs 12
  percent higher in K than an embedded crack (Y = 1.0) at the same
  size; K scales linearly with Y while the critical crack scales with
  1 / Y^2.
- Using K_IC outside the plane-strain regime: below the validity
  dimension 2.5 * (K_IC / sigma_ys) ** 2 the measured toughness rises
  as the section thins; the published K_IC only applies in the
  plane-strain regime.
- Ignoring orientation: wrought aerospace alloys are anisotropic, and
  K_IC in the TL orientation can be well below the LT value; use the
  orientation that matches the crack path in the part.

## Behavior contract (gate 3)

The stress intensity, failure criterion, critical crack size, and
plane-strain validity logic is exercised by the gate 3 contract test:
scripts/test_fracture_toughness.py against
scripts/fracture_toughness_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_toughness.py

## Compliance

- Standards referenced, not reproduced: ASTM E399 is named as the test
  method context for the plane-strain validity rule and MMPDS as the
  source of material allowables. Both are proprietary standards; this
  leaf carries only the summary-level formula and validity rule, which
  are common materials-engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
