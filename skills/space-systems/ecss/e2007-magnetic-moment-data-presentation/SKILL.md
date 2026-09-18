---
name: e2007-magnetic-moment-data-presentation
description: "Assess a steady magnetic emission report against ECSS-E-ST-20-07C clause 5.4.5.4, which replaces the general presentation rules for a field that has no spectrum. Use when magnetic moment results are tabulated or reviewed: require a value at every declared distance and on every axis rather than a plot or one summary figure, rebuild the resultant from its axis components and compare it with the stated one, derive the moment each distance implies so a row filed against the wrong distance shows up, and keep absent uncertainty as a limitation. Trigger: ecss, e-st-20-07c, magnetic-moment-data-presentation, steady-field-per-distance-table, per-axis-magnetic-result, magnetic-resultant-recomputation, dipole-moment-distance-consistency."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-magnetic-moment-data-presentation, steady-field-per-distance-table, per-axis-magnetic-result, magnetic-resultant-recomputation, dipole-moment-distance-consistency, steady-magnetic-emission-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Magnetic Moment Data Presentation (space-systems/ecss/e2007-magnetic-moment-data-presentation)

Use when the task is the reporting requirement of ECSS-E-ST-20-07C
clause 5.4.5.4 -- how steady magnetic emission results are set down.
The general emission-presentation rules assume a spectrum; a steady
field has none, so this clause puts a value at each measurement
distance and on each axis in their place.

## Domain quick reference

- The clause displaces the general rules rather than adding to them. A
  report that hands over an amplitude-against-frequency plot has
  answered the wrong question: there is no frequency axis to plot a
  steady field against, and the plot hides the distance behaviour that
  is the whole content of the result.
- Distance is the independent variable here, the way frequency is for
  a spectrum. One number at one distance says almost nothing, because
  the reader's own analysis sits at whatever separation their
  spacecraft imposes and they have to carry the result there.
- Per axis means the three components, not the magnitude alone. A
  moment is a vector; an attitude-control analysis needs to know which
  way it points, and a magnitude cannot be turned back into
  components.
- The resultant is checkable against the components that sit beside
  it. When a stated resultant does not follow from the three axis
  values on the same line, either a component was transcribed wrong or
  the resultant came from a different run.
- The distances check each other. A steady dipole field falls with the
  cube of separation, so the moment implied by each distance should
  agree across the table. Disagreement means a row filed against the
  wrong distance, a transcription slip, or a near point still inside
  the region where higher-order terms dominate -- and none of those is
  visible by reading the table down the page.
- Uncertainty missing is a limitation, not a defect in the
  presentation. The values are still per distance and per axis; what
  the reader loses is the ability to take a margin against a moment
  budget straight from the table.

## Workflow

1. Validate the report: a recognized presentation form, at least one
   result row, each row carrying a positive distance, a recognized
   axis and a non-negative field, and no axis repeated at a distance.
2. Check the presentation form, and record a plot or a single summary
   figure as a finding against the clause.
3. Compare the distances reported against the distances declared for
   the test, and list any that never appear.
4. At each reported distance, list the axes the table does not carry.
5. Where a resultant is stated alongside its components, rebuild it
   and compare.
6. Derive the moment each distance implies from its resultant, and
   compare the spread across distances against the allowance.
7. Aggregate: a wrong presentation form, an absent distance, an absent
   axis, a contradicted resultant or a moment spread beyond the
   allowance are findings; absent uncertainty and a single-distance
   table are limitations.

## Pitfalls

- Reusing the spectrum-presentation template because it is the one the
  test report already has. It produces a tidy document that omits the
  only structure the result has.
- Reporting the magnitude and calling it the per-axis requirement. The
  direction is lost, and no downstream analysis can recover it.
- Quoting one distance because the specification names one. The extra
  distances are what let anybody check the result is a dipole at all.
- Reading the implied-moment spread as a measurement problem. The
  nearest point is the usual culprit, and it is usually a geometry
  problem -- the sensor sat inside the multipole region -- not a
  faulty magnetometer.
- Failing a table for carrying no uncertainty. It weakens the report
  without breaking the presentation the clause asks for; record it as
  a limitation.

## Behavior contract (gate 3)

The row and report validation, presentation-form check, distance and
axis coverage, resultant rebuild, implied-moment derivation and
cross-distance agreement, and the aggregate verdict are exercised by
the gate 3 contract test:
scripts/test_e2007_magnetic_moment_data_presentation.py against
scripts/e2007_magnetic_moment_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_magnetic_moment_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
