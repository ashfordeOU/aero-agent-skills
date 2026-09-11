---
name: e1002-verification-report
description: "Use when compile or audit the Verification Report against the ECSS-E-ST-10-02 clause 5.3.2.5 and Annex F Document Requirements Definition: confirm every verification event cites the underlying report holding its evidence, reconcile the executed methods against the methods the verification control document planned in both directions, detect an event whose claimed status contradicts the verdict of the report it cites, and roll the events up to a status for each requirement. Trigger: ecss, e-st-10-02c, verification-report, vrpt, annex-f-drd, method-agreement, evidence-linkage, status-rollup."
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
  tags: [ecss, e-st-10-02c, verification-report, vrpt, annex-f-drd, method-agreement, status-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Verification Report DRD (space-systems/ecss/e1002-verification-report)

Use when the task is to compile or audit the Verification Report (VRPT)
of ECSS-E-ST-10-02 clause 5.3.2.5 and Annex F -- the summary layer that
states, per requirement, what was done and where the evidence lives.

## Domain quick reference

- The VRPT is a roll-up, so its integrity is a question about agreement
  with its sources, not about its own internal tidiness. A summary that
  disagrees with the reports beneath it is worse than no summary: it
  carries authority the evidence does not support.
- The central check is status against source. An event claiming
  "passed" while the test report it cites failed is the defect that
  makes a summary dangerous, and no per-event view can see it.
- The check runs one way only. Claiming passed over a failed source is a
  contradiction; claiming failed over a failed source is consistent
  reporting and must not be flagged.
- Method agreement is checked in both directions against the
  verification control document. A planned method with no event was not
  carried out; an executed method nobody planned was not agreed. Both
  are findings, and each is reported against its method.
- Every event cites the report holding its evidence. An entry with
  nothing beneath it summarizes nothing, and the citation is what lets
  the source check run at all.
- An event citing a report absent from the source index is left to the
  evidence check rather than reported twice -- one missing link, one
  finding.
- Requirement status is severity ordered: any failed event fails it, any
  event not executed leaves it open, only an all-passed set verifies it.
- A requirement with no event at all raises rather than reporting
  verified by default. Nothing was done, and an empty roll-up must never
  read as success.

## Workflow

1. Confirm requirement entries are present and uniquely identified.
2. For each event, confirm a supporting report reference is cited.
3. Reconcile executed methods against planned methods in both
   directions.
4. For each event whose cited report is in the source index, confirm
   its claimed status does not overstate the source verdict.
5. Roll the events up to a requirement status under the severity
   ordering.
6. The VRPT is complete only when nothing is open or failed and the
   summary agrees with every source.

## Pitfalls

- Auditing the VRPT on its own. Every internal consistency check can
  pass while the summary contradicts the reports it stands on.
- Flagging an event that reports a failure over a failed source. It is
  doing exactly what it should, and flagging it teaches reviewers to
  ignore the check that matters.
- Comparing executed methods against planned only one way, so a method
  quietly added outside the plan never surfaces.
- Accepting a narrative citation ("see test campaign") in place of a
  report reference, which breaks the link the source check needs.
- Reporting a requirement with no verification event as verified
  because nothing failed. An empty set must raise, not pass.
- Double-reporting an event whose reference is both missing and
  unresolvable as two separate defects.

## Behavior contract (gate 3)

The evidence-linkage, two-way method agreement, status-versus-source
and severity-ordered roll-up logic is exercised by the gate 3 contract
test: scripts/test_e1002_verification_report.py against
scripts/e1002_verification_report_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e1002_verification_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
