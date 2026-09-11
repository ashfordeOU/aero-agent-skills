---
name: e1012-env-margins
description: "Use when apply environment-driven margins for a spacecraft radiation
  assessment under ECSS-E-ST-10C §5.3: determine whether the AE-8 worst-case GEO
  trapped-electron exemption applies for a given mission orbit, compute the design
  dose by multiplying the predicted total ionising dose by the required radiation
  design margin factor for deterministic models, verify that a probabilistic-model
  confidence level meets the level agreed with the customer or authority, confirm
  that model-uncertainty evidence is documented, and record the §5.3a–e obligation
  status before the environment input is released to the radiation-effects analysis.
  Trigger: ecss, e-st-10-system-scope, radiation-margins, ae-8, geo-environment,
  model-uncertainty, rdm, probabilistic-model, confidence-level, environment-driven-margins."
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
  tags: [ecss, e-st-10-system-scope, radiation-margins, ae-8, geo-environment, model-uncertainty, rdm, probabilistic-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Systems — Environment-Driven Margins (space-systems/ecss/e1012-env-margins)

Use when the task is applying environment-driven margins in a spacecraft radiation
assessment under ECSS-E-ST-10C §5.3 — selecting the correct margin approach
(deterministic radiation design margin or probabilistic confidence-level agreement),
checking AE-8 worst-case GEO trapped-electron exemption eligibility, verifying
model-uncertainty documentation, and closing out the §5.3a–e obligations before
the environment input feeds the design.

## Domain quick reference

- §5.3a establishes that every radiation environment assessment must carry an
  explicit margin approach: either deterministic (a radiation design margin factor
  is multiplied into the predicted total ionising dose to yield the design dose)
  or probabilistic (a confidence level for solar-event and trapped-particle model
  outputs is agreed with the customer or designated authority before the value
  is used in design). The approach must be declared and documented; using an
  undeclared approach is a non-conformance, not a conservative default.
- §5.3b covers the AE-8 worst-case GEO exemption: when a mission operates in
  geostationary orbit and the exact epoch within the solar cycle is uncertain, the
  AE-8 (or AE-8 MAX) peak trapped-electron flux may be applied as a bounding
  environment without a full solar-cycle-averaged integration, provided the
  worst-case flag is explicitly set and the justification is recorded. The
  exemption does not extend to MEO or HEO orbits, where the electron flux
  profile depends strongly on the fraction of time spent inside the belt.
- §5.3c sets the minimum radiation design margin (RDM) factor for deterministic
  assessments. An RDM below the floor value (illustratively 2× for this module —
  projects must substitute their approved value) is not acceptable unless a
  higher authority explicitly approves a reduced margin with documented
  justification. The RDM is applied to the total ionising dose (TID) to obtain
  the design dose that drives part selection and shielding sizing.
- §5.3d requires model-uncertainty evidence to be on record for every model used:
  the model name, the specific version or release used for the analysis, and the
  known uncertainty factors (e.g., AE-8's historically documented factor-of-two
  uncertainty on electron fluence at GEO altitudes). Missing any of these three
  fields means the uncertainty has not been characterised and the margin
  rationale is incomplete.
- §5.3e covers probabilistic-model risk agreement: when a probabilistic model
  is used (e.g., for solar proton event fluence), the confidence level the model
  run was performed at must be recorded and confirmed to meet or exceed the
  mission-level agreed confidence level. A model run at a lower confidence than
  agreed is a finding even if the predicted dose would still pass after applying
  shielding.

## Workflow

1. For each spacecraft item with a radiation environment input, declare whether
   the assessment uses a deterministic or a probabilistic margin approach.
   Reject an undeclared or unrecognized approach before proceeding.
2. For items using a trapped-electron model in GEO, evaluate whether the AE-8
   worst-case exemption applies: the orbit must be GEO, the model must be AE-8
   (or AE-8 MAX or AE-8 MIN), and the worst-case flag must be explicitly set.
   Document the exemption justification when it is invoked; do not assume the
   exemption silently for MEO or HEO orbits.
3. Verify that model-uncertainty evidence is on record: model name, model
   version, and the set of known uncertainty factors. Flag every missing field
   as a distinct finding — a partially documented uncertainty record does not
   count as documented.
4. For deterministic assessments: retrieve the predicted total ionising dose
   and the RDM factor. Verify the RDM factor meets the minimum floor. Compute
   the design dose as total ionising dose × RDM factor. Flag a missing dose or
   missing factor as a finding before attempting the computation.
5. For probabilistic assessments: retrieve the model's confidence level and
   the agreed confidence level. Confirm the model's confidence level meets or
   exceeds the agreed level. Flag a shortfall as a finding; record the agreed
   level and the actual level in the finding for traceability.
6. Aggregate findings per item. An item is margin-compliant only when all
   finding lists are empty — a partial pass (e.g., model-uncertainty documented
   but RDM below floor) is still a non-conformance.

## Pitfalls

- Omitting the margin-approach declaration and treating the first numeric value
  found as a design dose — the approach determines how the margin is applied,
  and conflating deterministic and probabilistic processing produces incorrect
  design inputs.
- Applying the AE-8 worst-case GEO exemption to an MEO or HEO orbit because
  the peak flux envelope is similar in magnitude — the exemption is orbit-specific
  because the time-integral of flux (total fluence) behaves very differently
  outside GEO.
- Recording a model-uncertainty entry with the model name only and treating the
  version and uncertainty factors as implied — without the specific version,
  the analysis is not reproducible, and without the uncertainty factors, the
  RDM cannot be rationally justified.
- Using an RDM below the minimum floor and recording it as a tailoring — a
  reduced RDM requires a formal authority approval with documented risk
  acceptance, not just a project note.
- Running a probabilistic model at a higher confidence than agreed and not
  recording the actual level — this obscures the true conservatism of the
  analysis and prevents meaningful comparison across items.

## Behavior contract (gate 3)

The margin-approach categorization, AE-8 GEO exemption check, RDM computation,
probabilistic confidence-level agreement, model-uncertainty documentation check,
and full item assessment are exercised by the gate 3 contract test:
scripts/test_e1012_env_margins.py against scripts/e1012_env_margins_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_env_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
