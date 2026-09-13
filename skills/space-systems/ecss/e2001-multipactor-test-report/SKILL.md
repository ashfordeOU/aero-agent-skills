---
name: e2001-multipactor-test-report
description: "Use when verify the multipactor test report that ECSS-E-ST-20-01C clause 8.7 puts to the customer for approval once radio-frequency testing is complete: confirm the report carries every expected content item, that it cites the approved-procedure identifier and backs each as-run deviation with an agreed waiver, that every detection technique credited with the result has a recorded trace, that every non-conformance raised is closed with an agreed disposition, and that the outcome derived from the recorded operating-power, the applied-power and the observed threshold-power really demonstrates the required power-margin-db rather than resting on the report's own wording. Trigger: ecss, e-st-20-01c, multipactor-test-report, test-report-content, customer-approval-after-test, as-run-deviation, non-conformance-disposition, threshold-determination, achieved-margin-db."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-test-report, multipactor-test-report, test-report-content, customer-approval-after-test, as-run-deviation, non-conformance-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Test Report Content (space-systems/ecss/e2001-multipactor-test-report)

Use when the task is the clause 8.7 content audit of ECSS-E-ST-20-01C -- the
document the customer approves once multipactor testing of a
radio-frequency unit is finished. Where the clause 8.6 procedure audit asks
whether a plan is approvable, this leaf asks whether the as-run test is
traceable to that plan and whether the recorded evidence supports the
compliance statement the report makes.

## Domain quick reference

- Clause 8.7 makes the report a customer-approved deliverable, so it is
  audited on content and evidence, not on its conclusion. The expected items
  are the test-item identification and as-built configuration, the
  approved-procedure reference, the facility and calibration records, the
  as-run vacuum conditions and seeding arrangement, the drive levels
  actually applied, the detection traces, the threshold determination, the
  achieved margin, the deviation record, the non-conformance record, the
  pass-fail statement and the approval block.
- Traceability has two halves. The identifier the report cites must be the
  identifier of the plan the customer approved -- a report citing another
  document describes a test nobody agreed to. And every departure from that
  plan must carry a customer-agreed waiver reference, because an unwaived
  departure silently replaces the approved intent with the operator's.
- Evidence is per technique. A technique named in the conclusion but with no
  recorded trace makes that conclusion unverifiable, and a single credited
  technique is not independent coverage whatever its trace shows. A trace
  from a technique nobody credited is surplus evidence, recorded and not
  faulted.
- Every non-conformance raised during the run needs an agreed close-out --
  repair, rework, use-as-is, scrap or retest. An item still open leaves the
  article in an undetermined state, so the report cannot be approved around
  it, and a close-out outside the agreed set is not a disposition at all.
- The outcome is derived, never quoted. With no event detected, the margin
  demonstrated is a lower bound set by the highest power applied: ten times
  the base-ten logarithm of applied-power over operating-power. With an
  event detected, the margin is fixed by the lowest power at which it
  appeared, and an event recorded above the highest power applied is not a
  finding but an impossibility -- the report contradicts itself and is
  rejected outright.

## Workflow

1. Compare the report's section list against the expected content items;
   every absent item is a finding, extra annexes are recorded only.
2. Check the cited procedure identifier against the approved one, then walk
   the deviation record: any deviation without a customer-agreed waiver
   reference is a finding.
3. Walk the credited detection techniques against the recorded traces; flag
   a credited technique with no trace and flag fewer than two credited
   techniques. Record surplus traces without faulting them.
4. Walk the non-conformance record: an item with no disposition is open and
   blocks approval, an item with an unrecognised disposition is rejected.
5. Derive the outcome from the recorded powers -- operating-power, highest
   applied-power and observed threshold-power -- and compare the margin it
   yields against the required margin. Mark whether the margin is an exact
   figure or a lower bound.
6. Aggregate. The report is approvable only when content, traceability,
   evidence, non-conformances and the derived outcome are all clean.

## Pitfalls

- Approving on the report's own pass-fail statement: the statement is one
  more content item to audit, and the audit re-derives the margin from the
  recorded powers instead of trusting the wording.
- Reading "no event detected" as an unlimited margin: a clean run only
  demonstrates the margin its highest applied level reached, so the result
  is a lower bound and fails whenever that level fell short of the
  requirement.
- Waiving a deviation inside the report itself: the waiver is a customer
  agreement referenced by the report, and a deviation described but not
  referenced is unwaived no matter how reasonable it reads.
- Closing a non-conformance by describing it: an item without one of the
  agreed dispositions is open, and an open item blocks approval even when
  the test result itself looks compliant.
- Failing a threshold that sits one unit-in-the-last-place under the power
  the required margin demands: the target is a computed power, so the exact
  boundary is absorbed by the tolerance rather than by relaxing the margin.

## Behavior contract (gate 3)

The section-completeness, traceability, evidence, non-conformance and
outcome-derivation logic is exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_test_report.py against
scripts/e2001_multipactor_test_report_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2001_multipactor_test_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
