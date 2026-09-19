---
name: e7041-insert-activities-into-the-position-based-schedule
description: "Validate the instructions that insert activities into the position-based schedule, under ECSS-E-ST-70-41C clause 6.22.6.6. Use when an insertion request came back part-accepted and the ground needs to know which instruction failed and why, or when a load is being built for an orbit already under way: checking each instruction against the declared sub-schedules and scheduling groups, a release position inside one revolution, an identifier neither already held nor repeated in the same request, the room left, and the arc still ahead of the spacecraft. Trigger: ecss, e-st-70-41c, position-based-schedule-insertion, orbit-position-release-point, per-instruction-rejection-reason, schedule-capacity-exhaustion, insufficient-lead-arc."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-insert-activities-into-the-position-based-schedule, position-based-schedule-insertion, orbit-position-release-point, per-instruction-rejection-reason, schedule-capacity-exhaustion, insufficient-lead-arc]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Insert Activities into the Position-Based Schedule (space-systems/ecss/e7041-insert-activities-into-the-position-based-schedule)

Use when the task is the insertion of ECSS-E-ST-70-41C clause 6.22.6.6
— the eleven requirements governing how a request adds activities to a
position-based schedule, what each instruction has to satisfy, and what
happens to the rest of the request when one of them does not.

## Domain quick reference

- Each instruction carries four things: the sub-schedule it belongs to,
  optionally a scheduling group, the orbit position at which it is to
  be released, and the request to release there. Drop any of them and
  the activity cannot be held in a form the schedule can act on.
- The release point is a position, not a time. It lives inside one
  revolution, so 370 degrees and 10 degrees name the same point, and
  every comparison between two of them is a forward arc from the
  current position rather than a subtraction.
- An instruction is accepted or rejected on its own. A request carrying
  ten instructions where one names a sub-schedule that was never
  declared inserts the other nine; the rejection is reported per
  instruction, with the reason, not as a failed request.
- Acceptance and release are different questions. An activity goes into
  a disabled sub-schedule, a disabled group or a disabled schedule just
  as readily as into an enabled one — it is simply held there until the
  thing above it is enabled.
- The identifier has to be unique against what the schedule already
  holds and against the rest of the same request. A repeat inside one
  request is the easier one to miss, because nothing in the schedule
  conflicts with it until the first copy lands.
- Capacity is consumed as the request is worked through, so the
  instruction that fills the schedule is accepted and the next one is
  not. Checking capacity once for the whole request over-accepts.
- An activity needs arc ahead of it. A release position the spacecraft
  is about to sweep past leaves no room for the insertion to complete,
  and a position just behind the current one is not "late" — it is
  almost a full revolution away, which is a different operational fact.

## Workflow

1. Validate the schedule state: enabled flag, declared sub-schedules
   and groups, optional capacity, and the activities already held.
2. Validate each instruction and wrap its release position into one
   revolution before any comparison.
3. Reject an instruction naming an undeclared sub-schedule or group, a
   missing request body, an identifier already held, or an identifier
   already used earlier in the same request.
4. Track the room left as instructions are accepted and reject the
   first one that would exceed the capacity, not the whole request.
5. When the current orbit position is known, measure the forward arc to
   each release position and reject one that falls inside the minimum
   lead, absorbing representation error at that bound with a tolerance
   rather than padding the lead.
6. Hold the accepted activities in release-position order, and report
   the order in which the spacecraft will actually reach them from
   where it is now.
7. Report the findings: a wholly rejected request, a partially accepted
   one, a schedule now full, and activities parked behind a disabled
   sub-schedule or a disabled schedule.

## Pitfalls

- Failing the whole request on one bad instruction. The good ones were
  accepted on board, and a ground model that discards them diverges
  from the spacecraft immediately.
- Comparing release positions as plain numbers. Across the wrap point
  the smaller number is the later one, and the schedule walks in the
  wrong order.
- Checking capacity once before the loop. Two instructions then fit
  into one free slot and the second rejection only appears on board.
- Treating a release position just behind the spacecraft as expired. It
  is reached again next revolution; whether that is intended is an
  operator question, not an automatic rejection.
- Rejecting an insertion because the sub-schedule is disabled. The
  activity is held, and disabling is how operators park a load they
  intend to arm later.
- Letting one request carry the same activity identifier twice. The
  first insertion makes the second a duplicate, so the failure depends
  on ordering unless the request is checked against itself.

## Behavior contract (gate 3)

The state and instruction validation, the per-instruction rejection
reasons, running capacity, the forward-arc lead check with its boundary
tolerance, release-position ordering, the reach-order report and the
insertion findings are exercised by the gate 3 contract test:
scripts/test_e7041_insert_activities_into_the_position_based_schedule.py
against
scripts/e7041_insert_activities_into_the_position_based_schedule_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_insert_activities_into_the_position_based_schedule.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
