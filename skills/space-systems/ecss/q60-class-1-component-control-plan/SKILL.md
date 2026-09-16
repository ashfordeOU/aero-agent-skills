---
name: q60-class-1-component-control-plan
description: "Use when a drafted plan has to become a maintenance verdict. Evaluate whether a component control plan is both prepared and still maintained as the highest reliability class demands under ECSS-Q-ST-60C clause 4.1.2.2: refuse a plan carrying no reference or issue, count the required chapters that stand on a procedure rather than a heading, measure the share of the revision interval the current issue has consumed, age every substitution request, supplier change, obsolescence notice, alert and nonconformance disposition against the declared response time, and name the review milestones the plan was never taken through. Trigger: ecss, q-st-60c-clause-4-1-2-2, class-one-component-control-plan-maintenance, component-control-plan-revision-currency, component-control-plan-update-trigger-backlog, component-control-plan-milestone-review, component-control-plan-chapter-coverage."
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
  tags: [ecss, q-st-60-eee-component-selection-scope, q60-class-1-component-control-plan, class-one-component-control-plan-maintenance, component-control-plan-revision-currency, component-control-plan-update-trigger-backlog, component-control-plan-milestone-review, component-control-plan-chapter-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components -- Class 1 Component Control Plan (space-systems/ecss/q60-class-1-component-control-plan)

Use when the task is the clause 4.1.2.2 plan question of ECSS-Q-ST-60C
at the highest reliability class: a component control plan exists, and
the question is whether it was prepared properly and is still being
maintained, rather than written once and filed.

## Domain quick reference

- The clause has two halves and only the first is usually done.
  Preparing the plan means every required chapter is written with a
  procedure behind it. Maintaining it means the plan still describes the
  programme a year later, and both halves are graded here.
- A chapter drafted with no procedure reference behind it is not
  prepared. The contents page then matches the required list while each
  chapter defers its subject, so a blank procedure reference reads as an
  unwritten chapter and the covered share falls accordingly.
- Currency is a number, not a feeling. The issue age is measured against
  the declared revision interval and reported as the share of that
  interval consumed, so a plan approaching its revision date is visible
  before it passes it. An issue landing exactly on its interval is still
  current, the comparison tolerance being there to absorb representation
  error rather than to extend the interval.
- An event that moves a part starts a clock. A substitution request, a
  supplier or production line change, an obsolescence notice, an alert
  or a changed nonconformance disposition each has to reach the plan
  inside the declared response time. One that never arrived is an open
  item and stops the assessment; one that arrived outside the response
  time is recorded as late even though it landed, because the interval
  it was late by is when the programme ran on the old rule.
- Milestone reviews are where the plan is used. A plan never taken
  through the design reviews that depend on it was maintained for its
  own sake, so the outstanding milestones are named rather than counted.
- The slowest incorporation is worth as much as the verdict. A plan that
  absorbs every event on the last permitted day and one that absorbs
  them in a week carry the same word, and nobody can recover the
  difference later from the word alone.

## Workflow

1. Validate the maintenance policy first: the minimum chapter coverage,
   the revision interval, the response time an event has to reach the
   plan inside, the marginal band at the end of the interval inside
   which a current plan is still advised on, and the required review
   milestones. A coverage floor above one, a non-positive interval or
   response time, a full-width marginal band, or an unrecognised
   milestone is refused rather than used.
2. Validate the plan identity: a non-blank plan reference, a non-blank
   issue label, a non-negative issue age and a boolean approval
   declaration. An absent plan, or one with a blank reference or issue,
   closes the assessment on plan not established.
3. Validate every chapter record: a recognised chapter name, no
   duplicate chapter, a boolean drafted flag, and a procedure reference
   that may be blank but is then read as no procedure. Take the covered
   share over the required chapters and name the absent and the
   unprepared ones in full.
4. Validate every trigger event: a recognised trigger, a non-blank event
   reference recorded only once, a non-negative day it was raised, and
   an incorporation day that is either absent or not before the day it
   was raised.
5. Age the events. An incorporated event reports the days it took; an
   open one reports the days it has waited against the day the plan is
   assessed on. Sort them into open past the response time, late but
   landed, and timely, and keep the slowest incorporation.
6. Take the revision currency as the issue age over the interval, then
   check customer approval, the currency against its limit, the open
   event backlog, and the review milestones the plan has been taken
   through.
7. Report the chapter coverage, the currency, the absent and unprepared
   chapters, the open and late events, the slowest incorporation and the
   outstanding milestones, and raise an advisory when the issue sits in
   the last stretch of its interval. Close on one verdict: plan not
   established, chapter coverage short, plan not approved, revision
   overdue, trigger backlog open, milestone review outstanding, or plan
   maintained for class one.

## Pitfalls

- Grading preparation and stopping. A plan that covered every chapter at
  issue 1 and has not moved since is the failure this clause's second
  half exists to catch, so currency and the event backlog are graded
  beside the coverage.
- Reading the contents page as the coverage. A required chapter heading
  with no procedure behind it counts as unprepared, however carefully
  the heading is worded.
- Closing a late event as if it were timely. It landed, so it is not
  open, but the weeks it was late are weeks the programme bought parts
  against the previous rule, and that is recorded rather than dropped.
- Treating a review milestone as a distribution list. The plan is used
  at the review; a milestone the plan never reached is an unused plan,
  not a paperwork gap.
- Reporting a bare pass. The coverage, the currency, the slowest
  incorporation and the outstanding milestones are what the next issue
  is compared against, and the verdict word carries none of them.

## Behavior contract (gate 3)

The policy validation, plan identity validation, chapter validation and
coverage, the revision currency and its overdue test, the trigger event
validation, ageing, open and late sorting, the slowest incorporation,
the outstanding milestones, the marginal currency advisory and the plan
verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_1_component_control_plan.py against
scripts/q60_class_1_component_control_plan_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_component_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
