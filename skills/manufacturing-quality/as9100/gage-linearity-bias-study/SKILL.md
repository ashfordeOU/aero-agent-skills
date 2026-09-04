---
name: gage-linearity-bias-study
description: "Use when you must run the gage bias and linearity study: compute the per-level bias and the overall mean bias from reference masters and measured biases, fit the least-squares regression of bias on the reference value returning the slope, intercept, residual sum of squares and R-squared as the linearity evidence, test the mean bias for significance against the two-sided 95 percent t critical at the study degrees of freedom, and apply the percent-of-reference acceptability band per level. Produces per-level bias, mean bias, the regression linearity statistics, the bias significance verdict, the worst percent bias and an overall study verdict. Trigger: gage linearity and bias, measurement bias study, bias significance test, gage linearity regression, percent of reference band, linearity percent band, msa bias analysis."
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
  tags: [gage-linearity-bias-study, measurement-bias-study, gage-linearity-regression, bias-significance-test, linearity-percent-band, msa-bias-analysis]
  version: 0.1.0
  author: AeroSkills
---

# Gage Linearity and Bias Study (manufacturing-quality/as9100/gage-linearity-bias-study)

Use when the task is judging a gage's bias and linearity at the
conceptual level: reference-level masters are measured repeatedly, the
bias (observed minus reference) is recorded at each level, and the study
asks whether the gage reads true on average (bias significance test) and
whether the bias grows across the measurement range (linearity
regression of bias on the reference value). This leaf implements the
per-level bias, the mean bias, the least-squares linearity statistics,
the t test against the two-sided 95 percent critical at the study
degrees of freedom, and the percent-of-reference acceptability band, in
pure Python, stdlib only. It pairs with
manufacturing-quality/as9100/measurement-systems-analysis for the
repeatability and reproducibility variance decomposition (which does not
compute bias or linearity studies), and with
manufacturing-quality/as9100/calibration-control for instrument
calibration state and traceability.

## Domain quick reference

- Conventions: references are the certified master values in mm, one
  strictly increasing unique value per level; one bias per level with
  bias = observed - reference (signed mm, positive means the gage reads
  high); n = number of reference levels (3 or more).
- Per-level bias and percent of reference:
  bias_pct_i = 100 * bias_i / reference_i. A level is acceptable when
  |bias_pct| <= 10 percent of reference (ACCEPTANCE_PCT_BAND).
- Mean bias: bias_bar = sum(bias_i) / n. The spread terms:
  sst = sum (bias_i - bias_bar)^2 and s = sqrt(sst / (n - 1)).
- Bias significance: t = bias_bar / (s / sqrt(n)) against the two-sided
  95 percent t critical at df = n - 1 (12.706 at 1 df down to 2.086 at
  20 df, 1.96 above 20 df); significant when |t| >= t_crit.
- Linearity regression: least squares fit bias = intercept + slope *
  reference, with slope = Sxy / Sxx and intercept = bias_bar - slope *
  xbar over the level values; sse = sum (bias_i - predicted_i)^2 and
  r2 = 1 - sse / sst measure how well a straight line carries the bias
  trend across the range.
- Overall verdict: ACCEPT when the mean bias is not statistically
  significant AND every level is inside the percent band, else REVIEW.
  A significant mean bias alone forces REVIEW even when all levels are
  inside the band.
- AS9100 frames monitoring and measuring resources as controlled and
  fit for purpose; the bias and linearity study is one common
  measurement-system evidence practice in that context, summarized here
  without clause text.

## Workflow

1. Collect the study inputs: reference masters (mm) and the measured
   bias at each level (mm), as equal-length lists with 3 or more
   strictly increasing positive references.
2. Get the per-level table with per_level_bias(references, biases):
   reference, bias and bias_pct_of_reference per level.
3. Read the overall mean bias with mean_bias(biases).
4. Fit the linearity evidence with linearity_regression(references,
   biases): slope, intercept, sse, r_squared, n, xbar, bias_bar.
5. Test the mean bias with bias_significance(biases): t_stat, t_crit,
   df and the significant flag.
6. Run the whole study with gage_bias_linearity_study(references,
   biases) for the combined verdict: worst_bias_pct, worst_reference,
   per_level_acceptable and overall ACCEPT or REVIEW.
7. Confirm the deterministic checks with the contract test
   scripts/test_gage_linearity_bias_study.py.

## Worked example

Reference study: masters [2, 4, 6, 8, 10] mm with measured biases
[0.07, 0.10, 0.16, 0.18, 0.24] mm. Module outputs:

- Per-level bias percent of reference: 3.50, 2.50, 2.67, 2.25, 2.40
  percent (real module values 3.5, 2.5, 2.6667, 2.25, 2.4), all inside
  the 10 percent band.
