---
name: e2008-bare-cell-spectral-response
description: "Use when a simulator verification record or spectral response data set has to be assessed. Compute the spectral response quantities that clause 7.5.5 of ECSS-E-ST-20-08C puts behind sun simulator verification and measurement error assessment: validate the curve rises through strictly increasing wavelengths at a fine enough step and covers the band the cell responds in, convert absolute response into external quantum efficiency and refuse a point above unity, integrate test and reference responses against the simulator and reference spectra, then form the spectral mismatch factor and express it as the measurement error it contributes. Trigger: ecss, e-st-20-08c-clause-7-5-5, bare-solar-cell-spectral-response, sun-simulator-spectral-mismatch-factor, bare-cell-quantum-efficiency-conversion, spectral-measurement-error-budget."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-spectral-response, e-st-20-08c-clause-7-5-5, bare-solar-cell-spectral-response, sun-simulator-spectral-mismatch-factor, bare-cell-quantum-efficiency-conversion, spectral-measurement-error-budget, bare-cell-response-band-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells — Spectral Response (space-systems/ecss/e2008-bare-cell-spectral-response)

Use when the task is clause 7.5.5 of ECSS-E-ST-20-08C: the spectral response of
the bare cells, measured because it is what makes every later sun simulator
measurement defensible. The curve is not an end in itself. It is the input that
lets a simulator be verified against the reference spectrum and lets the error
the spectral difference contributes be put a number on.

## Domain quick reference

- The mismatch factor needs four integrals, not two. Test device against the
  simulator spectrum, test device against the reference spectrum, reference
  device against each of the same two. Only that combination cancels the areas
  and the absolute calibrations out and leaves the spectral difference behind.
- A factor of one is the statement that, for this particular pair of devices,
  the simulator spectrum and the reference spectrum are indistinguishable. It
  is a property of the pair, not of the simulator alone; the same simulator
  carries a different factor against a different cell technology.
- The four curves arrive on four different grids. Every supplier samples where
  their instrument sampled, so the integrals only mean anything after all four
  are interpolated onto one common wavelength grid.
- Quantum efficiency is the honesty check on an absolute response. Above one
  carrier per photon a device is not remarkable, it is miscalibrated, and the
  response curve that produced it will poison every integral it enters.
- Coverage is not a formality. A response curve that stops short of the band
  the cell responds in silently zeroes the missing region, and the integral
  then reports a smaller device rather than an incomplete measurement.
- Sampling step is an integration error, not a data volume preference. The
  trapezoidal rule interpolates straight lines between points, so a coarse grid
  across a response knee cuts the corner and biases the integral one way every
  time.

## Workflow

1. Validate every curve as a curve: at least two points, wavelengths strictly
   increasing, responses non-negative. Repeated or out-of-order wavelengths are
   refused rather than sorted, since the order carries information about how
   the file was assembled.
2. For each response curve, measure the widest gap between neighbouring
   wavelengths and hold it against the declared sampling limit, and check the
   curve reaches both edges of the required response band.
3. Convert each response point into external quantum efficiency using the
   photon energy at its own wavelength, and report any curve whose peak sits
   above one carrier per photon.
4. Build one common wavelength grid from the union of all four curves and
   interpolate each onto it, treating a wavelength outside a curve as no
   response and no irradiance rather than extrapolating.
5. Form the four weighted integrals by the trapezoidal rule and assemble the
   spectral mismatch factor from them, refusing the case where the denominator
   collapses because the curves and the spectra share no overlap.
6. Express the departure from unity as a percentage and hold it against the
   declared error budget, absorbing floating-point representation error at the
   budget edge with a named tolerance rather than by widening the budget.

## Pitfalls

- Comparing the two response curves directly instead of forming the factor.
  Two devices differ in area and calibration as well as in spectral shape, and
  only the four-integral combination removes everything but the shape.
- Integrating each curve on its own grid and dividing the results. The grids
  differ, so the quotient mixes a spectral difference with a sampling
  difference and nobody can separate them afterwards.
- Extrapolating a response curve past its last measured wavelength to reach the
  spectrum's range. That invents device behaviour; treating the region as zero
  at least leaves a coverage finding visible.
- Reading a mismatch factor as a simulator grade. It belongs to the pair of
  devices, and quoting it without the reference device it was taken against
  makes it unreproducible.
- Accepting a quantum efficiency above unity because the response curve came
  from a calibration house. The conversion is arithmetic; a value above one
  says the absolute calibration is wrong, whoever supplied it.
- Sampling the response coarsely where it changes fastest. The integral still
  returns a number, and the number is biased in the same direction on every
  repeat, which is exactly the kind of error a repeatability check will miss.

## Behavior contract (gate 3)

The curve validation, the sampling step and band coverage checks, the quantum
efficiency conversion and its unity ceiling, the common-grid interpolation, the
trapezoidal weighted integrals, the spectral mismatch factor, the unity
cancellation cases and the error budget comparison are exercised by the gate 3
contract test: scripts/test_e2008_bare_cell_spectral_response.py against
scripts/e2008_bare_cell_spectral_response_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2008_bare_cell_spectral_response.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
