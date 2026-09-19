---
name: q7005-calibration-and-standards
description: "Calibrate the infrared response of a surface-contamination method against standards of known deposit under ECSS-Q-ST-70-05C. Use when gravimetrically prepared standards have been run at several levels and the method needs a defensible slope, a bracketed working range and a verified recovery before any sample is quantified. Fits absorbance against areal mass by least squares, grades the fit on its coefficient of determination and its worst residual, refuses an inversion outside the bracketed range, and puts an independent verification standard back through the curve. Trigger: ecss, q-st-70-05, ir-calibration-standards, absorbance-versus-areal-mass-slope, calibration-working-range, least-squares-linearity-check, verification-standard-recovery, contamination-quantification."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-calibration-and-standards, ir-calibration-standards, absorbance-versus-areal-mass-slope, calibration-working-range, least-squares-linearity-check, verification-standard-recovery]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Calibration and Standards (space-systems/ecss/q7005-calibration-and-standards)

Use when the task is establishing what an absorbance is worth — turning
a set of prepared standards of known deposit into the slope, the working
range and the verified recovery a contamination result is quantified
against.

## Domain quick reference

- An infrared band height is an index until a calibration attaches it to
  a mass. The calibration is specific to the contaminant, the band, the
  substrate or window, and the instrument settings; carrying a slope
  across any of those four is the commonest way a number becomes wrong
  without becoming implausible.
- Standards are prepared by depositing a weighed quantity over a known
  area, so the abscissa of the curve is an areal mass and the ordinate
  is the net absorbance measured exactly as a sample would be. A
  standard measured differently from the samples calibrates nothing.
- Three levels is the floor, and they must be distinct. Replicates at
  one level measure repeatability, not response, and a fit through two
  points has no residual left to tell you whether the response is linear
  at all.
- The fit carries two separate questions. The coefficient of
  determination says how much of the spread the line explains; the worst
  relative residual says whether any single level is badly served.
  A curve can score well on the first and still miss the lowest standard
  by half, which is the level most samples sit near.
- A calibration is a statement about the interval its standards bracket.
  Inverting an absorbance above the top standard or below the bottom one
  is extrapolation, and the response commonly bends at both ends — at
  the top through saturation, at the bottom through the blank.
- The slope must be positive. A negative or flat fitted slope means the
  standards, the baseline or the band choice is wrong, and inverting
  through it produces a confidently signed nonsense.

## Workflow

1. Validate the standards: at least three distinct non-negative levels,
   each with a finite net absorbance measured under the sample method.
2. Fit the response by least squares, either with a free intercept or
   forced through the origin when a blank-corrected method justifies it.
3. Refuse a non-positive fitted slope outright rather than carrying it
   into an inversion.
4. Grade the fit: the coefficient of determination against the linearity
   threshold, and the worst relative residual against its own limit, so
   a poorly served low level is visible.
5. Record the working range as the interval the standards bracket, in
   both areal mass and predicted absorbance.
6. Invert a sample absorbance through the curve only inside that range;
   outside it, refuse and say which end was exceeded.
7. Put the independent verification standard back through the curve,
   form its recovery against its prepared value, and report a recovery
   outside the acceptance band as a finding rather than adjusting the
   slope to suit it.

## Pitfalls

- Forcing the line through the origin to gain a point of fit. A real
  intercept usually means an uncorrected blank or a baseline offset;
  suppressing it moves the error into the slope, where it scales every
  result.
- Calibrating on replicates of two levels and calling it three points.
  The fit then has no independent check of linearity, and the residual
  it reports is repeatability wearing a linearity label.
- Quantifying a sample above the top standard. Band saturation flattens
  the response, so the extrapolated mass is an underestimate exactly
  where an underestimate matters.
- Accepting a high coefficient of determination as sufficient. A single
  badly served level barely moves it while making every result near that
  level wrong; the worst relative residual is the check that catches it.
- Adjusting the slope until the verification standard recovers. The
  verification standard is the independent test of the curve; tuning the
  curve to it removes the only evidence the calibration works.

## Behavior contract (gate 3)

The standards validation, least-squares fit with and without a forced
origin, slope sign refusal, coefficient of determination, residual
grading, working-range bracketing, guarded inversion and
verification-standard recovery are exercised by the gate 3 contract test:
scripts/test_q7005_calibration_and_standards.py against
scripts/q7005_calibration_and_standards_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7005_calibration_and_standards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
