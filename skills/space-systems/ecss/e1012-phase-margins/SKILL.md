---
name: e1012-phase-margins
description: "Use when establish project-phase radiation hardness margins for a space mission under ECSS-E-ST-10-12C §5.6: determine the required radiation design margin (RDM) at each review milestone (pre-PDR, PDR-to-CDR, post-CDR), verify that the RDM for total ionising dose and displacement damage meets or exceeds 2.0 relative to the predicted mission environment, confirm phase-appropriate hardness assurance activities are scoped, and validate that post-CDR test methods (cobalt-60, proton, heavy-ion, or verified heritage similarity) are appropriate for each radiation type. Apply at every phase gate where a component radiation tolerance is compared against the mission environment budget. Trigger: ecss, e-st-10-12c, e-st-10-system-scope, radiation-hardness-assurance, phase-margins, rdm, tid-margin, dd-margin, see-qualification, test-methods."
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
  tags: [ecss, e-st-10-12c, e-st-10-system-scope, radiation-hardness-assurance, phase-margins, rdm, tid-margin, dd-margin, see-qualification, test-methods]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Project-Phase Margins (space-systems/ecss/e1012-phase-margins)

Use when the task is establishing and verifying radiation design margins
at each project phase under ECSS-E-ST-10-12C §5.6: computing the
radiation design margin (RDM) for total ionising dose (TID) and
displacement damage (DD), checking phase-gate compliance from pre-PDR
through post-CDR, and confirming that post-CDR hardness assurance uses
an appropriate test method for each radiation type.

## Domain quick reference

- §5.6.1 sets the mission margin requirement: the RDM is the ratio of
  the device's radiation tolerance to the predicted mission environment
  fluence or dose. The minimum acceptable RDM for TID and DD is 2.0 at
  every project phase. Single-event effects (SEE) are handled through a
  qualification approach rather than a numeric RDM gate.
- §5.6.2 (pre-PDR): margins are established from analysis using
  preliminary environment and parts data. Hardware test data are not yet
  required; analysis-only evidence is acceptable at this phase.
- §5.6.3 (PDR–CDR): the RDM must be maintained as environment and parts
  data mature. Any component whose RDM drops below 2.0 during this
  interval must be flagged and resolved before CDR.
- §5.6.4 (post-CDR hardness assurance): the RDM must be substantiated
  by hardware test data or verified heritage similarity — analysis alone
  is no longer sufficient. Each component is assigned a hardness
  assurance category based on its criticality and the availability of
  test evidence.
- §5.6.5 (test methods): the accepted methods per radiation type are
  cobalt-60 or X-ray (with ELDRS screening) for TID, proton or neutron
  irradiation for DD, and heavy-ion or proton testing for SEE. Verified
  heritage similarity is acceptable when the prior test conditions fully
  bound the mission environment.

## Workflow

1. For each component in the radiation-sensitive parts list, obtain the
   device radiation tolerance (TID in krad(Si), DD as normalised proton
   fluence or NIEL equivalent) and the predicted mission environment
   value for that location. Reject any component entry that is missing
   either value before computing its RDM.
2. Compute the RDM: device tolerance divided by predicted environment
   value. A component with RDM < 2.0 is non-compliant; flag it with the
   shortfall and the phase at which it was detected.
3. At the pre-PDR gate: confirm every component has a computed RDM based
   on preliminary data. Analysis-only evidence is acceptable; note where
   worst-case assumptions were used.
4. At the PDR–CDR gate: re-evaluate RDMs against updated environment and
   parts data. Flag any component whose RDM has decreased since pre-PDR
   and confirm it remains at or above 2.0.
5. At the post-CDR gate: for each component, verify that a hardware test
   or confirmed heritage similarity substantiates the RDM. Flag any
   component still relying solely on analysis at this phase.
6. For each post-CDR test record, confirm the test method is appropriate
   for the radiation type: cobalt-60, X-ray, or ELDRS for TID; proton
   or neutron for DD; heavy-ion or proton for SEE. Flag mismatches.
7. For SEE-sensitive components, confirm a qualification approach is
   documented (immune, tolerant with mitigation, or avoided) rather than
   a numeric RDM. Flag any SEE-sensitive component with no documented
   approach.
8. Aggregate findings per component across RDM compliance, hardness
   assurance evidence, and test-method validity. A component is
   phase-gate compliant only when all three finding lists are empty.

## Pitfalls

- Applying the TID or DD RDM threshold of 2.0 to SEE: SEE do not use
  a numeric RDM gate; they require a documented qualification approach.
  Treating absence of an SEE RDM as a violation produces false findings.
- Accepting analysis-only evidence at post-CDR: §5.6.4 requires hardware
  test data or verified similarity after CDR. An analysis-only record
  that was valid at pre-PDR becomes a compliance gap at post-CDR.
- Using a test method that does not bound the mission environment: a
  cobalt-60 test at dose rate several decades above the mission rate may
  underestimate ELDRS damage in bipolar devices. When ELDRS is a concern,
  the standard requires additional low-dose-rate testing or a correlation
  factor.
- Conflating tolerance at room temperature with tolerance across the
  operating range: RDM must be based on the worst-case operating
  temperature and bias condition, not the standard bench-test condition.
- Accepting a heritage similarity claim without bounding the prior
  environment: similarity is valid only when the previous mission
  environment fully covers the new one in dose, spectrum, and dose rate.

## Behavior contract (gate 3)

The RDM computation, phase-gate compliance checks, test-method
validation, and margin categorization logic are exercised by the gate 3
contract test: scripts/test_e1012_phase_margins.py against
scripts/e1012_phase_margins_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_phase_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
