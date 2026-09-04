# Wave-36 leaf spec: gage-linearity-bias-study (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/gage-linearity-bias-study/
- Pack: as9100. Closest siblings: measurement-systems-analysis (range-
  method GRR: EV/AV/GRR/PV/TV/%GRR/ndc; its pitfalls text says attribute
  work goes to attribute-agreement-analysis; it does NOT compute bias or
  linearity studies), attribute-agreement-analysis (attribute kappa),
  calibration-control (traceability/TAR/recall; MSA separate per the MSA
  leaf's own pitfall), cross-cutting/numerics regression leaves (generic
  OLS method; no gage verdict framing). Whole-tree grep: "gage
  linearity|linearity and bias|bias study" = 0 hits. ZERO owners for
  the bias and linearity study.
- Standards id: as9100 (reference-only; measurement system analysis in
  the AS9100/AS9102 context). Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Run the gage bias and linearity study at the conceptual level: from
reference-level masters and the measured biases at each level, compute
the per-level bias and the overall mean bias, fit the least-squares
regression of bias on the reference value, and return the slope,
intercept, residual sum of squares and R-squared as the linearity
evidence; test the mean bias for significance against the two-sided
95 percent t critical at the study degrees of freedom; and apply the
percent-of-reference acceptability band per level. Produces per-level
bias, mean bias, the regression linearity statistics, the bias
significance verdict, the worst percent bias and an overall study
verdict.

Does NOT do: GRR range-method variance decomposition and %GRR/ndc
(measurement-systems-analysis); attribute agreement kappa
(attribute-agreement-analysis); calibration recall intervals and TAR
(calibration-control); generic regression for other purposes
(cross-cutting numerics).

## Model (implement exactly)

Module constants:
- T_CRIT_95_TWOTAIL = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776,
  5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
  11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120,
  17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086} (two-sided 95 percent t
  critical values, df = n-1).
- T_CRIT_LARGE_DF = 1.96 (normal approximation for df > 20).
- ACCEPTANCE_PCT_BAND = 10.0 (percent of reference; per-level
  |bias|/reference <= 10 percent is acceptable).

Conventions: references in mm (ascending unique values); one bias value
per reference level (bias = observed - reference, signed mm). n = number
of reference levels.

Functions (pure stdlib):
- per_level_bias(references, biases) -> list of dict {reference,
  bias, bias_pct_of_reference}. ValueErrors: length mismatch; fewer than
  3 levels; reference not strictly increasing; any reference <= 0.
- mean_bias(biases) -> float. ValueError: empty.
- linearity_regression(references, biases) -> dict {slope, intercept,
  sse, r_squared, n, xbar, bias_bar} via least squares on
  bias = intercept + slope*reference; sse = sum (bias - pred)^2;
  r2 = 1 - sse/sst. ValueErrors as per_level_bias.
- bias_significance(biases) -> dict {t_stat, t_crit, df, significant}
  with t = bias_bar/(s/sqrt(n)), s = sample sd of biases (s = sqrt(sst/
  (n-1))), df = n-1, t_crit from the table (1.96 for df > 20),
  significant = |t| >= t_crit. ValueErrors: n < 3.
- gage_bias_linearity_study(references, biases) -> dict with per_level,
  mean_bias, regression stats, significance verdict, worst_bias_pct,
  worst_reference, per_level_acceptable (all |bias_pct| <= band), and
  overall verdict ACCEPT when significance is False and all levels
  acceptable, else REVIEW.

Identity to test: regression residuals sum to zero within 1e-9; r2 ==
1 - sse/sst; t = bias_bar/(s/sqrt(n)) exactly per the formula.

## Worked example

Reference study: masters [2, 4, 6, 8, 10] mm with measured biases
[0.07, 0.10, 0.16, 0.18, 0.24] mm.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- per-level bias pct of reference: 3.50%, 2.50%, 2.67%, 2.25%, 2.40%.
- mean bias = 0.150 mm; sst = 0.0180; s = 0.06708 mm.
- regression: slope = 0.0210 mm/mm, intercept = 0.0240 mm, sse =
  0.00036, r2 = 0.980.
- bias significance: t = 0.150/(0.06708/sqrt(5)) = 5.000; df = 4;
  t_crit = 2.776; significant = True (5.000 >= 2.776) -> mean bias is
  statistically significant.
- worst bias pct = 3.50% at 2 mm (within the 10 percent band);
  overall verdict REVIEW (bias significant even though all levels are
  inside the band).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: mismatched arrays; n < 3; non-increasing references;
  reference <= 0; empty biases.
- Per-level pct: 3.50/2.50/2.67/2.25/2.40 within 1e-2.
- Regression: slope 0.0210 within 1e-4; intercept 0.0240 within 1e-3;
  sse 0.00036 within 1e-5; r2 0.980 within 1e-3; residual sum ~ 0.
- Significance: t 5.000 within 1e-3; t_crit 2.776; significant True.
- A small-bias fixture (all biases 0.01) -> significant False.
- Overall verdict REVIEW on the anchor; ACCEPT on the small-bias
  fixture.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-gage-linearity-bias-study.yaml)

Query 1 (copy verbatim):
  "run the gage linearity and bias study from reference masters and measured biases across five levels"
  intent: "manufacturing-quality; gage bias linearity regression and significance"
  expected_skill: "manufacturing-quality/as9100/gage-linearity-bias-study"
Query 2 (copy verbatim):
  "assess measurement bias significance against the t critical and the percent of reference band for a gage study"
  intent: "manufacturing-quality; bias significance t test and acceptability band"
  expected_skill: "manufacturing-quality/as9100/gage-linearity-bias-study"
Task ids: w36-gage-linearity-bias-study-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run the gage bias and
linearity study:" and include the outputs in the Claim. First tag:
gage-linearity-bias-study. Additional tags ONLY: measurement-bias-
study, gage-linearity-regression, bias-significance-test,
linearity-percent-band, msa-bias-analysis. NEVER single generic words
(gage, bias, linearity, study, regression, measurement, reference,
level). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): grr, ev, av, ndc, %grr, range
method (measurement-systems-analysis); kappa, attribute agreement
(attribute-agreement-analysis); recall interval, tar, traceability
(calibration-control).
