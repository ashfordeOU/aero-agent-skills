---
name: e7041-managing-the-position-based-schedule-general
description: "Manage the content of a position-based schedule under ECSS-E-ST-70-41C clause 6.22.6.2: apply insertion and deletion operations one at a time against the loaded schedule, hold every entry ordered by orbit number and ascending-node angle, and enforce the store capacity and the uniqueness of each scheduled request identifier. Use when insertion, deletion, capacity exhaustion, a duplicate request identifier, free-slot accounting or the ordering of a position-based schedule is being specified or reviewed for a service 22 subservice. Refuses an insertion past capacity and the deletion of an absent identifier. Trigger: ecss, e-st-70-41c, pus-service-22, position-based-schedule-insertion, position-based-schedule-deletion, scheduled-request-identifier-uniqueness, position-based-schedule-capacity, orbit-position-entry-ordering."
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
  tags: [ecss, e-st-70-41c, pus-service-22, e7041-managing-the-position-based-schedule-general, position-based-schedule-insertion, position-based-schedule-deletion, scheduled-request-identifier-uniqueness, position-based-schedule-capacity, orbit-position-entry-ordering]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Position-Based Scheduling — Managing the Schedule, General (space-systems/ecss/e7041-managing-the-position-based-schedule-general)

Use when the task is the general schedule management of ECSS-E-ST-70-41C
clause 6.22.6.2 — putting activities into a position-based schedule, taking
them out again, and keeping the store consistent while a run of management
commands is applied to it.

## Domain quick reference

- The request identifier is the handle, so it has to be unique. Deletion
  names an entry by that identifier alone, and a schedule holding two entries
  under one identifier cannot say which of them a deletion removes.
- The schedule is ordered by orbit position, not by arrival. The execution
  function reads the next activity off the front, so an entry inserted late
  for an early position has to land in front of entries already held.
- Ordering needs the orbit number and the angle together. An entry near the
  end of one orbit precedes an entry at the ascending node of the next, and
  ordering on the angle alone inverts exactly that pair.
- Capacity is a hard edge of the store, not a guideline. An insertion into a
  full schedule is refused, and the refusal has to reach the ground as a
  refusal rather than as a silently dropped activity.
- A run of operations is applied in order, and each sees the state the
  previous one left. A deletion early in the run frees the slot a later
  insertion needs, so reordering the run changes which operations succeed.
- A refused operation does not abort the run. The remaining operations are
  still applied, and the answer is the pair of lists — accepted and rejected
  — rather than a single verdict.

## Workflow

1. Validate the capacity and the initial schedule: unique identifiers, whole
   non-negative orbit numbers and angles inside one revolution from the
   ascending node.
2. Refuse an initial schedule already holding more entries than the capacity;
   that is a load error rather than a management outcome.
3. Order the initial schedule by orbit position, breaking ties on the request
   identifier so the ordering is reproducible.
4. Apply each operation in turn. An insertion validates the entry, checks the
   identifier is free and the store has a slot, then places the entry in
   position order; a deletion removes the named identifier.
5. Record a refused operation with its reason and carry on with the run
   rather than abandoning the remaining operations.
6. Report the resulting schedule, its occupancy and free slots, and the
   accepted and rejected operation lists.

## Pitfalls

- Appending an insertion to the end of the store and sorting later. Any read
  of the schedule between the insertion and the sort sees an activity in the
  wrong place, and the execution function is exactly such a reader.
- Ordering on the ascending-node angle alone. Entries then interleave across
  orbits, and an activity due next orbit is released this one.
- Letting a duplicate identifier in because the orbit positions differ. The
  entries are distinct until someone deletes one of them, and then the
  deletion is ambiguous.
- Aborting the whole run on the first refusal. Operations the ground expected
  to take effect silently do not, and the schedule ends in a state neither
  side predicted.
- Reporting occupancy without free slots. The next uplink is planned against
  the remaining room, and a bare count of entries does not give it.

## Behavior contract (gate 3)

The entry validation, position ordering, insertion with capacity and
uniqueness checks, deletion of an absent identifier, sequential operation
application and the accepted/rejected reporting are exercised by the gate 3
contract test:
scripts/test_e7041_managing_the_position_based_schedule_general.py against
scripts/e7041_managing_the_position_based_schedule_general_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_managing_the_position_based_schedule_general.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
