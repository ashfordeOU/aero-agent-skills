---
name: gage-rr-anova
description: "Use when you must run the ANOVA estimator for a gage repeatability and reproducibility study: decompose total variation of replicated balanced readings into part, operator, part-by-operator interaction and equipment sums of squares, estimate variance components with the non-negative interaction floor, compute equipment, appraiser, interaction, combined GRR, part and total variation, the percent GRR verdict on the 10/30 acceptance bands, part and interaction F statistics, and the number of distinct categories. Produces the ANOVA table, variance components, verdict and ndc that gate measurement system approval. Trigger: gage rr anova, variance component decomposition, operator part interaction F test, distinct categories count."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [gage-rr-anova, two-way-anova-grr, variance-component-decomposition, operator-part-interaction, anova-grr-acceptance, distinct-categories-count]
  version: 0.1.0
  author: AeroSkills
---

# Two-Way ANOVA Gage R and R (manufacturing-quality/as9100/gage-rr-anova)

Use when a replicated gage repeatability and reproducibility (Gage R
and R) study must be scored with the two-way analysis of variance
estimator: balanced readings of several parts by several operators are
decomposed into part, operator, part-by-operator interaction and
equipment variance components, and the combined measurement error is
scored against the percent GRR acceptance bands. This leaf implements
the balanced two-way random-effects ANOVA in pure Python, stdlib only,
deterministic and offline. It pairs with
manufacturing-quality/as9100/measurement-systems-analysis, which runs
the range-based Gage R and R estimator for studies without replicated
operator-part interaction; the ANOVA estimator is the choice when every
operator-part cell carries two or more trials and the interaction must
be tested. The gage-linearity-bias-study, attribute-agreement-analysis
and statistical-process-control leaves cover the adjacent study types
and the process monitoring that follows gage approval.

## Domain quick reference

- Balanced layout: O operators, P parts, n trials per operator-part
  cell, with readings passed as a dict {operator: {part: [trials]}}.
  Total degrees of freedom O*P*n - 1.
- Sums of squares around the grand mean, with part_mean, op_mean and
  cell_mean the level means:
  ss_part = n*O*sum over parts (part_mean - grand_mean)^2;
  ss_operator = n*P*sum over operators (op_mean - grand_mean)^2;
  ss_interaction = n*sum over cells (cell_mean - part_mean - op_mean +
  grand_mean)^2; ss_equipment = sum over readings (reading -
  cell_mean)^2. The four effect sums add to the total sum of squares.
- Degrees of freedom: df_part = P-1, df_operator = O-1,
  df_interaction = (P-1)(O-1), df_equipment = O*P*(n-1); each mean
  square is ms = ss/df.
- Variance components by the expected-mean-square equations with the
  non-negative floor on the interaction and operator components:
  var_equipment = ms_equipment;
  var_interaction = max(0, (ms_interaction - ms_equipment)/n);
  var_operator = max(0, (ms_operator - ms_interaction)/(P*n));
  var_part = max(0, (ms_part - ms_interaction)/(O*n)).
- Variation chain: ev = sqrt(var_equipment), av = sqrt(var_operator),
  iv = sqrt(var_interaction), combined grr = sqrt(ev^2 + av^2 + iv^2),
  pv = sqrt(var_part), total tv = sqrt(grr^2 + pv^2).
- Percent GRR = 100*grr/tv with the 10/30 bands: under 10 percent is
  acceptable, 10 through 30 percent is conditional (usable only for
  specific applications), over 30 percent is unacceptable.
- Number of distinct categories: ndc = floor(1.41*pv/grr); five or
  more categories is the common adequacy threshold.
- F statistics: f_part = ms_part/ms_interaction tests the part effect
  against the interaction; f_interaction = ms_interaction/ms_equipment
  tests the interaction against repeatability. A large part F means the
  parts differ relative to the operator-part interaction; a small
  interaction F means operator offsets are additive across parts.
