---
name: e1012-dose-effects
description: "Use when assessing radiation dose-effects margin compliance for electronic
  components under ECSS-E-ST-10 §5.5.2: apply the radiation design margin factor to
  the predicted component dose, compare the result against each component's specified
  tolerance, check parametric degradation limits (gain, leakage current, threshold
  voltage) against allowable change fractions, verify functional continuity at the
  margin-multiplied dose, and flag every component that fails a dose, parametric, or
  functional limit. Trigger: ecss, e-st-10-system-scope, dose-effects,
  radiation-design-margin, total-ionizing-dose, parametric-degradation,
  functional-degradation, component-tolerance."
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
  tags: [ecss, e-st-10-system-scope, dose-effects, radiation-design-margin, total-ionizing-dose, parametric-degradation, functional-degradation, component-tolerance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Component Dose-Effects Margin Factors (space-systems/ecss/e1012-dose-effects)

Use when the task is applying component dose-effects margin factors per
ECSS-E-ST-10 §5.5.2 — determining whether each electronic component's
radiation tolerance, after multiplication by the radiation design margin
(RDM), is met, and whether its parametric and functional degradation limits
remain within specification.

## Domain quick reference

- §5.5.2 requires that the predicted component dose (from the mission
  radiation environment analysis) be multiplied by a margin factor —
  the radiation design margin — before comparing to the component's
  specified tolerance. The standard RDM is 2.0 unless a project-specific
  value is justified and formally agreed.
- Two degradation checks supplement the tolerance comparison:
  (a) **parametric degradation** — each performance parameter (gain,
  leakage current, threshold voltage, etc.) has an allowable change
  fraction relative to its pre-irradiation nominal; exceeding that fraction
  is a finding even if the gross tolerance is met;
  (b) **functional degradation** — the component must still satisfy its
  functional specification at the required (margin-multiplied) dose.
- A component is dose-effects compliant only when all three checks pass:
  the tolerance check, every parametric limit, and the functional test.
  A marginal pass on one check does not compensate a failure on another.
- Radiation-hardness-assurance (RHA) grades and lot acceptance test
  results are the primary evidence for component tolerance values; generic
  data-sheet minimums without RHA evidence are flagged as insufficient.

## Workflow

1. Obtain the predicted dose for every component location from the
   environment analysis. Reject any component with no dose record before
   proceeding — an absent predicted dose is itself a finding.
2. Multiply each predicted dose by the RDM (default 2.0) to get the
   required tolerance. Flag any component whose documented tolerance is
   below that required value; do not waive without a formal deviation.
3. For each component, retrieve the parametric degradation specification:
   the allowable change fraction for each tracked parameter. For each
   parameter compute the fractional change between the pre-irradiation
   nominal and the post-irradiation degraded value. Flag any parameter
   whose change fraction exceeds its allowable limit.
4. Confirm that the component passes its functional test at the required
   (margin-multiplied) dose. A component that nominally meets the gross
   tolerance but fails a functional test at that dose is non-compliant.
5. Aggregate findings per component: a component with any dose, parametric,
   or functional finding is non-compliant. Record which check failed and by
   how much (the margin shortfall or the exceeded change fraction).
6. Produce a component disposition table: compliant / non-compliant, with
   the specific finding for each flagged component. This table feeds the
   radiation-effects section of the design review package.

## Pitfalls

- Comparing predicted dose directly to component tolerance without
  applying the RDM — the factor of two (or project value) is mandatory;
  skipping it understates the design requirement.
- Treating a gross tolerance pass as sufficient when parametric limits
  have not been individually verified — a component that survives the
  total dose but degrades a critical parameter beyond its allowed fraction
  is non-compliant regardless of the tolerance margin.
- Using minimum data-sheet values instead of RHA-graded or lot-verified
  tolerance data — data-sheet minimums are often not characterised for
  the relevant radiation type or dose rate, and must not substitute for
  RHA evidence without formal justification.
- Applying the same RDM to every location without considering shielding
  heterogeneity — components behind thick shielding accumulate less dose;
  each location needs its own predicted-dose input before the RDM is applied.
- Conflating total ionizing dose (TID) effects with displacement damage
  (NIEL) effects — §5.5.2 addresses TID parametric and functional
  degradation; displacement damage is a separate mechanism requiring its
  own limit check and is not covered by this leaf.

## Behavior contract (gate 3)

The dose-margin, parametric-degradation, and functional-degradation logic
is exercised by the gate-3 contract test:
scripts/test_e1012_dose_effects.py against
scripts/e1012_dose_effects_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_e1012_dose_effects.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
