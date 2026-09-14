---
name: e2008-cell-electron-irradiation-test
description: "Use when a bare-cell electron irradiation run is scoped or its data is audited. Analyze how much electrical output a bare solar cell loses as electron fluence accumulates in the accelerated life exposure of ECSS-E-ST-20-08C clause 7.5.13: check the fluence staircase rises and carries an unirradiated reference, confirm every step was measured at the reference temperature and illumination, turn each step's current, voltage and maximum power into remaining factors, refuse a factor that climbs as fluence rises, fit each against the logarithm of fluence, flag a step off its own curve, and project the end-of-life retention. Trigger: ecss, e-st-20-08c-clause-7-5-13, bare-cell-electron-irradiation-test, bare-cell-electron-fluence-staircase, bare-cell-remaining-factor-monotonicity, bare-cell-degradation-log-fit, bare-cell-electron-eol-retention."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-cell-electron-irradiation-test, bare-cell-electron-irradiation-test, bare-cell-electron-fluence-staircase, bare-cell-remaining-factor-monotonicity, bare-cell-degradation-log-fit, bare-cell-electron-eol-retention]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Cell Electron Irradiation Test (space-systems/ecss/e2008-cell-electron-irradiation-test)

Use when the task is the bare-cell electron irradiation test of
ECSS-E-ST-20-08C clause 7.5.13 -- reading a staircase of electron exposures on
bare cells as a life curve rather than a set of readings, so the fraction of
current, voltage and maximum power the cell still holds at the mission's
end-of-life fluence can be projected and defended.

## Domain quick reference

- Every number in this test is a ratio. The unirradiated measurement is the
  denominator of everything that follows, so it is part of the test article's
  record, not a preliminary; a run without it produces absolute readings that
  no power budget can use.
- A ratio is only a damage number if both measurements were taken the same way.
  Cell voltage moves with temperature and current moves with illumination, so a
  step measured warmer or under a different lamp setting reports the measurement
  bench, and the beam gets the blame.
- Degradation is logarithmic in fluence, not linear. Retention falls by roughly
  a fixed amount per decade of fluence, which is why the steps are spaced by
  decades and why the fit is taken against the logarithm; fitting against
  fluence itself throws the low-fluence points away.
- The three parameters do not degrade together. Short-circuit current follows
  the loss of minority carrier diffusion length, open-circuit voltage moves
  more slowly, and maximum power falls faster than either because it carries
  both, so each parameter gets its own fit and its own projection.
- Damage does not heal between steps. A remaining factor that rises with
  fluence, or that sits above the unirradiated value, is a probe, a contact or
  a bench condition -- never a cell that recovered -- and it invalidates the
  step rather than improving the curve.

## Workflow

1. Validate the fluence staircase: every point positive and strictly above the
   one before it, at least two points so a fit exists, and an unirradiated
   reference measurement present.
2. Compare each step's measurement temperature and illumination against the
   reference, treating a value exactly on the tolerance as comparable.
3. Divide each step's reading by the unirradiated reading, parameter by
   parameter, to get remaining factors.
4. Check each parameter's factors fall: a rise beyond the measurement noise
   allowance, or a factor above the cell's own starting point, is a finding.
5. Fit each parameter's factors against the natural logarithm of fluence, and
   convert the slope into the retention lost per decade so the curve can be
   read without the logarithm.
6. Compare every measured step with its own fit and flag one that departs by
   more than the allowed residual.
7. Project the retention at the end-of-life fluence from each fit, compare it
   with what the power budget requires, and report factors, fit, per-decade
   loss, projection, findings and verdict.

## Pitfalls

- Reporting an absolute reading after irradiation. Without the unirradiated
  reading from the same cell on the same bench the number carries the cell's
  own spread rather than the damage.
- Fitting retention against fluence instead of its logarithm. The last decade
  then dominates the fit and the low-fluence points, which set the early-life
  behaviour, contribute almost nothing.
- Extrapolating far past the last measured step. A projection a decade beyond
  the run is a curve prediction, not a measurement, and the gap should be
  reported with the number.
- Treating a factor above unity as a good result. It means the two measurements
  are not comparable, and the run is missing the condition check that would
  have caught it.
- Taking one parameter's degradation as the cell's. Maximum power falls faster
  than current or voltage alone, so a run that tracks only current understates
  what the array loses.
- Averaging the three parameters into one retention number. The power budget
  needs power, and the other two are how the loss is explained, not summed.

## Behavior contract (gate 3)

The fluence staircase validation, measurement-condition comparison, remaining
factor derivation, monotonicity and above-unity checks, logarithmic fit,
per-decade retention loss, residual outlier flagging and the end-of-life
projection against the required retention are exercised by the gate 3 contract
test: scripts/test_e2008_cell_electron_irradiation_test.py against
scripts/e2008_cell_electron_irradiation_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_cell_electron_irradiation_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
