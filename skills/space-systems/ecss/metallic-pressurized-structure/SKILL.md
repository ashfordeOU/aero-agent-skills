---
name: metallic-pressurized-structure
description: "Use when determine combined Design Ultimate Loads for a metallic pressurized structure or manned-module pressure boundary per ECSS-E-ST-32C clause 4.4.2: derive pressure-induced and mechanical load contributions at Maximum Expected Operating Pressure (MEOP), compute thin-wall hoop and axial stresses, evaluate each margin of safety against metallic allowables, verify proof and burst pressure thresholds are met, and assess any pressure bulkhead marked Safety-critical (S) for a fail-safe feature or redundant load path. Trigger: ecss, e-st-32-structures-scope, metallic-pressurized-structure, manned-module, combined-dul, pressure-loads, margin-of-safety, pressure-bulkhead, meop, thin-wall-stress."
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
  tags: [ecss, e-st-32-structures-scope, metallic-pressurized-structure, manned-module, combined-dul, pressure-loads, margin-of-safety, pressure-bulkhead, meop, thin-wall-stress]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Metallic Pressurized Structure (space-systems/ecss/metallic-pressurized-structure)

Use when the task is the structural assessment of a metallic pressurized
structure (MPS) or manned-module pressure boundary under ECSS-E-ST-32C
clause 4.4.2 — combining internal pressure loads with mechanical loads
to form the Design Ultimate Load (DUL), computing thin-wall stresses,
and verifying margins of safety together with pressure bulkhead
fail-safe compliance.

## Domain quick reference

- Clause 4.4.2 covers metallic structures that carry both pressure and
  mechanical loads simultaneously. The governing load case is the combined
  Design Ultimate Load (DUL), formed by multiplying each Design Limit Load
  (DLL) component by the applicable ultimate factor before combining them.
  For manned modules the same combined-load approach applies with the same
  or higher safety factors set by the programme safety authority.
- Pressure loads are derived from the Maximum Expected Operating Pressure
  (MEOP): the Design Ultimate Pressure (DUP) equals MEOP multiplied by
  the pressure ultimate factor. Mechanical loads (axial, shear, bending)
  are factored separately and then superimposed with the pressure stress
  field in the critical cross-section.
- Thin-wall (membrane) theory is the standard first-pass method for
  cylindrical shells: hoop stress σ_h = p·r/t; pressure-induced axial
  stress σ_a_p = p·r/(2t); mechanical axial stress σ_a_m = N/(2π·r·t).
  The total axial stress at the critical section is the algebraic sum of
  both axial contributions.
- Margin of safety is computed as MoS = (allowable / applied) − 1.
  MoS ≥ 0 is required for every stress component at every critical
  cross-section. A negative margin at any location is a structural finding.
- Proof pressure and burst pressure requirements bound the pressure
  boundary integrity: proof pressure validates the absence of detrimental
  deformation; burst pressure sets the leak-before-burst or rupture
  threshold that the design must sustain without catastrophic failure.
- Pressure bulkheads carrying a Safety-critical (S) designation must
  incorporate either a fail-safe structural feature or a redundant load
  path so that no single structural failure propagates to loss of
  pressure containment.

## Workflow

1. Identify the load events that produce the maximum combined pressure
   and mechanical load on each critical cross-section of the structure.
   For each event, record the MEOP and the simultaneous mechanical loads
   (axial force, shear, bending moment).
2. Apply the ultimate factors to derive the Design Ultimate Pressure (DUP)
   and the Design Ultimate mechanical loads. The combined DUL represents
   the worst-case simultaneous factored loads the structure must sustain
   without failure.
3. Compute thin-wall hoop stress and total axial stress at each critical
   cross-section using DUP and the factored axial load. Where the
   geometry is not a thin-wall cylinder, replace the membrane formula
   with an appropriate analytical or FEA-derived stress field, and
   document the method.
4. Compare each computed stress against the metallic material allowable
   (ultimate tensile strength for static, fatigue allowable for cyclic
   events). Compute MoS for both hoop and axial directions; record any
   negative margin as a finding requiring design change or re-analysis.
5. Verify that the Design Proof Pressure (≥ 1.1 × MEOP for metallic
   pressurized hardware) and the Design Burst Pressure (≥ 2.0 × MEOP)
   are consistent with the design and test programme.
6. For each pressure bulkhead with a Safety-critical (S) designation,
   confirm that either a fail-safe structural feature (e.g. crack-arrest
   detail, doublers, bonded patch) or a redundant load path is in place.
   Flag any Safety-critical bulkhead with neither provision as a
   single-point failure item requiring design resolution.
7. Aggregate all stress-margin and bulkhead findings per structural
   assembly. The structure is considered compliant only when all margins
   are non-negative and all Safety-critical bulkheads meet the fail-safe
   or redundant load-path requirement.

## Pitfalls

- Omitting the simultaneous mechanical load when applying pressure to
  the cross-section — pressure alone does not close the load case; the
  axial and bending stresses from launch or operational mechanical events
  must be superimposed at DUL, not assessed separately.
- Using MEOP directly as the applied pressure in the stress calculation
  without multiplying by the pressure ultimate factor — this understates
  the applied stress and produces non-conservative margins.
- Reading MoS = 0 as "just compliant" and accepting it without margin
  recovery — for manned-module boundaries, programme safety requirements
  often impose a minimum positive margin beyond zero; check the
  applicable safety requirements before closing a zero-margin item.
- Treating a Safety-critical pressure bulkhead as compliant because it
  passes the stress margin check alone — the fail-safe or redundant
  load-path provision is a separate, mandatory structural design feature
  and must be verified independently of the stress margin.
- Applying thin-wall membrane formulas outside their valid range
  (r/t < 10 is generally outside the thin-wall regime) without
  correction — thick-wall or FEA methods are required for stocky
  cross-sections, and using the thin-wall formula there produces
  non-conservative hoop stress estimates.

## Behavior contract (gate 3)

The pressure load derivation, thin-wall stress computation,
margin-of-safety evaluation, and pressure-bulkhead fail-safe check
logic is exercised by the gate 3 contract test:
scripts/test_metallic_pressurized_structure.py against
scripts/metallic_pressurized_structure_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_metallic_pressurized_structure.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
