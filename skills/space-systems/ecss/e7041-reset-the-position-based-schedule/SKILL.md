---
name: e7041-reset-the-position-based-schedule
description: "Determine what a reset of the position-based schedule actually discards, under ECSS-E-ST-70-41C clause 6.22.6.5. Use when a reset has emptied a schedule and the ground has to account for what was lost, or when one is being planned against a live orbit: deleting every activity whatever sub-schedule or scheduling group it sat in and whether the schedule was enabled or disabled, releasing nothing on the way out, leaving the schedule's own enabled state and its sub-schedule and group definitions untouched, and warning about activities inside the arc just ahead of the current orbit position. Trigger: ecss, e-st-70-41c, position-based-schedule-reset, orbit-position-scheduling, discarded-scheduled-activity-census, schedule-enabled-state-preserved, imminent-release-arc-warning."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-reset-the-position-based-schedule, position-based-schedule-reset, orbit-position-scheduling, discarded-scheduled-activity-census, schedule-enabled-state-preserved, imminent-release-arc-warning]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Reset the Position-Based Schedule (space-systems/ecss/e7041-reset-the-position-based-schedule)

Use when the task is the reset of ECSS-E-ST-70-41C clause 6.22.6.5 — the
three requirements that say a reset empties the position-based schedule
completely, and everything the ground has to reconstruct afterwards
about what went with it.

## Domain quick reference

- A position-based schedule holds activities against an orbit position,
  not against a time. Each one is released when the spacecraft reaches
  the position recorded beside it, so "what is still pending" is an arc
  question, not a clock question.
- A reset deletes every activity the schedule holds. It does not walk
  the sub-schedules one at a time and it does not skip a disabled one:
  membership of a sub-schedule or of a scheduling group has no bearing
  on whether an activity survives a reset, because none of them do.
- A reset works the same whether the schedule is enabled or disabled.
  Disabling first does not preserve anything; it only means the
  activities were already not going to be released while it stayed
  that way.
- Nothing is released on the way out. An activity whose position the
  spacecraft is about to reach is discarded exactly like one half a
  revolution away, and that is the loss an operator notices first, so
  the arc immediately ahead of the current position is worth counting
  before the reset rather than reconstructing after it.
- A reset empties the schedule; it does not reconfigure the service.
  The schedule's own enabled state, the set of sub-schedules and the
  set of scheduling groups all survive it, along with their enabled
  flags. A reset that also cleared those would leave the ground unable
  to re-load the schedule it just lost.
- The census is the deliverable. Counts per sub-schedule and per group,
  taken before the deletion, are what a re-load is built from; taken
  after, there is nothing left to count.

## Workflow

1. Validate the schedule state: the enabled flag, the declared
   sub-schedules and scheduling groups with their flags, and every
   activity, wrapping each release position into one revolution.
2. Reject an activity naming a sub-schedule or group the service never
   declared, and a repeated activity identifier — both make the census
   that follows untrue.
3. Count what the reset will discard, broken down by sub-schedule and
   by scheduling group, with activities in no group counted separately
   rather than folded into one of them.
4. If the current orbit position is known, list the activities inside
   the arc just ahead of it; these are dropped unexecuted and are named
   individually, not just counted.
5. Apply the reset: an empty activity list, the same enabled flag, the
   same sub-schedule and group definitions.
6. Verify the outcome against those three invariants — empty, enabled
   flag unchanged, definitions unchanged — and raise a finding for each
   one that did not hold.
7. Report that a reset of an enabled schedule discarded activities
   without releasing them, so the record says what was lost rather than
   only that a reset happened.

## Pitfalls

- Resetting sub-schedule by sub-schedule and assuming that covers the
  schedule. An activity in no group, or in a sub-schedule nobody
  remembered to include, stays behind and then releases unexpectedly.
- Disabling the schedule before the reset in the belief that it
  protects pending activities. It changes nothing about what the reset
  deletes.
- Expecting an activity sitting a degree ahead of the current position
  to be released as the reset lands. It is discarded like every other.
- Clearing the sub-schedule and group definitions along with the
  activities. The ground then cannot re-load the schedule into the
  structure it had, and every subsequent insertion is rejected against
  an undeclared sub-schedule.
- Taking the census after the reset. There is nothing to count, and the
  re-load is rebuilt from memory instead of from the schedule.
- Reading an unchanged enabled flag as evidence the reset did not
  happen. Preserving it is the required behaviour, not a failure to
  act.

## Behavior contract (gate 3)

The state validation, position wrapping, per-sub-schedule and per-group
censuses, imminent-arc listing, the reset itself and the three
post-reset invariant checks are exercised by the gate 3 contract test:
scripts/test_e7041_reset_the_position_based_schedule.py against
scripts/e7041_reset_the_position_based_schedule_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_reset_the_position_based_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
