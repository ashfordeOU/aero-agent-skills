---
name: q2007-process-planning
description: "Plan the test process of a campaign under ECSS-Q-ST-20-07 clause 5.7.1 and say whether the plan can be committed to the customer. Use when activities, resources, reviews and customer interfaces have to be reconciled into one schedule rather than four: refuse a dependency graph that closes on itself, take the longest path through the activities as the campaign duration, measure the margin left against the customer milestone, load every resource against the capacity declared for it, and check the required reviews and the customer notification lead. Trigger: ecss, q-st-20-07-test-process-clause-5-7-1, test-campaign-critical-path-duration, test-campaign-schedule-margin, test-campaign-resource-capacity-shortfall, test-campaign-review-coverage."
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
  tags: [ecss, q-st-20-07-test-centre-scope, q2007-process-planning, q-st-20-07-test-process-clause-5-7-1, test-campaign-critical-path-duration, test-campaign-schedule-margin, test-campaign-resource-capacity-shortfall, test-campaign-review-coverage, test-campaign-customer-notification-lead]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centres — Test Process Planning (space-systems/ecss/q2007-process-planning)

Use when the task is clause 5.7.1 of ECSS-Q-ST-20-07: a test campaign
has to be planned before it is run, the activities, the resources, the
reviews and the customer interfaces all sit in the same plan, and the
question is whether that plan can be committed to.

## Domain quick reference

- A campaign duration is the longest path, not the sum. Activities that
  do not depend on each other run together, so adding the durations
  overstates the campaign and adding only the durations of the named
  chain understates it; the longest path through the dependency graph
  is the campaign.
- A dependency graph that closes on itself has no duration at all. A
  cycle is an input error, not a long path, and returning any number
  for it invents a plan that cannot be executed.
- Margin is against the customer milestone, not against the plan. The
  plan always fits itself; what matters is the span left between the
  end of the longest path and the date the customer is holding.
- Resource loading is per resource. A campaign can be inside its total
  effort and still be impossible because one shaker, one clean room or
  one qualified operator is committed twice, so each resource is loaded
  against its own declared capacity.
- The reviews are part of the plan. A campaign plan that names no test
  readiness review or no post-test review is short of the interfaces
  the clause asks for, whatever its schedule looks like.
- The customer interface has a lead time. A notification sent after the
  lead the contract carries denies the customer the chance to attend or
  to object, and it is checked against the start of the campaign rather
  than against the plan date.

## Workflow

1. Validate the planning policy first: the schedule margin the test
   centre requires, the reviews a campaign owes and the customer
   notification lead. A negative margin requirement is refused.
2. Refuse a campaign with no activities; that closes on the process not
   being planned rather than on a zero-length campaign.
3. Validate the activities: a label, a positive duration, a resource
   and a predecessor list naming only declared activities. Refuse the
   same activity twice and refuse an activity that depends on itself.
4. Order the activities topologically; a graph that will not order is a
   cycle and is refused rather than truncated.
5. Walk the order, taking each activity's earliest start as the latest
   finish among its predecessors, and keep the greatest finish as the
   campaign duration. Collect the chain that produced it.
6. Take the schedule margin as the customer milestone less the campaign
   duration, and compare it with the margin required.
7. Load each resource with the durations of the activities assigned to
   it and compare against the capacity declared for that resource.
8. Check the required reviews against those the plan names, and the
   notification lead against the campaign start. Close on one verdict
   in order: process not planned, a required review missing, schedule
   margin negative, a resource over capacity, the customer notified
   late, margin below the required span, or the plan committable.

## Pitfalls

- Summing the activity durations. Parallel activities are the reason a
  campaign fits at all, and a summed duration turns a feasible plan into
  a rejected one.
- Taking the longest named chain by inspection. The longest path is
  rarely the chain anyone wrote down; it has to be computed over the
  whole graph, including the branches that look short.
- Returning a duration for a cyclic graph. A cycle means somebody wired
  a predecessor backwards, and a number returned for it is a plan that
  cannot be run.
- Checking total effort against total capacity. One over-committed
  shaker sinks a campaign whose total effort is comfortably inside the
  test centre's total, so the load is taken per resource.
- Measuring the notification lead from the plan date. The lead the
  customer is owed runs back from the start of the campaign, and a plan
  written late does not shorten it.

## Behavior contract (gate 3)

The policy validation, activity validation, the self-dependency and
cycle refusals, the topological order, the longest-path duration and
its chain, the schedule margin, the per-resource load against capacity,
the review coverage, the customer notification lead and the verdict
ordering are exercised by the gate 3 contract test:
scripts/test_q2007_process_planning.py against
scripts/q2007_process_planning_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_process_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
