---
name: e3311-laser-mechanical-initiators-packaged-charges
description: "Evaluate laser initiator, mechanical initiator and packaged-charge properties against ECSS-E-ST-33-11C clause 4.11.2, tables 4-6, 4-7 and 4-8. Use when the task is working an optical budget so the energy that survives the fibre path, not the energy the laser produces, is graded against the all-fire energy with margin while the continuous monitor beam stays below the no-fire power, or computing firing-pin work as force through stroke and accidental drop energy from mass and height against the no-fire impact level, or grading an assembled charge on explosive mass tolerance, delivered output with margin and autoignition separation. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, laser-initiator-optical-budget, laser-initiator-no-fire-power, mechanical-percussion-initiator-energy, initiator-drop-impact-no-fire, packaged-charge-mass-tolerance, packaged-charge-output-margin."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-laser-mechanical-initiators-packaged-charges, laser-initiator-optical-budget, laser-initiator-no-fire-power, mechanical-percussion-initiator-energy, initiator-drop-impact-no-fire, packaged-charge-mass-tolerance, packaged-charge-output-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Laser, Mechanical and Packaged-Charge Properties (space-systems/ecss/e3311-laser-mechanical-initiators-packaged-charges)

Use when the task is clause 4.11.2 of ECSS-E-ST-33-11C for the three
families that are not electrically bridged -- a laser initiator, a
percussion initiator and an assembled packaged charge. They share a
clause and nothing else, except the one property that makes all three
awkward: the number on the datasheet is not the number that reaches
the explosive.

## Domain quick reference

- For a laser initiator the firing energy is generated somewhere else
  and arrives through fibre with connectors in it. The quantity to
  grade is the source energy reduced by the whole loss budget, so the
  budget has to be summed before anything is compared. An energy
  margin computed on the source energy is a margin on a number the
  device never sees.
- The same loss applies to the continuous monitor or alignment beam,
  and that path is graded the opposite way: what reaches the device
  has to stay a declared ratio below the no-fire power. One optical
  budget, two requirements pulling in opposite directions.
- Wavelength is a separate check and not a detail. A device is
  characterised in a band; outside it the absorption of the pyrotechnic
  is simply unknown, so no margin computed there means anything.
- For a mechanical initiator the firing energy is work: force through
  stroke. It is computed rather than quoted, because the two
  quantities are what the designer controls and the product is what
  the device responds to.
- The no-fire side of a mechanical device is an accidental drop, and
  the energy it puts in is computed from the handling mass and the
  height rather than taken from a handling procedure. That keeps the
  requirement attached to what can physically happen rather than to
  what the procedure forbids.
- A packaged charge is graded on three unrelated things: whether the
  explosive mass landed inside its tolerance band, whether the output
  it produces clears what the function needs with margin, and whether
  autoignition stands clear of the maximum operating temperature.
- The output requirement carries a margin for the same reason the
  energy requirements do. A charge that exactly meets the function
  need has nothing left for a cold day, an aged charge or a
  worst-case gap.

## Workflow

1. Take the device kind first and dispatch onto its table. A device
   graded against the wrong table produces numbers that look
   plausible and mean nothing.
2. For a laser device, sum the segment losses into one budget, turn
   that into a transmission, then apply it twice -- once to the
   source pulse energy and once to the monitor power.
3. Grade the delivered pulse energy against the all-fire energy times
   the declared margin, and the no-fire power against the delivered
   monitor power as a ratio. Treat a chain sitting exactly on either
   requirement as compliant rather than failing it on representation
   error, because the budget ran through a power of ten.
4. Grade the wavelength against both edges of the characterised band.
5. For a mechanical device, multiply firing-pin force by stroke for
   the delivered energy and grade it against the all-fire energy with
   margin.
6. Compute the drop energy from handling mass, standard gravity and
   drop height, grade it against the no-fire impact energy, and grade
   the all-fire to no-fire ratio as a third separate check.
7. For a packaged charge, take the mass deviation as a fraction of
   nominal, the delivered output against the function need times its
   margin, and the autoignition separation against its margin.
8. Roll the findings into a device verdict and, for a mixed set, into
   a roll-up that keeps the part name on every finding.

## Pitfalls

- Grading a laser initiator on the energy the laser emits. Every
  connector in the path takes its share, and a design that passes on
  source energy can be below all-fire at the device with one extra
  mating in the harness.
- Summing the loss budget after the comparison, or omitting a
  segment because it is small. The budget is in decibel, so the small
  segments add; three tenth-decibel connectors are not negligible
  against a two-times margin.
- Forgetting that the monitor beam travels the same fibre. The loss
  that protects the no-fire requirement is the same loss that
  threatens the all-fire one, so improving the path helps one and
  hurts the other.
- Treating wavelength as an interface detail. Outside the
  characterised band the device has no known sensitivity, and every
  energy margin computed there is arithmetic without a subject.
- Quoting a mechanical firing energy from a specification rather than
  computing force times stroke. The two quantities are what change
  when the spring ages or the stroke is shimmed.
- Taking the no-fire impact energy as satisfied because the handling
  procedure forbids the drop. The requirement exists for the drop the
  procedure did not prevent.
- Grading a charge output against the function need with no margin. A
  charge meeting its need exactly has nothing left for the cold end
  of the temperature range.
- Failing a margin that lands a hair under its requirement in the
  last bits of a float. Powers of ten are not correctly rounded and
  land differently on different machines; the requirement is
  untouched, the comparison absorbs the representation error.

## Behavior contract (gate 3)

The optical loss budget and transmission, the delivered-energy and
monitor-power gradings, the wavelength band, the firing-pin work and
drop-energy computations, the mechanical separation ratio, the charge
mass tolerance, output margin and autoignition separation, the kind
dispatch and the set roll-up are exercised by the gate 3 contract
test:
scripts/test_e3311_laser_mechanical_initiators_packaged_charges.py
against
scripts/e3311_laser_mechanical_initiators_packaged_charges_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3311_laser_mechanical_initiators_packaged_charges.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
