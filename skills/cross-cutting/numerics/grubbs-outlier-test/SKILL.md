---
name: grubbs-outlier-test
description: "Use when you must test a normal sample for a single outlier: compute the sample mean and standard deviation, form the Grubbs G statistic as the largest absolute deviation from the mean divided by the sample standard deviation, compare it against the two-sided 0.05 critical value for the sample size from an embedded reference table with linear interpolation between listed sizes, and report the outlier verdict with the flagged value. Produces the G statistic, the critical value, the reject or no-outlier verdict, the rejected value and index, and the mean and standard deviation, screening a measured data set for one spurious reading before further statistical work. Sibling leaves cover screening without a probability model, parametric significance tests, rank-based procedures, and ordering-randomness tests. Trigger: grubbs-outlier-test, grubbs g statistic, single-outlier-test, grubbs critical value, outlier screening of measured data, normal sample spurious reading check."
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
  tags: [grubbs-outlier-test, grubbs-g-statistic, single-outlier-test, grubbs-critical-value, outlier-screening-test]
  version: 0.1.0
  author: AeroSkills
---

# Grubbs Outlier Test (cross-cutting/numerics/grubbs-outlier-test)

Use when the task is deciding whether the single most extreme reading
of a normally distributed sample is a spurious outlier: a telemetry
channel with one wild sample, a calibration record with one bad
measurement, or a test series that needs one suspect value screened
before further statistics. This leaf implements the Grubbs test in
pure Python, stdlib only (scripts/grubbs_outlier_test_logic.py): it
computes the sample mean and the sample standard deviation (n-1
denominator), forms the G statistic as the largest absolute deviation
from the mean divided by the standard deviation, and compares G with
the two-sided 0.05 critical value for the sample size from an embedded
reference table with linear interpolation between listed sizes. It
pairs with cross-cutting/numerics/descriptive-statistics for summary
measures and non-probabilistic screening of the same data, with
cross-cutting/numerics/hypothesis-testing for parametric significance
tests on group comparisons, and with rank-based-hypothesis-testing for
rank procedures; this leaf tests ONE normal sample for ONE outlier, it
is not a screening rule without a probability model, not a
group-comparison test, and not an ordering-randomness test of a
sequence (see runs-test for that procedure).

## Domain quick reference

- Test question: under the null the sample is a single normal draw; a
  verdict of reject says the most extreme reading is a single outlier
  at the two-sided 0.05 significance level. Either tail counts, the
  largest deviation from the mean carries the test.
- Sample statistics: mean x_bar = sum(x) / n; sample standard
  deviation s = sqrt(sum((x - x_bar)^2) / (n - 1)) with the n-1
  denominator (grubbs_statistic).
- G statistic: G = max(|x - x_bar|) / s over all readings. The flagged
  candidate is the reading achieving the maximum deviation, returned
  with its index (first occurrence on a tie).
- Embedded critical table (module constant GRUBBS_CRIT_05, two-sided
  alpha 0.05, listed sample sizes with critical G): n = 3: 1.155,
  4: 1.481, 5: 1.715, 6: 1.887, 7: 2.020, 8: 2.032, 9: 2.215,
  10: 2.290, 12: 2.412, 15: 2.549, 20: 2.709, 30: 2.908, 40: 3.036,
  50: 3.128. Critical G grows with n: larger samples give the maximum
  deviation more chances under the null.
- Interpolation: an unlisted sample size n in [3, 50] takes the linear
  interpolation between the nearest listed sizes below and above it,
  e.g. n = 11 sits halfway between n = 10 and n = 12 and returns
  2.351. Only alpha 0.05 is supported; n below 3 or above 50, a
  fractional n, and any other alpha raise ValueError.
- Verdict rule: reject when G > critical (strictly greater). The
  result dict carries g, critical, verdict ("reject" or
  "no-outlier"), rejected_value, rejected_index, mean and std; the
  rejected fields are None on a no-outlier verdict.
- Iteration: grubbs_remove_outliers removes the flagged value and
  repeats on the remainder until no outlier remains or fewer than 3
  values are left. Each pass uses the critical value for the CURRENT
  sample size. An all-identical remainder (zero standard deviation)
  cannot carry an outlier and stops the loop.
- Minimum data: at least 3 values with nonzero spread. The verdict is
  a normal-model statement; the sample should look normal apart from
  the single suspect reading.
- NACA TR-824 is named as the numerics-pack reference; the relations
  above are standard statistical methodology, summary-only.

## Workflow

1. Collect the measured sample as a list of numbers with at least 3
   values and nonzero spread; confirm the normality assumption apart
   from the suspect reading.
2. Form the statistic: grubbs_statistic(sample) returns (g, mean,
   std, candidate, candidate_idx), where candidate is the reading
   farthest from the mean.
3. Look up the decision threshold: grubbs_critical(len(sample)) from
   the embedded 0.05 table with linear interpolation.
4. Run the full test: grubbs_test(sample) returns the result dict
   {g, critical, verdict, rejected_value, rejected_index, mean, std}.
5. Read the verdict next to the critical value: on "reject" quote the
   flagged reading and index with G and the threshold; on
   "no-outlier" state that no single outlier is supported at 0.05.
6. For several suspect readings, iterate with
   grubbs_remove_outliers(sample), which returns the clean list and
   the removed values, removing one outlier per pass.
7. Confirm the deterministic checks with the contract test
   scripts/test_grubbs_outlier_test.py.

## Worked example

Eight resistance readings in ohms, one of them suspiciously high:
[10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1, 12.5], n = 8.

