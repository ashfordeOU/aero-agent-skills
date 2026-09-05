---
name: power-analysis
description: "Use when you must determine the sample size or the statistical power of a planned comparison: compute the minimum sample size per group for a two-sample pooled z-based comparison at a significance level, target power and effect size, with the one-sample and one-sample-proportion variants, round up to whole groups, and evaluate the achieved power at the rounded sample size. Produces the per-group sample size, the total sample size and the achieved power that gate qualification-test planning and experiment sizing. Trigger: power analysis, minimum sample size, sample size per group, statistical power, achieved power, type II error, effect size, half sigma shift, eighty percent power, two-sample comparison, qualification-test planning."
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
  tags: [power-analysis, sample-size-determination, type-ii-error, effect-size, minimum-sample-size, achieved-power]
  version: 0.1.0
  author: AeroSkills
---

# Power Analysis (cross-cutting/numerics/power-analysis)

Use when the task is sizing a planned comparison before any data exists:
the minimum sample size per group that resolves a specified effect size at
a stated significance level and target power, and the achieved power of
the rounded plan. This leaf implements the standard normal-theory sample
size formulas (two-sample pooled, one-sample mean and one-sample
proportion) with an in-leaf Acklam standard normal quantile, in pure
Python, stdlib only. It pairs with the sibling numerics leaves: the NHST
verdict after data collection belongs to cross-cutting/numerics/
hypothesis-testing, and the interval estimation of the measured effect
belongs to cross-cutting/numerics/confidence-interval-estimation.

## Domain quick reference

- Two-sample pooled comparison, n per group of two equal groups sharing a
  common standard deviation sigma: n = ceil(2 * sigma^2 * (z_(1-alpha/2) +
  z_(1-beta))^2 / delta^2), where delta is the smallest mean shift to
  resolve and beta = 1 - power is the type II error rate.
- One-sample mean comparison: n = ceil(sigma^2 * (z_(1-alpha/2) +
  z_(1-beta))^2 / delta^2), exactly half the two-sample requirement before
  the ceiling is applied.
- One-sample proportion comparison: n = ceil((z_(1-alpha/2) *
  sqrt(p0*(1-p0)) + z_(1-beta) * sqrt(p1*(1-p1)))^2 / (p1 - p0)^2), with p0
  the proportion under the null and p1 the proportion under the
  alternative.
- Critical quantiles: z_(1-alpha/2) is 1.9600 for alpha 0.05 and
  z_(1-beta) = z_power is 0.8416 at eighty percent power, both from the
  in-leaf normal_quantile (Acklam rational approximation, self-contained).
- Achieved power at the rounded n: 1 - Phi(z_(1-alpha/2) - delta *
  sqrt(n / (2 * sigma^2))), evaluated with the in-leaf normal_survival.
- Trends: the required sample size grows as the effect size shrinks with
  n ~ 1/delta^2, grows as the target power rises, and grows as the
  significance level tightens (smaller alpha), because a more stringent
  two-sided critical value sits further into the tail.
- The rounded plan is the contract: a half sigma shift at alpha 0.05 and
  eighty percent power needs 63 per group (126 total), and 63 per group
  achieves 0.8013, at or above the 0.80 target.

## Workflow

1. Fix the test plan: the effect size delta to resolve (as an absolute
   mean shift or a sigma multiple), the population standard deviation
   sigma for the mean-based comparisons, the null proportion p0 and the
   alternative proportion p1 for the proportion case, the two-sided
   significance level alpha (0.05 by default) and the target power (0.8
   by default).
2. Quantile traverse: normal_quantile(1 - alpha / 2) returns z_(1-alpha/2)
   and normal_quantile(power) returns z_(1-beta) = z_power; the
   normal_survival function supplies the 1 - Phi term that the
   achieved-power evaluation needs.
3. Two-sample sizing traverse: sample_size_two_sample_pooled(delta,
   sigma, alpha, power) returns the minimum sample size per group,
   rounded up with math.ceil.
4. One-sample sizing traverse: sample_size_one_sample(delta, sigma,
   alpha, power) returns the minimum sample size for a one-sample mean
   comparison, half the two-sample requirement before rounding.
5. Proportion sizing traverse: sample_size_one_sample_proportion(p0, p1,
   alpha, power) returns the minimum sample size for a one-sample
   proportion comparison from the null and alternative proportions.
6. Achieved-power traverse: achieved_power_two_sample_pooled(n_per_group,
   delta, sigma, alpha) evaluates the power the rounded plan actually
   delivers, at least the target power by construction.
7. Power report bookkeeping: power_report(delta, sigma, alpha, power)
   returns the dict with keys n_per_group, n_total and achieved_power.
8. Verification run: confirm the anchors and guards with the contract
   test, python3 scripts/test_power_analysis.py (38 tests, deterministic,
   offline).

## Worked example

Two-sample pooled: delta = 0.5 * sigma (effect size 0.5 with sigma 1.0),
alpha = 0.05 two-sided, power 0.8. Module outputs (contract test anchors
in parentheses):

- Quantiles: z_(1-alpha/2) = normal_quantile(0.975) = 1.959964 (within
  1e-3 of 1.9600); z_(1-beta) = normal_quantile(0.8) = 0.841621 (within
  1e-3 of 0.8416).
- Sample size per group: n = 2 * (1.959964 + 0.841621)^2 / 0.25 = 62.79,
  rounded up to 63 per group, 126 total (module returns 63 and 126).
