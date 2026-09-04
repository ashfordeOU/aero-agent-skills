# Wave-34 leaf spec: cusum-ewma-monitoring (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/cusum-ewma-monitoring/
- Pack: as9100. Closest sibling: statistical-process-control (Shewhart
  charts: X-bar/R limits, d2 sigma, Cp/Cpk, Western Electric point
  rules; large-shift detection). This leaf owns cumulative and
  exponentially weighted evidence accumulation for SMALL sustained
  mean shifts: tabular CUSUM (standardized z, slack k, decision
  interval h) and EWMA recursion with time-varying sigma limits. No
  function overlap (SPC functions: xbar_r_limits, process_sigma,
  capability_indices, out_of_control_rules).
- Standards id: as9100 (reference-only; sibling convention). Ledger
  Standard: as9100.
- Family: manufacturing-quality

## Claim

Monitor a production process for small sustained mean shifts with
sequential control charts: the tabular CUSUM path (upper S+ and lower
S- statistics from standardized deviations with slack k and decision
interval h) with the first signal sample, the EWMA recursion with
time-varying sigma limits and its first signal sample, and the
combined monitoring verdict. Produces the CUSUM and EWMA statistics
paths, first-signal indices, the EWMA control limits and the verdict
that catches small shifts a Shewhart chart misses.

Does NOT do: Shewhart X-bar/R charts and capability indices
(statistical-process-control owns large-shift charting and Cpk);
control plans and corrective action (their own as9100 leaves).

## Model (implement exactly)

Conventions: observations x_i are assumed iid normal around the
in-control mean mu0 with known sigma (or sigma estimated in-control).
Standardized z_i = (x_i - mu0)/sigma.

Tabular CUSUM (one-sided upper and lower):
- S+_i = max(0, z_i - k + S+_{i-1}), S-_i = max(0, -z_i - k +
  S-__{i-1}), starting S+_0 = S-_0 = 0.
- A signal occurs when S+_i > h or S-_i > h. Defaults k = 0.5,
  h = 5.0 (standard choice for detecting a 1-sigma shift, ARL
  properties ~ standard).

EWMA (lambda-weighted recursion):
- e_0 = mu0; e_i = lam x_i + (1 - lam) e_{i-1}.
- Time-varying limits: sigma_e_i = sigma sqrt(lam/(2 - lam) (1 -
  (1 - lam)^(2 i))); UCL_i = mu0 + L sigma_e_i; LCL_i = mu0 -
  L sigma_e_i. Defaults lam = 0.2, L = 3.0.

Functions (pure stdlib):
- cusum_statistics(xs, mu0, sigma, k = 0.5, h = 5.0) -> dict
  {sp_plus (list), sp_minus (list), first_signal_index (int or
  None)}. ValueErrors: empty xs, sigma <= 0, k <= 0, h <= 0.
- ewma_statistics(xs, mu0, sigma, lam = 0.2, L = 3.0) -> dict
  {ewma_series (list), ucl (list), lcl (list), first_signal_index}.
  ValueErrors: empty xs, sigma <= 0, lam <= 0 or lam > 1, L <= 0.
- monitoring_verdict(cusum_signal_index, ewma_signal_index, n) ->
  dict {cusum_signaled (bool), ewma_signaled (bool), any_signal
  (bool), first_signal_index (min of the two or None)}.
  ValueErrors: n < 0.
- small_shift_monitoring_report(xs, mu0, sigma, k, h, lam, L) -> dict
  combining cusum_statistics, ewma_statistics and
  monitoring_verdict.

Chart identity to test: for an in-control sequence the CUSUM S+ and
S- remain at 0 (no signal) when every z_i <= k; EWMA of a constant
series converges toward mu0 with no signal. A sustained +1-sigma-ish
step produces a CUSUM signal after the tabular accumulation crosses h.

## Worked example