- Interaction-free data: when operator offsets are purely additive the
  interaction mean square falls below the equipment mean square and the
  floor clamps iv to zero, exactly the worked example below.
- AS9100 frames monitoring and measuring resources as controlled and
  fit for purpose (paraphrase of clause 7.1.5 practice); the gage study
  is the common aerospace evidence that a measurement system is fit for
  its task, summarized here without clause text.

## Workflow

1. Tabulate the study as a balanced dict {operator: {part: [trials]}}:
   every operator must measure every part with the same number of
   trials, two or more.
2. Validate the layout first with validate_study; it raises ValueError
   for fewer than 2 operators, fewer than 2 parts, fewer than 2 trials
   per cell, ragged cells and non-numeric readings.
3. Run the decomposition with anova_grr_study(data) to get the full
   result dict: sums of squares, degrees of freedom, mean squares,
   variance components, ev/av/iv/grr/pv/tv, percent_grr, ndc and the
   F statistics.
4. Read the verdict: percent_grr under 10 is acceptable, 10 through 30
   is conditional, over 30 is unacceptable. Score any percent value
   directly with verdict_for_percent_grr(pct) when you already have it.
5. Pull the five-source table (part, operator, interaction, equipment,
   total) with anova_table(data) for the report.
6. Interpret the F statistics: a large f_part confirms the parts span
   real variation, and a small f_interaction confirms the operator
   offsets are additive, so grr is driven by ev and av only.
7. Judge resolving power with ndc (five or more categories is the usual
   adequacy threshold) before approving the measurement system.
8. Confirm the deterministic checks with the contract test
   scripts/test_gage_rr_anova.py.

## Worked example

Three operators A, B, C, three parts P1..P3, two trials per cell,
operator B offset 0.01 low and operator C offset 0.04 high relative to
A:

A: P1 [0.30, 0.32], P2 [0.50, 0.52], P3 [0.70, 0.72]
B: P1 [0.29, 0.31], P2 [0.49, 0.51], P3 [0.69, 0.71]
C: P1 [0.34, 0.35], P2 [0.54, 0.55], P3 [0.74, 0.75]

Running anova_grr_study on this fixture gives the module outputs below
(deterministic, reproducible):

- Grand mean 0.5183; sums of squares ss_part 0.4800, ss_operator
  0.00670, ss_interaction about 4e-31 (the offsets are additive, so the
  interaction is numerically zero), ss_equipment 0.00135; the four sum
  to the total 0.48805.
- Degrees of freedom 2, 2, 4, 9 (total 17); mean squares ms_part 0.24,
  ms_operator 0.00335, ms_equipment 0.00015.
- Variance components: var_equipment 0.00015, var_operator 0.000558,
  var_interaction 0.0 by the floor, var_part 0.04.
- Variation chain: ev 0.01225, av 0.02363, iv 0.0, grr 0.02661, pv
  0.2000, tv 0.20176. The identity tv^2 = grr^2 + pv^2 holds.
- Percent GRR 13.19, inside the conditional band; verdict
  "conditional".
- Number of distinct categories ndc = floor(1.41*0.2/0.02661) = 10,
  above the adequacy threshold of five.
- F statistics: f_part about 2.3e30 (huge, the parts dominate) and
  f_interaction about 7.0e-28 (essentially zero, no operator-part
  interaction), so the study is driven by ev and av alone.
- ANOVA table rows: part (0.48, 2, 0.24, f_part), operator (0.0067, 2,
  0.00335, F not applicable), interaction (~4e-31, 4, ~1e-31,
  f_interaction), equipment (0.00135, 9, 0.00015, F not applicable),
  total (0.48805, 17).

## Verification

- Run the module on the worked fixture and confirm the anchors fall in
  the spec bands: percent_grr in [12.5, 14.0], ev in [0.011, 0.014],
  av in [0.021, 0.027], ndc == 10 and verdict "conditional".
- Confirm the closed-form identities: ss_part + ss_operator +
  ss_interaction + ss_equipment equals the total sum of squares around
  the grand mean, and tv^2 equals grr^2 + pv^2.
