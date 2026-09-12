---
name: drd-dimstab-analysis
description: "Use when prepare a dimensional stability analysis (DSA) report for a
  spacecraft structure per ECSS-E-ST-32C Annex C: verify the report contains every
  mandatory DRD section, validate material CTE and hygrothermal coefficients, compute
  linear thermal and hygrothermal displacements for each structural member, combine
  contributions to derive total dimensional change, compute stability margins against
  requirements, assess CTE mismatch between dissimilar joined materials, and confirm
  every structural member's dimensional change is within the applicable stability
  requirement. Trigger: ecss, e-st-32-structures-scope, dimensional-stability, cte,
  hygrothermal, thermal-distortion, displacement, stability-margin, drd."
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
  tags: [ecss, e-st-32-structures-scope, dimensional-stability, cte, hygrothermal, thermal-distortion, stability-margin, drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Dimensional Stability Analysis DRD (space-systems/ecss/drd-dimstab-analysis)

Use when the task is to prepare or review the dimensional stability analysis (DSA)
report deliverable required by ECSS-E-ST-32C Annex C — verifying that the document
covers every mandatory content element, that material data are well-formed, and that
computed dimensional changes satisfy the applicable stability requirements.

## Domain quick reference

- ECSS-E-ST-32C Annex C defines the content requirements for the dimensional
  stability analysis report (DRD). The report must demonstrate that every
  structural item whose dimensional stability is a mission driver is assessed
  against a traceable stability requirement and that the margin is explicitly
  stated.
- Two primary displacement drivers are addressed: thermal (governed by the
  coefficient of thermal expansion, CTE, α, in 1/K) and hygrothermal (governed
  by the coefficient of moisture expansion, β, in 1/% moisture content change).
  Mechanical contributors (preload relaxation, creep) are identified and
  enumerated but may be handled by reference to separate analyses.
- Linear displacement is computed per member as δ = α × L × ΔT (thermal) or
  δ = β × L × ΔM (hygrothermal). Contributions are summed algebraically to
  obtain total dimensional change for each structural member.
- Stability margin is defined as (allowable / |actual|) − 1; a margin ≥ 0
  indicates compliance; a margin < 0 is an exceedance and must be dispositioned.
- CTE mismatch between dissimilar materials joined at an interface is a common
  source of thermally-induced distortion and interface stress; the report must
  flag any pair where |α₁ − α₂| exceeds the threshold set by the joint design
  requirement.
- Mandatory DRD sections (ECSS-E-ST-32C Annex C): scope, applicable_documents,
  structure_description, material_properties, thermal_environments,
  moisture_environments, analysis_method, displacement_results,
  stability_requirements, margin_summary, conclusions.

## Workflow

1. Confirm the DRD report structure: check that all eleven mandatory sections are
   present. Flag every missing section before proceeding — an incomplete DRD is
   a non-conformance independent of the numerical results.
2. Validate every material entry in the material_properties section: each record
   must supply a name, a CTE (α, 1/K), a coefficient of moisture expansion (β,
   1/%), and a Young's modulus (E, GPa). Reject non-numeric or non-finite values
   with an explicit error; do not silently default.
3. For each structural member, compute the thermal displacement:
   δ_thermal = α × L × ΔT, using the worst-case ΔT from thermal_environments.
4. For each structural member, compute the hygrothermal displacement:
   δ_hygro = β × L × ΔM, using the worst-case ΔM from moisture_environments.
5. Sum the thermal and hygrothermal displacements algebraically to obtain the
   total displacement δ_total for the member. Identify and enumerate any
   mechanical contributors (e.g. creep, preload relaxation) separately.
6. For each structural member with an applicable stability requirement, compute
   the stability margin: margin = (allowable / |δ_total|) − 1. Record PASS where
   margin ≥ 0 and FAIL where margin < 0. A member with no stability requirement
   on record must be flagged as uncategorized — treat a missing requirement as a
   finding, not a pass.
7. At every material interface between dissimilar materials, assess CTE mismatch:
   compute |α₁ − α₂| and compare against the joint design threshold. Flag any
   pair that exceeds the threshold.
8. Aggregate findings into the margin_summary section: list every exceedance,
   every member with a missing stability requirement, and every interface with an
   excessive CTE mismatch. The DSA is compliant only when all three lists are
   empty.

## Pitfalls

- Omitting the hygrothermal contribution for composite structural members —
  composites can exhibit β values of the same order of magnitude as α for
  polymeric matrix systems, and ignoring moisture effects under a wet
  pre-conditioning case can significantly understate the total dimensional change.
- Treating a missing stability requirement as compliance — an untraced requirement
  is a gap in the design authority chain, not evidence of margin; flag it
  explicitly.
- Applying direct algebraic sum when thermal and hygrothermal contributions act
  in opposite directions and using the conservative worst-case combination: for
  a stability budget, always evaluate both the maximum positive and maximum
  negative combined displacement.
- Ignoring CTE mismatch at bonded or bolted interfaces — even when each material
  individually meets its stability requirement, a high mismatch generates
  interface loads that can degrade pointing stability and joint integrity at the
  same time.
- Using midpoint (average) temperature or moisture environments rather than the
  worst-case extremes specified in the thermal and moisture boundary conditions
  section — the DSA is a worst-case envelope analysis.

## Behavior contract (gate 3)

The DRD-section validation, material-entry validation, thermal and hygrothermal
displacement computation, stability margin computation, CTE mismatch assessment,
and stability requirement check logic is exercised by the gate 3 contract test:
scripts/test_drd_dimstab_analysis.py against scripts/drd_dimstab_analysis_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drd_dimstab_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
