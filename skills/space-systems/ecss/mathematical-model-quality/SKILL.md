---
name: mathematical-model-quality
description: "Use when validate the adequacy of a structural mathematical model (SMM) under ECSS-E-ST-32C clause 4.6.2.2: categorize the model by analysis type (linear-static, normal-modes, nonlinear-static, transient, frequency-response, or buckling), verify mesh-quality parameters against allowable aspect-ratio and angle bounds, confirm that free-free rigid-body modes lie within frequency tolerance of zero, check that SMM total mass matches the reference mass within budget, correlate SMM static displacements and modal frequencies against test measurements within prescribed tolerances, and aggregate all findings into an adequacy verdict. Trigger: ecss, e-st-32-structures-scope, structural-mathematical-model, smm, fem, finite-element, mesh-quality, rigid-body-modes, mass-properties, modal-correlation."
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
  tags: [ecss, e-st-32-structures-scope, structural-mathematical-model, smm, fem, finite-element, mesh-quality, rigid-body-modes, mass-properties, modal-correlation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Structural Mathematical Model Quality (space-systems/ecss/mathematical-model-quality)

Use when the task is to validate the adequacy of a structural mathematical
model (SMM) per ECSS-E-ST-32C clause 4.6.2.2 — demonstrating that a
finite-element model (FEM) meets quality requirements before it is used
for structural verification predictions.

## Domain quick reference

- Clause 4.6.2.2 requires the SMM to be formally assessed for adequacy
  before its analysis results are accepted as evidence of structural
  compliance. Adequacy covers four dimensions: model category, mesh
  geometry quality, dynamic model consistency (rigid-body modes), and
  correlation with test measurements (mass, static response, modal
  frequencies).
- The SMM is first categorized by analysis type — linear-static,
  normal-modes, nonlinear-static, transient, frequency-response, or
  buckling. Only models in one of these recognized categories are
  eligible for the adequacy assessment; an unrecognized type is rejected
  before any check proceeds.
- Mesh quality is governed by element geometry: the aspect ratio (longest
  to shortest side) must stay below the project-defined limit (default
  10.0), and element interior angles must remain within allowable bounds
  (default 45°–135°). Exceeding these bounds indicates a distorted mesh
  that can introduce numerical error in the solution.
- A free-free modal analysis on an unconstrained structure must return
  exactly six near-zero-frequency modes corresponding to the six rigid-body
  degrees of freedom. Non-zero rigid-body mode frequencies indicate
  spurious stiffness in the model (improper boundary conditions or
  constraint errors) and disqualify the SMM until resolved.
- Mass correlation compares the SMM total mass against a reference value
  (design mass budget or measured mass) within a tolerance fraction
  (default 2 %). A mass discrepancy beyond tolerance means the model does
  not represent the real structure correctly.
- Static and modal correlation compare SMM-predicted displacements and
  natural frequencies against test-measured values within separate
  tolerances (default 10 % for static, 5 % for modal). Both correlation
  checks must pass for the SMM to be considered adequate for predictions.

## Workflow

1. Categorize the SMM by its intended analysis type. Reject and flag
   any model whose type is not in the recognized set before proceeding.
   Record the accepted category in the adequacy log.
2. Evaluate mesh element quality: compute the worst-case aspect ratio
   and the extreme element angles across the mesh. Compare each against
   the project-defined limits (defaulting to the values in the domain
   quick reference). Flag any exceedance as a mesh-quality finding.
3. Run or retrieve the results of a free-free modal analysis on the
   unconstrained model. Identify the six lowest-frequency modes. Verify
   each has a frequency within the zero-frequency tolerance (default
   1 × 10⁻³ Hz). A mode above the tolerance is a rigid-body mode
   integrity finding; fewer than six modes in the result is a model
   incompleteness finding.
4. Compare the SMM total mass against the reference mass (measured or
   budgeted). Compute the relative difference. Flag a mass-property
   finding if the difference exceeds the project tolerance. An
   unset (zero or negative) reference mass is itself a finding.
5. For each available static load case with test data, compare the SMM
   predicted displacement at the correlation point against the measured
   value. Compute the relative error. Flag pairs whose error exceeds the
   static correlation tolerance.
6. For each available measured natural frequency, compare the SMM
   predicted modal frequency for the corresponding mode. Compute the
   relative error. Flag pairs whose error exceeds the modal frequency
   correlation tolerance.
7. Aggregate all check results from steps 1–6 into an overall adequacy
   verdict. The SMM is adequate only when every check returns no
   findings. Document findings with the check type, the computed value,
   the limit, and the exceedance margin.

## Pitfalls

- Accepting a model whose type has not been explicitly categorized —
  an uncategorized model bypasses the structural verification scope
  check and may be used for an analysis type it was never validated for.
- Skipping the rigid-body mode check and treating any free-free analysis
  as valid — a non-zero rigid-body mode frequency reveals a constraint
  or stiffness error that invalidates all subsequent predictions from
  that model.
- Using the mass correlation pass as a substitute for static or modal
  correlation — mass accuracy confirms material and density assignment
  but does not validate the model's stiffness or boundary condition
  representation, which static and modal checks exercise separately.
- Treating an unset mass budget as a pass — when no reference mass is
  recorded, the check cannot be performed and the gap is itself a
  finding, not a confirmation of correctness.
- Applying the same tolerance fraction to both static and modal
  correlation — static response and modal frequency exhibit different
  sensitivity to model errors; the standard specifies separate limits
  and they must be applied independently.
- Collapsing multiple rigid-body mode violations into a single finding —
  each violating mode is a separate indicator of a different model defect
  and must be logged individually to guide diagnosis.

## Behavior contract (gate 3)

The SMM-type categorization, mesh-quality, rigid-body-mode, mass-property,
static-correlation, and modal-correlation logic is exercised by the gate 3
contract test: scripts/test_mathematical_model_quality.py against
scripts/mathematical_model_quality_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_mathematical_model_quality.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor: ECSS-E-ST-32C clause 4.6.2.2 (structural mathematical model
  adequacy demonstration).
