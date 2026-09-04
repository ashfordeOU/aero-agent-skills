# Wave-37 leaf spec: gage-rr-anova (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/gage-rr-anova/
- Pack: as9100. Closest siblings: measurement-systems-analysis (MSA
  leaf - the RANGE-method Gage R&R: EV from average range, AV from the
  appraiser-average spread, combined GRR, PV, TV, %GRR, distinct
  categories; its body has ZERO mention of the ANOVA method or variance
  components), gage-linearity-bias-study (bias and linearity regression
  - wave-36), attribute-agreement-analysis (discrete Kappa studies),
  statistical-process-control (process monitoring). Whole-tree grep:
  "ANOVA" / "variance component" has ZERO owning hits in any leaf.
  GENUINE method gap with zero-owner evidence: the two-way ANOVA
  variance-component decomposition for replicated Gage R&R studies
  (operator by part interaction and F-test significance) is absent.
  WEAKEST-ACCEPTED candidate note (same tier as wave-36 runs-test): the
  family already hosts measurement-systems-analysis, so this leaf must
  stay strictly on the ANOVA estimator and the interaction test, with
  the range-method outputs fenced to the sibling.
- Standards id: as9100 (reference-only; measurement system context).
  Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Run the two-way analysis-of-variance estimator for a replicated gage
repeatability and reproducibility study: decompose the total variation
into part, operator, part-by-operator interaction, and equipment
(repeatability) sums of squares from balanced readings, estimate the
variance components by the expected-mean-square equations with the
non-negative floor on the interaction and operator components, compute
the equipment, appraiser, interaction, combined GRR, part and total
variation, the percent GRR verdict against the 10/30 acceptance bands,
the F statistics for the part and interaction effects, and the number
of distinct categories. Produces the ANOVA table, the variance
components, the percent GRR verdict and the distinct-category count
that gate measurement system approval when replicated readings and an
operator-by-part interaction are present. Does NOT do: the range-method
Gage R&R estimator (measurement-systems-analysis); bias and linearity
regression (gage-linearity-bias-study); attribute agreement Kappa
(attribute-agreement-analysis).

## Model (implement exactly)

Conventions: balanced study with O operators, P parts, n trials per
operator-part cell. Readings passed as a dict {operator: {part:
[trials]}}.

Functions (pure stdlib):
- anova_grr_study(data) -> dict with keys: grand_mean, ss_part,
  ss_operator, ss_interaction, ss_equipment, df_part, df_operator,
  df_interaction, df_equipment, ms_part, ms_operator, ms_interaction,
  ms_equipment, var_equipment, var_interaction, var_operator,
  var_part, ev, av, iv, grr, pv, tv, percent_grr, ndc, f_part,
  f_interaction, verdict, distinct_categories.
  Formulas (balanced two-way, random effects): ss_part = n*O*sum over
  parts (part_mean - grand_mean)^2; ss_operator = n*P*sum over
  operators (op_mean - grand_mean)^2; ss_interaction = n*sum over
  cells (cell_mean - part_mean - op_mean + grand_mean)^2;
  ss_equipment = sum over readings (reading - cell_mean)^2; dfs:
  P-1, O-1, (P-1)(O-1), O*P*(n-1). Variance components:
  var_equipment = ms_equipment; var_interaction = max(0,
  (ms_interaction - ms_equipment)/n); var_operator = max(0,
  (ms_operator - ms_interaction)/(P*n)); var_part = max(0,
  (ms_part - ms_interaction)/(O*n)). ev = sqrt(var_equipment); av =
  sqrt(var_operator); iv = sqrt(var_interaction); grr = sqrt(ev^2 +
  av^2 + iv^2); pv = sqrt(var_part); tv = sqrt(grr^2 + pv^2);
  percent_grr = 100*grr/tv; ndc = 1.41*pv/grr (round down to the
  integer); f_part = ms_part/ms_interaction;
  f_interaction = ms_interaction/ms_equipment; verdict: percent_grr <
  10 -> "acceptable"; <= 30 -> "conditional"; > 30 -> "unacceptable".
  ValueErrors: fewer than 2 operators, fewer than 2 parts, fewer than
  2 trials per cell, ragged cells, non-numeric readings.
- anova_table(data) -> list of row dicts for the five sources
  (part, operator, interaction, equipment, total) with ss, df, ms, F.

Identity to test: ss_part + ss_operator + ss_interaction + ss_equipment
== total ss; tv^2 == grr^2 + pv^2; the range-method sibling outputs are
NOT produced here (no average-range path).

## Worked example

Three operators A, B, C, three parts P1..P3, two trials per cell
(readings below; B is biased low by 0.01, C biased high by 0.04 vs A):
A: P1 [0.30, 0.32], P2 [0.50, 0.52], P3 [0.70, 0.72]
B: P1 [0.29, 0.31], P2 [0.49, 0.51], P3 [0.69, 0.71]
C: P1 [0.34, 0.35], P2 [0.54, 0.55], P3 [0.74, 0.75]
Run your module and take the real outputs as assert targets; bounds
independently verified at prep (two-way ANOVA, balanced): ev ~ 0.01225,
av ~ 0.02363, grr ~ 0.02661, pv ~ 0.2, tv ~ 0.20176, percent_grr ~
13.19, ndc = 10 (1.41*0.2/0.02661 = 10.6 -> 10), verdict
"conditional" (10 < 13.19 <= 30). Grand mean 0.5183. The F statistics
are large for the part effect and small for the interaction; assert
their signs and ordering, not exact values (they depend on your exact
df path, which is the documented balanced one).

## Validation list (contract test must include)

- ValueError: one operator, one part, one trial; ragged cells.
- Variance-component identity: ss sum; tv^2 = grr^2 + pv^2.
- Anchor magnitudes: percent_grr in [12.5, 14.0]; ev in [0.011, 0.014];
  av in [0.021, 0.027]; ndc == 10; verdict == "conditional".
- Non-negative floor: an interaction-free fixture yields iv == 0 and a
  deterministic rerun gives identical output.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave37-gage-rr-anova.yaml)

Query 1 (copy verbatim):
  "run the gage-rr-anova two way variance component decomposition for a replicated gage repeatability and reproducibility study"
  intent: "manufacturing-quality; ANOVA gage R&R variance components"
  expected_skill: "manufacturing-quality/as9100/gage-rr-anova"
Query 2 (copy verbatim):
  "check the gage-rr-anova operator part interaction F test and percent grr verdict against the acceptance bands"
  intent: "manufacturing-quality; ANOVA GRR interaction test and verdict"
  expected_skill: "manufacturing-quality/as9100/gage-rr-anova"
Task ids: w37-gage-rr-anova-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run the ANOVA estimator for a
gage repeatability and reproducibility study:" and include the outputs
in the Claim. First tag: gage-rr-anova. Additional tags ONLY:
two-way-anova-grr, variance-component-decomposition, operator-part-
interaction, anova-grr-acceptance, distinct-categories-count. NEVER
single generic words (anova, gage, grr, operator, part, repeatability).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): average range, range-method,
appraiser variation from ranges (measurement-systems-analysis); bias,
linearity regression (gage-linearity-bias-study); kappa, attribute
agreement (attribute-agreement-analysis); control chart
(statistical-process-control).
