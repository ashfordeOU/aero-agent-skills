---
name: e1003-uncertainties
description: "Use when verifying that a demonstrated test margin under ECSS-E-ST-10-03C still holds once measurement uncertainty is taken into account: compute the effective margin by subtracting the applicable measurement/instrumentation uncertainty (Table 4-2 typical values, overridable by project-specific characterization) from the demonstrated margin, assess whether the result is still positive, and flag any project-specific uncertainty that exceeds its Table 4-2 typical value for justification. Trigger: measurement uncertainty, instrumentation uncertainty, Table 4-2, test margin, demonstrated margin, effective margin, e-st-10-03, ecss, e-st-10c, test accuracy."
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
  tags: [ecss, e-st-10-03c, measurement-uncertainty, test-margin, testing, verification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Measurement Uncertainty vs. Test Margin (space-systems/ecss/e1003-uncertainties)

Use when the task is checking whether a demonstrated test margin under
ECSS-E-ST-10-03C clause 4.4.3 is still credible once the measurement
uncertainty of the test facility and instrumentation is taken into
account.

## Domain quick reference

- ECSS-E-ST-10-03C clause 4.4.3 requires that the measurement
  uncertainty of the facility and instrumentation used to control and
  measure a test be determined and accounted for whenever a test
  result is used to demonstrate compliance with a margin. A margin
  that is smaller than, or comparable to, the measurement uncertainty
  cannot be claimed as a genuine margin, because the uncertainty alone
  could account for the apparent difference between the measured
  result and the required value.
- Table 4-2 gives typical measurement uncertainty values, by test
  parameter type (e.g. temperature, vibration/acceleration, acoustic
  level, pressure, mass, electrical quantities), to use as a default
  when a project has not characterized its own facility/instrumentation
  uncertainty for that parameter.
- The effective margin for a test point is the demonstrated margin
  (achieved test result minus the required value) minus the applicable
  measurement uncertainty. A test point only supports its margin claim
  when the effective margin remains positive.
- When a project supplies its own measured/characterized uncertainty
  for a parameter type instead of the Table 4-2 typical, and that
  value is larger than the Table 4-2 typical, the difference needs to
  be flagged and justified rather than silently accepted, since it
  means the facility/instrumentation is less capable than the
  standard's baseline expectation.
- This leaf scopes measurement uncertainty vs. margin only. Allowable
  tolerances on the test input itself (e.g. how far the applied test
  condition may deviate from its nominal specified level) are the
  sibling e1003-input-tolerances leaf (clause 4.4.2, Table 4-1); the
  margin objectives a test campaign is required to demonstrate
  (qualification, acceptance, protoflight) are the sibling
  e1003-objectives leaf (clause 4.5).

## Workflow

1. For each test point (or requirement) whose compliance rests on a
   demonstrated margin, record its parameter type and the demonstrated
   margin (achieved result minus required value, in matching units).
2. Determine the measurement uncertainty to apply: use the project's
   own characterized facility/instrumentation uncertainty for that
   parameter type if available, otherwise fall back to the Table 4-2
   typical value for that parameter type.
3. Compute the effective margin: demonstrated margin minus the
   measurement uncertainty from step 2.
4. Mark the test point's margin claim adequate only when the effective
   margin is positive; otherwise it is inadequate and the margin claim
   cannot be accepted as-is (options: retest with a larger margin,
   reduce measurement uncertainty, or accept a documented risk).
5. Whenever a project-specific measured uncertainty was used in step
   2, compare it against the Table 4-2 typical for that parameter
   type; flag it for justification when it exceeds the typical value.
6. Roll every test point's adequacy and any uncertainty flags into the
   verification record; do not close out the associated requirement
   while any test point in scope is still inadequate.

## Pitfalls

- Comparing the achieved test result directly against the required
  value without subtracting measurement uncertainty, so a margin that
  is really within the noise floor of the instrumentation gets
  accepted as compliant.
- Defaulting every parameter to the Table 4-2 typical uncertainty even
  when the project has already characterized its own (larger) facility
  uncertainty for that parameter — the project-specific value takes
  precedence.
- Silently accepting a project-specific uncertainty that is worse than
  the Table 4-2 typical instead of flagging it for justification.
- Confusing this leaf's post-test measurement-uncertainty check with
  the pre-test input-tolerance allowance of the sibling
  e1003-input-tolerances leaf (clause 4.4.2) — tolerances bound how the
  test condition is applied, uncertainty bounds how confidently the
  result can be trusted.

## Behavior contract (gate 3)

The uncertainty-resolution, effective-margin, adequacy, and
typical-value-flagging logic is exercised by the gate 3 contract test:
scripts/test_e1003_uncertainties.py against
scripts/e1003_uncertainties_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_uncertainties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
