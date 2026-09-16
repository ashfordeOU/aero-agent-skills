---
name: e2008-capacitance-model-determination
description: "Use when a junction model is about to be quoted from capacitance read at a single bias point. Derive the junction model of a solar cell from capacitance read at several bias voltages per ECSS-E-ST-20-08C clause 11.1.4.2.2: fit one over capacitance squared against bias, take the built-in voltage from the voltage intercept and the doping of the lighter side from the slope, fit the graded power law for the grading coefficient and the zero-bias capacitance, then hold the sweep to its point count, bias span and fit quality and drop points pushed far enough forward that diffusion capacitance joins the depletion term. Trigger: ecss, e-st-20-08c-clause-11-1-4-2-2, solar-cell-capacitance-model-determination, mott-schottky-bias-sweep-fit, junction-built-in-voltage-extraction, depletion-doping-from-capacitance-slope, junction-grading-coefficient-fit, forward-bias-diffusion-capacitance-exclusion."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-capacitance-model-determination, solar-cell-capacitance-model-determination, mott-schottky-bias-sweep-fit, junction-built-in-voltage-extraction, depletion-doping-from-capacitance-slope, junction-grading-coefficient-fit, forward-bias-diffusion-capacitance-exclusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Cell Capacitance Model Determination (space-systems/ecss/e2008-capacitance-model-determination)

Use when the task is clause 11.1.4.2.2 of ECSS-E-ST-20-08C -- determining
the model of the cell junction from capacitance measured at several
different bias voltages, rather than reporting the one number an
instrument returned at whatever bias it happened to sit at.

A single capacitance reading is a number, not a model. The parameters
live in the way the capacitance moves as the bias moves, because the
depletion region widens and narrows with it. Fit the movement and the
built-in voltage, the doping and the junction grading fall out of the
fitted line; skip it and the array analyst is left multiplying one
reading by a cell count and hoping the bias the reading was taken at was
the bias the mission flies at.

## Domain quick reference

- The depletion capacitance of an abrupt junction obeys one over
  capacitance squared falling linearly with bias. That is why the sweep
  is plotted in that quantity rather than in capacitance: a straight
  line is what makes the two parameters separable.
- The line's voltage intercept is the built-in voltage. It is an
  extrapolation, not a reading, so it is only as trustworthy as the
  span and the scatter of the points it was extrapolated from.
- The line's slope carries the doping of the lighter-doped side, once
  the junction area and the relative permittivity of the semiconductor
  are supplied. Neither is measured by the capacitance meter, so both
  have to arrive with the sweep or the doping cannot be reported.
- A junction whose doping is graded rather than abrupt follows a power
  law: capacitance over the depletion drive term raised to a grading
  coefficient. One half is the abrupt case, about one third the linearly
  graded one, and a fitted value outside roughly a fifth to three fifths
  is a sign the model form itself is wrong.
- Forward bias past roughly a third of the built-in voltage brings in
  diffusion capacitance from injected minority carriers. Those points
  still lie on a smooth curve, so the fit does not complain -- it simply
  returns a doping that belongs to no junction.
- Fit quality is a gate, not a decoration. A coefficient of
  determination under about 0.98 on a noiseless physical sweep means the
  readings are not all following one model, and averaging them into one
  is what produces a confident wrong answer.

## Workflow

1. Validate the sweep first. Sort the readings by bias, refuse a
   repeated bias point rather than averaging it, and refuse a
   non-positive capacitance, because each of those silently changes the
   slope the whole determination rests on.
2. Hold the sweep to its point count and its bias span before fitting.
   Five points across half a volt is the floor; a slope read off a
   narrower window is indistinguishable from the scatter.
3. Fit one over capacitance squared against bias by ordinary least
   squares and keep the coefficient of determination alongside the
   slope and intercept, so the fit reports its own adequacy.
4. Take the built-in voltage from the voltage intercept and place it in
   the band a cell junction can physically occupy. An extracted value
   outside it condemns the sweep, not the band.
5. Convert the slope into a doping concentration using the junction
   area and the relative permittivity, both of which arrive as inputs
   rather than as assumptions.
6. For a graded model form, fit log capacitance against log depletion
   drive, read the grading coefficient off the slope and the zero-bias
   capacitance off the intercept, and hold the coefficient inside its
   band.
7. Identify the points sitting above the forward-bias ceiling and
   report them as a finding. The determination stays open while any
   finding stands.

## Pitfalls

- Reporting a model from two bias points. Two points define a line
  exactly, so the fit quality is perfect by construction and tells you
  nothing at all about whether the junction follows the model.
- Sweeping only a narrow window near zero bias because the meter is
  most comfortable there. The intercept is an extrapolation whose error
  grows as the extrapolation lengthens, and a narrow sweep is the
  longest extrapolation available.
- Keeping forward-bias points because they were measured. Diffusion
  capacitance is a real reading of a different quantity, and the fit
  has no way to tell the two contributions apart.
- Quoting a doping without the junction area. The slope alone fixes the
  product of doping and area squared, so an area taken from the cell
  outline rather than from the active junction moves the reported
  doping by the square of the error.
- Fitting a graded power law with an assumed built-in voltage. The
  drive term depends on it, so an assumed value propagates straight
  into the grading coefficient and makes an abrupt junction look
  graded.
- Comparing a derived fit quality or bias span against a written floor
  by bare arithmetic. Both are sums of floats that can land a few units
  in the last place either side of the limit, so the comparison absorbs
  that error while the limit itself is never relaxed.
- Treating a grading coefficient far outside its band as a result. It
  is a statement that the chosen model form does not describe this
  junction, and the answer is a different model, not a wider band.

## Behavior contract (gate 3)

The sweep validation, bias span and point count floors, least-squares
line and its coefficient of determination, built-in voltage
extrapolation and plausibility band, doping conversion from the slope,
graded power-law fit for the grading coefficient and zero-bias
capacitance, and forward-bias exclusion are exercised by the gate 3
contract test:
scripts/test_e2008_capacitance_model_determination.py against
scripts/e2008_capacitance_model_determination_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_capacitance_model_determination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
