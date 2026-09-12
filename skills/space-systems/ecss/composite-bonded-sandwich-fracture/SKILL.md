---
name: composite-bonded-sandwich-fracture
description: "Use when assess composite structures, bonded joints, and sandwich panels for delamination growth, defect severity, and damage threat compliance under ECSS-E-ST-32C clause 8.4: categorize each detected defect by type (delamination, disbond, core damage, matrix crack, impact damage) and laminate location, determine whether the mixed-mode delamination driving force remains below the critical strain energy release rate envelope, evaluate residual strength against design ultimate load using fracture toughness, and verify the damage-threat matrix covers all required manufacturing and in-service impact sources. Trigger: ecss, e-st-32c, composite-structures, bonded-joints, sandwich-panels, delamination-growth, fracture-compliance, damage-threat-assessment."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-32-structures-scope, composite-structures, bonded-joints, sandwich-panels, delamination-growth, fracture-compliance, damage-threat-assessment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Composite/Bonded/Sandwich Fracture (space-systems/ecss/composite-bonded-sandwich-fracture)

Use when the task is the defect assessment, damage threat evaluation, and
fracture compliance verification of composite structures, bonded joints, and
sandwich panels per ECSS-E-ST-32C clause 8.4 — categorizing detected flaws,
checking delamination growth driving force against critical allowables,
computing residual strength margins, and confirming the damage-threat matrix
is complete.

## Domain quick reference

- Clause 8.4 addresses three structural family types jointly: laminated
  composite panels, adhesively bonded joints, and sandwich panels with face
  sheets over a lightweight core. All three share the same fracture compliance
  framework but differ in their dominant failure modes and the relevant
  material fracture properties.
- Defects are categorized into three structural groups based on their origin
  and location: interlaminar (delamination, matrix crack — residing between
  plies or in the resin-rich zone); sandwich-interface (disbond or core damage
  at the facesheet-core boundary); and impact-induced (impact damage
  penetrating one or more plies and potentially the core). Each defect is
  assigned to exactly one group before the flaw-size check is performed.
- Delamination growth is governed by the mixed-mode strain energy release
  rate (SERR). The applied driving force D combines Mode I (opening) and
  Mode II (shear) components via a power-law interaction criterion:
  D = (G_I / G_Ic)^m + (G_II / G_IIc)^n. Growth initiates when D reaches 1.0;
  the growth margin is defined as 1/D - 1 and must be positive for all
  design load cases.
- Residual strength is assessed at design ultimate load using linear elastic
  fracture mechanics. For the critical flaw size retained after the
  flaw-size allowable check, the stress intensity factor
  K_I = F * σ * sqrt(π * a) must not exceed K_Ic, where F is the geometry
  correction factor, σ the applied far-field stress, and a the crack
  half-length. The residual strength margin is K_Ic / K_I - 1.
- The damage-threat matrix must enumerate every plausible source of
  in-service and manufacturing damage (tool drop, handling impact, debris
  impact, manufacturing void, porosity). A fracture compliance declaration
  is blocked until all required sources appear in the matrix.

## Workflow

1. Inventory all detected defects and categorize each one by type
   (delamination, disbond, core_damage, matrix_crack, impact_damage) and
   location within the laminate or sandwich stack (inner_facesheet,
   outer_facesheet, core, facesheet_core_interface, mid_laminate). Reject
   any defect with an unrecognized type or location before it enters the
   assessment — do not assume a default category.
2. For each defect, compare the measured flaw area against the panel's
   allowable flaw area. Flag any defect that exceeds the allowable as a
   FAIL finding. Raise a WARN advisory when the margin between measured
   and allowable falls below 10 %, since manufacturing scatter may consume
   that margin in service.
3. For each defect paired with each governing load case, compute the
   mixed-mode driving force D using the Mode I and Mode II applied SERRs
   and the material's critical SERRs (G_Ic, G_IIc). A driving force
   D >= 1.0 indicates delamination growth onset and is a FAIL finding.
   A growth margin below 15 % triggers a WARN advisory.
4. For each governing load case, compute the residual strength margin at
   the panel's design-allowable crack half-length using the material
   fracture toughness K_Ic and the applied far-field stress. A negative
   margin is a FAIL finding.
5. Review the damage-threat matrix and confirm that all required threat
   source categories are present (tool_drop, handling_impact,
   debris_impact, manufacturing_void at minimum). Flag any missing category
   as a FAIL finding — fracture compliance cannot be declared until the
   matrix is complete.
6. Collect all FAIL and WARN findings per panel. The panel is fracture
   compliant only when the FAIL list is empty. WARN findings are recorded
   for the design review but do not block compliance.

## Pitfalls

- Skipping the defect-location step and applying a single allowable flaw
  area to all defect types regardless of their structural zone — the
  allowable for a core-zone disbond differs from that for a mid-laminate
  delamination, and mixing them produces unconservative results.
- Treating Mode I and Mode II driving forces as independent checks rather
  than a combined interaction criterion — a defect with moderate G_I and
  moderate G_II can exceed the interaction envelope even when neither
  component alone reaches its respective critical value.
- Reading a positive residual strength margin at the measured flaw size as
  evidence of compliance — the check must be made at the allowable flaw
  size (the largest flaw that may exist after inspection), not the measured
  one, because the measured flaw may be smaller than the inspection
  resolution limit.
- Declaring the damage-threat matrix complete because every in-service
  source has been listed, while omitting manufacturing sources (porosity,
  bond-line voids) — clause 8.4 requires both populations to be covered
  before compliance is asserted.

## Behavior contract (gate 3)

The defect-categorization, flaw-size, delamination-growth driving force,
residual-strength, and damage-threat coverage logic is exercised by the
gate 3 contract test:
scripts/test_composite_bonded_sandwich_fracture.py against
scripts/composite_bonded_sandwich_fracture_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_composite_bonded_sandwich_fracture.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
