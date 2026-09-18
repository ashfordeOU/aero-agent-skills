---
name: e2007-indirect-discharge-test-equipment
description: "Determine whether the high-voltage supply and discharge generator primary circuit declared for an ECSS-E-ST-20-07C clause 5.4.12.2 indirect discharge run can deliver the exposure: derive the stored energy, the first peak current, the network decay constant, the recharge time the charging resistor imposes and the repetition rate that leaves, size the supply ceiling and the electrode holdoff from the severity level, bound the regulation error and the network tolerance, compare each declared item with its requirement, categorize every one as adequate, marginal or inadequate, and name the governing shortfall. Use when an indirect discharge generator bench is assembled or reviewed. Trigger: ecss, e-st-20-07c, indirect-discharge-test-equipment, esd-generator-primary-circuit, indirect-discharge-storage-capacitor, indirect-discharge-first-peak-current, indirect-discharge-recharge-interval, esd-supply-regulation-tolerance."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-indirect-discharge-test-equipment, esd-generator-primary-circuit, indirect-discharge-storage-capacitor, indirect-discharge-first-peak-current, indirect-discharge-recharge-interval, esd-supply-regulation-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Indirect Discharge Test Equipment (space-systems/ecss/e2007-indirect-discharge-test-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause
5.4.12.2 -- deciding whether the high-voltage supply, the discharge
generator and the primary circuit declared for an indirect discharge
exposure can actually produce the event at the severity level and the
repetition the run calls for, before the bench is built rather than
after a sequence turns out to be under-charged.

## Domain quick reference

- The primary circuit is two components and everything follows from
  them. The energy-storage capacitor and the charge voltage set the
  energy that is committed to the event; the discharge resistor and the
  same voltage set the current at the instant the switch closes. Neither
  number can be traded against the other after the fact.
- The supply is sized from the severity level plus headroom, never from
  the level itself. A supply whose ceiling equals the level has no room
  left for its own regulation error, so half the discharges land under
  the level and the exposure is quietly softer than the report says.
- Regulation is a separate requirement from ceiling and the one that is
  usually left undeclared. A generous ceiling with a loose regulation
  delivers a spread of energies, and the peak that matters is then a
  property of the supply rather than of the method.
- Component tolerance is graded against the nominal network, not against
  a catalogue value. A capacitor or resistor several tens of a percent
  away from nominal changes the decay constant and the first peak
  together, so the waveform is no longer the one the method defines.
- Repetition is a charging-circuit property. The capacitor comes back up
  through the charging resistor on an exponential, so the interval
  between discharges has to exceed the time that recharge takes to reach
  a defined fraction. Too large a charging resistor makes every discharge
  after the first one smaller than the first.
- The switch and electrode have to stand off more than the charge
  voltage. A hold-off sized at the level fires when it chooses, and the
  sequence then contains events nobody commanded.
- Fitness is three-valued. A capability comfortably past its requirement
  is adequate; one sitting on the requirement is usable but carried as a
  limitation, because instrument figures are typical rather than
  guaranteed; one short of it is inadequate.
- When several items are short, the governing one is short by the
  largest factor, not the first one listed. That is the item whose
  replacement changes the answer.

## Workflow

1. Validate the exposure: a recognized generator mode, a positive
   severity level and discharge interval, and positive nominal values
   for the capacitor and the discharge resistor of the network.
2. Normalize the declared inventory, refusing an unrecognized item and a
   second declaration of the same item, and record every required item
   nobody declared.
3. Derive the requirements: the supply ceiling and the electrode
   hold-off from the severity level and their headroom, the regulation
   limit, the network tolerance, and the charging-resistance ceiling
   from the discharge interval and the capacitor.
4. Derive what the declared circuit produces: stored energy, first peak
   current, network decay constant, recharge time and the repetition
   rate that recharge time allows.
5. Compare each declared quantity with its requirement in the right
   sense -- a floor for the supply ceiling and the hold-off, a ceiling
   for regulation, tolerance and charging resistance -- and categorize it
   adequate, marginal or inadequate.
6. Reduce the inadequate checks to the governing shortfall and aggregate
   findings and limitations. The bench is fit only when no finding
   stands.

## Pitfalls

- Sizing the supply on the severity level exactly, then discovering the
  regulation error sits underneath it for half the sequence.
- Declaring the ceiling and never the regulation, so the spread of
  delivered energies is invisible in the record.
- Choosing the storage capacitor on its voltage rating alone. Its value
  is what sets the energy and, with the discharge resistor, the decay,
  and a part well outside nominal changes both together.
- Setting the repetition interval from how fast the operator can press
  the button. The charging resistor and the capacitor set it, and a
  sequence run faster than that reports the first discharge and then a
  series of smaller ones.
- Reading an air discharge as equivalent to a contact one. It is usable,
  but approach speed and humidity enter the delivered waveform, and that
  belongs in the report as a limitation.
- Reporting the first inadequate item found, when another item is short
  by a far larger factor and is what actually has to change.
- Treating a capability that exactly equals its requirement as headroom.

## Behavior contract (gate 3)

The exposure validation, inventory normalization, stored energy, first
peak current, decay constant, recharge time and repetition rate
derivation, supply, hold-off, regulation, tolerance and charging
resistance requirements, floor and ceiling categorization and the
governing-shortfall reduction are exercised by the gate 3 contract test:
scripts/test_e2007_indirect_discharge_test_equipment.py against
scripts/e2007_indirect_discharge_test_equipment_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_indirect_discharge_test_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
