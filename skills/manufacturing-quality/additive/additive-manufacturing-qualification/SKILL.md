---
name: additive-manufacturing-qualification
description: "Define and validate the additive manufacturing process parameter set for aerospace parts: record the layer height, laser power, scan speed, and hatch spacing, compute the volumetric energy density from those four build parameters, size the witness coupon sample plan for material property verification, and check the additive manufacturing qualification record for first article completeness. Use when qualifying a powder bed fusion or directed energy deposition build, when a build parameter change needs energy density re-verification, or when preparing the AM qualification record and witness coupon plan. Trigger: additive manufacturing, volumetric energy density, laser power, scan speed, hatch spacing, layer height, witness coupon, powder bed fusion, AM build parameter."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: additive
  tags: [additive, manufacturing, qualification, laser, power, scan, speed, hatch, spacing, layer, height, energy, density, volumetric, witness, coupon, powder, bed, fusion, am, build, parameter, material, property, verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# Additive Manufacturing Qualification (manufacturing-quality/additive/additive-manufacturing-qualification)

Use when the task is qualifying an additive manufacturing (AM) process
for aerospace production: powder bed fusion or directed energy
deposition parameter set definition, volumetric energy density
verification, witness coupon sample planning, material property
verification, and first article checks for AM parts.

## Domain quick reference

- AM parameter set: layer height, laser power, scan speed, hatch
  spacing. The four build parameters pin the energy input to the melt
  pool for a powder bed fusion or directed energy deposition build.
- Volumetric energy density: VED = laser power / (scan speed x hatch
  spacing x layer height), in J/mm^3 with W, mm/s, mm, mm. A build
  parameter change without VED re-verification is a qualification gap.
- Witness coupons: test coupons built with the same parameter set and
  machine as the production parts. The sample plan maps material
  property tests (tensile, fatigue, hardness) to coupon counts, with
  one spare coupon per test type for re-test.
- Material property verification: coupon test results recorded against
  the parameter set; a missing test or an out-of-specification result
  blocks qualification.
- First article checks for AM parts: build file traceability, machine
  id, parameter set match, coupon results, dimensional report, and any
  required non-destructive examination.
- AS9100 link: AM process qualification sits under production control
  and quality management; AS9100 is referenced, not reproduced.

## Workflow

1. Define the AM parameter set: layer height, laser power, scan speed,
   hatch spacing. build_parameter_set() records the four parameters and
   computes the volumetric energy density.
2. Size the witness coupon sample plan: witness_coupon_count() returns
   the coupon count from the material property sample plan (total
   samples plus one spare coupon per test type).
3. Verify material properties: record coupon test results against the
   parameter set.
4. Run the first article checks for the AM part: build file, machine,
   parameter set match, coupon results, dimensional report, and NDT.
5. Assemble the qualification record and check completeness:
   build_qualification_record() and validate_record() flag any missing
   field (parameter_set, witness_coupon_plan,
   material_property_verification, first_article_inspection).
6. Validate inputs first: non-numeric or non-positive build parameters,
   malformed sample plans, and malformed records raise ValueError
   instead of returning a silent result.

## Pitfalls

- Confusion with special-process-qualification: the general special
  process qualification record (PQR) governs welding, heat treatment,
  and NDT processes with a validity interval; this leaf qualifies AM
  parameter sets with energy density and coupon evidence. An AM build
  is qualified by parameters and coupons, not by a PQR-style interval.
- Confusion with as9102/first-article-inspection: the AS9102 FAI forms
  remain the general first article inspection program. The AM first
  article checks here are build-specific (build file, machine,
  parameter set match, coupon results) and feed the FAI; they do not
  replace it.
- Unit mixing: VED in J/mm^3 needs W, mm/s, mm, mm. Converting the
  scan speed to m/s or the hatch spacing to cm changes the result by
  orders of magnitude.
- Missing hatch spacing: energy density computed from three of the four
  parameters is undefined, not approximate.
- Coupon count vs specimen count: the sample plan maps tests to
  coupons; the count includes the spare coupon per test type so a
  re-test does not require a new build.
- Energy density outside the qualified envelope: a parameter change can
  keep parts dimensionally acceptable while pushing VED outside the
  qualified window; re-verify before production runs.

## Behavior contract (gate 3)

The qualification logic is exercised by the gate 3 contract test:
scripts/test_additive_manufacturing_qualification.py against
scripts/additive_manufacturing_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_additive_manufacturing_qualification.py

## Compliance

- Standards referenced, not reproduced: AS9100 frames AM process
  qualification within production control; summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
