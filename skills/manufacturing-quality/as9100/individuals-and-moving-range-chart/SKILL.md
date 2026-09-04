---
name: individuals-and-moving-range-chart
description: "Use when you must run an individuals and moving range control chart: compute the moving ranges between successive measurements and the average moving range, build the individuals chart limits from the mean plus and minus E2 times the average moving range (E2 = 2.66), estimate the process standard deviation from the average moving range over the d2 constant (d2 = 1.128), set the moving range chart upper limit at 3.267 times the average moving range, flag the individual values and moving ranges outside their limits, and return the in-control or out-of-control verdict for one-measurement-per-lot processes (destructive testing, single unit per batch, bond or coating lots). Produces the central lines, limits, flagged points, and the stability verdict that gate lot-to-lot process control without subgroups. Trigger: moving range chart, individuals chart, I-MR chart, single measurement per lot, destructive testing, lot monitoring."
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
  tags: [individuals-and-moving-range-chart, moving-range-chart, individuals-chart, single-measurement-control, lot-monitoring-chart]
  version: 0.1.0
  author: AeroSkills
---

# Individuals and Moving Range Chart (manufacturing-quality/as9100/individuals-and-moving-range-chart)

Use when the process yields one measurement per lot or subgroup, so
subgroup charts cannot be built: destructive testing consumes the sample,
a single unit ships per batch, or one bond or coating coupon is pulled
per lot. The I-MR chart turns the time-ordered individual measurements
into moving ranges between successive values, draws both charts from the
average moving range with the E2 and 3.267 factors, and returns the
lot-to-lot stability verdict. It pairs with
manufacturing-quality/as9100/statistical-process-control, which owns the
subgroup charts (X-bar and R with the A2/D3/D4 constants, Cp/Cpk) that
apply when subgroup data exist.

## Domain quick reference

- Moving range at position i: MR_i = |x_i - x_{i-1}| for i >= 1; N
  individuals give N-1 moving ranges.
- Average moving range: mr_bar = mean(MR_i).
- Individuals (X) chart central line and limits: centerline = mean of the
  individuals; UCL = mean + E2 * mr_bar; LCL = mean - E2 * mr_bar, with
  the n = 1 constant E2 = 2.66.
- Process sigma estimate from the moving ranges: sigma_hat = mr_bar / d2,
  with d2 = 1.128 (the n = 2 constant for two-point moving ranges).
- Moving range chart limit: UCL = 3.267 * mr_bar; the MR lower limit is 0
  because moving ranges cannot be negative.
- Verdict: in-control when no individual and no moving range falls
  outside its limits, else out-of-control.
- A point exactly on a limit is inside (inclusive interval).
- AS9100 clause 8.5.1 frames production process control; the I-MR chart
  is the common evidence of stability for a single-measurement special
  process, summarized here without clause text.

## Workflow

1. Collect the time-ordered individual measurements, one per lot, in
   production sequence (moving_ranges and the limits all assume order).
2. Compute the moving ranges between successive values with
   moving_ranges(values).
3. Get the central line and X chart limits with individuals_limits(values);
   read mean, mr_bar, sigma_hat, UCL, LCL from the returned dict.
4. Get the MR chart limit with moving_range_limits(values); read mr_bar and
   UCL (LCL is 0).
5. Flag the out-of-limit points with flag_points(values, ucl, lcl); the
   returned indices point into the values list. Flag the moving ranges
   with flag_points(mr_values, mr_ucl, 0.0), where MR index i spans
   original measurements i and i + 1.
6. Combine both flag lists with stability_verdict(individual_flags,
   mr_flags) for the lot-to-lot verdict, or run imr_summary(values) once to
   get mean, mr_bar, sigma_hat, x_ucl, x_lcl, mr_ucl,
   flagged_individuals, flagged_moving_ranges and verdict in one dict.
7. Reject inputs first: fewer than 2 values raise ValueError (a chart
   needs at least one moving range); flag_points rejects an empty list.

## Worked example

