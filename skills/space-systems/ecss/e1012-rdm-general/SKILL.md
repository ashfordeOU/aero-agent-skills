---
name: e1012-rdm-general
description: "Use when compute the radiation design margin (RDM) in the general dose-effects case under ECSS-E-ST-10-12 §5.1.2/§5.2: determine the mission total ionizing dose at the component shielded location, obtain the component's lot-qualified failure dose, derive the design dose by applying an uncertainty factor to the mission dose, calculate the RDM as the ratio of failure dose to design dose, and verify that each component's RDM meets or exceeds the minimum required margin for its application category. Flag any component where the margin is insufficient before design acceptance. Trigger: ecss, e-st-10-system-scope, radiation-design-margin, rdm, total-ionizing-dose, dose-effects, radiation-hardness-assurance, margin-approach, lot-acceptance-test."
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
  tags: [ecss, e-st-10-system-scope, radiation-design-margin, rdm, total-ionizing-dose, dose-effects, radiation-hardness-assurance, margin-approach, lot-acceptance-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — RDM General Case (space-systems/ecss/e1012-rdm-general)

Use when the task is to compute and apply the radiation design margin
(RDM) for EEE components in the general dose-effects case under
ECSS-E-ST-10-12 §5.1.2/§5.2, following the margin approach: the
assessed mission dose at each component location is compared against
the lot-qualified failure dose, and each component must demonstrate
a ratio of failure dose to design dose that meets the required minimum
margin.

## Domain quick reference

- The margin approach for dose effects (§5.1.2) defines the RDM as
  the ratio of the lot-qualified failure dose to the design dose for
  each component. The design dose is derived by multiplying the
  shielded mission total ionizing dose (TID) by an uncertainty factor;
  when the RDM requirement itself absorbs all analysis uncertainties
  (the general case), the uncertainty factor is 1.0 and the design
  dose equals the mission dose directly.
- The mission dose at a component location is the accumulated TID in
  Gy(Si) computed from an approved radiation environment model and
  shielding analysis for the target orbit, mission duration, and
  enclosure geometry. It is not estimated — it is the output of a
  traceable analysis (SHIELDOSE, SPENVIS, or equivalent).
- The lot-qualified failure dose is the minimum failure threshold
  established from lot acceptance radiation testing of the part type;
  it must be a measured quantity from the actual lot, not a datasheet
  value or generic catalog figure.
- The minimum required RDM for the general case is 2.0: the failure
  dose must be at least twice the design dose. Components assigned to
  more demanding application categories may carry a higher required
  minimum.
- A component fails the RDM check when its computed RDM falls below
  the required minimum; this triggers either a design change
  (increased shielding, part substitution) or an uprated test
  programme — not a waiver of the margin without engineering
  substantiation.

## Workflow

1. Retrieve the shielded mission TID for each component location from
   the approved radiation analysis; reject any component entry without
   a traceable analysis reference.
2. Determine the uncertainty factor applicable to each component:
   use 1.0 for the general case (margin approach absorbs
   uncertainties); apply a value greater than 1.0 only when an
   elevated analysis uncertainty has been identified and separately
   justified.
3. Compute the design dose: design_dose = mission_dose_gy ×
   uncertainty_factor. This is the dose the component must be
   qualified against at the required margin.
4. Retrieve the lot-qualified failure dose for each component from
   the radiation test data; reject a catalogue or generic value —
   the lot data must be traceable.
5. Compute the RDM: RDM = qualified_failure_dose_gy / design_dose_gy.
   A ratio below 1.0 means the component fails at the design dose
   even before applying any margin.
6. Compare RDM against the required minimum margin (2.0 for the
   general case, or the value set for the component's application
   category); flag every component whose RDM falls short.
7. Aggregate the findings; a design is RDM-compliant only when the
   findings list is empty. Non-compliant components must be dispositioned
   (increased shielding, part substitution, or substantiated
   uprating) before the design can proceed.

## Pitfalls

- Using a datasheet TID rating instead of a measured lot failure dose
  — datasheet values are typically end-of-life operating ratings, not
  failure thresholds, and substituting them overstates the margin in
  an untraced way.
- Applying the uncertainty factor twice (once to inflate the mission
  dose and again as a required RDM multiplier) — in the general margin
  approach the required RDM is the sole uncertainty absorber; adding a
  separate factor on top of it double-counts the uncertainty.
- Treating a component as passing because its RDM is slightly below
  2.0 but "close enough" — the minimum RDM is a hard gate, not a soft
  target; a component at RDM 1.95 is non-compliant regardless of
  other margins.
- Omitting components with thick local shielding on the assumption
  that the dose is negligible — the dose estimate must be computed,
  not assumed; very high shielding can introduce secondary dose
  enhancement effects that increase effective TID.

## Behavior contract (gate 3)

The design-dose derivation, RDM computation, per-component compliance
check, and multi-component aggregation logic are exercised by the gate
3 contract test: scripts/test_e1012_rdm_general.py against
scripts/e1012_rdm_general_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_rdm_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
