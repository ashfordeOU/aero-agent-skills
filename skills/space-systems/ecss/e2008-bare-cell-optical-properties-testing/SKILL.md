---
name: e2008-bare-cell-optical-properties-testing
description: "Use when a bare cell reflectance scan or a coverglass gain figure is about to be accepted as optical performance evidence for a solar cell lot. Evaluate whether a bare solar cell's measured optical properties satisfy ECSS-E-ST-20-08C clause 7.5.6: weight a reflectance scan across the declared wavelength band into one band-averaged figure, derive the absorbed fraction it implies, confirm the scan reaches both band edges at a fine enough step before any average is trusted, and turn the covered against bare short-circuit current into a coverglass gain judged against its floor. Trigger: ecss, e-st-20-08c-clause-7-5-6, bare-solar-cell-reflectance-scan, coverglass-current-gain-factor, band-averaged-cell-reflectance, cell-optical-absorptance-fraction, reflectance-scan-wavelength-coverage, solar-cell-spectral-reflectance-average."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-bare-cell-optical-properties-testing, bare-solar-cell-reflectance-scan, coverglass-current-gain-factor, band-averaged-cell-reflectance, cell-optical-absorptance-fraction, reflectance-scan-wavelength-coverage, solar-cell-spectral-reflectance-average]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Bare Cell Optical Properties Testing (space-systems/ecss/e2008-bare-cell-optical-properties-testing)

Use when the task is clause 7.5.6 of ECSS-E-ST-20-08C -- judging the
optical performance of a bare solar cell from a reflectance measurement
and from the gain its coverglass returns. Two different measurements get
quoted side by side under one heading, and only one of them says
anything about the glass.

## Domain quick reference

- A reflectance scan is a curve, not a number. The spectrophotometer
  returns a reflected fraction at each wavelength it steps through, and
  what every downstream budget wants is a single band figure derived
  from that curve.
- The derivation is a weighted average. Reflectance where little light
  falls costs the cell little, so the irradiance falling on the cell is
  the weight. An unweighted wavelength average is a legitimate number
  for comparing two coupons and the wrong number for a current budget,
  and nothing in the value itself says which one it is.
- The average is only as good as the scan under it. A step too coarse
  makes the trapezoid between two samples invent the shape of the curve
  there, and a scan that stops short of a band edge silently averages
  over a narrower band than the one the requirement is written against.
- Reflectance is a fraction. A scan quoted in per cent looks like a
  valid scan of a catastrophically bad cell, so a value above one is a
  unit error rather than a measurement.
- Coverglass gain is the ratio of short-circuit current measured with
  the glass fitted to the same cell measured bare. A matched
  antireflective stack returns slightly more current than the bare cell;
  an unmatched or clouded one returns less.
- The gain cannot be recovered from the bare scan. It carries the
  transmission of the glass, the adhesive and the index match between
  them, none of which the bare front surface was ever measured with.

## Workflow

1. Validate the acceptance policy first: band edges, step ceiling,
   minimum sample count, reflectance ceiling and gain floor. A band
   whose end is not above its start is refused rather than used.
2. Order the scan by wavelength and validate every sample, rejecting a
   percentage-valued reflectance, a negative one and a repeated
   wavelength rather than averaging through them.
3. Grade the scan before grading the cell: sample count, coverage of
   both band edges, widest step. Report every scan finding, not the
   first, and stop there -- a band average over an inadequate scan is a
   number nobody can defend.
4. Integrate the scan trapezoidally, weighted by the supplied spectral
   irradiance when there is one, and record whether the answer is a
   solar-weighted figure or a bare wavelength average.
5. Derive the absorbed fraction from the band average, and compare the
   band average against its ceiling. A value landing exactly on the
   ceiling passes; the comparison tolerance absorbs representation
   error and the ceiling does not move.
6. Take the covered and bare short-circuit currents into a gain and a
   signed percentage change, and hold the gain above its floor. A case
   with no covered measurement closes on its own verdict rather than
   being graded as if the glass were acceptable.
7. Close on one verdict: scan inadequate, coverglass gain not measured,
   optical performance deficient, or optical performance accepted.

## Pitfalls

- Quoting a peak reflectance as the cell's reflectance. The peak is
  usually at a band edge where the irradiance is small, and it governs
  nothing the budgets care about.
- Averaging a scan without weights and calling it solar reflectance.
  The two numbers can differ by several points on a cell whose
  antireflective coating is tuned to the visible.
- Stepping coarsely through the antireflective minimum. The trapezoid
  cuts the corner of a sharp feature, and the error is one-sided
  because the minimum is always below the chord across it.
- Reporting a gain without saying which cell it came from. The gain is
  a property of a cell and its glass together, so a figure carried over
  from another coupon describes different hardware.
- Treating a gain below one as a measurement error. An unmatched or
  clouded coverglass genuinely costs current, and that is exactly the
  outcome the measurement exists to catch.
- Comparing a derived average against a limit by bare arithmetic. The
  integral is a sum of products that can land a few units in the last
  place either side of a limit, so the comparison absorbs that error
  while the limit itself is never relaxed.

## Behavior contract (gate 3)

The policy validation, scan ordering and unit checks, band coverage and
step grading, the weighted trapezoidal band average, the absorbed
fraction, the coverglass gain and its signed percentage, and the optical
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_optical_properties_testing.py against
scripts/e2008_bare_cell_optical_properties_testing_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_optical_properties_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
