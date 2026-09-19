---
name: e7041-position-based-scheduling-groups
description: "Map the scheduling-group partition of a position-based schedule onto its sub-schedules, under ECSS-E-ST-70-41C clause 6.22.8.1. Use when a group command reached more activities than expected, or when an activity will not release and it is unclear which gate holds it: placing every activity in at most one declared group, keeping the group partition independent of the sub-schedule partition, showing the two crossed rather than merged, naming the ungrouped remainder no group command can reach, and reporting all three release gates that must be open together. Trigger: ecss, e-st-70-41c, position-based-scheduling-group, group-sub-schedule-cross-partition, ungrouped-activity-remainder, triple-release-gate, orbit-position-scheduling."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-position-based-scheduling-groups, position-based-scheduling-group, group-sub-schedule-cross-partition, ungrouped-activity-remainder, triple-release-gate, orbit-position-scheduling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Position-Based Scheduling Groups (space-systems/ecss/e7041-position-based-scheduling-groups)

Use when the task is the scheduling-group structure of ECSS-E-ST-70-41C
clause 6.22.8.1 — the two requirements that say what a scheduling group
is inside a position-based schedule and how many of them an activity
can belong to.

## Domain quick reference

- A scheduling group is a second partition over the same activities,
  independent of the sub-schedule partition. An activity has one
  sub-schedule and, separately, at most one group; the two answers are
  unrelated and neither can be derived from the other.
- "At most one" is the difference from sub-schedules. Every activity
  has a sub-schedule; an activity may have no group at all, and that
  ungrouped remainder is exactly the set no group command will ever
  reach. It has to be counted, not assumed empty.
- Group support is a declared capability. On a service without it, no
  activity carries a group, and an activity that names one is a ground
  model believing in a partition the spacecraft does not have.
- The value of a group is that it crosses sub-schedules. A group
  collecting one activity from each of three sub-schedules is doing its
  job, and one command disables all three at once — which is also how a
  group command surprises an operator who was thinking in
  sub-schedules.
- Because the partitions are independent, the useful view is the two
  crossed: which activities sit in this sub-schedule and that group.
  Folding them into one list loses the fact that made the group worth
  declaring.
- Release is gated three times: the schedule, the activity's
  sub-schedule, and its group. An activity behind two shut gates does
  not move when one of them is opened, and reporting only the first
  gate found sends an operator round the loop twice.

## Workflow

1. Resolve the scheduling-group capability: supported with its declared
   groups and enabled flags, or unsupported with none.
2. Resolve each activity's group, allowing none, rejecting an
   undeclared group and rejecting any group at all on a service without
   support.
3. Validate the sub-schedule of each activity against the declared
   sub-schedules, and wrap every release position into one revolution.
4. Build the group census over every declared group, empty ones
   included, plus the ungrouped remainder as its own entry.
5. Cross the two partitions into a matrix keyed by sub-schedule and
   group, so an activity's two memberships stay separately visible.
6. Identify the groups that span more than one sub-schedule and name
   the sub-schedules each one reaches.
7. For every activity, list all the shut gates rather than the first
   one, and report the activities held by more than one.
8. When the current orbit position is known, give the releasable
   activities in the order the spacecraft will reach them, skipping
   everything any gate holds.

## Pitfalls

- Treating a group as a sub-schedule by another name. They partition
  the same activities independently, and a command against one says
  nothing about the other.
- Assuming every activity is in a group. The ungrouped remainder is
  invisible to group commands, which is how a "disable everything by
  group" leaves activities releasing.
- Deriving a group from its activities' sub-schedule. A group that
  happens to sit inside one sub-schedule today is not confined to it.
- Reporting only the first shut gate. The operator enables it, nothing
  releases, and the second gate is discovered a revolution later.
- Accepting a group name on a service that declared no group support.
  It resolves to nothing on board and the activity is not where the
  ground thinks it is.
- Dropping empty declared groups from the census. A group that exists
  and is unloaded is a different state from one that does not exist.

## Behavior contract (gate 3)

The capability resolution and its idempotence, at-most-one group
membership, the ungrouped remainder, the sub-schedule cross-partition,
spanning-group detection, the three-gate release permission with the
full list of shut gates and the forward-arc releasable order are
exercised by the gate 3 contract test:
scripts/test_e7041_position_based_scheduling_groups.py against
scripts/e7041_position_based_scheduling_groups_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_position_based_scheduling_groups.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
