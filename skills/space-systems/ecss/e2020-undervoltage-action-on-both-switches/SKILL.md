---
name: e2020-undervoltage-action-on-both-switches
description: "Verify that an undervoltage protection opens both the main switch and the extra switch of a current limiter, each through a memory cell of its own, under clause 5.2.13.5.1 of ECSS-E-ST-20-20C. Use when one detection chain has to latch two series switches off and the two command paths share parts. Walk each path element by element, confirm every switch holds its open state in its own cell, name any memory or drive element the two paths hold in common, and run a single failure walk reporting which switches stay closed. Trigger: ecss, e-st-20-20c, undervoltage-opens-both-switches, main-and-extra-switch-opening, independent-undervoltage-memory-cell, shared-undervoltage-memory-cell, undervoltage-off-command-path, limiter-extra-switch-latch."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-undervoltage-action-on-both-switches, undervoltage-opens-both-switches, main-and-extra-switch-opening, independent-undervoltage-memory-cell, shared-undervoltage-memory-cell, undervoltage-off-command-path, limiter-extra-switch-latch]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Undervoltage Action on Both Switches (space-systems/ecss/e2020-undervoltage-action-on-both-switches)

Use when the task is clause 5.2.13.5.1 of ECSS-E-ST-20-20C: the undervoltage
protection of a current limiter has to open the main switch and the extra
switch, and each open state has to be held by a memory cell of its own. This
leaf takes the two command paths and walks them element by element.

## Domain quick reference

- The clause names two switches because the limiter has two. The extra switch
  exists so that the output can still be removed when the main switch has
  failed; an undervoltage action that opens only the main switch leaves the
  one device that was supposed to cover that failure closed.
- A command is not a state. The undervoltage detection raises an off command
  for as long as the bus is low, and a bus that recovers — because the load
  was just removed — drops it again. Only a memory cell keeps the switch off
  afterwards, so a path with no cell in it gives an oscillation, not a trip.
- Each switch needs its own cell. Two switches latched by one cell open
  together and, more to the point, stay closed together when that cell fails
  or is reset, which is the arrangement the separate extra switch was meant
  to avoid.
- The drive stage behind the cells counts. Two independent memory cells that
  reach the switches through one driver put both switches behind one part
  again, and the walk has to reach past the cells to see it.
- A shared detection element is normal and is graded elsewhere. One
  undervoltage sensing function serving both paths is the expected design;
  whether that function is itself single failure tolerant belongs to the
  shared-protection clause, so this leaf reports it and does not double-count
  it as a defect here.
- Conformance is per switch, not per unit. The report names the role whose
  path is broken, because "the protection works" is true of a unit where only
  the main switch ever opens.

## Workflow

1. Validate the architecture: a named unit, exactly one main and one extra
   switch, a non-empty command path per switch, and elements that declare a
   known kind consistently across both paths.
2. Confirm the action reaches both switches with nothing failed.
3. Check each path for a memory cell and check that every cell it holds is
   declared to hold its state; a path with no cell, or with a cell that
   releases, is a finding against that switch by name.
4. Collect the elements the two paths hold in common and split them by kind:
   a shared memory or drive element is a finding, a shared detection element
   is a note.
5. Walk each distinct element as a single failure and record which switch
   roles stay closed; elements that block both roles are the common mode
   list.
6. Return the verdict: conformant only when both switches are reached, both
   hold their open state, and no memory or drive element is common.

## Pitfalls

- Reading "the protection opens the limiter" as one action. It is two, and a
  design that latches only the main switch passes every functional test on a
  healthy unit while failing the case the clause exists for.
- Accepting a combinational off path with no memory in it. It removes the
  load, the bus recovers, the command drops and the switch closes back into
  the same fault; the trip has to be held, not merely issued.
- Counting two cells as independent because they carry different part
  numbers. Independence is about what they share downstream, and a common
  driver, gate resistor or opto behind them makes the pair one item again.
- Treating the shared undervoltage detection as this clause's defect. It is a
  single point of the detection function and it is real, but it is graded by
  the shared-protection clause; report it and keep the memory finding clean.
- Letting a reset line leak between the cells. A cell that another path can
  clear is not holding its own state, and it is reported through the same
  holds-state check rather than assumed away.
- Averaging the walk into one pass or fail. The report names the element and
  the roles it blocks, because a point that closes one switch and a point
  that closes both are different findings.

## Behavior contract (gate 3)

The architecture validation, path and memory-cell lookup, open-state holding
check, command reachability, shared-element split by kind, single failure
walk, common-mode collection and verdict are exercised by the gate 3 contract
test: scripts/test_e2020_undervoltage_action_on_both_switches.py against
scripts/e2020_undervoltage_action_on_both_switches_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_undervoltage_action_on_both_switches.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
