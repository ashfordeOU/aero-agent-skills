---
name: e2008-component-physical-property-measurements
description: "Use when an array analysis is about to consume material data whose completeness and temperature validity are unproven. Determine which thermal and mechanical property values a solar-array material or component must have established under ECSS-E-ST-20-08C clause 4.2, and grade the set that exists: pick the required properties from what the item does, refuse any declared value outside its physical band, name the values still outstanding, compare the temperature band each value covers against the mission band and size the cold and hot shortfall in kelvin, and derive the absorptance-to-emittance ratio, the specific stiffness, and the expansion-mismatch strain and stress a bonded pair carries over a deep cycle. Trigger: ecss, e-st-20-electrical-scope, e-st-20-08c, solar-array-material-property-determination, solar-array-thermal-property-band, solar-array-mechanical-property-set, coverglass-expansion-mismatch-strain, solar-array-absorptance-emittance-ratio, photovoltaic-assembly-property-completeness."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-component-physical-property-measurements, solar-array-material-property-determination, solar-array-thermal-property-band, solar-array-mechanical-property-set, coverglass-expansion-mismatch-strain, solar-array-absorptance-emittance-ratio, photovoltaic-assembly-property-completeness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Array — Component Physical Property Measurements (space-systems/ecss/e2008-component-physical-property-measurements)

Use when the task is clause 4.2 of ECSS-E-ST-20-08C -- the thermal and
mechanical property values that have to be determined for the materials
and components of a solar array before anything is predicted about it.
A solar array is a stack of dissimilar materials bonded together and
flown through thousands of deep thermal cycles, so the properties that
govern its behaviour are the ones that differ across the stack.

## Domain quick reference

- Properties grouped as thermal: solar-absorptance and
  infrared-emittance (the radiative pair that sets the operating
  temperature), thermal-conductivity and specific-heat (how fast that
  temperature moves), and the coefficient of thermal expansion (how
  much each layer moves when it does).
- Properties grouped as mechanical: density, Young's modulus,
  Poisson's ratio and tensile strength. Density is carried in both
  arguments -- it enters the thermal diffusivity and the specific
  stiffness -- which is why a partially determined set breaks more
  analyses than its size suggests.
- Which properties a given item owes depends on what the item does. An
  optical coating owes its radiative pair and its expansion; a
  substrate facesheet owes the full mechanical set; an interconnect
  owes conduction, expansion and strength because it is a current path
  that is also cycled.
- Every value has a physical band it cannot leave. An emittance or an
  absorptance above one, a Poisson ratio above one half, a negative
  density: each of these is a transcription error rather than an
  unusual material, and it is cheaper to refuse it at the input than
  to trace it out of a thermal model later.
- The coefficient of thermal expansion is the exception that must stay
  signed. Some laminates contract on heating, and clamping the value
  to positive numbers destroys exactly the mismatch that drives the
  bond-line stress.
- A value is only usable over the temperature band it was determined
  across. A modulus measured from room temperature upward says nothing
  about an eclipse exit at 120 K, so the determined band is carried
  with the value and the shortfall against the mission band is
  reported in kelvin at each end rather than as a yes or no.
- The mismatch that matters is between neighbours in the stack. The
  strain a bonded pair carries is the difference of their expansion
  coefficients times the temperature change, and the stress that
  follows is compared against the weaker allowable of the pair.

## Workflow

1. Name the item by what it does -- solar cell, coverglass, adhesive,
   substrate facesheet, interconnect, optical coating -- and take the
   required property set from that, rather than asking for everything
   and treating the gaps as acceptable.
2. Validate each declared value against its physical band and its
   expected unit. Reject a value outside the band instead of flagging
   it, because a downstream model that consumes it will produce a
   plausible number from an impossible input.
3. Compare the determined set against the required set in both
   directions: the values still outstanding block the analysis, and
   the values determined beyond need are recorded rather than
   discarded because they are evidence already paid for.
4. Check the temperature band. Size the cold and the hot shortfall
   separately, since the two are retired by different test setups and
   a single combined number tells the thermal engineer nothing about
   which one to buy.
5. Derive what the values were determined for: the
   absorptance-to-emittance ratio that drives the operating
   temperature, the specific stiffness that ranks a facesheet, the
   thermal diffusivity, and the expansion-mismatch strain and stress
   across each bonded pair with a margin against the weaker allowable.
6. Close with the determination completeness and a verdict that stays
   open while any required value is outstanding or the determined band
   fails to envelop the mission band.

## Pitfalls

- Accepting a property value with no temperature band attached. The
  number looks complete and is only valid where it was determined, so
  a set that reports full completeness can still be silent at both
  ends of the mission range.
- Clamping the expansion coefficient to positive values. Laminates
  that contract on heating are common in array structures, and
  removing the sign removes the mismatch the bond line actually sees.
- Reading a high absorptance as a thermal problem on its own. It is
  the ratio against emittance that sets the operating temperature; a
  high absorptance next to a high emittance runs cooler than a modest
  absorptance on a poor radiator.
- Treating a surplus determined value as an error. A property measured
  for one item and not required for it is evidence already paid for,
  so it is recorded rather than dropped and never counted toward the
  completeness of the required set.
- Comparing an expansion mismatch stress against an allowable by bare
  arithmetic when the two are equal by construction. The stress is a
  product of small floats and the comparison absorbs that
  representation error, while the allowable itself is never relaxed.
- Quoting a mismatch stress without naming the pair. The value belongs
  to two neighbouring layers and a temperature change, and the same
  coverglass against a different adhesive is a different answer.

## Behavior contract (gate 3)

The property grouping, required-set selection, physical-band
validation, completeness and surplus accounting, temperature-band
coverage, radiative ratio, specific stiffness, thermal diffusivity and
bonded-pair mismatch stress are exercised by the gate 3 contract test:
scripts/test_e2008_component_physical_property_measurements.py against
scripts/e2008_component_physical_property_measurements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_component_physical_property_measurements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
