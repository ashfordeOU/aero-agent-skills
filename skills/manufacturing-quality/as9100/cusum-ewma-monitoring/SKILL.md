---
name: cusum-ewma-monitoring
description: "Use when you must monitor a production process for small sustained mean shifts: compute the tabular CUSUM path (upper S+ and lower S- statistics from standardized deviations with slack k and decision interval h) and the first signal sample, run the EWMA recursion with per-sample time-varying sigma limits (lambda weighting, L-sigma UCL/LCL) and its first signal sample, and combine both charts into one monitoring verdict that catches small shifts a single-point check misses. Produces the CUSUM and EWMA statistics paths, first-signal indices, per-sample EWMA control limits and the combined verdict. Trigger: cusum-ewma-monitoring, cusum-control-chart, ewma-control-chart, cumulative-sum-monitoring, small-shift-detection, sequential-process-monitoring."
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
  tags: [cusum-ewma-monitoring, cusum-control-chart, ewma-control-chart, cumulative-sum-monitoring, small-shift-detection, sequential-process-monitoring]
  version: 0.1.0
  author: Aero Agent Skills
---

# CUSUM and EWMA Monitoring (manufacturing-quality/as9100/cusum-ewma-monitoring)

Use when the task is sequential monitoring of a production process for
small sustained mean shifts that a single-point check on the raw values
would miss. This leaf implements the tabular CUSUM (accumulating
standardized deviations against a slack k and a decision interval h) and
the EWMA recursion with time-varying sigma limits in pure Python, stdlib
only. It pairs with the large-shift charting sibling
manufacturing-quality/as9100/statistical-process-control for the point
rule side of process monitoring and with
manufacturing-quality/as9100/corrective-action for the downstream
response once a signal fires. Observations are assumed independent and
normal around the in-control mean mu0 with known sigma (or sigma
estimated from an in-control study).

## Domain quick reference

- Standardized observation: z_i = (x_i - mu0) / sigma.
- Tabular CUSUM (one-sided): S+_i = max(0, z_i - k + S+_{i-1}),
  S-_i = max(0, -z_i - k + S-_{i-1}), starting S+_0 = S-_0 = 0. A
  signal fires when S+_i > h or S-_i > h. Defaults k = 0.5, h = 5.0,
  the standard choice for detecting a sustained 1-sigma shift with
  good average run length behaviour.
- EWMA recursion: e_0 = mu0, e_i = lam * x_i + (1 - lam) * e_{i-1}.
- Time-varying EWMA sigma: sigma_e_i = sigma * sqrt(lam / (2 - lam) *
  (1 - (1 - lam)^(2 i))), so the limits widen from the first sample
  toward the steady state sigma * sqrt(lam / (2 - lam)) as i grows.
- EWMA limits: UCL_i = mu0 + L * sigma_e_i, LCL_i = mu0 - L *
  sigma_e_i. Defaults lam = 0.2, L = 3.0.
- First signal index is the 1-based sample number where the statistic
  first exceeds its limit, or None for an in-control sequence.
- AS9100 frames the monitoring and data-analysis context; the chart
  methodology above is standard engineering method, summary-only.

## Workflow

1. Confirm the in-control reference: the target mean mu0 and the
   process sigma (known or from an in-control study) for the sequence
   xs.
2. Run cusum_statistics(xs, mu0, sigma) and read sp_plus, sp_minus and
   first_signal_index; S+ accumulates positive standardized
   deviations beyond the slack k, S- the negative ones.
3. Run ewma_statistics(xs, mu0, sigma) and read ewma_series, ucl, lcl
   and first_signal_index; e smooths the raw values with weight lam and
   is compared against the per-sample limits.
4. Compare the two first-signal samples: EWMA with lam 0.2 usually
   fires first on gentle drifts, CUSUM on slightly stronger sustained
   steps; both beat a single-point check for small shifts.
5. Combine with monitoring_verdict(cusum_index, ewma_index, n) to get
   cusum_signaled, ewma_signaled, any_signal and the earlier
   first_signal_index.
6. For a one-call run use small_shift_monitoring_report(xs, mu0, sigma)
   which returns the cusum dict, the ewma dict and the verdict dict.
7. Confirm the deterministic checks with the contract test
   scripts/test_cusum_ewma_monitoring.py.

## Worked example

mu0 = 10, sigma = 1, xs = [10.2, 10.5, 11.0, 10.8, 11.5, 11.9, 12.2,
11.6, 12.0, 11.4, 11.8], k = 0.5, h = 5.0, lam = 0.2, L = 3.0.