- Achieved power at 63 per group: 1 - Phi(1.959964 - 0.5 *
  sqrt(63 / 2)) = 1 - Phi(-0.846) = 0.801301455 (within 0.002 of 0.8013,
  above the 0.80 target).
- One-sample at the same inputs: 31.40 continuous, 32 rounded; at 0.25
  sigma the one-sample 126 is exactly half of the two-sample 252.
- One-sample proportion: p0 = 0.30, p1 = 0.50, alpha 0.05, power 0.8:
  continuous 43.5, rounded to 44 (module returns 44).
- Power report dict: n_per_group 63, n_total 126, achieved_power
  0.801301455.
- Scaling checks: 0.25 sigma needs 252 per group (4 times 63, the
  inverse-square growth), ninety percent power needs 85, and alpha 0.01
  needs 94.

## Verification

- Confirm normal_quantile(0.975) returns 1.959964 and normal_quantile(0.8)
  returns 0.841621, with normal_quantile antisymmetric about the median
  and 0.5 returning exactly 0.0.
- Confirm sample_size_two_sample_pooled(0.5, 1.0) returns 63 and that
  only the delta-to-sigma ratio matters: delta 1.0 with sigma 2.0 also
  returns 63.
- Confirm the inverse-square growth: 0.25 sigma returns 252, exactly four
  times the 63 of 0.5 sigma.
- Confirm achieved_power_two_sample_pooled(63, 0.5, 1.0) returns
  0.801301455, equals normal_survival of the shifted critical value
  z_(1-alpha/2) - delta * sqrt(n / (2 * sigma^2)), and sits at or above
  the target power.
- Confirm the two-sample and one-sample relation: the one-sample 126 at
  0.25 sigma is exactly half the two-sample 252, and at 0.5 sigma the
  two-sample 63 is within one of twice the one-sample 32.
- Confirm sample_size_one_sample_proportion(0.30, 0.50) returns 44.
- Confirm every non-physical input raises ValueError: delta 0 or
  negative, sigma 0 or negative, alpha 0 or 1, power 0 or 1, power at or
  above 1 - alpha, p1 equal to p0, proportions at or outside (0, 1), and
  a per-group sample size below 2 in the achieved-power traverse.
- Run the contract test offline: python3 scripts/test_power_analysis.py
  (38 tests, deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the NHST verdict on data
  already collected; it has no beta, no power and no sample-size solver.
- cross-cutting/numerics/proportion-confidence-interval: interval
  estimation for a binomial proportion whose in-leaf normal quantile is a
  sibling technique, not a shared import.
- cross-cutting/numerics/confidence-interval-estimation: interval
  estimation of the measured effect, the counterpart of pre-study power.
- cross-cutting/numerics/rank-based-hypothesis-testing: nonparametric
  verdicts that sidestep the normal-theory sizing assumptions.
- manufacturing-quality/as9100/acceptance-sampling: lot-disposition
  plans from AQL and code letters, distinct from test power.
- cross-cutting/numerics/monte-carlo-sampling: simulation-based study of
  the generic sample-size question, distinct from the closed-form
  normal-theory planning here.

## Pitfalls

- Sizing on the continuous value: the 62.79 unrounded requirement is not
  a plan, 63 whole subjects per group is; running 62 per group achieves
  0.7950, just under the 0.80 target, while 63 delivers 0.8013.
- Quoting the target power as the achieved power: the achieved power at
  the computed n is 0.8013 for an 0.80 target, and dropping below the
  computed n erodes it fast, to about 0.71 at 50 per group and 0.52 at
  32 per group for the half sigma shift.
- Halving the plan for a one-sample study: the one-sample requirement is
  exactly half the two-sample requirement before rounding, so a 63-per-
  group two-sample plan is a 32-subject one-sample plan, not a 63-subject
  one.
- Applying the two-sample formula to a proportion comparison: the
  proportion case sizes from the binomial standard deviations
  sqrt(p*(1-p)) under each hypothesis, not from a common sigma, so the
  inputs and the rounding target differ.
- Reversing the significance trend: a stricter alpha raises the
  requirement (alpha 0.01 needs 94 per group against 63 at alpha 0.05);
  the module implements the standard z_(1-alpha/2) formulation, and the
  target power must stay below 1 - alpha for the requirement to stay
  finite.
- Treating power as a post-hoc verdict: this leaf plans and reports
  achieved power only, the running of the test and its p-value belong to
  the sibling hypothesis-testing leaf.
- Feeding non-physical inputs: the module raises ValueError for a zero
  effect, zero spread, invalid levels and a per-group sample size below
  2 instead of returning a meaningless number.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_power_analysis.py

The test covers the worked-example anchors (63 per group with 126 total
for the half sigma shift, achieved power 0.801301455 within 0.002 of
0.8013, one-sample 32, proportion 44), the quantile anchors and tail
values, the survival identities, the inverse-square effect-size growth
(252 at 0.25 sigma), the monotonicity of the required sample size in the
effect size and target power, the alpha-tightening trend (94 at alpha
0.01), the exact doubling relation between the two-sample and one-sample
requirements, the achieved-power closed form against the normal survival
of the shifted critical value, the determinism of the power report dict
with its exact keys, and every ValueError guard from the validation list.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the
  statistical methodology context; the sample size and power relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
