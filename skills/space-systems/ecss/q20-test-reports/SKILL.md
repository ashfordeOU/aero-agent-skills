---
name: q20-test-reports
description: "Evaluate a test report against the quality-assurance content and approval rules of ECSS-Q-ST-20C clause 5.6.3.2: check the mandatory sections are present, that every parameter the procedure demanded carries a finite measured value in the demanded unit or a justified not-measured declaration, grade each value against its limits with a value sitting on a limit counted inside, confirm every anomaly seen during the run was written up with a nonconformance reference and a disposition, and refuse a pass conclusion contradicted by the data. Use when a test report is submitted for approval or returned for correction. Trigger: ecss, q-st-20c-clause-5-6-3-2, qa-test-report-content-check, test-data-completeness-ratio, test-discrepancy-recording, test-report-approval-signature, measured-value-limit-grading."
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
  tags: [ecss, q-st-20-quality-assurance-scope, q20-test-reports, qa-test-report-content-check, test-data-completeness-ratio, test-discrepancy-recording, test-report-approval-signature, measured-value-limit-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Quality Assurance -- Test Report Grading (space-systems/ecss/q20-test-reports)

Use when the task is the test-report check of ECSS-Q-ST-20C clause
5.6.3.2: a report has been written after a test and the question is
whether it can be approved as the record of that test, or has to go back
for correction.

## Domain quick reference

- A report is a record, not a narrative. It stands or falls on whether
  somebody who was not in the chamber can reconstruct what was tested,
  under what conditions, against which procedure revision, with what
  numbers, and what was wrong. The mandatory sections exist to make that
  reconstruction possible, so a blank section is the same defect as an
  absent one.
- Data completeness is measured against the procedure, not against what
  the report happens to contain. Every parameter the procedure demanded
  is either recorded with a finite value in the demanded unit, or is
  declared not measured with a justification. A value recorded in a
  different unit is not a completeness item; it is an uninterpretable
  number, and it counts as not recorded.
- A result the procedure never asked for is worth reporting too. It
  usually means the report was copied from a neighbouring article, or
  that the procedure and the report are on different revisions.
- Grading a value against its limits is a directional question with a
  boundary case. A value that should land exactly on its limit can sit a
  few units in the last place outside it once it has been through a
  conversion, so the comparison absorbs that representation error with a
  named tolerance instead of widening the limit itself.
- The discrepancy record is the part reviewers skip and auditors do not.
  Every anomaly observed during the run is written up; every write-up
  carries a nonconformance reference so it can be followed, and a
  disposition so it can be closed. A conclusion of pass standing over an
  out-of-limit value or an undispositioned discrepancy is the single
  most common defect in this clause.
- Approval dates bracket the test. A signature before the test ended
  approves something that had not happened; a signature after the issue
  date approves something already circulated.

## Workflow

1. Normalise the report and refuse a malformed one early: a duplicate
   measured parameter, a non-numeric value, a not-measured declaration
   with no justification, or an issue date before the test ended.
2. Check the mandatory sections; report each absent or blank one by
   name.
3. Compute data completeness against the procedure parameter list,
   keeping the recorded count, the missing list, the wrong-unit list,
   the justified not-measured list and the undemanded extras.
4. Grade each measured value against its limits, absorbing the boundary
   with the named tolerance, and derive the measured outcome from the
   set of gradings rather than from the written conclusion.
5. Grade the discrepancy record against the anomalies observed during
   the run, and each write-up for its reference and its disposition.
6. Grade the approval signatures against the test end and issue dates,
   then compare the stated conclusion with the measured outcome and the
   open discrepancies. Approve only when nothing is outstanding.

## Pitfalls

- Reading the report's own conclusion as the outcome. The outcome is
  derived from the graded values; the conclusion is a claim about it,
  and reconciling the two is the point of the check.
- Counting a value recorded in the wrong unit as present. It inflates
  completeness and hides a real defect, because nobody can grade it
  against a limit without knowing which unit was meant.
- Letting a not-measured parameter pass on the strength of a note. The
  declaration needs a justification recorded with it, otherwise the
  parameter is simply missing under a different name.
- Accepting a discrepancy write-up with no disposition because the test
  passed. An open discrepancy is what prevents the record from being
  closed, whatever the values did.
- Widening a limit so a boundary value passes. The boundary is a
  representation question, handled by the tolerance inside the
  comparison; the limit stays as the procedure wrote it.

## Behavior contract (gate 3)

The report normalisation, section check, data-completeness computation,
limit grading with its boundary tolerance, discrepancy grading, approval
date bracketing and the conclusion reconciliation are exercised by the
gate 3 contract test: scripts/test_q20_test_reports.py against
scripts/q20_test_reports_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q20_test_reports.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
