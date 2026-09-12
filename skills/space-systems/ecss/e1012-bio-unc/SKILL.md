---
name: e1012-bio-unc
description: "Use when evaluate uncertainties in a space-radiation biological-effects
  assessment under ECSS-E-ST-10-12C §11.6: identify each required uncertainty source
  (radiation quality factor, dose-and-dose-rate effectiveness factor, cancer-risk
  coefficient from epidemiology, inter-population transfer model, and dosimetry and
  transport), combine the independent log-space components in quadrature to obtain a
  geometric standard deviation, derive the 95% confidence interval around the
  point-estimate risk value, assign a qualitative uncertainty level, and flag any
  required source type absent from the budget. Trigger: ecss, e-st-10-system-scope,
  biological-effects-uncertainty, quality-factor, ddref, cancer-risk,
  confidence-interval, dose-equivalent-uncertainty."
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
  tags: [ecss, e-st-10-system-scope, biological-effects-uncertainty, quality-factor, ddref, cancer-risk, confidence-interval, dose-equivalent-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Radiation — Biological-Effects Uncertainty (space-systems/ecss/e1012-bio-unc)

Use when the task is to evaluate and propagate uncertainties in a space-radiation
biological-effects assessment under ECSS-E-ST-10-12C §11.6 — verifying that all
required uncertainty sources are identified and quantified, combining them in the
lognormal quadrature model, deriving confidence bounds around the risk point
estimate, and confirming no required source has been omitted.

## Domain quick reference

- §11.6 identifies five independent uncertainty sources that must each be
  accounted for in a biological-effects risk assessment. Radiation quality
  factor uncertainty reflects the limited experimental basis for Q(L) at high
  LET (HZE ions above roughly 100 keV/µm carry the largest uncertainty in
  biological effectiveness). Dose-and-dose-rate effectiveness factor (DDREF)
  uncertainty arises from extrapolating high-dose, high-dose-rate laboratory
  exposures to the low-dose-rate chronic irradiation of the space environment;
  the DDREF is treated as a range (typically 1.5–2.5) rather than a fixed
  value. Cancer-risk coefficient uncertainty is the statistical uncertainty in
  the risk-per-unit-dose-equivalent derived from epidemiological cohorts,
  primarily A-bomb survivor data. Transfer model uncertainty reflects the
  systematic error in mapping risk estimates from the reference Japanese cohort
  to the astronaut population. Dosimetry and transport uncertainty captures
  errors in the computed or measured absorbed dose, including transport code
  accuracy and shielding geometry approximations.
- Each source is treated as lognormally distributed. Its magnitude is
  expressed as a sigma in natural-log space (sigma_log), which is the natural
  logarithm of the geometric standard deviation. A sigma_log of ln(2)/1.645
  means the 95th-percentile upper bound is a factor of 2 above the median.
- Independent uncertainty sources combine in quadrature in log space: the
  combined sigma_log is the square root of the sum of the squared individual
  sigma_log values. This preserves the lognormal model and avoids the
  under-estimation that results from arithmetic addition of asymmetric
  uncertainties.
- The 95% confidence interval is obtained by multiplying and dividing the
  point-estimate risk by exp(z_0.95 × combined_sigma_log), where z_0.95 ≈
  1.645 is the one-sided standard normal quantile at the 95th percentile.
  The resulting interval is asymmetric in linear space (the upper bound is
  farther from the median than the lower bound) and symmetric in log space.
- Qualitative uncertainty levels are assigned based on the 95th-percentile
  CI factor: less than ×2 is low; ×2 to ×4 is moderate; ×4 to ×8 is high;
  ×8 or more is very high.

## Workflow

1. Enumerate the five required uncertainty sources for the assessment: quality
   factor, DDREF, risk coefficient, transfer model, and dosimetry. Confirm
   that each source appears in the uncertainty budget; flag any source that is
   absent, because its omission invalidates the combined confidence interval.
2. For each present source, assign a sigma_log value derived from the
   supporting evidence (experimental spread, published uncertainty analysis, or
   expert elicitation). Document the basis for each assigned sigma_log; a
   sigma_log that is simply assumed without basis must be flagged as
   unquantified.
3. Validate each component: reject a component whose sigma_log is not a
   positive finite number, and reject a component whose source type is not one
   of the five required identifiers. An unknown source type indicates either a
   labelling error or an undocumented additional source that requires explicit
   engineering justification before it enters the combined budget.
4. Combine the validated components: compute the combined sigma_log as the
   square root of the sum of the squared individual sigma_log values. Do not
   add the sigma_log values directly (linear addition overstates the
   combination for independent lognormal components).
5. Derive the 95% confidence interval: multiply the point-estimate risk by
   exp(z × combined_sigma_log) for the upper bound and divide by the same
   factor for the lower bound, where z is the standard normal quantile at the
   chosen percentile (1.645 for 95%).
6. Label the combined uncertainty level from the 95th-percentile CI factor: if
   upper_CI / point_estimate < 2, the level is low; 2–4 is moderate; 4–8 is
   high; above 8 is very high.
7. Report the combined sigma_log, the lower and upper confidence bounds, the
   qualitative level, and the list of any missing required sources. A result
   with missing sources must not be accepted as a complete assessment.

## Pitfalls

- Combining sigma_log values by arithmetic sum instead of quadrature: the
  arithmetic sum is the correct rule only when the components are perfectly
  correlated (worst-case combination); for independent sources it
  over-estimates the combined uncertainty by treating every component as if it
  points in the same direction simultaneously.
- Using a symmetric (normal) confidence interval for a lognormal distribution:
  the correct interval is asymmetric in linear space; a symmetric ±σ interval
  allows the lower bound to become negative for large uncertainty, which is
  physically meaningless for a risk quantity that must remain non-negative.
- Treating DDREF as a fixed scalar rather than an uncertain quantity: DDREF
  is itself a variable derived from experimental dose-response models; locking
  it to a nominal value of 2 and omitting the DDREF source from the budget
  understates the combined uncertainty and typically violates §11.6
  requirements.
- Declaring an assessment complete when one or more required uncertainty
  sources are absent: the gap does not default to zero uncertainty — it
  indicates the source has not been evaluated and the combined interval is
  narrower than it should be, which may falsely suggest the risk is
  well-constrained.
- Applying the combined uncertainty interval directly to a point estimate
  derived from a different dose-rate regime without also applying the DDREF
  correction: the risk coefficient from epidemiological data applies to acute
  exposures; the DDREF adjustment and its uncertainty must both be carried
  through before the interval is meaningful for the chronic space exposure.

## Behavior contract (gate 3)

The uncertainty-component validation, quadrature combination in log space,
95% confidence-interval derivation, qualitative level labelling, and
completeness check are exercised by the gate 3 contract test:
scripts/test_e1012_bio_unc.py against scripts/e1012_bio_unc_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1012_bio_unc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
