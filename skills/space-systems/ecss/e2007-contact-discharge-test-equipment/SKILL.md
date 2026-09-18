---
name: e2007-contact-discharge-test-equipment
description: "Verify the discharge generator a contact-discharge test names for direct application under ECSS-E-ST-20-07C clause 5.4.14.2: compare the declared storage capacitance and discharge resistance with their nominal values and tolerances, form the time constant they produce and grade it separately because two in-band parts can still miss it, walk the exponential tail through the required waveform points, confirm the charge-voltage range reaches every required level, and bound the charging resistance and the discharge return cable. Use when a contact-discharge bench is specified or reviewed. Trigger: ecss, e-st-20-07c, contact-discharge-test-equipment, contact-discharge-generator-capacitance, contact-discharge-resistance-tolerance, contact-discharge-time-constant, contact-discharge-tail-waveform, contact-discharge-tip-and-return."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-contact-discharge-test-equipment, contact-discharge-generator-capacitance, contact-discharge-resistance-tolerance, contact-discharge-time-constant, contact-discharge-tail-waveform, contact-discharge-tip-and-return]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Contact-Discharge Test Equipment (space-systems/ecss/e2007-contact-discharge-test-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause 5.4.14.2
-- deciding whether the discharge generator offered for direct application
to a unit really delivers the pulse the clause names, before the bench is
accepted rather than after a campaign has to be repeated on a generator
nobody checked.

## Domain quick reference

- The pulse is defined by two parts, not by a voltage. The energy-storage
  capacitance sets how much charge is delivered and the discharge
  resistance sets how fast it leaves; the charge voltage only scales what
  those two shape. A generator at the right voltage with the wrong network
  applies a different event with the same number on the dial.
- The product of the two is the quantity that has to be graded in its own
  right. Capacitance and resistance each carry a tolerance, and a part at
  the top of one band multiplied by a part at the top of the other lands a
  time constant well outside its own band while both parts pass their
  individual checks. Grading the parts and inferring the pulse is the
  defect this leaf exists to catch.
- The tail is an exponential, and the waveform points a requirement names
  are read off it as fractions of the resistance-limited amplitude. That
  amplitude is the charge voltage over the discharge resistance; the much
  faster initial spike belongs to the tip and the arc, not to the named
  network, and is not what these checkpoints grade.
- Direct application is a different arrangement from the indirect one, and
  the tip says which. A rounded tip intended for an air discharge fitted to
  a generator run in contact mode changes where the arc forms and therefore
  what the unit sees, so the fitted tip is part of the equipment check.
- The charging resistance is a safety item, not a performance one. It
  bounds the current an operator can draw from the charged network, and a
  generator that clears every waveform requirement with an inadequate
  charging resistor is still not fit to be used.
- The discharge return cable is part of the circuit. A long return adds
  inductance in series with the named resistance, which slows the front and
  rings the tail, so its length is bounded rather than left to whatever
  reaches the bench.
- Fitness is three-valued. A declared value comfortably inside its band is
  adequate; one sitting near the edge is usable and carried as a limitation
  because the next calibration lands on the other side; one outside is
  inadequate. When several are outside, the one short by the largest factor
  is the one whose replacement changes the answer.

## Workflow

1. Validate the declared generator: storage capacitance, discharge
   resistance, charging resistance, charge-voltage range, fitted tip,
   application mode and return-cable length.
2. Validate the requirement: nominal capacitance and resistance with their
   tolerances, the separate time-constant tolerance, the charging-resistance
   floor, the cable ceiling, the required levels and the waveform
   checkpoints.
3. Grade the capacitance and the resistance against their nominal values,
   then form the time constant from the declared pair and grade it against
   its own tolerance about the nominal product.
4. Grade the charging resistance against its floor and the return cable
   against its ceiling.
5. Walk the exponential tail: at each named delay, form the fraction of the
   amplitude still flowing and compare it with the required fraction inside
   the stated tolerance.
6. Check the arrangement is the direct one and the fitted tip belongs to
   it, then confirm the charge-voltage range reaches every required level.
7. Aggregate: a value outside its band, a missed checkpoint, an indirect
   arrangement, a wrong tip or an unreachable level are findings; a value
   near a band edge is a limitation. Reduce the findings to the governing
   deviation and report the derived time constant, tail amplitude, stored
   energy and transferred charge at the top required level.

## Pitfalls

- Grading capacitance and resistance separately and calling the pulse
  correct. Two parts inside their own bands can put the time constant well
  outside its band, and the delivered event is the time constant.
- Reading the tail amplitude as the peak the datasheet quotes. The quoted
  peak is the fast front the tip and the arc produce; the checkpoints in a
  requirement sit on the resistance-limited tail and are a different number.
- Accepting a generator on its voltage range alone. The range only says the
  dial reaches the level; what arrives is set by the network behind it.
- Leaving the fitted tip out of the equipment check because it is an
  accessory. An air tip in contact mode moves the arc and changes what the
  unit is subjected to.
- Treating the charging resistance as a performance parameter to be traded.
  It bounds what an operator can draw from a charged network, and no
  waveform result buys it back.
- Using whatever return cable reaches the bench. Its inductance is in
  series with the named resistance and it reshapes the pulse the clause
  defined.
- Reporting the first out-of-band item found. Another may be out by a far
  larger factor and is the one that actually has to be changed.

## Behavior contract (gate 3)

The generator and requirement validation, capacitance, resistance and
time-constant grading, floor and ceiling grading, exponential tail
checkpoints, voltage-range coverage, tip and application-mode checks and
the governing-deviation reduction are exercised by the gate 3 contract
test: scripts/test_e2007_contact_discharge_test_equipment.py against
scripts/e2007_contact_discharge_test_equipment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_contact_discharge_test_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
