---
name: e2040-experience-summary-report-task
description: "Determine whether the device Experience Summary Report is owed at all and, when it is, whether it actually captures the development. Use when an ECSS-E-ST-20-40C clause 5.8.4 lessons record is being settled: decide applicability from the customer request before grading anything, check every mandated topic is written, trace each development event into the topic that owns its kind, separate events carried nowhere from events misfiled and events sent to an unwritten topic, weight significant events above trivial ones, and return not-required, complete or incomplete. Refuses a request reference with no request and an unknown event kind. Trigger: ecss, e-st-20-40c, experience-summary-report, device-lessons-capture, customer-requested-deliverable, development-event-traceability, report-topic-coverage, event-significance-weighting."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-experience-summary-report-task, experience-summary-report, device-lessons-capture, customer-requested-deliverable, development-event-traceability, report-topic-coverage, event-significance-weighting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Experience Summary Report (space-systems/ecss/e2040-experience-summary-report-task)

Use when the task is the experience summary record of ECSS-E-ST-20-40C
clause 5.8.4 — capturing what was learned developing an ASIC, FPGA or IP
core, in the case where the customer has asked for such a record, and
judging whether the record that exists actually carries the development.

## Domain quick reference

- Applicability comes first and is binary. This output is owed only on a
  customer request, so a development with no request owes nothing;
  grading an absent report as a shortfall invents a finding, and the
  request itself has to be cited rather than assumed.
- A report offered where none was asked for is still read, but its gaps
  are informational. Nothing was owed, so nothing can be short — the
  useful output is the mismatch between the delivery list and the
  request.
- Topic coverage and event capture are different measures. A report can
  write every mandated topic and still have lost the anomalies, and it
  can carry every anomaly into a topic it never actually wrote. Both are
  reported, and they are combined rather than substituted.
- An event lands in exactly one topic, determined by its kind. A waiver
  and a design change both belong to the design-issues topic; an anomaly
  belongs to the anomalies topic. Filing an anomaly under tool issues is
  a different defect from not filing it at all, and both differ again
  from filing it into a topic the report never wrote.
- Events are not equal. A record that captured every trivial item and
  lost the significant ones is not a lessons record, so significance
  weights the capture measure instead of a flat count.

## Workflow

1. Decide applicability from the customer request. A request with no
   cited reference, or a reference with no request, is an input error
   that has to be settled before anything is graded.
2. If nothing was requested and nothing exists, return not-required and
   stop. If nothing was requested but a report exists, read it and
   report the mismatch without turning its gaps into shortfalls.
3. If a report was requested and none exists, that is the whole finding;
   return it rather than scoring an empty record.
4. Validate the report: a topic outside the mandated set, a repeated
   topic or an unknown issue state is refused.
5. Compute topic coverage over the mandated set.
6. Validate each development event and resolve the topic that owns its
   kind. Group the failures into carried nowhere, carried into the wrong
   owner, and carried into a topic the report never wrote.
7. Compute the capture measure on significance weights, not on a count.
8. Combine coverage and capture into the completeness index, absorb
   representation error at unity with a named tolerance, and return the
   disposition — a report still in draft is incomplete however good its
   content.

## Pitfalls

- Grading the report before deciding whether it was owed. Clause 5.8.4
  is conditional, and an unrequested report cannot be short of anything.
- Treating an absent report and an empty report the same way. One is a
  contractual gap with a cited request behind it; the other is a content
  gap in something that exists.
- Counting events rather than weighting them. Losing one major anomaly
  and losing one minor tool niggle are not the same loss, and a flat
  count says they are.
- Collapsing the three event failure modes into "not captured". Filed
  under the wrong topic is a reorganisation; carried into an unwritten
  topic means the topic still has to be authored; carried nowhere means
  the lesson was never written down at all.
- Accepting a draft as complete because its content is complete. The
  record has to be issued to be a record.
- Letting a near-unity index pass by loosening the comparison. The
  named tolerance absorbs the representation error; the completeness
  condition is not widened.

## Behavior contract (gate 3)

Applicability resolution from the customer request, report validation,
mandated-topic coverage, event-kind ownership, the three event failure
modes, significance-weighted capture and the combined completeness index
are exercised by the gate 3 contract test:
scripts/test_e2040_experience_summary_report_task.py against
scripts/e2040_experience_summary_report_task_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_experience_summary_report_task.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
