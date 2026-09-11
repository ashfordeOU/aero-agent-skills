---
name: e10-req-baseline
description: "Use when establishing or controlling the requirements baseline for a configuration item (CI) under ECSS-E-ST-10C clause 5.2.3.9: classify each requirement's approval status ahead of an agreed baseline milestone, verify it carries requirement text and a verification method, identify duplicate requirement identifiers within the set, define the baseline record once every requirement in the set is ready, and validate every subsequent addition, modification, or deletion of a baselined requirement against an approved change request. Trigger: ecss, e-st-10c, requirements baseline, baseline management, configuration item, milestone review, change control, requirement verification."
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
  tags: [ecss, e-st-10c, requirements-baseline, baseline-management, configuration-item, change-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Requirements Baseline Management (space-systems/ecss/e10-req-baseline)

Use when the task is to establish and control the requirements
baseline of a configuration item (CI) under ECSS-E-ST-10C clause
5.2.3.9 -- checking a CI's requirement set for baseline readiness at
an agreed project milestone, freezing it into a baseline record, and
tracking every later change to a baselined requirement through an
authorized change request.

## Domain quick reference

- A CI's requirement set is baselined at an agreed project milestone
  (e.g. SRR, PDR, CDR, QR), not on an arbitrary date -- the milestone
  is the trigger that closes the requirement definition activity for
  that phase and opens the change-control activity.
- A requirement is baseline-ready only when it is approved (not
  draft, in review, or withdrawn), carries requirement text, and
  carries a verification method; a requirement missing any one of
  these is a distinct, independently reported gap, because fixing one
  gap does not imply the others are fixed too.
- Two requirements sharing the same identifier within one CI's set is
  a baseline-blocking defect in its own right -- it breaks
  traceability between the requirement and its verification evidence
  even if both copies are individually approved.
- Once a baseline is established, the requirement set behind it is
  frozen: an addition, a modification, or a deletion against a
  baselined requirement is only authorized when it carries an approved
  change request. A baseline that has not yet been established has no
  change-control obligation -- there is nothing frozen to protect yet.

## Workflow

1. Assemble the CI's full requirement set for the target milestone.
   Reject an unrecognized requirement status or milestone name before
   the review proceeds -- an unrecognized value is a data problem to
   fix, not a baseline gap to report.
2. For each requirement, check approval status, requirement text, and
   verification method independently, and report every gap found (not
   just the first). Separately scan the set for duplicate requirement
   identifiers.
3. A CI with zero requirements at the milestone is itself a finding --
   an empty set is not vacuously ready.
4. Establish the baseline only when the full review comes back with no
   violations; an ineligible attempt is rejected, not recorded with a
   caveat, so an incomplete baseline can never be mistaken for a
   complete one.
5. After establishment, route every proposed change (add, modify,
   delete) against a baselined requirement through the change-control
   check: a change without an approved change request is flagged, and
   the baseline itself must be in "established" status before any
   change control can be applied against it.
6. Aggregate the change-control findings for the baseline; the
   baseline is not change-controlled until that list is empty.

## Pitfalls

- Baselining a requirement set that has an unset verification method
  because the requirement text itself looks complete -- text and
  verification method are separate readiness gates and both must be
  satisfied.
- Treating a duplicate requirement identifier as harmless when both
  copies happen to be approved -- the duplicate breaks the one-to-one
  link to verification evidence regardless of each copy's status.
- Recording an ineligible baseline attempt "with exceptions noted"
  instead of rejecting it -- clause 5.2.3.9 baseline control depends on
  the baseline record meaning the set was actually ready, not that it
  was reviewed and waved through anyway.
- Applying change control to a baseline that was never established --
  there is no frozen reference to change against, so the check must
  reject the attempt rather than silently approve or silently flag
  every change.

## Behavior contract (gate 3)

The requirement-readiness, duplicate-identifier, milestone-baseline,
and change-control logic is exercised by the gate 3 contract test:
scripts/test_e10_req_baseline.py against
scripts/e10_req_baseline_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_req_baseline.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