- Sample statistics: mean = 10.4125, sample standard deviation =
  0.8526 (spec bound 0.853). The 12.5 reading sits 2.0875 ohms from
  the mean, far beyond any other deviation (next largest 0.5125).
- G statistic: G = 2.0875 / 0.8526 = 2.4483 (module value 2.4483,
  spec anchor 2.448 within 0.01), candidate 12.5 at index 7.
- Critical value: grubbs_critical(8) = 2.032 (exact table hit).
- Verdict: 2.4483 > 2.032, so grubbs_test returns verdict "reject"
  with rejected_value 12.5 and rejected_index 7.
- Removal: grubbs_remove_outliers returns the clean list
  [10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1] with removed [12.5];
  exactly the spurious reading is taken out and the iteration stops.
- Rerun on the 7-value remainder: G = 1.5930 stays below the n = 7
  critical value 2.020, verdict "no-outlier": removing the flagged
  value and rerunning never flags it again.
- Clean control sample [10.0, 10.1, 10.2, 10.1, 10.0, 10.3, 10.2,
  10.1]: G = 1.6907 below 2.032, verdict "no-outlier".

## Verification

- Confirm grubbs_statistic on the worked sample returns mean 10.4125
  within 1e-4, std 0.853 within 1e-3, and G = 2.448 within 0.01 with
  candidate 12.5 at index 7.
- Confirm grubbs_test verdict is "reject" with rejected_value 12.5,
  and that the 7-value remainder and the clean control sample both
  return "no-outlier" with None rejected fields.
- Confirm critical table spot checks: n = 8 -> 2.032, n = 5 -> 1.715,
  n = 20 -> 2.709, all within 1e-3, plus the boundaries n = 3 ->
  1.155 and n = 50 -> 3.128.
- Confirm interpolation: grubbs_critical(11) = 2.351 (midpoint of the
  n = 10 and n = 12 entries) and grubbs_critical(16) = 2.581, with
  every interpolated value bounded by its table neighbors and the
  critical values monotone in n.
- Confirm the identity: a symmetric sample gives the same G whichever
  side is larger, e.g. [10.0, 11.0, 12.0] and [12.0, 11.0, 10.0] both
  give G = 1.0.
- Confirm iterative removal: the worked sample drops exactly the 12.5
  and stops; a two-pass case [10.0, 10.0, 10.0, 10.0, 10.0, 10.0,
  20.0, 50.0] removes 50.0 then 20.0; all-identical samples and an
  identical remainder left after a removal stop cleanly.
- Confirm ValueError rejection of fewer than 3 values, zero standard
  deviation, non-numeric values, n outside [3, 50], fractional n,
  non-integer n, and any alpha other than 0.05.
- Run the contract test offline: python3
  scripts/test_grubbs_outlier_test.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/descriptive-statistics: summary measures and
  fence-based suspect flagging without a probability model, the
  screening layer that hands a suspect reading to this test.
- cross-cutting/numerics/hypothesis-testing: the parametric
  significance-test family for group comparisons of means and
  variances, for questions beyond one sample and one outlier.
- cross-cutting/numerics/rank-based-hypothesis-testing: nonparametric
  two-sample and paired procedures built on ranks, used when the
  normal assumption does not hold.
- cross-cutting/numerics/runs-test: the ordering-randomness test for a
  two-sign sequence (wave-36 neighbor), for questions about order
  rather than extreme values.

## Pitfalls

- Quoting G without its critical value: the threshold depends on the
  sample size (2.032 at n = 8, 2.709 at n = 20), so a fixed rule of
  thumb has no meaning; always report G against grubbs_critical(n).
- Dividing by a population standard deviation: the n-1 denominator is
  part of the contract; an n-denominator std shrinks G and can flip a
  reject into a no-outlier.
- Testing several outliers in one pass: the G test flags ONE extreme
  reading per run. Removing one outlier changes both the mean and the
  standard deviation, so the iteration must re-derive the critical
  value at the current sample size on every pass.
- Extrapolating the table: n below 3 or above 50 has no embedded
  support and raises ValueError instead of inventing a threshold.
  Small samples also carry low power, a reject at n = 3 needs G above
  1.155 only.
- Forgetting the normal-model assumption: the verdict is a statement
  about a normal sample with one contaminant. Heavily skewed or
  multi-modal data should go to descriptive-statistics screening or a
  rank-based procedure instead.
- Reading the boundary as inclusive: the contract rejects strictly
  when G > critical; equality keeps the no-outlier verdict.
- Interpolating with the wrong neighbors or a non-0.05 alpha: unlisted
  sizes interpolate only between the nearest listed sizes inside
  [3, 50], and the table exists only for two-sided alpha 0.05.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_grubbs_outlier_test.py

The test covers the worked-example anchors (mean 10.4125, std 0.853,
G = 2.448 at the 12.5 reading, critical 2.032, verdict "reject"), the
clean control and the post-removal remainder giving "no-outlier" with
None rejected fields, exact critical-table hits with the n = 8, 5, 20
spot checks, midpoint and general linear interpolation with
neighbor-bounding and monotonicity, the symmetric-tie G identity, the
iterative removal contract (exactly the 12.5 removed and stopped; the
two-pass case; the all-identical guard), determinism across calls, the
exact result dict key set, and ValueError rejection of every
non-physical input (short, zero-spread, or non-numeric samples; n
outside [3, 50]; fractional and non-integer n; alpha other than 0.05).

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named as the
  numerics-pack reference; the Grubbs test relations and the embedded
  critical table (module constant GRUBBS_CRIT_05) are standard
  statistical methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
