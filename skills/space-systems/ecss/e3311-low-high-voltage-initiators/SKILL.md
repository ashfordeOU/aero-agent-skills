---
name: e3311-low-high-voltage-initiators
description: "Verify low-voltage and high-voltage initiator properties against ECSS-E-ST-33-11C clause 4.11.2, tables 4-4 and 4-5. Use when the task is grading a bridgewire device on its no-fire current floor, its all-fire current ceiling, the ratio between them, the bridge-resistance band and the electrostatic withstand declared separately pin-to-pin and pin-to-case, or grading an exploding-bridge device on no-fire voltage, all-fire energy, the energy separation ratio and whether its firing set actually delivers the all-fire energy with margin from the capacitance and voltage it charges to. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, low-voltage-bridgewire-initiator, high-voltage-exploding-bridgewire-initiator, initiator-no-fire-all-fire-separation, initiator-bridge-resistance-band, initiator-esd-withstand-per-path, eb-firing-set-energy-margin."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-low-high-voltage-initiators, low-voltage-bridgewire-initiator, high-voltage-exploding-bridgewire-initiator, initiator-no-fire-all-fire-separation, initiator-bridge-resistance-band, initiator-esd-withstand-per-path, eb-firing-set-energy-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Low- and High-Voltage Initiators (space-systems/ecss/e3311-low-high-voltage-initiators)

Use when the task is clause 4.11.2 of ECSS-E-ST-33-11C for the two
electrically initiated families -- a bridgewire heated by a current
and a bridge or foil exploded by depositing energy fast. Two property
tables, and one mistake that runs through both: grading the wrong
family's properties because the device was sorted by its connector
rather than by how it initiates.

## Domain quick reference

- The low-voltage table is written in currents and a resistance. The
  no-fire current is a floor -- a device below it is more sensitive
  than the subsystem was designed around. The all-fire current is a
  ceiling -- a device above it asks the firing circuit for more than
  the circuit was specified to deliver. The two limits therefore fail
  for opposite reasons and cannot be combined.
- The separation between no-fire and all-fire is the safety case, and
  it is a ratio. A device can satisfy both the floor and the ceiling
  and still leave too little room between them, which is the case a
  table read row by row never surfaces.
- The bridge-resistance band is a batch property rather than a safety
  limit. It exists so the firing circuit sees the load it was sized
  for and so a continuity check can tell a good device from an open
  or a short.
- The high-voltage table replaces currents with a no-fire voltage and
  an all-fire energy, because an exploding bridge is not heated to
  its function point, it is vaporised. Bridge resistance is not a
  meaningful band for it.
- A high-voltage device is graded together with its firing set. The
  energy that matters is what the capacitor actually holds at its
  charge voltage, and a device whose datasheet all-fire energy is
  comfortable can still be driven by a firing set that cannot reach
  it with margin.
- The electrostatic withstand is declared per path for both families.
  Pin-to-case runs through the housing insulation and is routinely
  the weaker of the two, so a single figure quoted for the device
  grades the path that was never the concern.
- A property from the other table is an error rather than surplus
  evidence. It usually means the device was categorized wrongly, and
  the table it was graded against is then the wrong one.

## Workflow

1. Read the category first and resolve the property table it calls
   for. Reject a device that omits a property from its own table or
   carries one from the other.
2. For a low-voltage device: grade the no-fire current against its
   floor, the all-fire current against its ceiling, and then the
   ratio of the two against the required separation. All three are
   separate findings.
3. Grade the bridge resistance against both edges of its band,
   treating a device sitting exactly on an edge as inside it.
4. For a high-voltage device: grade the no-fire voltage and the
   all-fire energy against their limits, then the energy separation
   ratio.
5. Compute the firing-set delivery from its capacitance and charge
   voltage and grade it against the all-fire energy times the
   declared margin.
6. Grade the electrostatic withstand on each path separately and the
   insulation resistance against its floor, for either family.
7. Roll the findings into a device verdict and, for a mixed
   population, into a roll-up that keeps the part name on every
   finding.

## Pitfalls

- Treating the no-fire current as something to stay under. It is the
  level the device tolerates, so in the property table it is a floor
  the device has to reach, not a limit the design has to respect.
  That second reading belongs to the circuit analysis, not here.
- Reading a comfortable floor and a comfortable ceiling as a
  comfortable device. The separation between them is a third check
  and it is the one that carries the safety case.
- Applying the bridge-resistance band to a high-voltage device. It has
  no bridgewire to hold a resistance, and forcing the property means
  the device was put in the wrong family.
- Grading a high-voltage initiator on its datasheet alone. The
  all-fire energy is a property of the device; whether it fires is a
  property of the device and the firing set together.
- Quoting one electrostatic withstand figure for both paths. The
  housing path is the weaker one and the single number almost always
  came from the other.
- Accepting a property from the other table as harmless extra data.
  It is the visible symptom of a device sorted into the wrong family,
  and every other grade on that device is then suspect.
- Failing a ratio that lands a hair under its requirement in the last
  bits of a float. Every separation here is a quotient, so a device
  sized exactly onto its requirement can land just below it; the
  comparison absorbs that while the requirement stays untouched.

## Behavior contract (gate 3)

The per-category property tables, the no-fire floor and all-fire
ceiling, the separation ratios, the bridge-resistance band, the
firing-set energy computation and margin, the per-path electrostatic
withstand, the insulation floor, the category dispatch and the
population roll-up are exercised by the gate 3 contract test:
scripts/test_e3311_low_high_voltage_initiators.py against
scripts/e3311_low_high_voltage_initiators_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3311_low_high_voltage_initiators.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
