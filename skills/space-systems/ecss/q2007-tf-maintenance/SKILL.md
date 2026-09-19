---
name: q2007-tf-maintenance
description: "Assess the maintenance control of a test facility under ECSS-Q-ST-20-07 clause 5.6.4 and say whether the facility may be released to a campaign. Use when preventive tasks and corrective work orders have to be read together before a run rather than separately after it: refuse a facility with no maintenance plan, measure every preventive task against its own interval instead of one calendar, age the open corrective work orders against their close-out allowance, and hold a facility whose completed maintenance carries no revalidation record. Trigger: ecss, q-st-20-07-test-facility-clause-5-6-4, test-facility-preventive-maintenance-interval, test-facility-corrective-work-order-backlog, test-facility-post-maintenance-revalidation, test-facility-release-to-service."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-tf-maintenance, q-st-20-07-test-facility-clause-5-6-4, test-facility-preventive-maintenance-interval, test-facility-corrective-work-order-backlog, test-facility-post-maintenance-revalidation, test-facility-release-to-service, test-facility-safety-critical-task-overdue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Facility Maintenance Control (space-systems/ecss/q2007-tf-maintenance)

Use when the task is clause 5.6.4 of ECSS-Q-ST-20-07: a test facility
is to be released to a campaign, its preventive maintenance plan and
its corrective work orders are the record, and the question is whether
the facility is in a state the campaign can be run in.

## Domain quick reference

- Every preventive task carries its own interval. A pump seal on a
  ninety day cycle and a crane inspection on a yearly one are overdue at
  different moments, so each task is aged against its own interval and
  never against a single facility-wide calendar date.
- Overdue is a span, not a flag. How far past its interval a task has
  run is what separates a task due this week from one that lapsed two
  cycles ago, and the worst span across the plan is what a release
  decision argues from.
- A safety-critical task is not a task with a larger span. It is a
  different decision: one lapsed safety-critical task holds the
  facility, whatever the rest of the plan looks like.
- Corrective work is aged from when it was raised, against the
  close-out allowance its priority carries, not against the preventive
  intervals. A corrective backlog can be entirely inside allowance while
  the preventive plan has lapsed, and the reverse happens just as often.
- Maintenance completed is not maintenance closed. Work that disturbed a
  measurement chain, an interlock or a structural path leaves the
  facility unproven until the revalidation it called for is recorded,
  so a completed task awaiting revalidation holds the release.
- A facility with no maintenance plan is not a facility with an empty
  one. There is nothing for a task to be overdue against, and the
  assessment closes there rather than reporting a clean plan.

## Workflow

1. Validate the maintenance policy first: the overdue span the test
   centre tolerates on a routine task, the close-out allowance per
   corrective priority, and the share of the preventive plan that has
   to be current. A negative allowance is refused rather than used.
2. Refuse a facility with no maintenance plan; that closes the
   assessment on the facility not being under maintenance control.
3. Validate the preventive tasks: a label, a positive interval, a last
   completion day not in the future, and a safety-critical flag that is
   a real boolean. Refuse the same task twice.
4. Age each task against its own interval to get its overdue span,
   taking a negative span as time still in hand.
5. Separate the lapsed safety-critical tasks; if any exist, close
   there, naming them and their spans.
6. Validate the corrective work orders and age each from the day it was
   raised against the allowance its priority carries.
7. Check the completed tasks that called for revalidation and collect
   those with no revalidation record.
8. Close on one verdict in order: no maintenance plan, a lapsed
   safety-critical task, a revalidation outstanding, a corrective order
   past its allowance, preventive currency short, a routine task past
   the tolerated span, or the facility released to service.

## Pitfalls

- Aging the whole plan against one date. A facility-wide calendar makes
  the yearly tasks look chronically overdue and hides the weekly one
  that actually lapsed.
- Ranking a lapsed safety-critical task by its span. A two day lapse on
  an interlock check is not smaller than a sixty day lapse on a filter
  change; it is a different decision and it outranks the span ordering.
- Aging corrective work against the preventive intervals. The two clocks
  are unrelated, and mixing them lets a fresh high-priority order hide
  behind a preventive plan that is current.
- Closing a task on completion. If the work called for revalidation, the
  facility is unproven until the revalidation is recorded, and the
  release has to be held rather than argued around.
- Reporting a clean plan for a facility that has none. An empty plan
  produces no overdue tasks, which reads as a pass and is the exact
  reverse of the finding.

## Behavior contract (gate 3)

The policy validation, preventive task validation, per-task overdue
spans, the safety-critical separation, corrective work order aging
against its priority allowance, the revalidation outstanding check,
preventive currency and the verdict ordering are exercised by the gate 3
contract test: scripts/test_q2007_tf_maintenance.py against
scripts/q2007_tf_maintenance_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_tf_maintenance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