- Mean bias = 0.150 mm; sst = 0.0180; s = 0.06708 mm.
- Linearity regression: slope = 0.0210 mm/mm, intercept = 0.0240 mm,
  sse = 0.00036, r2 = 0.980 (bias grows about 0.021 mm per mm of
  reference).
- Bias significance: t = 0.150 / (0.06708 / sqrt(5)) = 5.000; df = 4;
  t_crit = 2.776; |5.000| >= 2.776, so significant = True.
- Worst percent bias = 3.50 percent at the 2 mm level; all levels are
  inside the 10 percent band, yet the study verdict is REVIEW because
  the mean bias is statistically significant.

## Verification

- Confirm per_level_bias on the anchor returns the five rows with
  bias_pct_of_reference 3.50, 2.50, 2.67, 2.25, 2.40 within 1e-2, and
  that mean_bias returns 0.150.
- Confirm linearity_regression returns slope 0.0210 within 1e-4,
  intercept 0.0240 within 1e-3, sse 0.00036 within 1e-5 and r2 0.980
  within 1e-3, that the regression residuals sum to zero within 1e-9,
  and that r2 equals 1 - sse/sst exactly.
- Confirm bias_significance returns t = bias_bar / (s / sqrt(n)) exactly
  per the formula (5.000 on the anchor), t_crit 2.776 at 4 df, and
  significant True; a small-bias fixture with all biases 0.01 returns
  significant False.
- Confirm gage_bias_linearity_study returns REVIEW on the anchor
  (significant bias despite the band) and ACCEPT on the all-biases-0.01
  fixture.
- Confirm ValueError rejection of mismatched arrays, fewer than 3
  levels, references that are not strictly increasing, any reference
  at or below zero, and empty bias lists.
- Deterministic, offline: run python3
  scripts/test_gage_linearity_bias_study.py (29 tests, exit 0).

## Related leaves

- manufacturing-quality/as9100/measurement-systems-analysis: the
  repeatability and reproducibility variance decomposition with percent
  contributions and distinct categories; it does not compute bias or
  linearity studies.
- manufacturing-quality/as9100/attribute-agreement-analysis: agreement
  analysis for attribute go/no-go judgments instead of variable-data
  bias studies.
- manufacturing-quality/as9100/calibration-control: calibration state,
  recall and traceability of the instrument behind the study.
- cross-cutting/numerics/least-squares-regression: the generic fitting
  machinery without the gage verdict framing.

## Pitfalls

- Reading a significant mean bias as an automatic failure: the t test
  compares the mean bias against the spread of the level biases, so the
  anchor's 0.150 mm mean bias is significant (t = 5.000 against 2.776)
  even though every level sits inside the 10 percent band; the verdict
  REVIEW, not ACCEPT, is the correct joint reading of both gates.
- Reading the percent band as the only gate: a mean bias can be tiny
  but statistically significant when the level biases are tightly
  grouped, so the significance test and the band must both pass before
  ACCEPT.
- Dividing by zero on uniform bias: identical biases across levels give
  s = 0 and an undefined t; the study reports t_stat 0.0 and
  significant False (zero-dispersion convention) and lets the percent
  band decide.
- Forgetting the bias sign: bias is observed minus reference, so a
  positive bias means the gage reads high and the regression slope
  carries the sign of the linearity drift.
- Using the wrong degrees of freedom: df = n - 1 with n the number of
  reference levels, not the number of readings per level; above 20 df
  the t critical is 1.96, not an extrapolated table value.
- Feeding non-positive or unordered masters: the percent of reference
  blows up near zero and an unordered level list breaks the fit;
  references must be strictly increasing positive values (ValueError).
- Routing variance-decomposition questions here: the repeatability and
  reproducibility study with its percent-of-total verdicts belongs to
  measurement-systems-analysis; this leaf owns only the reference-level
  bias and linearity study.
- Routing generic fit questions here: a bare least-squares regression
  without gage verdict framing belongs to
  cross-cutting/numerics/least-squares-regression.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_gage_linearity_bias_study.py

The test covers the anchor worked example (masters [2, 4, 6, 8, 10] mm,
biases [0.07, 0.10, 0.16, 0.18, 0.24] mm: per-level percents within
1e-2, slope 0.0210, intercept 0.0240, sse 0.00036, r2 0.980, t 5.000
with t_crit 2.776 at 4 df, verdict REVIEW), the residual-sum-zero and
r2 = 1 - sse/sst and t-formula identities, the small-bias fixture
(all biases 0.01: not significant, ACCEPT), the zero-dispersion
convention, the large-df normal critical 1.96, the t critical table
spot checks, the ACCEPT/REVIEW verdict logic including the band-breach
case, and ValueError rejection of mismatched arrays, fewer than 3
levels, non-increasing or non-positive references and empty biases.

## Compliance

- Standards referenced, not reproduced: AS9100 is cited as reference
  context only (measurement system analysis in the AS9100/AS9102
  environment); no standard text is reproduced and the study equations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
