---
name: e1012-dose-margins
description: "Use when compute deposited dose with margin split across environment, shielding, and susceptibility uncertainties per ECSS-E-ST-10-12C §5.4: derive the nominal absorbed dose from the environment model, apply the three independent uncertainty factors (environment, shielding, susceptibility) to obtain the design dose, compute the margin ratio against the component lot-testing threshold, and determine whether each part meets the required design margin. Trigger: ecss, e-st-10-system-scope, dose-margin, total-ionizing-dose, radiation-hardness, uncertainty-factor, design-dose, shielding-uncertainty, susceptibility-uncertainty."
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
  tags: [ecss, e-st-10-system-scope, dose-margin, total-ionizing-dose, radiation-hardness, uncertainty-factor, design-dose, shielding-uncertainty]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Effects — Deposited Dose with Margin Split (space-systems/ecss/e1012-dose-margins)

Use when the task is to compute the total deposited dose for a spacecraft
component and verify that the combined design margin across environment,
shielding, and susceptibility uncertainties satisfies the required margin
factor per ECSS-E-ST-10-12C §5.4.

## Domain quick reference

- §5.4 of ECSS-E-ST-10-12C requires that the radiation design dose be
  derived from the nominal environment dose by multiplying in three
  independent uncertainty factors: environment uncertainty (k_env),
  shielding uncertainty (k_shield), and susceptibility uncertainty
  (k_suscept). Each factor is a dimensionless number ≥ 1.0 capturing
  one source of conservatism; they are applied multiplicatively, not
  as a single lumped margin.
- The design dose D_design = D_nominal × k_env × k_shield × k_suscept,
  where D_nominal is the absorbed dose computed from the approved
  environment model (e.g. AE8/AP8 trapped particles, JPL-91 solar
  proton model, ISO-15390 GCR) integrated over the mission duration
  behind the specified shielding thickness.
- The margin ratio M = T_lot / D_design, where T_lot is the total
  ionizing dose (TID) threshold established by lot-acceptance testing
  of the component lot. A margin ratio ≥ the required margin (typically
  2.0 for EEE parts without enhanced screening) indicates the part
  passes. A margin ratio < 1.0 means the design dose already exceeds
  the tested threshold — an unconditional failure.
- Uncertainty factors have standard default starting values that the
  programme may tighten through additional analysis or testing:
  k_env ≥ 2.0 (environment model conservatism), k_shield ≥ 1.5
  (shielding analysis tolerance), k_suscept ≥ 1.0 (worst-case lot
  screening). The required margin applied on top of these factors
  depends on the criticality of the part and the programme's radiation
  design policy.

## Workflow

1. For each component under assessment, record the nominal absorbed dose
   D_nominal (rad(Si)) from the approved environment analysis at the
   component location, using the shielding configuration assumed for
   that part position.
2. Assign the three uncertainty factors. If a factor is not yet
   justified by analysis, use the standard default (k_env = 2.0,
   k_shield = 1.5, k_suscept = 1.0). Record any deviation from defaults
   with a justification reference.
3. Compute the design dose: multiply D_nominal by k_env, k_shield, and
   k_suscept in sequence. Report D_design in rad(Si).
4. Retrieve the component's TID threshold T_lot from the lot-acceptance
   test report. If T_lot is not available, record the component as
   having an unresolved threshold — do not estimate.
5. Compute the margin ratio M = T_lot / D_design.
6. Compare M against the programme-required margin (default 2.0). A
   component is margin-compliant when M ≥ required margin. Flag any
   component where M < required margin and record which uncertainty
   factor contributes most to D_design.
7. Flag separately any component whose T_lot record is absent — these
   cannot be margin-checked and represent an open action independent of
   the numerical margin outcome.
8. Aggregate results: a component is fully radiation-margin-verified
   only when it is margin-compliant and T_lot is on record.

## Pitfalls

- Applying a single lumped margin factor instead of splitting across
  the three uncertainty axes — §5.4 requires independent traceability
  of each factor so that targeted re-testing or improved analysis can
  buy back margin on one axis without disturbing the others.
- Using the nominal dose directly as the design dose — the nominal dose
  is the best-estimate model output, not the design value; the three
  factors are mandatory conservatism, not optional reserves.
- Treating a missing T_lot as "implicitly infinite" and declaring a
  pass — an unresolved threshold is an open action, not a passing state.
- Conflating the margin ratio with a safety factor applied to the
  environment model alone — the margin ratio spans the full chain from
  environment through shielding through susceptibility; halving k_env
  alone while leaving the others unchanged moves the design dose by
  only one axis and still requires margin verification on the result.
- Allowing k_suscept < 1.0 — susceptibility factors encode worst-case
  lot variation and cannot be less than 1.0 without lot-specific data
  explicitly approved by the radiation authority.

## Behavior contract (gate 3)

The design-dose computation, margin-ratio calculation, compliance check,
and error-path logic are exercised by the gate 3 contract test:
scripts/test_e1012_dose_margins.py against
scripts/e1012_dose_margins_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1012_dose_margins.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
