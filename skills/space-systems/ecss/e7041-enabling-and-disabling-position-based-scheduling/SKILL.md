---
name: e7041-enabling-and-disabling-position-based-scheduling
description: "Manage the enable and disable state of position-based scheduling and its scheduling groups under ECSS-E-ST-70-41C clause 6.22.8.3: hold the service level gate and the per-group gates separately, apply an enable or disable command over a set of group identifiers, reject an undeclared group without dropping the rest of the command, and partition the schedule into released, service-held and group-held activities. Use when the release gating, group enable state or group command handling of a position-based schedule is being designed or reviewed. Refuses a group command on a subservice without the group capability and an empty identifier set. Trigger: ecss, e-st-70-41c, pus-service-22, position-based-scheduling-control, scheduling-group-enable, position-schedule-release-gate, group-command-rejection, position-schedule-suspension."
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
  tags: [ecss, e-st-70-41c-scope, e7041-enabling-and-disabling-position-based-scheduling, pus-service-22, position-based-scheduling-control, scheduling-group-enable, position-schedule-release-gate, position-schedule-suspension]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS PUS Position-Based Scheduling — Enabling and Disabling (space-systems/ecss/e7041-enabling-and-disabling-position-based-scheduling)

Use when the task is the enable and disable control of the position-based
scheduling function of ECSS-E-ST-70-41C clause 6.22.8.3 — deciding which
scheduled activities the service may release once the service level gate
and the scheduling group gates have both been commanded.

## Domain quick reference

- The release of a scheduled activity passes two independent gates. The
  first is the service level gate, set by enabling or disabling the
  position-based scheduling function itself. The second is the gate of
  the scheduling group the activity belongs to. Both must be open before
  the activity is a release candidate, so an open service gate is
  necessary and never sufficient on a grouped subservice.
- The group gates exist only on a subservice that declares the group
  capability. On a subservice without it there are no groups to command
  and the service gate is the whole answer; a group command against such
  a subservice is refused rather than silently ignored.
- Disabling suspends, it does not delete. The scheduled activities and
  their orbit positions survive a disable of the service or of a group
  unchanged, and reopening the gate makes exactly the same set of
  activities eligible again. A control model that drops the schedule on
  disable is a different service.
- A command naming several groups is not all-or-nothing at the group
  level: identifiers that are declared are applied, an identifier that
  is not declared is rejected with its own reason, and the caller sees
  both lists. Malformed input, by contrast, is an input error.
- An enable of an already enabled group is accepted and moves no gate.
  Counting the gates a command actually moved separates a real state
  change from a no-op repeat, which is what makes the command safely
  repeatable after a communications gap.

## Workflow

1. Validate the declared group namespace: group numbering starts at one,
   the zero code point addresses no group, and an identifier past the
   declared capacity is an input error rather than a group to create.
2. Build the control state from the declared groups, the initial service
   gate and any group gates already open. Refuse a duplicate declaration
   and a preset enable of a group that was never declared.
3. Apply each command in order. A service command sets the service gate;
   a group command applies an enable or a disable across a set of group
   identifiers, collapsing duplicates so one identifier repeated in one
   command is one gate.
4. Record, per command, the accepted identifiers, the rejected ones with
   a reason, and the number of gates the command moved.
5. Partition the schedule against the resulting state: released when
   both gates are open, held by the service when the service gate is
   closed, held by its group when only the group gate is closed.
6. Report the gate counts, the partition, the retained schedule size and
   any finding: a rejected identifier, a command that moved nothing, or
   activities held by a group while the service gate is open.

## Pitfalls

- Treating the service gate as the only gate. On a grouped subservice an
  enabled service with every group disabled releases nothing, and a
  review that checks only the service gate reports a schedule as live
  when it is entirely suspended.
- Dropping the schedule on a disable. The activities are retained; the
  gate decides release, not membership, and re-enabling must make the
  same set eligible rather than an empty one.
- Failing a whole multi-group command because one identifier is not
  declared. The declared identifiers are applied and the undeclared one
  is reported; conflating this with a malformed request hides which
  groups actually moved.
- Accepting a group command on a subservice that never declared the
  group capability. There is no gate for the command to move, so
  accepting it reports a control the operator does not have.
- Reading a repeated enable as a failure. It is accepted and moves no
  gate; the moved count, not the acceptance, is what distinguishes the
  repeat from a first command.

## Behavior contract (gate 3)

The group identifier validation, control state construction, service and
group command application, release gating and schedule partition are
exercised by the gate 3 contract test:
scripts/test_e7041_enabling_and_disabling_position_based_scheduling.py
against
scripts/e7041_enabling_and_disabling_position_based_scheduling_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_enabling_and_disabling_position_based_scheduling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
