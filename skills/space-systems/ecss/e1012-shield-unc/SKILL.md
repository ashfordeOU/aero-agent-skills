---
name: e1012-shield-unc
description: "Use when determine shielding calculation uncertainties for a spacecraft radiation analysis under ECSS-E-ST-10C §6.4: identify each uncertainty contributor as model (transport-code assumptions and dose-conversion factors), geometry (simplified mesh versus as-built structural detail), or cross-section (nuclear reaction data spread), assign a fractional uncertainty to each contributor, combine them by RSS or linear worst-case summation, apply a k-sigma margin to the nominal computed dose or fluence, and verify the margined result remains within the allowable shielding requirement. Trigger: ecss, e-st-10-system-scope, shielding-uncertainty, model-uncertainty, geometry-uncertainty, cross-section-uncertainty, radiation-margin, dose-budget."
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
  tags: [ecss, e-st-10-system-scope, shielding-uncertainty, model-uncertainty, geometry-uncertainty, cross-section-uncertainty, radiation-margin, dose-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Shielding Calculation Uncertainties (space-systems/ecss/e1012-shield-unc)

Use when the task is to determine and propagate the uncertainties in a
spacecraft shielding calculation per ECSS-E-ST-10C §6.4 — covering model
errors in the transport code, geometric simplifications of the structural
model, and nuclear cross-section data spread — so that a margin-adjusted
dose or fluence can be checked against the shielding requirement.

## Domain quick reference

- §6.4 identifies three uncertainty families that affect a shielding result:
  model uncertainty (approximations built into the radiation transport code and
  dose-conversion methodology), geometry uncertainty (difference between the
  simplified mesh used in the analysis and the actual as-built spacecraft
  structure), and cross-section uncertainty (spread in the nuclear reaction
  data libraries used to model particle interactions). Each contributor is
  assigned to exactly one family before its magnitude is estimated.
- A fractional uncertainty is assigned to each contributor as a dimensionless
  ratio (0 to 1). Contributors within or across families are combined either
  by root-sum-square (RSS) for statistically independent contributors or by
  linear worst-case sum for correlated or conservatively treated contributors.
  RSS yields a smaller combined uncertainty; worst-case is used when
  correlations between contributors cannot be ruled out.
- The combined fractional uncertainty is applied to the nominal shielded dose
  or fluence via a k-sigma margin: margined value = nominal × (1 + k ×
  combined_unc). k = 1 represents a one-sigma margin; k = 2 a two-sigma margin.
  The margined value must not exceed the shielding requirement; if it does,
  the nominal shielding thickness is insufficient or the uncertainty estimate
  must be revisited.

## Workflow

1. Enumerate all contributors to shielding result uncertainty and assign each
   to one of three families: model, geometry, or cross-section. Reject any
   contributor whose family cannot be determined before it enters the budget.
2. For each contributor, assign a fractional uncertainty value in [0, 1] backed
   by analysis, literature data, or engineering judgement. Document the
   rationale for each value.
3. Select the combination method: RSS when contributors are independent, linear
   worst-case when they are correlated or when a conservative bound is required
   by the project's radiation design margin policy.
4. Combine the fractional uncertainties using the selected method to produce a
   single combined fractional uncertainty for the calculation.
5. Apply the k-sigma margin to the nominal computed dose or fluence to obtain
   the uncertainty-margined result.
6. Compare the margined result against the shielding requirement. Flag an
   exceedance and identify the dominant uncertainty family to guide where
   analysis effort should be focused to reduce the combined uncertainty.

## Pitfalls

- Assigning the same contributor to more than one uncertainty family — each
  source of error belongs to exactly one family; double-counting inflates the
  combined uncertainty and overstates the margin requirement.
- Using RSS combination when contributors share a common input (e.g., both
  model and geometry uncertainty driven by the same simplified orbit model) —
  correlated sources must be combined linearly to avoid underestimating the
  combined effect.
- Treating a missing k value as equivalent to k = 0 — a zero margin means the
  nominal result is used directly against the requirement, which may violate
  the project's radiation design margin policy even if the nominal result
  passes.
- Accepting a result as compliant when the fractional uncertainty for any
  contributor is unsubstantiated — an engineering-judgement placeholder that
  has not been reviewed and accepted by the project carries a hidden risk that
  the true uncertainty exceeds the budget.

## Behavior contract (gate 3)

The uncertainty-source validation, RSS and worst-case combination, margin
application, and compliance-check logic are exercised by the gate 3 contract
test: scripts/test_e1012_shield_unc.py against
scripts/e1012_shield_unc_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_shield_unc.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
