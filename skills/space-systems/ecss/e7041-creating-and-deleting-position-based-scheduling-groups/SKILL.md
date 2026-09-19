---
name: e7041-creating-and-deleting-position-based-scheduling-groups
description: "Manage the creation and deletion of position-based scheduling groups, under ECSS-E-ST-70-41C clause 6.22.8.2. Use when a group request came back part-rejected, or before deleting a group that still holds a load: refusing a create for an identifier the registry already holds and once the group limit is reached, refusing a delete for an unknown group and for one still enabled, starting every new group empty and disabled, counting by sub-schedule the activities a deletion discards before they are gone, and tracking the limit across the request. Trigger: ecss, e-st-70-41c, position-based-scheduling-group-lifecycle, group-deletion-cascade-census, scheduling-group-limit, enabled-group-delete-refusal, per-instruction-rejection-reason."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-creating-and-deleting-position-based-scheduling-groups, position-based-scheduling-group-lifecycle, group-deletion-cascade-census, scheduling-group-limit, enabled-group-delete-refusal, per-instruction-rejection-reason]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Creating and Deleting Position-Based Scheduling Groups (space-systems/ecss/e7041-creating-and-deleting-position-based-scheduling-groups)

Use when the task is the scheduling-group lifecycle of ECSS-E-ST-70-41C
clause 6.22.8.2 — the fifteen requirements covering the requests that
create and delete position-based scheduling groups, what each
instruction has to satisfy, and what a deletion takes with it.

## Domain quick reference

- A group is a registry entry with an enabled flag, not a container the
  ground invents on the fly. Creating one adds the entry; the service
  decides how many it can hold, and a create beyond that limit is
  refused rather than queued.
- A new group starts empty and disabled. Creation therefore changes
  nothing about what the schedule releases, which is what makes it safe
  to do at any point in a revolution.
- An identifier already in the registry cannot be created again. The
  second create is not a no-op returning the existing group; it is a
  refusal, because silently reusing it would give two owners one gate.
- Deleting an enabled group is refused. The flag is a release gate, and
  removing a gate that is holding a load back would let it go at the
  next revolution with nobody having asked for it.
- Deleting a disabled group takes its activities with it. That is the
  point operators underestimate: the group is a membership, and losing
  the membership loses the activities that had it.
- The census has to be taken before the deletion, broken down by
  sub-schedule. Afterwards the activities are gone, and the
  sub-schedules they came from look untouched — nothing in their own
  state records that a group deletion emptied part of them.
- Capacity moves in both directions inside one request. A delete frees
  a slot the next create can use, so the limit is tracked as the
  request is worked through rather than checked once at the start.
- Each instruction stands alone. An unknown group in the middle of a
  request does not withdraw the creations around it.

## Workflow

1. Validate the registry: support flag, the declared groups with their
   enabled flags, and the optional limit — rejecting a registry already
   holding more groups than its limit allows.
2. Validate the activities attached to those groups, rejecting one that
   names a group the registry does not hold, and wrap every release
   position into one revolution.
3. Validate each instruction: one action, one group identifier,
   normalized for case and padding.
4. Refuse every instruction outright when the service declares no
   scheduling-group support, per instruction rather than as a whole
   request.
5. For a create: refuse an identifier already held, refuse once the
   remaining capacity is gone, otherwise add the group empty and
   disabled and consume a slot.
6. For a delete: refuse an unknown group, refuse an enabled one,
   otherwise count the activities it holds by sub-schedule, remove them
   with the group, and return the slot.
7. Report the outcome per instruction with its reason, the activity
   count before and after, the identifiers discarded, the remaining
   capacity and the cascade census taken before anything was removed.

## Pitfalls

- Deleting a group to tidy the registry. The activities it held go with
  it, and no sub-schedule report shows where they went.
- Taking the cascade census after the deletion. It returns zero, and
  the loss is reconstructed from memory instead of from the schedule.
- Disabling a group and reading that as having removed it. The entry is
  still there, still occupying a slot against the limit.
- Deleting an enabled group by disabling it first without checking what
  it holds. The delete then succeeds and discards a live load.
- Checking the group limit once for the whole request. A delete may
  have freed a slot, and a create may have taken the last one.
- Treating a duplicate create as harmless. It is refused, and a ground
  model that assumed success attaches activities to a group whose
  enabled flag someone else owns.
- Failing the whole request on one unknown group. The creations around
  it were applied on board.

## Behavior contract (gate 3)

The registry and activity validation, the instruction normalization,
the create refusals for duplicate identifiers and the group limit, the
delete refusals for unknown and enabled groups, the cascade census by
sub-schedule, capacity returning on delete and the per-instruction
rejection reasons are exercised by the gate 3 contract test:
scripts/test_e7041_creating_and_deleting_position_based_scheduling_groups.py
against
scripts/e7041_creating_and_deleting_position_based_scheduling_groups_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_creating_and_deleting_position_based_scheduling_groups.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
