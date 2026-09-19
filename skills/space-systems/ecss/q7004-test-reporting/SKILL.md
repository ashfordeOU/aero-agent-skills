---
name: q7004-test-reporting
description: "Document an ECSS thermal test so the report carries its conditions, its results and its anomalies in the agreed format, and grade what it is missing. Use when an ECSS-Q-ST-70-04C reporting clause has to become a releasable document: check every field the format asks for, treat a blank field as an omission while a measured zero stays a result, validate the recorded conditions against each other, require a disposition on every anomaly, catch an anomaly logged outside the cycles that ran, and block release on a pass standing over an open anomaly. Trigger: ecss, q-st-70-04-thermal-testing-scope, thermal-test-report-completeness, test-condition-recording, test-anomaly-disposition, report-release-blocking, thermal-test-report-format."
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
  tags: [ecss, q-st-70-04-thermal-testing-scope, q7004-test-reporting, thermal-test-report-completeness, test-condition-recording, test-anomaly-disposition, report-release-blocking, thermal-test-report-format]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Testing — Test Reporting (space-systems/ecss/q7004-test-reporting)

Use when the task is the ECSS-Q-ST-70-04C reporting clauses — what the report
has to carry about the conditions the test ran at, the results it produced
and the anomalies seen on the way, and whether the document in hand is
actually releasable.

## Domain quick reference

- A report is graded on three separate things: whether it carries every
  field the format asks for, whether those fields agree with each other, and
  whether it is honest about its own anomalies. Only the first is visible at
  a glance.
- A field present but empty is missing. Downstream it reads as a zero to
  every reader and as an omission to none, which is the worst of both. A
  measured zero, by contrast, is a result and must survive the check.
- Conditions have to agree with themselves. A maximum below a minimum, a
  cycle count of zero, a dwell of zero: each of them means the report is
  describing a test that did not happen the way it is written.
- Every anomaly needs a disposition. An anomaly with a description and no
  disposition is neither closed nor carried, and it disappears at the next
  document revision.
- An anomaly logged outside the cycles that ran is a contradiction the
  report cannot resolve on its own. Either the cycle count or the anomaly
  entry is wrong, and both are worth an hour of somebody's time.
- A pass verdict standing over an open anomaly is the most expensive
  sentence a report can contain, because it is read as clearance by people
  who will never open the annex.

## Workflow

1. Take the format and check each graded section field by field, counting a
   blank exactly as an absence.
2. Grade the conditions section only when it is complete, then validate the
   recorded conditions against one another.
3. Walk the anomaly records: refuse an incomplete one, refuse an unknown
   disposition, and keep whether each is open.
4. Cross-check every anomaly cycle against the cycle count the conditions
   section recorded.
5. Read the results verdict and test it against the open anomalies rather
   than accepting it.
6. Return the verdict: incomplete while fields are missing, blocked on an
   open or inconsistent anomaly, releasable only when neither applies — plus
   the completeness figure and the standing duties.

## Pitfalls

- Filling a field with a dash or a zero to clear the template. The gap was
  the finding, and it is now unrecoverable.
- Grading completeness as a percentage and stopping there. A report at 95%
  with the conditions section missing has nothing to compare its results
  against.
- Accepting an anomaly with a narrative and no disposition. It reads as
  handled and nobody ever closed it.
- Taking the verdict at face value. The verdict is a claim in the report,
  not a conclusion about it, and the whole point of the check is testing
  that claim against the anomaly list.
- Letting an out-of-range anomaly cycle through as a typo. It is equally
  likely the cycle count is wrong, and that number is the one everything
  else in the report is scaled against.
- Putting open anomalies in an annex. They belong in the verdict statement,
  because that is the sentence that gets quoted.

## Behavior contract (gate 3)

The per-section field grading, the blank-versus-zero rule, the conditions
self-consistency check, anomaly validation with dispositions, the cycle
cross-check, the pass-over-open-anomaly finding and the releasable,
incomplete and blocked verdicts are exercised by the gate 3 contract test:
scripts/test_q7004_test_reporting.py against
scripts/q7004_test_reporting_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7004_test_reporting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
