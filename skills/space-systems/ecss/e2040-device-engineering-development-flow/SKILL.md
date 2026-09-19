---
name: e2040-device-engineering-development-flow
description: "Map the milestone sequence a device engineering development is structured around under ECSS-E-ST-20-40C clause 5.1.3: fold the review spellings onto the canonical order, confirm the declared flow is a subsequence of it rather than a reordering, attach each engineering activity to the review that closes it, refuse an activity gated earlier than something it depends on or a dependency loop, and report the reviews the flow omits, the reviews nothing closes and the longest dependency chain. Use when a device development schedule is being structured, or when a review finds work arriving at the wrong gate. Trigger: ecss, e-st-20-40c, device-engineering-development-flow, device-milestone-review-sequence, activity-to-milestone-mapping, device-review-phase-mapping, activity-dependency-gating, longest-device-activity-chain."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-engineering-development-flow, device-engineering-development-flow, device-milestone-review-sequence, activity-to-milestone-mapping, device-review-phase-mapping, activity-dependency-gating, longest-device-activity-chain]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Engineering Development Flow (space-systems/ecss/e2040-device-engineering-development-flow)

Use when the task is the development flow of ECSS-E-ST-20-40C clause
5.1.3 -- the order the reviews come in, which project phase each one
closes, and which engineering activity has to be finished before each
of them.

## Domain quick reference

- The flow is a sequence of reviews, and the sequence is the point. A
  development may leave a review out when the device is simple enough,
  but it cannot hold the same review twice or run one before an
  earlier one, because each review's entry condition is the previous
  one's output.
- Reviews and phases are not the same thing. Two reviews can close
  inside one phase, so counting reviews tells nothing about how far
  through the development a device is; the phase mapping is what makes
  the flow comparable with the project schedule.
- Every activity is gated by exactly one review -- the one that cannot
  be held until the activity is finished. An activity with no gate is
  work nobody will notice is late, and a review with no activity is a
  gate with nothing to hold.
- Dependencies run forward through the gates. An activity that depends
  on another cannot be gated at an earlier review than the one it
  depends on, because the thing it needs will not exist yet. This is
  the defect a schedule tool will happily accept and a review will
  find on the day.
- A dependency loop is not a scheduling problem to resolve by choosing
  an order. It means two activities each claim to need the other's
  output, and one of the two dependencies is wrong.
- The real length of a development is the longest chain of dependent
  activities, not the number of reviews. Removing a review from the
  flow shortens the plan on paper and leaves the chain exactly as long
  as it was.

## Workflow

1. Fold every review spelling onto the canonical order and refuse an
   unrecognised one; a review nobody recognises is a review nobody
   holds.
2. Validate the declared flow as a subsequence: reject a repeat and a
   reorder, and record the reviews it leaves out as findings rather
   than as errors, because omission is a legitimate choice that has to
   be visible.
3. Map each review in the flow onto the project phase it closes, so
   the flow can be laid against the project schedule.
4. Attach each activity to its gating review. Refuse a duplicate
   activity identifier, a self-dependency and a repeated dependency,
   each of which corrupts the ordering silently.
5. Report activities gated at a review the declared flow does not
   hold: the work exists but nothing in this development closes it.
6. Walk the dependencies and report every activity gated earlier than
   something it depends on, plus every dependency naming an activity
   nobody declared.
7. Compute the longest dependency chain, refusing a loop, and report
   it alongside the review count so the plan's real length is visible.

## Pitfalls

- Reading the review count as progress. Two reviews inside one phase
  make a development look further along than it is; the phase mapping
  is what answers that question.
- Omitting a review quietly. Leaving one out can be right for a simple
  device, but it has to be recorded as a decision, or the next reader
  assumes the flow is complete and the review was simply missed.
- Gating an activity at a review that this development does not hold.
  The activity then has no closure date at all, and nothing in the
  schedule is late until the day it is needed.
- Letting a dependency point backwards through the gates. A schedule
  tool accepts it and levels the dates; the review finds that the
  input does not exist yet.
- Resolving a dependency loop by picking an order. The loop is a
  statement that two activities each need the other, and one of the
  two dependency records is simply wrong.
- Measuring the plan by milestone count. Dropping a review shortens
  the milestone list and leaves the longest dependency chain exactly
  as long, which is what actually sets the development duration.

## Behavior contract (gate 3)

The review folding, subsequence validation of the flow, review to phase
mapping, activity gating, activities outside the declared flow, reviews
closing no activity, dependency direction checking, unknown dependency
reporting and the longest dependency chain with loop refusal are
exercised by the gate 3 contract test:
scripts/test_e2040_device_engineering_development_flow.py against
scripts/e2040_device_engineering_development_flow_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_engineering_development_flow.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
