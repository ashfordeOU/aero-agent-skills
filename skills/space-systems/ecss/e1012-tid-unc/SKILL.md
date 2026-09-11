---
name: e1012-tid-unc
description: "Use when evaluate TID assessment uncertainties for space electronic
  components under ECSS-E-ST-10-12C §7.8: identify every uncertainty source (radiation
  environment model, shielding geometry, dose-rate and temperature effects during test,
  part-to-part variability), assign a multiplicative uncertainty factor to each source,
  compute the combined factor as the product of all individual factors, derive the design
  TID as the product of the mean environment TID and the combined uncertainty factor, and
  verify that the component's minimum lot tolerance divided by the design TID meets the
  required Radiation Design Margin. Trigger: ecss, e-st-10-12c, tid, total-ionizing-dose,
  uncertainty, radiation-design-margin, dose-rate, shielding, part-variability, rdm."
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
  tags: [ecss, e-st-10-12c, tid, total-ionizing-dose, uncertainty, radiation-design-margin, dose-rate, shielding, part-variability, rdm]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Environment — TID Assessment Uncertainty Accounting (space-systems/ecss/e1012-tid-unc)

Use when the task is to evaluate and account for the uncertainties present
in a Total Ionizing Dose (TID) assessment for space electronic components,
following the uncertainty-handling procedure anchored in ECSS-E-ST-10-12C §7.8.
The goal is to confirm that the Radiation Design Margin (RDM) applied to the
mean environment TID adequately covers all identified uncertainty sources, and
to flag components where the margin is insufficient.

## Domain quick reference

- TID uncertainties arise from four distinct sources, each treated as an
  independent multiplicative factor applied to the mean environment dose:
  (1) **environment model**: orbit propagation, solar-cycle phase, trapped-particle
  or solar-particle fluence model accuracy; (2) **shielding geometry**: ray-trace
  mesh resolution, material density tolerances, and shield construction detail;
  (3) **test conditions**: dose-rate mismatch between irradiation and mission
  operation, temperature during test, bias state during irradiation; and
  (4) **part-to-part variability**: process spread across a lot and between lots,
  wafer position effects, and foundry-to-foundry differences.
- The combined uncertainty factor is the product of all individual source factors.
  Each factor is dimensionless and must be ≥ 1.0; a factor below 1.0 indicates
  a modelling error rather than a conservative correction.
- The design TID for a component is the mean environment TID multiplied by the
  combined uncertainty factor.
- The Radiation Design Margin is defined as the component's minimum guaranteed
  lot tolerance divided by the design TID. ECSS-E-ST-10-12C §7.8 requires this
  ratio to be ≥ 2.0 for standard space-qualified components; a higher minimum
  may be specified for lot-sensitive or COTS parts.
- A component with an RDM below the required minimum is not acceptable unless
  additional shielding, re-screening, or a design change eliminates the shortfall.

## Workflow

1. List every electronic component that receives a non-zero TID from the mission
   radiation environment model.  For each component, record the mean environment
   TID and the minimum lot tolerance (from the acceptance test data sheet or
   radiation characterisation report).
2. For each component, enumerate the active uncertainty sources by category:
   environment model, shielding geometry, test conditions, part-to-part variability.
   Assign a multiplicative factor ≥ 1.0 to each source based on the analysis
   confidence level; a factor of 1.0 represents a source with no residual
   uncertainty (rare; document the justification).
3. Compute the combined uncertainty factor as the product of all individual
   source factors for that component.
4. Multiply the mean environment TID by the combined uncertainty factor to obtain
   the design TID.
5. Divide the minimum lot tolerance by the design TID to obtain the achieved RDM.
   Compare against the required minimum (default 2.0 unless the programme
   requirement specifies otherwise).
6. Record the outcome for each component:
   - PASS: achieved RDM ≥ required minimum.
   - FAIL: achieved RDM < required minimum — raise a non-conformance and assess
     corrective options (additional shielding, screening test, design change).
7. Aggregate results and confirm that every component in scope has been evaluated;
   a component with no uncertainty sources recorded is not automatically compliant
   — confirm the absence of uncertainty is justified before accepting it.

## Pitfalls

- Using a combined factor of 1.0 by default without reviewing each source category
  independently — at minimum the environment model and part variability always
  carry non-trivial uncertainty and should not be silently set to 1.0.
- Applying the RDM factor to the lot tolerance (numerator) instead of to the
  mean TID (denominator) — both formulations can appear in literature but the
  standard anchors the factor to the dose, not to the threshold.
- Accepting an RDM of exactly the minimum as comfortable margin — an RDM of
  exactly 2.0 leaves no margin for model refinement during later programme phases;
  flag it as borderline even when it technically passes.
- Mixing units or reference materials in the TID values — all dose figures must
  be in the same material (rad(Si) is conventional); comparing a threshold quoted
  in rad(SiO₂) against a dose in rad(Si) without conversion introduces a
  systematic error.

## Behavior contract (gate 3)

The uncertainty-source validation, combined-factor computation, RDM check, and
full component assessment pipeline are exercised by the gate 3 contract test:
scripts/test_e1012_tid_unc.py against scripts/e1012_tid_unc_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_tid_unc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
