---
name: local-yielding-and-buckling-functionality
description: "Use when determine and verify local yielding control and buckling resistance for metallic structural items under ECSS-E-ST-32 clauses 4.3.3 and 4.3.4: assess whether local plastic zones at stress raisers remain within permissible limits at limit load using the von Mises criterion, compute elastic plate buckling critical stress with appropriate buckling coefficients, evaluate crippling of thin-walled sections, apply combined-load buckling interaction equations, and derive margins of safety for each check. Apply to panels, stiffeners, columns, or any sub-item where local yielding control and stability must be demonstrated before design acceptance. Trigger: ecss, e-st-32-structures-scope, buckling-analysis, plate-buckling, crippling-analysis, local-yielding, margin-of-safety, combined-loads."
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
  tags: [ecss, e-st-32-structures-scope, buckling-analysis, plate-buckling, crippling-analysis, local-yielding, margin-of-safety, combined-loads]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Local Yielding Control and Buckling Resistance (space-systems/ecss/local-yielding-and-buckling-functionality)

Use when the task is verifying local yielding control and buckling resistance
at item and sub-item level per ECSS-E-ST-32 clauses 4.3.3 and 4.3.4 —
computing von Mises equivalent stress against yield strength at limit load,
determining plate buckling critical stresses, checking crippling of
thin-walled sections, and evaluating combined-load interaction margins.

## Domain quick reference

- **Clause 4.3.3 — Local yielding control**: Localised plastic deformation at
  stress raisers (cutouts, fastener holes, load-introduction regions) is
  permissible at limit load provided it does not propagate to threaten the
  overall structural integrity. The von Mises equivalent stress is compared
  to the 0.2 % proof strength (or yield strength) of the material; a
  yield ratio ≤ 1.0 means the local zone is permissible. A margin of safety
  of zero or better at limit load satisfies the local-yielding requirement.
- **Clause 4.3.4 — Buckling resistance**: Structural plates, panels, shells,
  and columns must not experience instability (buckling) at or below the
  design limit load unless the post-buckling carrying capacity is explicitly
  substantiated. The governing check is the margin of safety between the
  elastic buckling critical stress and the applied compressive or shear
  stress. For combined loading, an interaction equation governs. Thin-walled
  sections (stringers, frames, clip angles) additionally require a crippling
  check using empirical knock-down methods from structural handbooks.
- **Buckling coefficient k**: Depends on plate aspect ratio (a/b) and
  boundary conditions. A simply-supported plate under uniform edge compression
  has k = 4.0 for a square or long plate. Clamped edges increase k; free
  edges decrease it. The correct k must be selected before the critical
  stress formula is applied.
- **Margin of safety**: MS = (critical stress / applied stress) − 1. An MS ≥ 0
  satisfies the requirement at the relevant load level.

## Workflow

1. **Identify structural items under review**: List each plate, stiffener,
   column, or cross-section that must be checked for local yielding and
   buckling. Confirm the material properties (E, ν, yield strength, ultimate
   strength) and applied stress state (σ_x, σ_y, τ_xy) at the governing
   load case.
2. **Local yielding check (clause 4.3.3)**: Compute the von Mises equivalent
   stress from the 2-D stress state at the point of maximum stress
   concentration. Compare to the material yield strength. Derive the yield
   ratio and margin of safety. Flag any item where the yield ratio exceeds
   1.0 as a local-yielding exceedance and record it for disposition.
3. **Select buckling model**: For each plate, determine the boundary conditions
   and aspect ratio; select the appropriate buckling coefficient k. For
   columns, select the Euler or Johnson-Euler model. For thin-walled sections,
   identify each sub-element width b and thickness t for crippling.
4. **Compute plate buckling critical stress (clause 4.3.4)**: Apply the Euler
   plate formula: σ_cr = k π² E / [12(1 − ν²)] × (t/b)². Compare σ_cr to
   the applied compressive stress. Derive the buckling margin of safety.
5. **Crippling check**: For each thin-walled sub-element, apply an empirical
   crippling formula to derive F_cc. Compare to the applied compressive stress.
   Derive the crippling margin of safety.
6. **Combined-load interaction (if applicable)**: Where axial compression and
   shear act simultaneously, evaluate the interaction index
   R = (σ / σ_cr_axial)² + (τ / τ_cr)². An R ≤ 1.0 is stable.
7. **Aggregate results**: Collect all margins of safety across local-yielding
   and buckling checks. The governing margin is the minimum. Flag any item
   with MS < 0 for design change or substantiation.

## Pitfalls

- Using ultimate strength instead of yield strength in the local-yielding
  check — clause 4.3.3 is a limit-load check against yield; ultimate strength
  governs the separate static-strength margin at ultimate load.
- Applying the simply-supported buckling coefficient k = 4 regardless of actual
  boundary conditions — clamped edges (k ≈ 6.97) or free edges (k ≈ 0.43)
  change the critical stress substantially.
- Omitting the crippling check for thin-walled open sections — elastic buckling
  of the full panel may give a comfortable margin while individual sub-elements
  are crippling-critical at a lower stress.
- Treating a combined-load interaction index of exactly 1.0 as a failure —
  R = 1.0 corresponds to MS = 0 (exactly at the boundary), which satisfies the
  requirement at that load level.
- Neglecting to apply a plasticity correction factor when the applied stress
  is in the inelastic range — the Euler formula is elastic; a secant or
  tangent modulus correction is needed when σ approaches the yield stress.

## Behavior contract (gate 3)

The von Mises stress, local-yielding check, plate buckling critical stress,
buckling margin, combined-load interaction, crippling stress, and aggregation
logic are exercised by the gate 3 contract test:
scripts/test_local_yielding_and_buckling_functionality.py against
scripts/local_yielding_and_buckling_functionality_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_local_yielding_and_buckling_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the standard + clause as
  the anchor only; paraphrase all procedural content.
- compliance: STANDARDS-REF, gated: false.
