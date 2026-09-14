---
name: e2008-coverglass-transmission-into-air
description: "Use when a coverglass transmission scan has been taken into air and the band figure must be derived and dispositioned. Compute the into-air spectral transmission of a coverglass from a spectrophotometer scan per ECSS-E-ST-20-08C clause 8.7.2: check the scan covers the specified wavelength band with strictly ascending, closely enough spaced sample points and a referenced baseline calibration, integrate the band-average transmittance by trapezoid, weight it with a supplied spectral irradiance when one is given, locate the cut-on wavelength by interpolation, and judge the average against the required minimum. Trigger: ecss, e-st-20-08c, clause-8-7-2, coverglass-transmission-into-air, coverglass-spectrophotometer-scan, coverglass-band-average-transmittance, coverglass-cut-on-wavelength, coverglass-spectral-sampling-interval."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-transmission-into-air, coverglass-spectrophotometer-scan, coverglass-band-average-transmittance, coverglass-cut-on-wavelength, coverglass-spectral-sampling-interval, coverglass-solar-weighted-transmission, solar-cell-assembly-optical-measurement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Transmission Into Air (space-systems/ecss/e2008-coverglass-transmission-into-air)

Use when the task is the transmission measurement of ECSS-E-ST-20-08C
clause 8.7.2 -- a spectrophotometer scan of the light that passes through
the coverglass and out into air, taken across the wavelengths the project
has specified, reduced to the band figure that closes the clause.

## Domain quick reference

- The measurement is into air. The far face of the glass in the
  instrument is an air interface, so the scan carries the rear-surface
  Fresnel reflection. The same coverglass bonded to a cell with an
  index-matched adhesive does not have that interface. The two figures are
  not interchangeable, and a bonded-stack number quoted here answers a
  different question from the one the clause asks.
- The scan is evidence only over the wavelengths it reaches. A band
  average taken from a scan that stops short of the specified band is an
  extrapolation wearing the band's name, so the coverage check runs before
  any integral is taken and stops the reduction when it fails.
- Sampling interval matters as much as coverage. A coverglass with a sharp
  cut-on can be sampled so coarsely that the edge falls between two
  samples and the trapezoid walks straight through it, reporting a band
  average the glass does not have. The widest gap between adjacent samples
  is the figure to compare against the specified interval, not the nominal
  step the instrument was set to.
- The band figure is an integral, not a mean of the recorded ordinates.
  Sample points are rarely evenly spaced and the band edges rarely land on
  one, so the average is a trapezoidal integral over the band with
  interpolated endpoints, divided by the band width. Averaging the raw
  ordinates lets a densely sampled region carry the whole figure.
- The solar-weighted average is the same integral with spectral irradiance
  as the weight, and it is the figure that tracks array power. It is
  reported when a weighting is supplied and never invented when it is not.
- A scan with no baseline calibration reference is an instrument trace,
  not a transmission measurement of the coverglass, and it closes the
  assessment rather than passing it.
- The cut-on wavelength is read by interpolating where the trace first
  rises through the threshold. A scan that already sits above the
  threshold at its first point has not measured the cut-on at all.

## Workflow

1. Validate the scan: two points or more, strictly ascending wavelengths,
   every transmittance a fraction between zero and one. Reject a repeated
   wavelength rather than quietly keeping one of the pair.
2. Confirm a baseline calibration reference is attached. Without it the
   reduction stops here.
3. Compare the scan span against the specified band. A short scan stops
   the reduction; report the span and the band side by side.
4. Take the widest adjacent-sample gap and compare it against the
   specified interval. Too coarse stops the reduction.
5. Integrate the band average by trapezoid over the band, interpolating
   the two band edges onto the scan, and divide by the band width.
6. When a spectral irradiance weighting is supplied, integrate the
   weighted average on the union of the scan and weighting nodes.
7. Interpolate the cut-on wavelength, or record the advisory when the
   trace starts above the threshold.
8. Judge the band average against the declared minimum. Report the margin
   either way; with no declared minimum, report the figure and say so.

## Pitfalls

- Quoting a bonded-stack or in-air-in-glass figure against this clause.
  The rear air interface is part of what is being measured.
- Averaging the recorded transmittance values. Unevenly spaced samples
  make that a weighted average with weights nobody chose.
- Integrating only between the outermost samples and calling it the band
  average when the scan is narrower than the band.
- Trusting the instrument's nominal step instead of measuring the gaps. A
  dropped sample widens one gap and only the measured maximum sees it.
- Reporting a solar-weighted figure computed from a weighting that does
  not span the band. The missing weight is not zero, it is unknown.
- Reading a cut-on from a scan that begins above the threshold. That
  wavelength lies below the scan and was never measured.
- Comparing a band average with a required minimum by bare arithmetic.
  The average is a trapezoidal sum divided by a band width, so a scan
  exactly on the requirement can evaluate a few units in the last place
  below it; the comparison absorbs that representation error while the
  requirement stays untouched.

## Behavior contract (gate 3)

The scan validation, band coverage and sampling-interval checks, the
trapezoidal band average with interpolated edges, the irradiance-weighted
average, the interpolated cut-on wavelength and the verdict against the
declared minimum are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_transmission_into_air.py against
scripts/e2008_coverglass_transmission_into_air_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_transmission_into_air.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
