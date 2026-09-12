---
name: ndt-verification
description: "Use when verify NDT/NDI method applicability, inspection coverage
  adequacy, and indication acceptance for structural elements under ECSS-E-ST-32C
  clause 4.6.3.13: determine the applicable inspection methods for a given material
  family (metallic, composite, bond, weld) and defect family (surface, subsurface,
  volumetric, delamination), confirm the inspected fraction meets the
  criticality-based coverage minimum (100% primary, 50% secondary, 20% tertiary),
  evaluate each recorded NDT indication against its acceptance limit, and confirm no
  rejectable or marginal indications remain. Applies to primary, secondary, and
  tertiary load-carrying structures where NDT evidence is required in the structural
  verification matrix. Trigger: ecss, e-st-32-structures-scope, ndt, ndi,
  non-destructive-testing, structural-verification, coverage, acceptance-criteria,
  indication-evaluation."
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
  tags: [ecss, e-st-32-structures-scope, ndt, ndi, non-destructive-testing, structural-verification, coverage, acceptance-criteria, indication-evaluation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — NDT/NDI Verification (space-systems/ecss/ndt-verification)

Use when the task is the NDT/NDI verification of structural elements under
ECSS-E-ST-32C clause 4.6.3.13 — selecting applicable inspection methods,
confirming coverage fractions meet criticality-based minimums, and evaluating
each indication against its acceptance limit.

## Domain quick reference

- Clause 4.6.3.13 requires that every structural element subject to NDT evidence
  be assessed against three criteria: method applicability, inspection coverage,
  and indication acceptance. All three must pass before the element is considered
  NDT-verified.
- **Method applicability** depends on the material family (metallic, composite,
  bond, weld) and the defect family targeted (surface, subsurface, volumetric,
  delamination). Not every method is effective for every combination — penetrant
  testing (PT) and magnetic particle testing (MT) address surface-only flaws; MT
  further requires a ferromagnetic material, so composites are excluded. Ultrasonic
  testing (UT) and radiographic testing (RT) reach subsurface and volumetric
  defects. Eddy current testing (ET) is applicable to conductive materials for
  surface and near-surface flaws. Visual testing (VT) is a baseline for all
  accessible surfaces.
- **Inspection coverage** is the fraction of the element's inspectable area that
  is actually examined. The minimum fraction is set by criticality: primary
  load-carrying structure requires 100%, secondary structure 50%, and tertiary
  structure 20%. A shortfall is a finding regardless of indication results.
- **Indication acceptance** compares the recorded size of each relevant indication
  against the method-specific acceptance limit. An indication below the limit is
  acceptable; one equal to the limit is marginal (does not pass); one above the
  limit is rejectable. Both marginal and rejectable indications block NDT
  acceptance.

## Workflow

1. For each structural element in the verification matrix that requires NDT
   evidence, record its material family, defect families targeted, criticality
   level, and the NDT method applied.
2. Look up the applicable methods for each (material family, defect family) pair.
   Confirm the method actually used appears in the applicable set; if it does not,
   flag an inapplicable-method finding before proceeding.
3. Retrieve the inspected coverage fraction and the criticality level. Check
   whether the fraction meets the criticality-based minimum. Record any shortfall
   as a coverage finding.
4. For each NDT indication recorded during inspection, compare its size to the
   acceptance limit. Categorize the outcome as acceptable, marginal, or
   rejectable. Any non-acceptable indication becomes an indication finding.
5. Aggregate all findings per element. The element achieves NDT verification only
   when the applicable-method check passes, coverage is adequate, and no
   indication findings remain.
6. Document the method, coverage fraction, indication summary, and pass/fail
   verdict in the structural verification data package per the project data
   requirements.

## Pitfalls

- Applying a method outside its applicable range (e.g., MT on a composite) and
  recording no indications as a passing result — the absence of indications from
  an inapplicable method carries no evidentiary weight.
- Treating a coverage fraction below the criticality minimum as acceptable because
  no rejectable indications were found in the inspected portion — the missed area
  is uninspected, not defect-free.
- Accepting a marginal indication on the grounds that it is "at" the limit — the
  acceptance criterion is strictly below the limit; equal-to is a finding.
- Omitting the defect family from the method-selection step and applying a
  surface-only method to a subsurface-sensitive joint — the target defect may be
  invisible to the chosen method even if the method is valid for other defect
  types in the same material.

## Behavior contract (gate 3)

The method-applicability, coverage-check, indication-evaluation, and full
component-assessment logic is exercised by the gate 3 contract test:
scripts/test_ndt_verification.py against scripts/ndt_verification_logic.py
(stdlib unittest, offline). Run:

```
python3 scripts/test_ndt_verification.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
