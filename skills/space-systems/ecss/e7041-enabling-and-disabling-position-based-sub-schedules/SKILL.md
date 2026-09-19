---
name: e7041-enabling-and-disabling-position-based-sub-schedules
description: "Evaluate an enable or disable request against the position-based sub-schedules it names, under ECSS-E-ST-70-41C clause 6.22.7.2. Use when a load stopped releasing and the sub-schedule gate is suspected, or when arming one mid-revolution: applying each instruction on its own so an undeclared name does not withdraw the rest, accepting a restatement of the current state as inert, retaining rather than deleting the activities of a disabled sub-schedule, counting the release points swept while the gate was shut, and warning about what a newly enabled sub-schedule releases next. Trigger: ecss, e-st-70-41c, position-based-sub-schedule-enable, sub-schedule-disable-retention, missed-position-release-arc, per-instruction-status-rejection, effective-release-gate."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-enabling-and-disabling-position-based-sub-schedules, position-based-sub-schedule-enable, sub-schedule-disable-retention, missed-position-release-arc, per-instruction-status-rejection, effective-release-gate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Enabling and Disabling Position-Based Sub-Schedules (space-systems/ecss/e7041-enabling-and-disabling-position-based-sub-schedules)

Use when the task is the sub-schedule status control of ECSS-E-ST-70-41C
clause 6.22.7.2 — the nineteen requirements covering the requests that
enable and disable position-based sub-schedules, what each instruction
is allowed to do, and what happens to the activities underneath.

## Domain quick reference

- Enabling and disabling act on the gate, never on the load. A disabled
  sub-schedule keeps every activity it held, at the same release
  position, in the same sub-schedule. Nothing is deleted, re-homed or
  re-positioned, and the schedule that comes back when it is enabled
  again is the one that went in.
- A request carries instructions, and each one stands or falls alone.
  One naming a sub-schedule the service never declared is rejected on
  its own; the instructions around it still take effect, so the
  spacecraft state after a partly rejected request is not the state
  before it.
- Restating a status is legal and inert. Enabling an already enabled
  sub-schedule is accepted and changes nothing, which is what makes a
  status request safe to re-send after a doubtful uplink.
- A request that acts twice on the same sub-schedule is resolved by
  order, the later instruction standing. That is a deterministic answer
  but rarely the intended one, so it is worth reporting rather than
  quietly applying.
- Release positions come round every revolution, so a release point
  swept while the gate was shut is missed, not lost: the activity is
  still held, and it becomes eligible again once the spacecraft has
  travelled the remaining arc back to it.
- Enabling mid-revolution can release something almost immediately. The
  activities sitting a few degrees ahead of the current position are
  the ones the operator has to be told about before the instruction
  goes up, not after.
- The sub-schedule flag is not the whole gate. The schedule's own
  enabled state sits above it, and an enabled sub-schedule inside a
  disabled schedule releases nothing while telling every status report
  that it is enabled.

## Workflow

1. Validate the status map of declared sub-schedules and the activities
   held against them, wrapping each release position into one
   revolution.
2. Validate each instruction: one declared sub-schedule, one of the two
   actions, normalized for case and padding.
3. Apply the instructions in order, recording three outcomes separately
   — applied, accepted-but-inert, and rejected with its reason — and
   note every sub-schedule acted on more than once.
4. Confirm the activity population is unchanged across the request; a
   disable that reduced it is a defect, not a status change.
5. Combine the resulting sub-schedule flags with the schedule's own
   enabled state to give the effective release gate per sub-schedule.
6. Over the arc swept since the gate shut, list the release points that
   passed unreleased, and give the remaining arc before each comes
   round again.
7. For every sub-schedule this request just opened, list the activities
   inside the imminent arc ahead of the current position.
8. Report per sub-schedule: the flag, the effective gate and the load
   it holds.

## Pitfalls

- Reading a disable as a delete. The activities are all still there,
  and a ground model that dropped them re-uploads duplicates the moment
  the sub-schedule is enabled.
- Failing a whole status request on one undeclared name. The other
  instructions were applied on board and the ground model diverges.
- Treating an inert instruction as a rejection. It is accepted, and
  re-sending a status request after an uncertain uplink depends on it.
- Assuming a swept release point is gone. On a position-based schedule
  it returns next revolution, which is either the recovery the operator
  wanted or an unplanned release they need to be warned about.
- Enabling a sub-schedule without checking what sits just ahead of the
  current position. An activity a degree away releases before anyone
  can react.
- Reading an enabled flag as proof of release. The schedule gate above
  it can be shut, and both have to be open.
- Resolving a doubled instruction silently. Order decides it, but the
  request almost certainly did not mean both.

## Behavior contract (gate 3)

The status-map and instruction validation, per-instruction apply with
its rejected, inert and superseded outcomes, activity retention, the
two-gate effective status, the swept-arc missed-release census, the
re-arm arcs, the imminent-on-enable warning and the per-sub-schedule
report are exercised by the gate 3 contract test:
scripts/test_e7041_enabling_and_disabling_position_based_sub_schedules.py
against
scripts/e7041_enabling_and_disabling_position_based_sub_schedules_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e7041_enabling_and_disabling_position_based_sub_schedules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
