---
name: monte-carlo-sampling
description: "Use when you must estimate the distribution of an output quantity by Monte Carlo sampling: draw seeded pseudo-random samples from a uniform input range, compute the sample mean and the sample standard deviation, extract percentile confidence intervals, and bin the draws into a histogram. Produces the sample statistics, the confidence interval, and the histogram counts that gate the sampling study. Trigger: monte carlo sampling, random seed, sample size, percentile, confidence interval, histogram, pseudo-random draws, output distribution."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [monte-carlo-sampling, random-seed, sample-size, percentile, confidence-interval, histogram, pseudo-random, uniform-distribution]
  version: 0.1.0
  author: AeroSkills
---

# Monte Carlo Sampling (cross-cutting/numerics/monte-carlo-sampling)

Use when the task is estimating the distribution of an output
quantity by Monte Carlo sampling: seeded pseudo-random draws over an
input range, sample statistics, percentile confidence intervals, and
histograms of the sampled values. The analytic GUM first order law
lives in the uncertainty-propagation leaf; this leaf is the sampling
alternative that needs no sensitivity coefficients.

## Domain quick reference

- Monte Carlo sampling draws n pseudo-random input values from a
  uniform distribution on [low, high] with a fixed seed, so the draw
  is reproducible and the study can be audited.
- The sample mean is the arithmetic mean of the draws; the sample
  standard deviation uses the n - 1 denominator.
- The p-th percentile is the value below which p percent of the
  sample lies, computed with linear interpolation between the order
  statistics (percentile 50 is the median).
- The two-tailed confidence interval at level 0.95 is the percentile
  pair (2.5, 97.5); it brackets the central 95 percent of the
  sampled distribution.
- A histogram bins the draws into k equal-width intervals over the
  sample range; the counts sum to the sample size and the last bin
  is inclusive.
- Propagation applies the model function to every draw and reports
  the mean, standard deviation, and confidence interval of the
  transformed outputs; the spread of the outputs carries the effect
  of the input spread through the model.
- Sample statistics converge with the sample size: the error of the
  mean estimate shrinks like 1 / sqrt(n).

## Workflow

1. Fix the input range [low, high] and the sample size n; a few
   thousand draws is a common starting point.
2. Draw the inputs with draw_samples(seed, n, low, high) and keep
   the seed for reproducibility.
3. Summarize the draws with sample_mean and sample_stddev.
4. Extract the spread with confidence_interval(draws, 0.95).
5. Inspect the shape with histogram(draws, bins) before gating the
   study.
6. For a model output, run propagate_samples(seed, n, low, high,
   func) and report the transformed statistics.

## Pitfalls

- Changing the seed between runs: the study is only reproducible
  when the same seed is reused; record it with the results.
- Small sample sizes: a few dozen draws give noisy percentiles; the
  tails of the distribution need thousands of draws to stabilize.
- Reading the sample standard deviation as the population value: the
  n - 1 denominator is the unbiased estimate for a sample.
- Interpolating percentiles by hand: percentile uses the linear
  interpolation method over the sorted order statistics, not a
  rounding to the nearest rank.
- Histogramming a constant sample set: a zero range cannot be binned
  and the logic raises ValueError.
- Passing a high bound at or below the low bound, a sample size
  below 1, or a percentile outside [0, 100]: all raise ValueError.
- Confusing this leaf with uncertainty-propagation: the GUM first
  order law needs sensitivity coefficients; Monte Carlo sampling
  needs only the input range and the model function.

## Behavior contract (gate 3)

The sampling, percentile, interval, and histogram logic is exercised
by the gate 3 contract test: scripts/test_monte_carlo_sampling.py
against scripts/monte_carlo_sampling_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_monte_carlo_sampling.py

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. The Monte Carlo method follows the
  JCGM 101 (GUM supplement 1) sampling procedure, which is generic
  numerical methodology, not RTCA or SAE content; summary and
  formulas only.
- compliance: STANDARDS-REF, gated: false.