Reference: mu0 = 10, sigma = 1, sequence [10.2, 10.5, 11.0, 10.8,
11.5, 11.9, 12.2, 11.6, 12.0, 11.4, 11.8], k = 0.5, h = 5.0,
lam = 0.2, L = 3.0.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- cusum S+ path: [0, 0, 0.5, 0.8, 1.8, 3.2, 4.9, 6.0, 7.5, 8.4, 9.7]
  with S- all 0; first_signal_index = 8 (1-based sample 8, x = 11.6,
  S+ = 6.0 > 5.0).
- ewma series (lam 0.2): e = [10.040, 10.132, 10.306, 10.404,
  10.624, 10.879, 11.143, 11.234, 11.387, 11.390, 11.472] with UCL =
  [10.600, 10.768, 10.859, 10.912, 10.945, 10.965, 10.978, 10.987,
  10.993, 10.997, 11.000]; first_signal_index = 7 (x = 12.2, e =
  11.143 > UCL 10.978).
- Contrast: a Shewhart 3-sigma single-point check finds NO violation
  in this sequence (all x_i within 10 +- 3), the gap this leaf fills.
- monitoring_verdict: any_signal True, first_signal_index = 7 (EWMA
  fires before CUSUM here).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty xs; sigma <= 0; k <= 0; h <= 0; lam <= 0 or > 1;
  L <= 0; n < 0.
- CUSUM path: the worked S+ path matches the listed values to 1e-9;
  S- stays 0 for the worked sequence; in-control constant mu0 series
  gives all-zero statistics; a single huge outlier gives S+ jump of
  (z - k) then reset if below h.
- EWMA: the worked e-series and UCL series match to 1e-6;
  e_1 = lam x_1 + (1-lam) mu0 exactly; steady-state sigma_e limit =
  sigma sqrt(lam/(2-lam)) as i grows (check the last limit within
  0.1%).
- Signal indices: worked first_signal_index 8 (CUSUM) and 7 (EWMA);
  a flat in-control series returns None for both.
- Verdict: combined report any_signal True for the worked sequence;
  all-clear sequence returns False/None.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-cusum-ewma-monitoring.yaml)

Query 1 (copy verbatim):
  "run the tabular cusum control chart statistics over a production sequence and report the first signal sample for a small sustained mean shift"
  intent: "manufacturing-quality; tabular CUSUM path and first signal for small mean shift"
  expected_skill: "manufacturing-quality/as9100/cusum-ewma-monitoring"
Query 2 (copy verbatim):
  "compute the ewma recursion with time varying control limits and the monitoring verdict for small shift detection in statistical process control"
  intent: "manufacturing-quality; EWMA recursion, time varying limits and monitoring verdict"
  expected_skill: "manufacturing-quality/as9100/cusum-ewma-monitoring"
Task ids: w34-cusum-ewma-monitoring-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must monitor a production process
for small sustained mean shifts:" and include the outputs in the
Claim. First tag: cusum-ewma-monitoring. Additional tags ONLY:
cusum-control-chart, ewma-control-chart, cumulative-sum-monitoring,
small-shift-detection, sequential-process-monitoring. NEVER single
generic words (control, chart, process, monitoring, shift, statistics).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): Shewhart, X-bar, range chart,
Western Electric, capability, Cp, Cpk (statistical-process-control
owns the large-shift Shewhart content); control plan (its own leaf);
corrective action (corrective-action leaf). The words "CUSUM", "EWMA",
"small shift", "sequential monitoring", "decision interval" are this
leaf's own.

Tags: [cusum-ewma-monitoring, cusum-control-chart, ewma-control-chart,
cumulative-sum-monitoring, small-shift-detection,
sequential-process-monitoring]

Sibling-citation lines for Related leaves:
manufacturing-quality/as9100/statistical-process-control (the Shewhart
sibling; boundary: large-shift point rules vs small-shift accumulation),
manufacturing-quality/as9100/corrective-action (downstream response
when a signal fires).

Ledger Standard: as9100.
