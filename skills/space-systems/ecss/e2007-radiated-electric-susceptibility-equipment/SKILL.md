---
name: e2007-radiated-electric-susceptibility-equipment
description: "Assess the instrument chain an ECSS-E-ST-20-07C clause 5.4.11.2 radiated electric susceptibility exposure is made with. Use when the exposure bench is specified or reviewed: confirm a signal generator, a power amplifier, a transmit antenna and an isotropic field probe are each declared once, intersect their usable spans and name the item bounding the method band, derive the forward power the required field strength needs from antenna gain and separation, compare it with what the generator and amplifier deliver once the rating caps the drive, confirm the probe is isotropic and reads the required field, and reject an item whose calibration lapses mid-campaign. Trigger: ecss, e-st-20-07c, radiated-electric-susceptibility-equipment, field-exposure-power-amplifier, transmit-antenna-gain, isotropic-field-probe-range, forward-power-for-field-strength, exposure-instrument-calibration."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-susceptibility-equipment, field-exposure-power-amplifier, transmit-antenna-gain, isotropic-field-probe-range, forward-power-for-field-strength, exposure-instrument-calibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Susceptibility, Instrument Set (space-systems/ecss/e2007-radiated-electric-susceptibility-equipment)

Use when the task is the equipment clause of ECSS-E-ST-20-07C clause
5.4.11.2 -- deciding whether the items a radiated electric field
exposure is to be made with (a signal generator, a power amplifier, a
transmit antenna and an isotropic field probe) are present, reach the
method band between them, can raise the required field at the stated
separation, and stay calibrated for as long as the campaign runs.

## Domain quick reference

- The list is a set of roles, not a count of boxes. The generator sets
  the frequency and the modulation, the amplifier turns that into
  power, the antenna turns power into a field, and the probe says what
  the field actually is. A role declared twice is as much a defect as
  a role absent, because it means the run plan has not said which item
  does what.
- Usable span is the binding property, and it is the intersection of
  the declared spans, not the widest item on the bench. One item sets
  each edge of it -- usually the antenna, whose useful range is
  narrower than the generator's by orders of magnitude. Naming that
  item is what makes a coverage shortfall fixable, because it says
  which box to change.
- Forward power follows from the field, not the other way round. The
  power the antenna needs is the required field times the separation,
  squared, divided by thirty times the linear antenna gain. Sizing an
  amplifier by its wattage without that calculation is how a bench
  ends up eight decibels short at the top of the band.
- The amplifier cannot give back more than it is rated for. The drive
  the generator offers is capped at that rating before feed loss is
  taken off, so a chain that looks comfortable on paper can be running
  compressed, with the level set by the amplifier rather than by the
  dial. That is a limitation worth naming, not a silent detail.
- A power comparison happens after a logarithm, so a chain that
  exactly meets its requirement can land a few units in the last place
  either side of equality. That is absorbed with a named tolerance;
  meeting the need exactly is compliance, carried as a limitation
  because nothing is left for feed-loss drift.
- The probe has to be isotropic and it has to reach the level. A
  directional probe reports whatever its orientation favours, and a
  probe whose ceiling sits under the required field cannot confirm the
  exposure it is there to witness.
- Calibration validity is graded against the campaign window, not
  against today. An item whose certificate expires mid-campaign
  invalidates every exposure after that date.
- The instrument set is graded on its own. Where the items sit and how
  the unit is watched belong to the setup and monitoring clauses of
  the same method.

## Workflow

1. Validate each declared item: a recognized role, a non-empty
   identifier, a positive lower span edge with an upper edge above it,
   a non-negative calibration validity, and the numbers its role needs
   -- generator output, amplifier gain and rating, antenna gain, probe
   range and isotropy.
2. Index the set by role, refuse a duplicate role, and name every
   listed role the set does not fill. A set missing a role cannot
   raise the exposure at all, so the assessment stops there.
3. Intersect the declared spans, refuse an empty intersection, and
   name the item setting each edge; compare that intersection with the
   declared method band.
4. Derive the forward power the required field needs at the stated
   separation from the antenna gain, and convert it to the decibel
   scale the generator and amplifier are specified on.
5. Compute the power the chain delivers: generator output plus
   amplifier gain, capped at the amplifier rating, less the feed loss.
6. Take the margin over the required power -- a shortfall is a
   finding, exact equality a limitation, a capped drive a limitation.
7. Check the probe is isotropic and that the required field sits
   inside its range, then grade every item's calibration against the
   campaign window. The chain is ready only when no finding stands.

## Pitfalls

- Sizing the amplifier in watts and never converting to a field. The
  requirement is volts per metre at the unit; power is only the way to
  get there, and the conversion needs the antenna gain and distance.
- Reading the generator span and calling the band covered. The run is
  bounded by the intersection, and the antenna is nearly always the
  narrow item.
- Ignoring the amplifier rating because the gain figure is large
  enough. Drive past the rating does not become field, it becomes
  compression and harmonics the probe will not separate.
- Substituting a single-axis probe because it was on the shelf. Its
  reading depends on orientation, so the field it witnesses is not the
  field the unit sees unless someone rotates it through every axis.
- Confirming calibration on the day of the readiness review. A
  certificate valid this morning and expired next week still
  invalidates the second half of the campaign.

## Behavior contract (gate 3)

The instrument validation, role indexing and completeness check, span
intersection and bounding-item selection, band coverage, forward-power
derivation, delivered-power capping, margin grading, probe isotropy
and range checks, calibration grading and the aggregate readiness
verdict are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_susceptibility_equipment.py
against
scripts/e2007_radiated_electric_susceptibility_equipment_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_susceptibility_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