- CUSUM S+ path: [0, 0, 0.5, 0.8, 1.8, 3.2, 4.9, 6.0, 7.5, 8.4, 9.7];
  S- stays 0 everywhere. First signal at sample 8 (x = 11.6, S+ = 6.0
  > 5.0); sample 7 sits at 4.9, just below the decision interval.
- EWMA e series: [10.040, 10.132, 10.306, 10.404, 10.624, 10.879,
  11.143, 11.234, 11.388, 11.390, 11.472]; UCL series: [10.600,
  10.768, 10.859, 10.912, 10.945, 10.965, 10.978, 10.986, 10.991,
  10.994, 10.996] widening toward the steady-state limit 11.000. First
  signal at sample 7 (x = 12.2, e = 11.143 > UCL 10.978).
- Contrast: every raw value stays within 10 +- 3, so a single-point
  3-sigma check on this sequence finds nothing; the accumulation charts
  flag it, which is the gap this leaf fills.
- Verdict: any_signal True, first_signal_index 7 (EWMA fires before
  CUSUM on this drift).
- The module outputs above are the exact recursion results, rounded to
  three decimals; they agree with the spec anchor lists at display
  precision (the exact closed-form UCL values are asserted to 1e-9 in
  the contract test).

## Verification

- Confirm cusum_statistics returns the S+ path above to 1e-9, all-zero
  S- for the worked sequence, and first_signal_index 8.
- Confirm a constant mu0 series leaves S+ and S- at 0 with no signal,
  and that a sustained negative shift fires on the S- side.
- Confirm ewma_statistics reproduces the e and UCL series above, e_1 =
  lam * x_1 + (1 - lam) * mu0 exactly, first_signal_index 7, and that
  the last sigma_e of a 200-sample in-control run sits within 0.1
  percent of sigma * sqrt(lam / (2 - lam)).
- Confirm monitoring_verdict and small_shift_monitoring_report report
  any_signal True with first_signal_index 7 for the worked sequence and
  False/None for a flat sequence.
- Confirm ValueError rejection of empty xs, sigma <= 0, k <= 0, h <=
  0, lam <= 0 or lam > 1, L <= 0 and n < 0.
- Run the contract test offline: python3
  scripts/test_cusum_ewma_monitoring.py (34 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/statistical-process-control: the
  large-shift charting sibling (point rules and index-based process
  scoring); the boundary is point rules for large shifts here vs
  accumulation statistics for small shifts in this leaf.
- manufacturing-quality/as9100/corrective-action: downstream response
  planning once a monitoring signal fires.

## Pitfalls

- Running the charts without a validated in-control reference: the
  statistics assume independent, normal observations around mu0 with
  known sigma, so a mu0 or sigma pulled from a drifting process fires
  signals that are artefacts of the reference, not of the shift.
- Declaring the process fine from a single-point check: every raw value
  in the worked sequence sits within mu0 +- 3 sigma, yet EWMA signals at
  sample 7 and CUSUM at sample 8 — the accumulation statistics exist
  precisely because the point check misses small sustained shifts.
- Reading only the S+ side: a sustained negative shift accumulates on
  S- (which stays at 0 for the worked example) and fires only there;
  both sides must be read before declaring in control.
- Judging charts by which fires first: EWMA with lam 0.2 usually leads
  on gentle drifts and CUSUM on slightly stronger sustained steps (7 vs
  8 in the worked example), so an earlier first signal is a behaviour of
  the statistic, not proof of a larger shift.
- Comparing EWMA values against steady-state limits: the per-sample
  sigma_e widens from the first sample toward sigma * sqrt(lam /
  (2 - lam)), so early samples face narrower limits and late-sample
  comparisons against the steady state misplace the signal.
- Passing non-physical parameters: empty xs, sigma <= 0, k <= 0, h <= 0,
  lam outside (0, 1], L <= 0 and n < 0 raise ValueError, and silent
  defaults (k 0.5, h 5.0, lam 0.2, L 3.0) only suit the 1-sigma-shift
  detection context they were designed for.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cusum_ewma_monitoring.py

The test covers the worked-example anchors (CUSUM S+ path to 1e-9,
first CUSUM signal at sample 8, EWMA e and UCL display series, first
EWMA signal at sample 7), the in-control all-zero CUSUM behaviour, the
EWMA steady-state sigma_e limit within 0.1 percent, the exact
closed-form UCL identity with LCL mirroring, outlier jump and decay,
lambda = 1 passthrough, dict key contracts, deterministic run-to-run
floats, and ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: AS9100 frames the quality
  management and data-analysis context (standards-map.yaml); the CUSUM
  and EWMA relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
