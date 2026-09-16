---
name: e2008-bare-cell-temperature-coefficients
description: "Use when a coefficient data sheet or qualification subgroup record has to be evaluated. Derive the bare solar cell temperature coefficients that clause 7.5.4 of ECSS-E-ST-20-08C asks for on the irradiated samples of the qualification subgroup: confirm each sample really carries its irradiation and belongs to the subgroup, hold the measurement set to enough distinct temperatures over a wide enough span, fit short circuit current, open circuit voltage and peak power against temperature by least squares, report absolute and relative coefficients with the fit quality behind them, and name the subgroup member nobody measured. Trigger: ecss, e-st-20-08c-clause-7-5-4, bare-solar-cell-temperature-coefficients, irradiated-qualification-subgroup-sampling, temperature-coefficient-least-squares-fit, bare-cell-coefficient-sign-convention."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-temperature-coefficients, e-st-20-08c-clause-7-5-4, bare-solar-cell-temperature-coefficients, irradiated-qualification-subgroup-sampling, temperature-coefficient-least-squares-fit, bare-cell-coefficient-sign-convention, bare-cell-coefficient-fit-quality]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Temperature Coefficients (space-systems/ecss/e2008-bare-cell-temperature-coefficients)

Use when the task is clause 7.5.4 of ECSS-E-ST-20-08C: the temperature
coefficients of the bare cells, measured on the samples of the qualification
subgroup that have already taken their irradiation. Two things make this clause
what it is — the coefficient is a slope, so it lives or dies on the spread of
the temperatures behind it, and the sample is a specific one, already degraded,
not whichever cell was nearest the bench.

## Domain quick reference

- The sample is part of the requirement. A coefficient measured on a pristine
  cell describes a state the mission leaves behind in its first months; the
  clause points at the irradiated members of the qualification subgroup
  precisely so the end-of-life prediction rests on end-of-life cells.
- A coefficient is a slope, and a slope needs a span. Readings clustered inside
  a few kelvin produce a number the arithmetic will happily return, but the
  instrument noise then dominates the temperature effect and the number is
  noise with a unit on it.
- Separate readings are not the same as separate temperatures. Five points
  taken within a fraction of a kelvin of each other are one point measured five
  times, and the fit has two degrees of freedom fewer than the point count
  suggests.
- The fit quality travels with the coefficient. A slope on its own cannot be
  argued with; a slope plus the fraction of the measured spread the straight
  line accounts for tells a reviewer whether the cell is linear over the range
  at all.
- The signs are known in advance. Short circuit current rises with temperature
  while open circuit voltage and maximum power fall, so a slope of the wrong
  sign is an instrument polarity or a transcription fault rather than a
  surprising cell.
- Both forms of the coefficient are needed. A generator thermal model consumes
  the relative form, per kelvin as a fraction of the value at reference
  temperature, while the test report records the absolute one in amperes,
  volts or watts per kelvin.

## Workflow

1. For each sample, confirm it carries its irradiation and appears on the
   qualification subgroup roster. Either failure is a finding against the
   sample before any arithmetic runs.
2. Collect the readings into temperature, current, voltage and power columns,
   and count how many of the temperatures sit far enough apart to be separate
   points rather than one point repeated.
3. Hold the set to the declared minimum of separate temperatures and the
   declared minimum span, absorbing floating-point representation error at
   those limits with a named tolerance rather than by loosening them.
4. Fit each quantity against temperature by ordinary least squares and keep the
   fit quality alongside the slope.
5. Express each slope relative to the value the fit puts at reference
   temperature, and refuse a relative coefficient whose reference value is zero.
6. Hold each slope to its expected sign and each fit to the declared quality
   floor.
7. Reject a sample identifier that appears twice, then reconcile the samples
   measured against the subgroup roster and name every member nobody measured.

## Pitfalls

- Measuring coefficients on unirradiated cells because they were to hand. The
  numbers look cleaner and predict the wrong spacecraft.
- Fitting three readings taken across five kelvin. The slope is dominated by
  the noise of the two end points, and no amount of significant figures in the
  report makes it a measurement.
- Counting readings instead of temperatures. A set of clustered points passes a
  naive point count and then produces a slope resting on a span it never had.
- Reporting a slope without its fit quality. Nonlinearity over the range is
  invisible in the slope alone, and the reviewer has no way to see it.
- Accepting a coefficient of the wrong sign as a property of the cell. Cells do
  not reverse their thermal behaviour; benches reverse their leads.
- Mixing the absolute and relative forms between the test report and the
  generator model. Both are per kelvin, both are small, and swapping them
  scales every prediction by the value at reference temperature.

## Behavior contract (gate 3)

The irradiation and subgroup eligibility, the separate-temperature count, the
span floor, the least squares fit and its quality, the absolute and relative
coefficient forms, the expected sign check, the duplicate-identifier rejection
and the roster reconciliation are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_temperature_coefficients.py against
scripts/e2008_bare_cell_temperature_coefficients_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_temperature_coefficients.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
