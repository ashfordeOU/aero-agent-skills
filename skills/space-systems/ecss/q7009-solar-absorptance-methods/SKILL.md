---
name: q7009-solar-absorptance-methods
description: "Compute the solar absorptance of a thermal-control surface by solar-weighted spectral integration and reconcile it with a calorimetric determination and a certified reference standard, under ECSS-Q-ST-70-09C. Use when a spectrophotometric reflectance scan, a steady-state calorimetric run, or both, have to become one defensible absorptance carrying its uncertainty. Weights measured absorptance by the solar spectral irradiance over the scanned span, reports the fraction of that irradiance the span actually carries, rescales a relative scan through the certified reflectance of the standard, and grades the two routes on their combined expanded uncertainty. Trigger: ecss, q-st-70-09, solar-absorptance-spectrophotometric-integration, solar-weighted-reflectance, calorimetric-solar-absorptance, certified-reflectance-standard, solar-spectral-coverage-fraction, absorptance-method-agreement."
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
  tags: [ecss, q-st-70-thermo-optical-scope, q7009-solar-absorptance-methods, solar-absorptance-spectrophotometric-integration, solar-weighted-reflectance, calorimetric-solar-absorptance, certified-reflectance-standard, solar-spectral-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermo-Optical Measurement — Solar Absorptance Methods (space-systems/ecss/q7009-solar-absorptance-methods)

Use when the task is the solar-absorptance determination of
ECSS-Q-ST-70-09C — turning a spectral scan, a reference-standard
transfer or a calorimetric run into the single absorptance figure a
thermal model will be built on, and saying whether that figure is
defensible.

## Domain quick reference

- Solar absorptance is a weighted average, not a measured quantity. The
  instrument measures spectral reflectance; the absorptance is the
  spectral absorptance averaged with the solar spectral irradiance as
  the weight. Two surfaces with the same average reflectance and
  different spectral shapes have different solar absorptance.
- The weight makes the scan span matter. A scan that stops short of the
  near-infrared leaves out irradiance that still has to be absorbed
  somewhere, and the weighted integration quietly renormalises over what
  was measured. The covered fraction of the solar irradiance therefore
  travels with the result.
- A spectrophotometer with an integrating sphere reads relative to a
  standard, not absolutely. The scan is a ratio, and it becomes a
  reflectance only after being multiplied by the certified reflectance
  of that standard at the same wavelengths. A transfer landing above
  unity says the scan and the standard do not belong together.
- The calorimetric route measures the same property through a different
  physics: at steady state the absorbed solar flux equals the radiated
  flux plus the parasitic losses, so the absorptance falls out of the
  temperature the specimen settles at, its emittance and its areas. It
  is sensitive to the loss terms in exactly the region where the
  spectral route is not.
- Two routes agreeing is evidence; two routes differing by more than
  their combined expanded uncertainty is a finding about the
  measurement, not a reason to average. The normalised error ratio is
  the statement, and it needs both uncertainties to be real.

## Workflow

1. Validate every spectral table: wavelengths strictly increasing and
   positive, reflectance-like values inside the unit interval, spectral
   irradiance non-negative. A table with one point, a repeated
   wavelength or a boolean is an input error.
2. If the scan is relative, transfer it through the certified
   reflectance of the reference standard interpolated at the scan
   wavelengths, and refuse a transferred value above unity.
3. Form the spectral absorptance as one minus reflectance, less
   transmittance where the surface transmits, and refuse a point where
   the two already exceed unity.
4. Integrate the spectral absorptance against the solar spectral
   irradiance over the span both tables share, using a grid that keeps
   every node of both tables so no structure is interpolated away.
5. Report the covered irradiance fraction alongside the result and
   compare it with the coverage floor, absorbing representation error at
   the boundary with a named tolerance.
6. Where a calorimetric run exists, close the steady-state balance for
   its absorptance, carrying the parasitic loss explicitly rather than
   folding it into the emittance.
7. Grade the two determinations on their combined expanded uncertainty
   and report the normalised error, then declare the result reportable
   only when no finding stands.

## Pitfalls

- Reporting an unweighted average reflectance as solar absorptance. It
  is the same arithmetic with the wrong weight, and it flatters exactly
  the surfaces whose reflectance rises through the near-infrared.
- Letting a short scan renormalise silently. The integration divides by
  the irradiance it covered, so a scan over two thirds of the spectrum
  still returns a plausible number, with the missing third simply
  assumed to behave like the measured part.
- Treating a relative scan as an absolute reflectance. The certified
  standard is typically a few percent below unity, so the omission
  biases every absorptance in one direction by an amount that looks like
  instrument drift.
- Folding the parasitic losses of a calorimetric rig into the emittance
  to make the balance close. That moves the error into a second reported
  property and makes the two determinations agree for the wrong reason.
- Averaging a spectral and a calorimetric result that disagree. Beyond
  the combined expanded uncertainty the disagreement is information
  about the measurement, and the mean of two inconsistent numbers is
  supported by neither.
- Relaxing the coverage floor or the coverage factor so a marginal case
  passes. An equality at the limit is a representation question, handled
  by the tolerance inside the comparison; the limits stay as specified.

## Behavior contract (gate 3)

The spectral-table validation, reference-standard transfer,
solar-weighted integration with its coverage fraction, calorimetric
steady-state balance and the method-agreement grading are exercised by
the gate 3 contract test:
scripts/test_q7009_solar_absorptance_methods.py against
scripts/q7009_solar_absorptance_methods_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7009_solar_absorptance_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