Twelve bond-lot pull-off force measurements, one destructive coupon per
lot: values [42.1, 41.6, 43.0, 42.4, 41.2, 44.1, 43.5, 42.8, 41.9, 43.2,
44.0, 42.6]. Real module outputs:

- mean = 42.700; mr_bar = 1.118; sigma_hat = 0.991.
- X chart: UCL = 45.674; LCL = 39.726 (mean plus and minus 2.66 * 1.118).
- MR chart: UCL = 3.653 (3.267 * 1.118); LCL = 0.
- Flagging: no individual outside [39.726, 45.674] and no moving range
  above 3.653 (the largest, 2.90, stays inside), so the verdict is
  in-control: lot-to-lot stability is demonstrated with no subgroup data.
- Appending a 50.0 coupon flags individual index 12 and moving range
  index 11, and the verdict flips to out-of-control.

## Verification

- Confirm the worked series returns mean 42.700, mr_bar 1.118,
  sigma_hat 0.991, UCL 45.674, LCL 39.726, MR UCL 3.653 (each within
  1e-3) and verdict in-control.
- Confirm [1, 5, 2] gives moving ranges [4, 3] and a constant series
  gives all-zero moving ranges, zero sigma_hat and X limits collapsed to
  the constant mean.
- Confirm a two-value series gives mr_bar equal to the absolute
  difference and UCL_X = mean + 2.66 * |difference|.
- Confirm adding a large outlier widens the X limits (the moving range
  grows) and flags that position.
- Confirm ValueError rejection: fewer than 2 values for
  moving_ranges/individuals_limits/moving_range_limits, an empty list for
  flag_points.
- Confirm determinism: identical inputs give identical dicts.
- Run the contract test offline: python3
  scripts/test_individuals_and_moving_range_chart.py (35 tests,
  deterministic).

## Related leaves

- manufacturing-quality/as9100/statistical-process-control: X-bar and R
  subgroup charts with the A2/D3/D4 constants, subgroup d2 sigma estimate
  and Cp/Cpk; use it when subgroups exist, not for n = 1.
- manufacturing-quality/as9100/cusum-ewma-monitoring: CUSUM and EWMA
  statistics for detecting small sustained mean shifts on individual
  values.
- manufacturing-quality/as9100/attribute-control-charts: p, np, c and u
  charts for defect and nonconformity rates when the response is counted,
  not measured.

## Pitfalls

- Feeding values out of production order: moving ranges pair successive
  measurements, so the limits, flags and verdict all assume
  time-ordered one-per-lot sequence - a reordered series produces a
  different chart.
- Using the I-MR chart where subgroup data exist: X-bar and R with the
  A2/D3/D4 constants belong to the statistical-process-control sibling;
  I-MR is the n = 1 fallback (destructive testing, single unit per
  batch), not a replacement for subgroup charting.
- Treating a moving-range flag as an individual flag: MR index i spans
  original measurements i and i + 1, so flagging must be read against
  the MR list, not the individuals list.
- Ignoring the outlier-limits interaction: injecting a 50.0 coupon both
  flags the point and inflates mr_bar, widening the X limits - an early
  extreme value can mask a later excursion of the same size.
- Misreading a point exactly on a limit: limits are inclusive, so a
  value equal to UCL or LCL is inside the chart, not a flag.
- Charting with fewer than two measurements: a single lot yields no
  moving range, and fewer than 2 values (or an empty flag list) raises
  ValueError rather than producing a chart.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_individuals_and_moving_range_chart.py

The test covers the worked-example limits (mean 42.700, mr_bar 1.118,
sigma_hat 0.991, X UCL 45.674 / LCL 39.726, MR UCL 3.653 within 1e-3),
moving range arithmetic and the N-1 count, the constant-series collapse
and two-value identities, boundary points on the limits, outlier flagging
at the injected index with the out-of-control verdict, the exact
convenience dict keys, determinism, and ValueError rejection of fewer
than 2 values and of empty flag input.

## Compliance

- Standards referenced, not reproduced: AS9100 (SAE) is cited as the
  production process control frame; the I-MR equations above are standard
  engineering methodology (the n = 1 control chart constants E2 = 2.66
  and MR factor 3.267), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
