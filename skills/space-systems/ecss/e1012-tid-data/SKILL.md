---
name: e1012-tid-data
description: "Use when determine the total ionizing dose (TID) degradation of a component or material from experimental test records under ECSS-E-ST-10-12C §7.6–7.7: extract the dose-response curve from laboratory TID test measurements, interpolate the parameter value at the mission design dose, apply an enhanced low dose-rate sensitivity (ELDRS) correction factor when bipolar semiconductor devices are present to account for greater on-orbit degradation at lower dose rates, apply a lot-variability margin to bound the worst-case parameter value across production lots, and compare the result against the functional limit to assess TID compliance. Trigger: ecss, e-st-10-system-scope, tid, total-ionizing-dose, tid-testing, degradation-prediction, eldrs, dose-rate, lot-variability."
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
  tags: [ecss, e-st-10-system-scope, tid, total-ionizing-dose, tid-testing, degradation-prediction, eldrs, dose-rate, lot-variability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Design — TID Degradation from Experimental Data (space-systems/ecss/e1012-tid-data)

Use when the task is to determine TID-induced degradation of a specific
component or material by applying measured dose-response data, as required
by ECSS-E-ST-10-12C §7.6–7.7. This leaf covers: extracting the dose-response
curve from TID test records, correcting for enhanced low dose-rate sensitivity
(ELDRS), bounding lot-to-lot variability, and checking the resulting
worst-case parameter value against the functional limit.

## Domain quick reference

- TID experimental data is expressed as a table of (dose_krad, parameter_value)
  pairs from laboratory irradiation runs (typically Co-60 gamma or X-ray). The
  parameter tracked depends on the component type: leakage current and
  threshold-voltage shift for MOS devices; gain (hFE) and input bias current
  for bipolar transistors; dark current for photodetectors; output voltage
  stability for linear regulators.
- ELDRS applies to bipolar devices only. High dose-rate lab tests can
  underestimate on-orbit degradation because the low flux in space allows more
  defect annealing-then-trapping cycles per unit dose. The ELDRS factor (ratio
  of low-dose-rate to high-dose-rate degradation, always >= 1.0) corrects the
  interpolated lab value before margin application.
- Lot-to-lot variability reflects manufacturing spread across production
  batches. A fractional margin (e.g. 0.20 for 20 %) applied in the worst-case
  direction bounds the range of parts likely to be procured from a given vendor.
- The functional limit is the parameter threshold at which the component no
  longer meets its circuit specification: a maximum for increasing parameters
  (leakage current, offset voltage) and a minimum for decreasing parameters
  (gain, power-supply rejection). Design margin is the percentage gap between
  the worst-case predicted value and the functional limit; negative margin
  indicates an exceedance.

## Workflow

1. Collect the TID test dataset for the component or material: a sorted list
   of (dose_krad, parameter_value) measurement pairs spanning at least the
   mission design dose, including any radiation design margin dose required by
   ECSS-E-ST-10-12C §7.3–7.5. If the design dose exceeds the maximum measured
   dose, request additional testing before proceeding; do not extrapolate.
2. Interpolate the parameter value at the design dose using the measured
   dose-response data. Linear interpolation between bracketing data points is
   acceptable for monotonic curves; flag any non-monotonic data for engineering
   review before interpolating.
3. For bipolar devices, determine the ELDRS factor (>= 1.0) from low dose-rate
   irradiation data or a device characterization report. Apply it to the
   interpolated value: multiply for an increasing parameter (degradation
   worsens by rising), divide for a decreasing parameter (degradation worsens
   by falling). For components with no ELDRS susceptibility, use factor 1.0.
4. Apply the lot-variability margin fraction (in [0, 1)) to the ELDRS-corrected
   value in the same worst-case direction: multiply by (1 + fraction) for
   increasing parameters, or multiply by (1 - fraction) for decreasing
   parameters. This produces the final predicted worst-case parameter value.
5. Compare the predicted value against the functional limit. Record the design
   margin in percent. Positive margin is compliant; negative margin is an
   exceedance requiring disposition (re-design, added shielding, part
   substitution, or a formal engineering waiver).
6. Document the test data source, ELDRS factor and its justification,
   lot-margin value and its basis, functional limit and its circuit derivation,
   and the compliance determination. This record feeds the TID assessment
   summary required by ECSS-E-ST-10-12C §7.8.

## Pitfalls

- Applying a high dose-rate lab measurement to a bipolar device without ELDRS
  correction — on-orbit degradation routinely exceeds the lab value, and
  omitting the correction understates risk.
- Extrapolating the dose-response curve beyond the maximum measured dose
  without a formal justification — degradation is often nonlinear and can
  accelerate at high dose; any extrapolation must be explicitly flagged,
  bounded, and reviewed.
- Using a lot-variability margin of zero when the component lacks lot-acceptance
  data — the absence of data does not imply zero spread; a default margin should
  be applied until test evidence is available.
- Treating zero design margin as compliant — a prediction that lands exactly on
  the functional limit carries no headroom for model uncertainty or test
  scatter; the radiation design margin policy requires positive margin.
- Conflating the ELDRS correction with the radiation design margin (RDM) — ELDRS
  is a physics correction applied to the measured parameter value, not a safety
  margin; the RDM is applied separately to the design dose before interpolation.

## Behavior contract (gate 3)

The interpolation, ELDRS correction, lot-margin, compliance check, and full
pipeline logic are exercised by the gate 3 contract test:
scripts/test_e1012_tid_data.py against scripts/e1012_tid_data_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_tid_data.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
