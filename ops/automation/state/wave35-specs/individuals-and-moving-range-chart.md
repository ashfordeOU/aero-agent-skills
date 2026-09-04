# Wave-35 leaf spec: individuals-and-moving-range-chart (manufacturing-quality, as9100 pack)

- Path: skills/manufacturing-quality/as9100/individuals-and-moving-range-chart/
- Pack: as9100. Closest siblings: statistical-process-control (the
  SUBGROUP variables SPC leaf: X-bar and R charts with the A2/D3/D4
  constants for subgroup sizes 2-10, d2 sigma estimate, Cp/Cpk,
  Western Electric rules; its pitfall states n=1 is unsupported -
  subgroup size outside the constants table raises ValueError),
  cusum-ewma-monitoring (CUSUM/EWMA small-shift statistics),
  attribute-control-charts (wave-35: p/np/c/u attribute charts).
  Repo-wide grep proves ZERO owners for individuals chart, moving
  range chart, I-MR.
- Standards id: as9100 (reference-only; SPC sibling convention).
  Ledger Standard: as9100.
- Family: manufacturing-quality

## Claim

Run an individuals (I) and moving-range (MR) control chart when the
process yields one measurement per lot or subgroup (destructive
testing, single unit per batch, bond or coating lot): compute the
moving ranges between successive measurements, the average moving
range, the individuals chart limits from the mean plus and minus E2
times the average moving range (E2 = 2.66), the process standard
deviation estimate from the average moving range over d2 (d2 =
1.128), the moving range chart upper limit at 3.267 times the
average moving range, flag the individual values and moving ranges
outside their limits, and return the in-control or out-of-control
verdict for the single-measurement process. Produces the central
lines, the limits, the flagged points, and the stability verdict
that gate lot-to-lot process control when no subgroups are
available.

Does NOT do: X-bar/R and X-bar/S subgroup charts with the A2/D3/D4
constants (statistical-process-control); Cp/Cpk capability indices
(statistical-process-control); CUSUM/EWMA monitoring statistics
(cusum-ewma-monitoring); p/np/c/u attribute charts
(attribute-control-charts); gage studies.

## Model (implement exactly)

Module constants:
- E2 = 2.66 (individuals chart constant for n = 1).
- D2_N1 = 1.128 (d2 constant for n = 2 moving ranges).
- D3_MR_UCL = 3.267 (moving range chart upper factor).

Conventions: input is a time-ordered list of individual
measurements. The moving range at position i is |x_i - x_{i-1}| for
i >= 1, giving N-1 moving ranges for N individuals. All limits come
from the average moving range (no per-subgroup range averaging).

Functions (pure stdlib):
- moving_ranges(values) -> list of |x_i - x_{i-1}|. ValueError:
  fewer than 2 values.
- individuals_limits(values) -> dict {mean, mr_bar, sigma_hat,
  UCL, LCL}: mr_bar = mean(moving_ranges); sigma_hat = mr_bar /
  D2_N1; UCL = mean + E2 * mr_bar; LCL = mean - E2 * mr_bar.
  ValueErrors: fewer than 2 values.
- moving_range_limits(values) -> dict {mr_bar, UCL} = 3.267 *
  mr_bar (LCL is 0). ValueErrors as above.
- flag_points(values, ucl, lcl) -> list of indices where the value
  is outside [lcl, ucl]. ValueErrors: empty values.
- stability_verdict(individual_flags, mr_flags) -> "in-control"
  when both flag lists are empty else "out-of-control".
- imr_summary(values) -> dict with mean, mr_bar, sigma_hat, X UCL
  and LCL, MR UCL, flagged individuals, flagged moving ranges,
  verdict.

Identity to test: for a constant series the moving ranges are all
zero, sigma_hat is 0 and the X limits collapse to the constant mean;
with exactly two values the single moving range equals their
absolute difference and UCL_X = mean + 2.66 * |difference|.

## Worked example

Reference data: 12 bond-lot pull-off force measurements (one
destructive sample per lot), values [42.1, 41.6, 43.0, 42.4, 41.2,
44.1, 43.5, 42.8, 41.9, 43.2, 44.0, 42.6].

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- mean = 42.700; mr_bar = 1.118.
- sigma_hat = 1.118 / 1.128 = 0.991.
- X chart: UCL = 42.700 + 2.66 * 1.118 = 45.674; LCL = 42.700 -
  2.66 * 1.118 = 39.726.
- MR chart: UCL = 3.267 * 1.118 = 3.653 (LCL 0).
- Max |MR| = 2.90 <= 3.653 and every individual inside
  [39.726, 45.674] -> verdict in-control (lot-to-lot stability
  demonstrated with no subgroup data).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: fewer than 2 values; empty values list.
- Moving ranges: [1, 5, 2] -> [4, 3]; constant series -> all zero.
- X limits: worked example UCL 45.674 / LCL 39.726 within 1e-3;
  sigma_hat 0.991 within 1e-3; adding a large outlier widens the
  limits (moving range grows).
- MR UCL: worked example 3.653 within 1e-3.
- Flagging: one injected individual far outside (e.g. 50.0 in the
  worked series) -> flagged index 12 (0-based 11? no: 50.0 appended
  at index 12 -> flagged) and verdict out-of-control; an injected
  large moving range flags that MR position.
- Two-value series: mr_bar equals |x1 - x0|; identity checks above.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-individuals-and-moving-range-chart.yaml)

Query 1 (copy verbatim):
  "run an individuals and moving range control chart for one measurement per lot with destructive testing"
  intent: "manufacturing-quality; I-MR chart for single measurements per lot"
  expected_skill: "manufacturing-quality/as9100/individuals-and-moving-range-chart"
Query 2 (copy verbatim):
  "compute the moving range control limits and the process sigma estimate for a variable process without subgroups"
  intent: "manufacturing-quality; moving range limits and sigma estimate for individuals data"
  expected_skill: "manufacturing-quality/as9100/individuals-and-moving-range-chart"
Task ids: w35-individuals-and-moving-range-chart-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run an individuals and
moving range control chart:" and include the outputs in the Claim.
First tag: individuals-and-moving-range-chart. Additional tags
ONLY: moving-range-chart, individuals-chart, single-measurement-
control, lot-monitoring-chart. NEVER single generic words
(individuals, moving range, chart, sigma, limits, process, lot).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): X-bar, R chart, A2, D3, D4,
Cp, Cpk, capability index, Western Electric (statistical-process-
control); CUSUM, EWMA (cusum-ewma-monitoring); p-chart, np-chart,
c-chart, u-chart (attribute-control-charts); gage, GRR.
