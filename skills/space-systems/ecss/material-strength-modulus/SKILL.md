---
name: material-strength-modulus
description: "Use when determine material strength and elastic modulus property requirements for load-bearing structural elements under ECSS-E-ST-32C clauses 4.2.1–4.2.2: collect yield (Fty, Fcy) and ultimate (Ftu) strength allowables at A-basis (fracture-critical) or B-basis (non-fracture-critical), verify elastic modulus consistency G = E/(2(1+ν)) for isotropic materials, apply environmental knockdown factors to base allowables, compute multiaxial yield margin via von Mises or Tresca criterion for multi-directional principal stress states, and confirm each material property is traceable to an accepted data source. Trigger: ecss, e-st-32-structures-scope, material-strength, elastic-modulus, yield-criterion, von-mises, tresca, strength-allowables."
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
  tags: [ecss, e-st-32-structures-scope, material-strength, elastic-modulus, yield-criterion, von-mises, tresca, strength-allowables]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Material Strength and Elastic Modulus Properties (space-systems/ecss/material-strength-modulus)

Use when the task is establishing material strength and elastic modulus property
requirements for load-bearing structural elements under ECSS-E-ST-32C clauses
4.2.1–4.2.2 — gathering statistically-based allowables, verifying isotropic
modulus consistency, and computing yield margins for multi-directional stress
states.

## Domain quick reference

- Clause 4.2.1 requires that every load-bearing material in the structure have
  documented strength allowables covering tensile yield (Fty), compressive yield
  (Fcy), ultimate tensile (Ftu), shear (Fsu), and bearing (Fbru, Fbry) as
  applicable to the loading mode. Allowables must carry a statistical basis:
  A-basis (99th-percentile strength with 95 % confidence) for fracture-critical
  and single-load-path parts; B-basis (90th-percentile, 95 % confidence) as the
  minimum for redundant load paths.
- Clause 4.2.2 requires that the elastic property set — Young's modulus E, shear
  modulus G, and Poisson's ratio ν — be internally consistent with the material
  model used in analysis. For isotropic metals the relation G = E / (2(1+ν))
  must hold within the accepted tolerance; departure indicates either a data
  entry error or an inappropriate isotropic assumption (e.g. a laminate or
  honeycomb core being treated as isotropic).
- Multiaxial yield criteria apply whenever the structural analysis produces
  principal stresses in more than one direction. Von Mises (distortion-energy) is
  the standard criterion for ductile metallic alloys and is less conservative
  than Tresca (maximum-shear-stress). Tresca is used as a conservative
  cross-check or when a simpler bounding approach is preferred.
- Environmental knockdown factors account for the reduction in room-temperature
  allowables due to elevated or cryogenic temperature, absorbed moisture,
  radiation dose, or fatigue pre-damage. Every allowable used in margin-of-safety
  calculations must have any applicable knockdown applied before comparison.

## Workflow

1. Inventory every load-bearing material in the structural model. For each
   material, identify its load-path role (primary, secondary, tertiary) and
   whether any element is fracture-critical or single-load-path — that
   designation controls the required allowable basis.
2. Collect published strength allowables for each material from an accepted data
   source: a mechanical test campaign on the production lot, an approved
   material handbook entry, a qualification database, or a supplier datasheet
   with traceability. Reject any source that cannot be categorized into one of
   these recognized types before it enters the analysis.
3. Verify the allowable basis: confirm A-basis is used for every fracture-critical
   or single-load-path element; confirm at minimum B-basis for all others. Flag
   any part whose allowable basis is not on record as an open finding.
4. Collect elastic modulus data: E, G, and ν for each material. For isotropic
   materials compute the expected shear modulus G_expected = E / (2(1+ν)) and
   compare it against the supplied G. A relative discrepancy exceeding the project
   tolerance (typically 2 %) indicates an inconsistency that must be resolved
   before the FEM is used for sizing.
5. Apply environmental knockdown factors: identify the design operating temperature
   range and any other environmental conditions (moisture uptake, radiation dose)
   and multiply the base allowable by the appropriate knockdown factors to obtain
   the design allowable for each condition.
6. For each critical load combination, extract the three principal stresses from
   the structural analysis and compute the von Mises equivalent stress:
   σ_vm = √(0.5 · ((σ₁−σ₂)² + (σ₂−σ₃)² + (σ₃−σ₁)²)).
   Compute margin of safety MS = Fty / σ_vm − 1. Where a conservative bound is
   needed, substitute the Tresca equivalent σ_T = max(|σ₁−σ₂|, |σ₂−σ₃|, |σ₃−σ₁|).
7. Aggregate all findings: missing basis documentation, modulus inconsistencies,
   unrecognized data sources, negative margins, and missing knockdown factors.
   A material entry is compliant only when all findings for that entry are
   resolved.

## Pitfalls

- Using mean or typical-value strength data instead of statistically-based
  allowables — mean data provides no guarantee of exceedance probability and
  will over-predict the actual lower-tail strength of a production batch.
- Applying room-temperature allowables directly to a high-temperature or
  cryogenic design condition without a knockdown factor — the temperature
  dependence of yield strength is significant for most aerospace alloys and can
  easily exceed 15 % at elevated service temperatures.
- Treating compressive yield strength as equal to tensile yield strength for all
  materials — several aerospace alloys (notably some aluminium alloys and cold-
  worked titanium) exhibit a measurable compressive-to-tensile yield ratio
  different from unity; using Fty where Fcy applies can be unconservative in
  column or panel buckling calculations.
- Skipping the modulus-consistency check by assuming that G from a data sheet
  automatically satisfies G = E/(2(1+ν)) — data sheet values are sometimes
  rounded or measured at a different condition and the apparent discrepancy
  carries over into the FEM stiffness matrix if not corrected.
- Applying von Mises to a brittle material — the distortion-energy criterion is
  valid for ductile metals; brittle materials require a fracture-mechanics or
  modified-Mohr criterion and will appear artificially safe under von Mises.
- Accepting an allowable from an unrecognized data source without review — an
  allowable without traceable provenance cannot be verified and should be treated
  as an open finding, not a pass.

## Behavior contract (gate 3)

The strength allowable basis, modulus consistency, multiaxial yield margin, and
knockdown-factor logic is exercised by the gate 3 contract test:
scripts/test_material_strength_modulus.py against
scripts/material_strength_modulus_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_material_strength_modulus.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
