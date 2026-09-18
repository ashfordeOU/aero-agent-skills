---
name: e2007-radiated-electric-emission-setup
description: "Derive the bench layout for an ECSS-E-ST-20-07C clause 5.4.6.3 radiated electric-emission run and audit the realized bench against it: apply each declared method delta to the baseline geometry, compare the antenna-to-unit separation, boresight height, cabling run length and ground-plane bond resistance against their bands, confirm the separation clears the near-field boundary at the lowest frequency, check every radiating face of the unit was presented to the antenna in both polarizations, and return the governing parameter with the setup verdict. Use when a radiated-emission bench layout is being built or graded. Trigger: ecss, e-st-20-07c, radiated-electric-emission-setup, antenna-to-unit-separation, unit-face-presentation-coverage, radiated-bench-boresight-height, near-field-boundary-clearance, radiated-setup-deviation-categorization."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-radiated-electric-emission-setup, radiated-electric-emission-setup, antenna-to-unit-separation, unit-face-presentation-coverage, radiated-bench-boresight-height, near-field-boundary-clearance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Radiated Electric Emission, Bench Layout (space-systems/ecss/e2007-radiated-electric-emission-setup)

Use when the task is the setup clause of ECSS-E-ST-20-07C clause
5.4.6.3 -- building the bench for a radiated electric-field emission
run and turning the unit to face the measuring antennas. The clause
fixes two things at once, and both have to hold: where the parts of
the bench sit relative to each other, and which sides of the unit were
actually shown to the antenna.

## Domain quick reference

- Geometry and orientation are graded together because either one
  alone is worthless. A bench measured to the millimetre that only
  ever saw the front of the unit has left every other face
  unmeasured, and a complete set of presentations made at the wrong
  separation has measured something other than what the limit is
  written against.
- The separation is the one free choice the clause leaves the bench,
  and the rest of the layout follows from it. The clearance the
  absorber keeps behind the antenna is stated as a fraction of the
  separation, so moving the antenna back moves that bound too. A
  bench that changes the separation and keeps the old clearance
  figure has derived nothing.
- Bounds come in three shapes and they behave differently. A nominal
  parameter has to land inside a symmetric band; a maximum has a
  ceiling and no floor worth naming; a minimum has a floor and is open
  above. Treating a minimum as a nominal turns a generously clear
  bench into a deviation.
- Deviations are in different units -- metres and milliohms -- so they
  cannot be ranked as they are. Each is divided by its own parameter's
  scale, and the governing parameter is the largest of those
  unit-free fractions.
- A separation of one metre is inside the reactive near-field boundary
  for the bottom of the band. That is normal practice and is not a
  finding, but it does mean the recorded field cannot be rescaled to
  another distance by the inverse-distance law, so it is carried as a
  limitation on the record rather than passed over in silence.
- Every presentation is scanned in both antenna planes. A face shown
  only vertically has been half measured, and the gap is named by face
  and plane so the bench knows what to repeat.
- The layout is graded on its own. What the instruments are, and what
  the run has to demonstrate, belong to the equipment and purpose
  clauses of the same method.

## Workflow

1. Derive the layout: start from the general bench arrangement, apply
   the chosen antenna-to-unit separation so the dependent bounds move
   with it, then apply each declared method delta.
2. Refuse a delta that names an unknown parameter or field, changes
   what kind of bound a parameter has, or leaves it with no allowed
   band. That is an input error, caught at derivation rather than
   discovered mid-run.
3. Refuse a measurement set that does not describe every parameter, or
   that spells one of them twice. An undescribed bench cannot be
   graded.
4. Compute each parameter's deviation from its derived band, absorbing
   representation error at a bound with a named tolerance, and
   categorize it as conforming, a declared deviation or
   nonconforming.
5. Express each deviation as a fraction of its own scale and take the
   largest as the governing parameter, breaking an exact tie on the
   parameter name so the selection is reproducible.
6. Check the presentation log: every face of the unit, in both
   polarizations, with no entry recorded twice. Name each missing
   combination.
7. Compare the realized separation with the near-field boundary at the
   lowest frequency of the run and record the regime.
8. Report the verdict with its findings (out-of-band parameters,
   unpresented faces) and its limitations (declared deviations, a
   near-field separation). The layout conforms only when no finding
   stands.

## Pitfalls

- Moving the antenna back and leaving the absorber clearance at its
  old figure. The clearance is stated against the separation, so the
  derivation has to be redone, not carried over.
- Grading a minimum bound as if it were a nominal one. Extra clearance
  behind the antenna is not a deviation; too little is.
- Ranking a bond resistance overrun in milliohms against a separation
  overrun in metres. The numbers are not comparable until each is
  divided by its own scale.
- Presenting the four side faces and stopping. The top radiates too,
  and a face never turned toward the antenna was never measured.
- Recording one polarization per presentation because the peak looked
  higher in that plane. The plane carrying the peak changes with
  frequency and with the face.
- Treating a one-metre separation at the bottom of the band as a
  clean far-field measurement and rescaling the result to another
  distance. It is a near-field reading, and the rescaling is invalid.

## Behavior contract (gate 3)

The layout derivation, delta refusal, bound shapes, deviation and
relative-overrun computation, parameter categorization,
governing-parameter selection, presentation coverage and the
near-field regime check are exercised by the gate 3 contract test:
scripts/test_e2007_radiated_electric_emission_setup.py
against
scripts/e2007_radiated_electric_emission_setup_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2007_radiated_electric_emission_setup.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
