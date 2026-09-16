---
name: q6013-class-3-programmable-devices
description: "Use when a lowest-class parts list carries a programmable part. Assess whether the programming record of a programmable device carries the controls the lowest assurance class of ECSS-Q-ST-60-13C clause 6.6.4 asks for: group the declared family into one time, reprogrammable non-volatile or reprogrammable volatile, derive the control set that category owes, name every required control the record leaves open, refuse a readback that does not reproduce the declared pattern, compare the devices verified against the batch floor, and compare programming operations spent against the derated endurance budget, an exact landing counted as met. Trigger: ecss, q-st-60-13c-clause-6-6-4, class-three-programming-controls, programming-pattern-readback-verification, programming-batch-verification-coverage, programming-endurance-derating-budget, open-programming-control-record."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-programmable-devices, class-three-programming-controls, programming-pattern-readback-verification, programming-batch-verification-coverage, programming-endurance-derating-budget, open-programming-control-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Programmable Devices (space-systems/ecss/q6013-class-3-programmable-devices)

Use when the task is clause 6.6.4 of ECSS-Q-ST-60-13C at the lowest assurance
class: a commercial parts list carries a programmable device, a programming
operation has been recorded for it, and the question is which controls that
device actually owed and which of them the record left open.

## Domain quick reference

- At the lowest class the programming record is the assurance evidence. There
  is no lot acceptance behind it and no qualification history in front of it,
  so a control missing from the record is not a paperwork gap, it is the only
  place that control would ever have been demonstrated.
- The category, not the part number, decides the control set. A part that
  cannot be erased owes a blank verification before the pattern goes in; a
  part that can be erased owes an erase verification and a count of what it
  has already spent; a part that loses its pattern at power-down owes a load
  path that can be trusted every time the power comes back.
- A pattern identity and a readback are one control, not two halves of a
  preference. Without the identity there is nothing to compare the readback
  against; without the readback the identity is a label on an unverified part.
- The verification floor is not the same for every category. A device that
  cannot be reprogrammed is scrap when it is wrong, so nothing short of the
  whole batch is meaningful there; a volatile part is reloaded every power-up
  and a sample carries the argument.
- Programming endurance is spent, not owned. The rated cycle count is a
  manufacturer figure at a manufacturer condition, so a lowest-class programme
  works to a derated share of it and treats the remainder as the budget the
  device has left.
- An open control that the programme itself declared advisory is a different
  outcome from an open mandatory control. The first is a condition recorded
  against the build; the second leaves the operation undemonstrated.

## Workflow

1. Validate the record: a reference, a declared family, the controls actually
   performed, the pattern identity, the declared and read-back patterns, the
   batch size and the devices verified.
2. Group the family into one of the three categories, refusing a family that
   is not in the recognised set rather than defaulting it to the mildest one.
3. Derive the required control set: the controls every operation owes plus the
   ones the category adds, and name the required controls left open.
4. Compare the read-back pattern with the declared one and confirm a pattern
   identity exists to compare against.
5. Compute the share of the batch verified device by device and compare it
   with the floor the category carries.
6. For a reprogrammable device, derate the rated endurance by its declared
   fraction and compare the operations already spent with that budget through
   a named tolerance; for a one time device, treat a second operation as a
   finding in its own right.
7. Return one verdict in precedence order: an unverified pattern, an open
   mandatory control or a coverage or budget shortfall, an open advisory
   control, otherwise an accepted record. Report every open control.

## Pitfalls

- Reading the lowest class as permission to skip the programming controls.
  The class removes the screening behind the device, which makes the
  programming record more load-bearing, not less.
- Choosing controls from the part number. Two devices with the same pin count
  can sit in different categories, and the control set follows the category.
- Recording a readback with no pattern identity. A readback that matches
  nothing in particular demonstrates that the programmer read what it wrote,
  which was never the question.
- Applying one verification floor to every category. Verifying a quarter of a
  one time batch leaves three quarters of an unrecoverable operation
  unchecked; verifying the whole of a volatile batch spends effort on a
  pattern that is reloaded at every power-up anyway.
- Working to the rated endurance figure. It is a manufacturer number at a
  manufacturer condition, and a lowest-class build that spends all of it has
  no margin left for the reprogramming the integration phase will ask for.
- Treating an open advisory control and an open mandatory control alike.
  Collapsing the two either blocks a build that was acceptable with a record
  or lets an undemonstrated operation through as a note.

## Behavior contract (gate 3)

The family grouping, control-set derivation, open-control listing, pattern
identity and readback comparison, per-category verification floor, derated
endurance budget, exact-landing tolerance and verdict precedence are exercised
by the gate 3 contract test:
scripts/test_q6013_class_3_programmable_devices.py against
scripts/q6013_class_3_programmable_devices_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_programmable_devices.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
