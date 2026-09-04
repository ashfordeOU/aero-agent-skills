---
name: descriptive-statistics
description: "Use when you must summarize a sample of engineering measurements with descriptive statistics: compute the arithmetic mean, median, data range, sample and population variance and standard deviation, the quartiles and interquartile range by linear interpolation, the five-number summary, the coefficient of variation, and flag outliers with the 1.5-IQR rule. Produces the location, spread, and outlier report that gates a first look at any measured data set; pure Python stdlib, deterministic, no distribution fitting or hypothesis testing. Trigger: descriptive-statistics, summary-statistics, five-number-summary, interquartile-range, coefficient-of-variation, sample-variance, quartiles, outlier flagging."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [descriptive-statistics, summary-statistics, five-number-summary, interquartile-range, coefficient-of-variation]
  version: 0.1.0
  author: Aero Agent Skills
---

# Descriptive Statistics (cross-cutting/numerics/descriptive-statistics)

Use when the task is a first numerical look at a measured data set:
the arithmetic mean and median for location, the range, sample and
population variance and standard deviation for spread, the quartiles
and interquartile range by linear interpolation between ranks, the
five-number summary for the boxplot skeleton, the coefficient of
variation for relative spread, and 1.5-IQR outlier flagging. This leaf
is the pure sample-summary utility of the numerics pack: it takes a
full sample and returns deterministic summary values, stdlib only, no
RNG. It pairs with cross-cutting/numerics/probability-distributions
(parameter estimation and fitting of the same data) and with
cross-cutting/numerics/hypothesis-testing (significance tests between
samples after they are summarized). It does NOT fit probability
models, run significance tests, fit lines or curves, or compute
production-monitoring statistics: manufacturing-quality/as9100/
statistical-process-control owns the X-bar/R and capability-index
methods for production process monitoring.

## Domain quick reference

- Mean: m = sum(x_i) / n. Median: the middle value of the sorted
  sample; an even count averages the two middle values. Range: max -
  min.
- Variance at degrees-of-freedom correction ddof: s^2 = sum((x_i -
  m)^2) / (n - ddof). ddof = 1 gives the sample variance (n - 1 in the
  denominator), ddof = 0 the population variance (divide by n).
- Standard deviation: s = sqrt(s^2). Sample std at ddof = 1 by
  default.
- Linear-interpolation percentile: rank r = p * (n - 1); the lower
  index is floor(r), the upper index ceil(r), and the value blends the
  two ranked entries by the fraction r - floor(r). This is the
  percentile convention used throughout the leaf.
- Quartiles: q1, q2 and q3 are percentiles of the sample at p = 0.25,
  0.5 and 0.75; q2 equals the median. Interquartile range: iqr = q3 -
  q1.
- Five-number summary: {min, q1, median, q3, max}, the boxplot
  skeleton.
- Coefficient of variation: cv = s / m as a fraction (not percent);
  undefined when the mean is zero.
- 1.5-IQR outlier rule: fences at q1 - IQR_FACTOR * iqr and q3 +
  IQR_FACTOR * iqr with IQR_FACTOR = 1.5; a value is flagged only when
  it is strictly below the lower fence or strictly above the upper
  fence, so a value exactly on a fence is not an outlier.
- NACA TR-824 frames the numerics-pack public-domain reference set;
  the relations above are standard engineering methodology,
  summary-only.

## Workflow

1. Collect the sample as a list of floats; location measures need at
   least 1 element, variance measures at least 2 for ddof = 1.
2. Get the location: mean(sample), median(sample), and the spread
   extent with data_range(sample).
3. Choose the spread convention: variance(sample) and std_dev(sample)
   are sample measures (ddof = 1); pass ddof=0 for the population
   measures of the same sample.
4. Locate the distribution: quartiles(sample) for q1, q2, q3 and
   interquartile_range(sample) for iqr, or percentile(sample, p) for
   any other quantile p in [0, 1].
5. Build the boxplot skeleton with five_number_summary(sample).
6. Scale the spread: coefficient_of_variation(sample) gives the
   relative spread as a fraction of the mean.
7. Screen for suspects: outlier_indices_iqr(sample) returns the
   original-order indices outside the 1.5-IQR fences; pull the values
   with sample[i].
8. For one report of everything, call summary(sample) and read the n,
   mean, median, min, max, range, sample_variance, sample_std, q1, q3,
   iqr, five_number_summary, coefficient_of_variation, outlier_indices
   and outlier_values keys.
9. Confirm the deterministic checks with the contract test
   scripts/test_descriptive_statistics.py.

## Worked example

Sample [2, 4, 4, 4, 5, 5, 7, 9], the spec anchor data set (n = 8).
Real module outputs:

- mean = 5.0 exactly (40 / 8); median = 4.5 exactly (average of the
  two middle values 4 and 5); data range = 9 - 2 = 7.0.
- Sample variance (ddof = 1) = 32/7 = 4.5714285714; sample std =
  2.1380899353. Population variance (ddof = 0) = 32/8 = 4.0 exactly;
  population std = 2.0 exactly.
