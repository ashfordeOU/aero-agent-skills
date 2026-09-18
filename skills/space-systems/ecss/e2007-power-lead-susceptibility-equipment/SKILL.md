---
name: e2007-power-lead-susceptibility-equipment
description: "Verify the injection chain for a power-lead conducted susceptibility test. Use when the task is ECSS-E-ST-20-07C clause 5.4.7.2 and a bench inventory of generator, power amplifier and low-inductance series resistor must be judged fit to drive a disturbance onto the supply leads: confirm the generator and the amplifier span the required band, derive the drive power the amplifier has to deliver into the lead impedance once path loss and headroom are added as decibels, hold that against its rated output, and keep the series resistor inside its reactance-to-resistance ratio at the top frequency and inside its derated dissipation at the lead current. Refuses a duplicated role, an unknown item key and a band declared backwards. Trigger: ecss, e-st-20-07c, power-lead-susceptibility-equipment, conducted-susceptibility-injection-chain, low-inductance-series-resistor, amplifier-drive-power, generator-band-coverage, resistor-reactance-ratio, injection-resistor-derating."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-power-lead-susceptibility-equipment, conducted-susceptibility-injection-chain, low-inductance-series-resistor, amplifier-drive-power, generator-band-coverage, resistor-reactance-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Power-Lead Susceptibility Injection Equipment (space-systems/ecss/e2007-power-lead-susceptibility-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause 5.4.7.2
-- the generator, the power amplifier and the low-inductance series
resistor that together put a conducted disturbance onto the supply leads
of a unit, and the question of whether the items on the bench can actually
deliver the injection the test requires.

## Domain quick reference

- The chain carries three roles and each is filled once. A generator sets
  the frequency, an amplifier raises it to a usable level, and a series
  resistor of very low residual inductance couples it into the supply
  lead. Two amplifiers on the bench is an inventory error, not a spare.
- The amplifier is sized from the delivered power, not from the wanted
  voltage alone. The wanted injected voltage across the lead impedance
  fixes the power that has to arrive there; the loss of the injection
  path and the test headroom are then added to it as decibels, because
  both are ratios and neither is a number of watts.
- Headroom exists so the amplifier is never driven at its compression
  point, where the injected waveform stops being the waveform that was
  asked for. It is part of the sizing, not a comfort factor to drop when
  an amplifier is nearly big enough.
- The series element is a resistor only while it behaves as one. Its
  residual inductance shows a reactance that rises with frequency, so the
  item is judged at the TOP of the band: the ratio of that reactance to
  its resistance has to stay small there, and a part that looks ideal at
  the bottom of the band can be useless at the top.
- The same resistor sits in the live supply lead and carries the whole
  lead current for the length of the run. Its dissipation is the square
  of that current times its resistance, and it is held to a derated
  fraction of its rating, not to the rating on the label.
- Band coverage is judged against the band the injection is required to
  cover, not against a nominal catalogue span. A generator that stops
  short at either end leaves a stretch of the band with nothing that can
  be tuned to it, and that stretch is reported as an uncovered range.
- A bound met exactly is met. A ratio or a decibel conversion can land a
  few units in the last place outside an exactly-met bound; absorb that
  in the comparison, never by widening the bound.

## Workflow

1. Normalize each inventory item: identifier, role, and the numbers that
   role carries. Reject an unknown role, an unknown or missing key, a
   blank identifier, a non-numeric or non-finite value, and a tuning span
   whose upper end does not exceed its lower end.
2. Reject a duplicated identifier and a role that appears twice; report a
   role that appears not at all as a finding, so a partly assembled bench
   still produces a usable report.
3. Normalize the requirement: the band to be covered, the wanted injected
   voltage, the lead impedance, the path loss, the headroom and the lead
   current.
4. Derive the drive power: convert the wanted voltage and the lead
   impedance into a delivered power, then raise it by the sum of the path
   loss and the headroom expressed in decibels.
5. Check the amplifier rating against that drive power and report the
   margin in decibels, negative when the amplifier is short.
6. Check the generator span, and the amplifier span, against the required
   band; report each end that falls short as an uncovered range.
7. Check the series resistor twice: reactance-to-resistance ratio at the
   top of the required band, and dissipation at the lead current against
   the derated rating.
8. Aggregate: the chain is ready only when no finding remains.

## Pitfalls

- Sizing the amplifier from the wanted voltage and forgetting that the
  path loss and the headroom are decibels on top of the delivered power,
  which understates the rating needed by a factor, not by a few percent.
- Judging the series resistor at the bottom of the band, where its
  residual inductance shows almost no reactance -- the ratio that matters
  is the one at the top frequency the injection has to reach.
- Reading the resistor power rating off the label and ignoring the
  derating, then losing it part-way through a long run.
- Treating a second amplifier on the bench as a spare rather than an
  inventory error: the chain is defined by one item per role, and a
  duplicate leaves the report unable to say which item was used.
- Accepting a generator whose catalogue span is wide but whose ends fall
  inside the required band, so a stretch of frequencies has nothing that
  can be tuned to it.
- Widening a ratio or a power bound to make a borderline item conform,
  rather than absorbing the representation error of the comparison.

## Behavior contract (gate 3)

The drive-power derivation, the amplifier margin, the generator and
amplifier span coverage, the series-resistor reactance ratio and derated
dissipation, the item and requirement validation and the whole-chain
readiness verdict are exercised by the gate 3 contract test:
scripts/test_e2007_power_lead_susceptibility_equipment.py against
scripts/e2007_power_lead_susceptibility_equipment_logic.py (stdlib
unittest, offline). Run:

python3 scripts/test_e2007_power_lead_susceptibility_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