- Confirm the floor: an interaction-free fixture (additive operator
  offsets) yields var_interaction 0.0 and iv 0.0, and a second run
  returns a dict identical to the first (determinism, no RNG).
- Confirm the result dict keys match the documented set exactly
  (grand_mean, the four ss and df and ms keys, the four variance
  components, ev, av, iv, grr, pv, tv, percent_grr, ndc, f_part,
  f_interaction, verdict, distinct_categories).
- Confirm ValueError rejection: one operator, one part, one trial per
  cell, ragged cells (a missing part or unequal trial counts), and
  non-numeric or boolean readings all raise ValueError.
- Confirm verdict band edges: 9.99 acceptable, 10.0 and 30.0
  conditional, 30.01 unacceptable.
- Run the contract test offline: python3
  scripts/test_gage_rr_anova.py (34 tests, deterministic, under a
  second).

## Related leaves

- manufacturing-quality/as9100/measurement-systems-analysis: the
  range-based Gage R and R estimator (EV from the average cell range,
  AV from the appraiser-average spread); choose it when each cell has
  few trials and no interaction term is needed.
- manufacturing-quality/as9100/gage-linearity-bias-study: the operator
  offset and linearity regression study for a single gage over its
  working range.
- manufacturing-quality/as9100/attribute-agreement-analysis: agreement
  scoring for go/no-go and categorical judgments, not continuous
  readings.
- manufacturing-quality/as9100/statistical-process-control: the process
  monitoring that runs once the measurement system is approved.

## Pitfalls

- Routing a single-trial or short study here: without replicated trials
  per cell there is no within-cell error term and no interaction test,
  so the range-based estimator in measurement-systems-analysis is the
  right tool; the ANOVA path needs n >= 2 trials per cell.
- Reporting the equipment component without the interaction: the
  combined grr is sqrt(ev^2 + av^2 + iv^2), so an unmodeled interaction
  understates measurement error when operator offsets differ across
  parts.
- Forgetting the non-negative floor: a negative raw interaction
  estimate (ms_interaction below ms_equipment) means no interaction is
  detectable, and the component is clamped to zero, not reported
  negative.
- Reading ndc as zero for a perfect gage: when grr is zero the ratio
  1.41*pv/grr is undefined and the module returns None for ndc and
  distinct_categories, with percent_grr 0.0 and an acceptable verdict.
- Treating a tiny interaction F as proof the operators agree: the
  interaction test only shows the offsets are additive; operator spread
  still enters av and can push percent_grr into the conditional or
  unacceptable bands by itself.
- Interpreting F statistics on degenerate data: with no equipment or
  interaction variation the denominator mean square is zero and the F
  value is None (both terms zero) or infinite (effect present), never a
  meaningful finite number.
- Routing operator offset or linearity studies here: those belong to
  gage-linearity-bias-study, and go/no-go agreement studies belong to
  attribute-agreement-analysis; this leaf scores only the ANOVA
  variance-component decomposition of continuous replicated readings.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gage_rr_anova.py

The test covers the worked-example anchors against the spec magnitude
bands (percent_grr in [12.5, 14.0], ev in [0.011, 0.014], av in
[0.021, 0.027], ndc 10, verdict "conditional"), the balanced-design
identities (sum-of-squares decomposition, tv^2 = grr^2 + pv^2,
percent GRR ratio), the exact result-dict keys, the five-source ANOVA
table with matching F values, the 10/30 verdict band edges, the
non-negative interaction floor on a 2x2 fixture, degenerate zero
variation data, deterministic reruns, and ValueError rejection of one
operator, one part, one trial, ragged cells and non-numeric readings.

## Compliance

- Standards referenced, not reproduced: AS9100 clause 7.1.5 frames
  monitoring and measuring resources; the balanced two-way ANOVA
  expected-mean-square equations and the 10/30 percent GRR bands are
  common MSA methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