- Quartiles by linear interpolation: q1 = 4.0 (rank 1.75 blends the
  two 4s), q2 = 4.5, q3 = 5.5 (rank 5.25 blends 5 and 7); iqr = 1.5.
- Five-number summary {2, 4, 4.5, 5.5, 9}.
- Coefficient of variation = 2.1380899353 / 5 = 0.4276179871.
- Outlier fences: lower = 4.0 - 1.5 * 1.5 = 1.75, upper = 5.5 + 2.25 =
  7.75. Only the 9 at index 7 is flagged (9 > 7.75); the 2 is not an
  outlier (2 > 1.75). outlier_indices = [7], outlier_values = [9].
- summary(sample) returns n 8, mean 5.0, median 4.5, min 2, max 9,
  range 7, sample_variance 4.5714285714, sample_std 2.1380899353,
  q1 4.0, q3 5.5, iqr 1.5, five_number_summary {2, 4, 4.5, 5.5, 9},
  coefficient_of_variation 0.4276179871, outlier_indices [7],
  outlier_values [9].

## Pitfalls

- Mixing the ddof conventions: the sample variance uses ddof 1 (32/7 =
  4.5714) and the population variance ddof 0 (32/8 = 4.0); quoting one
  as the other shifts the standard deviation by sqrt(8/7).
- Reading quartiles as values that must appear in the sample: the
  quartiles use linear interpolation over ranks (q1 = 4.0 blends rank
  1.75 across the two 4s, q3 = 5.5 blends 5 and 7), which is why the
  five-number summary reads {2, 4, 4.5, 5.5, 9}.
- Forgetting the fence rule is strict: a value exactly at the upper
  fence (7.75 in a crafted sample) is NOT flagged as an outlier, while
  a value just past it (7.76) is.
- Computing the coefficient of variation on a zero mean: it raises
  ValueError, as do empty samples for every measure, variance and std
  at n = 1 with ddof = 1 (n - ddof <= 0), and percentile p outside
  [0, 1].
- Calling percentile with p outside [0, 1]: it raises ValueError, and
  the p = 0 and p = 1 endpoints return min and max by design.
- Trusting the mean alone on skewed data: the median (4.5) and the
  outlier flags (only the 9, above the 7.75 fence) carry the shape
  information that the mean of 5.0 hides.

## Verification

- Confirm mean, median and data_range of [2, 4, 4, 4, 5, 5, 7, 9]
  return 5.0, 4.5 and 7.0, and that variance(sample) returns 32/7
  within 1e-9 relative.
- Confirm quartiles return q1 4.0, q2 4.5, q3 5.5 and that the
  five-number summary equals {2, 4, 4.5, 5.5, 9}.
- Confirm percentile([0, 10, 20, 30], 0.5) returns 15.0 by the
  rank-blend rule and that p = 0 and p = 1 return min and max.
- Confirm the 1.5-IQR rule flags only index 7 of the worked sample,
  that a value exactly at the upper fence (7.75 in a crafted sample)
  is NOT flagged, and that a value just past it (7.76) is.
- Confirm the sample std squared equals the sample variance, and the
  coefficient of variation equals std / mean.
- Confirm ValueError rejection: empty samples for every measure,
  variance and std at n = 1 with ddof = 1, n - ddof <= 0, percentile
  with p outside [0, 1], and coefficient of variation on a zero mean.
- Confirm determinism: repeated summary calls return identical dicts;
  the module never uses random numbers.
- Run the contract test offline: python3
  scripts/test_descriptive_statistics.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/probability-distributions: distribution
  parameter fitting and estimation, the model step after a summary.
- cross-cutting/numerics/hypothesis-testing: significance tests on
  samples that this leaf only summarizes.
- cross-cutting/numerics/least-squares-regression: straight-line fits
  of the relationships behind the samples.
- cross-cutting/numerics/interpolation: table interpolation, a
  different operation from the rank interpolation used for quartiles.
- cross-cutting/numerics/monte-carlo-sampling: seeded sampling to
  estimate output distributions; this leaf consumes full samples only.
- manufacturing-quality/as9100/statistical-process-control: X-bar/R
  and capability-index methods for production process monitoring, not
  one-off sample summaries.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_descriptive_statistics.py

The test covers the spec worked-example anchors (mean 5.0, median 4.5,
range 7.0, sample variance 32/7, sample std 2.1380899353, population
variance 4.0 and std 2.0, q1 4.0, q3 5.5, iqr 1.5, five-number summary
{2, 4, 4.5, 5.5, 9}, coefficient of variation 0.4276179871, only index
7 flagged), median behavior for odd and even counts, single-element
samples, percentile endpoints and the linear-interpolation midpoint,
outlier fences including the exact-fence boundary case, the full
summary dict, ValueError rejection of empty samples, ddof violations,
out-of-range p and zero-mean CV, and determinism. Runs in well under a
second.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  numerics-pack public-domain reference set; descriptive statistics is
  standard engineering methodology (paraphrase-only) per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
