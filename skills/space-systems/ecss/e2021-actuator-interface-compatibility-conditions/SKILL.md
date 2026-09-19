---
name: e2021-actuator-interface-compatibility-conditions
description: "Determine whether an actuator electronics output and the actuator it drives are compatible, so the firing current lands inside its specified window at every corner, per clause 5.4.1 of ECSS-E-ST-20-21C. Use when a drive voltage tolerance, a source resistance, a harness resistance and an actuator resistance spread have to become a verdict rather than a nominal sum: build the high-current corner from the highest drive voltage against the lowest total loop resistance and the low-current corner the other way round, compare each against the interface floor and ceiling, and return the drive voltage band that would close a violated corner. Trigger: ecss, e-st-20-21c, actuator-interface-compatibility, firing-current-window, actuator-resistance-spread, loop-resistance-corner, drive-voltage-tolerance, actuator-source-resistance."
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
  tags: [ecss, e-st-20-21-actuator-interface-scope, e-st-20-21c-clause-5-4-1, e2021-actuator-interface-compatibility-conditions, e-st-20-21c, actuator-interface-compatibility, firing-current-window, actuator-resistance-spread, loop-resistance-corner, drive-voltage-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Actuator Interface — Compatibility Conditions (space-systems/ecss/e2021-actuator-interface-compatibility-conditions)

Use when the task is clause 5.4.1 of ECSS-E-ST-20-21C: the output of an
actuator electronics and the actuator wired to it have to be shown
compatible, which means the current that flows when the line fires sits
inside the window the interface specifies. This leaf reads one drive
line and returns the verdict taken at the two corners that decide it.

## Domain quick reference

- The firing current belongs to a loop, not to the actuator. The drive
  voltage divides across the source resistance inside the electronics,
  the harness between the two boxes, and the actuator itself, so all
  three spreads move the current and all three have to be declared.
- Compatibility is a two-corner statement. The high-current corner is
  the highest drive voltage the supply tolerance permits against the
  lowest total loop resistance; the low-current corner is the lowest
  drive voltage against the highest total loop resistance. Nothing in
  between needs checking, because the current is monotone in both.
- The nominal sum is the number that hides the problem. It sits between
  the two corners by construction, so a line whose corners both fall
  outside the window still reports a comfortable nominal current, and a
  design reviewed on that figure alone is not reviewed at all.
- The window has two different reasons behind its two ends. The floor is
  what the actuator needs in order to function at all; the ceiling is
  what the interface is allowed to present, and it protects the harness,
  the return path and anything sharing them.
- A violated corner has a constructive answer rather than a verdict
  only. Making the low corner reach the floor fixes a lowest admissible
  drive voltage; keeping the high corner under the ceiling fixes a
  highest admissible one. Those two bound a band the supply can be
  specified into.
- When the lowest admissible drive voltage rises above the highest, the
  resistance spread itself is too wide for the window and no supply
  closes the case. That result points at the actuator tolerance, the
  harness budget or the source resistance, not at the power supply.

## Workflow

1. Validate the drive line: a drive voltage band whose lower end is
   positive and whose upper end is not below it, plus three resistance
   bands, each non-negative and each with its maximum at or above its
   minimum.
2. Form the two loop resistances -- the sum of the three minima and the
   sum of the three maxima -- and refuse a loop that sums to zero rather
   than dividing by it.
3. Compute the high-current corner and the low-current corner from those
   loops and the two ends of the drive voltage band.
4. Compare the low corner against the floor and the high corner against
   the ceiling, absorbing floating-point representation error at an
   exact match with a named tolerance rather than by widening either
   limit.
5. Report each violated corner with the amount it misses by, in ampere,
   so the shortfall can be traded against a resistance change or a
   supply change.
6. Derive the admissible drive voltage band from the two loops and the
   two current limits, and mark it infeasible when its lower end passes
   its upper end.
7. Grade a set of lines on the one holding the least headroom to either
   limit, and return the finding list with the compatibility token.

## Pitfalls

- Sizing the line on the nominal resistance and the nominal supply. The
  result always lands inside the window when the corners straddle it, so
  the check passes precisely on the designs that need it.
- Pairing the corners the natural-looking way. The high-current case is
  the high voltage with the low resistance; taking the high voltage with
  the high resistance mixes a worst case with a best case and reports a
  current that no unit ever draws.
- Leaving the source resistance of the electronics out of the loop. On a
  low-resistance actuator it is a large fraction of the total, and
  omitting it overstates the current at exactly the corner the ceiling
  is protecting against.
- Treating the floor as the only requirement. An overdriven line passes
  every functional firing test and still violates the interface, because
  the ceiling is there for the harness and the return path rather than
  for the actuator.
- Answering an infeasible spread by raising the supply. When no drive
  voltage satisfies both corners, the spread is the defect; a higher
  supply moves the high corner further out while it pulls the low corner
  in.

## Behavior contract (gate 3)

The line validation, loop formation, corner currents, window comparison,
shortfall reporting, admissible drive band and worst-line grading are
exercised by the gate 3 contract test:
scripts/test_e2021_actuator_interface_compatibility_conditions.py against
scripts/e2021_actuator_interface_compatibility_conditions_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2021_actuator_interface_compatibility_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
