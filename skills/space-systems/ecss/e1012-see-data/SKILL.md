---
name: e1012-see-data
description: "Use when compute in-orbit single-event-effect rates and degradation
  predictions from experimental cross-section measurements per ECSS-E-ST-10C §9.4.2:
  validate the four-parameter Weibull fit (saturation cross-section, threshold LET,
  width, shape exponent) against physical constraints, integrate the fitted cross-section
  curve against the mission differential LET spectrum using the trapezoidal rule to
  obtain the predicted in-orbit SEE rate, and compare the result against the component
  hardness limit to assess compliance. Reject an invalid Weibull parameter set or
  an unsorted LET spectrum before integration proceeds. Trigger: ecss,
  e-st-10-system-scope, see-data, weibull-fit, single-event-effects, cross-section,
  let-spectrum, see-rate-prediction, hardness-limit."
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
  tags: [ecss, e-st-10-system-scope, see-data, weibull-fit, single-event-effects, cross-section, let-spectrum, see-rate-prediction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — SEE Experimental Data and Rate Prediction (space-systems/ecss/e1012-see-data)

Use when the task is predicting in-orbit single-event-effect rates from
accelerator-measured cross-section data under ECSS-E-ST-10C §9.4.2 —
validating the Weibull parameterisation, integrating the fitted curve
against the mission LET spectrum, and checking the result against the
component hardness limit.

## Domain quick reference

- Accelerator tests produce a set of measured SEE cross-section values
  (cm² per device or per bit) at discrete ion LET values
  (MeV·cm²/mg). These points are fitted to the Weibull sigmoid to give
  a continuous cross-section curve. The four Weibull parameters are:
  saturation cross-section σ_sat (asymptotic value at high LET),
  threshold LET L₀ (LET below which no SEEs occur), width parameter W
  (scale of the sigmoid rise), and shape exponent s (steepness).
  Physical constraints require σ_sat > 0, L₀ ≥ 0, W > 0, and s > 0;
  a parameter set that violates any of these must be rejected before use.
- The Weibull cross-section at LET L is:
  σ(L) = 0 for L ≤ L₀;
  σ(L) = σ_sat × (1 − exp(−((L − L₀)/W)^s)) for L > L₀.
  This function is zero at and below threshold and approaches σ_sat
  asymptotically for large L.
- The in-orbit SEE rate is the integral of σ(L) × φ(L) over LET, where
  φ(L) is the mission differential LET spectrum (events per cm² per
  second per unit LET). The integral is evaluated numerically using the
  trapezoidal rule over the discrete LET spectrum points supplied by the
  environment model. The LET spectrum must be sorted in ascending LET
  order; a non-ascending or duplicate-LET input must be rejected.
- Each component carries a hardness limit (maximum allowable SEE rate in
  events per second). The predicted rate is compared against this limit;
  if the rate exceeds the limit the component is non-compliant. The
  compliance margin is the ratio of the limit to the predicted rate; a
  margin below 1.0 indicates a violation.

## Workflow

1. Collect the four Weibull fit parameters (σ_sat, L₀, W, s) from the
   component test report and validate each parameter against its physical
   constraint: σ_sat > 0, L₀ ≥ 0, W > 0, s > 0. Reject the parameter
   set with a clear error if any constraint is violated; do not proceed
   to integration with an invalid fit.
2. Obtain the mission differential LET spectrum from the approved
   environment model for the target orbit and shielding configuration.
   Verify that the spectrum points are provided as (LET, flux) pairs
   sorted in ascending LET order with no duplicate LET values; reject an
   unsorted or empty spectrum before integration.
3. Evaluate the Weibull cross-section σ(L) at each LET point in the
   spectrum. For any LET at or below L₀ the cross-section is zero; for
   LET above L₀ apply the Weibull formula.
4. Apply the trapezoidal rule across adjacent spectrum intervals:
   rate = Σ 0.5 × (σ(Lᵢ) × φᵢ + σ(Lᵢ₊₁) × φᵢ₊₁) × (Lᵢ₊₁ − Lᵢ).
   Sum over all intervals to obtain the predicted in-orbit SEE rate
   (events per second).
5. Compare the predicted rate against the component hardness limit.
   Compute the compliance margin as limit / rate (undefined when rate is
   zero). Flag the component as non-compliant if the predicted rate
   exceeds the limit; flag a missing or unset limit as an open finding
   rather than an implicit pass.
6. Report the predicted rate, compliance margin, and compliance status
   alongside the Weibull parameters and the orbit/shielding inputs used,
   so the result is traceable to the test data and environment model.

## Pitfalls

- Applying the Weibull formula for LET values at or below the threshold
  L₀: the result is mathematically zero but a negative argument to the
  power function can produce a complex or domain error depending on the
  shape exponent. Always return zero explicitly for L ≤ L₀.
- Treating an unsorted LET spectrum as acceptable: the trapezoidal rule
  requires monotonically increasing LET. An unsorted input produces a
  sign error in the interval width (Lᵢ₊₁ − Lᵢ becomes negative) and
  silently gives a wrong result. Validate sort order before integrating.
- Using only two asymptotic points (both near saturation) and reading
  the near-σ_sat rate as conservative: the integral of a flat function
  near saturation multiplied by the flux at those LET values may
  substantially overestimate or underestimate the rate depending on
  where the flux peaks relative to the Weibull knee.
- Omitting the hardness limit check and reporting only the predicted
  rate: a rate without a comparison against the requirement gives no
  compliance verdict; an unset limit is itself a finding that must be
  recorded, not treated as an automatic pass.

## Behavior contract (gate 3)

The Weibull parameter validation, cross-section evaluation, LET spectrum
integration, and hardness-limit comparison logic are exercised by the
gate 3 contract test: scripts/test_e1012_see_data.py against
scripts/e1012_see_data_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_see_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
