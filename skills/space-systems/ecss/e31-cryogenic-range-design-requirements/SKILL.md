---
name: e31-cryogenic-range-design-requirements
description: "Evaluate a thermal control item operating below two hundred kelvin against the cryogenic design constraints of ECSS-E-ST-31 clause 4.2.3 and its cryogenic annex: confirm the temperature sensor still resolves the cold end with usable sensitivity, decide whether a mechanical thermostat is qualified that low or must be replaced by an electronic controller, hold the interface gradient inside its allowable, and widen every material property by the scatter it acquires below the boundary before a heat leak is quoted. Use when a unit has been grouped into the cryogenic range and its sensing, control and conduction assumptions need checking. Trigger: ecss, e-st-31, cryogenic-tcs-design-constraints, cryogenic-sensor-sensitivity, cryogenic-thermostat-deadband, cryogenic-interface-gradient, cryogenic-property-scatter, cryogenic-heat-leak-band."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-cryogenic-range-design-requirements, cryogenic-tcs-design-constraints, cryogenic-sensor-sensitivity, cryogenic-thermostat-deadband, cryogenic-interface-gradient, cryogenic-property-scatter]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Cryogenic Range Design Requirements (space-systems/ecss/e31-cryogenic-range-design-requirements)

Use when the task is the clause 4.2.3 step of ECSS-E-ST-31 and its cryogenic
annex: an item has already been placed in the cryogenic range, and the
sensing, control, gradient and material assumptions carried over from
room-temperature practice now have to be re-examined before they are relied
on.

## Domain quick reference

- A sensor has a usable span, not just a range printed on a datasheet. Its
  sensitivity — the signal it produces per kelvin — collapses at one end of
  that span, and a sensor reading a tenth of a millivolt per kelvin cannot
  hold a control loop no matter how well it is calibrated. Both the span
  coverage and the sensitivity at the cold end have to be checked.
- Mechanical thermostats are qualified down to a temperature and no further.
  Below it the bimetal stiffens, the snap action slows and the deadband
  widens, so a controller qualified at room temperature can be sitting at
  several times its catalogue deadband in the cold case. Where the widened
  deadband exceeds the allowable control band, an electronic controller is
  the answer, not a tighter set point.
- Gradients matter more, not less, when everything is cold. The same heat
  leak across a joint produces a larger fractional temperature error at
  twenty kelvin than at three hundred, and detector and structure alignment
  requirements are usually written against the gradient rather than the
  absolute level.
- Material properties scatter below the range boundary. Thermal conductivity,
  specific heat and expansion coefficient are measured on fewer samples at
  cryogenic temperatures and vary more between lots, so a single catalogue
  value is a mid-estimate rather than a design value.
- The consequence is that a cryogenic heat leak is a band, not a number. The
  design has to work at the high-conductivity end of the scatter and the
  cooler sizing has to survive it, so the two ends of the band are both
  carried rather than averaged.
- Scatter and prediction uncertainty are different quantities and both apply.
  Collapsing them into one allowance is how a cryogenic chain ends up with a
  margin that exists only on paper.

## Workflow

1. Validate the item: an operating range wholly or partly below the cryogenic
   boundary, positive temperatures, and a range that does not run backwards.
   An item entirely above the boundary is not this skill's subject and is
   refused rather than quietly graded.
2. Check the sensor: its usable span must cover the operating range with the
   declared margin at both ends, and its sensitivity at the cold end must
   meet the floor the control electronics need.
3. Check the controller: take the catalogue deadband, apply the cold growth
   factor if the set point sits below the mechanical qualification floor, and
   compare the widened deadband with the allowable control band. Record the
   need for an electronic controller as a finding rather than a failure.
4. Check the interface gradient against its allowable, absorbing
   representation error at the boundary with a named tolerance.
5. Widen each material property: the nominal value is multiplied out to a low
   and a high bound using the scatter fraction, itself multiplied by the
   cryogenic scatter factor when the item sits below the boundary.
6. Propagate the conductivity band into a conduction heat leak band using the
   conductive path geometry and the temperature difference across it.
7. Size the cooler or cold-strap against the high end of the heat-leak band,
   never the mid value, and report the required capacity alongside the band.
8. Report a per-constraint verdict and the findings, so a unit that fails one
   constraint is not reported as failing all of them.

## Pitfalls

- Reading only the sensor's stated range. Range coverage without sensitivity
  gives a sensor that is technically in range and practically useless for
  control at the cold end.
- Keeping a mechanical thermostat below its qualification floor because it
  "still clicks". The deadband is what moved, and the control band is what it
  broke.
- Sizing a cooler on the nominal conductivity. Half the population sits above
  it, and the cooler either runs out of capacity or spends its entire margin.
- Averaging the property band into a single design value. The point of the
  band is that both ends have to be survivable; an average is survivable in
  neither direction on its own.
- Folding scatter into the prediction uncertainty. They are independent
  contributions and combining them by hand usually means one of them silently
  disappeared.
- Checking the absolute temperature and not the gradient. Alignment and
  detector performance requirements are written against the gradient, and it
  is the constraint that goes red first.

## Behavior contract (gate 3)

The cryogenic-range admission check, sensor span and sensitivity check,
thermostat deadband growth and control-band comparison, gradient check,
property scatter banding, conduction heat-leak band and cooler sizing are
exercised by the gate 3 contract test:
scripts/test_e31_cryogenic_range_design_requirements.py against
scripts/e31_cryogenic_range_design_requirements_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e31_cryogenic_range_design_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
