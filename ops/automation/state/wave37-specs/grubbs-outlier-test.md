# Wave-37 leaf spec: grubbs-outlier-test (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/grubbs-outlier-test/
- Pack: numerics. Closest siblings: descriptive-statistics (flags
  suspects with the 1.5-IQR fence as a SCREENING rule and explicitly
  does no hypothesis testing - whole-tree grep shows its outlier
  function is the IQR fence), hypothesis-testing (t/F/chi-square
  family), rank-based-hypothesis-testing (nonparametric tests),
  runs-test (wave-36, randomness test). Whole-tree grep: "grubbs" has
  ZERO owning hits. GENUINE gap on the deterministic bar: Grubbs is the
  standard parametric test for a single outlier in a normal sample with
  a critical-value decision. WEAKEST-ACCEPTED note (same tier as
  wave-36 runs-test): single-purpose hypothesis test in a stats-rich
  pack; accepted because it is a distinct, widely used procedure with a
  fixed critical-value table and zero owners; disclosed in the state
  note.
- Standards id: naca-tr-824 (reference-only; the numerics-pack sibling
  convention - hypothesis-testing, descriptive-statistics and rank-based-
  hypothesis-testing all carry naca-tr-824 as their map id).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Run the Grubbs test for a single outlier in a normally distributed
sample: compute the sample mean and standard deviation, form the G
statistic as the largest absolute deviation from the mean divided by
the sample standard deviation, compare it against the two-sided
critical value for the sample size and significance level from an
embedded table, and report the outlier verdict with the rejected value
and the critical value. Produces the G statistic, the critical value,
the verdict, and the flagged value that screen a measured data set for
a single spurious reading. Does NOT do: 1.5-IQR fence screening without
a probability model (descriptive-statistics); the t/F/chi-square
hypothesis-test family (hypothesis-testing); nonparametric tests
(rank-based-hypothesis-testing); the Wald-Wolfowitz randomness test
(runs-test).

## Model (implement exactly)

Module constants:
- GRUBBS_CRIT_05 = {3: 1.155, 4: 1.481, 5: 1.715, 6: 1.887, 7: 2.020,
  8: 2.032, 9: 2.215, 10: 2.290, 12: 2.412, 15: 2.549, 20: 2.709,
  30: 2.908, 40: 3.036, 50: 3.128} (two-sided alpha 0.05 critical G;
  documented reference table; interpolate linearly between listed n;
  ValueError for n below 3 or above 50)
- SIGNIFICANCE default 0.05.

Functions (pure stdlib):
- grubbs_statistic(sample) -> (g, mean, std, candidate, candidate_idx):
  g = max(|x - mean|)/std with std as the sample standard deviation
  (n-1 denominator). ValueErrors: fewer than 3 values; zero standard
  deviation (all values identical).
- grubbs_critical(n, alpha=0.05) -> float: table lookup with linear
  interpolation between the nearest listed sample sizes; alpha only
  0.05 supported (ValueError otherwise); n outside [3, 50] raises.
- grubbs_test(sample, alpha=0.05) -> dict {g, critical, verdict:
  "reject" | "no-outlier", rejected_value, rejected_index, mean, std}:
  reject when g > critical.
- grubbs_remove_outliers(sample, alpha=0.05) -> (clean_list,
  removed_list): iterate grubbs_test, remove the flagged value, and
  repeat until no outlier or fewer than 3 values remain.

Identity to test: grubbs_statistic on a symmetric two-value-around-mean
sample returns the same g whichever side is larger; removing a flagged
outlier and rerunning never flags it again; all-identical samples raise
on the zero-std check.

## Worked example

Sample [10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1, 12.5], n = 8. Run
your module and take the real outputs as assert targets; bounds
independently verified at prep: mean 10.4125, sample std 0.853, G =
2.448 (the 12.5 reading), grubbs_critical(8) = 2.032 -> verdict
"reject", rejected_value 12.5. Removing it leaves a clean list of 7
values whose rerun G stays below the n=7 critical value (no further
outlier).

## Validation list (contract test must include)

- ValueError: fewer than 3 values; zero standard deviation; n outside
  [3, 50]; unsupported alpha.
- Critical table spot checks: n=8 -> 2.032; n=5 -> 1.715; n=20 ->
  2.709 (within 1e-3).
- G statistic anchor 2.448 at the worked example within 0.01; verdict
  "reject".
- Clean-sample case: [10.0, 10.1, 10.2, 10.1, 10.0, 10.3, 10.2, 10.1]
  yields "no-outlier".
- Iteration: grubbs_remove_outliers removes exactly the 12.5 and stops.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave37-grubbs-outlier-test.yaml)

Query 1 (copy verbatim):
  "run the grubbs-outlier-test g statistic against the critical value for a single outlier in a normal sample"
  intent: "cross-cutting; Grubbs single-outlier hypothesis test"
  expected_skill: "cross-cutting/numerics/grubbs-outlier-test"
Query 2 (copy verbatim):
  "check the grubbs-outlier-test verdict and rejected value when screening measured data for one spurious reading"
  intent: "cross-cutting; Grubbs outlier screening verdict"
  expected_skill: "cross-cutting/numerics/grubbs-outlier-test"
Task ids: w37-grubbs-outlier-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must test a normal sample for a
single outlier:" and include the outputs in the Claim. First tag:
grubbs-outlier-test. Additional tags ONLY: grubbs-g-statistic,
single-outlier-test, grubbs-critical-value, outlier-screening-test.
NEVER single generic words (outlier, test, statistic, sample, mean,
standard). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): 1.5-IQR fence, five-number
summary (descriptive-statistics); t statistic, chi-square, F test
(hypothesis-testing); Mann-Whitney, Kruskal-Wallis (rank-based-
hypothesis-testing); Wald-Wolfowitz, runs (runs-test).
