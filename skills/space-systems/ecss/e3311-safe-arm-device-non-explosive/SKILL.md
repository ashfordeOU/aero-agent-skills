---
name: e3311-safe-arm-device-non-explosive
description: "Assess the functions and interfaces of a non-explosive safe-and-arm device against ECSS-E-ST-33-11C clause 4.10.11. Use when the task is counting how many genuinely independent inhibits sit in the firing path while the device is safe, once inhibits sharing a coil, a ground return or any other common cause have been collapsed into one, and confirming the device interrupts the firing energy, reports its position from the interrupter rather than from the command, safes by hand without primary power, holds state through a power loss, keeps its command and monitor interfaces off the firing-output connector, and arms and safes inside its time and cycle-life limits. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, non-explosive-safe-arm-device, safe-arm-independent-inhibit-count, safe-arm-position-indication, safe-arm-interface-segregation, safe-arm-cycle-life."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-safe-arm-device-non-explosive, non-explosive-safe-arm-device, safe-arm-independent-inhibit-count, safe-arm-position-indication, safe-arm-interface-segregation, safe-arm-cycle-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Non-Explosive Safe-and-Arm Device (space-systems/ecss/e3311-safe-arm-device-non-explosive)

Use when the task is ECSS-E-ST-33-11C clause 4.10.11 -- a safe-and-arm
device with no explosive train to misalign, so everything it does it
does electrically, and the whole safety case reduces to things a
reviewer can count.

## Domain quick reference

- The inhibit count is the heart of the clause, and the word that
  carries it is independent. Two relay contacts driven from one coil,
  or two switches sharing a ground return, are two inhibits on the
  drawing and one inhibit in the failure tree. The number that matters
  is the count of distinct common-cause groups among the inhibits that
  are actually active while the device is safe.
- An inhibit that is not active in the safe state contributes nothing.
  It is part of the firing sequence, not part of the safety case, and
  counting it is how a single-inhibit device passes on paper.
- Position indication is a separate requirement from the interrupt
  itself. An indication derived from the command, or from the current
  in a drive coil, reports the state the device was told to reach. An
  indication read off the interrupter reports the state it is in, and
  the difference is the stuck interrupter nobody hears about.
- Manual safing is specified without primary power on purpose. The
  situation in which somebody needs to safe the device by hand is
  frequently the situation in which the bus is already down.
- The interfaces are declared as five separate things -- command,
  monitor, primary power, firing output, manual safing -- because the
  requirement is about which connector carries which. A command line
  sharing the firing shell turns a harness fault into a firing event.
- Arming time, safing time and qualified cycle life are graded
  together with the operations plan, because a device qualified for
  more cycles than the plan uses is compliant and one qualified for
  fewer is not, whatever the datasheet headline says.

## Workflow

1. Read the inhibit list first. Reject a duplicate identifier and an
   inhibit that does not say whether it is active in the safe state,
   because both silently change the count.
2. Drop the inhibits inactive in safe, then group what remains by
   declared common cause. Each group contributes one; each inhibit
   with no declared group contributes one. Grade that total against
   the required independent count and name every group that collapsed
   two entries into one.
3. Walk the closed function set and name each function absent. An
   undeclared function is rejected rather than assumed.
4. Take the indication source on its own and accept only an
   interrupter-driven one.
5. Read the five interfaces, reject an undeclared one, then compare
   the command and monitor connectors with the firing-output
   connector and raise a finding on any shared shell.
6. Grade arming and safing times against their limits, treating a
   device sitting exactly on a limit as compliant rather than failing
   it on representation error, then compare planned cycles with
   qualified cycles.
7. Close with the overall verdict and the parts that produced it.

## Pitfalls

- Counting inhibits off the schematic. The schematic shows contacts;
  the requirement is about causes. Two contacts on one coil are one
  inhibit, and the leaf will say so only if the common-cause group is
  actually declared, so an undeclared group is a claim, not a fact.
- Counting an inhibit that opens during the arming sequence. The
  question is what is interrupting the firing path while the device is
  safe, not how many interruptions exist anywhere in the design.
- Accepting a commanded-state position indication because the command
  is verified. Verifying the command proves the command was sent. The
  interrupter is the thing that can stick, and it is the thing the
  indication has to be read from.
- Specifying manual safing that needs the primary bus. It is the one
  function most likely to be called on after the bus is gone.
- Putting the monitor return on the firing connector to save a shell.
  The saving is one connector; the cost is a shared failure path
  between a low-level telemetry line and a firing line.
- Reading a generous qualified cycle count without checking the
  operations plan against it. Ground campaigns arm and safe far more
  often than the flight profile suggests, and the count that fails is
  the one nobody added up.
- Failing a device whose arming time lands a hair over its limit in
  the last bits of a float. The limit is untouched; the comparison
  absorbs the representation error.

## Behavior contract (gate 3)

The common-cause inhibit grouping and count, the function walk, the
indication-source rule, the interface segregation check, the timing
and cycle-life limits and the overall verdict are exercised by the
gate 3 contract test:
scripts/test_e3311_safe_arm_device_non_explosive.py against
scripts/e3311_safe_arm_device_non_explosive_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_safe_arm_device_non_explosive.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
