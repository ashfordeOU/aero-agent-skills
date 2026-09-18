---
name: e2007-radiated-magnetic-susceptibility-equipment
description: "Assess the field-generating chain a radiated magnetic susceptibility run is built from under ECSS-E-ST-20-07C clause 5.4.10.2: confirm a signal source, a power amplifier and a radiating loop are all present and in date, intersect their frequency coverage with the required exposure band and report every uncovered sub-band, size the loop from its diameter and turn count, derive the loop current that reaches the wanted flux density at the stated standoff, convert it to a drive level through the loop impedance at the worst-case tune frequency, and compare the gain and the output ceiling the amplifier must supply with the ones it has. Use when assembling or auditing a magnetic susceptibility bench before the loop is placed. Trigger: ecss, e-st-20-07c, radiated-magnetic-susceptibility-equipment, magnetic-field-radiating-loop, loop-turns-area-product, magnetic-susceptibility-power-amplifier, magnetic-loop-drive-current, exposure-band-instrument-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-magnetic-susceptibility-equipment, radiated-magnetic-susceptibility-equipment, magnetic-field-radiating-loop, loop-turns-area-product, magnetic-susceptibility-power-amplifier, magnetic-loop-drive-current, exposure-band-instrument-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Magnetic Susceptibility Equipment (space-systems/ecss/e2007-radiated-magnetic-susceptibility-equipment)

Use when the task is the field-generating list of ECSS-E-ST-20-07C clause
5.4.10.2 -- deciding whether the signal source, the power amplifier and
the radiating loop on hand can actually raise the required magnetic flux
density across the whole exposure band, and naming what is short when
they cannot.

## Domain quick reference

- The clause names three roles, not three boxes. A bench carrying two
  generators and no loop is not a chain, and an amplifier without a loop
  cannot be system verified at all. Readiness is decided per role, and an
  absent role is a finding rather than a detail to be worked around.
- Coverage is an intersection, never a union. The usable exposure band is
  the overlap of the source, the amplifier and the loop coverages with
  the required band; the chain is exactly as wide as its narrowest
  member, so an amplifier reaching far above the band buys nothing once
  the loop self-resonates below it.
- Report the shortfall as a frequency interval, not as a percentage. A
  chain covering most of a decade-wide band can still be blind across the
  sub-band a converter's switching fundamental sits in, and only the
  interval says so.
- The loop is one figure, not two. Diameter and turn count enter through
  their product, the turns-area, so a small many-turn loop and a large
  few-turn loop can be interchangeable on coupling while behaving nothing
  alike on impedance.
- Flux density falls off steeply with standoff. The on-axis field goes as
  the loop radius squared over the radius-and-standoff distance cubed, so
  a loop held a few centimetres further back needs several times the
  current for the same exposure.
- Drive is a level, not a current. The loop presents its winding
  resistance in series with its reactance, and the reactance dominates at
  the top of the band; the drive level therefore has to be derived at the
  worst-case tune frequency, not at the bottom one.
- The amplifier is graded twice, on gain and on output ceiling. A part
  with ample gain and a low ceiling clips before the wanted field is
  reached, and the run then exposes the unit to a distorted waveform
  rather than the tone the record claims.
- The loop also has a current rating. Driving more current than the
  winding takes overheats it and drifts the field mid-sweep, so the rated
  current is compared against the current the wanted field demands.
- Calibration currency is part of the equipment list. A lapsed
  calibration is a finding; one about to lapse before the campaign ends
  is a limitation to be carried, not silently ignored.

## Workflow

1. Normalize every equipment record to one of the three recognized roles
   and reject an unrecognized role or a role appearing twice.
2. Validate each record: positive, ordered frequency edges, a calibration
   figure, plus a whole turn count, diameter, winding resistance,
   inductance and current rating on the loop, and gain and output ceiling
   on the amplifier.
3. List the absent roles. Without all three, stop at incomplete rather
   than grading a coverage that cannot be raised.
4. Intersect the three coverages with the required exposure band, express
   the result in decades, and reduce the leftovers to explicit uncovered
   sub-bands.
5. Attribute the loss: the item removing the most decades from the band
   is the limiting one, with ties resolved in the clause's own role order
   so the answer is stable.
6. Size the loop, derive the current the wanted flux density needs at the
   standoff, and compare it with the loop current rating.
7. Convert that current to a drive level through the loop impedance at
   the worst-case tune frequency, then grade the amplifier gain and
   ceiling against it and keep the headroom.
8. Aggregate the findings and the limitations. The chain is ready only
   when no finding stands.

## Pitfalls

- Adding the coverages together instead of intersecting them, so a wide
  amplifier hides a loop that stops a decade short.
- Treating a missing role as recoverable and grading the coverage of the
  two items that did turn up.
- Quoting coverage as a percentage of the band. The uncovered interval is
  what a reviewer needs; the percentage hides where the blindness sits.
- Reading the loop by diameter alone and swapping in a loop of the same
  size with half the turns, which halves the field for the same current.
- Deriving the drive level at the bottom of the band, where the winding
  looks resistive, then finding the amplifier starved at the top where
  the reactance dominates.
- Grading the amplifier on gain alone. Gain gets the level there; the
  output ceiling decides whether it arrives undistorted.
- Ignoring the standoff the loop is actually held at, so a field computed
  for contact is credited to a run taken several centimetres back.
- Carrying an item whose calibration lapses mid-campaign without
  recording it, then having the whole exposure set questioned afterwards.

## Behavior contract (gate 3)

The role normalization, equipment validation, band-intersection coverage,
limiting-item attribution, turns-area and on-axis flux-density geometry,
loop-current and drive-level derivation and readiness aggregation logic
is exercised by the gate 3 contract test:
scripts/test_e2007_radiated_magnetic_susceptibility_equipment.py against
scripts/e2007_radiated_magnetic_susceptibility_equipment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_magnetic_susceptibility_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
