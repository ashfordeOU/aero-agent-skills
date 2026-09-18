---
name: q6012-development-plan-review-item
description: "Evaluate the development plan review item of ECSS-Q-ST-60-12C clause 7.3.12 for a microwave die: order the remaining activities through their dependencies, reject a circular or dangling link, roll the durations forward to the earliest finish the work allows, size the float left against the committed date, spread each activity effort across its duration to find the peak staffing demand against declared capacity, test every milestone against the earliest finish of the work it names, then close, action or reject the item. Use when a microwave die design review reaches the schedule, milestones and resources planned for the work still ahead. Trigger: ecss, q-st-60-12-microwave-die-scope, microwave-die-development-plan-review, remaining-development-schedule-margin, development-activity-critical-path, development-milestone-feasibility, development-resource-loading-peak, development-plan-dependency-cycle."
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
  tags: [ecss, q-st-60-12-microwave-die-scope, q6012-development-plan-review-item, microwave-die-development-plan-review, remaining-development-schedule-margin, development-activity-critical-path, development-milestone-feasibility, development-resource-loading-peak, development-plan-dependency-cycle]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Microwave Die — Development Plan Review Item (space-systems/ecss/q6012-development-plan-review-item)

Use when the task is the development plan review item of
ECSS-Q-ST-60-12C clause 7.3.12 -- reviewing the schedule, the
milestones and the resources planned for the development activity that
is still ahead, rather than reviewing the die that activity produces.

## Domain quick reference

- The item grades a plan, not a part. Three questions carry it and all
  three have to be answered before it closes: does the remaining work
  fit inside its commitment, do the people exist to do it, and is every
  milestone reachable by the work it names.
- Activities are listed in the order somebody typed them and executed
  in the order their dependencies allow. The earliest finish therefore
  comes from rolling durations forward through the dependency graph,
  never from adding the durations up or reading the last row.
- Two malformed dependency shapes have to be rejected before anything
  is computed. A link to an activity the plan does not list means the
  plan is incomplete; a cycle means it cannot be executed at all, and
  neither produces a finish date worth arguing about.
- Float is the difference between that earliest finish and the
  committed date, and it is the only float the programme owns. A plan
  that finishes exactly on its commitment has none, which is a finding
  in its own right rather than a pass.
- Effort and duration are different quantities and a plan that confuses
  them looks affordable. Spreading each activity effort across its
  duration and summing what overlaps gives a loading profile; the peak
  of that profile, not the average, is what capacity has to cover.
- A milestone placed before the earliest finish of the work it names is
  not ambitious, it is unreachable, and no amount of added resource
  moves it. A milestone sitting exactly on that finish is reachable
  only if nothing at all slips.

## Workflow

1. Normalize the remaining activities: canonical identifier, positive
   duration, non-negative effort, dependencies reduced to a set. Reject
   a duplicate identifier and an unknown field rather than carrying
   either through.
2. Reject a dependency on an activity the plan does not list, and
   reject a cycle. Both make the rest of the item unanswerable, so they
   are found before any date is computed.
3. Roll the durations forward through the dependency order to get the
   earliest start and finish of every activity, then take the latest
   finish as the earliest the remaining work can be done.
4. Size the float against the committed date and grade it on the margin
   policy share of the span. Separate a finish past the commitment,
   which blocks, from a thin float, which actions.
5. Build the loading profile from effort over duration across each
   activity span and take its peak. Compare the peak with the declared
   capacity, and flag a peak inside capacity but above the caution
   share separately from a peak beyond capacity.
6. Test every milestone against the earliest finish of the activities
   it names, then close, action or reject the item, reporting the
   critical path so the action lands on the activities that set the
   date.

## Pitfalls

- Adding the activity durations up. That answers a plan with no
  parallel work and inflates the finish for every plan that has some,
  which hides the real driver and puts the action on the wrong row.
- Reading effort as duration. Twenty person-days over ten days is two
  people; taken as a twenty day activity it is one person and a plan
  that will not hold, and the loading question is never asked at all.
- Grading the loading on the average across the span. The average is
  always inside capacity on a long plan; only the peak of the profile
  says whether the programme can staff the week it is worst.
- Accepting a milestone because it is after the committed date. The
  milestone has to be after the work it names, and a milestone hanging
  off an early branch can sit late in the programme and still be placed
  before the branch it depends on can finish.
- Comparing a float or a loading peak against its bound by bare
  arithmetic. Both are sums and products of floating-point durations,
  so a plan holding exactly the required float can land a few units in
  the last place on the wrong side of the bound; the comparison absorbs
  that representation error while the bound stays untouched.

## Behavior contract (gate 3)

The activity normalization, dependency rejection, forward pass,
critical path, float grading, loading profile peak, milestone
reachability and closure verdict are exercised by the gate 3 contract
test: scripts/test_q6012_development_plan_review_item.py against
scripts/q6012_development_plan_review_item_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_development_plan_review_item.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
