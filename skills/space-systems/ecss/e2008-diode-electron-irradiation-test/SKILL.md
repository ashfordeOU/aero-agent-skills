---
name: e2008-diode-electron-irradiation-test
description: "Analyze how far an external protection diode drifts as electron fluence accumulates in the accelerated life exposure of ECSS-E-ST-20-08C clause 9.6.12: check the fluence staircase rises and carries an unirradiated reference, confirm every step was measured at the reference temperature, turn each step's forward drop and reverse leakage into ratios against that reference, refuse a ratio that falls back, fit the forward drift against the logarithm of fluence and the leakage growth as a power law, flag a step off its own curve, and project both to the mission end-of-life fluence. Use when a protection diode electron irradiation run is scoped or its data is audited. Trigger: ecss, e-st-20-08c-clause-9-6-12, protection-diode-electron-irradiation-test, diode-electron-fluence-staircase, diode-forward-voltage-drift-with-fluence, diode-reverse-leakage-growth-with-fluence, diode-degradation-log-fit, diode-electron-eol-projection."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-electron-irradiation-test, protection-diode-electron-irradiation-test, diode-electron-fluence-staircase, diode-forward-voltage-drift-with-fluence, diode-reverse-leakage-growth-with-fluence, diode-degradation-log-fit, diode-electron-eol-projection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Electron Irradiation Test (space-systems/ecss/e2008-diode-electron-irradiation-test)

Use when the task is the electron irradiation test of ECSS-E-ST-20-08C clause
9.6.12 -- reading a staircase of electron exposures on external protection
diodes as a life curve rather than a set of readings, so what the diode still
does at the mission's end-of-life fluence can be projected and defended
against the string budget it sits in.

## Domain quick reference

- Every number in this test is a ratio. The unirradiated measurement is the
  denominator of everything that follows, so it belongs in the article's
  record rather than being treated as a preliminary; a run without it produces
  absolute readings no power budget can use.
- A protection diode degrades in two directions and they are not symmetric.
  Displacement damage cuts carrier lifetime, so the forward drop grows and the
  extra volts come straight out of the string. Damage also adds generation
  centres, so reverse leakage grows -- typically by orders of magnitude, not
  by percent.
- That asymmetry decides the arithmetic. The forward-drop multiple is fitted
  directly against the logarithm of fluence; the leakage multiple is fitted in
  its own logarithm, because a quantity that climbs by decades is a power law
  and fitting it linearly throws the projection away.
- A ratio is only a damage number if both readings were taken the same way. A
  junction's forward drop moves with temperature all on its own, so a step
  measured warm reports the bench and the beam gets the blame.
- Damage accumulates per decade of fluence, not per unit of it, which is why
  the steps are spaced by factors of ten and why the slope worth quoting is
  per decade.
- Damage does not anneal back mid-staircase. A step reporting less drift than
  the exposure before it is a dosimetry or a measurement finding, and so is a
  step sitting off the curve its neighbours fall on.
- The end-of-life fluence is a mission input, not a test input. The staircase
  usually runs past it on purpose, and the projection is read at the mission
  number rather than at the highest exposure the beam happened to reach.

## Workflow

1. Validate the exposure policy first: reference temperature and its
   tolerance, the fewest irradiated steps a curve may be drawn through, the
   monotonicity and residual allowances, and the end-of-life limits. A limit
   below unity, which would ask the diode to improve under irradiation, is
   refused rather than used.
2. Read the unirradiated reference. A run without it closes immediately,
   because nothing later in the staircase has a denominator.
3. Read every step and confirm the staircase rises. A repeated or falling
   exposure leaves the accumulated fluence at each reading undefined.
4. Check the reference and every step against the measurement temperature
   band before converting anything, and close on inconsistent conditions when
   any of them sat outside it.
5. Turn each step's forward drop and reverse leakage into ratios against the
   reference, and keep the raw readings beside them so a revised reference can
   be applied without re-irradiating anything.
6. Refuse a series that falls back. Report how many steps did it rather than
   the first one, so the dosimetry is repaired once.
7. Fit the forward ratios against the logarithm of fluence and the leakage
   ratios in their own logarithm, report both slopes per decade, and close on
   a step whose relative distance from its fitted curve exceeds the allowance.
8. Project both parameters to the mission end-of-life fluence and compare
   against the string and blocking limits, reporting both exceedances together
   when both are present.
9. Close on one verdict: unirradiated reference missing, fluence staircase
   invalid, measurement conditions inconsistent, degradation not monotonic,
   step off the degradation curve, end-of-life limit exceeded, or diode
   degradation characterized.

## Pitfalls

- Quoting the highest exposure reached as the qualification result. The beam
  ran past end of life to save time; the number the mission needs is read off
  the curve at the mission fluence.
- Fitting leakage linearly against fluence. A quantity that climbs by decades
  is dominated by its last point, and the projection is then set by one
  reading.
- Reporting drift without the measurement temperature. A junction moves with
  temperature on its own, and the ratio silently absorbs a warm bench.
- Explaining a step that sits off the curve as annealing. Displacement damage
  does not recover mid-staircase at these temperatures, so the finding belongs
  to the dosimetry or the measurement.
- Discarding the raw readings once the ratios are computed. A revised
  unirradiated reference then cannot be applied, and the article has to be
  irradiated again to recover a number it already produced.
- Carrying one device's degradation slope onto another part number. The slope
  is a property of the junction and its process, not of the beam.

## Behavior contract (gate 3)

The policy validation, the reference and step reads, the staircase rise, the
decade span, the measurement-condition band, the two damage ratios, the
monotonicity check, the log-fluence fit and its slope per decade, the relative
residual, the power-law leakage projection, the forward projection and the run
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_diode_electron_irradiation_test.py against
scripts/e2008_diode_electron_irradiation_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_electron_irradiation_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
