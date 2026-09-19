---
name: e7041-position-based-sub-schedules
description: "Model the sub-schedule partition of the position-based schedule, under ECSS-E-ST-70-41C clause 6.22.7.1. Use when activities are not releasing and the question is which sub-schedule each one actually sits in, or when a service that never declared sub-schedule support is being modelled: placing every activity in exactly one sub-schedule, collapsing an unsupporting service onto the single default, keeping declared but empty sub-schedules visible in the partition, gating release on the schedule and the sub-schedule together, and naming the next release point ahead of the spacecraft. Trigger: ecss, e-st-70-41c, position-based-sub-schedule-partition, sub-schedule-exclusive-membership, default-sub-schedule-fallback, sub-schedule-release-gating, orbit-position-scheduling."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-position-based-sub-schedules, position-based-sub-schedule-partition, sub-schedule-exclusive-membership, default-sub-schedule-fallback, sub-schedule-release-gating, orbit-position-scheduling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Position-Based Sub-Schedules (space-systems/ecss/e7041-position-based-sub-schedules)

Use when the task is the sub-schedule structure of ECSS-E-ST-70-41C
clause 6.22.7.1 — the two requirements that say what a sub-schedule is
inside a position-based schedule and where an activity lives when the
service does not offer them.

## Domain quick reference

- A sub-schedule is a partition of the position-based schedule, not a
  second schedule. Every activity the schedule holds belongs to exactly
  one of them: not none, not two. The partition is what lets operators
  arm and disarm a whole load without touching its contents.
- Sub-schedule support is a declared service capability. A service that
  does not support them still has somewhere to put every activity — one
  implicit default sub-schedule holding the lot — so "no sub-schedules"
  means one, never zero.
- On a service without support, an activity naming a sub-schedule is
  not a harmless label. There is nothing to place it in, and quietly
  re-homing it into the default hides a ground model that believes in a
  partition the spacecraft does not have.
- A declared sub-schedule that holds nothing is a real state and has to
  stay visible. An absent key in the partition says the sub-schedule
  does not exist; an empty list says it exists and is not loaded, and
  those lead to opposite operator actions.
- Release is gated twice. The schedule has an enabled state and so does
  each sub-schedule, and an activity releases only when both permit it.
  An enabled schedule therefore proves nothing about any one activity.
- Because release points are orbit positions, "the next one" is the
  smallest forward arc from where the spacecraft is now, and that
  search skips activities whose sub-schedule is disabled rather than
  reporting them and letting the reader filter.

## Workflow

1. Resolve the service capability: supported with its declared
   sub-schedules and their enabled flags, or unsupported and reduced to
   the single default with its own flag.
2. Resolve each activity's home against that capability, rejecting an
   activity with no sub-schedule on a supporting service, one naming an
   undeclared sub-schedule, and one naming anything but the default on
   a service without support.
3. Wrap every release position into one revolution as the activity is
   validated, so later arc arithmetic is done once and consistently.
4. Build the partition over every declared sub-schedule, empty ones
   included, and reject a repeated activity identifier before it can be
   counted twice.
5. Collect the membership findings separately from the partition: an
   activity claimed by two sub-schedules, an unplaceable home, and a
   declared sub-schedule holding nothing.
6. Compute release permission per sub-schedule from the schedule flag
   and the sub-schedule flag together, and list the sub-schedules that
   hold activities they cannot currently release.
7. When the current orbit position is known, report the next activity
   the spacecraft will release, considering only the ones both gates
   allow.

## Pitfalls

- Treating a sub-schedule as a separate schedule with its own release
  logic. It is a partition of one schedule, and the schedule's own
  enabled state still sits above it.
- Reading "sub-schedules not supported" as "no sub-schedule". Every
  activity still has exactly one home, the default, and modelling it as
  absent breaks the very reports that would have shown the difference.
- Dropping empty sub-schedules from the partition. The distinction
  between undeclared and unloaded disappears at the moment an operator
  needs it.
- Concluding an activity will release because the schedule is enabled.
  The sub-schedule gate is the one that usually explains a load sitting
  still.
- Sorting release points by numeric position to find the next one.
  Across the wrap point the nearest activity has the larger number.
- Re-homing an activity into the default when its named sub-schedule is
  not declared. That hides a mismatch between the ground model and the
  on-board partition instead of reporting it.

## Behavior contract (gate 3)

The capability resolution and its idempotence, exclusive membership,
the default fallback, partition coverage of empty sub-schedules, the
membership findings, the two-gate release permission and the
forward-arc next-release search are exercised by the gate 3 contract
test: scripts/test_e7041_position_based_sub_schedules.py against
scripts/e7041_position_based_sub_schedules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_position_based_sub_schedules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
